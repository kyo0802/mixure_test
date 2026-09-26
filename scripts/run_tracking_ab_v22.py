"""Run frozen-YOLO-seeded SAM 2.1 propagation without loading GT."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v22.sam_tracking import ROOT, run


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=["task1", "task2"])
    args = parser.parse_args()
    run(args.task, ROOT / "outputs_v22" / args.task / "tracking_ab")
