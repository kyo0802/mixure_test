"""Record immutable inputs and isolated runtime facts before V2.6.1 inference."""
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
OUT = ROOT / "outputs_v261"
SAM31_REVISION = "2345a4ad109ac29c569da749c91d84f10dc08c40"
HF_REVISION = "daa63191845a41281374e725f4c9e51c7a824460"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def nvidia_query() -> dict:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version,compute_cap", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True,
    )
    name, total, free, driver, compute = [x.strip() for x in result.stdout.splitlines()[0].split(",")]
    return {"name": name, "total_mib": int(total), "free_mib_at_audit": int(free),
            "driver_version": driver, "compute_capability": compute}


def build_manifests() -> tuple[dict, dict]:
    baseline = read_json(ROOT / "outputs_v26" / "baseline_manifest.json")
    paths = {name: ROOT / name for name in baseline["video_sha256"]}
    video_hashes = {name: sha256(path) for name, path in paths.items()}
    if video_hashes != baseline["video_sha256"]:
        raise ValueError("Current videos do not match V2.6 frozen baseline")
    checkpoint = ROOT / ".models" / "sam3.1" / "sam3.1_multiplex.pt"
    if not checkpoint.is_file() or checkpoint.stat().st_size != 3502755717:
        raise ValueError("Official SAM 3.1 checkpoint missing or wrong size")
    gpu = nvidia_query()
    environment = {
        "schema": "v261_environment_1", "audited_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(), "python": platform.python_version(),
        "sam31_executable": sys.executable,
        "v26_environment": {"path": ".venv", "python": "3.12.8", "torch": "2.10.0+cu128",
                             "torchvision": "0.25.0+cu128", "cuda_runtime": "12.8",
                             "numpy": "2.5.3", "opencv_python": "4.14.0.94", "ultralytics": "8.4.158",
                             "huggingface_hub": "0.36.2", "mutated": False},
        "sam31_environment": {"path": ".venv_sam31", "torch": torch.__version__,
                              "torchvision": package("torchvision"), "cuda_runtime": torch.version.cuda,
                              "numpy": numpy.__version__, "opencv_python": cv2.__version__,
                              "sam3": package("sam3"), "timm": package("timm"),
                              "triton_windows": package("triton-windows"),
                              "flash_attn_3": package("flash-attn-3"),
                              "einops": package("einops"), "huggingface_hub": package("huggingface-hub")},
        "gpu": gpu,
        "sam21": {"repository": "facebookresearch/sam2", "revision": "2b90b9f5ceec907a1c18123530e92e794ad901a4",
                  "checkpoint": ".models/sam2.1_hiera_small.pt", "checkpoint_sha256": baseline["frozen_component_sha256"][".models/sam2.1_hiera_small.pt"],
                  "config": "configs/sam2.1/sam2.1_hiera_s.yaml"},
        "sam31": {"repository": "facebookresearch/sam3", "revision": SAM31_REVISION,
                  "model_repository": "facebook/sam3.1", "model_revision": HF_REVISION,
                  "checkpoint": ".models/sam3.1/sam3.1_multiplex.pt", "checkpoint_bytes": checkpoint.stat().st_size,
                  "checkpoint_sha256": sha256(checkpoint), "authenticated_head_authorized": True},
        "official_requirements": {"python": ">=3.12", "pytorch": ">=2.7", "cuda": ">=12.6"},
    }
    windows = {}
    for number in range(3, 10):
        task = f"test{number}"
        baseline_log_path = ROOT / "outputs_v25_rerun" / task / "sam" / "sam_continuity_log.json"
        reinit_log_path = ROOT / "outputs_v26" / task / "sam_reinit_log.json"
        baseline_log = read_json(baseline_log_path)
        reinit_log = read_json(reinit_log_path)
        items = []
        for segment in baseline_log["segments"]:
            init = next(e for e in segment["events"] if e["type"] == "INIT")
            items.append({"name": segment["segment"], "frames": segment["frames"],
                          "init_frame": init["frame_index"], "init_time": init["timestamp"],
                          "init_source": "frozen_yolo_detection",
                          "source_detection": init["frozen_yolo_detection"],
                          "persistent_entity_id": "phone_01", "sam21_local_id": init["object_id"]})
        if reinit_log["status"] == "EXECUTED":
            if reinit_log["authorized_by"] != "CONFIRMED_MATCH":
                raise ValueError(f"Unauthorized reinit in {task}")
            segment = reinit_log["segment"]
            init = next(e for e in segment["events"] if e["type"] == "INIT")
            items.append({"name": segment["segment"], "frames": segment["frames"],
                          "init_frame": init["frame_index"], "init_time": init["timestamp"],
                          "init_source": "v26_confirmed_match_frozen_yolo_detection",
                          "source_detection": init["frozen_yolo_detection"],
                          "persistent_entity_id": "phone_01", "sam21_local_id": init["object_id"],
                          "authorization": "CONFIRMED_MATCH"})
        elif task == "test7" and reinit_log["status"] != "NONE_AUTHORIZED":
            raise ValueError("test7 provisional candidate must not reinitialize SAM")
        windows[task] = {"video_sha256": video_hashes[f"{task}.mp4"],
                         "sam21_log": str(baseline_log_path.relative_to(ROOT)),
                         "sam21_log_sha256": sha256(baseline_log_path),
                         "v26_reinit_log": str(reinit_log_path.relative_to(ROOT)),
                         "v26_reinit_log_sha256": sha256(reinit_log_path),
                         "windows": items}
    experiment = {
        "schema": "v261_experiment_1", "created_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "PRE_INFERENCE_FROZEN_INPUTS", "inference_gt_access": False,
        "baseline_manifest_sha256": sha256(ROOT / "outputs_v26" / "baseline_manifest.json"),
        "v26_prediction_manifest_sha256": sha256(ROOT / "outputs_v26" / "prediction_manifest.json"),
        "v25_prediction_manifest_sha256": sha256(ROOT / "outputs_v25_rerun" / "prediction_manifest.json"),
        "videos": windows,
        "fixed": ["video", "YOLO model", "YOLO observations", "target binding", "candidate admission",
                  "appearance model", "Re-ID thresholds", "V2.6 authorization", "identity guard",
                  "review frames", "physical identity decisions"],
        "only_variable": "SAM21_BASELINE vs SAM31_MATCHED_PROMPT",
        "primary_prompt_mapping": "same frozen YOLO xyxy pixel box -> normalized xywh SAM 3.1 bounding_boxes; no concept text",
        "sam31_checkpoint_sha256": environment["sam31"]["checkpoint_sha256"],
        "sam31_repository_revision": SAM31_REVISION,
    }
    return environment, experiment


def main() -> None:
    OUT.mkdir(exist_ok=True)
    environment, experiment = build_manifests()
    for name, data in (("environment_manifest.json", environment), ("experiment_manifest.json", experiment)):
        (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("audited seven frozen videos and two isolated environments")


if __name__ == "__main__":
    main()
