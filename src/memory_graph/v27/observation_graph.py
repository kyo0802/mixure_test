"""2D image geometry; no function here asserts physical spatial relations."""
from __future__ import annotations

from math import hypot

from .models import EntityObservation, RelationObservation


def image_relations(target: EntityObservation, anchor: EntityObservation,
                    size: tuple[int, int], near_fraction: float) -> list[RelationObservation]:
    a, b = target.bbox, anchor.bbox
    ax, ay = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
    bx, by = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    gap = hypot(max(b[0] - a[2], a[0] - b[2], 0), max(b[1] - a[3], a[1] - b[3], 0))
    diagonal = max(1, hypot(*size))
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area = max(1, (a[2] - a[0]) * (a[3] - a[1]))
    metrics = {"box_gap_fraction": gap / diagonal, "target_overlap_fraction": intersection / area,
               "center_distance_fraction": hypot(ax - bx, ay - by) / diagonal,
               "physical_verification": False}
    names = ["IMAGE_LEFT_OF" if ax < bx else "IMAGE_RIGHT_OF", "IMAGE_ABOVE" if ay < by else "IMAGE_BELOW"]
    if gap / diagonal <= near_fraction:
        names.append("IMAGE_NEAR")
    if intersection > 0:
        names.append("IMAGE_OVERLAP")
    return [RelationObservation(target.entity_id or target.source_id, name, anchor.entity_id,
                                target.frame, target.time, "image_relative", [target.observation_id, anchor.observation_id],
                                dict(metrics)) for name in names]
