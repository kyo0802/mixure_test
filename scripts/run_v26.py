"""Run GT-free V2.6 authorization on one fresh-input V2.5 video."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v26.pipeline import run_video

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=[f"test{i}" for i in range(3,10)])
    args = parser.parse_args()
    audit = run_video(args.task)
    print(args.task, "confirmed", audit["confirmed_match"],
          "provisional", audit["provisional_candidate_ids"],
          "audits", len(audit["attempts"]), flush=True)
