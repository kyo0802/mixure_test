from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from memory_graph.pass_t.phase2b.authority import DATASET_SHA256, load_phase2b_authority
from memory_graph.pass_t.phase2b.backends import MockBackend, register_backend
from memory_graph.pass_t.phase2b.builders import build_multi_image, build_storyboard, build_video, uniform_positions
from memory_graph.pass_t.phase2b.common import Phase2BBlocked, canonical_bytes, digest, exclusive_tree, read_json, repository_root
from memory_graph.pass_t.phase2b.config import check_capabilities, unresolved_template, validate_config
from memory_graph.pass_t.phase2b.eligibility import build_eligibility, by_id
from memory_graph.pass_t.phase2b.evaluation import evaluate_item, summarize_evaluations
from memory_graph.pass_t.phase2b.inference import run_real_pilot
from memory_graph.pass_t.phase2b.mocks import mock_payload, run_mock_suite
from memory_graph.pass_t.phase2b.model_visible import build_payload, inspect_payload, source_contract
from memory_graph.pass_t.phase2b.predictions import parse_raw, validate_prediction
from memory_graph.pass_t.phase2b.protocol import freeze_protocol, prepare_protocol, verify_frozen_protocol
from memory_graph.pass_t.phase2b.reporting import preservation_check
from memory_graph.pass_t.phase2b.inputs import build_input_package, load_package


@pytest.fixture(scope="module")
def authority():
    return load_phase2b_authority()


@pytest.fixture(scope="module")
def eligibility(authority):
    return build_eligibility(authority)


def complete_config(status="LOCALLY_VERIFIED"):
    config = unresolved_template()
    config.update(provider="mock-provider", backend="mock-backend", model="one-model", revision="revision-1",
                  execution_location="LOCAL", modalities=["video", "multi-image"], complete=True)
    config["limits"] = {"max_images": 12, "max_pixels_per_image": 1280 * 720, "context_tokens": 32768}
    config["generation"] = {"temperature": 0.0, "sampling": False, "seed": 1, "max_output_tokens": 2048}
    config["transport"] = {"timeout_seconds": 60, "max_retries": 0, "monetary_budget_usd": 0}
    for rep in config["capabilities"].values():
        rep.update(status=status, evidence="local deterministic capability probe")
    return config


def decisions(ids):
    return {"multi_image_frame_count": 6, "storyboard_frame_count": 6, "storyboard_columns": 3,
            "video_fps": 30.0, "event_time_tolerance_s": 0.2, "bounded_interval_overlap_required": True,
            "repeat_count": 1, "run_order": ["MULTI_IMAGE", "STORYBOARD", "REENCODED_AUTHORIZED_VIDEO"],
            "pilot_item_ids": ids, "reference_policy": "NONE", "budget_limit_usd": 0}


