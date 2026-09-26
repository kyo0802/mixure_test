"""Freeze GT-free outputs before evaluation-only scenario review."""
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


def isolation_check():
    for relative in ("src/memory_graph/v241/adapter.py", "scripts/run_v241_sam.py",
                     "scripts/run_v241_identity.py"):
        source = (ROOT / relative).read_text(encoding="utf-8").lower()
        for forbidden in ("test3: the target", "test4: the target", "scenario_gt",
                          "reviewed_identity", "evaluation/v241", "ground_truth"):
            if forbidden in source:
                raise ValueError(f"GT leakage marker in inference source: {relative}")


if __name__ == "__main__":
    isolation_check()
    baseline = json.loads((OUT / "frozen_baseline_manifest.json").read_text(encoding="utf-8"))
    for name, expected in baseline["component_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"Frozen V2.4 file changed: {name}")
    required = ("upstream_v21/prediction_manifest.json", "sam/sam_propagation_log.json",
                "identity_timeline.json", "reid_audit.json")
    videos = {}
    for i in range(3, 10):
        task = f"test{i}"
        paths = {name: OUT / task / name for name in required}
        for path in paths.values():
            if not path.exists():
                raise FileNotFoundError(path)
        videos[task] = {name: digest(path) for name, path in paths.items()}
    payload = {"schema": "v241-prediction-freeze-1", "stage": "A_BLIND_INFERENCE_COMPLETE",
               "gt_read_before_freeze": False, "baseline_manifest_sha256": digest(OUT / "frozen_baseline_manifest.json"),
               "inference_code_sha256": {name: digest(ROOT / name) for name in
                   ("src/memory_graph/v241/adapter.py", "scripts/run_v241_sam.py", "scripts/run_v241_identity.py")},
               "videos": videos}
    path = OUT / "prediction_manifest.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != payload:
        raise ValueError("Frozen prediction manifest changed")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Frozen {len(videos)} videos: {digest(path)}")
