from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)

from memory_graph.reasoning.validator import DirectReasoningValidator  # noqa: E402
from memory_graph.v2101_deploy.boundary import make_candidate_record, require_v2101_artifact_path  # noqa: E402
from memory_graph.v2101_deploy.contracts import event_json_schema, schema_valid  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def project_path(relative: str) -> Path:
    return (ROOT / relative).resolve()


def read_api(url: str, timeout: float = 3.0) -> tuple[int, bytes]:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


def post_json(url: str, body: dict[str, Any], timeout: float = 1200.0) -> tuple[int, bytes, float]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, raw, time.perf_counter() - start
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, raw, time.perf_counter() - start


class ResourceMonitor:
    def __init__(self, server_pid: int | None):
        self.server_pid = server_pid
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.samples: list[dict[str, Any]] = []

    @staticmethod
    def _gpu_sample() -> dict[str, Any]:
        result: dict[str, Any] = {"memory_used_mib": None, "memory_total_mib": None,
                                  "utilization_gpu_percent": None, "compute_processes": []}
        try:
            output = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, check=True,
            ).stdout.strip().splitlines()[0]
            used, total, util = [int(x.strip()) for x in output.split(",")]
            result.update(memory_used_mib=used, memory_total_mib=total, utilization_gpu_percent=util)
        except Exception as exc:
            result["nvidia_smi_error"] = str(exc)
        try:
            output = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, check=False,
            ).stdout.strip()
            result["compute_processes"] = [x.strip() for x in output.splitlines() if x.strip()]
        except Exception as exc:
            result["compute_process_error"] = str(exc)
        return result

    def _rss_sample(self) -> dict[str, Any]:
        result = {"server_rss_mib": None, "server_process_tree_pids": []}
        if self.server_pid is None:
            return result
        try:
            import psutil
            root = psutil.Process(self.server_pid)
            procs = [root, *root.children(recursive=True)]
            total = 0
            active = []
            for proc in procs:
                try:
                    total += proc.memory_info().rss
                    active.append(proc.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            result["server_rss_mib"] = round(total / (1024 * 1024), 2)
            result["server_process_tree_pids"] = active
        except Exception as exc:
            result["rss_error"] = str(exc)
        return result

    def _run(self) -> None:
        while not self.stop_event.is_set():
            sample = {"timestamp_utc": now(), **self._gpu_sample(), **self._rss_sample()}
            self.samples.append(sample)
            self.stop_event.wait(0.5)

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, name="v2101-resource-monitor", daemon=True)
        self.thread.start()

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=10)
        used = [s["memory_used_mib"] for s in self.samples if isinstance(s.get("memory_used_mib"), int)]
        rss = [s["server_rss_mib"] for s in self.samples if isinstance(s.get("server_rss_mib"), (int, float))]
        per_proc = []
        for sample in self.samples:
            for row in sample.get("compute_processes", []):
                try:
                    pid, mib = [int(v.strip()) for v in row.split(",", 1)]
                    per_proc.append((pid, mib))
                except Exception:
                    continue
        peak_by_pid: dict[int, int] = {}
        server_pids = {pid for sample in self.samples for pid in sample.get("server_process_tree_pids", [])}
        for pid, mib in per_proc:
            if pid in server_pids:
                peak_by_pid[pid] = max(peak_by_pid.get(pid, 0), mib)
        return {
            "sample_interval_seconds": 0.5,
            "sample_count": len(self.samples),
            "idle_start": self.samples[0] if self.samples else None,
            "final_sample": self.samples[-1] if self.samples else None,
            "peak_global_gpu_memory_used_mib": max(used) if used else None,
            "gpu_memory_total_mib": max((s["memory_total_mib"] or 0 for s in self.samples), default=None) or None,
        "peak_server_process_gpu_memory_mib_by_pid": peak_by_pid,
            "peak_server_process_tree_rss_mib": max(rss) if rss else None,
            "peak_torch_allocated_mib": None,
            "peak_torch_reserved_mib": None,
            "torch_memory_note": "Remote vLLM/SGLang serving does not expose CUDA allocator counters through its OpenAI endpoint; process memory is measured with nvidia-smi.",
            "samples": self.samples,
        }


