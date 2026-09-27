"""Hash all label-blind predictions before physical-target review."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v262"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    stage = json.loads((OUT / "stage_a_feasibility.json").read_text(encoding="utf-8"))
    if stage["decision"] != "PASS":
        raise RuntimeError("Stage B was not authorized")
    manifest = json.loads((OUT / "experiment_manifest.json").read_text(encoding="utf-8"))
    files = {}
    counts = {}
    for task, spec in manifest["videos"].items():
        expected = sum(len(w["frames"]) for w in spec["windows"])
        for model in ("sam21", "sam3", "sam3point"):
            path = OUT / task / f"{model}_predictions.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["status"] != "COMPLETE" or not record["label_blind"]:
                raise RuntimeError(f"Incomplete or unblinded predictions: {path}")
            observations = [row for window in record["windows"].values() for row in window["observations"]]
            if len(observations) != expected:
                raise RuntimeError(f"Frame count mismatch: {path}")
            files[str(path.relative_to(ROOT)).replace("\\", "/")] = sha(path)
            for row in observations:
                mask = ROOT / row["mask"]
                files[row["mask"]] = sha(mask)
            counts[f"{task}_{model}"] = len(observations)
    result = {
        "schema": "v262_prediction_freeze_1", "freeze_utc": datetime.now(timezone.utc).isoformat(),
        "stage_a_decision": "PASS", "inference_code_read_labels": False,
        "operator_viewed_existing_v26_review_notes_before_freeze": True,
        "frozen_before_v262_mask_review": True, "input_manifest_sha256": sha(OUT / "experiment_manifest.json"),
        "prediction_files_sha256": files, "observation_counts": counts,
    }
    (OUT / "prediction_manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Frozen", len(files), "prediction and mask files")


if __name__ == "__main__":
    main()
