"""Generic frame routing through frozen V2.3 registry operations and guard."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from memory_graph.v22.sam_tracking import box_iou, read_json
from memory_graph.v23.fusion import EntityRegistry, Observation
from memory_graph.v25rerun.adapter import v21_inputs

ROOT = Path(__file__).resolve().parents[3]


def fuse_video(task, bound):
    inputs, hashes = v21_inputs(task)
    if bound is None:
        return {"status": "TARGET_BINDING_AMBIGUOUS", "registry": None,
                "phone_timeline": [], "sam_accepted_boxes": {}, "v21_hashes": hashes}
    sam = read_json(ROOT / "outputs_v25_rerun" / task / "sam" / "sam_continuity_log.json")
    if sam["frozen_input_sha256"] != hashes:
        raise ValueError("Target SAM/V2.1 input hashes disagree")
    target_track = bound.source_track_id
    base = ROOT / "outputs_v25_rerun" / task / "upstream_v21"
    v21_entities = read_json(base / "persistent_entities.json")
    groups = {tid: e["entity_id"] for e in v21_entities for tid in e["local_track_ids"]}
    registry = EntityRegistry(target_track, groups)
    tracks_by_frame, raw_by_frame, sam_by_frame = defaultdict(list), defaultdict(list), defaultdict(list)
    for track in inputs["track_timelines.json"]:
        for obs in track["observations"]:
            tracks_by_frame[obs["frame_index"]].append((track["track_id"], obs))
    for index, det in enumerate(inputs["detections.json"]):
        raw_by_frame[det["frame_index"]].append((index, det))
    sam_initial = set()
    for segment in sam["segments"]:
        for event in segment["events"]:
            if event["type"] == "INIT":
                sam_initial.add((event["frame_index"], event["object_id"]))
        for obs in segment["observations"]:
            sam_by_frame[obs["frame_index"]].append(obs)
    timeline, accepted_boxes = [], {}
    for info in inputs["video_metadata.json"]["sampled_frames"]:
        frame, timestamp = info["frame_index"], info["timestamp"]
        registry.begin_frame(frame, timestamp)
        raw_phone_boxes = [d["bbox"] for _, d in raw_by_frame[frame] if d["class_name"] == "cell phone"]
        if frame == bound.frame_index and "phone_01" not in registry.entities:
            selected = next((o for tid, o in tracks_by_frame[frame] if tid == target_track), None)
            if selected is None:
                raise ValueError("Bound target track missing at binding frame")
            obs = Observation("yolo_track", frame, timestamp, f"track:{target_track}", selected["bbox"],
                              "cell phone", selected["confidence"], None, "trusted_local", "bound_online_track")
            registry.observe_yolo(obs, target_track, [])
        accepted = []
        for s in sam_by_frame[frame]:
            obs = Observation("sam", frame, timestamp, s["object_id"], s["bbox"], "cell phone", None,
                              f"outputs_v25_rerun/{task}/sam/sam_continuity_log.json#{frame}:{s['object_id']}",
                              "fixed_v22_diagnostics", "official_sam2.1_frozen_v22")
            result = registry.observe_sam(obs, s["diagnostics"], raw_phone_boxes,
                                          (frame, s["object_id"]) in sam_initial)
            if result is not None:
                accepted.append(result)
                if result[0] == "phone_01":
                    accepted_boxes[frame] = s["bbox"]
        for tid, y in sorted(tracks_by_frame[frame]):
            if tid == target_track and frame < bound.frame_index:
                continue
            obs = Observation("yolo_track", frame, timestamp, f"track:{tid}", y["bbox"],
                              y["class_name"], y["confidence"], None, "trusted_local", "frozen_v21_track")
            registry.observe_yolo(obs, tid, accepted)
        for _, det in raw_by_frame[frame]:
            registry.confirm_raw_yolo(det, accepted)
        phone = registry.entities.get("phone_01")
        timeline.append({"frame_index": frame, "timestamp": timestamp,
                         "state": phone["state"] if phone else None,
                         "phone_track_ids": sorted(tid for tid, eid in registry.track_to_entity.items() if eid == "phone_01"),
                         "raw_phone_count": len(raw_phone_boxes),
                         "accepted_sam_target": frame in accepted_boxes,
                         "last_trusted_seen": phone["last_trusted_seen"] if phone else None})
    return {"status": "COMPLETE", "registry": registry, "phone_timeline": timeline,
            "sam_accepted_boxes": accepted_boxes, "v21_hashes": hashes}


def route_phone_observations(inputs, fusion):
    """One record per raw phone box; local ID is supporting provenance only."""
    by_frame = defaultdict(list)
    tracks_by_frame = defaultdict(list)
    for track in inputs["track_timelines.json"]:
        if track["detector_class"] != "cell phone":
            continue
        for obs in track["observations"]:
            tracks_by_frame[obs["frame_index"]].append((track["track_id"], obs))
    state_by_frame = {row["frame_index"]: row for row in fusion["phone_timeline"]}
    target_boxes = fusion["sam_accepted_boxes"]
    for index, det in enumerate(inputs["detections.json"]):
        if det["class_name"] != "cell phone":
            continue
        frame = det["frame_index"]
        match = max(((box_iou(det["bbox"], obs["bbox"]), tid)
                     for tid, obs in tracks_by_frame[frame]), default=(0., None))
        track_id = match[1] if match[0] >= .95 else None
        mapped_target = track_id in state_by_frame[frame]["phone_track_ids"] if track_id is not None else False
        sam_target = frame in target_boxes and box_iou(det["bbox"], target_boxes[frame]) >= .3
        by_frame[frame].append({"frame_index": frame, "timestamp": det["timestamp"],
                                "bbox": det["bbox"], "confidence": det["confidence"],
                                "semantic_class": "cell phone", "source_track_id": track_id,
                                "raw_detection_index": index,
                                "target_association": mapped_target or sam_target,
                                "target_association_reason": "V2.3 track/SAM fusion" if mapped_target or sam_target else None})
    return by_frame
