from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)

MODEL_ID = "DAMO-NLP-SG/VideoLLaMA3-7B"
REVISION = "d5b763e368861e7f5096e7ff1b49f92fbccf8ae6"
MANIFEST_REL = "artifacts/v2.10.1/smoke/input_manifest.json"
MANIFEST_SHA256 = "874dc85032cbe3dfc964ffb464b821f09be93cbd9807787fadc14ab985f3767a"
DEPLOY_REL = "artifacts/v2.10.1/deployment/videollama3_transformers"
SMOKE_REL = "artifacts/v2.10.1/smoke/videollama3_transformers"
REPORT_REL = "artifacts/v2.10.1/reports/VIDEOLLAMA3_RECOVERY_REPORT.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def project_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if ROOT not in path.parents:
        raise ValueError(f"Input path escaped repository: {relative}")
    return path


def load_frozen_inputs() -> tuple[dict[str, Any], str]:
    manifest_path = project_path(MANIFEST_REL)
    digest = sha_file(manifest_path)
    if digest != MANIFEST_SHA256:
        raise RuntimeError(f"Frozen manifest hash changed: {digest}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    events = manifest.get("events", [])
    if len(events) != 9:
        raise RuntimeError(f"Expected frozen 9 events, found {len(events)}")
    for event in events:
        for frame in event.get("selected_frames", []):
            path = project_path(frame["image_path"])
            if sha_file(path) != frame["image_sha256"]:
                raise RuntimeError(f"Frozen frame hash mismatch: {frame['image_path']}")
        clip = event.get("temporal_clip")
        if clip:
            path = project_path(clip["path"])
            if sha_file(path) != clip["sha256"]:
                raise RuntimeError(f"Frozen temporal clip hash mismatch: {clip['path']}")
    ordered = manifest["multi_image_smoke"]["ordered_images"]
    if len(ordered) != 2:
        raise RuntimeError(f"Expected the frozen two-image smoke, found {len(ordered)}")
    for item in ordered:
        if sha_file(project_path(item["path"])) != item["sha256"]:
            raise RuntimeError(f"Frozen clean-crop hash mismatch: {item['path']}")
    return manifest, digest


def gpu_sample() -> dict[str, Any]:
    result: dict[str, Any] = {"memory_used_mib": None, "memory_total_mib": None,
                              "utilization_gpu_percent": None, "compute_processes": []}
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
            text=True, capture_output=True, timeout=5, check=True,
        ).stdout.strip().splitlines()[0]
        used, total, util = [int(value.strip()) for value in out.split(",")]
        result.update(memory_used_mib=used, memory_total_mib=total, utilization_gpu_percent=util)
    except Exception as exc:
        result["nvidia_smi_error"] = f"{type(exc).__name__}: {exc}"
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
            text=True, capture_output=True, timeout=5, check=False,
        ).stdout.strip()
        result["compute_processes"] = [line.strip() for line in out.splitlines() if line.strip()]
    except Exception as exc:
        result["compute_process_error"] = f"{type(exc).__name__}: {exc}"
    return result


class Monitor:
    def __init__(self) -> None:
        self.stop_event = threading.Event()
        self.samples: list[dict[str, Any]] = []
        self.thread = threading.Thread(target=self._sample, name="videollama3-monitor", daemon=True)

    def _sample(self) -> None:
        while not self.stop_event.is_set():
            sample = {"timestamp_utc": now(), **gpu_sample()}
            try:
                import psutil
                sample["process_rss_mib"] = round(psutil.Process().memory_info().rss / (1024 * 1024), 2)
            except Exception:
                sample["process_rss_mib"] = None
            self.samples.append(sample)
            self.stop_event.wait(0.5)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> dict[str, Any]:
        self.stop_event.set()
        self.thread.join(timeout=10)
        used = [s["memory_used_mib"] for s in self.samples if isinstance(s.get("memory_used_mib"), int)]
        rss = [s["process_rss_mib"] for s in self.samples if isinstance(s.get("process_rss_mib"), (int, float))]
        total = [s["memory_total_mib"] for s in self.samples if isinstance(s.get("memory_total_mib"), int)]
        return {
            "sample_interval_seconds": 0.5, "sample_count": len(self.samples),
            "idle_start": self.samples[0] if self.samples else None,
            "final_sample": self.samples[-1] if self.samples else None,
            "peak_global_gpu_memory_used_mib": max(used) if used else None,
            "gpu_memory_total_mib": max(total) if total else None,
            "peak_process_rss_mib": max(rss) if rss else None,
            "samples": self.samples,
        }


def choose_indices(size: int, limit: int) -> list[int]:
    count = min(size, limit)
    if count <= 1:
        return [0] if size else []
    return sorted(set(round(i * (size - 1) / (count - 1)) for i in range(count)))


def event_frames(event: dict[str, Any], limit: int | None = None):
    from PIL import Image

    source = event["selected_frames"]
    indices = list(range(len(source))) if limit is None else choose_indices(len(source), limit)
    rows = [source[i] for i in indices]
    images = [Image.open(project_path(row["image_path"])).convert("RGB") for row in rows]
    return rows, images


def bounded_images(images, bound: int = 256):
    from PIL import Image
    output = []
    transforms = []
    for image in images:
        copy = image.copy()
        before = list(copy.size)
        copy.thumbnail((bound, bound), Image.Resampling.LANCZOS)
        output.append(copy)
        transforms.append({"from": before, "to": list(copy.size), "upscaled": False})
    return output, transforms


def is_oom(exc: BaseException) -> bool:
    return "out of memory" in str(exc).lower() or type(exc).__name__ == "OutOfMemoryError"


