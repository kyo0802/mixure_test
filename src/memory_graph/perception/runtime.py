"""Keep third-party runtime writes inside the project and avoid implicit installers."""
import os
from pathlib import Path


def configure_ultralytics() -> None:
    directory = Path(".runtime/ultralytics").resolve()
    directory.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(directory))
    os.environ.setdefault("YOLO_AUTOINSTALL", "false")