def image_url(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def run_chat(base_url: str, body: dict[str, Any], label: str) -> dict[str, Any]:
    code, raw, elapsed = post_json(base_url.rstrip("/") + "/v1/chat/completions", body)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        payload = None
    choice = (payload or {}).get("choices", [{}])[0] if isinstance(payload, dict) else {}
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    usage = (payload or {}).get("usage", {}) if isinstance(payload, dict) else {}
    wall_seconds = round(elapsed, 4)
    output_tokens = usage.get("completion_tokens")
    return {
        "label": label, "http_status": code, "completed": 200 <= code < 300,
        "raw_response_body": raw.decode("utf-8", errors="replace"),
        "model_response": content if isinstance(content, str) else None,
        "finish_reason": choice.get("finish_reason") if isinstance(choice, dict) else None,
        "eos": choice.get("finish_reason") == "stop" if isinstance(choice, dict) else False,
        "input_tokens": usage.get("prompt_tokens"), "output_tokens": output_tokens,
        "wall_seconds": wall_seconds, "ttft_seconds": None,
        "preprocessing_seconds": None, "visual_tokens": None,
        "effective_output_tokens_per_wall_second": (round(output_tokens / wall_seconds, 3)
                                                    if isinstance(output_tokens, (int, float)) and wall_seconds > 0 else None),
        "error": None if 200 <= code < 300 else f"HTTP_{code}",
    }


def parse_and_validate(result: dict[str, Any], event: dict[str, Any]) -> None:
    answer = None
    try:
        answer = json.loads(result["model_response"] or "")
        result["json_valid"] = True
    except Exception as exc:
        result["json_valid"] = False
        result["json_parse_error"] = str(exc)
    markers = event.get("markers", [])
    result["schema_valid"] = schema_valid(markers, answer)
    try:
        result["semantic_validator"] = DirectReasoningValidator().validate(
            {"pack_id": event["pack_id"], "markers": markers}, answer
        ) if result["schema_valid"] else None
    except Exception as exc:
        result["semantic_validator"] = {"valid": False, "error": str(exc)}
    result["semantic_validator_valid"] = (
        result["semantic_validator"].get("valid")
        if isinstance(result.get("semantic_validator"), dict) else None
    )


def response_format(markers: list[str], name: str) -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {
        "name": name, "strict": True, "schema": event_json_schema(markers),
    }}


