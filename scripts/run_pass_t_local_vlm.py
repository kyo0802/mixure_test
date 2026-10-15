"""Safe diagnostics/config/preflight CLI; never loads a VLM."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in ("src", "artifacts/pass_i/runtime/vendor"):
    sys.path.insert(0, str(ROOT / relative))
from memory_graph.pass_t.phase2b.common import file_sha256, exclusive_tree, pretty_bytes, read_json
from memory_graph.pass_t.phase2b.local_vlm.catalog import SPECS
from memory_graph.pass_t.phase2b.local_vlm.diagnostics import diagnose
from memory_graph.pass_t.phase2b.config import unresolved_template

OUT = ROOT / "artifacts/pass_t/phase2b/local_vlm/v1"

def snapshot():
    names = set()
    for base in (ROOT / "src/memory_graph/pass_t", ROOT / "artifacts/pass_t/phase2b"):
        for p in base.rglob("*"):
            relative = p.relative_to(ROOT).as_posix()
            if (p.is_file() and "/local_vlm/" not in relative and "__pycache__" not in relative
                    and "/test_tmp" not in relative and "/.staging/" not in relative):
                names.add(relative)
    names.update(["scripts/run_pass_t_phase2b.py", "scripts/pass_t_phase2b_preflight.py", "tests/test_pass_t_phase2b.py"])
    hashes = {name: file_sha256(ROOT / name) for name in sorted(names)}
    return {"schema_version": "PASS_T_LOCAL_PREFLIGHT_V1", "files_sha256": hashes,
            "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
            "index_diff_sha256": hashlib.sha256(subprocess.check_output(["git", "diff", "--cached", "--binary"], cwd=ROOT)).hexdigest()}

def prepare():
    files = {}
    template = read_json(ROOT / "artifacts/pass_t/phase2b/config/protocol_decisions.template.json")
    proposed = {**template, "multi_image_frame_count": 6, "storyboard_frame_count": 6, "storyboard_columns": 3,
                "video_fps": 30, "event_time_tolerance_s": 0.2, "bounded_interval_overlap_required": True,
                "repeat_count": 1, "budget_limit_usd": 0, "run_order": ["MULTI_IMAGE", "STORYBOARD"]}
    files["protocol_decisions.proposed.json"] = pretty_bytes(proposed)
    for index, spec in enumerate(SPECS.values()):
        config = unresolved_template()
        config.update(provider="LOCAL_ONLY", backend=spec.backend, model=spec.model, revision=spec.revision,
                      execution_location="LOCAL", modalities=["image", "video"] if spec.key != "nemotron_nvfp4" else ["image"])
        config["generation"] = {"temperature": 0.0, "sampling": False, "seed": 42, "max_output_tokens": 1024}
        config["transport"] = {"timeout_seconds": 180, "max_retries": 0, "monetary_budget_usd": 0}
        config["limits"] = {"max_images": 6 if spec.key != "nemotron_nvfp4" else 1, "max_pixels_per_image": 401408, "context_tokens": 8192}
        for rep, cap in config["capabilities"].items():
            cap["status"] = "UNKNOWN" if rep in spec.documented else "UNSUPPORTED"
            cap["evidence"] = "Official documentation only; exact local runtime not smoke-tested"
        files[f"{spec.key}/model_config.candidate.json"] = pretty_bytes(config)
        deployment = {"schema_version": "PASS_T_LOCAL_DEPLOYMENT_V1", "endpoint": f"http://127.0.0.1:{8765 + index}",
                      "quantization": spec.quantization, "approved_representations": [], "max_images": config["limits"]["max_images"],
                      "max_frames": 6, "max_input_pixels": 921600, "processor_max_pixels": 401408,
                      "attention": "sdpa", "max_gpu_memory_gib": 12, "cpu_offload": "UNRESOLVED",
                      "snapshot_path": None, "approved": False}
        files[f"{spec.key}/deployment.candidate.json"] = pretty_bytes(deployment)
        files[f"{spec.key}/decision_status.json"] = pretty_bytes({
            "VERIFIED": ["exact public model repository", "checkpoint revision", "public weight byte count"],
            "PROPOSED": ["16GB resource budgets", "generation", "sampling", "reference NONE", "localhost transport", "separate environment"],
            "UNRESOLVED": ["runtime engine version lock", "GPU quantization kernel", "actual VRAM fit", "processor alias mapping", "end-to-end JSON", "model smoke authorization"],
            "model": spec.model, "quantization": spec.quantization, "never_substitute": True})
    return exclusive_tree(OUT / "candidates", files, {"schema_version": "PASS_T_LOCAL_CANDIDATES_V1", "status": "PROPOSED_NOT_APPROVED_NOT_FROZEN"})

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preflight", "diagnostics", "prepare-configs"])
    parser.add_argument("--cuda-probe", action="store_true")
    args = parser.parse_args()
    if args.command == "preflight":
        folder = exclusive_tree(OUT / "preflight", {"baseline.json": pretty_bytes(snapshot())}, {"schema_version": "PASS_T_LOCAL_PREFLIGHT_RECEIPT_V1"})
    elif args.command == "diagnostics":
        folder = exclusive_tree(OUT / "diagnostics", {"hardware.json": pretty_bytes(diagnose(cuda_probe=args.cuda_probe))}, {"schema_version": "PASS_T_LOCAL_DIAGNOSTICS_RECEIPT_V1", "model_loaded": False})
    else:
        folder = prepare()
    print(json.dumps({"status": "SAFE_ENGINEERING_ONLY", "path": str(folder)}))

if __name__ == "__main__":
    main()
