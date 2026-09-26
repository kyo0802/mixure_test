"""GT-free appearance-assisted Re-ID inference after parameter lock."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v24.reid import run


if __name__ == "__main__":
    for task in ("task1", "task2"):
        audit = run(task)
        print(task, [(a["candidate_entity_id"], a["appearance"]["max_similarity"], a["decision"])
                     for a in audit["attempts"]])
