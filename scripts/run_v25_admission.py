"""Stage A: continuous GT-free candidate admission after full target SAM."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v25.pipeline import run_admission

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=[f"test{i}" for i in range(3,10)])
    args = parser.parse_args()
    fusion, stream = run_admission(args.task)
    print(args.task, fusion["status"], "candidates", len(stream.candidates),
          "phone states", len(fusion["phone_timeline"]))