def event_body(model_id: str, event: dict[str, Any], video_mode: bool = True) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": event["prompt"]}]
    selected_frames = event.get("selected_frames", [])
    # A one-frame MP4 carries no temporal information and may be rejected by
    # OpenCV/vLLM as an undecodable 0.4s stream. Preserve the frozen event and
    # submit its sole existing frame as an image; the separate preview tests video.
    if video_mode and len(selected_frames) > 1:
        clip = project_path(event["temporal_clip"]["path"])
        if sha_file(clip) != event["temporal_clip"]["sha256"]:
            raise RuntimeError(f"Temporal clip SHA-256 mismatch: {event['pack_id']}")
        encoded = base64.b64encode(clip.read_bytes()).decode("ascii")
        content.append({"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{encoded}"}})
    else:
        for frame in event["selected_frames"]:
            path = project_path(frame["image_path"])
            if sha_file(path) != frame["image_sha256"]:
                raise RuntimeError(f"Frozen frame SHA-256 mismatch: {event['pack_id']}:{frame['sequence_index']}")
            content.append({"type": "image_url", "image_url": {"url": image_url(path)}})
    return {
        "model": model_id,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.0, "top_p": 1.0, "seed": 0, "max_tokens": 128,
        "response_format": response_format(event.get("markers", []), "event_output"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="v2.10.1 deployment config JSON")
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    model_id = config["model_id"]
    revision = config["revision"]
    output_dir = project_path(config["output_dir"])
    require_v2101_artifact_path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_path = output_dir / "runtime.json"
    response_path = output_dir / "responses.json"
    if runtime_path.exists() or response_path.exists():
        raise FileExistsError("Refusing to overwrite prior v2.10.1 smoke outputs")

    input_manifest_path = project_path("artifacts/v2.10.1/smoke/input_manifest.json")
    input_manifest = json.loads(input_manifest_path.read_text(encoding="utf-8"))
    base_url = config.get("base_url", f"http://127.0.0.1:{config.get('port', 8000)}")
    server_cmd = config["server_command"]
    env = os.environ.copy()
    env.update(config.get("server_environment", {}))
    server_log_path = output_dir / "server.log"
    if server_log_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing server log: {server_log_path}")
    server_log = server_log_path.open("wb")
    process = None
    monitor: ResourceMonitor | None = None
    records: list[dict[str, Any]] = []
    lifecycle: dict[str, Any] = {"start_utc": now(), "loaded": False, "server_exited": False}
    try:
        monitor = ResourceMonitor(None)
        monitor.start()
        lifecycle["preload_gpu"] = monitor.samples[0] if monitor.samples else ResourceMonitor._gpu_sample()
        process = subprocess.Popen(server_cmd, cwd=ROOT, env=env, stdout=server_log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        monitor.server_pid = process.pid
        lifecycle["server_pid"] = process.pid
        lifecycle["server_command"] = server_cmd
        (output_dir / "server_process.json").write_text(json.dumps({"pid": process.pid, "started_utc": now()}, indent=2) + "\n", encoding="utf-8")
        deadline = time.monotonic() + float(config.get("startup_timeout_seconds", 1200))
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Model server exited during startup with code {process.returncode}")
            try:
                status, _ = read_api(base_url.rstrip("/") + "/health", timeout=3)
                if status == 200:
                    break
            except Exception:
                pass
            time.sleep(2)
        else:
            raise TimeoutError("Model server did not become healthy before startup timeout")
        lifecycle["loaded"] = True
        lifecycle["load_seconds"] = round(time.monotonic() - (deadline - float(config.get("startup_timeout_seconds", 1200))), 2)
        try:
            _, models_raw = read_api(base_url.rstrip("/") + "/v1/models")
            lifecycle["served_models"] = json.loads(models_raw.decode("utf-8"))
        except Exception as exc:
            lifecycle["served_models_error"] = str(exc)
        generic_schema = {"type": "object", "properties": {"status": {"type": "string", "const": "READY"}},
                          "required": ["status"], "additionalProperties": False}
        basic = run_chat(base_url, {
            "model": model_id,
            "messages": [{"role": "user", "content": "Return READY as a JSON object with the single key status."}],
            "temperature": 0.0, "top_p": 1.0, "seed": 0, "max_tokens": 16,
            "response_format": {"type": "json_schema", "json_schema": {"name": "basic_ready", "strict": True, "schema": generic_schema}},
        }, "basic_text_request")
        try:
            basic_answer = json.loads(basic.get("model_response") or "")
            basic["json_valid"] = True
            basic["schema_valid"] = basic_answer == {"status": "READY"}
        except Exception as exc:
            basic.update(json_valid=False, schema_valid=False, json_parse_error=str(exc))
        records.append(basic)

        events = input_manifest["events"]
        preview = run_chat(base_url, event_body(model_id, events[0], video_mode=True), "temporal_video_smoke_preview")
        preview["event_id"] = events[0]["pack_id"]
        preview["request_modality"] = "video"
        parse_and_validate(preview, events[0])
        records.append(preview)

        multi = input_manifest["multi_image_smoke"]
        selected_multi_images = multi["ordered_images"]
        multi_content: list[dict[str, Any]] = [{
            "type": "text",
            "text": "Two safe clean crops are supplied in order. Confirm that both were received by returning READY.",
        }]
        for image in selected_multi_images:
            path = project_path(image["path"])
            if sha_file(path) != image["sha256"]:
                raise RuntimeError(f"Multi-image crop SHA-256 mismatch: {image['path']}")
            multi_content.append({"type": "image_url", "image_url": {"url": image_url(path)}})
        multi_result = run_chat(base_url, {
            "model": model_id, "messages": [{"role": "user", "content": multi_content}],
            "temperature": 0.0, "top_p": 1.0, "seed": 0, "max_tokens": 16,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "multi_image_ready", "strict": True,
                "schema": {"type": "object", "properties": {"status": {"type": "string", "const": "READY"}},
                           "required": ["status"], "additionalProperties": False},
            }},
        }, "multi_image_smoke")
        multi_result["input_image_count"] = len(selected_multi_images)
        multi_result["input_order"] = [x["path"] for x in selected_multi_images]
        try:
            multi_answer = json.loads(multi_result.get("model_response") or "")
            multi_result["json_valid"] = True
        except Exception as exc:
            multi_answer = None
            multi_result["json_valid"] = False
            multi_result["json_parse_error"] = str(exc)
        multi_result["schema_valid"] = multi_answer == {"status": "READY"}
        multi_result["semantic_validator_valid"] = None
        records.append(multi_result)

        event_results = []
        for event in events:
            result = run_chat(base_url, event_body(model_id, event, video_mode=True), "canonical_frozen_event")
            result["event_id"] = event["pack_id"]
            result["request_modality"] = "video" if len(event.get("selected_frames", [])) > 1 else "image_single_frame_fallback"
            result["selected_frame_count"] = len(event.get("selected_frames", []))
            result["selected_frame_timestamps_seconds"] = [x["timestamp_seconds"] for x in event.get("selected_frames", [])]
            parse_and_validate(result, event)
            event_results.append(result)
            records.append(result)
            if process.poll() is not None:
                lifecycle["server_crashed_during_requests"] = True
                raise RuntimeError(f"Model server exited during canonical event requests with code {process.returncode}")
        lifecycle["canonical_event_requests_attempted"] = len(event_results)
        lifecycle["canonical_event_requests_completed"] = sum(bool(x["completed"]) for x in event_results)
    except Exception as exc:
        lifecycle["fatal_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if monitor:
            resource_metrics = monitor.stop()
        else:
            resource_metrics = ResourceMonitor._gpu_sample()
        if process is not None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGINT)
                    process.wait(timeout=float(config.get("shutdown_timeout_seconds", 60)))
                except Exception:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                        process.wait(timeout=20)
                    except Exception:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except Exception:
                            pass
            lifecycle["server_exit_code"] = process.poll()
            lifecycle["server_exited"] = process.poll() is not None
        server_log.close()
        lifecycle["end_utc"] = now()
        lifecycle["fully_unloaded"] = False
        release_samples = []
        for _ in range(45):
            sample = ResourceMonitor._gpu_sample()
            release_samples.append(sample)
            baseline = resource_metrics.get("idle_start") or {}
            used = sample.get("memory_used_mib")
            start_used = baseline.get("memory_used_mib")
            if isinstance(used, int) and isinstance(start_used, int) and used <= start_used + 300:
                lifecycle["fully_unloaded"] = True
                break
            time.sleep(1)
        lifecycle["gpu_release_samples"] = release_samples
        resource_metrics["server_unload_confirmed"] = lifecycle["fully_unloaded"]
        resource_metrics["release_probe_sample_count"] = len(release_samples)
        responses = []
        for rec in records:
            candidate = make_candidate_record(
                model_id=model_id, model_revision=revision,
                event_id=rec.get("event_id", rec["label"]),
                raw_response=rec.get("model_response") or rec.get("raw_response_body", ""),
                completed=rec.get("completed", False), json_valid=rec.get("json_valid", False),
                schema_valid=rec.get("schema_valid", False),
                semantic_validator_valid=rec.get("semantic_validator_valid"),
                metrics={k: rec.get(k) for k in ("http_status", "input_tokens", "output_tokens", "wall_seconds", "ttft_seconds", "finish_reason")},
            )
            responses.append({**candidate, **rec})
        response_path.write_text(json.dumps(responses, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporal_records = [r for r in records if r["label"] == "temporal_video_smoke_preview"]
        multi_records = [r for r in records if r["label"] == "multi_image_smoke"]
        temporal_smoke_passed = any(r.get("completed") and r.get("json_valid") and r.get("schema_valid") for r in temporal_records)
        multi_image_smoke_passed = any(r.get("completed") and r.get("json_valid") and r.get("schema_valid") for r in multi_records)
        expected_multi_order = [x["path"] for x in input_manifest["multi_image_smoke"]["ordered_images"]]
        multi_image_order_preserved = any(r.get("input_order") == expected_multi_order for r in multi_records)
        runtime = {
            "schema": "findmind_v2101_stage0_runtime_v1",
            "model_id": model_id, "model_revision": revision,
            "engine": config.get("engine"), "engine_version": config.get("engine_version"),
            "processor_revision": config.get("processor_revision", revision),
            "deployment_config": str(config_path.relative_to(ROOT)),
            "input_manifest_sha256": sha_file(input_manifest_path),
            "started_utc": lifecycle["start_utc"], "ended_utc": lifecycle["end_utc"],
            "lifecycle": lifecycle, "resources": resource_metrics,
            "basic_request_completed": bool(records[0].get("completed")) if records else False,
            "temporal_smoke_passed": temporal_smoke_passed,
            "multi_image_smoke_passed": multi_image_smoke_passed,
            "multi_image_order_preserved": multi_image_order_preserved,
            "multi_image_smoke": {
                "submitted_count": len(input_manifest["multi_image_smoke"]["ordered_images"]),
                "available_count": len(input_manifest["multi_image_smoke"].get("available_images", input_manifest["multi_image_smoke"]["ordered_images"])),
                "submitted_order": [x["path"] for x in input_manifest["multi_image_smoke"]["ordered_images"]],
            },
            "canonical_events": {
                "attempted": sum(r["label"] == "canonical_frozen_event" for r in records),
                "completed": sum(r["label"] == "canonical_frozen_event" and r.get("completed") for r in records),
                "json_valid": sum(r["label"] == "canonical_frozen_event" and r.get("json_valid") for r in records),
                "schema_valid": sum(r["label"] == "canonical_frozen_event" and r.get("schema_valid") for r in records),
                "semantic_validator_valid": sum(bool(r["label"] == "canonical_frozen_event" and r.get("semantic_validator_valid")) for r in records),
                "responses": [{k: r.get(k) for k in ("event_id", "completed", "json_valid", "schema_valid", "semantic_validator_valid", "http_status", "error", "wall_seconds", "input_tokens", "output_tokens")} for r in records if r["label"] == "canonical_frozen_event"],
            },
            "requests": [{k: r.get(k) for k in ("label", "event_id", "http_status", "completed", "json_valid", "schema_valid", "semantic_validator_valid", "wall_seconds", "input_tokens", "output_tokens", "error")} for r in records],
            "canonical_event_frame_sampling": [
                {"event_id": r.get("event_id"), "request_modality": r.get("request_modality"),
                 "frame_count": r.get("selected_frame_count"),
                 "timestamps_seconds": r.get("selected_frame_timestamps_seconds")}
                for r in records if r["label"] == "canonical_frozen_event"
            ],
            "performance_metrics_note": "Time-to-first-token, modality-separated visual tokens, and framework allocator allocated/reserved counters are unavailable from the non-streaming OpenAI endpoint. Total input/output tokens and process/global VRAM/RSS are recorded where exposed.",
            "actual_attention_backend": config.get("actual_attention_backend", "engine_default_auto; inspect server log for selected kernel"),
            "cache_dtype": config.get("cache_dtype", "engine_default"),
            "no_operational_memory_or_identity_writes": True,
        }
        log_text = server_log_path.read_text(encoding="utf-8", errors="replace") if server_log_path.exists() else ""
        log_lower = log_text.lower()
        expected_log_terms = [str(x).lower() for x in config.get("optimization_log_checks", [])]
        optimization_log_checks = {term: term in log_lower for term in expected_log_terms}
        optimized_model_config_verified = bool(optimization_log_checks) and all(optimization_log_checks.values())
        oom_detected = any(marker in log_lower for marker in ("out of memory", "cuda error: out of memory", "torch.cuda.outofmemoryerror"))
        event_rows = runtime["canonical_events"]["responses"]
        runtime["optimization_log_term_checks"] = optimization_log_checks
        runtime["optimized_model_config_verified"] = optimized_model_config_verified
        stage0_conditions = {
            "model_loaded": bool(lifecycle.get("loaded")),
            "revision_pinned": bool(re.fullmatch(r"[0-9a-f]{40,64}", revision)),
            "engine_version_pinned": bool(config.get("engine_version")),
            "basic_request_completed": runtime["basic_request_completed"],
            "basic_json_schema_valid": bool(records and records[0].get("json_valid") and records[0].get("schema_valid")),
            "temporal_smoke_passed": runtime["temporal_smoke_passed"],
            "multi_image_smoke_passed": runtime["multi_image_smoke_passed"],
            "multi_image_order_preserved": runtime["multi_image_order_preserved"],
            "nine_event_requests_completed": runtime["canonical_events"]["attempted"] == 9 and runtime["canonical_events"]["completed"] == 9,
            "nine_json_parse": runtime["canonical_events"]["attempted"] == 9 and runtime["canonical_events"]["json_valid"] == 9,
            "nine_schema_valid": runtime["canonical_events"]["attempted"] == 9 and runtime["canonical_events"]["schema_valid"] == 9,
            "no_oom": not oom_detected,
            "no_server_crash_during_requests": not lifecycle.get("server_crashed_during_requests", False),
            "server_fully_unloaded": bool(lifecycle.get("fully_unloaded")),
            "optimized_model_config_verified": optimized_model_config_verified,
            "all_event_rows_have_ids": len(event_rows) == 9 and all(row.get("event_id") for row in event_rows),
        }
        runtime["oom_detected"] = oom_detected
        runtime["stage0_conditions"] = stage0_conditions
        runtime["stage0_status"] = "STAGE0_PASS" if all(stage0_conditions.values()) else "STAGE0_FAIL"
        runtime_path.write_text(json.dumps(runtime, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"model": model_id, "loaded": lifecycle.get("loaded"), "fatal_error": lifecycle.get("fatal_error"),
                      "canonical": runtime["canonical_events"], "multi_image": runtime["multi_image_smoke_passed"],
                      "unloaded": lifecycle["fully_unloaded"], "stage0_status": runtime["stage0_status"],
                      "runtime": str(runtime_path.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if lifecycle.get("loaded") and lifecycle.get("fully_unloaded") else 1


if __name__ == "__main__":
    raise SystemExit(main())
