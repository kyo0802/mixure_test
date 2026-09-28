"""Build auditable relation hypotheses from time ordered dense evidence."""
from __future__ import annotations

from collections import defaultdict
from math import hypot

from memory_graph.v22.sam_tracking import decode_mask
from memory_graph.v28.roles import compatible_relations, semantic_roles


def _center(box):
    return ((box[0]+box[2])/2, (box[1]+box[3])/2)


def _relative_distance(a, b, size):
    p, q = _center(a), _center(b)
    return hypot((p[0]-q[0])/size[0], (p[1]-q[1])/size[1])


def _mask_inside(rle: dict, bbox: list[float]) -> float:
    mask = decode_mask(rle)
    x1, y1, x2, y2 = [int(v) for v in bbox]
    x1, x2 = max(0, x1), min(mask.shape[1], x2)
    y1, y2 = max(0, y1), min(mask.shape[0], y2)
    return float(mask[y1:y2, x1:x2].sum()/max(1, mask.sum())) if x2>x1 and y2>y1 else 0.0


def temporal_features(rows: list[dict], masks: dict, anchor_id: str, size: tuple[int, int]) -> dict:
    observed = []
    for row in rows:
        if not row["identity_authorized"] or not row["sam_phone"]:
            continue
        anchor = next((a for a in row["anchors"] if a["entity_id"] == anchor_id), None)
        if not anchor:
            continue
        rle = masks.get(str(row["frame"]))
        if rle is None:
            continue
        observed.append({"frame": row["frame"], "time": row["time"],
                         "area": row["sam_phone"]["area"],
                         "distance": _relative_distance(row["sam_phone"]["bbox"], anchor["bbox"], size),
                         "mask_containment": _mask_inside(rle, anchor["bbox"]),
                         "target_center": _center(row["sam_phone"]["bbox"]),
                         "anchor_center": _center(anchor["bbox"]),
                         "anchor_bbox": anchor["bbox"]})
    if not observed:
        return {"support_frames": 0, "sampled": [], "mask_available": False}
    first, last = observed[0], observed[-1]
    areas = [x["area"] for x in observed]
    contains = [x["mask_containment"] for x in observed]
    target_motion = [hypot(observed[i]["target_center"][0]-observed[i-1]["target_center"][0],
                           observed[i]["target_center"][1]-observed[i-1]["target_center"][1]) for i in range(1, len(observed))]
    anchor_motion = [hypot(observed[i]["anchor_center"][0]-observed[i-1]["anchor_center"][0],
                           observed[i]["anchor_center"][1]-observed[i-1]["anchor_center"][1]) for i in range(1, len(observed))]
    velocity_coupling = 0.0
    if target_motion and anchor_motion:
        velocity_coupling = sum(abs(t-a) <= max(10, .35*t) and t > 3 for t, a in zip(target_motion, anchor_motion))/len(target_motion)
    post = [r for r in rows if r["frame"] > last["frame"] and
            any(a["entity_id"] == anchor_id for a in r["anchors"])]
    post_without_target = [r for r in post if not r["identity_authorized"]]
    trend = last["mask_containment"]-first["mask_containment"]
    return {"support_frames": len(observed), "support_seconds": last["time"]-first["time"],
            "first_frame": first["frame"], "last_frame": last["frame"],
            "initial_distance": first["distance"], "final_distance": last["distance"],
            "distance_change": first["distance"]-last["distance"],
            "initial_containment": first["mask_containment"], "final_containment": last["mask_containment"],
            "containment_trend": trend, "max_containment": max(contains),
            "initial_mask_area": first["area"], "final_mask_area": last["area"],
            "visible_area_ratio": last["area"]/max(1, max(areas)),
            "area_change_fraction": (last["area"]-first["area"])/max(1, first["area"]),
            "target_motion_px": target_motion, "anchor_motion_px": anchor_motion,
            "velocity_coupling": velocity_coupling,
            "post_anchor_frames": len(post), "post_anchor_without_target": len(post_without_target),
            "target_disappears_after": len(post_without_target) >= 2,
            "mask_available": True,
            "sampled": [{k: x[k] for k in ("frame", "time", "area", "distance", "mask_containment")} for x in observed]}


def generate_candidates(task: str, event: dict, dense: dict, masks: dict,
                        size: tuple[int, int]) -> list[dict]:
    rows = dense["rows"]
    anchors = defaultdict(list)
    for row in rows:
        for anchor in row["anchors"]:
            if anchor["entity_id"] is not None:
                anchors[anchor["entity_id"]].append(anchor)
    candidates = []
    for anchor_id, seen in sorted(anchors.items()):
        label = seen[0]["label"]
        features = temporal_features(rows, masks, anchor_id, size)
        if features["support_frames"] < 2:
            continue
        for relation in compatible_relations(label):
            positive = ["trusted target and known anchor co-visible in dense window",
                        f"{features['support_frames']} frame mask support"]
            missing = []
            negative = []
            if features["distance_change"] > .03:
                positive.append("target approaches anchor")
            else:
                missing.append("clear approach transition")
            if features["containment_trend"] > .1:
                positive.append("target mask containment increases")
            else:
                missing.append("increasing mask containment")
            if features["visible_area_ratio"] < .7:
                positive.append("target visible mask area decreases")
            else:
                missing.append("visibility decrease")
            if features["target_disappears_after"]:
                positive.append("anchor remains after target observation ends")
            else:
                missing.append("anchor visible after target loss")
            if features["support_seconds"] < .25:
                negative.append("short temporal support")
            candidates.append({"candidate_id": f"PRC{len(candidates)+1:04d}", "task": task,
                               "event_id": event["event_id"], "target": "phone_01",
                               "anchor": anchor_id, "anchor_label": label,
                               "candidate_relation": relation, "window": [event["start_frame"], event["end_frame"]],
                               "start_frame": features["first_frame"], "end_frame": features["last_frame"],
                               "semantic_roles": semantic_roles(label), "features": features,
                               "positive_evidence": positive, "negative_evidence": negative,
                               "missing_evidence": missing,
                               "vlm_verification_required": relation != "NEAR" and features["support_frames"] >= 3
                                 and features["support_seconds"] >= .25 and
                                 (features["distance_change"] > .03 or features["containment_trend"] > .1 or
                                  features["visible_area_ratio"] < .7) and
                                 (relation != "HELD_BY" or features["velocity_coupling"] >= .5),
                               "provenance": [f"outputs_v29/{task}/dense_windows/{event['event_id']}/dense_observations.json",
                                              f"outputs_v29/{task}/dense_windows/{event['event_id']}/target_masks.json"]})
    return candidates
