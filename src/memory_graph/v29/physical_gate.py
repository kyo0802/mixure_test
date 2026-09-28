"""Relation-specific physical evidence gates; VLM never owns identity or memory."""
from __future__ import annotations


def decide(candidate: dict, verification: dict | None = None) -> dict:
    f = candidate["features"]
    relation = candidate["candidate_relation"]
    roles = set(candidate["semantic_roles"])
    verification = verification or {"status": "NOT_RUN", "structured_output": None}
    output = verification.get("structured_output") or {}
    rationale = [str(output.get(k, "")) for k in ("temporal_evidence", "visual_evidence")]
    substantive = all(len(value) >= 20 and not value.lstrip().startswith("[") for value in rationale)
    uncertainty = str(output.get("uncertainty", "")).strip().upper()
    vlm_support = (verification.get("status") == "VALID" and output.get("relation") == relation
                   and output.get("confidence", 0) >= .8 and substantive
                   and uncertainty not in {"UNCERTAIN", "HIGH", "UNKNOWN"})
    vlm_contradiction = verification.get("status") == "VALID" and output.get("relation") == "NONE"
    identity = f["support_frames"] >= 2 and f["mask_available"]
    temporal = f.get("support_frames", 0) >= 3 and f.get("support_seconds", 0) >= .25
    approach = f.get("distance_change", 0) >= .03
    overlap_growth = f.get("containment_trend", 0) >= .12
    high_overlap = f.get("final_containment", 0) >= .45
    visibility_loss = f.get("visible_area_ratio", 1) <= .65
    disappears = f.get("target_disappears_after", False)
    anchor_after = f.get("post_anchor_without_target", 0) >= 2
    geometry = approach or overlap_growth or high_overlap
    mask = overlap_growth or visibility_loss
    semantic = relation == "NEAR" or (
        relation == "INSIDE" and "CONTAINER" in roles or
        relation == "ON" and "SUPPORT" in roles or
        relation in {"BEHIND", "OCCLUDED_BY"} and "OCCLUDER" in roles or
        relation == "HELD_BY" and "INTERACTION_AGENT" in roles)
    pattern = False
    strong = False
    reason = "Relation-specific transition absent"
    if relation == "NEAR":
        pattern = temporal and f.get("final_distance", 1) <= .30
        reason = "2D proximity remains unconfirmed physical context"
    elif relation == "INSIDE":
        pattern = temporal and approach and overlap_growth and visibility_loss and disappears and anchor_after
        strong = pattern and f.get("final_containment", 0) >= .65 and vlm_support
        reason = "Entry, visibility loss, anchor persistence and independent confirmation required"
    elif relation == "ON":
        motion = f.get("target_motion_px", [])
        settled = len(motion) >= 3 and max(motion[-2:]) < .4*max(motion[:-2], default=0)
        pattern = temporal and approach and settled and not visibility_loss and f.get("final_containment", 0) >= .25
        strong = pattern and anchor_after and vlm_support
        reason = "Stable support placement and independent confirmation required"
    elif relation == "OCCLUDED_BY":
        pattern = temporal and overlap_growth and visibility_loss and disappears and anchor_after
        strong = pattern and vlm_support and high_overlap
        reason = "Ordered overlap then mask visibility loss required; detector miss is insufficient"
    elif relation == "BEHIND":
        pattern = temporal and approach and overlap_growth and visibility_loss and disappears and anchor_after
        strong = pattern and vlm_support and f.get("final_containment", 0) >= .65
        reason = "Behind placement requires stronger evidence than temporary occlusion"
    elif relation == "HELD_BY":
        pattern = temporal and f.get("velocity_coupling", 0) >= .8 and f.get("final_distance", 1) <= .15
        strong = pattern and vlm_support
        reason = "Sustained contact and target/agent motion coupling required"
    if not identity or not semantic:
        decision = "REJECTED"
        reason = "Identity or semantic role gate failed"
    elif not temporal:
        decision = "UNCERTAIN"
        reason = "Insufficient distinct-frame trusted temporal support"
    elif vlm_contradiction and relation != "NEAR":
        decision = "REJECTED"
        reason = "Candidate-scoped VLM reports no physical relation or is uncertain"
    elif strong:
        decision = "PROMOTED"
        reason = "All relation-specific temporal, mask, semantic, and independent visual gates passed"
    elif pattern or relation == "NEAR" and geometry:
        decision = "CANDIDATE"
    else:
        decision = "UNCERTAIN"
    missing = list(candidate["missing_evidence"])
    if relation != "NEAR" and not vlm_support:
        missing.append("independent VLM verification")
    return {"candidate_id": candidate["candidate_id"], "event_id": candidate["event_id"],
            "candidate_relation": relation, "target": candidate["target"], "anchor": candidate["anchor"],
            "start_frame": candidate["start_frame"], "end_frame": candidate["end_frame"],
            "decision": decision, "identity_gate": identity, "geometry_gate": geometry,
            "mask_gate": mask, "temporal_gate": temporal and pattern, "semantic_gate": semantic,
            "vlm_gate": {"status": verification.get("status", "NOT_RUN"), "support": vlm_support,
                         "rationale_substantive": substantive,
                         "contradiction": vlm_contradiction},
            "positive_evidence": candidate["positive_evidence"],
            "negative_evidence": candidate["negative_evidence"],
            "missing_evidence": missing, "final_reason": reason,
            "provenance": candidate["provenance"]}
