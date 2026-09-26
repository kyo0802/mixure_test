"""Stage A: continuous frozen V2.4 Re-ID on the live V2.5 candidate stream."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v25.reid import run_reid

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=[f"test{i}" for i in range(3,10)])
    args = parser.parse_args()
    audit = run_reid(args.task)
    print(args.task, audit["decision"], audit["match_candidate_id"],
          "events", len(audit["attempts"]), "sam", audit["sam_reinitialization_status"])
