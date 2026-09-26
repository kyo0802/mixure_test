"""GT-free SAM 2.1 video propagation from frozen YOLO evidence."""
from __future__ import annotations

import hashlib
import json
import math
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
SAM_SOURCE = ROOT / ".sam2_official"
SAM_DEPS = ROOT / ".sam2_deps"
CHECKPOINT = ROOT / ".models" / "sam2.1_hiera_small.pt"
CONFIG = "configs/sam2.1/sam2.1_hiera_s.yaml"
STEP = 6


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def frozen_inputs(task):
    base = ROOT / "outputs_v21" / task / "event_analysis"
    paths = {name: base / name for name in ("detections.json", "track_timelines.json", "video_metadata.json")}
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = read_json(ROOT / "outputs_v21" / task / "prediction_manifest.json")
    for name, path in paths.items():
        expected = manifest[f"event_analysis/{name}"]
        if sha256(path) != expected:
            raise ValueError(f"V2.1 frozen artifact changed: {path}")
    return {name: read_json(path) for name, path in paths.items()}, {name: sha256(path) for name, path in paths.items()}


def yolo_box_for_track(tracks, detections, track_id, frame):
    track = next(t for t in tracks if t["track_id"] == track_id)
    obs = next((o for o in track["observations"] if o["frame_index"] == frame), None)
    if obs is None:
        return None
    matches = [d for d in detections if d["frame_index"] == frame and d["class_name"] == "cell phone"
               and box_iou(d["bbox"], obs["bbox"]) >= 0.95]
    return max(matches, key=lambda d: d["confidence"], default=None)


def box_iou(a, b):
    x = max(0., min(a[2], b[2]) - max(a[0], b[0]))
    y = max(0., min(a[3], b[3]) - max(a[1], b[1]))
    inter = x * y
    union = max(0., a[2] - a[0]) * max(0., a[3] - a[1]) + max(0., b[2] - b[0]) * max(0., b[3] - b[1]) - inter
    return inter / union if union else 0.


def mask_to_observation(mask, frame, timestamp, segment, obj_id, previous=None, yolo_boxes=()):
    """Return a LocalObservation-compatible geometry record, never a fabricated detection score."""
    binary = np.asarray(mask, dtype=bool)
    ys, xs = np.nonzero(binary)
    if len(xs) == 0:
        return None
    bbox = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]
    area = int(len(xs))
    center = [float(xs.mean()), float(ys.mean())]
    bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    diagnostics = {"mask_area_ratio": None, "bbox_area_ratio": None, "centroid_displacement": None,
                   "max_yolo_iou": max((box_iou(bbox, b) for b in yolo_boxes), default=None),
                   "possible_mask_drift": False, "reasons": []}
    if previous is not None:
        prior_area = previous["mask_area"]
        prior_box = previous["bbox"]
        prior_box_area = (prior_box[2] - prior_box[0]) * (prior_box[3] - prior_box[1])
        diagnostics["mask_area_ratio"] = area / prior_area
        diagnostics["bbox_area_ratio"] = bbox_area / prior_box_area
        diagnostics["centroid_displacement"] = math.dist(center, previous["center"])
        if not .2 <= diagnostics["mask_area_ratio"] <= 5:
            diagnostics["reasons"].append("sudden_mask_area_change")
        if not .2 <= diagnostics["bbox_area_ratio"] <= 5:
            diagnostics["reasons"].append("sudden_bbox_area_change")
        if diagnostics["centroid_displacement"] > .25 * math.hypot(*binary.shape):
            diagnostics["reasons"].append("large_centroid_jump")
    # Other cell-phone boxes can be different desk phones. A missing overlap with
    # those boxes is recorded above, but is not itself evidence of mask drift.
    diagnostics["possible_mask_drift"] = bool(diagnostics["reasons"])
    return {"frame_index": frame, "timestamp": timestamp, "bbox": bbox, "center": center,
            "mask_area": area, "source": "sam2.1_propagation", "segment": segment,
            "object_id": obj_id, "confidence": None, "diagnostics": diagnostics}


def encode_mask(mask):
    """Compact binary RLE in image row order for auditable mask overlays."""
    flat = np.asarray(mask, dtype=np.uint8).ravel()
    edges = np.flatnonzero(np.diff(np.r_[0, flat, 0]))
    return {"shape": list(mask.shape), "starts": edges[::2].tolist(),
            "lengths": (edges[1::2] - edges[::2]).tolist()}


def decode_mask(rle):
    flat = np.zeros(math.prod(rle["shape"]), dtype=bool)
    for start, length in zip(rle["starts"], rle["lengths"]):
        flat[start:start + length] = True
    return flat.reshape(rle["shape"])


def choose_seeds(task, segment, inputs):
    """Predeclared frozen-track or all-raw-candidate policy; GT is never accessed."""
    detections = inputs["detections.json"]
    tracks = inputs["track_timelines.json"]
    if (task, segment) == ("task1", "initial"):
        candidates = [("phone_track17", yolo_box_for_track(tracks, detections, 17, 240))]
    elif (task, segment) == ("task2", "initial"):
        candidates = [("phone_track22", yolo_box_for_track(tracks, detections, 22, 78))]
    elif (task, segment) == ("task2", "late_candidates"):
        # Prompt every frozen cell-phone detection at the first late frame. No GT chooses a box.
        matches = sorted((d for d in detections if d["frame_index"] == 528 and d["class_name"] == "cell phone"),
                         key=lambda d: (-d["confidence"], d["bbox"][0]))
        candidates = [(f"late_candidate_{i + 1}", d) for i, d in enumerate(matches)]
    else:
        raise ValueError((task, segment))
    if not candidates or any(d is None for _, d in candidates):
        raise ValueError(f"YOLO_INITIALIZATION_MISS: {task} {segment}")
    return candidates


