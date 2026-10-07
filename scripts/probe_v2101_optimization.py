from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)

from memory_graph.v2101_deploy.boundary import make_candidate_record, require_v2101_artifact_path  # noqa: E402
from run_v2101_model_smoke import (  # noqa: E402
    ResourceMonitor,
    event_body,
    now,
    parse_and_validate,
    project_path,
    read_api,
    run_chat,
    sha_file,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--trial-name", required=True)
    parser.add_argument("--probe", choices=("basic", "video"), default="video")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,48}", args.trial_name):
        raise ValueError("trial name must be a simple lowercase slug")

    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    model_id = config["model_id"]
    revision = config["revision"]
    candidate = config_path.parent.name
    output_dir = ROOT / "artifacts/v2.10.1/deployment" / candidate / "trials" / args.trial_name
    require_v2101_artifact_path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    log_path = output_dir / "server.log"
    response_path = output_dir / "probe_response.json"
    runtime_path = output_dir / "trial.json"
    server_log = log_path.open("wb")
    server_cmd = config["server_command"]
    env = os.environ.copy()
    env.update(config.get("server_environment", {}))
    base_url = config.get("base_url", f"http://127.0.0.1:{config['port']}")
    process = None
    monitor = ResourceMonitor(None)
    lifecycle = {"start_utc": now(), "loaded": False, "server_exited": False}
    records: list[dict] = []
    trial_start = time.monotonic()
    try:
        monitor.start()
        lifecycle["preload_gpu"] = monitor.samples[0] if monitor.samples else ResourceMonitor._gpu_sample()
        process = subprocess.Popen(server_cmd, cwd=ROOT, env=env, stdout=server_log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        monitor.server_pid = process.pid
        lifecycle["server_pid"] = process.pid
        (output_dir / "server_process.json").write_text(
            json.dumps({"pid": process.pid, "started_utc": now()}, indent=2) + "\n", encoding="utf-8"
        )
        deadline = time.monotonic() + float(config.get("startup_timeout_seconds", 3600))
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"server exited during optimization preflight with code {process.returncode}")
            try:
                status, _ = read_api(base_url.rstrip("/") + "/health", timeout=3)
                if status == 200:
                    lifecycle["loaded"] = True
                    lifecycle["load_seconds"] = round(time.monotonic() - trial_start, 2)
                    break
            except Exception:
                pass
            time.sleep(2)
        else:
            raise TimeoutError("server did not become healthy before the optimization-trial timeout")

        ready = run_chat(base_url, {
            "model": model_id,
            "messages": [{"role": "user", "content": "Return READY as JSON with only the key status."}],
            "temperature": 0.0, "top_p": 1.0, "seed": 0, "max_tokens": 16,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "basic_ready", "strict": True,
                "schema": {"type": "object", "properties": {"status": {"type": "string", "const": "READY"}},
                           "required": ["status"], "additionalProperties": False},
            }},
        }, "optimization_basic_probe")
        try:
            answer = json.loads(ready.get("model_response") or "")
            ready["json_valid"] = True
            ready["schema_valid"] = answer == {"status": "READY"}
        except Exception as exc:
            ready.update(json_valid=False, schema_valid=False, json_parse_error=str(exc))
        records.append(ready)

        if args.probe == "video":
            manifest = json.loads(project_path("artifacts/v2.10.1/smoke/input_manifest.json").read_text(encoding="utf-8"))
            event = manifest["events"][0]
            preview = run_chat(base_url, event_body(model_id, event, video_mode=True), "optimization_video_probe")
            preview["event_id"] = event["pack_id"]
            preview["selected_frame_count"] = len(event["selected_frames"])
            parse_and_validate(preview, event)
            records.append(preview)
        lifecycle["server_alive_after_probe"] = process.poll() is None
        if not lifecycle["server_alive_after_probe"]:
            lifecycle["server_crashed_during_probe"] = True
    except Exception as exc:
        lifecycle["fatal_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        resources = monitor.stop()
        if process is not None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGINT)
                    process.wait(timeout=float(config.get("shutdown_timeout_seconds", 120)))
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
        baseline = resources.get("idle_start") or {}
        for _ in range(90):
            sample = ResourceMonitor._gpu_sample()
            release_samples.append(sample)
            used, start_used = sample.get("memory_used_mib"), baseline.get("memory_used_mib")
            if isinstance(used, int) and isinstance(start_used, int) and used <= start_used + 300:
                lifecycle["fully_unloaded"] = True
                break
            time.sleep(1)
        lifecycle["gpu_release_samples"] = release_samples
        resources["server_unload_confirmed"] = lifecycle["fully_unloaded"]
        resources["release_probe_sample_count"] = len(release_samples)

        response_records = []
        for rec in records:
            candidate_record = make_candidate_record(
                model_id=model_id, model_revision=revision,
                event_id=rec.get("event_id", rec["label"]),
                raw_response=rec.get("model_response") or rec.get("raw_response_body", ""),
                completed=rec.get("completed", False), json_valid=rec.get("json_valid", False),
                schema_valid=rec.get("schema_valid", False),
                semantic_validator_valid=rec.get("semantic_validator_valid"),
                metrics={k: rec.get(k) for k in ("http_status", "input_tokens", "output_tokens", "wall_seconds", "ttft_seconds")},
            )
            response_records.append({**candidate_record, **rec})
        response_path.write_text(json.dumps(response_records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
        log_lower = log_text.lower()
        expected_terms = [x.lower() for x in config.get("optimization_log_checks", [])]
        term_checks = {term: term in log_lower for term in expected_terms}
        runtime = {
            "schema": "findmind_v2101_optimization_trial_v1",
            "trial_name": args.trial_name, "probe_kind": args.probe,
            "model_id": model_id, "model_revision": revision,
            "engine": config.get("engine"), "engine_version": config.get("engine_version"),
            "weight_dtype": config.get("weight_dtype"), "quantization": config.get("quantization"),
            "cache_dtype": config.get("cache_dtype"), "mamba_ssm_cache_dtype": config.get("mamba_ssm_cache_dtype"),
            "attention_backend_requested": config.get("actual_attention_backend"),
            "context_limit": config.get("max_model_len"), "gpu_memory_utilization": config.get("gpu_memory_utilization"),
            "multimodal_limits": config.get("multimodal"),
            "started_utc": lifecycle["start_utc"], "ended_utc": lifecycle["end_utc"],
            "lifecycle": lifecycle, "resources": resources,
            "oom_detected": any(x in log_lower for x in ("out of memory", "cuda error: out of memory", "torch.cuda.outofmemoryerror")),
            "optimization_log_term_checks": term_checks,
            "responses": response_records,
            "raw_server_log_sha256": sha_file(log_path) if log_path.is_file() else None,
            "raw_probe_response_path": str(response_path.relative_to(ROOT).as_posix()),
            "probe_completed": bool(records and records[0].get("completed")) and all(r.get("completed") for r in records),
            "probe_json_schema_valid": bool(records and records[0].get("json_valid") and records[0].get("schema_valid")) and all(r.get("json_valid") and r.get("schema_valid") for r in records),
            "no_operational_memory_or_identity_writes": True,
        }
        runtime["stable_preflight"] = bool(
            lifecycle.get("loaded") and runtime["probe_completed"] and runtime["probe_json_schema_valid"]
            and not lifecycle.get("server_crashed_during_probe") and not runtime["oom_detected"]
            and lifecycle.get("fully_unloaded")
        )
        runtime_path.write_text(json.dumps(runtime, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"trial": args.trial_name, "loaded": lifecycle.get("loaded"),
                      "stable_preflight": runtime["stable_preflight"],
                      "oom": runtime["oom_detected"], "unloaded": lifecycle.get("fully_unloaded"),
                      "peak_vram_mib": resources.get("peak_global_gpu_memory_used_mib"),
                      "trial_record": str(runtime_path.relative_to(ROOT).as_posix())}, ensure_ascii=False))
    return 0 if runtime["stable_preflight"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
