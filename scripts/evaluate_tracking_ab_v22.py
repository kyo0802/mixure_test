"""Evaluation-only entry point. This is the only V2.2 script that reads GT."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v22.evaluate import evaluate


if __name__ == "__main__":
    for task in ("task1", "task2"):
        result = evaluate(task)
        print(task, result["branch_a"]["local_observation_hits"], result["branch_b"]["sam_observation_hits"],
              result["reviewed_visible_samples"])
