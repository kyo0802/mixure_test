"""Read-only hardware/runtime diagnostics; CUDA probes never load a model."""
from __future__ import annotations

import importlib.metadata
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def command(argv: list[str], timeout: int = 20) -> dict:
    try:
        result = subprocess.run(argv, capture_output=True, timeout=timeout)
        raw = result.stdout
        encoding = "utf-16-le" if b"\x00" in raw else "utf-8"
        return {"returncode": result.returncode, "stdout": raw.decode(encoding, errors="replace").strip(),
                "stderr": result.stderr.decode("utf-8", errors="replace").strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"returncode": None, "error": type(error).__name__, "message": str(error)}


def diagnose(*, cuda_probe: bool = False) -> dict:
    packages = {}
    for name in ("torch", "torchvision", "transformers", "accelerate", "vllm", "autoawq", "awq", "flash-attn", "qwen-vl-utils", "av", "timm", "mamba-ssm", "causal-conv1d"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "NOT_INSTALLED"
    data = {"os": platform.platform(), "python": sys.version, "executable": sys.executable,
            "packages": packages, "tools": {name: shutil.which(name) for name in ("uv", "ffmpeg", "ffprobe", "nvcc", "nvidia-smi", "wsl")},
            "gpu": command(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.free,memory.used,compute_cap", "--format=csv,noheader"]),
            "disk": {"total_bytes": shutil.disk_usage(Path.cwd()).total, "free_bytes": shutil.disk_usage(Path.cwd()).free},
            "wsl": command(["wsl", "--list", "--verbose"]) if platform.system() == "Windows" else {"status": "RUNNING_LINUX"},
            "cuda_toolkit_note": "NVIDIA-SMI driver capability does not establish an installed CUDA Toolkit",
            "model_inference_performed": False}
    try:
        import torch
        data["torch"] = {"version": torch.__version__, "cuda_runtime": torch.version.cuda,
                         "available": torch.cuda.is_available(), "architectures": torch.cuda.get_arch_list()}
        if cuda_probe:
            if not torch.cuda.is_available():
                data["kernel_probe"] = {"passed": False, "reason": "CUDA_UNAVAILABLE"}
            else:
                a = torch.arange(256, device="cuda", dtype=torch.float32).reshape(16, 16)
                b = a @ a.T
                torch.cuda.synchronize()
                data["kernel_probe"] = {"passed": bool(torch.isfinite(b).all().item()) and b[0, 0].item() == 1240,
                                        "operation": "16x16 float32 matmul", "compute_capability": list(torch.cuda.get_device_capability()),
                                        "memory_free_total_bytes": list(torch.cuda.mem_get_info())}
                del a, b
    except Exception as error:
        data["kernel_probe"] = {"passed": False, "reason": type(error).__name__, "message": str(error)}
    return data
