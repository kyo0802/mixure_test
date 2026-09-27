"""Conservative promotion with explicit, causal physical evidence."""
from __future__ import annotations

from .models import Config, EntityObservation, PHYSICAL, RelationCandidate
from .relevance import supported


def valid_assertions(target: EntityObservation, anchor: EntityObservation,
                     evidence: list[dict], config: Config) -> list[dict]:
    if not target.trusted or target.entity_id != config.target_id or not anchor.trusted:
        return []
    return [e for e in evidence
            if e.get("subject") == target.entity_id and e.get("object") == anchor.entity_id
            and e.get("relation") in PHYSICAL
            and e.get("source_kind") in {"interaction", "verified_event", "vlm"}
            and e.get("independent_physical_support") is True
            and e.get("confidence", 0) >= config.physical_evidence_confidence
            and 0 <= target.frame - e.get("frame", target.frame + 1)
            and 0 <= target.time - e.get("time", target.time + 1) <= config.maximum_support_gap_seconds
            and e.get("source_ref")]


def promote(candidate: RelationCandidate, target: EntityObservation, config: Config) -> bool:
    if not target.trusted or target.entity_id != config.target_id or not supported(candidate, config):
        return False
    if candidate.relation not in PHYSICAL:
        return False
    # Repeated 2D boxes alone never qualify. Multiple distinct physical evidence frames are required.
    frames = {e["frame"] for e in candidate.evidence if e.get("independent_physical_support") is True}
    return len(frames) >= config.minimum_support_frames
