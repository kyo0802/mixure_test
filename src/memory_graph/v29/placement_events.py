"""Generic, label-blind placement window discovery from trusted trajectories."""
from __future__ import annotations

from math import hypot


def _center(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def _distance(a, b, size):
    x, y = _center(a), _center(b)
    return hypot((x[0]-y[0])/size[0], (x[1]-y[1])/size[1])


def _overlap(a, b):
    x = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    y = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area = max(1, (a[2]-a[0])*(a[3]-a[1]))
    return x*y/area


def _target(row, masks):
    trusted = [o for o in row["observations"] if o.entity_id == "phone_01" and o.trusted]
    if trusted:
        return trusted[-1].bbox, trusted[-1].observation_id
    mask = masks.get(row["frame"])
    if mask and mask["trusted"]:
        return mask["mask_bbox"], mask["mask_reference"]
    return None, None


def detect_events(frames: list[dict], masks: list[dict], size: tuple[int, int], fps: float,
                  max_events: int = 3) -> list[dict]:
    """Use disappearance only as one cue, then require a second interaction cue."""
    mask_by_frame = {r["frame"]: r for r in masks if r["trusted"]}
    target_rows = []
    for i, row in enumerate(frames):
        box, ref = _target(row, mask_by_frame)
        if box:
            target_rows.append((i, row, box, ref))
    proposals = []
    for pos, (index, row, box, ref) in enumerate(target_rows):
        next_row = frames[index+1] if index+1 < len(frames) else None
        if next_row is None or _target(next_row, mask_by_frame)[0] is not None:
            continue
        # Another trusted frame immediately after a single miss prevents a false
        # final-loss event. This check uses only the frozen identity timeline.
        if index+2 < len(frames) and _target(frames[index+2], mask_by_frame)[0] is not None:
            continue
        recent = target_rows[max(0, pos-4):pos+1]
        nearby = []
        for anchor in row["anchors"]:
            if anchor.entity_id == "phone_01" or anchor.label == "cell phone":
                continue
            d = _distance(box, anchor.bbox, size)
            if d <= .35:
                nearby.append((d, anchor))
        nearby.sort(key=lambda x: x[0])
        near = nearby[:3]
        mask_areas = [mask_by_frame[r["frame"]]["mask_area"] for _, r, _, _ in recent if r["frame"] in mask_by_frame]
        visibility_loss = len(mask_areas) >= 3 and mask_areas[-1] < .65*max(mask_areas[:-1])
        overlap = any(_overlap(box, a.bbox) > .08 for _, a in near)
        approach = False
        if near and len(recent) >= 3:
            anchor_id = near[0][1].entity_id
            distances = []
            for _, old_row, old_box, _ in recent:
                same = next((a for a in old_row["anchors"] if a.entity_id == anchor_id), None)
                if same:
                    distances.append(_distance(old_box, same.bbox, size))
            approach = len(distances) >= 3 and distances[0]-distances[-1] >= .035
        motion_slowdown = False
        if len(recent) >= 3:
            speeds = [_distance(recent[j-1][2], recent[j][2], size) for j in range(1, len(recent))]
            motion_slowdown = len(speeds) >= 2 and speeds[-1] < .6*max(speeds[:-1]) and max(speeds[:-1]) > .008
        anchor_remains = False
        if near and next_row:
            ids = {a.entity_id for a in next_row["anchors"]}
            anchor_remains = any(a.entity_id in ids for _, a in near)
        cues = {"motion_slowdown": motion_slowdown, "anchor_approach": approach,
                "overlap_increase": overlap, "visibility_loss": visibility_loss,
                "target_disappearance": True, "anchor_remains_visible": anchor_remains,
                "hand_release": False}
        independent = sum((bool(near), visibility_loss, overlap, approach, motion_slowdown, anchor_remains))
        if independent < 1:
            continue
        strength = "HIGH" if independent >= 3 else "MEDIUM" if independent == 2 else "LOW"
        peak = row["frame"]
        # Clip to the sampled video span; 1.5 seconds before and after loss.
        radius = round(1.5*fps)
        start = max(frames[0]["frame"], peak-radius)
        end = min(frames[-1]["frame"], peak+radius)
        proposals.append({"event_id": "", "target": "phone_01", "start_frame": start,
                          "peak_frame": peak, "end_frame": end,
                          "start_time": start/fps, "end_time": end/fps,
                          "event_type": "POSSIBLE_PLACEMENT",
                          "candidate_anchors": [{"entity_id": a.entity_id, "raw_label": a.label,
                                                  "distance_fraction": round(d, 4), "bbox": a.bbox,
                                                  "source": a.observation_id} for d, a in near],
                          "cues": cues, "evidence_strength": strength,
                          "reason": f"Trusted target loss with {independent} independent interaction cues",
                          "provenance": [ref, f"outputs_v26/identity_timeline.json#{peak}"]})
    # Favour late, strongly cued transitions but avoid overlapping windows.
    proposals.sort(key=lambda e: (-sum(e["cues"].values()), -e["peak_frame"]))
    chosen = []
    for event in proposals:
        if any(abs(event["peak_frame"]-old["peak_frame"]) < fps*2 for old in chosen):
            continue
        chosen.append(event)
        if len(chosen) == max_events:
            break
    chosen.sort(key=lambda x: x["peak_frame"])
    for i, event in enumerate(chosen, 1):
        event["event_id"] = f"PE{i:04d}"
    return chosen
