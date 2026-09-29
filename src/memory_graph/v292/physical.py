"""Pair-specific geometry and evidence adapter for the unchanged V2.9 relation gate."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from memory_graph.v29.physical_gate import decide as v29_decide


def ordered_boundary_transition(rows: list[dict], anchor_key: str) -> dict[str, Any]:
    states = []
    for row in sorted(rows, key=lambda x: x["frame"]):
        anchor = next((a for a in row.get("anchors", []) if a.get("anchor_key") == anchor_key), None)
        target = row.get("target_bbox") if row.get("target_authorized") else None
        if not anchor or not target:
            continue
        ax1, ay1, ax2, ay2 = anchor["bbox"]
        cx, cy = (target[0]+target[2])/2, (target[1]+target[3])/2
        inside = ax1 <= cx <= ax2 and ay1 <= cy <= ay2
        states.append({"frame": row["frame"], "inside": inside, "contact": bool(row.get("contact")),
                       "visible": True})
    outside_before = any(not x["inside"] for x in states[:-1])
    boundary_contact = any(x["contact"] for x in states)
    inside_after = bool(states and states[-1]["inside"])
    return {"outside_before": outside_before, "boundary_contact_transition": boundary_contact,
            "inside_or_occluded_after": inside_after,
            "ordered": outside_before and boundary_contact and inside_after,
            "support_frames": [x["frame"] for x in states]}


def relation_verification(candidate: dict, observable: dict | None,
                          grounding: dict | None) -> dict[str, Any]:
    """Facts support/contradict a proposed relation; the VLM never supplies relation labels."""
    relation = candidate["candidate_relation"]
    if not grounding or not grounding.get("grounding_valid") or not observable:
        return {"status": "UNUSABLE_GROUNDING", "structured_output": None}
    facts = observable
    if relation == "NEAR":
        return {"status": "NOT_REQUIRED", "structured_output": None}
    positive = facts.get("target_contacts_or_crosses_anchor_boundary") == "YES"
    visible_loss = facts.get("target_visible_area_decreases") == "YES"
    remains = facts.get("anchor_remains_visible") == "YES"
    released = facts.get("hand_or_person_releases_target") == "YES"
    stays = facts.get("target_stays_after_release") == "YES"
    moves = facts.get("target_moves_toward_anchor") == "YES"
    transition = candidate.get("ordered_boundary_transition", {}).get("ordered", False)
    relation_fact = {
        "INSIDE": positive and visible_loss and remains and transition,
        "ON": positive and moves and (released and stays or remains),
        "BEHIND": positive and visible_loss and remains and transition,
        "OCCLUDED_BY": positive and visible_loss and remains and transition,
        "HELD_BY": positive and moves and facts.get("target_visible_during") == "YES",
    }.get(relation, False)
    output = {"relation": relation if relation_fact else "NONE", "confidence": .85 if relation_fact else 0.,
              "temporal_evidence": f"Pair-grounded observable facts for {relation}; ordered geometry={transition}.",
              "visual_evidence": " ; ".join(f"{key}={facts.get(key)}" for key in
                    ("target_moves_toward_anchor", "target_contacts_or_crosses_anchor_boundary",
                     "target_visible_area_decreases", "anchor_remains_visible",
                     "hand_or_person_releases_target", "target_stays_after_release")),
              "uncertainty": "LOW" if relation_fact else "UNCERTAIN"}
    return {"status": "VALID", "structured_output": output,
            "fact_to_relation_adapter": "V292_RELATION_SPECIFIC_OBSERVABLE_RULES"}


def gate(candidate: dict, observable: dict | None = None,
         grounding: dict | None = None) -> dict[str, Any]:
    adapted = deepcopy(candidate)
    adapted["ordered_boundary_transition"] = ordered_boundary_transition(
        adapted.get("rows", []), adapted.get("anchor"))
    verification = relation_verification(adapted, observable, grounding)
    legacy_candidate = {k: deepcopy(adapted[k]) for k in (
        "candidate_id", "event_id", "candidate_relation", "target", "anchor", "start_frame", "end_frame",
        "semantic_roles", "features", "positive_evidence", "negative_evidence", "missing_evidence", "provenance")
        if k in adapted}
    result = v29_decide(legacy_candidate, verification)
    result["provenance"] = [p.replace("outputs_v29", "outputs_v292") for p in result.get("provenance", [])]
    result["identity_authorized"] = candidate.get("identity_authorized") is True
    if not result["identity_authorized"]:
        result["decision"] = "REJECTED"
        result["final_reason"] = "Target identity evidence is not authorized"
    result["grounding"] = grounding
    result["observable_fact_status"] = "GROUNDED" if grounding and grounding.get("grounding_valid") else "UNUSABLE_GROUNDING"
    return result
