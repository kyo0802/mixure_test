"""GT-free SAM stage for all seven videos."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v241.adapter import run_sam

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=[f"test{i}" for i in range(3, 10)])
    args = parser.parse_args()
    result = run_sam(args.task)
    print(args.task, result["status"], [len(s["observations"]) for s in result["segments"]])
