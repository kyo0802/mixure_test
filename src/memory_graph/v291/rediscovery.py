"""Identity-gated post-loss phone proposals; this module never authors aliases."""
from __future__ import annotations


def propose_rediscovery(task: str, stream: dict, identity_timeline: dict,
                        reid_audit: dict, sam_support: dict | None = None) -> dict:
    timeline = identity_timeline.get("phone_timeline", [])
    trusted = [r["frame_index"] for r in timeline if r.get("state") in {"VISIBLE_TRUSTED", "MATCHED"}]
    last = max(trusted, default=-1)
    score_rows = {}
    for attempt in reid_audit.get("attempts", []):
        for decision in attempt.get("candidate_decisions", []):
            cid = decision.get("candidate_entity_id")
            score_rows.setdefault((cid, attempt["frame_index"]), decision)
    sam_cids = {row.get("candidate_id") for row in (sam_support or {}).get("candidate_support", [])
                if row.get("status") == "SEEDED"}
    result = []
    for row in stream.get("observations", []):
        frame = row["frame_index"]
        cid = row.get("candidate_id")
        if not cid or frame <= last:
            continue
        reid = row.get("reid_decision")
        exact = score_rows.get((cid, frame))
        sim = exact.get("appearance", {}).get("max_similarity") if exact else None
        if reid in {"CONFIRMED_MATCH", "MATCH"}:
            decision = "CONFIRMED"
            reason = "existing V2.6 Identity Guard authorized this candidate at the observed frame"
        elif reid in {"PROVISIONAL_MATCH"}:
            decision, reason = "PROVISIONAL", "V2.6 classified candidate provisional; no PersistentEntity update"
        elif reid in {"AMBIGUOUS", "NOT_EVALUATED", "NO_SAFE_MATCH", None}:
            decision, reason = "AMBIGUOUS", "candidate proposal lacks a frozen Identity Guard confirmation"
        elif reid in {"REJECTED", "REJECT"}:
            decision, reason = "REJECTED", "frozen Identity Guard rejected candidate"
        else:
            decision, reason = "AMBIGUOUS", f"unrecognized identity state {reid}"
        mask_ref = f"sam_candidate:{cid}:f{frame}" if cid in sam_cids else None
        result.append({"candidate_id": cid, "frame": frame, "source": "YOLO_PHONE_CANDIDATE",
                       "box_or_mask": row.get("bbox"), "mask_reference": mask_ref,
                       "appearance_similarity": sim, "context_consistency": None,
                       "identity_decision": decision, "reason": reason,
                       "memory_update_authorized": decision == "CONFIRMED",
                       "provenance": [f"candidate_stream#{frame}:{cid}", "outputs_v26/reid_audit.json"]})
    return {"schema": "v291_rediscovery_1", "task": task, "last_trusted_frame": last,
            "candidates": result,
            "counts": {key: sum(c["identity_decision"] == key for c in result)
                       for key in ("CONFIRMED", "PROVISIONAL", "AMBIGUOUS", "REJECTED")},
            "backward_authorization": False,
            "policy": "only frozen Identity Guard decisions can authorize forward memory updates"}
