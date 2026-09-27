"""Audit the completed V2.6.1 partial freeze without claiming a full paired A/B."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import pytest


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v261"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def evidence():
    return {
        "experiment": read(OUT / "experiment_manifest.json"),
        "summary": read(OUT / "comparison_summary.json"),
        "freeze": read(OUT / "prediction_manifest.json"),
        "environment": read(OUT / "environment_manifest.json"),
        "sam21": read(OUT / "smoke/sam21_eight_frame_result.json"),
        "box": read(OUT / "smoke/smoke_math_max1_capacity16_frames8.json"),
        "point": read(OUT / "smoke/smoke_point_math_max1_capacity16_frames8.json"),
    }


def test_sam21_and_sam31_use_same_video(evidence):
    assert evidence["sam21"]["video"] == evidence["box"]["video"] == "test8.mp4"


def test_sam21_and_sam31_use_same_initialization_frame(evidence):
    assert evidence["sam21"]["frames"] == evidence["box"]["frames"]
    assert evidence["sam21"]["frames"][0] == 804


def test_sam21_and_sam31_use_same_target_entity(evidence):
    window = evidence["experiment"]["videos"]["test8"]["windows"][-1]
    assert window["persistent_entity_id"] == "phone_01"
    assert window["init_frame"] == evidence["sam21"]["frames"][0]
    assert evidence["sam21"]["frozen_box_xyxy"] == evidence["box"]["frozen_box_xyxy"]


def test_sam31_prompt_is_derived_from_frozen_target_evidence(evidence):
    cap = cv2.VideoCapture(str(ROOT / "test8.mp4"))
    width, height = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    cap.release()
    assert width > 0 and height > 0
    x1, y1, x2, y2 = evidence["experiment"]["videos"]["test8"]["windows"][-1]["source_detection"]["bbox"]
    assert evidence["box"]["prompt_xywh_normalized"][0] == pytest.approx(
        [x1 / width, y1 / height, (x2 - x1) / width, (y2 - y1) / height]
    )
    assert evidence["point"]["prompt_center_point_normalized"][0] == pytest.approx(
        [(x1 + x2) / (2 * width), (y1 + y2) / (2 * height)]
    )


def test_gt_not_used_for_sam31_prompt(evidence):
    source = (ROOT / "src/memory_graph/v261/smoke.py").read_text(encoding="utf-8")
    assert evidence["experiment"]["inference_gt_access"] is False
    assert "review.md" not in source and "REVIEWED" not in source


def test_sam_specific_ids_never_become_persistent_ids(evidence):
    internal_ids = [value for row in evidence["box"]["outputs"] for value in row["object_ids"]]
    assert internal_ids and all(isinstance(value, int) for value in internal_ids)
    assert evidence["experiment"]["videos"]["test8"]["windows"][-1]["persistent_entity_id"] == "phone_01"


def test_provisional_match_cannot_reinitialize_sam21(evidence):
    log = read(ROOT / "outputs_v26/test7/sam_reinit_log.json")
    assert log["status"] == "NONE_AUTHORIZED"


def test_provisional_match_cannot_reinitialize_sam31(evidence):
    names = [window["name"] for window in evidence["experiment"]["videos"]["test7"]["windows"]]
    assert names == ["target_full"]
    assert evidence["summary"]["per_video"]["test7"]["status"].startswith("NOT_MEASURABLE")


def test_confirmed_match_can_reinitialize_sam21(evidence):
    log = read(ROOT / "outputs_v26/test8/sam_reinit_log.json")
    assert log["status"] == "EXECUTED" and log["authorized_by"] == "CONFIRMED_MATCH"
    assert log["segment"]["frames"][0] == evidence["sam21"]["frames"][0]


def test_confirmed_match_can_reinitialize_sam31(evidence):
    window = evidence["experiment"]["videos"]["test8"]["windows"][-1]
    assert window["authorization"] == "CONFIRMED_MATCH"
    assert window["init_frame"] == evidence["box"]["frames"][0]


def test_comparison_uses_same_review_frames(evidence):
    pytest.skip("No full paired predictions or post-freeze physical-target review were performed")


def test_drift_is_not_counted_as_coverage_success(evidence):
    metrics = evidence["summary"]["full_ablation_metrics"]
    assert metrics["correct_target_coverage"] is None
    assert metrics["raw_drift_events"] is None
    assert evidence["summary"]["smoke"]["sam31_box"]["nonempty_mask_count"] == 3


def test_runtime_hardware_is_identical(evidence):
    assert evidence["summary"]["same_gpu"] == evidence["environment"]["gpu"]["name"]
    assert evidence["sam21"]["frames"] == evidence["box"]["frames"]


def test_primary_comparison_does_not_mix_text_prompt_discovery(evidence):
    mapping = evidence["experiment"]["primary_prompt_mapping"]
    source = (ROOT / "src/memory_graph/v261/smoke.py").read_text(encoding="utf-8")
    assert "no concept text" in mapping
    assert '"text":' not in source
    assert evidence["box"]["prompt_xywh_normalized"]
    assert "smoke/smoke_math_max1_capacity16_frames8.json" in evidence["freeze"]["smoke_output_sha256"]


def test_prediction_freeze_precedes_manual_review(evidence):
    freeze = evidence["freeze"]
    assert freeze["stage"] == "PARTIAL_SMOKE_FROZEN_FULL_ABLATION_STOPPED"
    assert freeze["manual_review_started"] is False
    assert freeze["review_labels_read_by_inference"] is False
    for name, expected in freeze["smoke_output_sha256"].items():
        assert sha(OUT / name) == expected


def test_v26_outputs_are_read_only(evidence):
    experiment = evidence["experiment"]
    assert sha(ROOT / "outputs_v26/prediction_manifest.json") == experiment["v26_prediction_manifest_sha256"]
    assert sha(ROOT / "outputs_v25_rerun/prediction_manifest.json") == experiment["v25_prediction_manifest_sha256"]
    for task in (f"test{i}" for i in range(3, 10)):
        assert sha(ROOT / f"{task}.mp4") == experiment["videos"][task]["video_sha256"]
