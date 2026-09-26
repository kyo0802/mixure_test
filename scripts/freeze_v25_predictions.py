"""Hash all GT-free V2.5 predictions before loading reviewed identities."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v25"


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            value.update(block)
    return value.hexdigest()


def verify_inference_isolation():
    inference = ["src/memory_graph/v25/binding.py", "src/memory_graph/v25/candidates.py",
                 "src/memory_graph/v25/sam_route.py", "src/memory_graph/v25/fusion.py",
                 "src/memory_graph/v25/pipeline.py", "src/memory_graph/v25/reid.py",
                 "scripts/run_v25_sam_target.py", "scripts/run_v25_admission.py",
                 "scripts/run_v25_candidate_sam.py", "scripts/run_v25_reid.py"]
    for name in inference:
        source = (ROOT/name).read_text(encoding="utf-8").lower()
        for prohibited in ("reviewed_cases", "evaluate_v25", "evaluation/v25",
                           "ground_truth", "scenario_gt", "test5 wrong", "test8 target"):
            if prohibited in source:
                raise ValueError(f"GT marker in inference path: {name}")
    return {name: sha(ROOT/name) for name in inference}


if __name__ == "__main__":
    code_hashes = verify_inference_isolation()
    architecture = json.loads((OUT/"architecture_manifest.json").read_text(encoding="utf-8"))
    for name, expected in architecture["frozen_component_sha256"].items():
        if sha(ROOT/name) != expected:
            raise ValueError(f"Frozen baseline changed: {name}")
    if sha(ROOT/"outputs_v241/prediction_manifest.json") != architecture["v241_prediction_manifest_sha256"]:
        raise ValueError("V2.4.1 prediction manifest changed")
    names = ("target_binding_audit.json", "candidate_stream.json", "candidate_grouping_audit.json",
             "reid_audit.json", "entity_registry.json", "identity_timeline.json",
             "sam/sam_continuity_log.json", "sam/candidate_sam_support.json", "sam_reinit_log.json")
    videos = {}
    for i in range(3,10):
        task = f"test{i}"
        task_files = {name: OUT/task/name for name in names}
        if i == 8:
            task_files["contact_sheet.png"] = OUT/task/"contact_sheet.png"
        for path in task_files.values():
            if not path.is_file():
                raise FileNotFoundError(path)
        videos[task] = {name: sha(path) for name,path in task_files.items()}
    payload = {"schema":"v25-prediction-freeze-1", "stage":"A_BLIND_INFERENCE_COMPLETE",
               "gt_read_before_freeze":False, "architecture_manifest_sha256":sha(OUT/"architecture_manifest.json"),
               "inference_code_sha256":code_hashes, "videos":videos}
    path = OUT/"prediction_manifest.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != payload:
        raise ValueError("Existing V2.5 prediction manifest changed")
    path.write_text(json.dumps(payload,indent=2),encoding="utf-8")
    print("frozen",len(videos),sha(path))
