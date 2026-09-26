"""Freeze all GT-free V2.6 decisions before reviewed identity evaluation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v26"
BASE = ROOT / "outputs_v25_rerun"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    baseline_path = OUT / "baseline_manifest.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if sha(BASE / "prediction_manifest.json") != baseline["v25_prediction_manifest_sha256"]:
        raise ValueError("V2.5 rerun manifest changed")
    for name, expected in baseline["video_sha256"].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"Video changed during V2.6: {name}")
    sources = ["src/memory_graph/v26/__init__.py", "src/memory_graph/v26/authorization.py",
               "src/memory_graph/v26/pipeline.py", "scripts/run_v26.py"]
    for name in sources:
        text = (ROOT / name).read_text(encoding="utf-8").lower()
        for prohibited in ("reviewed_cases", "ground_truth", "test7", "test8", "candidate_004", "candidate_009"):
            if prohibited in text:
                raise ValueError(f"Reviewed identity marker in inference source: {name}")
    artifacts = ("reid_audit.json", "candidate_stream.json", "candidate_grouping_audit.json",
                 "entity_registry.json", "sam_reinit_log.json", "identity_timeline.json")
    initial_path = OUT / "initial_blind" / "prediction_manifest.json"
    initial = json.loads(initial_path.read_text(encoding="utf-8"))
    if initial["stage"] != "A_BLIND_INFERENCE_COMPLETE" or initial["gt_read_before_freeze"]:
        raise ValueError("Initial V2.6 blind freeze unavailable")
    videos = {}
    for i in range(3,10):
        task = f"test{i}"
        files = {name: sha(OUT / task / name) for name in artifacts}
        audit = json.loads((OUT / task / "reid_audit.json").read_text(encoding="utf-8"))
        if audit["gt_accessed"]:
            raise ValueError(f"GT used during inference: {task}")
        original_audit = json.loads((OUT / "initial_blind" / task / "reid_audit.json").read_text(encoding="utf-8"))
        def categories(value):
            return [(attempt["frame_index"], row["candidate_entity_id"], row["decision"])
                    for attempt in value["attempts"] for row in attempt.get("candidate_decisions", [])]
        if categories(audit) != categories(original_audit) or audit["confirmed_match"] and not original_audit["confirmed_match"]:
            raise ValueError(f"Post-freeze registry cleanup changed Re-ID decisions: {task}")
        videos[task] = files
    payload = {"schema": "v26-prediction-freeze-2", "stage": "B_POSTFREEZE_PROVENANCE_REPAIR",
               "initial_blind_manifest_sha256": sha(initial_path),
               "initial_blind_predictions_frozen_before_gt": True,
               "postfreeze_repair_after_review": True,
               "gt_labels_used_in_repair": False,
               "categorical_reid_decisions_identical_to_initial_blind": True,
               "repair_scope": "remove inherited V2.5 merged candidate provenance from comparison registry and mark confirmed entity MATCHED",
               "baseline_manifest_sha256": sha(baseline_path),
               "inference_code_sha256": {name: sha(ROOT / name) for name in sources},
               "videos": videos}
    path = OUT / "prediction_manifest.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) not in (payload, initial):
        raise ValueError("Existing V2.6 prediction manifest differs from preserved initial blind freeze")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("V2.6 FROZEN", len(videos), sha(path))


if __name__ == "__main__":
    main()
