"""Fresh-video provenance and prediction-freeze checks for the isolated rerun."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v25_rerun"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_all_fresh_v21_inputs_match_current_videos():
    manifest = read(OUT / "prediction_manifest.json")
    assert len(manifest["videos"]) == 7
    for task, entry in manifest["videos"].items():
        actual = sha(ROOT / f"{task}.mp4")
        assert entry["video_sha256"] == actual
        assert read(OUT / task / "upstream_v21/run_status.json")["video_sha256"] == actual


def test_test5_updated_video_replaced_stale_detection_input():
    fresh = read(OUT / "test5/upstream_v21/run_status.json")
    old = read(ROOT / "outputs_v241/frozen_baseline_manifest.json")
    assert fresh["video_sha256"] == sha(ROOT / "test5.mp4")
    assert fresh["video_sha256"] != old["videos_sha256"]["test5.mp4"]
    assert read(OUT / "test5/target_binding_audit.json")["bound_target"]["frame_index"] == 96


def test_prediction_manifest_covers_all_rerun_artifacts():
    manifest = read(OUT / "prediction_manifest.json")
    assert manifest["stage"] == "A_BLIND_INFERENCE_COMPLETE" and not manifest["gt_read_before_freeze"]
    for task, entry in manifest["videos"].items():
        for name, expected in entry["predictions"].items():
            assert sha(OUT / task / name) == expected


def test_frozen_v24_reid_gates_preserved_in_rerun():
    architecture = read(OUT / "architecture_manifest.json")
    assert architecture["reid"]["minimum_match_similarity"] == .6
    assert architecture["reid"]["minimum_uniqueness_margin"] == .1
    for i in range(3, 10):
        audit = read(OUT / f"test{i}/reid_audit.json")
        assert not audit["gt_accessed"]
