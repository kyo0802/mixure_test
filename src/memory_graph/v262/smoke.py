"""Official SAM 3, matched-box, eight-frame runtime feasibility probe."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import time
import traceback
from pathlib import Path

import cv2
import numpy as np
import torch
from torch.profiler import ProfilerActivity, profile


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v262" / "smoke" / "sam3"
CHECKPOINT = ROOT / ".models" / "sam3" / "sam3.pt"
FRAMES = list(range(804, 847, 6))


def save(result: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    from sam3.model_builder import build_sam3_predictor

    assert CHECKPOINT.name == "sam3.pt" and "sam3.1" not in str(CHECKPOINT).lower()
    frozen = json.loads((ROOT / "outputs_v26" / "test8" / "sam_reinit_log.json").read_text(encoding="utf-8"))
    assert frozen["status"] == "EXECUTED" and frozen["authorized_by"] == "CONFIRMED_MATCH"
    init = next(e for e in frozen["segment"]["events"] if e["type"] == "INIT")
    assert init["frame_index"] == 804
    box = init["frozen_yolo_detection"]["bbox"]
    result = {
        "schema": "v262_sam3_smoke_1", "model": "SAM3", "model_repository": "facebook/sam3",
        "builder": "build_sam3_predictor(version='sam3')", "checkpoint": str(CHECKPOINT.relative_to(ROOT)),
        "checkpoint_sha256": hashlib.file_digest(CHECKPOINT.open("rb"), "sha256").hexdigest(),
        "frames": FRAMES, "frozen_box_xyxy": box, "target_persistent_entity": "phone_01",
        "authorization": "CONFIRMED_MATCH", "primary_prompt": "normalized_xywh_box_no_text",
        "status": "STARTED", "timing_seconds": {}, "outputs": [], "attention_ops": [],
    }
    save(result)
    predictor = None
    try:
        cap = cv2.VideoCapture(str(ROOT / "test8.mp4"))
        assert cap.isOpened()
        with tempfile.TemporaryDirectory(prefix="sam3_smoke_", dir=OUT) as tmp:
            folder = Path(tmp)
            width = height = 0
            for local, source in enumerate(FRAMES):
                cap.set(cv2.CAP_PROP_POS_FRAMES, source)
                ok, bgr = cap.read()
                if not ok:
                    raise RuntimeError(f"Could not read frame {source}")
                height, width = bgr.shape[:2]
                if not cv2.imwrite(str(folder / f"{local:05d}.jpg"), bgr, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                    raise RuntimeError(f"Could not write sampled frame {source}")
            cap.release()
            x1, y1, x2, y2 = map(float, box)
            normalized = [[x1 / width, y1 / height, (x2 - x1) / width, (y2 - y1) / height]]
            result["normalized_box_xywh"] = normalized
            result["frame_size"] = [width, height]
            result["status"] = "BUILDING"
            save(result)
            start = time.perf_counter()
            predictor = build_sam3_predictor(
                checkpoint_path=str(CHECKPOINT), version="sam3", compile=False,
                async_loading_frames=False, video_loader_type="cv2",
            )
            torch.cuda.synchronize()
            result["timing_seconds"]["build"] = time.perf_counter() - start
            assert "Multiplex" not in type(predictor.model).__name__
            result["predictor_type"] = type(predictor).__name__
            result["model_type"] = type(predictor.model).__name__
            result["status"] = "SESSION"
            save(result)
            start = time.perf_counter()
            session = predictor.handle_request({
                "type": "start_session", "resource_path": str(folder),
                "offload_video_to_cpu": True, "offload_state_to_cpu": True,
            })
            torch.cuda.synchronize()
            result["timing_seconds"]["session"] = time.perf_counter() - start
            session_id = session["session_id"]
            torch.cuda.reset_peak_memory_stats()
            result["status"] = "PROMPT"
            save(result)
            start = time.perf_counter()
            with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA]) as prof:
                prompt = predictor.handle_request({
                    "type": "add_prompt", "session_id": session_id, "frame_index": 0,
                    "bounding_boxes": normalized, "bounding_box_labels": [1],
                })
                torch.cuda.synchronize()
            result["timing_seconds"]["prompt_with_profiler"] = time.perf_counter() - start
            result["attention_ops"] = sorted({e.key for e in prof.key_averages() if "attention" in e.key.lower() or "flash" in e.key.lower()})
            result["prompt_object_ids"] = np.asarray(prompt["outputs"].get("out_obj_ids", [])).astype(int).tolist()
            result["prompt_boxes_xywh"] = np.asarray(prompt["outputs"].get("out_boxes_xywh", [])).tolist()
            result["prompt_scores"] = np.asarray(prompt["outputs"].get("out_scores", [])).tolist()
            result["selected_object_id"] = choose_object_id(result["prompt_object_ids"], result["prompt_boxes_xywh"], normalized[0])
            result["status"] = "PROPAGATION"
            save(result)
            start = time.perf_counter()
            for row in predictor.handle_stream_request({
                "type": "propagate_in_video", "session_id": session_id,
                "propagation_direction": "forward", "start_frame_index": 0,
                "max_frame_num_to_track": len(FRAMES),
            }):
                local = row["frame_index"]
                output = row["outputs"]
                masks = np.asarray(output.get("out_binary_masks", []))
                result["outputs"].append({
                    "frame_index": FRAMES[local],
                    "object_ids": np.asarray(output.get("out_obj_ids", [])).astype(int).tolist(),
                    "areas": [int(np.count_nonzero(mask)) for mask in masks],
                })
                ids = result["outputs"][-1]["object_ids"]
                result["outputs"][-1]["selected_area"] = (
                    result["outputs"][-1]["areas"][ids.index(result["selected_object_id"])]
                    if result["selected_object_id"] in ids else 0
                )
            torch.cuda.synchronize()
            result["timing_seconds"]["propagation"] = time.perf_counter() - start
            result["effective_fps"] = len(result["outputs"]) / result["timing_seconds"]["propagation"]
            result["nonempty_frames"] = sum(any(a > 0 for a in row["areas"]) for row in result["outputs"])
            result["peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
            result["peak_reserved_bytes"] = torch.cuda.max_memory_reserved()
            result["gpu_memory_info_bytes"] = list(torch.cuda.mem_get_info())
            result["attention_backend"] = infer_attention(result["attention_ops"])
            try:
                smi = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
                result["nvidia_smi_used_mib"] = int(smi.stdout.strip().splitlines()[0]) if smi.returncode == 0 else None
            except Exception:
                result["nvidia_smi_used_mib"] = None
            result["status"] = "COMPLETE"
            save(result)
    except Exception as exc:
        result["status"] = "ERROR"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
        result["peak_allocated_bytes"] = torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None
        result["peak_reserved_bytes"] = torch.cuda.max_memory_reserved() if torch.cuda.is_available() else None
        save(result)
        raise
    finally:
        if predictor is not None:
            predictor.shutdown()


def infer_attention(ops: list[str]) -> str:
    names = " ".join(ops).lower()
    if "_scaled_dot_product_flash_attention" in names:
        return "PYTORCH_FLASH_SDPA"
    if "_scaled_dot_product_efficient_attention" in names:
        return "PYTORCH_MEM_EFFICIENT_SDPA"
    if "_scaled_dot_product_attention_math" in names or "_scaled_dot_product_attention_math" in names:
        return "MATH_SDPA"
    return "UNKNOWN"


def choose_object_id(ids: list[int], boxes: list[list[float]], target: list[float]) -> int | None:
    """Bind one SAM-local output to the frozen YOLO box without review labels."""
    if not ids or len(ids) != len(boxes):
        return None
    def iou(box: list[float]) -> float:
        ax, ay, aw, ah = box
        bx, by, bw, bh = target
        overlap = max(0.0, min(ax + aw, bx + bw) - max(ax, bx)) * max(0.0, min(ay + ah, by + bh) - max(ay, by))
        union = aw * ah + bw * bh - overlap
        return overlap / union if union > 0 else 0.0
    best = max(range(len(ids)), key=lambda index: iou(boxes[index]))
    return ids[best] if iou(boxes[best]) > 0 else None


if __name__ == "__main__":
    main()
