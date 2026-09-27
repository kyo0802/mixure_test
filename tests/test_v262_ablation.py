"""V2.6.2 source, identity, gate, and prediction-freeze invariants."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from memory_graph.v262.adapters import can_reinitialize, counts_as_correct_target
from memory_graph.v262.paired import require_stage_b


def read(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _rows(model: str):
    for number in range(3, 10):
        prediction = read(f"outputs_v262/test{number}/{model}_predictions.json")
        for window in prediction["windows"].values():
            yield from window["observations"]


def test_v26_outputs_read_only():
    from memory_graph.v262.audit import sha
    manifest = read("outputs_v262/experiment_manifest.json")
    assert sha(ROOT / "outputs_v26/baseline_manifest.json") == manifest["baseline_manifest_sha256"]
    assert sha(ROOT / "outputs_v26/prediction_manifest.json") == manifest["v26_prediction_manifest_sha256"]


def test_v261_outputs_read_only():
    from memory_graph.v262.audit import sha
    manifest = read("outputs_v262/experiment_manifest.json")
    assert sha(ROOT / "outputs_v261/experiment_manifest.json") == manifest["v261_experiment_manifest_sha256"]


def test_sam31_checkpoint_not_used_in_v262():
    env = read("outputs_v262/environment_manifest.json")["sam3"]
    assert env["checkpoint"].endswith("/sam3.pt")
    assert "sam3.1" not in env["checkpoint"].lower()
    assert "Multiplex" not in (env["model"] or "")


def test_official_sam3_checkpoint_used():
    env = read("outputs_v262/environment_manifest.json")["sam3"]
    smoke = read("outputs_v262/smoke/sam3/result.json")
    assert env["checkpoint_repository"] == "facebook/sam3"
    assert env["checkpoint_sha256"] == smoke["checkpoint_sha256"]
    assert env["checkpoint_bytes"] == (ROOT / env["checkpoint"]).stat().st_size


def test_sam3_repository_revision_recorded():
    env = read("outputs_v262/environment_manifest.json")["sam3"]
    assert len(env["source_revision"]) == 40
    assert len(env["checkpoint_revision"]) == 40


def test_same_test8_smoke_frames():
    a = read("outputs_v262/smoke/sam21/result.json")
    b = read("outputs_v262/smoke/sam3/result.json")
    assert a["frames"] == b["frames"] == list(range(804, 847, 6))


def test_same_f804_target_initialization():
    a = read("outputs_v262/smoke/sam21/result.json")
    b = read("outputs_v262/smoke/sam3/result.json")
    frozen = read("outputs_v26/test8/sam_reinit_log.json")
    init = next(e for e in frozen["segment"]["events"] if e["type"] == "INIT")
    assert a["frozen_box_xyxy"] == b["frozen_box_xyxy"] == init["frozen_yolo_detection"]["bbox"]


def test_sam21_sam3_same_target_entity():
    assert all(row["target_persistent_entity"] == "phone_01" for model in ("sam21", "sam3", "sam3point") for row in _rows(model))


def test_gt_not_used_for_prompt():
    source = (ROOT / "src/memory_graph/v262/paired.py").read_text(encoding="utf-8")
    assert "review.md" not in source and "evaluation/" not in source
    assert all(read(f"outputs_v262/test{n}/sam3_predictions.json")["label_blind"] for n in range(3, 10))


def test_sam_ids_not_persistent_ids():
    assert all(row["source_object_id"] != row["target_persistent_entity"] for model in ("sam21", "sam3", "sam3point") for row in _rows(model))


def test_provisional_cannot_reinitialize_sam21():
    assert not can_reinitialize("PROVISIONAL_MATCH")
    assert not any(w["initialization_frame"] == 636 for w in read("outputs_v262/test7/sam21_predictions.json")["windows"].values())


def test_provisional_cannot_reinitialize_sam3():
    assert not can_reinitialize("PROVISIONAL_MATCH")
    assert not any(w["initialization_frame"] == 636 for w in read("outputs_v262/test7/sam3_predictions.json")["windows"].values())


def test_confirmed_can_reinitialize_sam21():
    assert can_reinitialize("CONFIRMED_MATCH")
    assert read("outputs_v262/test8/sam21_predictions.json")["windows"]["same_identity_reinit"]["initialization_frame"] == 804


def test_confirmed_can_reinitialize_sam3():
    assert can_reinitialize("CONFIRMED_MATCH")
    assert read("outputs_v262/test8/sam3_predictions.json")["windows"]["same_identity_reinit"]["initialization_frame"] == 804


def test_attention_backend_actually_executed():
    smoke = read("outputs_v262/smoke/sam3/result.json")
    assert smoke["attention_backend"] == "PYTORCH_MEM_EFFICIENT_SDPA"
    assert "aten::_scaled_dot_product_efficient_attention" in smoke["attention_ops"]


def test_stage_b_requires_stage_a_pass():
    with pytest.raises(RuntimeError, match="Stage B"):
        require_stage_b({"decision": "FAIL"})
    require_stage_b({"decision": "PASS"})


def test_drift_not_counted_as_success():
    assert not counts_as_correct_target({"accepted_by_guard": True}, "DRIFT_TO_OTHER_OBJECT")
    assert not counts_as_correct_target({"accepted_by_guard": False}, "CORRECT_TARGET")
    assert counts_as_correct_target({"accepted_by_guard": True}, "CORRECT_TARGET")


def test_prediction_freeze_before_review():
    freeze = read("outputs_v262/prediction_manifest.json")
    assert freeze["frozen_before_v262_mask_review"] and not freeze["inference_code_read_labels"]
    timestamp = datetime.fromisoformat(freeze["freeze_utc"]).timestamp()
    for number in range(3, 10):
        review = ROOT / f"outputs_v262/test{number}/review.md"
        if review.exists():
            assert review.stat().st_mtime >= timestamp