def extract_frames(video, frames, output):
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise OSError(video)
    for i, frame in enumerate(frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = cap.read()
        if not ok or not cv2.imwrite(str(output / f"{i:05d}.jpg"), image, [cv2.IMWRITE_JPEG_QUALITY, 95]):
            raise OSError(f"Cannot decode frame {frame}: {video}")
    cap.release()


def run_segment(task, segment, first, last, inputs, predictor, output):
    import torch
    frames = list(range(first, last + 1, STEP))
    timestamps = {f["frame_index"]: f["timestamp"] for f in inputs["video_metadata.json"]["sampled_frames"]}
    detections = inputs["detections.json"]
    seeds = choose_seeds(task, segment, inputs)
    observations, events, masks = [], [], {}
    previous = {}
    with tempfile.TemporaryDirectory(prefix="sam_frames_", dir=output) as folder:
        folder = Path(folder)
        extract_frames(ROOT / ("test1.mp4" if task == "task1" else "test2.mp4"), frames, folder)
        state = predictor.init_state(str(folder), offload_video_to_cpu=True, offload_state_to_cpu=True)
        for obj_number, (obj_name, evidence) in enumerate(seeds, start=1):
            if evidence["frame_index"] != first:
                raise ValueError("Seed frame must match segment start")
            box = np.array(evidence["bbox"], dtype=np.float32)
            _, ids, logits = predictor.add_new_points_or_box(state, frame_idx=0, obj_id=obj_number, box=box)
            events.append({"type": "INIT", "frame_index": first,
                           "timestamp": timestamps[first], "segment": segment, "object_id": obj_name,
                           "frozen_yolo_detection": evidence, "mode": "INITIAL_PROPAGATION" if segment == "initial" else "YOLO_REINITIALIZED_PROPAGATION_CANDIDATE"})
        start_time = time.monotonic()
        torch.cuda.reset_peak_memory_stats()
        for local_index, ids, logits in predictor.propagate_in_video(state, start_frame_idx=0, max_frame_num_to_track=len(frames)):
            frame = frames[local_index]
            raw_boxes = [d["bbox"] for d in detections if d["frame_index"] == frame and d["class_name"] == "cell phone"]
            for j, obj_number in enumerate(ids):
                name = seeds[obj_number - 1][0]
                mask = (logits[j, 0] > 0).cpu().numpy()
                obs = mask_to_observation(mask, frame, timestamps[frame], segment, name,
                                          previous.get(name), raw_boxes)
                if obs is None:
                    events.append({"type": "LOST", "frame_index": frame, "object_id": name, "reason": "empty_mask"})
                    previous.pop(name, None)
                    continue
                previous[name] = obs
                observations.append(obs)
                masks[f"{frame}:{name}"] = encode_mask(mask)
                events.append({"type": "PROPAGATE", "frame_index": frame, "object_id": name,
                               "possible_mask_drift": obs["diagnostics"]["possible_mask_drift"]})
        elapsed = time.monotonic() - start_time
        for name, _ in seeds:
            events.append({"type": "TERMINATE", "frame_index": frames[-1], "object_id": name,
                           "reason": "evaluation_window_end"})
        predictor.reset_state(state)
    return {"segment": segment, "frames": frames, "seeds": [name for name, _ in seeds], "events": events,
            "observations": observations, "masks_rle": masks,
            "compute": {"frames_processed": len(frames), "wall_seconds": elapsed,
                        "effective_fps": len(frames) / elapsed if elapsed else None,
                        "peak_gpu_bytes": torch.cuda.max_memory_allocated()}}


def run(task, output):
    import torch
    for path in (SAM_DEPS, SAM_SOURCE):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from sam2.build_sam import build_sam2_video_predictor

    inputs, hashes = frozen_inputs(task)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    predictor = build_sam2_video_predictor(CONFIG, str(CHECKPOINT), device="cuda", apply_postprocessing=False)
    windows = [("initial", 240, 420)] if task == "task1" else [("initial", 78, 312), ("late_candidates", 528, 606)]
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        segments = [run_segment(task, name, first, last, inputs, predictor, output) for name, first, last in windows]
    result = {"task": task, "implementation": "official facebookresearch/sam2", "code_revision": "2b90b9f5ceec907a1c18123530e92e794ad901a4",
              "checkpoint": "sam2.1_hiera_small.pt", "checkpoint_sha256": sha256(CHECKPOINT), "config": CONFIG,
              "device": torch.cuda.get_device_name(0), "dtype": "bfloat16", "torch": torch.__version__,
              "cuda": torch.version.cuda, "frozen_input_sha256": hashes, "step_frames": STEP,
              "drift_rule": "fixed before GT review: mask or bbox area ratio outside [0.2, 5], or centroid jump > 0.25 image diagonal; YOLO overlap recorded separately, not used to force a decision",
              "segments": segments}
    (output / "sam_propagation_log.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
