"""Recover safe event-local anchor hypotheses from frozen YOLO and VLM boxes."""
from __future__ import annotations

from collections import defaultdict
from statistics import median

from memory_graph.v22.sam_tracking import box_iou
from memory_graph.v28.roles import semantic_roles


ROLE_OVERRIDES = {
    "box": ["CONTAINER"], "bag": ["CONTAINER"], "drawer": ["CONTAINER"],
    "suitcase": ["CONTAINER"], "handbag": ["CONTAINER"], "backpack": ["CONTAINER"],
    "table": ["SUPPORT"], "dining table": ["SUPPORT"], "desk": ["SUPPORT"], "counter": ["SUPPORT"],
    "sports ball": ["OCCLUDER", "LANDMARK"], "teddy bear": ["OCCLUDER", "LANDMARK"],
    "microwave": ["LANDMARK"], "bottle": ["LANDMARK"], "chair": ["LANDMARK"],
    "person": ["INTERACTION_AGENT"],
}


def roles_for(label: str) -> list[str]:
    result = ROLE_OVERRIDES.get((label or "").casefold().strip(), semantic_roles(label))
    return ["UNKNOWN_LANDMARK"] if result == ["OTHER"] else result


def recover_anchors(event: dict, dense: dict, max_anchors: int = 12,
                    frame_size: tuple[int, int] | None = None) -> dict:
    rows = dense.get("rows", [])
    known = defaultdict(list)
    loose = []
    for row in rows:
        for det in row.get("anchors", []):
            if det.get("entity_id"):
                known[det["entity_id"]].append((row["frame"], det))
            else:
                loose.append((row["frame"], det))
    output = []
    for entity_id, entries in sorted(known.items()):
        unique = {frame: det for frame, det in entries}
        det = next(iter(unique.values()))
        output.append({"anchor_id": entity_id, "persistent_entity_id": entity_id,
                       "source": "EXISTING_ENTITY", "raw_label": det["label"],
                       "normalized_label": det["label"], "semantic_role": roles_for(det["label"]),
                       "frame_range": [min(unique), max(unique)],
                       "boxes": [{"frame": f, "bbox": x["bbox"]} for f, x in sorted(unique.items())],
                       "mask_refs": [], "temporal_consistency": len(unique),
                       "trusted_for_physical_reasoning": len(unique) >= 2,
                       "reason": "frozen persistent anchor matched to dense YOLO by same class and IoU",
                       "provenance": sorted({x.get("source", "frozen_v28_anchor") for _, x in entries})})
    # Greedy same-class short-window tracking. No class becomes a global entity.
    tracks = []
    for frame, det in sorted(loose, key=lambda x: (x[0], x[1]["label"], x[1]["bbox"][0])):
        options = [(box_iou(det["bbox"], tr[-1][1]["bbox"]), i) for i, tr in enumerate(tracks)
                   if tr[-1][1]["label"] == det["label"] and 0 < frame-tr[-1][0] <= 6]
        score, idx = max(options, default=(0, None))
        if idx is not None and score >= .15:
            tracks[idx].append((frame, det))
        else:
            tracks.append([(frame, det)])
    if frame_size is None:
        # Infer a conservative image extent from observed boxes when metadata
        # is unavailable. Callers with video metadata should pass it explicitly.
        width = max((d["bbox"][2] for _, d in loose), default=1280.0)
        height = max((d["bbox"][3] for _, d in loose), default=720.0)
    else:
        width, height = frame_size
    local_number = 1
    for track in tracks:
        frames = sorted({f for f, _ in track})
        if len(frames) < 3:
            continue
        dets = [d for _, d in track]
        label = dets[0]["label"]
        boxes = [d["bbox"] for d in dets]
        normalized_center_spread = median(abs((b[0]+b[2]-a[0]-a[2])/(2*max(1, width)))
                                          for a, b in zip(boxes, boxes[1:])) if len(boxes) > 1 else 1.0
        role = roles_for(label)
        stable = normalized_center_spread < .08
        output.append({"anchor_id": f"event_anchor_{local_number:03d}", "persistent_entity_id": None,
                       "source": "YOLO", "raw_label": label, "normalized_label": label,
                       "semantic_role": role or ["UNKNOWN_LANDMARK"],
                       "frame_range": [min(frames), max(frames)],
                       "boxes": [{"frame": f, "bbox": d["bbox"]} for f, d in track],
                       "mask_refs": [], "temporal_consistency": len(frames),
                       "trusted_for_physical_reasoning": stable and any(r != "UNKNOWN_LANDMARK" for r in role),
                       "scope": "EVENT_LOCAL_ANCHOR",
                       "reason": "short-window YOLO detections grouped by same class and consecutive-frame box overlap",
                       "provenance": ["frozen_yolo_checkpoint", "event_window_only"]})
        local_number += 1
    output.sort(key=lambda a: (a["persistent_entity_id"] is None,
                               -a["temporal_consistency"], a["anchor_id"]))
    output = output[:max_anchors]
    return {"schema": "v291_anchor_recovery_1", "event_id": event["event_id"],
            "anchors": output,
            "counts": {"existing_persistent": sum(a["persistent_entity_id"] is not None for a in output),
                       "event_local": sum(a["persistent_entity_id"] is None for a in output),
                       "trusted_for_physical_reasoning": sum(a["trusted_for_physical_reasoning"] for a in output)},
            "identity_policy": "event-local anchors never alias a PersistentEntity without a separate Identity Guard decision"}
