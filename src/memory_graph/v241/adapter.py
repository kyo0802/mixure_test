"""Route unseen videos through the unchanged V2.2 SAM implementation.

Only seed/frame-window selection is generalized because the V2.2 runner hardcodes
task1/task2 IDs and frames. This policy is fixed before seven-video SAM inference.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from memory_graph.v22 import sam_tracking as frozen
from memory_graph.v23.fusion import EntityRegistry, Observation
from memory_graph.v24.appearance import (AppearanceBank, MobileNetEmbedder, choose_diverse_views,
                                         crop_rgb, bank_summary)
from memory_graph.v24.reid import decide, locked_parameters, registry_update

ROOT = frozen.ROOT
OUT = ROOT / "outputs_v241"
INITIAL_SPAN_FRAMES = 180  # V2.2 Task1's initial span
LATE_GAP_FRAMES = 108      # fixed conservative separation after initial window
LATE_SPAN_FRAMES = 78      # V2.2 late-candidate span


def v21_inputs(task):
    base = OUT / task / "upstream_v21"
    manifest = frozen.read_json(base / "prediction_manifest.json")
    names = ("detections.json", "track_timelines.json", "video_metadata.json")
    paths = {name: base / "event_analysis" / name for name in names}
    for name, path in paths.items():
        if frozen.sha256(path) != manifest[f"event_analysis/{name}"]:
            raise ValueError(f"Frozen V2.1 prediction hash mismatch: {path}")
    return {name: frozen.read_json(path) for name, path in paths.items()}, {name: frozen.sha256(path) for name, path in paths.items()}


def choose_initial(inputs):
    """Earliest repeated local phone track with at least one >=.5 YOLO view."""
    tracks = inputs["track_timelines.json"]
    eligible = []
    for track in tracks:
        obs = track["observations"]
        if track["detector_class"] != "cell phone" or len(obs) < 2:
            continue
        first_trusted = next((o for o in obs if o["confidence"] >= .5), None)
        if first_trusted is not None:
            eligible.append((first_trusted["frame_index"], track["track_id"], first_trusted))
    if not eligible:
        return None
    frame, track_id, obs = min(eligible, key=lambda item: (item[0], item[1]))
    raw = frozen.yolo_box_for_track(tracks, inputs["detections.json"], track_id, frame)
    if raw is None:
        raise ValueError(f"No matching raw YOLO seed for local track {track_id} at {frame}")
    return {"track_id": track_id, "frame_index": frame, "detection": raw,
            "rule": "earliest repeated local cell-phone track with >=0.5 detector observation"}


def choose_late(inputs, initial_frame):
    sampled = {row["frame_index"] for row in inputs["video_metadata.json"]["sampled_frames"]}
    earliest = initial_frame + INITIAL_SPAN_FRAMES + LATE_GAP_FRAMES
    by_frame = {}
    for detection in inputs["detections.json"]:
        frame = detection["frame_index"]
        if frame >= earliest and frame in sampled and detection["class_name"] == "cell phone":
            by_frame.setdefault(frame, []).append(detection)
    if not by_frame:
        return None
    frame = min(by_frame)
    candidates = sorted(by_frame[frame], key=lambda d: (-d["confidence"], d["bbox"][0]))
    return {"frame_index": frame, "detections": candidates,
            "rule": "all raw phone boxes at first sampled frame >= initial seed + 180 + 108 frames"}


def windows(initial, late, inputs):
    last = inputs["video_metadata.json"]["sampled_frames"][-1]["frame_index"]
    result = [("initial", initial["frame_index"], min(initial["frame_index"] + INITIAL_SPAN_FRAMES, last))]
    if late is not None:
        result.append(("late_candidates", late["frame_index"], min(late["frame_index"] + LATE_SPAN_FRAMES, last)))
    return result


def run_sam(task):
    """Use the exact frozen SAM builder, run_segment, diagnostics and STEP=6."""
    import torch
    inputs, hashes = v21_inputs(task)
    initial = choose_initial(inputs)
    output = OUT / task / "sam"
    output.mkdir(parents=True, exist_ok=True)
    if initial is None:
        payload = {"task": task, "status": "NO_INITIAL_LOCAL_PHONE", "segments": [],
                   "frozen_input_sha256": hashes, "initialization": None, "late_selection": None}
        (output / "sam_propagation_log.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    late = choose_late(inputs, initial["frame_index"])
    original_choose, original_extract = frozen.choose_seeds, frozen.extract_frames
    video = ROOT / f"{task}.mp4"

    def seeds(_task, segment, _inputs):
        if segment == "initial":
            return [(f"phone_track{initial['track_id']}", initial["detection"])]
        return [(f"late_candidate_{n}", det) for n, det in enumerate(late["detections"], 1)]

    def extract(_video, frames, folder):
        return original_extract(video, frames, folder)

    for path in (frozen.SAM_DEPS, frozen.SAM_SOURCE):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from sam2.build_sam import build_sam2_video_predictor
    predictor = build_sam2_video_predictor(frozen.CONFIG, str(frozen.CHECKPOINT), device="cuda", apply_postprocessing=False)
    frozen.choose_seeds, frozen.extract_frames = seeds, extract
    try:
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            segments = [frozen.run_segment(task, segment, first, last, inputs, predictor, output)
                        for segment, first, last in windows(initial, late, inputs)]
    finally:
        frozen.choose_seeds, frozen.extract_frames = original_choose, original_extract
    payload = {"task": task, "status": "COMPLETE", "implementation": "unchanged V2.2 run_segment",
               "checkpoint_sha256": frozen.sha256(frozen.CHECKPOINT), "config": frozen.CONFIG,
               "step_frames": frozen.STEP, "frozen_input_sha256": hashes,
               "initialization": initial, "late_selection": late, "segments": segments,
               "adapter_policy": {"initial_span_frames": INITIAL_SPAN_FRAMES,
                                  "late_gap_frames": LATE_GAP_FRAMES, "late_span_frames": LATE_SPAN_FRAMES}}
    (output / "sam_propagation_log.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def run_fusion(task):
    """Apply V2.3 EntityRegistry methods in their original per-frame order."""
    inputs, hashes = v21_inputs(task)
    sam_path = OUT / task / "sam" / "sam_propagation_log.json"
    sam = frozen.read_json(sam_path)
    if sam["frozen_input_sha256"] != hashes:
        raise ValueError("SAM and V2.1 hashes differ")
    initial = sam["initialization"]
    if initial is None:
        return {"status": "NO_INITIAL_LOCAL_PHONE", "registry": None, "timeline": []}
    track_id, seed_frame = initial["track_id"], initial["frame_index"]
    base = OUT / task / "upstream_v21"
    manifest = frozen.read_json(base / "prediction_manifest.json")
    entities_path = base / "persistent_entities.json"
    if frozen.sha256(entities_path) != manifest["persistent_entities.json"]:
        raise ValueError("V2.1 entity hash mismatch")
    v21_entities = frozen.read_json(entities_path)
    groups = {track: entity["entity_id"] for entity in v21_entities for track in entity["local_track_ids"]}
    registry = EntityRegistry(track_id, groups)
    tracks_by_frame, raw_by_frame, sam_by_frame = defaultdict(list), defaultdict(list), defaultdict(list)
    for track in inputs["track_timelines.json"]:
        for obs in track["observations"]:
            tracks_by_frame[obs["frame_index"]].append((track["track_id"], obs))
    for det in inputs["detections.json"]:
        raw_by_frame[det["frame_index"]].append(det)
    sam_initial = set()
    for segment in sam["segments"]:
        for event in segment["events"]:
            if event["type"] == "INIT":
                sam_initial.add((event["frame_index"], event["object_id"]))
        for obs in segment["observations"]:
            sam_by_frame[obs["frame_index"]].append(obs)
    timeline = []
    for info in inputs["video_metadata.json"]["sampled_frames"]:
        frame, timestamp = info["frame_index"], info["timestamp"]
        registry.begin_frame(frame, timestamp)
        phone_boxes = [d["bbox"] for d in raw_by_frame[frame] if d["class_name"] == "cell phone"]
        if frame == seed_frame and "phone_01" not in registry.entities:
            selected = next((o for tid, o in tracks_by_frame[frame] if tid == track_id), None)
            if selected is None:
                raise ValueError("Selected YOLO target unavailable at SAM seed")
            obs = Observation("yolo_track", frame, timestamp, f"track:{track_id}", selected["bbox"],
                              selected["class_name"], selected["confidence"], None,
                              "trusted_local", "frozen_v21_track")
            registry.observe_yolo(obs, track_id, [])
        accepted = []
        for s in sam_by_frame[frame]:
            obs = Observation("sam", frame, timestamp, s["object_id"], s["bbox"], "cell phone", None,
                              f"outputs_v241/{task}/sam/sam_propagation_log.json#{frame}:{s['object_id']}",
                              "fixed_v22_diagnostics", "official_sam2.1_frozen_v22")
            result = registry.observe_sam(obs, s["diagnostics"], phone_boxes,
                                          (frame, s["object_id"]) in sam_initial)
            if result is not None:
                accepted.append(result)
        for tid, y in sorted(tracks_by_frame[frame]):
            obs = Observation("yolo_track", frame, timestamp, f"track:{tid}", y["bbox"],
                              y["class_name"], y["confidence"], None, "trusted_local", "frozen_v21_track")
            registry.observe_yolo(obs, tid, accepted)
        for det in raw_by_frame[frame]:
            registry.confirm_raw_yolo(det, accepted)
        phone = registry.entities.get("phone_01")
        timeline.append({"frame_index": frame, "timestamp": timestamp,
                         "state": phone["state"] if phone else None,
                         "raw_phone_count": len(phone_boxes),
                         "sam_phone_count": sum(s["object_id"] == f"phone_track{track_id}" for s in sam_by_frame[frame]),
                         "phone_last_trusted_seen": phone["last_trusted_seen"] if phone else None})
    return {"status": "COMPLETE", "registry": registry, "timeline": timeline,
            "input_hashes": hashes, "sam_hash": frozen.sha256(sam_path), "initialization": initial}


def video_frame(task, frame):
    cap = cv2.VideoCapture(str(ROOT / f"{task}.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
    okay, image = cap.read()
    cap.release()
    if not okay:
        raise OSError(f"Cannot decode {task} frame {frame}")
    return image


def appearance_and_reid(task, fusion):
    """Exact V2.4 embedder/decide/registry_update on routed new-video crops."""
    params, parameter_hash = locked_parameters()
    registry = fusion["registry"]
    phone = registry.entities.get("phone_01")
    sam = frozen.read_json(OUT / task / "sam" / "sam_propagation_log.json")
    if phone is None:
        return {"decision": "NO_SAFE_MATCH", "reason": "no initial target entity", "attempts": [],
                "appearance_bank": None, "parameter_manifest_sha256": parameter_hash}
    target = f"phone_track{sam['initialization']['track_id']}"
    sam_rows = {}
    for segment in sam["segments"]:
        for obs in segment["observations"]:
            key = f"{obs['frame_index']}:{obs['object_id']}"
            sam_rows[(obs["frame_index"], obs["object_id"])] = (obs, segment["masks_rle"].get(key))
    rows = []
    for obs in phone["observation_history"]:
        frame = obs["frame_index"]
        s = sam_rows.get((frame, target))
        if obs["source"] != "yolo_track" or (obs["detector_confidence"] or 0) < .5 or s is None:
            continue
        sam_obs, rle = s
        if sam_obs["diagnostics"]["possible_mask_drift"] or rle is None:
            continue
        if frozen.box_iou(obs["bbox"], sam_obs["bbox"]) < .5:
            continue
        rows.append({"frame_index": frame, "timestamp": obs["timestamp"], "bbox": obs["bbox"],
                     "source": obs["source_object_id"], "detector_confidence": obs["detector_confidence"],
                     "mask": rle})
    chosen = choose_diverse_views(rows)
    late_entities = sorted((e for e in registry.entities.values() if e["entity_id"].startswith("candidate_phone_")),
                           key=lambda e: e["entity_id"])
    if len(chosen) < params["minimum_evidence_prototypes"]:
        return {"decision": "NO_SAFE_MATCH", "reason": "fewer than two trusted appearance prototypes",
                "attempts": [], "appearance_bank": {"entity_id": "phone_01", "prototypes": []},
                "late_candidate_entity_ids": [e["entity_id"] for e in late_entities],
                "parameter_manifest_sha256": parameter_hash}
    embedder = MobileNetEmbedder()
    if embedder.weight_sha256 != params["checkpoint_sha256"]:
        raise ValueError("Frozen embedding checkpoint changed")
    bank = AppearanceBank("phone_01")
    for row in chosen:
        crop = crop_rgb(video_frame(task, row["frame_index"]), row["bbox"], frozen.decode_mask(row["mask"]))
        vector, key = embedder.embed_crop(crop)
        bank.add({"entity_id": "phone_01", "frame_index": row["frame_index"],
                  "timestamp": row["timestamp"], "source": row["source"],
                  "crop_reference": f"{task}:frame{row['frame_index']}:{row['source']}",
                  "mask_used": True, "embedding_cache_key": key, "embedding": vector.tolist()},
                 trusted=True, reason="YOLO local observation agrees with accepted SAM mask")
    candidates = []
    for entity in late_entities:
        source = next((s for s, eid in registry.sam_to_entity.items() if eid == entity["entity_id"]), None)
        observations = sorted((frame, value) for (frame, sid), value in sam_rows.items() if sid == source)
        if not observations:
            continue
        frame, (obs, rle) = observations[0]
        if rle is None or obs["mask_area"] <= 0:
            continue
        crop = crop_rgb(video_frame(task, frame), obs["bbox"], frozen.decode_mask(rle))
        vector, key = embedder.embed_crop(crop)
        candidates.append({"entity_id": entity["entity_id"], "source_id": source,
                           "frame_index": frame, "timestamp": obs["timestamp"], "bbox": obs["bbox"],
                           "semantic_label": entity["semantic_label"], "mask_used": True,
                           "embedding_cache_key": key, "vector": vector,
                           "quality": "frozen_yolo_seed_and_nonempty_sam_mask", "registry_entity": entity})
    if not candidates:
        return {"decision": "NO_SAFE_MATCH", "reason": "no late phone candidates",
                "attempts": [], "appearance_bank": bank_summary(bank),
                "parameter_manifest_sha256": parameter_hash}
    contexts = {c["entity_id"]: {"match_sufficient": False, "world_fixed": False}
                for c in candidates}
    scored = decide(phone, bank, candidates, params, contexts)
    matches = [row for row in scored if row["decision"] == "MATCH"]
    update = None
    if matches:
        candidate = next(c for c in candidates if c["entity_id"] == matches[0]["candidate_entity_id"])
        update = registry_update("phone_01", candidate, "MATCH", phone, bank)
    # The query's appearance memory is never changed for ambiguous candidates.
    return {"decision": "MATCH" if matches else "NO_SAFE_MATCH", "reason": "frozen V2.4 gates",
            "attempts": scored, "appearance_bank": bank_summary(bank),
            "registry_update": update, "parameter_manifest_sha256": parameter_hash,
            "gt_accessed": False}


def run_identity(task):
    fusion = run_fusion(task)
    output = OUT / task
    if fusion["registry"] is None:
        timeline = {"task": task, "status": fusion["status"], "phone_timeline": [],
                    "target_entity": None, "phone_entities": []}
        reid = {"decision": "NO_SAFE_MATCH", "reason": "no initial target entity", "attempts": []}
    else:
        registry = fusion["registry"]
        reid = appearance_and_reid(task, fusion)
        target = registry.entities.get("phone_01")
        timeline = {"task": task, "status": fusion["status"], "initialization": fusion["initialization"],
                    "phone_timeline": fusion["timeline"], "target_entity": target,
                    "phone_entities": [e for e in registry.entities.values() if e["semantic_label"] == "cell phone"],
                    "track_to_entity": registry.track_to_entity, "sam_to_entity": registry.sam_to_entity,
                    "fusion_audit": registry.audit, "v21_input_sha256": fusion["input_hashes"],
                    "sam_log_sha256": fusion["sam_hash"], "gt_accessed": False}
    (output / "identity_timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    (output / "reid_audit.json").write_text(json.dumps(reid, indent=2), encoding="utf-8")
    return timeline, reid
