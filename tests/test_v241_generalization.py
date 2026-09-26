"""V2.4.1 frozen-evaluation isolation and conservative outcome checks."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v241"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluation_module():
    spec = importlib.util.spec_from_file_location("v241_evaluation_only", ROOT / "scripts" / "evaluate_v241.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v241_uses_frozen_v24_reid_parameters():
    original = read(ROOT / "outputs_v24" / "reid_parameter_manifest.json")
    baseline = read(OUT / "frozen_baseline_manifest.json")
    assert original["minimum_match_similarity"] == baseline["reid_match_threshold"] == .60
    assert original["minimum_uniqueness_margin"] == baseline["reid_uniqueness_margin"] == .10
    assert digest(ROOT / "outputs_v24" / "reid_parameter_manifest.json") == baseline["parameter_manifest_sha256"]


def test_v241_does_not_modify_v24_artifacts():
    baseline = read(OUT / "frozen_baseline_manifest.json")
    for name, expected in baseline["component_sha256"].items():
        assert digest(ROOT / name) == expected


def test_gt_not_accessible_before_prediction_freeze():
    manifest = read(OUT / "prediction_manifest.json")
    assert manifest["stage"] == "A_BLIND_INFERENCE_COMPLETE"
    assert manifest["gt_read_before_freeze"] is False
    for name in manifest["inference_code_sha256"]:
        source = (ROOT / name).read_text(encoding="utf-8").lower()
        assert "reviewed_cases" not in source
        assert "evaluate_v241" not in source


def test_prediction_manifest_written_before_evaluation():
    summary = read(OUT / "generalization_summary.json")
    assert summary["prediction_manifest_sha256_before_gt_review"] == digest(OUT / "prediction_manifest.json")
    assert evaluation_module().verify_predictions_frozen() == digest(OUT / "prediction_manifest.json")


def test_unobserved_phone_not_counted_as_detection_failure():
    classify = evaluation_module().detection_class
    assert classify(False, False) == "NOT_REVIEWABLE"
    assert classify(True, False) == "DETECTION_MISS"


def test_no_safe_match_is_valid():
    for i in range(3, 10):
        audit = read(OUT / f"test{i}" / "reid_audit.json")
        assert audit["decision"] == "NO_SAFE_MATCH"
        assert not any(a["decision"] == "MATCH" for a in audit["attempts"])


def test_final_unobserved_location_not_fabricated():
    for i in (3, 5, 6, 7, 9):
        review = read(OUT / f"test{i}" / "review.json")
        assert review["exact_final_location_directly_visible"] is False
        assert read(OUT / f"test{i}" / "identity_timeline.json")["target_entity"]["state"] == "UNOBSERVED"


def test_same_class_candidates_not_force_merged():
    test9 = read(OUT / "test9" / "reid_audit.json")
    assert len(test9["attempts"]) == 2
    assert all(a["decision"] == "AMBIGUOUS" for a in test9["attempts"])


def test_failure_attribution_separates_detection_tracking_reid():
    matrix = read(OUT / "failure_matrix.json")
    assert matrix["Detection"]["test6"] == "FAIL"
    assert matrix["Local tracking"]["test5"] == "FAIL"
    assert matrix["Re-ID"]["test8"] == "INSUFFICIENT_EVIDENCE"


def test_spatial_diagnostic_does_not_modify_inference():
    manifest = read(OUT / "prediction_manifest.json")
    for task, files in manifest["videos"].items():
        assert digest(OUT / task / "identity_timeline.json") == files["identity_timeline.json"]
        assert digest(OUT / task / "reid_audit.json") == files["reid_audit.json"]


def test_all_seven_videos_are_evaluated():
    expected = {f"test{i}" for i in range(3, 10)}
    assert set(read(OUT / "prediction_manifest.json")["videos"]) == expected
    assert read(OUT / "generalization_summary.json")["videos_evaluated"] == 7
    assert all((OUT / task / "review.md").is_file() and (OUT / task / "timeline.png").is_file()
               for task in expected)
