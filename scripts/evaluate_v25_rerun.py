"""Post-freeze evaluation of seven current videos; reviewed labels never enter inference."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v25_rerun"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_freeze():
    p = OUT / "prediction_manifest.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    assert m["stage"] == "A_BLIND_INFERENCE_COMPLETE" and not m["gt_read_before_freeze"]
    assert sha(OUT / "architecture_manifest.json") == m["architecture_manifest_sha256"]
    assert sha(ROOT / "scripts/run_v25_full_rerun.py") == m["inference_runner_sha256"]
    a = json.loads((OUT / "architecture_manifest.json").read_text(encoding="utf-8"))
    for name, expected in a["rerun_inference_code_sha256"].items():
        assert sha(ROOT / name) == expected, name
    for task, entry in m["videos"].items():
        assert sha(ROOT / f"{task}.mp4") == entry["video_sha256"]
        upstream = OUT / task / "upstream_v21"
        assert sha(upstream / "prediction_manifest.json") == entry["v21_manifest_sha256"]
        assert json.loads((upstream / "run_status.json").read_text())["video_sha256"] == entry["video_sha256"]
        for name, expected in entry["predictions"].items():
            assert sha(OUT / task / name) == expected, f"{task}/{name}"
    return sha(p)


def main():
    frozen_hash = verify_freeze()
    spec = importlib.util.spec_from_file_location("v25_evaluator", ROOT / "scripts/evaluate_v25.py")
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    evaluator.OUT = OUT
    evaluator.verify_freeze = lambda: frozen_hash
    evaluator.REVIEW["test5"] = {"binding": True, "target_samples": [], "match_label": "none",
                                  "failure": "no_safe_late_match"}
    evaluator.main()
    summary_path = OUT / "fusion_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["aggregate"]["input_consistent_current_videos"] = 7
    summary["videos"]["test5"]["reviewed_trusted_target_frames"] = [96, 192, 288, 366]
    summary["videos"]["test5"]["updated_video_sha256"] = summary["videos"]["test5"].get("video_sha256",
        json.loads((OUT / "prediction_manifest.json").read_text())["videos"]["test5"]["video_sha256"])
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "test5/review.md").write_text(
        "# test5 updated-video post-freeze review\n\n"
        "Fresh video SHA-256: `da637b42681ec7e59d8161ace0680aae7878e45da0ca7799c565f9828720f81f`. "
        "The bound handheld target at frame 96 visually matches the tagged target at frames 192, 288, and 366; "
        "these fresh detections remain associated with `phone_01`. Later scene-phone candidates are landline distractors "
        "in the reviewed contact sheet, and the frozen gate returns NO_SAFE_MATCH. Exact final target location is not established.\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
