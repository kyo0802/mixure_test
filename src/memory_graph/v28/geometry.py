"""Projection geometry and temporal trends. These features are not physical truth."""
from __future__ import annotations

from math import hypot
from statistics import mean


def _area(box: list[float]) -> float:
    return max(1.0, (box[2] - box[0]) * (box[3] - box[1]))


def _center(box: list[float]) -> tuple[float, float]:
    return (box[0] + box[2]) / 2, (box[1] + box[3]) / 2


def bbox_features(target: list[float], anchor: list[float], size: tuple[int, int]) -> dict:
    tx, ty = _center(target)
    ax, ay = _center(anchor)
    iw = max(0.0, min(target[2], anchor[2]) - max(target[0], anchor[0]))
    ih = max(0.0, min(target[3], anchor[3]) - max(target[1], anchor[1]))
    intersection = iw * ih
    target_area, anchor_area = _area(target), _area(anchor)
    union = target_area + anchor_area - intersection
    diagonal = max(1.0, hypot(*size))
    gap_x = max(anchor[0] - target[2], target[0] - anchor[2], 0.0)
    gap_y = max(anchor[1] - target[3], target[1] - anchor[3], 0.0)
    aw, ah = max(1.0, anchor[2] - anchor[0]), max(1.0, anchor[3] - anchor[1])
    return {
        "bbox_iou": intersection / max(1.0, union),
        "containment_ratio": intersection / target_area,
        "target_center_relative_to_anchor": [(tx - anchor[0]) / aw, (ty - anchor[1]) / ah],
        "normalized_center_distance": hypot(tx - ax, ty - ay) / diagonal,
        "box_gap_fraction": hypot(gap_x, gap_y) / diagonal,
        "x_overlap_ratio": iw / max(1.0, min(target[2] - target[0], aw)),
        "y_overlap_ratio": ih / max(1.0, min(target[3] - target[1], ah)),
        "target_bottom_minus_anchor_top": (target[3] - anchor[1]) / max(1.0, size[1]),
        "relative_size": target_area / anchor_area,
        "target_bbox_area_fraction": target_area / max(1.0, size[0] * size[1]),
        "anchor_bbox_area_fraction": anchor_area / max(1.0, size[0] * size[1]),
        "mask_evidence_available": False,
    }


def _trend(values: list[float]) -> float:
    return 0.0 if len(values) < 2 else values[-1] - values[0]


def _velocity(boxes: list[list[float]], times: list[float], size: tuple[int, int]) -> float:
    if len(boxes) < 2 or times[-1] <= times[0]:
        return 0.0
    a, b = _center(boxes[0]), _center(boxes[-1])
    return hypot(b[0] - a[0], b[1] - a[1]) / max(1.0, hypot(*size)) / (times[-1] - times[0])


def temporal_summary(observations: list[dict], size: tuple[int, int]) -> dict:
    features = [bbox_features(row["target_bbox"], row["anchor_bbox"], size) for row in observations]
    times = [row["time"] for row in observations]
    tboxes = [row["target_bbox"] for row in observations]
    aboxes = [row["anchor_bbox"] for row in observations]
    distances = [f["normalized_center_distance"] for f in features]
    overlaps = [f["containment_ratio"] for f in features]
    areas = [f["target_bbox_area_fraction"] for f in features]
    target_velocity = _velocity(tboxes, times, size)
    anchor_velocity = _velocity(aboxes, times, size)
    relative = abs(target_velocity - anchor_velocity)
    return {
        "frame_features": features,
        "mean_iou": mean(f["bbox_iou"] for f in features),
        "mean_containment": mean(overlaps),
        "final_containment": overlaps[-1],
        "containment_trend": _trend(overlaps),
        "mean_distance": mean(distances),
        "final_distance": distances[-1],
        "distance_trend": _trend(distances),
        "overlap_trend": _trend(overlaps),
        "visibility_ratio_proxy_trend": _trend(areas),
        "target_velocity": target_velocity,
        "anchor_velocity": anchor_velocity,
        "trajectory_velocity_delta": relative,
        "trajectory_sync_proxy": max(0.0, 1.0 - relative / max(target_velocity, anchor_velocity, 0.02)),
        "final_target_bottom_minus_anchor_top": features[-1]["target_bottom_minus_anchor_top"],
        "final_x_overlap": features[-1]["x_overlap_ratio"],
        "support_frames": len(observations),
        "support_seconds": times[-1] - times[0] if len(times) > 1 else 0.0,
        "mask_evidence_available": any(row.get("target_mask_ref") for row in observations),
    }
