"""Eligibility-aware, event-local exploratory evaluation without global metrics."""
from __future__ import annotations

from .common import Phase2BBlocked


FORBIDDEN_METRICS = ["accuracy", "precision", "recall", "F1", "hallucination_rate", "significance", "superiority", "generalization"]


def _prediction_interval(event: dict, private_mapping: list[dict]) -> tuple[float, float] | None:
    lookup = {row["opaque_alias"]: row.get("source_timestamp_s", row.get("native_source_timestamp_s")) for row in private_mapping}
    if any(value is None for value in lookup.values()):
        raise Phase2BBlocked("PRIVATE_TIME_MAPPING_INCOMPLETE")
    timing = event["timing"]
    if timing["status"] == "TIMING_UNKNOWN":
        return None
    if timing["status"] == "EXACT_SUPPLIED_FRAME":
        value = lookup[timing["frame_alias"]]
        return value, value
    return lookup[timing["start_frame_alias"]], lookup[timing["end_frame_alias"]]


def _gt_interval(event: dict) -> tuple[float, float]:
    timing = event["event_time"]
    return float(timing["start_timestamp_s"]), float(timing["end_timestamp_s"])


def _compatible(gt: dict, pred: dict, mapping: list[dict], tolerance: float, require_overlap: bool) -> tuple[bool, float]:
    if pred.get("target_association_uncertainty") != "NONE":
        return False, float("inf")
    if gt["event_type"] != pred["event_type"]:
        return False, float("inf")
    pred_interval = _prediction_interval(pred, mapping)
    if pred_interval is None:
        return False, float("inf")
    gs, ge = _gt_interval(gt)
    ps, pe = pred_interval
    if gs == ge:
        distance = 0.0 if ps <= gs <= pe else min(abs(gs - ps), abs(gs - pe))
        return distance <= tolerance, distance
    overlap = max(0.0, min(ge, pe) - max(gs, ps))
    if require_overlap:
        return overlap > 0 or (gs == ps == ge == pe), -overlap
    distance = 0.0 if overlap > 0 else min(abs(gs - pe), abs(ps - ge))
    return distance <= tolerance, distance


def match_known_events(gt_events: list[dict], predicted: list[dict], mapping: list[dict], tolerance_s: float, require_overlap: bool) -> dict:
    candidates = []
    for gi, gt in enumerate(gt_events):
        for pi, pred in enumerate(predicted):
            ok, score = _compatible(gt, pred, mapping, tolerance_s, require_overlap)
            if ok:
                candidates.append((score, gi, pi))
    matches, used_gt, used_pred = [], set(), set()
    for score, gi, pi in sorted(candidates):
        if gi in used_gt or pi in used_pred:
            continue
        used_gt.add(gi); used_pred.add(pi)
        matches.append({"gt_event_id": gt_events[gi]["event_id"], "predicted_event_id": predicted[pi]["event_id"], "event_type": gt_events[gi]["event_type"], "temporal_match_score": score})
    return {
        "matches": matches,
        "unmatched_supported_gt_event_ids": [event["event_id"] for i, event in enumerate(gt_events) if i not in used_gt],
        "extra_predicted_event_ids": [event["event_id"] for i, event in enumerate(predicted) if i not in used_pred],
    }


def evaluate_item(record: dict, eligibility: dict, prediction: dict, representation: dict, decisions: dict) -> dict:
    permission = eligibility["pilot_scoring_permission"]
    if permission == "AUDIT_ONLY_NO_MODEL_RUN":
        raise Phase2BBlocked("EXCLUDED_ITEM_MUST_NOT_BE_EVALUATED")
    base = {
        "annotation_item_id": record["annotation_item_id"],
        "evaluation_scope": permission,
        "prediction_outcome": prediction["window_outcome"],
        "predicted_event_count": len(prediction["events"]),
        "binding_causality_status": "CAUSALITY_UNVERIFIED",
    }
    if permission == "KNOWN_EVENT_MATCHING_ONLY":
        supported = [event for event in record["response"]["events"] if event["event_id"] in eligibility["supported_positive_event_ids"]]
        result = match_known_events(supported, prediction["events"], representation["private_mapping"],
                                    float(decisions["event_time_tolerance_s"]), bool(decisions["bounded_interval_overlap_required"]))
        return {**base, **result, "extra_predictions_interpretation": "UNEVALUATED", "full_window_false_positive_claim": "UNDEFINED"}
    if permission == "STRICT_NEGATIVE_CASE_ALERT_ANALYSIS":
        return {**base, "case_level_false_event_alert": bool(prediction["events"]), "population_false_positive_rate": "UNDEFINED", "population_false_positive_rate_reason": "Three selected DEV strict-negative cases are not a benchmark population"}
    return {**base, "descriptive_only": True, "matching": "UNDEFINED", "reason": "Human outcome is uncertain; no event-list completeness claim"}


def summarize_evaluations(results: list[dict]) -> dict:
    return {
        "schema_version": "PASS_T_PHASE2B_EVALUATION_SUMMARY_V1",
        "items": results,
        "global_metrics": {metric: {"value": "UNDEFINED", "reason": "Phase 2b DEV pilot eligibility and sample-size restrictions"} for metric in FORBIDDEN_METRICS},
        "counts": {
            "evaluated_items": len(results),
            "known_event_matches": sum(len(row.get("matches", [])) for row in results),
            "strict_negative_case_alerts": sum(bool(row.get("case_level_false_event_alert")) for row in results),
            "descriptive_only_items": sum(bool(row.get("descriptive_only")) for row in results),
        },
    }