def synthetic_source(tmp_path: Path, count=6):
    rows = []
    for index in range(count):
        path = tmp_path / f"source_{index}.png"
        Image.new("RGB", (64, 36), (index * 20, 10, 100)).save(path)
        import hashlib
        rows.append({"opaque_alias": f"F{index + 1:04d}", "private_source_frame_index": 100 + index,
                     "private_source_timestamp_s": index / 30, "private_path": str(path),
                     "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return {"private_schema_version": "PASS_T_PHASE2B_SOURCE_CONTRACT_V1", "private_annotation_item_id": "private",
            "opaque_window_id": "W_0123456789abcdef0123", "frames": rows, "references": [],
            "width": 64, "height": 36, "reference_policy": "NONE"}


def test_authority_hash_and_item_set(authority):
    assert authority.provenance["dataset_sha256"] == DATASET_SHA256
    assert len(authority.items) == len(authority.records) == 7


def test_eligibility_is_explicit_and_non_promotional(eligibility):
    assert eligibility["summary"] == {"total": 7, "known_event_matching_only": 2,
        "strict_negative_case_alerts": 3, "descriptive_uncertainty_only": 1, "audit_only": 1,
        "formal_benchmark_eligible": 0, "additional_human_full_visual_reviews": 0}
    assert all(not row["formal_benchmark_permission"] for row in eligibility["records"])


def test_window_specific_permissions(eligibility):
    rows = by_id(eligibility)
    assert rows["PT2A_0bfb99c324769681"]["pilot_scoring_permission"] == "AUDIT_ONLY_NO_MODEL_RUN"
    assert rows["PT2A_5dbb180e8ff88762"]["pilot_scoring_permission"] == "DESCRIPTIVE_UNCERTAINTY_ONLY"
    assert rows["PT2A_9d15d2a6b56b56d0"]["independent_visual_review_status"] == "ASSISTANT_SPOT_CHECK"
    assert rows["PT2A_eb60192e6986cb4f"]["final_exhaustiveness_status"] == "NON_EXHAUSTIVE_CONFIRMED"


def test_source_contract_uses_opaque_aliases(authority):
    item = authority.items["PT2A_9d15d2a6b56b56d0"]
    source = source_contract(item, secret="0123456789abcdef", reference_policy="NONE")
    assert source["opaque_window_id"].startswith("W_")
    assert source["frames"][0]["opaque_alias"] == "F0001"
    assert source["private_annotation_item_id"] == item["annotation_item_id"]


def test_neutral_reference_requires_explicit_approved_provenance(authority):
    with pytest.raises(Phase2BBlocked, match="NEUTRAL_LOCALIZATION_REFERENCE_NOT_CONFIGURED"):
        source_contract(authority.items["PT2A_9d15d2a6b56b56d0"], secret="0123456789abcdef",
                        reference_policy="APPROVED_NEUTRAL_LOCALIZATION")


def test_payload_has_no_gt_or_source_identifiers(authority, tmp_path):
    source = source_contract(authority.items["PT2A_9d15d2a6b56b56d0"], secret="0123456789abcdef")
    built = build_multi_image(source, tmp_path, 4)
    payload = build_payload(source, built, "Return the event JSON contract.")
    inspection = inspect_payload(payload, source)
    raw = canonical_bytes(payload).decode()
    assert inspection["safe"]
    assert "PT2A_" not in raw and "test1" not in raw and "source_frame_index" not in raw


def test_input_package_repeat_is_identical_and_detects_tampering(authority, tmp_path):
    kwargs = dict(secret="deterministic-test-secret", prompt_text="Return the event JSON contract.",
                  representations=["MULTI_IMAGE", "STORYBOARD"], frame_count=3,
                  storyboard_columns=3, video_fps=30, base=tmp_path / "inputs")
    item = authority.items["PT2A_9d15d2a6b56b56d0"]
    first = build_input_package(item, **kwargs)
    second = build_input_package(item, **kwargs)
    assert first == second
    assert load_package(first)["manifest"]["representations"]
    target = first / "model_visible/MULTI_IMAGE/payload.json"
    target.chmod(0o666)
    target.write_bytes(b"{}")
    with pytest.raises(Phase2BBlocked, match="INPUT_PACKAGE_HASH_MISMATCH"):
        load_package(first)


def test_protocol_invalid_numeric_decisions_block_freeze(eligibility):
    selected = decisions(["PT2A_9d15d2a6b56b56d0"])
    selected["event_time_tolerance_s"] = -1
    protocol = prepare_protocol(complete_config(), eligibility, selected)
    assert protocol["status"] == "DRAFT_UNRESOLVED"


def test_serialized_leakage_detection():
    payload = mock_payload()
    payload["target"]["annotation_item_id"] = "PT2A_deadbeefdeadbeef"
    result = inspect_payload(payload)
    assert not result["safe"]
    assert any("FORBIDDEN" in row for row in result["errors"])


def test_uniform_sampler_whole_window():
    assert uniform_positions(10, 4) == [0, 3, 6, 9]
    with pytest.raises(Phase2BBlocked):
        uniform_positions(2, 3)


def test_multi_image_and_storyboard_share_selection(tmp_path):
    source = synthetic_source(tmp_path)
    multi = build_multi_image(source, tmp_path / "multi", 4)
    board = build_storyboard(source, tmp_path / "board", 4, 2)
    assert multi["selection_policy"]["positions"] == board["selection_policy"]["positions"]
    assert [r["opaque_alias"] for r in multi["private_mapping"]] == [r["opaque_alias"] for r in board["private_mapping"]]


def test_video_builder_exact_frame_count_and_endpoints(tmp_path):
    source = synthetic_source(tmp_path, 4)
    video = build_video(source, tmp_path / "video", 30.0)
    assert video["verification"]["decoded_frame_count"] == 4
    assert video["verification"]["first_pixel_exact"] and video["verification"]["last_pixel_exact"]
    assert video["temporal_mapping"]["native_pts_retained"] is False


def test_unresolved_config_is_blocked():
    result = validate_config(unresolved_template(), real_run=True)
    assert not result["valid"] and "model" in result["errors"]


def test_declared_capability_is_not_verified():
    result = check_capabilities(complete_config("DECLARED"))
    assert not result["real_run_ready"] and result["verified_representations"] == []


def test_verified_complete_config_passes():
    assert validate_config(complete_config(), real_run=True)["valid"]
    assert check_capabilities(complete_config())["real_run_ready"]


def test_protocol_draft_refuses_unresolved(eligibility, tmp_path):
    draft = prepare_protocol(unresolved_template(), eligibility, {})
    assert draft["status"] == "DRAFT_UNRESOLVED" and draft["unresolved_fields"]
    with pytest.raises(Phase2BBlocked):
        freeze_protocol(draft, tmp_path)


def test_protocol_freeze_and_verify(eligibility, tmp_path):
    allowed = [r["annotation_item_id"] for r in eligibility["records"] if r["pilot_scoring_permission"] != "AUDIT_ONLY_NO_MODEL_RUN"]
    draft = prepare_protocol(complete_config(), eligibility, decisions(allowed))
    assert draft["status"] == "READY_TO_FREEZE"
    folder = freeze_protocol(draft, tmp_path)
    assert verify_frozen_protocol(folder)["status"] == "FROZEN"


@pytest.mark.parametrize("scenario", ["valid_pickup", "valid_placement", "no_event", "insufficient", "target_not_observable", "extra_events"])
def test_valid_mock_scenarios(scenario):
    payload = mock_payload(); aliases = payload["media"][0]["supplied_frame_aliases"]
    prediction = parse_raw(MockBackend(scenario).invoke(payload, {}, 1))
    assert validate_prediction(prediction, aliases)["valid"]


@pytest.mark.parametrize("scenario", ["missing_fields", "out_of_payload_citation", "global_identity_claim", "fabricated_exact_timing", "persisted_state"])
def test_invalid_mock_scenarios(scenario):
    payload = mock_payload(); aliases = payload["media"][0]["supplied_frame_aliases"]
    prediction = parse_raw(MockBackend(scenario).invoke(payload, {}, 1))
    assert not validate_prediction(prediction, aliases)["valid"]


def test_malformed_and_timeout_are_not_repaired():
    payload = mock_payload()
    with pytest.raises(Phase2BBlocked):
        parse_raw(MockBackend("malformed_json").invoke(payload, {}, 1))
    with pytest.raises(TimeoutError):
        MockBackend("timeout").invoke(payload, {}, 1)


def test_duplicate_keys_and_nonfinite_numbers_are_rejected():
    with pytest.raises(Phase2BBlocked, match="DUPLICATE_MODEL_OUTPUT_KEY"):
        parse_raw(b'{"a":1,"a":2}')
    with pytest.raises(Phase2BBlocked, match="NONFINITE_MODEL_OUTPUT"):
        parse_raw(b'{"a":NaN}')


def test_mock_suite_isolated_and_complete():
    result = run_mock_suite()
    assert result["passed"] and result["mock_only"] and not result["experimental_result"]
    assert len(result["scenarios"]) == 13


def test_strict_negative_is_case_alert_not_rate(authority, eligibility):
    item_id = "PT2A_9d15d2a6b56b56d0"
    prediction = parse_raw(MockBackend("valid_pickup").invoke(mock_payload(), {}, 1))
    representation = {"private_mapping": [{"opaque_alias": f"F{i:04d}", "source_timestamp_s": float(i)} for i in range(1, 7)]}
    result = evaluate_item(authority.records[item_id], by_id(eligibility)[item_id], prediction, representation, decisions([item_id]))
    assert result["case_level_false_event_alert"] is True
    assert result["population_false_positive_rate"] == "UNDEFINED"


def test_nonexhaustive_positive_extras_are_unevaluated(authority, eligibility):
    item_id = "PT2A_eb60192e6986cb4f"
    record = authority.records[item_id]
    timestamp = record["response"]["events"][0]["event_time"]["start_timestamp_s"]
    payload = mock_payload(); prediction = parse_raw(MockBackend("extra_events").invoke(payload, {}, 1))
    mapping = [{"opaque_alias": f"F{i:04d}", "source_timestamp_s": timestamp + (i - 2) * .05} for i in range(1, 7)]
    result = evaluate_item(record, by_id(eligibility)[item_id], prediction, {"private_mapping": mapping}, decisions([item_id]))
    assert len(result["matches"]) == 1
    assert result["extra_predictions_interpretation"] == "UNEVALUATED"
    assert result["full_window_false_positive_claim"] == "UNDEFINED"


def test_global_summary_forbids_metrics():
    summary = summarize_evaluations([])
    assert all(row["value"] == "UNDEFINED" for row in summary["global_metrics"].values())


def test_excluded_item_evaluation_refused(authority, eligibility):
    item_id = "PT2A_0bfb99c324769681"
    with pytest.raises(Phase2BBlocked):
        evaluate_item(authority.records[item_id], by_id(eligibility)[item_id], {}, {}, {})


def test_real_run_requires_three_explicit_gates(tmp_path, eligibility, monkeypatch):
    allowed = [r["annotation_item_id"] for r in eligibility["records"] if r["pilot_scoring_permission"] != "AUDIT_ONLY_NO_MODEL_RUN"]
    folder = freeze_protocol(prepare_protocol(complete_config(), eligibility, decisions(allowed)), tmp_path)
    monkeypatch.delenv("PASS_T_PHASE2B_REAL_RUN_PERMISSION", raising=False)
    with pytest.raises(Phase2BBlocked, match="EXPLICIT_REAL_RUN_PERMISSION_REQUIRED"):
        run_real_pilot(protocol_folder=folder, packages=[], confirmation="WRONG", run_permission=False)


def test_failed_backend_call_is_preserved(tmp_path, eligibility, monkeypatch):
    class TimeoutBackend:
        name = "TEST_TIMEOUT_BACKEND"
        def invoke(self, request, media, timeout_seconds):
            raise TimeoutError("controlled failure")
    try:
        register_backend("TEST_TIMEOUT_BACKEND", lambda config: TimeoutBackend())
    except Phase2BBlocked as error:
        assert "DUPLICATE" in str(error)
    item_id = "PT2A_9d15d2a6b56b56d0"
    config = complete_config()
    config["backend"] = "TEST_TIMEOUT_BACKEND"
    config["transport"]["max_retries"] = 1
    selected = decisions([item_id])
    selected["run_order"] = ["MULTI_IMAGE"]
    folder = freeze_protocol(prepare_protocol(config, eligibility, selected), tmp_path / "protocol")
    payload = mock_payload()
    prompt = (repository_root() / "artifacts/pass_t/phase2b/templates/event_reasoning_prompt_v1.txt").read_text(encoding="utf-8")
    payload["instructions"] = prompt
    blob = b"mock-media"
    payload["media"][0]["content_sha256"] = digest(blob)
    package = {
        "payload": payload,
        "media_bytes": {"MEDIA_001": blob},
        "private_mapping": {
            "source_contract": {"private_annotation_item_id": item_id, "reference_policy": "NONE"},
            "representations": {"MULTI_IMAGE": {"selection_policy": {"requested_count": 6}}},
        },
    }
    monkeypatch.setenv("PASS_T_PHASE2B_REAL_RUN_PERMISSION", "true")
    run = run_real_pilot(protocol_folder=folder, packages=[package],
                         confirmation="RUN_PHASE2B_EXPLORATORY_PILOT", run_permission=True,
                         output_base=tmp_path / "runs")
    manifest = read_json(run / "run_manifest.json")
    assert manifest["runs"][0]["status"] == "FAILED_RECORDED"
    assert len(manifest["runs"][0]["attempts"]) == 2
    run_id = manifest["runs"][0]["run_id"]
    assert (run / f"per_run/{run_id}/attempt_00/failure.json").is_file()
    assert (run / f"per_run/{run_id}/attempt_01/failure.json").is_file()


def test_content_addressed_store_refuses_conflict(tmp_path):
    folder = exclusive_tree(tmp_path, {"x.json": b"{}\n"}, {"schema_version": "TEST"})
    (folder / "x.json").chmod(0o666)
    (folder / "x.json").write_bytes(b"changed")
    with pytest.raises(Phase2BBlocked):
        exclusive_tree(tmp_path, {"x.json": b"{}\n"}, {"schema_version": "TEST"})


def test_preservation_baseline_remains_intact():
    result = preservation_check()
    assert result["verified"] and result["changed"] == [] and result["head_unchanged"]
