"""Targeted source-video reinspection at half-native-rate (~15 fps)."""
from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import time

import cv2
import numpy as np

from memory_graph.v22.sam_tracking import (SAM_DEPS, SAM_SOURCE, CONFIG, CHECKPOINT,
                                            encode_mask, mask_to_observation, box_iou)
from memory_graph.v27.pipeline import ROOT, write


def frame_numbers(event: dict, fps: float, native_fps: float) -> list[int]:
    """Bounded to the detected window, with no whole-video path."""
    step = max(1, round(native_fps / min(15.0, native_fps)))
    return list(range(event["start_frame"], event["end_frame"]+1, step))


def _extract(video: Path, numbers: list[int], folder: Path) -> None:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise OSError(video)
    try:
        for index, number in enumerate(numbers):
            cap.set(cv2.CAP_PROP_POS_FRAMES, number)
            ok, frame = cap.read()
            if not ok or not cv2.imwrite(str(folder/f"{index:05d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 90]):
                raise OSError(f"Cannot extract frame {number} from {video}")
    finally:
        cap.release()


def _detections(model, images: list[Path]) -> dict[int, list[dict]]:
    # Frozen checkpoint and no training. Every output is local to this event.
    result = {}
    for start in range(0, len(images), 12):
        batch = model.predict(source=[str(x) for x in images[start:start+12]], conf=.15,
                              imgsz=960, device=0, verbose=False)
        for offset, item in enumerate(batch):
            rows = []
            for box in item.boxes:
                cid = int(box.cls[0])
                rows.append({"label": model.names[cid], "class_id": cid,
                             "confidence": float(box.conf[0]),
                             "bbox": [float(v) for v in box.xyxy[0].tolist()]})
            result[start+offset] = rows
    return result


def _match_anchor(detection: dict, known: list[dict]) -> dict:
    same = [(box_iou(detection["bbox"], a["bbox"]), a) for a in known
            if a["raw_label"] == detection["label"]]
    score, winner = max(same, key=lambda x: x[0], default=(0, None))
    if score >= .35:
        return {**detection, "entity_id": winner["entity_id"], "authorization": "FROZEN_ANCHOR_IOU",
                "source": winner["source"], "match_iou": score}
    return {**detection, "entity_id": None, "authorization": "UNKNOWN_ANCHOR",
            "source": None, "match_iou": score}


class DenseRunner:
    def __init__(self):
        from ultralytics import YOLO
        import torch
        self.torch = torch
        self.yolo = YOLO(str(ROOT/".models/yolo11s.pt"))
        for path in (SAM_DEPS, SAM_SOURCE):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        from sam2.build_sam import build_sam2_video_predictor
        self.sam = build_sam2_video_predictor(CONFIG, str(CHECKPOINT), device="cuda",
                                               apply_postprocessing=False)

    def run(self, task: str, event: dict, trusted_masks: list[dict], fps: float,
            folder: Path) -> dict:
        folder.mkdir(parents=True, exist_ok=True)
        video = ROOT/f"{task}.mp4"
        cap = cv2.VideoCapture(str(video))
        native_fps = float(cap.get(cv2.CAP_PROP_FPS))
        cap.release()
        numbers = frame_numbers(event, fps, native_fps)
        trusted = [m for m in trusted_masks if m["trusted"] and numbers[0] <= m["frame"] <= numbers[-1]]
        seed = trusted[0] if trusted else None
        started = time.monotonic()
        with TemporaryDirectory(prefix="v29_event_", dir=folder) as tmp:
            image_dir = Path(tmp)
            _extract(video, numbers, image_dir)
            images = [image_dir/f"{i:05d}.jpg" for i in range(len(numbers))]
            detections = _detections(self.yolo, images)
            masks = {}
            sam_status = "NO_TRUSTED_SEED"
            if seed:
                seed_index = min(range(len(numbers)), key=lambda i: abs(numbers[i]-seed["frame"]))
                # A seed cannot be selected using future evidence; the nearest
                # frame is within one dense sample of its frozen timestamp.
                state = self.sam.init_state(str(image_dir), offload_video_to_cpu=True,
                                            offload_state_to_cpu=True)
                previous = None
                with self.torch.inference_mode(), self.torch.autocast("cuda", dtype=self.torch.bfloat16):
                    self.sam.add_new_points_or_box(state, frame_idx=seed_index, obj_id=1,
                                                    box=np.asarray(seed["mask_bbox"], dtype=np.float32))
                    for local, ids, logits in self.sam.propagate_in_video(
                            state, start_frame_idx=seed_index,
                            max_frame_num_to_track=len(numbers)-seed_index):
                        if 1 not in ids:
                            continue
                        frame = numbers[local]
                        j = list(ids).index(1)
                        binary = (logits[j, 0] > 0).cpu().numpy()
                        obs = mask_to_observation(binary, frame, frame/native_fps, event["event_id"],
                                                  "phone_01_continuation", previous,
                                                  [d["bbox"] for d in detections[local] if d["label"] == "cell phone"])
                        if obs is None:
                            previous = None
                            continue
                        # A propagated mask is authorized only for a short
                        # causal continuation from the final frozen trusted mask.
                        nearest = min((abs(frame-m["frame"]) for m in trusted), default=10**9)
                        identity_ok = nearest <= round(.4*native_fps)
                        segmentation_ok = not obs["diagnostics"]["possible_mask_drift"]
                        masks[local] = {"frame": frame, "bbox": obs["bbox"], "area": obs["mask_area"],
                                        "center": obs["center"], "trusted": identity_ok and segmentation_ok,
                                        "identity_authorization": "FROZEN_SHORT_CONTINUITY" if identity_ok else "UNAUTHORIZED_LONG_GAP",
                                        "sam_status": "ACCEPT" if segmentation_ok else "DRIFT_REJECTED",
                                        "rle": encode_mask(binary) if identity_ok and segmentation_ok else None,
                                        "diagnostics": obs["diagnostics"]}
                        previous = obs if segmentation_ok else None
                self.sam.reset_state(state)
                sam_status = "PROPAGATED"
            rows = []
            last_trusted = max((m["frame"] for m in trusted), default=-1)
            for local, frame in enumerate(numbers):
                phone_dets = [d for d in detections[local] if d["label"] == "cell phone"]
                anchors = [_match_anchor(d, event["candidate_anchors"])
                           for d in detections[local] if d["label"] != "cell phone"]
                mask = masks.get(local)
                # YOLO phone candidates stay separate. Identity comes only
                # from already authorized SAM short continuity.
                rows.append({"frame": frame, "time": frame/native_fps,
                             "yolo_phone_detections": phone_dets,
                             "phone_candidates": [{**d, "entity_id": None, "identity": "CANDIDATE_ONLY"}
                                                  for d in phone_dets],
                             "sam_phone": {k: v for k, v in mask.items() if k != "rle"} if mask else None,
                             "identity_authorized": bool(mask and mask["trusted"]),
                             "phone_01_state": "VISIBLE_PROPAGATED" if mask and mask["trusted"] else "UNOBSERVED",
                             "anchors": anchors,
                             "known_anchor_count": sum(a["entity_id"] is not None for a in anchors),
                             "provenance": {"video_frame": frame, "seed_mask": seed["mask_reference"] if seed else None}})
            # Persist only trusted dense RLE and compact source frame indices.
            write(folder/"target_masks.json", {str(v["frame"]): v["rle"] for v in masks.values() if v["trusted"]})
            write(folder/"dense_observations.json", {"schema": "v29_dense_window_1", "task": task,
                  "event_id": event["event_id"], "source_video": video.name,
                  "sampling": {"native_fps": native_fps, "processed_frames": len(numbers),
                               "start_frame": numbers[0], "end_frame": numbers[-1]},
                  "seed": seed["mask_reference"] if seed else None,
                  "sam_status": sam_status, "rows": rows,
                  "runtime_seconds": time.monotonic()-started,
                  "peak_vram_bytes": self.torch.cuda.max_memory_allocated()})
            from .visualization import render_event_sheet
            render_event_sheet(images, numbers, rows, event, folder)
        return {"event_id": event["event_id"], "dense_frames": len(rows),
                "trusted_dense_masks": sum(r["identity_authorized"] for r in rows),
                "phone_detections": sum(len(r["yolo_phone_detections"]) for r in rows),
                "anchor_detections": sum(len(r["anchors"]) for r in rows),
                "known_anchor_covisible": sum(r["identity_authorized"] and r["known_anchor_count"] > 0 for r in rows),
                "runtime_seconds": time.monotonic()-started}