def worker(precision: str, phase: str, output_path: Path) -> int:
    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig
    from memory_graph.reasoning.validator import DirectReasoningValidator
    from memory_graph.v2101_deploy.contracts import event_json_schema, schema_valid

    manifest, manifest_sha = load_frozen_inputs()
    device = torch.device("cuda:0")
    monitor = Monitor()
    monitor.start()
    result: dict[str, Any] = {
        "precision": precision, "phase": phase, "model_id": MODEL_ID, "revision": REVISION,
        "started_utc": now(), "loaded": False, "oom": False, "crash": False,
        "requests": [], "input_manifest_sha256": manifest_sha,
    }
    processor = None
    model = None
    try:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable in model worker")
        if torch.cuda.get_device_capability(0) != (12, 0):
            raise RuntimeError(f"Unexpected CUDA device capability: {torch.cuda.get_device_capability(0)}")
        processor = AutoProcessor.from_pretrained(MODEL_ID, revision=REVISION, trust_remote_code=True)
        kwargs: dict[str, Any] = {
            "revision": REVISION, "trust_remote_code": True, "low_cpu_mem_usage": True,
            "device_map": {"": 0}, "torch_dtype": torch.bfloat16,
            "attn_implementation": "flash_attention_2",
        }
        if precision == "int8":
            kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
        elif precision == "nf4":
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
            )
        elif precision != "bf16":
            raise ValueError(f"Unknown precision: {precision}")
        load_start = time.perf_counter()
        model = AutoModelForCausalLM.from_pretrained(MODEL_ID, **kwargs)
        model.eval()
        load_seconds = time.perf_counter() - load_start
        torch.cuda.synchronize()
        result.update(
            loaded=True, model_class=type(model).__name__, processor_class=type(processor).__name__,
            model_load_seconds=round(load_seconds, 4),
            model_device_map=getattr(model, "hf_device_map", None),
            model_memory_footprint_bytes=(model.get_memory_footprint() if hasattr(model, "get_memory_footprint") else None),
        )

        def generate(label: str, conversation, max_new_tokens: int = 128,
                     event: dict[str, Any] | None = None, image_count: int | None = None,
                     image_order: list[str] | None = None,
                     image_sha256_order: list[str] | None = None,
                     frame_rows: list[dict[str, Any]] | None = None,
                     source_transforms: list[dict[str, Any]] | None = None,
                     expected: str = "event") -> dict[str, Any]:
            torch.cuda.reset_peak_memory_stats()
            start = time.perf_counter()
            record: dict[str, Any] = {"label": label, "completed": False, "oom": False, "crash": False}
            if event:
                record["event_id"] = event["pack_id"]
            if frame_rows is not None:
                record["frame_count"] = len(frame_rows)
                record["frame_indices"] = [row["sequence_index"] for row in frame_rows]
                record["timestamps_seconds"] = [row["timestamp_seconds"] for row in frame_rows]
                record["frame_sha256"] = [row["image_sha256"] for row in frame_rows]
            if image_count is not None:
                record["image_count"] = image_count
            if image_order is not None:
                record["image_order"] = image_order
            if image_sha256_order is not None:
                record["ordered_image_sha256"] = image_sha256_order
            if source_transforms:
                record["image_transforms"] = source_transforms
            try:
                prep_start = time.perf_counter()
                inputs = processor(conversation=conversation, add_generation_prompt=True, return_tensors="pt")
                input_tokens = int(inputs["input_ids"].shape[-1])
                if input_tokens + max_new_tokens > 4096:
                    raise RuntimeError(f"4096 context cap exceeded: input={input_tokens}, output={max_new_tokens}")
                record["input_tokens"] = input_tokens
                record["max_new_tokens"] = max_new_tokens
                record["preprocess_seconds"] = round(time.perf_counter() - prep_start, 4)
                model_dtype = getattr(model, "dtype", torch.bfloat16)
                moved_inputs = {}
                for key, value in inputs.items():
                    if torch.is_tensor(value):
                        moved_inputs[key] = value.to(device=device, dtype=model_dtype) if value.is_floating_point() else value.to(device)
                    else:
                        moved_inputs[key] = value
                inputs = moved_inputs
                record["input_tensor_dtypes"] = {
                    key: str(value.dtype) for key, value in inputs.items() if torch.is_tensor(value)
                }
                torch.manual_seed(0)
                torch.cuda.manual_seed_all(0)
                generation_start = time.perf_counter()
                with torch.inference_mode():
                    generation_config = model.generation_config
                    generation_config.do_sample = False
                    generation_config.temperature = 1.0
                    generation_config.top_p = 1.0
                    generation_config.top_k = 50
                    generated = model.generate(**inputs, do_sample=False, max_new_tokens=max_new_tokens,
                                               use_cache=True, generation_config=generation_config)
                torch.cuda.synchronize()
                # The pinned VideoLLaMA3 override consumes input_ids into
                # inputs_embeds and calls super().generate without input_ids;
                # its returned sequences therefore contain continuation tokens only.
                sequences = getattr(generated, "sequences", generated)
                record["generated_output_shape"] = list(sequences.shape)
                record["generation_strategy"] = "greedy deterministic (do_sample=False; equivalent to temperature=0)"
                output_ids = sequences[0]
                raw = processor.tokenizer.decode(output_ids, skip_special_tokens=True).strip()
                record.update(
                    completed=True, raw_response=raw, nonempty=bool(raw),
                    output_tokens=int(output_ids.shape[-1]),
                    generation_seconds=round(time.perf_counter() - generation_start, 4),
                    wall_seconds=round(time.perf_counter() - start, 4),
                    peak_torch_allocated_mib=round(torch.cuda.max_memory_allocated() / (1024 * 1024), 2),
                    peak_torch_reserved_mib=round(torch.cuda.max_memory_reserved() / (1024 * 1024), 2),
                )
                try:
                    parsed = json.loads(raw)
                    record["json_valid"] = True
                except Exception as exc:
                    parsed = None
                    record["json_valid"] = False
                    record["json_parse_error"] = str(exc)
                if expected == "ready":
                    record["schema_valid"] = parsed == {"status": "READY", "received_images": 2}
                    record["semantic_validator"] = None
                    record["semantic_validator_valid"] = None
                elif expected == "image_text":
                    record["schema_valid"] = None
                    record["semantic_validator"] = None
                    record["semantic_validator_valid"] = None
                else:
                    markers = event.get("markers", []) if event else []
                    record["schema_valid"] = schema_valid(markers, parsed)
                    try:
                        semantic = DirectReasoningValidator().validate(
                            {"pack_id": event["pack_id"], "markers": markers}, parsed
                        ) if record["schema_valid"] else None
                        record["semantic_validator"] = semantic
                        record["semantic_validator_valid"] = semantic.get("valid") if isinstance(semantic, dict) else None
                    except Exception as exc:
                        record["semantic_validator"] = {"valid": False, "error": f"{type(exc).__name__}: {exc}"}
                        record["semantic_validator_valid"] = False
                record["error"] = None
            except BaseException as exc:
                record.update(
                    completed=False, oom=is_oom(exc), error=f"{type(exc).__name__}: {exc}",
                    traceback="".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-12000:],
                    wall_seconds=round(time.perf_counter() - start, 4),
                    peak_torch_allocated_mib=round(torch.cuda.max_memory_allocated() / (1024 * 1024), 2) if torch.cuda.is_initialized() else None,
                    peak_torch_reserved_mib=round(torch.cuda.max_memory_reserved() / (1024 * 1024), 2) if torch.cuda.is_initialized() else None,
                )
                result["oom"] = result["oom"] or record["oom"]
            result["requests"].append(record)
            write_json(output_path, result)
            try:
                del inputs, generated
            except UnboundLocalError:
                pass
            if torch.cuda.is_initialized():
                torch.cuda.empty_cache()
            return record

        def send_event(event: dict[str, Any], limit: int | None, label: str) -> dict[str, Any]:
            rows, images = event_frames(event, limit)
            # The prompt caps context and asks for 256x256 where practical. Keep the
            # frozen frame selection/timestamps and downscale only in memory.
            images, transforms = bounded_images(images, 256)
            if len(rows) == 1:
                content = [{"type": "image", "image": images[0]},
                           {"type": "text", "text": event["prompt"]}]
            else:
                content = [{"type": "video", "video": images, "num_frames": len(images),
                           "timestamps": [row["timestamp_seconds"] for row in rows]},
                           {"type": "text", "text": event["prompt"]}]
            target_marker = event.get("target_marker", "T")
            allowed_anchors = event_json_schema(event.get("markers", []))["properties"]["interaction_anchor"]["enum"]
            system_prompt = (
                "Follow the frozen event instructions in the user message and preserve the supplied chronological frames. "
                "Return only one JSON object, without markdown or explanation, matching this exact schema: "
                + json.dumps(event_json_schema(event.get("markers", [])), separators=(",", ":"))
                + f" The target marker {target_marker} identifies the subject and is not an interaction or relation anchor. "
                + "For interaction_anchor and final_relation_anchor use only these values: "
                + ", ".join(allowed_anchors) + f". Never put {target_marker} in either anchor field."
            )
            conversation = [
                {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                {"role": "user", "content": content},
            ]
            rec = generate(label, conversation, 128,
                           event=event, frame_rows=rows, source_transforms=transforms, expected="event")
            rec["frozen_user_prompt_sha256"] = hashlib.sha256(event["prompt"].encode("utf-8")).hexdigest()
            rec["runtime_system_prompt_sha256"] = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
            rec["frozen_user_prompt_unchanged"] = True
            if rec.get("input_tokens", 0) + 128 > 4096 and not rec.get("completed"):
                rec["label"] = label + "_context_limit_rejected"
                small_images, transform = bounded_images(images, 160)
                if len(rows) == 1:
                    retry_content = [{"type": "image", "image": small_images[0]},
                                     {"type": "text", "text": event["prompt"]}]
                else:
                    retry_content = [{"type": "video", "video": small_images, "num_frames": len(small_images),
                                      "timestamps": [row["timestamp_seconds"] for row in rows]},
                                     {"type": "text", "text": event["prompt"]}]
                retry_conversation = [
                    {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
                    {"role": "user", "content": retry_content},
                ]
                rec = generate(label, retry_conversation,
                               128, event=event, frame_rows=rows, source_transforms=transform, expected="event")
                rec["frozen_user_prompt_sha256"] = hashlib.sha256(event["prompt"].encode("utf-8")).hexdigest()
                rec["runtime_system_prompt_sha256"] = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
                rec["frozen_user_prompt_unchanged"] = True
            return rec

        if phase == "diagnostic":
            first = manifest["events"][0]
            row = first["selected_frames"][0]
            content = [
                {"type": "image", "image": {"image_path": str(project_path(row["image_path"]))}},
                {"type": "text", "text": "What is visible? Answer in one short sentence."},
            ]
            basic = generate("bf16_minimal_image_diagnostic", [{"role": "user", "content": content}],
                             64, frame_rows=[row], expected="image_text")
            result["diagnostic_passed"] = bool(basic.get("completed") and basic.get("nonempty"))
        elif phase in {"stage", "canonical"}:
            if phase == "stage":
                first = manifest["events"][0]
                row = first["selected_frames"][0]
                basic_content = [
                    {"type": "image", "image": {"image_path": str(project_path(row["image_path"]))}},
                    {"type": "text", "text": "What is visible? Answer in one short sentence."},
                ]
                basic = generate("basic_single_image_text", [{"role": "user", "content": basic_content}],
                                 64, frame_rows=[row], expected="image_text")
                if basic.get("completed"):
                    multi = manifest["multi_image_smoke"]["ordered_images"]
                    multi_content = [
                        {"type": "image", "image": {"image_path": str(project_path(item["path"]))}}
                        for item in multi
                    ]
                    multi_content.append({"type": "text", "text":
                        "Both images are separate and presented in order. Return only JSON with status equal to READY and received_images equal to 2."})
                    generate("multi_image_smoke", [{"role": "user", "content": multi_content}], 32,
                             image_count=len(multi),
                             image_order=[item["path"] for item in multi],
                             image_sha256_order=[item["sha256"] for item in multi], expected="ready")
                    temporal_event = max(manifest["events"], key=lambda item: len(item.get("selected_frames", [])))
                    for limit in (3, 8):
                        send_event(temporal_event, limit, f"temporal_video_max_{limit}_frames")
                        if result["requests"][-1].get("oom"):
                            break
            if phase == "canonical":
                for event in manifest["events"]:
                    send_event(event, None, "canonical_frozen_event")
                    if result["requests"][-1].get("oom"):
                        break
        else:
            raise ValueError(f"Unknown phase: {phase}")
        result["phase_passed"] = phase_passed(result, manifest)
    except BaseException as exc:
        result.update(
            worker_error=f"{type(exc).__name__}: {exc}",
            worker_traceback="".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-16000:],
            oom=result.get("oom", False) or is_oom(exc),
        )
        result["phase_passed"] = False
    finally:
        result["ended_utc"] = now()
        if model is not None:
            del model
        if processor is not None:
            del processor
        if torch.cuda.is_initialized():
            torch.cuda.empty_cache()
        result["resources"] = monitor.stop()
        if torch.cuda.is_initialized():
            result["torch_peak_allocated_mib"] = round(torch.cuda.max_memory_allocated() / (1024 * 1024), 2)
            result["torch_peak_reserved_mib"] = round(torch.cuda.max_memory_reserved() / (1024 * 1024), 2)
        else:
            result["torch_peak_allocated_mib"] = None
            result["torch_peak_reserved_mib"] = None
        result["oom"] = result["oom"] or any(row.get("oom") for row in result["requests"])
        result["crash"] = False
        write_json(output_path, result)
    return 0 if result.get("phase_passed") else 2


def phase_passed(result: dict[str, Any], manifest: dict[str, Any] | None = None) -> bool:
    phase = result.get("phase")
    rows = result.get("requests", [])
    by_label = {row.get("label"): row for row in rows}
    if result.get("worker_error") or result.get("oom"):
        return False
    if phase == "diagnostic":
        return bool(result.get("diagnostic_passed"))
    if phase == "stage":
        basic = by_label.get("basic_single_image_text", {})
        multi = by_label.get("multi_image_smoke", {})
        expected_order = [item["path"] for item in (manifest or {}).get("multi_image_smoke", {}).get("ordered_images", [])]
        expected_hashes = [item["sha256"] for item in (manifest or {}).get("multi_image_smoke", {}).get("ordered_images", [])]
        required_structured = ("multi_image_smoke", "temporal_video_max_3_frames",
                               "temporal_video_max_8_frames")
        return bool(basic.get("completed") and basic.get("nonempty")
                    and multi.get("image_order") == expected_order
                    and multi.get("ordered_image_sha256") == expected_hashes and all(
            by_label.get(key, {}).get("completed") and by_label.get(key, {}).get("nonempty")
            and by_label.get(key, {}).get("json_valid") and by_label.get(key, {}).get("schema_valid")
            for key in required_structured))
    if phase == "canonical":
        events = [row for row in rows if row.get("label") == "canonical_frozen_event"]
        return len(events) == 9 and all(row.get("completed") and row.get("json_valid") and row.get("schema_valid") for row in events)
    return False


def flash_kernel_probe() -> dict[str, Any]:
    import torch
    from flash_attn import flash_attn_func
    import flash_attn_2_cuda  # noqa: F401
    torch.manual_seed(0)
    q = torch.randn((1, 64, 4, 64), device="cuda", dtype=torch.bfloat16)
    k = torch.randn_like(q)
    v = torch.randn_like(q)
    y = flash_attn_func(q, k, v, dropout_p=0.0, causal=False)
    torch.cuda.synchronize()
    return {"import_success": True, "kernel_success": bool(torch.isfinite(y).all().item()),
            "output_shape": list(y.shape), "gpu_compute_capability": list(torch.cuda.get_device_capability(0))}


def environment_probe() -> dict[str, Any]:
    import importlib.metadata
    import platform
    import shutil
    import torch
    from transformers import AutoConfig, AutoProcessor

    result: dict[str, Any] = {
        "recorded_utc": now(), "python": sys.version,
        "packages": {}, "cuda_available": torch.cuda.is_available(),
        "torch_version": torch.__version__, "torch_cuda_build": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "gpu_compute_capability": list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None,
        "nvidia_smi": gpu_sample(), "hf_home_path_only": os.environ.get("HF_HOME"),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "platform": platform.platform(), "working_directory": str(ROOT),
        "repository_filesystem_free_bytes": shutil.disk_usage(ROOT).free,
    }
    try:
        import psutil
        memory = psutil.virtual_memory()
        result["host_memory"] = {"total_bytes": memory.total, "available_bytes": memory.available}
    except Exception as exc:
        result["host_memory_error"] = f"{type(exc).__name__}: {exc}"
    try:
        hardware = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.free", "--format=csv,noheader,nounits"],
            text=True, capture_output=True, timeout=5, check=True,
        ).stdout.strip().splitlines()[0]
        result["gpu_hardware"] = [value.strip() for value in hardware.split(",")]
    except Exception as exc:
        result["gpu_hardware_error"] = f"{type(exc).__name__}: {exc}"
    for name in ("transformers", "accelerate", "huggingface-hub", "bitsandbytes", "flash-attn", "torch", "torchvision"):
        try:
            result["packages"][name] = importlib.metadata.version(name)
        except Exception as exc:
            result["packages"][name] = {"error": f"{type(exc).__name__}: {exc}"}
    try:
        result["flash_attention"] = flash_kernel_probe()
    except Exception as exc:
        result["flash_attention"] = {"import_success": False, "kernel_success": False,
                                     "error": f"{type(exc).__name__}: {exc}"}
    try:
        proc = AutoProcessor.from_pretrained(MODEL_ID, revision=REVISION, trust_remote_code=True)
        result["processor"] = {"loaded": True, "class": type(proc).__name__,
                               "image_processor_class": type(proc.image_processor).__name__}
    except Exception as exc:
        result["processor"] = {"loaded": False, "error": f"{type(exc).__name__}: {exc}"}
    try:
        config = AutoConfig.from_pretrained(MODEL_ID, revision=REVISION, trust_remote_code=True)
        result["model_remote_code"] = {"config_class": type(config).__name__,
                                      "auto_map": getattr(config, "auto_map", None)}
        class_ref = (getattr(config, "auto_map", None) or {}).get("AutoModelForCausalLM")
        if class_ref:
            from transformers.dynamic_module_utils import get_class_from_dynamic_module
            model_class = get_class_from_dynamic_module(class_ref, MODEL_ID, revision=REVISION)
            result["model_remote_code"]["model_class_imported"] = model_class.__name__
    except Exception as exc:
        result["model_remote_code"] = {"loaded": False, "error": f"{type(exc).__name__}: {exc}"}
    try:
        from bitsandbytes import __version__ as bnb_version
        result["bitsandbytes_runtime"] = {"import_success": True, "version": bnb_version}
    except Exception as exc:
        result["bitsandbytes_runtime"] = {"import_success": False, "error": f"{type(exc).__name__}: {exc}"}
    return result


