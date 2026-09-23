import platform
import torch
from importlib.metadata import version


def hardware_report():
    report = {"python": platform.python_version(), "pytorch": torch.__version__,
              "cuda_available": torch.cuda.is_available(), "gpu": None, "vram_gb": None,
              "processor": platform.processor()}
    report["packages"] = {name: version(name) for name in ("ultralytics", "opencv-python", "numpy", "pydantic")}
    if torch.cuda.is_available():
        report.update(gpu=torch.cuda.get_device_name(0), vram_gb=torch.cuda.get_device_properties(0).total_memory/2**30)
    try:
        import psutil
        report.update(ram_gb=psutil.virtual_memory().total/2**30, available_ram_gb=psutil.virtual_memory().available/2**30)
    except ImportError:
        report["available_ram_gb"] = None
    return report
