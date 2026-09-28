"""Deterministic relation hypotheses from measurable facts plus observable VLM facts."""
from __future__ import annotations


def infer_candidates(event: dict, anchors: list[dict], dense: dict,
                     vlm_rows: list[dict]) -> list[dict]:
    facts = {v["anchor_id"]: v.get("observable_facts") for v in vlm_rows if v.get("status") == "VALID"}
    rows = dense.get("rows", [])
    target = [r for r in rows if r.get("identity_authorized") and r.get("sam_phone")]
    output = []
    for anchor in anchors:
        if not anchor["trusted_for_physical_reasoning"]:
            continue
        related = [r for r in rows if any(a["anchor_id"] == anchor["anchor_id"] for a in r.get("recovered_anchors", []))]
        co = [r for r in target if any(a.get("anchor_id") == anchor["anchor_id"] for a in r.get("recovered_anchors", []))]
        if len(co) < 3:
            continue
        labels = set(anchor["semantic_role"])
        obs = facts.get(anchor["anchor_id"]) or {}
        matched_anchor_rows = [a for r in co for a in r.get("recovered_anchors", [])
                               if a.get("anchor_id") == anchor["anchor_id"]]
        approaches = any(a.get("target_approach", False) for a in matched_anchor_rows)
        visibility_loss = any(a.get("mask_area_decrease", False) for a in matched_anchor_rows)
        boundary = any(a.get("boundary_crossing", False) for a in matched_anchor_rows)
        anchor_remains = any(r.get("anchor_visible_after", False) for r in related)
        disappeared = any(not r.get("identity_authorized") and r["frame"] >= event["peak_frame"]
                          for r in rows)
        candidate_relations = []
        if "CONTAINER" in labels and approaches and boundary and visibility_loss and anchor_remains and disappeared:
            candidate_relations.append("INSIDE")
        if "SUPPORT" in labels and approaches and any(a.get("target_stable", False) for a in matched_anchor_rows) and obs.get("hand_or_person_releases_target") == "YES":
            candidate_relations.append("ON")
        if "OCCLUDER" in labels and approaches and visibility_loss and anchor_remains:
            candidate_relations.extend(["OCCLUDED_BY", "BEHIND"])
        if "INTERACTION_AGENT" in labels and obs.get("hand_or_person_releases_target") == "NO":
            candidate_relations.append("HELD_BY")
        if len(co) >= 3:
            candidate_relations.append("NEAR")
        for relation in dict.fromkeys(candidate_relations):
            positive, missing = [], []
            if approaches: positive.append("dense target geometry approaches anchor")
            else: missing.append("approach sequence")
            if boundary: positive.append("mask boundary transition")
            else: missing.append("mask crossing/entry evidence")
            if visibility_loss: positive.append("trusted mask visible area decreases")
            else: missing.append("target visibility loss")
            if anchor_remains: positive.append("anchor remains detected after target change")
            else: missing.append("anchor persistence")
            if not obs: missing.append("observable VLM facts")
            output.append({"candidate_id": f"V291PR{len(output)+1:03d}",
                           "event_id": event["event_id"], "target": "phone_01",
                           "anchor": anchor["anchor_id"], "anchor_scope": anchor.get("scope", "PERSISTENT"),
                           "candidate_relation": relation, "positive_evidence": positive,
                           "missing_evidence": missing,
                           "observable_facts": obs,
                           "identity_authorized": bool(co),
                           "decision": "CANDIDATE" if relation == "NEAR" or obs else "UNCERTAIN",
                           "reason": "observable facts support further review; the VLM cannot directly choose or promote a relation"})
    return output


def gate(candidate: dict) -> dict:
    facts = candidate.get("observable_facts") or {}
    relation = candidate["candidate_relation"]
    enough = candidate["identity_authorized"] and len(candidate["positive_evidence"]) >= 2
    decision = "CANDIDATE" if enough else "UNCERTAIN"
    if relation == "INSIDE":
        required = (facts.get("target_moves_toward_anchor") == "YES" and
                    facts.get("target_contacts_or_crosses_anchor_boundary") == "YES" and
                    facts.get("target_visible_area_decreases") == "YES" and
                    facts.get("anchor_remains_visible") == "YES" and
                    facts.get("target_visible_after") == "NO")
        if not required:
            decision = "UNCERTAIN"
    elif relation == "BEHIND":
        required = (facts.get("target_moves_toward_anchor") == "YES" and
                    facts.get("target_visible_area_decreases") == "YES" and
                    facts.get("anchor_remains_visible") == "YES")
        if not required:
            decision = "UNCERTAIN"
    # V2.9 promotion thresholds remain in force; the new observable adapter
    # cannot promote by itself. Safe candidates remain explicitly unconfirmed.
    return {**candidate, "decision": decision, "physical_promotion": False,
            "gate_evidence": {"identity": candidate["identity_authorized"],
                              "observable_facts_complete": bool(facts),
                              "relation_specific": decision == "CANDIDATE"}}
