"""Executable mock matrix; mock artifacts are never treated as experimental results."""
from __future__ import annotations

from .backends import MockBackend
from .common import Phase2BBlocked
from .config import check_capabilities, unresolved_template
from .predictions import parse_raw, validate_prediction


SCENARIOS = [
    "valid_pickup", "valid_placement", "no_event", "insufficient", "target_not_observable",
    "missing_fields", "malformed_json", "out_of_payload_citation", "global_identity_claim",
    "fabricated_exact_timing", "persisted_state", "extra_events", "timeout",
]


def mock_payload() -> dict:
    aliases = [f"F{i:04d}" for i in range(1, 7)]
    return {
        "schema_version": "PASS_T_PHASE2B_MODEL_PAYLOAD_V1",
        "request_id": "REQ_0123456789abcdef0123",
        "target": {"opaque_id": "TARGET_A", "description": "the authorized target object"},
        "ontology": {"event_types": ["PICKUP", "PLACEMENT"], "window_outcomes": ["CONFIRMED_EVENTS", "NO_CONFIRMED_EVENT", "INSUFFICIENT_EVIDENCE", "TARGET_NOT_OBSERVABLE"]},
        "representation": "MULTI_IMAGE",
        "media": [{"media_id": "MEDIA_001", "media_type": "image/png", "content_sha256": "0" * 64, "supplied_frame_aliases": aliases}],
        "instructions": "Use only supplied evidence and return the required JSON contract.",
        "output_contract": "PASS_T_PHASE2B_PREDICTION_V1",
    }


def run_mock_suite() -> dict:
    payload = mock_payload()
    aliases = payload["media"][0]["supplied_frame_aliases"]
    rows = []
    expected_valid = {"valid_pickup", "valid_placement", "no_event", "insufficient", "target_not_observable", "extra_events"}
    for scenario in SCENARIOS:
        raw = b""
        error = None
        valid = False
        validation = None
        try:
            raw = MockBackend(scenario).invoke(payload, {}, 1)
            prediction = parse_raw(raw)
            validation = validate_prediction(prediction, aliases)
            valid = validation["valid"]
            if valid != (scenario in expected_valid):
                error = "UNEXPECTED_VALIDATION_RESULT"
        except (Phase2BBlocked, TimeoutError) as exc:
            valid = False
            error = type(exc).__name__ + ":" + str(exc)
            if scenario not in {"malformed_json", "timeout"}:
                error = "UNEXPECTED_EXCEPTION:" + error
        rows.append({"scenario": scenario, "valid": valid, "expected_valid": scenario in expected_valid,
                     "raw_output_utf8": raw.decode("utf-8", errors="replace"), "validation": validation, "error": error})
    declared = unresolved_template()
    declared.update(provider="example", backend="example", model="example", revision="r1", execution_location="LOCAL", complete=True)
    declared["generation"] = {"temperature": 0.0, "sampling": False, "seed": 1, "max_output_tokens": 1024}
    declared["transport"] = {"timeout_seconds": 30, "max_retries": 0, "monetary_budget_usd": 0}
    for rep in declared["capabilities"].values():
        rep.update(status="DECLARED", evidence="manual declaration")
    cap = check_capabilities(declared)
    capability_mismatch_passed = not cap["real_run_ready"] and not cap["verified_representations"]
    passed = all((row["valid"] == row["expected_valid"] and not (row["error"] or "").startswith("UNEXPECTED")) for row in rows) and capability_mismatch_passed
    return {"schema_version": "PASS_T_PHASE2B_MOCK_SUITE_V1", "passed": passed, "scenarios": rows,
            "capability_mismatch_rejected": capability_mismatch_passed, "mock_only": True, "experimental_result": False}

