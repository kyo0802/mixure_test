"""Run existing tests in this audit directory without mutating frozen outputs."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
os.environ["MPLCONFIGDIR"] = str(HERE / "runtime" / "matplotlib")
os.environ["YOLO_CONFIG_DIR"] = str(HERE / "runtime" / "ultralytics")
sys.path.insert(0, str(ROOT / ".venv" / "Lib" / "site-packages"))
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)
import pytest
print(f"Interpreter: {sys.executable}\nProject packages: {ROOT / '.venv/Lib/site-packages'}", flush=True)
sys.exit(pytest.main(["tests", "-q", "-p", "no:cacheprovider", "--basetemp", str(HERE / "runtime" / "pytest"),
                     "--junitxml", str(HERE / "regression_results.xml")]))
