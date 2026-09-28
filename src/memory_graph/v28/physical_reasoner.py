"""Relation-specific temporal patterns and conservative evidence gates."""
from __future__ import annotations

from .geometry import temporal_summary
from .models import Config, PhysicalRelationCandidate, SpatialSegment
from .roles import compatible_relations


def _vlm(segment: SpatialSegment) -> dict:
    supplied = [row.get("vlm_evidence") for row in segment.observations if row.get("vlm_evidence")]
    return supplied[-1] if supplied else {"status": "NOT_RUN", "relation": None, "confidence": None,
                                         "evidence": None,
                                         "uncertainty": "No cached candidate-scoped VLM evidence; no model download permitted"}


def reason_relation(segment: SpatialSegment, relation: str, size: tuple[int, int],
                    config: Config | None = None, candidate_id: str = "PRC0001") -> PhysicalRelationCandidate:
    config = config or Config()
    geometry = temporal_summary(segment.observations, size)
    roles = set(segment.semantic_roles)
    vlm = _vlm(segment)
    vlm_support = (vlm.get("status") == "VALID" and vlm.get("relation") == relation
                   and (vlm.get("confidence") or 0) >= config.vlm_promotion_confidence)
    independent = any(row.get("independent_physical_support") is True for row in segment.observations)
    interaction = any(row.get("interaction_evidence") is True for row in segment.observations)
    remains_unobserved = any(row.get("remains_unobserved") is True for row in segment.observations)
    disappears = any(row.get("target_disappears_after") is True for row in segment.observations)
    reappears = any(row.get("reappeared_consistently") is True for row in segment.observations)
    identity_ok = all(row.get("target_identity") in {"TRUSTED", "CONFIRMED", "CONFIRMED_MATCH"}
                      for row in segment.observations)
    multi = geometry["support_frames"] >= config.minimum_support_frames and geometry["support_seconds"] >= config.minimum_support_seconds
    decision, reason = "REJECTED", "Relation-specific temporal pattern is absent"
    pattern = False
    if relation == "NEAR":
        pattern = multi and geometry["mean_distance"] <= config.primary_local_distance_fraction
        if pattern:
            decision, reason = "CANDIDATE", "Stable multi-frame image proximity; depth is unverified"
            if independent or vlm_support:
                decision, reason = "PROMOTED", "Stable proximity plus independent physical or VLM support"
    elif relation == "HELD_BY" and "INTERACTION_AGENT" in roles:
        pattern = (multi and geometry["mean_distance"] <= .18 and geometry["trajectory_sync_proxy"] >= .80
                   and geometry["target_velocity"] >= .01)
        if pattern:
            decision, reason = "CANDIDATE", "Phone and interaction agent remain close and move synchronously"
            if interaction and (independent or vlm_support):
                decision, reason = "PROMOTED", "Synchronous motion plus explicit interaction evidence"
    elif relation == "ON" and "SUPPORT" in roles:
        pattern = (multi and geometry["final_x_overlap"] >= .45
                   and abs(geometry["final_target_bottom_minus_anchor_top"]) <= .12
                   and geometry["final_distance"] <= .25)
        if pattern:
            decision, reason = "CANDIDATE", "Target settles over a support-compatible anchor"
            if independent or vlm_support:
                decision, reason = "PROMOTED", "Stable final support placement plus independent evidence"
    elif relation == "INSIDE" and "CONTAINER" in roles:
        pattern = multi and (geometry["containment_trend"] >= .20 or geometry["final_containment"] >= .65)
        if pattern:
            decision, reason = "CANDIDATE", "Containment increases within a container-compatible anchor"
            if geometry["final_containment"] >= .65 and (geometry["mask_evidence_available"] or independent or vlm_support):
                decision, reason = "PROMOTED", "Temporal entry and strong independently supported containment"
    elif relation == "OCCLUDED_BY" and "OCCLUDER" in roles:
        pattern = (multi and disappears and (geometry["overlap_trend"] >= .10 or geometry["final_containment"] >= .30)
                   and geometry["visibility_ratio_proxy_trend"] < 0)
        if pattern:
            decision, reason = "CANDIDATE", "Overlap grows while target visibility proxy falls before disappearance"
            if reappears and (independent or vlm_support):
                decision, reason = "PROMOTED", "Temporary visibility event is independently supported by consistent reappearance"
    elif relation == "BEHIND" and "OCCLUDER" in roles:
        pattern = (multi and disappears and remains_unobserved
                   and (geometry["overlap_trend"] >= .10 or geometry["final_containment"] >= .30)
                   and geometry["visibility_ratio_proxy_trend"] < 0)
        if pattern:
            decision, reason = "CANDIDATE", "Last context supports a possible behind-placement, but 2D evidence is ambiguous"
            if independent or vlm_support:
                decision, reason = "PROMOTED", "Behind-placement temporal pattern has additional independent semantic support"
    if not identity_ok:
        decision, reason = "REJECTED", "Target identity is not trusted throughout the segment"
    elif not multi:
        decision, reason = "UNCERTAIN", "Insufficient distinct-frame temporal support"
    return PhysicalRelationCandidate(
        candidate_id, segment.subject, segment.object, relation, segment.start_frame, segment.end_frame,
        "TRUSTED" if identity_ok else "UNAUTHORIZED", geometry,
        {"multi_frame_support": multi, "pattern_present": pattern, "target_disappears_after": disappears,
         "remains_unobserved": remains_unobserved, "reappeared_consistently": reappears,
         "interaction_evidence": interaction, "independent_physical_support": independent},
        {"raw_label": segment.raw_label, "semantic_roles": segment.semantic_roles,
         "relation_compatible": relation in compatible_relations(segment.raw_label)},
        vlm, decision, reason,
        sorted({ref for row in segment.observations for ref in
                (row.get("target_observation"), row.get("anchor_observation")) if ref}),
        segment_id=segment.segment_id)


def reason_all(primary_segments: list[dict], size: tuple[int, int], config: Config | None = None) -> list[PhysicalRelationCandidate]:
    config = config or Config()
    results = []
    for raw in primary_segments:
        segment = SpatialSegment(**raw)
        for relation in compatible_relations(segment.raw_label):
            results.append(reason_relation(segment, relation, size, config, f"PRC{len(results)+1:04d}"))
    return results
