"""Write immutable model/rule manifest before V2.5 video inference."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v25"


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


if __name__ == "__main__":
    files = ["configs/v2_gpu_7b.yaml", "configs/default.yaml", "yolo11s.pt",
             ".models/sam2.1_hiera_small.pt", "outputs_v24/reid_parameter_manifest.json",
             "outputs_v24/cache/mobilenet_v3_small-047dcff4.pth",
             "src/memory_graph/v22/sam_tracking.py", "src/memory_graph/v23/fusion.py",
             "src/memory_graph/v24/appearance.py", "src/memory_graph/v24/reid.py"]
    payload = {"schema": "v25-architecture-1", "frozen_component_sha256": {name: sha(ROOT/name) for name in files},
               "v241_prediction_manifest_sha256": sha(ROOT/"outputs_v241/prediction_manifest.json"),
               "v241_video_input_sha256": {f"test{i}.mp4": sha(ROOT/f"test{i}.mp4") for i in range(3,10)},
               "target_binding": {"minimum_observations": 3, "minimum_span_seconds": .4,
                                  "minimum_mean_confidence": .5, "tie_quality_margin": .1},
               "candidate_grouping": {"max_time_gap_seconds": .8, "minimum_box_iou": .30,
                                      "same_frame_distinct_iou_below": .10, "max_appearance_views": 4},
               "reid": {"minimum_match_similarity": .60, "minimum_uniqueness_margin": .10,
                        "minimum_evidence_prototypes": 2,
                        "candidate_view_policy": "highest-confidence available view, reevaluated after each new view; no GT ranking"},
               "sam": {"checkpoint": "sam2.1_hiera_small.pt", "step_frames": 6,
                       "target_span": "from online binding to end of sampled video",
                       "candidate_seed": "first eligible frozen YOLO local/raw phone box; selective short support"},
               "gt_isolation": "scenario descriptions and reviewed identities evaluation-only after prediction freeze"}
    path = OUT/"architecture_manifest.json"
    OUT.mkdir(exist_ok=True)
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != payload:
        raise ValueError("Architecture manifest already frozen with different content")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(sha(path))
