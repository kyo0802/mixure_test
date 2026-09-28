"""Run V2.8 against all seven frozen streams without loading a perception model."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from memory_graph.v28.pipeline import run_all

if __name__ == "__main__":
    result = run_all()
    for row in result["videos"]:
        print({key: value for key, value in row.items() if key != "input_sha256"})
