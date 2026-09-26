"""GT-free V2.3 fusion and V2.4 appearance decisions on the routed videos."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v241.adapter import run_identity

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=[f"test{i}" for i in range(3, 10)])
    args = parser.parse_args()
    timeline, reid = run_identity(args.task)
    print(args.task, timeline["status"], reid["decision"], len(reid["attempts"]))