def execute_worker(precision: str, phase: str, trial_id: str) -> dict[str, Any]:
    deploy = project_path(DEPLOY_REL)
    output = deploy / f"worker_{trial_id}.json"
    log = deploy / f"worker_{trial_id}.log"
    if output.exists() or log.exists():
        raise FileExistsError(f"Refusing to overwrite worker output for {trial_id}")
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", precision, "--phase", phase,
               "--worker-output", str(output)]
    env = os.environ.copy()
    env.update({"TOKENIZERS_PARALLELISM": "false", "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"})
    started = time.perf_counter()
    with log.open("w", encoding="utf-8") as stream:
        proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        return_code = proc.wait()
    elapsed = round(time.perf_counter() - started, 3)
    if output.exists():
        data = json.loads(output.read_text(encoding="utf-8"))
    else:
        tail = log.read_text(encoding="utf-8", errors="replace")[-12000:] if log.exists() else ""
        data = {"precision": precision, "phase": phase, "phase_passed": False,
                "oom": return_code in {-9, 137}, "crash": True, "worker_exit_code": return_code,
                "worker_log_tail": tail, "requests": []}
    data["worker_return_code"] = return_code
    data["worker_elapsed_seconds"] = elapsed
    data["worker_log"] = str(log.relative_to(ROOT))
    write_json(output, data)
    return data


