from __future__ import annotations

import inspect

import pytest

from memory_graph.v2101_deploy.boundary import (
    AUTHORITY,
    make_candidate_record,
    require_v2101_artifact_path,
)


def test_candidate_output_has_no_operational_identity_authority():
    before = {"core": {"entities": ["phone_01"]}, "negative_bank": ["phone_02"]}
    record = make_candidate_record(
        model_id="candidate", model_revision="rev", event_id="event-1",
        raw_response='{"event_type":"STATIC"}', completed=True, json_valid=True,
        schema_valid=False, semantic_validator_valid=None, metrics={"wall_s": 1.0},
    )
    assert before == {"core": {"entities": ["phone_01"]}, "negative_bank": ["phone_02"]}
    assert record["authority"] == AUTHORITY
    assert not ({"persistent_id", "alias", "identity_write", "memory_graph_write"} & record.keys())
    assert "identity_state" not in inspect.signature(make_candidate_record).parameters
    assert "memory_graph" not in inspect.signature(make_candidate_record).parameters


def test_v2101_writer_rejects_historical_output_namespaces():
    assert "artifacts\\v2.10.1" in str(require_v2101_artifact_path("artifacts/v2.10.1/smoke/x.json"))
    for path in ("outputs/v297_physical_identity/x.json", "outputs/current_development/x.json"):
        with pytest.raises(ValueError, match="artifacts/v2.10.1"):
            require_v2101_artifact_path(path)
