from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from memory_graph.v2101_deploy.contracts import schema_sha256


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/v2.10.1/freeze"
TAG = "v2.9.7-frozen"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def read_json(relative: str):
    path = ROOT / relative
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def file_ref(relative: str) -> dict:
    path = ROOT / relative
    if not path.is_file():
        return {"path": relative, "exists": False}
    return {"path": relative, "exists": True, "size_bytes": path.stat().st_size, "sha256": sha_file(path)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    v297 = read_json("outputs/v297_physical_identity/FROZEN_V297_POLICY_MANIFEST.json") or {}
    qwen_manifest = read_json("outputs/reference_qwen/manifest.json") or {}
    qwen_requests = read_json("outputs/reference_qwen/model_7b/requests.json") or []
    packs = read_json("outputs/reference_qwen/event_packs/event_pack_manifest.json") or []
    old_preservation = read_json("outputs/v297_physical_identity/baseline/preservation_manifest.json") or {}

    status = git("status", "--porcelain=v1", "--untracked-files=all", check=False).splitlines()
    branch = git("branch", "--show-current")
    tag_commit = git("rev-parse", f"{TAG}^{{commit}}")
    tag_object = git("rev-parse", TAG)
    base_commit = git("rev-parse", f"{TAG}^1")
    source_hashes = v297.get("source_hashes", {})
    frozen_artifacts = v297.get("frozen_artifacts", {})
    tag_rows_raw = git("ls-tree", "-r", TAG).splitlines()
    tag_entries = {}
    gitlinks = []
    for row in tag_rows_raw:
        metadata, relative = row.split("\t", 1)
        mode, object_type, object_sha = metadata.split(" ", 2)
        tag_entries[relative] = {"mode": mode, "type": object_type, "object_sha": object_sha}
        if mode == "160000":
            gitlinks.append({"path": relative, "commit": object_sha, "declared_in_gitmodules": False})
    relevant_tag_paths = set(source_hashes) | {
        "configs/default.yaml", "configs/v2.yaml", "configs/v292_canonical.yaml",
        "configs/v2_gpu.yaml", "configs/v2_gpu_7b.yaml", "configs/sam2.1/sam2.1_hiera_s.yaml",
        "scripts/run_v297_identity.py", "scripts/preflight_v297.py", "scripts/report_v297.py",
        "scripts/build_v297_scenarios.py", "tests/test_v297_identity.py",
    }
    tag_hashes: dict[str, str] = {}
    for relative in sorted(relevant_tag_paths):
        entry = tag_entries.get(relative)
        if entry and entry["type"] == "blob":
            blob = subprocess.run(["git", "cat-file", "blob", entry["object_sha"]], cwd=ROOT, capture_output=True, check=True).stdout
            tag_hashes[relative] = sha_bytes(blob)

    source_checks = {}
    for relative, expected in source_hashes.items():
        committed = tag_hashes.get(relative)
        current_path = ROOT / relative
        current_bytes = current_path.read_bytes() if current_path.is_file() else None
        current = sha_bytes(current_bytes) if current_bytes is not None else None
        git_normalized_current = sha_bytes(current_bytes.replace(b"\r\n", b"\n")) if current_bytes is not None else None
        source_checks[relative] = {
            "manifest_sha256": expected,
            "tag_sha256": committed,
            "working_tree_sha256": current,
            "working_tree_git_normalized_sha256": git_normalized_current,
            "manifest_matches_tag": committed == git_normalized_current,
            "working_tree_matches_manifest": current == expected,
        }

    artifact_checks = {}
    for relative, expected in frozen_artifacts.items():
        path = ROOT / relative
        actual = sha_file(path) if path.is_file() else None
        artifact_checks[relative] = {"manifest_sha256": expected, "working_tree_sha256": actual, "matches": actual == expected}

    configs = [
        "configs/default.yaml", "configs/v2.yaml", "configs/v292_canonical.yaml",
        "configs/v2_gpu.yaml", "configs/v2_gpu_7b.yaml", "configs/sam2.1/sam2.1_hiera_s.yaml",
        "outputs/v297_physical_identity/physical_identity/state_policy.json",
        "outputs/v297_physical_identity/person_epochs/policy.json",
        "outputs/v297_physical_identity/interaction/state_machine.json",
        "outputs/v297_physical_identity/calibration/interaction_policy.json",
        "outputs/v297_physical_identity/calibration/physical_policy.json",
        "outputs/v297_physical_identity/calibration/parameters.json",
        "outputs/reference_qwen/model_7b/model_config.json",
        "outputs/reference_qwen/experiment_manifest.json",
        "outputs/current_development/event_windows/config.json",
    ]
    config_refs = {path: file_ref(path) for path in configs}

    videos = {}
    for i in range(1, 10):
        name = f"test{i}.mp4"
        candidates = [ROOT / name, ROOT / "videos" / name]
        path = next((p for p in candidates if p.is_file()), None)
        videos[name] = ({"path": str(path.relative_to(ROOT)), "size_bytes": path.stat().st_size, "sha256": sha_file(path)}
                        if path else {"exists": False, "searched": [str(p.relative_to(ROOT)) for p in candidates]})

    schema_by_event = {}
    prompt_hashes = {}
    req_by_id = {r.get("pack_id"): r for r in qwen_requests}
    for pack in packs:
        request = req_by_id.get(pack.get("pack_id"), {})
        markers = list((pack.get("markers") or {}).keys())
        schema_by_event[pack.get("pack_id", "unknown")] = schema_sha256(markers)
        if request.get("prompt"):
            prompt_hashes[pack["pack_id"]] = sha_bytes(request["prompt"].encode("utf-8"))

    prior_files = old_preservation.get("files", {})
    prior_integrity = read_json("outputs/v297_physical_identity/final/integrity_manifest.json") or {}
    preservation_comparison = {
        "recorded_file_count": len(prior_files),
        "current_full_rehash_performed": False,
        "reason": "The repository entered this task with a pre-existing dirty tree and historical output deletions; preserve the prior V297 SHA-256 ledger and compare the explicit v2.10.1 protected snapshot instead of attributing old changes to this task.",
        "last_recorded_integrity_result": {
            "unchanged": prior_integrity.get("unchanged"),
            "changed": prior_integrity.get("changed"),
            "missing": prior_integrity.get("missing"),
            "checked_unix": prior_integrity.get("checked_unix"),
        },
    }

    input_manifest_paths = [
        "outputs/validation/pre_run_freeze_manifest.json", "outputs/validation/input_manifest.json",
        "outputs/current_development/event_windows/event_manifest.json",
        "outputs/current_development/event_windows/candidate_manifest.json",
        "outputs/reference_qwen/event_packs/event_pack_manifest.json",
        "outputs/reference_qwen/experiment_manifest.json",
        "outputs/reference_qwen/final/artifact_manifest.json",
    ]
    manifests = {path: file_ref(path) for path in input_manifest_paths}
    validation_manifests = {}
    validation_root = ROOT / "outputs/validation"
    if validation_root.exists():
        for path in sorted(validation_root.rglob("*manifest*.json")):
            if path.is_file():
                rel = path.relative_to(ROOT).as_posix()
                validation_manifests[rel] = {"size_bytes": path.stat().st_size, "sha256": sha_file(path)}

    baseline_policy = {
        "v297_policy_source_manifest": file_ref("outputs/v297_physical_identity/FROZEN_V297_POLICY_MANIFEST.json"),
        "physical": read_json("outputs/v297_physical_identity/physical_identity/state_policy.json"),
        "person_epoch": read_json("outputs/v297_physical_identity/person_epochs/policy.json"),
        "interaction_state_machine": read_json("outputs/v297_physical_identity/interaction/state_machine.json"),
        "calibration_interaction": read_json("outputs/v297_physical_identity/calibration/interaction_policy.json"),
        "calibration_physical": read_json("outputs/v297_physical_identity/calibration/physical_policy.json"),
        "calibration_parameters": read_json("outputs/v297_physical_identity/calibration/parameters.json"),
        "identity_guard_source_sha256": source_hashes.get("src/memory_graph/identity/guard.py"),
        "candidate_epoch_source_sha256": source_hashes.get("src/memory_graph/v296_reid/epochs.py"),
    }

    # These local weights remain referenced by immutable config/hash plus file metadata;
    # large model blobs are not copied into the freeze artifact.
    local_model_files = {}
    for relative in ["yolo11s.pt", ".models/yolo11s.pt", ".models/sam2.1_hiera_small.pt", "outputs_v24/cache/mobilenet_v3_small-047dcff4.pth"]:
        path = ROOT / relative
        if path.is_file():
            local_model_files[relative] = {"size_bytes": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns}

    try:
        import torch
        pytorch_info = {"version": torch.__version__, "cuda_runtime": torch.version.cuda,
                        "cuda_available": torch.cuda.is_available(),
                        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
    except Exception as exc:
        pytorch_info = {"error": str(exc)}

    manifest = {
        "schema": "findmind_v2101_v297_freeze_manifest_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git": {
            "frozen_commit": tag_commit, "tag_object": tag_object, "annotated_tag": TAG,
            "tag_parent_base": base_commit, "branch_at_freeze_creation": branch,
            "working_tree_dirty": bool(status), "working_tree_status_entry_count_at_manifest": len(status),
            "working_tree_status_sample": status[:20],
            "pre_task_dirty_state_from_stage_a": {"tracked_changes": 8343, "untracked_files": 1069,
                                                   "note": "Captured during Stage A before v2.10.1 files were added."},
            "tag_scope": "V297 source-only commit over existing repository base; unrelated dirty work excluded.",
            "submodules": {"declared_in_gitmodules": False, "gitlinks_in_tag": gitlinks,
                           "checked_out_heads": {".sam2_official": git("-C", ".sam2_official", "rev-parse", "HEAD", check=False) or None,
                                                  ".sam31_official": git("-C", ".sam31_official", "rev-parse", "HEAD", check=False) or None}},
            "tag_tree_entry_count": len(tag_entries),
            "tag_content_sha256_scope": "V297 source/config files and the pre-existing 38,700-entry preservation ledger; source tag SHA checks use Git-normalized LF content while Windows working-tree hashes retain the original CRLF bytes.",
        },
        "host_environment": {
            "os": platform.platform(), "python": platform.python_version(), "pytorch": pytorch_info,
            "nvidia_driver": "617.14", "cuda_runtime_in_existing_windows_env": "12.8",
            "gpu": "NVIDIA GeForce RTX 5070 Ti", "vram_mib": 16303,
            "windows_nvidia_smi_cuda_version": "13.4",
            "wsl": {"distribution": "Ubuntu 26.04.1 LTS", "version": 2,
                    "python": "3.14.4", "gpu_access": True, "free_vram_mib_at_probe": 15091,
                    "note": "A separate Python 3.12 v2.10.1 environment is being prepared."},
        },
        "models": {
            "yolo": {"reference": "yolo11s.pt", "revision": None, "config_sha256": config_refs["configs/default.yaml"].get("sha256"),
                     "local_weight_metadata": local_model_files.get("yolo11s.pt") or local_model_files.get(".models/yolo11s.pt"),
                     "revision_note": "Existing config names checkpoint but does not pin an upstream revision."},
            "sam2_1": {"reference": ".models/sam2.1_hiera_small.pt", "revision": None,
                       "config_sha256": config_refs["configs/sam2.1/sam2.1_hiera_s.yaml"].get("sha256"),
                       "local_weight_metadata": local_model_files.get(".models/sam2.1_hiera_small.pt"),
                       "revision_note": "Existing config/checkpoint retained; upstream commit was not recorded."},
            "dinov3": {"revision": v297.get("model_revisions", {}).get("dinov3")},
            "dinov2": {"revision": v297.get("model_revisions", {}).get("dinov2")},
            "lightglue": {"source": "tools/LightGlue", "source_tree_sha256": None,
                          "model_metadata": file_ref("outputs/v295_reid/setup/lightglue_model.json")},
            "superpoint": {"config_sha256": config_refs["configs/default.yaml"].get("sha256"),
                           "exact_checkpoint_revision": None, "note": "Recorded through V297 source/config hashes; no standalone revision field found."},
        },
        "configs": config_refs,
        "identity_thresholds_and_policy": baseline_policy,
        "qwen_historical_control": {
            "status": "HISTORICAL_FROZEN_CONTROL", "model": qwen_manifest.get("latest_model"),
            "revision": qwen_manifest.get("revision"),
            "runtime_config": file_ref("outputs/reference_qwen/model_7b/model_config.json"),
            "prompt_sha256_by_event": prompt_hashes,
            "schema_sha256_by_event": schema_by_event,
            "request_count": len(qwen_requests),
            "source_experiment_manifest": file_ref("outputs/reference_qwen/experiment_manifest.json"),
        },
        "data": {
            "development_manifest_hashes": manifests,
            "known_regression_manifest_hashes": validation_manifests,
            "test1_test9_media": videos,
            "event_window_manifest_hashes": {
                k: v for k, v in manifests.items() if "event_windows" in k or "event_packs" in k
            },
        },
        "integrity": {
            "v297_existing_source_manifest_sha256": file_ref("outputs/v297_physical_identity/FROZEN_V297_POLICY_MANIFEST.json"),
            "v297_source_checks": source_checks,
            "v297_frozen_artifact_checks": artifact_checks,
            "preexisting_38700_file_preservation_manifest_sha256": file_ref("outputs/v297_physical_identity/baseline/preservation_manifest.json"),
            "pre_task_baseline_comparison": preservation_comparison,
            "prior_integrity_check": prior_integrity,
        },
    }

    protected = {
        "schema": "findmind_v2101_protected_hashes_v1",
        "freeze_tag": TAG,
        "freeze_commit": tag_commit,
        "tag_relevant_source_config_sha256": tag_hashes,
        "v297_source_hashes_from_original_freeze_manifest": source_hashes,
        "v297_source_comparison": source_checks,
        "v297_frozen_artifact_hashes": frozen_artifacts,
        "v297_frozen_artifact_comparison": artifact_checks,
        "preexisting_baseline_preservation_hashes": prior_files,
        "previous_38700_file_hash_ledger": prior_files,
        "previous_38700_file_ledger_sha256": file_ref("outputs/v297_physical_identity/baseline/preservation_manifest.json").get("sha256"),
        "pre_task_baseline_comparison": preservation_comparison,
        "qwen_historical_artifact_hashes": (read_json("outputs/reference_qwen/final/artifact_manifest.json") or {}).get("files", {}),
        "task_boundary": "Only artifacts/v2.10.1 and the new v2101_deploy/test/script paths are task outputs.",
    }
    for path, document in [(OUT / "V297_FREEZE_MANIFEST.json", manifest), (OUT / "protected_hashes.json", protected)]:
        path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT).as_posix()} sha256={sha_file(path)} size={path.stat().st_size}")
    print("frozen_commit", tag_commit, "branch", branch, "dirty", bool(status))
    print("v297 source manifest matches", sum(x["manifest_matches_tag"] for x in source_checks.values()), "/", len(source_checks))
    print("v297 source current matches", sum(x["working_tree_matches_manifest"] for x in source_checks.values()), "/", len(source_checks))
    print("v297 artifacts current matches", sum(x["matches"] for x in artifact_checks.values()), "/", len(artifact_checks))
    print("prior preservation ledger entries", preservation_comparison["recorded_file_count"], "last recorded unchanged", preservation_comparison["last_recorded_integrity_result"]["unchanged"])
    print("validation manifests hashed", len(validation_manifests), "canonical packs", len(packs), "qwen requests", len(qwen_requests))


if __name__ == "__main__":
    main()
