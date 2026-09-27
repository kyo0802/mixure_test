"""Freeze V2.6.2 inputs and write reproducible environment facts."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy
import torch


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v262"
SAM3_SOURCE_REVISION = "2345a4ad109ac29c569da749c91d84f10dc08c40"
SAM3_HF_REVISION = "3c879f39826c281e95690f02c7821c4de09afae7"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_text_hash_form(path: Path, expected: str) -> str | None:
    """The V2.6 manifest documents restoration of original CRLF text bytes."""
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() == expected:
        return "current_bytes"
    canonical_crlf = data.replace(bytes([13, 10]), bytes([10])).replace(bytes([10]), bytes([13, 10]))
    if hashlib.sha256(canonical_crlf).hexdigest() == expected:
        return "original_crlf_reconstruction"
    return None


def pkg(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> None:
    OUT.mkdir(exist_ok=True)
    prior = read(ROOT / "outputs_v261" / "experiment_manifest.json")
    baseline = read(ROOT / "outputs_v26" / "baseline_manifest.json")
    video_hashes = {name: sha(ROOT / name) for name in baseline["video_sha256"]}
    if video_hashes != baseline["video_sha256"]:
        raise ValueError("Seven videos differ from the frozen V2.6 baseline")
    frozen_text_forms = {}
    for task, record in prior["videos"].items():
        if record["video_sha256"] != video_hashes[f"{task}.mp4"]:
            raise ValueError(f"Frozen V2.6.1 video hash mismatch: {task}")
        for key, path_key in (("sam21_log_sha256", "sam21_log"), ("v26_reinit_log_sha256", "v26_reinit_log")):
            if sha(ROOT / record[path_key]) != record[key]:
                raise ValueError(f"Frozen evidence changed: {task} {path_key}")
        sam_log = read(ROOT / record["sam21_log"])
        frozen_text_forms[task] = {}
        for filename, expected in sam_log["frozen_input_sha256"].items():
            path = ROOT / "outputs_v25_rerun" / task / "upstream_v21" / "event_analysis" / filename
            form = frozen_text_hash_form(path, expected)
            if form is None:
                raise ValueError(f"Frozen YOLO input changed: {path}")
            frozen_text_forms[task][filename] = form
    ckpt = ROOT / ".models" / "sam3" / "sam3.pt"
    if ckpt.name != "sam3.pt" or ckpt.stat().st_size != 3450062241:
        raise ValueError("Official SAM 3 checkpoint absent or incorrect size")
    source = ROOT / ".sam31_official"
    revision = subprocess.run(["git", "-c", f"safe.directory={source.as_posix()}", "-C", str(source), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    if revision != SAM3_SOURCE_REVISION:
        raise ValueError("Official SAM 3 source revision changed")
    smi = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version,compute_cap", "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True)
    name, total, driver, compute = [v.strip() for v in smi.stdout.strip().split(",")]
    smoke = read(OUT / "smoke" / "sam3" / "result.json")
    if smoke["checkpoint_sha256"] != sha(ckpt):
        raise ValueError("Smoke used a different checkpoint")
    environment = {
        "schema": "v262_environment_1", "audited_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(), "python": platform.python_version(), "executable": sys.executable,
        "torch": torch.__version__, "torchvision": pkg("torchvision"), "cuda_runtime": torch.version.cuda,
        "numpy": numpy.__version__, "opencv": cv2.__version__, "sam3_package": pkg("sam3"),
        "triton_windows": pkg("triton-windows"), "flash_attn_3": pkg("flash-attn-3"),
        "gpu": {"name": name, "vram_mib": int(total), "driver": driver, "compute_capability": compute},
        "sam3": {"source_repository": "https://github.com/facebookresearch/sam3", "source_revision": SAM3_SOURCE_REVISION,
                 "source_checkout": ".sam31_official (same official Meta revision, installed as isolated wheel)",
                 "checkpoint_repository": "facebook/sam3", "checkpoint_revision": SAM3_HF_REVISION,
                 "checkpoint": ".models/sam3/sam3.pt", "checkpoint_bytes": ckpt.stat().st_size,
                 "checkpoint_sha256": sha(ckpt), "builder": "build_sam3_predictor(version='sam3')",
                 "predictor": smoke.get("predictor_type"), "model": smoke.get("model_type"),
                 "attention_backend_executed": smoke.get("attention_backend"), "attention_ops": smoke.get("attention_ops")},
        "sam21": read(ROOT / "outputs_v261" / "environment_manifest.json")["sam21"],
        "v26_environment_modified": False, "v261_environment_modified": False,
    }
    experiment = {
        "schema": "v262_experiment_1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "STAGE_A_COMPLETE_PRE_STAGE_B", "inference_gt_access": False,
        "baseline_manifest_sha256": sha(ROOT / "outputs_v26" / "baseline_manifest.json"),
        "v26_prediction_manifest_sha256": sha(ROOT / "outputs_v26" / "prediction_manifest.json"),
        "v261_experiment_manifest_sha256": sha(ROOT / "outputs_v261" / "experiment_manifest.json"),
        "videos": prior["videos"], "fixed": prior["fixed"],
        "frozen_yolo_text_hash_forms": frozen_text_forms,
        "only_variable": "SAM21 vs SAM3", "primary_prompt_mapping": "same frozen YOLO xyxy -> SAM3 normalized xywh box; no concept text",
        "sam3_selection": "one SAM-local ID chosen by maximum prompt-frame bbox IoU with frozen YOLO box; fixed across propagation; no labels",
        "sam3_checkpoint_sha256": environment["sam3"]["checkpoint_sha256"],
        "sam3_repository_revision": SAM3_SOURCE_REVISION,
    }
    (OUT / "environment_manifest.json").write_text(json.dumps(environment, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "experiment_manifest.json").write_text(json.dumps(experiment, indent=2, ensure_ascii=False), encoding="utf-8")
    print("V2.6.2 seven-video hashes and official SAM 3 environment audited")


if __name__ == "__main__":
    main()
