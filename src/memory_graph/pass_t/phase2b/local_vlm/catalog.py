"""Exact checkpoints and conservative modality policy, never implicit fallback."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelSpec:
    key: str
    backend: str
    model: str
    revision: str
    quantization: str
    documented: tuple[str, ...]

SPECS = {
    "qwen_nf4": ModelSpec("qwen_nf4", "LOCAL_QWEN25_VL_NF4", "Qwen/Qwen2.5-VL-7B-Instruct",
        "cc594898137f460bfe9f0759e9844b3ce807cfb5", "NF4_DOUBLE_BF16", ("MULTI_IMAGE", "STORYBOARD", "REENCODED_AUTHORIZED_VIDEO")),
    "qwen_awq": ModelSpec("qwen_awq", "LOCAL_QWEN25_VL_AWQ", "Qwen/Qwen2.5-VL-7B-Instruct-AWQ",
        "536a35794df8831aa814970ee8f89eff577e7718", "AWQ", ("MULTI_IMAGE", "STORYBOARD", "REENCODED_AUTHORIZED_VIDEO")),
    "videollama3_7b": ModelSpec("videollama3_7b", "LOCAL_VIDEOLLAMA3_7B", "DAMO-NLP-SG/VideoLLaMA3-7B",
        "d5b763e368861e7f5096e7ff1b49f92fbccf8ae6", "BF16", ("MULTI_IMAGE", "STORYBOARD", "REENCODED_AUTHORIZED_VIDEO")),
    "nemotron_nvfp4": ModelSpec("nemotron_nvfp4", "LOCAL_NEMOTRON_NVFP4_QAD",
        "nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-NVFP4-QAD", "16853d6c682223e967d5622c99d0082cb994b771",
        "NVFP4_MODEL_OPT", ("STORYBOARD",)),
}

def for_backend(name):
    return next((spec for spec in SPECS.values() if spec.backend == name), None)

def runtime_error(error):
    message = str(error).lower()
    if "out of memory" in message:
        return "CUDA_OOM_NO_AUTOMATIC_RESAMPLING"
    if "no kernel image" in message or "invalid device function" in message:
        return "GPU_KERNEL_ARCHITECTURE_INCOMPATIBLE"
    if "awq" in message or "nvfp4" in message:
        return "QUANTIZATION_ENGINE_INCOMPATIBLE"
    return "LOCAL_RUNTIME_FAILURE"