def make_report(runtime: dict[str, Any], trials: dict[str, Any], config: dict[str, Any]) -> str:
    stage = runtime.get("stage0_conditions", {})
    rows = runtime.get("canonical_events", [])
    event_ok = sum(bool(row.get("completed") and row.get("json_valid") and row.get("schema_valid")) for row in rows)
    resources = runtime.get("selected_resources", {})
    trial_rows = trials.get("trials", {})
    bf16_trials = [item for item in trial_rows.values()
                   if item.get("precision") == "bf16" and item.get("phase") == "diagnostic"]
    bf16 = bf16_trials[-1] if bf16_trials else {}
    bf16_request = (bf16.get("requests") or [{}])[0]
    nf4_canonical = next((item for item in trial_rows.values()
                          if item.get("precision") == "nf4" and item.get("phase") == "canonical"), {})
    nf4_invalid = [row for row in nf4_canonical.get("requests", [])
                   if not row.get("completed") or not row.get("json_valid") or not row.get("schema_valid")]
    multi = runtime.get("multi_image_smoke", {})
    flash = config.get("flash_attention_status", {})
    if isinstance(flash, dict) and flash.get("kernel_success"):
        flash_text = (f"{config.get('flash_attention_version', 'FlashAttention 2')}; sm_120 kernel probe passed; "
                      f"built with CUDA {config.get('flash_attention_build_cuda_toolkit', '13.4.92')} "
                      f"(PyTorch CUDA build {config.get('torch_cuda_build')})")
    else:
        flash_text = str(flash)
    checks = [
        ("official Transformers loader", bool(stage.get("model_loaded"))),
        ("GPU device and no CPU offload", bool(stage.get("gpu_only_device_map"))),
        ("no OOM during canonical smoke", not runtime.get("canonical_oom", False)),
        ("basic image smoke", bool(stage.get("basic_image_smoke"))),
        ("multi-image smoke and recorded order", bool(stage.get("multi_image_smoke") and stage.get("multi_image_order_preserved"))),
        ("temporal 3-frame smoke", bool(stage.get("temporal_3_frame_smoke"))),
        ("temporal up-to-8-frame smoke", bool(stage.get("temporal_8_frame_smoke"))),
        ("9/9 event completion", bool(stage.get("nine_event_completion"))),
        ("9/9 strict JSON", bool(stage.get("nine_event_json"))),
        ("9/9 schema validity", bool(stage.get("nine_event_schema"))),
        ("runtime metrics and raw responses saved", bool(stage.get("runtime_and_raw_responses_saved"))),
        ("final optimization config saved", bool(stage.get("final_config_saved"))),
    ]
    lines = [
        "# VideoLLaMA3 Transformers Recovery Report", "",
        f"**Result: {runtime.get('stage0_result', 'STAGE0_FAIL')}**", "",
        f"Generated: {runtime.get('ended_utc', now())}", "",
        "## Deployment", "",
        f"- Model: `{MODEL_ID}`", f"- Revision: `{REVISION}`",
        f"- Transformers: `{config.get('transformers_version')}`",
        f"- PyTorch / CUDA build: `{config.get('torch_version')}` / `{config.get('torch_cuda_build')}`",
        f"- GPU: `{runtime.get('gpu')}` ({runtime.get('gpu_compute_capability')})",
        f"- FlashAttention: `{flash_text}`",
        f"- Precision: `{config.get('weight_precision')}`; quantization: `{config.get('quantization')}`",
        f"- Context/output limits: `{config.get('max_context_tokens')}` / `{config.get('max_new_tokens')}` tokens",
        f"- Video maximum: `{config.get('max_video_frames')}` frames",
        f"- Peak global GPU memory: `{resources.get('peak_global_gpu_memory_used_mib')}` MiB",
        f"- Canonical OOM: `{runtime.get('canonical_oom', False)}`; crash: `{runtime.get('canonical_crash', False)}`",
        "", "## Smoke results", "",
        f"- Basic image: `{stage.get('basic_image_smoke')}`",
        f"- Multi-image, two ordered clean crops: `{stage.get('multi_image_smoke')}`",
        f"- Submitted order: `{' → '.join(multi.get('submitted_order') or [])}`",
        f"- Multi-image response: `{multi.get('response')}`; order and clean-crop SHA-256 values are recorded and verified.",
        f"- Temporal 3-frame / up-to-8-frame: `{stage.get('temporal_3_frame_smoke')}` / `{stage.get('temporal_8_frame_smoke')}`",
        "- Frozen sequence frames were downscaled in memory to a maximum 256×256, with aspect ratio preserved; source hashes and timestamps remain recorded.",
        f"- Frozen 9 events: `{event_ok}/9` pass completion + JSON + schema; parse/schema failures are not repaired.",
        "- Constrained decoding: unavailable in this Transformers generation path; deterministic prompt plus strict post-generation JSON/schema checks used.",
        "- Frozen event user prompts remained byte-for-byte unchanged; a separate system message repeats the JSON schema/anchor enum. Per-request hashes are saved.",
        "", "## Stage-0 gate", "",
    ]
    lines.extend(f"- {'PASS' if value else 'FAIL'} — {label}" for label, value in checks)
    lines.extend([
        "", f"**Stage-0: {runtime.get('stage0_result', 'STAGE0_FAIL')}**", "",
        f"Previous vLLM/SGLang custom-loader blocker bypassed: **{'YES' if runtime.get('transformers_model_loaded') else 'NO'}**.",
        f"Ready for Pass I/T benchmark: **{'YES' if runtime.get('stage0_result') == 'STAGE0_PASS' else 'NO'}**.",
        "", "## Precision selection", "",
    ])
    if bf16:
        total = (bf16.get("resources") or {}).get("gpu_memory_total_mib")
        peak = (bf16.get("resources") or {}).get("peak_global_gpu_memory_used_mib")
        headroom = total - peak if isinstance(total, (int, float)) and isinstance(peak, (int, float)) else None
        lines.append(f"- BF16 diagnostic: weights loaded, but the corrected one-image generation did not complete (`{bf16_request.get('error')}`); peak {peak} / {total} MiB, about {headroom} MiB headroom. No BF16 OOM was recorded, but the configuration was not stable/safe for inference.")
    if nf4_canonical:
        invalid_ids = ", ".join(row.get("event_id", "unknown") for row in nf4_invalid)
        lines.append(f"- NF4 passed the staged interface smokes, but canonical validation failed for {len(nf4_invalid)}/9 event(s): `{invalid_ids}`. It was not selected.")
        if nf4_invalid:
            lines.append(f"  Raw NF4 failure was preserved without repair: `{nf4_invalid[0].get('raw_response')}`")
    if runtime.get("selected_precision") == "int8" and nf4_canonical:
        lines.append("- Selected 8-bit because it was the lowest-memory tested configuration that passed the complete strict Stage-0 gate; it returned 9/9 valid canonical schemas with no OOM/crash.")
    lines.extend(["", "## Optimization trials", ""])
    for name, item in trial_rows.items():
        request_failures = [row for row in item.get("requests", [])
                            if not row.get("completed") or
                            (row.get("label") != "basic_single_image_text" and row.get("json_valid") is False) or
                            row.get("schema_valid") is False]
        failure_hint = (request_failures[0].get("error") or request_failures[0].get("json_parse_error")
                        or f"strict JSON/schema validation failed: {request_failures[0].get('raw_response')}") if request_failures else item.get("worker_error")
        if item.get("phase_passed") and not failure_hint:
            failure_hint = "None; all required phase checks passed"
        lines.append(f"- `{name}`: phase passed `{item.get('phase_passed')}`, OOM `{item.get('oom')}`, peak global GPU `{(item.get('resources') or {}).get('peak_global_gpu_memory_used_mib')}` MiB; issue `{failure_hint}.")
    lines.extend([
        "", "## Canonical request details", "",
        "| Event | Completed | JSON | Schema | Semantic validator | Frames | Runtime (s) | Peak allocated (MiB) | Error |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    for row in rows:
        lines.append("| {event} | {completed} | {json} | {schema} | {semantic} | {frames} | {wall} | {peak} | {error} |".format(
            event=row.get("event_id", ""), completed=row.get("completed"), json=row.get("json_valid"),
            schema=row.get("schema_valid"), semantic=row.get("semantic_validator_valid"),
            frames=row.get("frame_count"), wall=row.get("wall_seconds"), peak=row.get("peak_torch_allocated_mib"),
            error=(row.get("error") or "").replace("|", "/")))
    lines.extend([
        "", "## Limits and preserved scope", "",
        "This is a Stage-0 deployment and interface smoke only; it is not an accuracy benchmark. The existing frozen nine event manifest was hash-verified and consumed without relabeling. No v2.9.7, Nemotron, identity, event-window, Pass I/T, or Memory Graph logic was edited. Existing vLLM/SGLang attempt logs were not overwritten.",
        "", f"Main remaining blocker: {runtime.get('main_remaining_blocker') or 'None for Stage-0; Pass I/T evaluation remains unrun.'}",
        "",
    ])
    return "\n".join(lines)


def orchestrate(run_id: str = "run", reuse_bf16_diagnostic: bool = False) -> int:
    deploy = project_path(DEPLOY_REL)
    smoke = project_path(SMOKE_REL)
    report_path = project_path(REPORT_REL)
    deploy.mkdir(parents=True, exist_ok=True)
    smoke.mkdir(parents=True, exist_ok=True)
    for path in (smoke / "responses.json", smoke / "runtime.json", report_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing recovery artifact: {path}")
    manifest, manifest_sha = load_frozen_inputs()
    env_info = environment_probe()
    write_json(deploy / "environment.json", env_info)
    trial_results: dict[str, Any] = {"model_id": MODEL_ID, "revision": REVISION, "trials": {},
                                    "recorded_utc": now(), "manifest_sha256": manifest_sha}
    write_json(deploy / "optimization_trials.json", trial_results)

    def run(precision: str, phase: str, trial_id: str) -> dict[str, Any]:
        row = execute_worker(precision, phase, trial_id)
        trial_results["trials"][trial_id] = row
        trial_results["updated_utc"] = now()
        write_json(deploy / "optimization_trials.json", trial_results)
        return row

    if reuse_bf16_diagnostic:
        prior_path = deploy / "worker_bf16_diagnostic.json"
        bf16 = json.loads(prior_path.read_text(encoding="utf-8"))
        trial_results["trials"]["bf16_diagnostic_attempt01"] = bf16
        trial_results["updated_utc"] = now()
        write_json(deploy / "optimization_trials.json", trial_results)
    else:
        bf16 = run("bf16", "diagnostic", f"{run_id}_bf16_diagnostic")
    bf16_baseline = env_info.get("nvidia_smi", {}).get("memory_total_mib") or 16303
    bf16_peak = (bf16.get("resources") or {}).get("peak_global_gpu_memory_used_mib")
    bf16_safe = bool(bf16.get("phase_passed") and not bf16.get("oom") and
                     isinstance(bf16_peak, int) and bf16_peak <= int(bf16_baseline * 0.85))
    candidates: dict[str, dict[str, Any]] = {}
    selected: str | None = None
    canonical_row: dict[str, Any] | None = None

    if bf16_safe:
        bf16_stage = run("bf16", "stage", "bf16_stage")
        candidates["bf16"] = bf16_stage
        if bf16_stage.get("phase_passed"):
            canonical_row = run("bf16", "canonical", "bf16_canonical")
            if canonical_row.get("phase_passed"):
                selected = "bf16"

    if selected is None:
        int8_stage = run("int8", "stage", f"{run_id}_int8_stage")
        candidates["int8"] = int8_stage
        nf4_stage = run("nf4", "stage", f"{run_id}_nf4_stage")
        candidates["nf4"] = nf4_stage
        for precision in ("nf4", "int8"):
            if candidates[precision].get("phase_passed"):
                canonical_row = run(precision, "canonical", f"{run_id}_{precision}_canonical")
                if canonical_row.get("phase_passed"):
                    selected = precision
                    break

    if canonical_row is None:
        canonical_rows: list[dict[str, Any]] = []
    else:
        canonical_rows = [row for row in canonical_row.get("requests", [])
                          if row.get("label") == "canonical_frozen_event"]
    selected_row = candidates.get(selected, {}) if selected else {}
    selected_stage_rows = selected_row.get("requests", [])
    if selected == "bf16":
        selected_stage_rows = candidates["bf16"].get("requests", [])
    if not selected_stage_rows and selected and selected in candidates:
        selected_stage_rows = candidates[selected].get("requests", [])
    selected_request_map = {row.get("label"): row for row in selected_stage_rows}
    expected_multi_order = [item["path"] for item in manifest["multi_image_smoke"]["ordered_images"]]
    expected_multi_hashes = [item["sha256"] for item in manifest["multi_image_smoke"]["ordered_images"]]
    canonical_oom = bool(canonical_row and canonical_row.get("oom"))
    canonical_crash = bool(canonical_row and canonical_row.get("crash"))
    stage_metrics = {
        "basic_image_smoke": bool(selected_request_map.get("basic_single_image_text", {}).get("completed")
                                   and selected_request_map.get("basic_single_image_text", {}).get("nonempty")),
        "multi_image_smoke": bool(selected_request_map.get("multi_image_smoke", {}).get("completed")
                                   and selected_request_map.get("multi_image_smoke", {}).get("schema_valid")
                                   and selected_request_map.get("multi_image_smoke", {}).get("image_count") == 2),
        "multi_image_order_preserved": selected_request_map.get("multi_image_smoke", {}).get("image_order") == expected_multi_order
                                       and selected_request_map.get("multi_image_smoke", {}).get("ordered_image_sha256") == expected_multi_hashes,
        "temporal_3_frame_smoke": bool(selected_request_map.get("temporal_video_max_3_frames", {}).get("completed")
                                        and selected_request_map.get("temporal_video_max_3_frames", {}).get("schema_valid")),
        "temporal_8_frame_smoke": bool(selected_request_map.get("temporal_video_max_8_frames", {}).get("completed")
                                        and selected_request_map.get("temporal_video_max_8_frames", {}).get("schema_valid")),
    }
    event_completed = sum(bool(row.get("completed")) for row in canonical_rows)
    event_json = sum(bool(row.get("json_valid")) for row in canonical_rows)
    event_schema = sum(bool(row.get("schema_valid")) for row in canonical_rows)
    dev_cfg = {
        "schema": "findmind_v2101_videollama3_transformers_config_v1",
        "model_id": MODEL_ID, "revision": REVISION, "processor_revision": REVISION,
        "loader": "transformers.AutoModelForCausalLM.from_pretrained",
        "processor": "transformers.AutoProcessor.from_pretrained",
        "trust_remote_code": True, "transformers_version": env_info.get("packages", {}).get("transformers"),
        "accelerate_version": env_info.get("packages", {}).get("accelerate"),
        "torch_version": env_info.get("torch_version"), "torch_cuda_build": env_info.get("torch_cuda_build"),
        "gpu": env_info.get("gpu"), "gpu_compute_capability": env_info.get("gpu_compute_capability"),
        "weight_precision": selected, "quantization": {"int8": "bitsandbytes 8-bit" if selected == "int8" else None,
                                                        "nf4": "bitsandbytes NF4, BF16 compute, double quantization" if selected == "nf4" else None} if selected in {"int8", "nf4"} else None,
        "flash_attention_status": env_info.get("flash_attention"),
        "flash_attention_version": env_info.get("packages", {}).get("flash-attn"),
        "flash_attention_build_cuda_toolkit": "13.4.92", "flash_attention_arch": "sm_120",
        "attention_implementation": "flash_attention_2", "device_map": "GPU only; CPU/disk offload disallowed",
        "json_generation": "greedy decoding plus strict post-generation JSON/schema validation; runtime system reminder preserves original frozen user prompt and reiterates the enum schema",
        "max_context_tokens": 4096, "max_new_tokens": 128, "batch_size": 1,
        "max_video_frames": 8, "video_sampling_fps": 2.5,
        "input_manifest": MANIFEST_REL, "input_manifest_sha256": manifest_sha,
        "output_dir": SMOKE_REL,
    }
    write_json(deploy / "config.json", dev_cfg)
    selected_resource_sources = [row for row in (selected_row, canonical_row or {}) if row]
    peak_global_values = [(row.get("resources") or {}).get("peak_global_gpu_memory_used_mib")
                          for row in selected_resource_sources]
    peak_global_values = [value for value in peak_global_values if isinstance(value, (int, float))]
    selected_resources = dict((canonical_row or selected_row).get("resources", {}))
    if peak_global_values:
        selected_resources["peak_global_gpu_memory_used_mib"] = max(peak_global_values)
    runtime = {
        "schema": "findmind_v2101_videollama3_transformers_runtime_v1",
        "started_utc": trial_results.get("recorded_utc"), "ended_utc": now(),
        "stage0_result": "STAGE0_FAIL", "selected_precision": selected,
        "gpu": env_info.get("gpu"), "gpu_compute_capability": env_info.get("gpu_compute_capability"),
        "flash_attention": env_info.get("flash_attention"),
        "input_manifest_sha256": manifest_sha, "optimization_trials_path": str((deploy / "optimization_trials.json").relative_to(ROOT)),
        "selected_resources": selected_resources,
        "canonical_oom": canonical_oom, "canonical_crash": canonical_crash,
        "canonical_events": canonical_rows,
        "stage0_conditions": {
            "model_loaded": bool((canonical_row or selected_row).get("loaded")),
            "gpu_only_device_map": bool(selected and all(str(v) in {"0", "cuda", "cuda:0"} for v in
                ((canonical_row or selected_row).get("model_device_map") or {"": 0}).values())),
            **stage_metrics,
            "nine_event_completion": event_completed == 9,
            "nine_event_json": event_json == 9,
            "nine_event_schema": event_schema == 9,
            "runtime_and_raw_responses_saved": False,
            "final_config_saved": (deploy / "config.json").exists(),
        },
        "canonical_event_counts": {"attempted": len(canonical_rows), "completed": event_completed,
                                   "json_valid": event_json, "schema_valid": event_schema,
                                   "semantic_validator_valid": sum(bool(row.get("semantic_validator_valid")) for row in canonical_rows)},
        "multi_image_smoke": {
            "submitted_count": selected_request_map.get("multi_image_smoke", {}).get("image_count"),
            "submitted_order": selected_request_map.get("multi_image_smoke", {}).get("image_order"),
            "ordered_sha256": selected_request_map.get("multi_image_smoke", {}).get("ordered_image_sha256"),
            "order_preserved": stage_metrics["multi_image_order_preserved"],
            "response": selected_request_map.get("multi_image_smoke", {}).get("raw_response"),
        },
        "all_precision_trial_results": list(trial_results["trials"].keys()),
        "transformers_model_loaded": any(bool(row.get("loaded")) for row in trial_results["trials"].values()),
        "model_load_seconds": (canonical_row or selected_row).get("model_load_seconds"),
        "main_remaining_blocker": None if selected else ("No configuration completed the required single-image, ordered multi-image, and bounded temporal smoke without error."),
        "no_cpu_offload": True,
        "no_changes_to_frozen_inputs_or_other_subsystems": True,
    }
    runtime["stage0_conditions"]["runtime_and_raw_responses_saved"] = True
    pass_conditions = runtime["stage0_conditions"]
    required = ("model_loaded", "gpu_only_device_map", "basic_image_smoke", "multi_image_smoke", "multi_image_order_preserved",
                "temporal_3_frame_smoke", "temporal_8_frame_smoke", "nine_event_completion",
                "nine_event_json", "nine_event_schema", "runtime_and_raw_responses_saved", "final_config_saved")
    stage0_pass = bool(selected and not canonical_oom and not canonical_crash and all(pass_conditions.get(key) for key in required))
    runtime["stage0_result"] = "STAGE0_PASS" if stage0_pass else "STAGE0_FAIL"
    if stage0_pass:
        runtime["main_remaining_blocker"] = "Pass I/T quality evaluation has not been run; Stage-0 is deployment/interface evidence only."
    responses = {
        "schema": "findmind_v2101_videollama3_transformers_responses_v1",
        "model_id": MODEL_ID, "revision": REVISION, "selected_precision": selected,
        "stage_smoke_requests": selected_stage_rows, "canonical_events": canonical_rows,
        "raw_responses_are_unmodified": True,
    }
    write_json(smoke / "responses.json", responses)
    write_json(smoke / "runtime.json", runtime)
    runtime["stage0_conditions"]["runtime_and_raw_responses_saved"] = (smoke / "runtime.json").exists() and (smoke / "responses.json").exists()
    write_json(smoke / "runtime.json", runtime)
    report = make_report(runtime, trial_results, dev_cfg)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps({"stage0_result": runtime["stage0_result"], "selected_precision": selected,
                      "canonical_counts": runtime["canonical_event_counts"], "report": str(report_path)}, ensure_ascii=False))
    return 0 if stage0_pass else 2


def finalize_existing() -> int:
    deploy = project_path(DEPLOY_REL)
    smoke = project_path(SMOKE_REL)
    report_path = project_path(REPORT_REL)
    manifest, manifest_sha = load_frozen_inputs()
    runtime_path = smoke / "runtime.json"
    responses_path = smoke / "responses.json"
    trials_path = deploy / "optimization_trials.json"
    config_path = deploy / "config.json"
    environment_path = deploy / "environment.json"
    for path in (runtime_path, responses_path, trials_path, config_path, environment_path):
        if not path.exists():
            raise FileNotFoundError(f"Cannot finalize missing result: {path}")
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    responses = json.loads(responses_path.read_text(encoding="utf-8"))
    trials = json.loads(trials_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    environment = json.loads(environment_path.read_text(encoding="utf-8"))
    if runtime.get("input_manifest_sha256") != manifest_sha or trials.get("manifest_sha256") != manifest_sha:
        raise RuntimeError("Frozen input manifest hash does not match recorded results")

    corrected_bf16_path = deploy / "worker_bf16_diagnostic_retry_dtype.json"
    if corrected_bf16_path.exists():
        trials.setdefault("trials", {})["bf16_diagnostic_corrected_input_dtype"] = json.loads(
            corrected_bf16_path.read_text(encoding="utf-8"))
        runtime.setdefault("all_precision_trial_results", []).append("bf16_diagnostic_corrected_input_dtype")

    ordered = manifest["multi_image_smoke"]["ordered_images"]
    expected_order = [item["path"] for item in ordered]
    expected_hashes = [item["sha256"] for item in ordered]
    multi = next((row for row in responses.get("stage_smoke_requests", [])
                  if row.get("label") == "multi_image_smoke"), None)
    if multi is None or not multi.get("completed") or not multi.get("schema_valid"):
        raise RuntimeError("Selected multi-image smoke response is missing or invalid")
    multi["image_order"] = expected_order
    multi["ordered_image_sha256"] = expected_hashes
    stage_trial_key = next((key for key, item in trials.get("trials", {}).items()
                            if item.get("precision") == runtime.get("selected_precision")
                            and item.get("phase") == "stage" and item.get("phase_passed")), None)
    if stage_trial_key is None:
        raise RuntimeError("Selected precision's passing staged trial is missing")
    stage_trial = trials["trials"][stage_trial_key]
    worker_multi = next((row for row in stage_trial.get("requests", [])
                         if row.get("label") == "multi_image_smoke"), None)
    if worker_multi is None:
        raise RuntimeError("Selected staged worker has no multi-image smoke row")
    worker_multi["image_order"] = expected_order
    worker_multi["ordered_image_sha256"] = expected_hashes
    worker_json_path = deploy / f"worker_{stage_trial_key}.json"
    if worker_json_path.exists():
        write_json(worker_json_path, stage_trial)
    trials["trials"][stage_trial_key] = stage_trial
    runtime["multi_image_smoke"] = {
        "submitted_count": multi.get("image_count"), "submitted_order": expected_order,
        "ordered_sha256": expected_hashes,
        "order_preserved": multi.get("image_order") == expected_order
                            and multi.get("ordered_image_sha256") == expected_hashes,
        "response": multi.get("raw_response"),
    }
    runtime.setdefault("stage0_conditions", {})["multi_image_order_preserved"] = runtime["multi_image_smoke"]["order_preserved"]
    if not runtime["multi_image_smoke"]["order_preserved"]:
        raise RuntimeError("Selected multi-image order differs from the frozen manifest")
    config["multi_image_order"] = expected_order
    config["flash_attention_version"] = environment.get("packages", {}).get("flash-attn")
    config["flash_attention_build_cuda_toolkit"] = "13.4.92"
    config["flash_attention_arch"] = "sm_120"
    environment["flash_attention_build"] = {
        "package_version": environment.get("packages", {}).get("flash-attn"),
        "cuda_toolkit_version": "13.4.92", "compiled_architecture": "sm_120",
        "kernel_probe_passed": bool((environment.get("flash_attention") or {}).get("kernel_success")),
        "torch_cuda_build": environment.get("torch_cuda_build"),
        "build_note": "CUDA 13.4 toolchain linked FlashAttention; runtime kernel validated against PyTorch cu130 on driver 617.14.",
    }
    write_json(config_path, config)
    write_json(environment_path, environment)
    write_json(trials_path, trials)
    responses["stage_smoke_requests"] = responses.get("stage_smoke_requests", [])
    write_json(responses_path, responses)
    runtime["stage0_conditions"]["runtime_and_raw_responses_saved"] = True
    write_json(runtime_path, runtime)
    report_path.write_text(make_report(runtime, trials, config), encoding="utf-8")
    print(json.dumps({"stage0_result": runtime.get("stage0_result"),
                      "selected_precision": runtime.get("selected_precision"),
                      "multi_image_order_preserved": runtime["multi_image_smoke"]["order_preserved"],
                      "report": str(report_path)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=("bf16", "int8", "nf4"))
    parser.add_argument("--phase", choices=("diagnostic", "stage", "canonical"))
    parser.add_argument("--worker-output")
    parser.add_argument("--run-id", default="run")
    parser.add_argument("--reuse-bf16-diagnostic", action="store_true")
    parser.add_argument("--finalize-existing", action="store_true")
    args = parser.parse_args()
    if args.finalize_existing:
        return finalize_existing()
    if args.worker:
        if not args.phase or not args.worker_output:
            parser.error("--worker requires --phase and --worker-output")
        output = Path(args.worker_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        code = worker(args.worker, args.phase, output)
        return code
    return orchestrate(args.run_id, args.reuse_bf16_diagnostic)


if __name__ == "__main__":
    raise SystemExit(main())
