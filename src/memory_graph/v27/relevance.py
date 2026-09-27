"""Admit stable image localization context, not every co-visible scene object."""
from __future__ import annotations

from .models import Config, EntityObservation, RelationCandidate, RelationObservation

SUPPORT = {"table", "dining table", "counter", "shelf", "box", "container", "couch", "sofa", "bed"}
LOCATORS = {"microwave", "refrigerator", "teddy bear", "sports ball", "bottle", "potted plant", "tv"}


def eligible(anchor: EntityObservation, relations: list[RelationObservation], explicit_relation: bool = False) -> bool:
    if not anchor.trusted:
        return False
    if explicit_relation:
        return True
    return anchor.label in SUPPORT | LOCATORS and any(r.relation == "IMAGE_NEAR" for r in relations)


def supported(candidate: RelationCandidate, config: Config) -> bool:
    return (len(candidate.support_frames) >= config.minimum_support_frames
            and candidate.support_times[-1] - candidate.support_times[0] >= config.minimum_support_seconds)


def context_order(anchor: EntityObservation, relations: list[RelationObservation]) -> tuple:
    metrics = relations[0].metrics
    return (0 if anchor.label in SUPPORT else 1, metrics["box_gap_fraction"],
            metrics["center_distance_fraction"], anchor.entity_id)
