"""Freeze the unchanged V2.4 components before seven-video blind inference."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v241"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


if __name__ == "__main__":
    files = [
        "configs/v2_gpu_7b.yaml", "configs/default.yaml", "yolo11s.pt",
        ".models/sam2.1_hiera_small.pt", "outputs_v24/reid_parameter_manifest.json",
        "outputs_v24/cache/mobilenet_v3_small-047dcff4.pth",
        "src/memory_graph/perception/detector.py", "src/memory_graph/perception/tracker.py",
        "src/memory_graph/v21/pipeline.py", "src/memory_graph/v21/resolver.py",
        "src/memory_graph/v22/sam_tracking.py", "src/memory_graph/v23/fusion.py",
        "src/memory_graph/v24/appearance.py", "src/memory_graph/v24/reid.py",
    ]
    missing = [name for name in files if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError(missing)
    OUT.mkdir(exist_ok=True)
    payload = {
        "schema": "v241-frozen-baseline-1", "source_version": "V2.4",
        "parameter_manifest_sha256": digest(ROOT / "outputs_v24/reid_parameter_manifest.json"),
        "reid_match_threshold": .60, "reid_uniqueness_margin": .10,
        "component_sha256": {name: digest(ROOT / name) for name in files},
        "videos_sha256": {f"test{i}.mp4": digest(ROOT / f"test{i}.mp4") for i in range(3, 10)},
        "no_gt_in_inference": True,
        "extension_constraint": "Existing V2.2/V2.3/V2.4 runners hardcode task1/task2 and fixed frame seeds; V2.4.1 may adapt input routing and predeclare a GT-free generic seed policy, but frozen model/gates stay unchanged.",
    }
    path = OUT / "frozen_baseline_manifest.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != payload:
        raise ValueError("Frozen baseline changed")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(path)
