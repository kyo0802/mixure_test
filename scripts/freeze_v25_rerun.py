"""Freeze fresh seven-video V2.5 predictions before reviewed evaluation."""
import hashlib
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


def main():
    architecture_path = OUT / "architecture_manifest.json"
    architecture = json.loads(architecture_path.read_text(encoding="utf-8"))
    for name, expected in architecture["frozen_component_sha256"].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"Frozen component changed: {name}")
    for name, expected in architecture["rerun_inference_code_sha256"].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"Rerun inference code changed: {name}")
    video_hashes = architecture["current_video_sha256"]
    videos = {}
    artifacts = ("target_binding_audit.json", "candidate_stream.json", "candidate_grouping_audit.json",
                 "reid_audit.json", "entity_registry.json", "identity_timeline.json",
                 "sam/sam_continuity_log.json", "sam/candidate_sam_support.json", "sam_reinit_log.json")
    for i in range(3, 10):
        task = f"test{i}"
        video = ROOT / f"{task}.mp4"
        if sha(video) != video_hashes[video.name]:
            raise ValueError(f"Video changed since architecture freeze: {task}")
        upstream = OUT / task / "upstream_v21"
        status = json.loads((upstream / "run_status.json").read_text(encoding="utf-8"))
        if status["status"] != "complete" or status["video_sha256"] != video_hashes[video.name] or status["gt_used"]:
            raise ValueError(f"V2.1 input not fresh/complete: {task}")
        v21_manifest = json.loads((upstream / "prediction_manifest.json").read_text(encoding="utf-8"))
        for name in ("event_analysis/detections.json", "event_analysis/track_timelines.json",
                     "event_analysis/video_metadata.json", "persistent_entities.json"):
            if sha(upstream / name) != v21_manifest[name]:
                raise ValueError(f"V2.1 artifact changed: {task}/{name}")
        files = {name: sha(OUT / task / name) for name in artifacts}
        if i == 8:
            files["contact_sheet.png"] = sha(OUT / task / "contact_sheet.png")
        videos[task] = {"video_sha256": video_hashes[video.name], "v21_manifest_sha256": sha(upstream / "prediction_manifest.json"),
                        "predictions": files}
    result = {"schema": "v25-full-rerun-prediction-freeze-1", "stage": "A_BLIND_INFERENCE_COMPLETE",
              "gt_read_before_freeze": False, "architecture_manifest_sha256": sha(architecture_path),
              "inference_runner_sha256": sha(ROOT / "scripts/run_v25_full_rerun.py"), "videos": videos}
    path = OUT / "prediction_manifest.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != result:
        raise ValueError("Existing rerun prediction freeze differs")
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("FROZEN", len(videos), sha(path))


if __name__ == "__main__":
    main()
