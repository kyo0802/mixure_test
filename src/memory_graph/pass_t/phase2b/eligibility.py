"""Explicit, non-promotional Phase 2b evaluation eligibility projection."""
from __future__ import annotations

from .authority import Phase2BAuthority
from .common import Phase2BBlocked


VISUAL_STATUSES = {"NONE", "ASSISTANT_SPOT_CHECK", "HUMAN_PARTIAL", "HUMAN_FULL"}


def build_eligibility(authority: Phase2BAuthority) -> dict:
    sidecars = {row["parent"]["annotation_item_id"]: row for row in authority.exhaustive_sidecar["records"]}
    rows = []
    for item_id in sorted(authority.records):
        record = authority.records[item_id]
        item = authority.items[item_id]
        outcome = record["response"]["window_outcome"]
        category = record["category"]
        status = "NONE"
        limits: list[str] = []
        permission = "NONE"
        supported_ids: list[str] = []
        strict_negative = False
        final_exhaustiveness = record["evaluation"].get("event_list_exhaustiveness", "NOT_APPLICABLE")
        original_valid = bool(record["independent_validation"]["valid"])
        v2_full = bool(record["evaluation"]["full_window_event_evaluation_supported"])
        exploratory = bool(record["evaluation"]["supported_event_exploratory_use_allowed"])
        if category == "QUARANTINED_EXCLUDED":
            permission = "AUDIT_ONLY_NO_MODEL_RUN"
            limits.extend(record["evaluation"]["event_evaluation_exclusion_reasons"])
        elif outcome == "INSUFFICIENT_EVIDENCE":
            permission = "DESCRIPTIVE_UNCERTAINTY_ONLY"
            final_exhaustiveness = "NO_COMPLETENESS_CLAIM"
            limits.append("No confirmed-event completeness or scoring claim")
        elif outcome == "NO_CONFIRMED_EVENT":
            permission = "STRICT_NEGATIVE_CASE_ALERT_ANALYSIS"
            strict_negative = original_valid and v2_full
            final_exhaustiveness = "STRICT_NEGATIVE_FULL_WINDOW_ATTESTED"
            if item_id == "PT2A_9d15d2a6b56b56d0":
                status = "ASSISTANT_SPOT_CHECK"
                limits.append("Only 7 of 107 frames received an additional assistant spot check")
            else:
                limits.append("No independent full-window visual quality review beyond the accepted V2 response")
        elif outcome == "CONFIRMED_EVENTS" and item_id in sidecars:
            sidecar = sidecars[item_id]
            permission = "KNOWN_EVENT_MATCHING_ONLY"
            status = "HUMAN_PARTIAL"
            final_exhaustiveness = "NON_EXHAUSTIVE_CONFIRMED"
            supported_ids = [event["event_id"] for event in record["response"].get("events", [])]
            exploratory = True
            v2_full = False
            limits.extend([
                sidecar["blocking_reason"],
                "Unlisted predicted events are UNEVALUATED, not false positives",
            ])
        else:
            raise Phase2BBlocked(f"UNSUPPORTED_ELIGIBILITY_COMBINATION:{item_id}:{category}:{outcome}")
        if status not in VISUAL_STATUSES:
            raise Phase2BBlocked("INVALID_VISUAL_REVIEW_STATUS")
        exclusions = list(record["evaluation"].get("event_evaluation_exclusion_reasons", []))
        row = {
            "annotation_item_id": item_id,
            "original_response_valid": original_valid,
            "original_v2_full_window_eligible": v2_full,
            "v2_full_window_evidence_supported": v2_full,
            "final_exhaustiveness_status": final_exhaustiveness,
            "strict_negative_supported": strict_negative,
            "supported_positive_event_ids": supported_ids,
            "exploratory_matching_allowed": exploratory and permission == "KNOWN_EVENT_MATCHING_ONLY",
            "independent_visual_review_status": status,
            "additional_visual_quality_verified": status == "HUMAN_FULL",
            "visual_review_limitations": limits,
            "exclusion_reasons": exclusions,
            "binding_causality_status": "CAUSALITY_UNVERIFIED",
            "formal_benchmark_permission": False,
            "pilot_scoring_permission": permission,
            "unlisted_events_status": "UNEVALUATED" if permission == "KNOWN_EVENT_MATCHING_ONLY" else (
                "CASE_LEVEL_ALERT_ONLY" if permission == "STRICT_NEGATIVE_CASE_ALERT_ANALYSIS" else "NOT_SCORED"
            ),
            "source_video_identifier": item["source_video_identifier"],
            "original_pack_ids": item["original_pack_ids"],
        }
        if row["formal_benchmark_permission"] or item.get("formal_eligible"):
            raise Phase2BBlocked("FORMAL_ELIGIBILITY_PROMOTION_FORBIDDEN")
        rows.append(row)
    return {
        "schema_version": "PASS_T_PHASE2B_ELIGIBILITY_V1",
        "authority": authority.provenance,
        "records": rows,
        "summary": {
            "total": len(rows),
            "known_event_matching_only": sum(r["pilot_scoring_permission"] == "KNOWN_EVENT_MATCHING_ONLY" for r in rows),
            "strict_negative_case_alerts": sum(r["strict_negative_supported"] for r in rows),
            "descriptive_uncertainty_only": sum(r["pilot_scoring_permission"] == "DESCRIPTIVE_UNCERTAINTY_ONLY" for r in rows),
            "audit_only": sum(r["pilot_scoring_permission"] == "AUDIT_ONLY_NO_MODEL_RUN" for r in rows),
            "formal_benchmark_eligible": 0,
            "additional_human_full_visual_reviews": 0,
        },
        "metric_policy": {
            "strict_negative_windows": "case-level false-event alerts only; no population false-positive rate",
            "positive_windows": "conditional known-event matching only; extra predictions are UNEVALUATED",
            "uncertain_windows": "descriptive outputs only",
            "forbidden_global_metrics": ["accuracy", "precision", "recall", "F1", "hallucination_rate", "significance", "superiority", "generalization"],
        },
    }


def by_id(eligibility: dict) -> dict[str, dict]:
    return {row["annotation_item_id"]: row for row in eligibility["records"]}

