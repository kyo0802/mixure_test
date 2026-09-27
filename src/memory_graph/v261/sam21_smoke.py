"""Fresh eight-frame SAM 2.1 feasibility comparison on the frozen test8 box."""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v261" / "smoke"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for path in (ROOT / ".sam2_deps", ROOT / ".sam2_official"):
        sys.path.insert(0, str(path))
    from sam2.build_sam import build_sam2_video_predictor

    frozen = json.loads((ROOT / "outputs_v26" / "test8" / "sam_reinit_log.json").read_text(encoding="utf-8"))
    assert frozen["status"] == "EXECUTED" and frozen["authorized_by"] == "CONFIRMED_MATCH"
    init = next(e for e in frozen["segment"]["events"] if e["type"] == "INIT")
    box = init["frozen_yolo_detection"]["bbox"]
    frames = list(range(init["frame_index"], init["frame_index"] + 48, 6))
    cap = cv2.VideoCapture(str(ROOT / "test8.mp4"))
    if not cap.isOpened():
        raise RuntimeError("test8 video could not be opened")
    with tempfile.TemporaryDirectory(prefix="sam21_smoke_", dir=OUT) as temporary:
        folder = Path(temporary)
        for local, source in enumerate(frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, source)
            ok, bgr = cap.read()
            if not ok or not cv2.imwrite(str(folder / f"{local:05d}.jpg"), bgr, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError(f"Frame extraction failed: {source}")
        cap.release()
        start = time.perf_counter()
        predictor = build_sam2_video_predictor(
            "configs/sam2.1/sam2.1_hiera_s.yaml",
            str(ROOT / ".models" / "sam2.1_hiera_small.pt"),
            device="cuda", apply_postprocessing=False,
        )
        build_seconds = time.perf_counter() - start
        start = time.perf_counter()
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            state = predictor.init_state(str(folder), offload_video_to_cpu=True, offload_state_to_cpu=True)
            session_seconds = time.perf_counter() - start
            torch.cuda.reset_peak_memory_stats()
            start = time.perf_counter()
            predictor.add_new_points_or_box(state, frame_idx=0, obj_id=1, box=np.array(box, dtype=np.float32))
            prompt_seconds = time.perf_counter() - start
            start = time.perf_counter()
            outputs = []
            for local, object_ids, logits in predictor.propagate_in_video(
                state, start_frame_idx=0, max_frame_num_to_track=len(frames)
            ):
                outputs.append({"frame_index": frames[local], "object_ids": list(map(int, object_ids)),
                                "areas": [int((logits[i, 0] > 0).sum().item()) for i in range(len(object_ids))]})
            propagation_seconds = time.perf_counter() - start
            peak_bytes = torch.cuda.max_memory_allocated()
            predictor.reset_state(state)
    result = {"video": "test8.mp4", "frames": frames, "frozen_box_xyxy": box,
              "attention_backend": "sam21_official", "outputs": outputs,
              "timing_seconds": {"build": build_seconds, "session": session_seconds,
                                 "prompt": prompt_seconds, "propagation": propagation_seconds},
              "peak_gpu_bytes": peak_bytes}
    (OUT / "sam21_eight_frame_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"SAM21 eight frames: propagation={propagation_seconds:.3f}s, nonempty={sum(bool(row['areas'][0]) for row in outputs)}/8, peak={peak_bytes}")


if __name__ == "__main__":
    main()
