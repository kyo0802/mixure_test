"""Stage A: GT-free target binding and full remaining-video SAM propagation."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v241.adapter import v21_inputs
from memory_graph.v25.binding import automatic_bind
from memory_graph.v25.sam_route import SamRouter

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=[f"test{i}" for i in range(3,10)])
    args = parser.parse_args()
    inputs, _ = v21_inputs(args.task)
    bound, audit = automatic_bind(inputs["video_metadata.json"]["sampled_frames"], inputs["track_timelines.json"])
    output = ROOT / "outputs_v25" / args.task
    output.mkdir(parents=True, exist_ok=True)
    (output / "target_binding_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    router = SamRouter(args.task)
    result = router.target(bound)
    print(args.task, audit["decision"], bound.frame_index if bound else None,
          len(result["segments"][0]["observations"]) if result["segments"] else 0)
