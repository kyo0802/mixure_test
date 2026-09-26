"""Pre-challenge source/parameter boundary check; reads no evaluation annotations."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v22.sam_tracking import ROOT
from memory_graph.v24.reid import locked_parameters


if __name__ == "__main__":
    files = [ROOT / "src/memory_graph/v24/appearance.py", ROOT / "src/memory_graph/v24/reid.py",
             ROOT / "scripts/prepare_reid_v24.py"]
    forbidden = ["evaluation/v21", "task1_annotations", "task2_annotations", "smartphone_01",
                 "correct_candidate", "ground_truth"]
    for path in files:
        text = path.read_text(encoding="utf-8")
        matches = [token for token in forbidden if token in text]
        if matches:
            raise SystemExit(f"GT isolation failure in {path}: {matches}")
    controls = json.loads((ROOT / "outputs_v24/cache/development_controls.json").read_text(encoding="utf-8"))
    if controls["heldout_task2_late_candidates_accessed"]:
        raise SystemExit("Held-out candidates accessed during development")
    _, manifest_hash = locked_parameters()
    print("GT isolation and parameter lock valid", manifest_hash)
