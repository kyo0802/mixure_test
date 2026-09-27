"""Small GT-free SAM 3.1 API and runtime check using frozen test8 reinit evidence."""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

import cv2
import torch

from memory_graph.v261.compat import build_compatible_predictor


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v261" / "smoke"
CHECKPOINT = ROOT / ".models" / "sam3.1" / "sam3.1_multiplex.pt"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frozen = json.loads((ROOT / "outputs_v26" / "test8" / "sam_reinit_log.json").read_text(encoding="utf-8"))
    assert frozen["status"] == "EXECUTED" and frozen["authorized_by"] == "CONFIRMED_MATCH"
    init = next(e for e in frozen["segment"]["events"] if e["type"] == "INIT")
    first = init["frame_index"]
    box = init["frozen_yolo_detection"]["bbox"]
    frame_count = int(os.environ.get("SAM31_SMOKE_FRAME_COUNT", "8"))
    frames = list(range(first, first + 6 * frame_count, 6))
    cap = cv2.VideoCapture(str(ROOT / "test8.mp4"))
    if not cap.isOpened():
        raise RuntimeError("test8 video could not be opened")
    with tempfile.TemporaryDirectory(prefix="sam31_smoke_", dir=OUT) as temp:
        folder = Path(temp)
        width = height = None
        for local, source in enumerate(frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, source)
            ok, bgr = cap.read()
            if not ok:
                raise RuntimeError(f"test8 frame {source} could not be read")
            height, width = bgr.shape[:2]
            if not cv2.imwrite(str(folder / f"{local:05d}.jpg"), bgr, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError("JPEG write failed")
        cap.release()
        xywh = [[box[0] / width, box[1] / height, (box[2] - box[0]) / width, (box[3] - box[1]) / height]]
        center_point = [[(box[0] + box[2]) / (2 * width), (box[1] + box[3]) / (2 * height)]]
        start = time.perf_counter()
        use_fa3 = os.environ.get("SAM31_USE_FA3", "1") == "1"
        max_objects = int(os.environ.get("SAM31_MAX_OBJECTS", "16"))
        capacity = int(os.environ.get("SAM31_CAPACITY", "16"))
        predictor = build_compatible_predictor(
            CHECKPOINT, OUT / "official_build_stdout.txt", use_fa3=use_fa3,
            max_num_objects=max_objects, multiplex_count=capacity,
        )
        build_seconds = time.perf_counter() - start
        print(f"build_seconds={build_seconds:.3f}", flush=True)
        start = time.perf_counter()
        response = predictor.handle_request({
            "type": "start_session", "resource_path": str(folder),
            "offload_video_to_cpu": True,
        })
        session_id = response["session_id"]
        session_seconds = time.perf_counter() - start
        print(f"session_seconds={session_seconds:.3f}", flush=True)
        torch.cuda.reset_peak_memory_stats()
        start = time.perf_counter()
        prompt_mode = os.environ.get("SAM31_PROMPT_MODE", "box")
        if prompt_mode == "box":
            prompt_request = {"bounding_boxes": xywh, "bounding_box_labels": [1]}
        elif prompt_mode == "point":
            prompt_request = {"points": center_point, "point_labels": [1], "obj_id": 1}
        else:
            raise ValueError("SAM31_PROMPT_MODE must be box or point")
        response = predictor.handle_request({"type": "add_prompt", "session_id": session_id,
                                             "frame_index": 0, **prompt_request})
        prompt_seconds = time.perf_counter() - start
        print(f"prompt_seconds={prompt_seconds:.3f}; init_ids={response['outputs']['out_obj_ids'].tolist()}", flush=True)
        start = time.perf_counter()
        rows = []
        for result in predictor.handle_stream_request({
            "type": "propagate_in_video", "session_id": session_id,
            "propagation_direction": "forward", "start_frame_index": 0,
            "max_frame_num_to_track": len(frames),
        }):
            out = result["outputs"]
            rows.append({
                "frame_index": frames[result["frame_index"]],
                "object_ids": out["out_obj_ids"].tolist(),
                "areas": [int(mask.sum()) for mask in out["out_binary_masks"]],
                "probabilities": out.get("out_probs", []).tolist(),
            })
            print(f"frame={rows[-1]['frame_index']}; ids={rows[-1]['object_ids']}; areas={rows[-1]['areas']}", flush=True)
        propagation_seconds = time.perf_counter() - start
        peak = torch.cuda.max_memory_allocated()
        predictor.handle_request({"type": "close_session", "session_id": session_id})
    result_name = f"smoke_{prompt_mode}_{'fa3' if use_fa3 else 'math'}_max{max_objects}_capacity{capacity}_frames{frame_count}.json"
    (OUT / result_name).write_text(json.dumps({
        "video": "test8.mp4", "frames": frames, "frozen_box_xyxy": box,
        "prompt_xywh_normalized": xywh,
        "prompt_mode": prompt_mode, "prompt_center_point_normalized": center_point,
        "attention_backend": "flash_attn_3" if use_fa3 else "torch_math_sdpa",
        "max_num_objects": max_objects, "multiplex_count": capacity,
        "timing_seconds": {"build": build_seconds, "session": session_seconds,
                           "prompt": prompt_seconds, "propagation": propagation_seconds},
        "peak_gpu_bytes": peak, "outputs": rows,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
