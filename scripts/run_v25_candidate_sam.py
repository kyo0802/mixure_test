"""Stage A: selective SAM 2.1 support for every eligible continuous candidate."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v241.adapter import v21_inputs
from memory_graph.v25.candidates import CandidateHypothesis
from memory_graph.v25.sam_route import SamRouter

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=[f"test{i}" for i in range(3,10)])
    args = parser.parse_args()
    output = ROOT / "outputs_v25" / args.task
    summaries = json.loads((output / "candidate_grouping_audit.json").read_text())["candidates"]
    inputs, _ = v21_inputs(args.task)
    last = inputs["video_metadata.json"]["sampled_frames"][-1]["frame_index"]
    router = SamRouter(args.task)
    path = output / "sam" / "candidate_sam_support.json"
    results = []
    for summary in summaries:
        candidate = CandidateHypothesis(summary["candidate_id"])
        for obs in summary["observations"]:
            candidate.add(obs)
        result = router.candidate(candidate, last)
        results.append(result)
        path.write_text(json.dumps({"task": args.task, "candidate_support": results,
                                    "status": "RUNNING"}, indent=2), encoding="utf-8")
    path.write_text(json.dumps({"task": args.task, "candidate_support": results,
                                "status": "COMPLETE", "gt_accessed": False}, indent=2), encoding="utf-8")
    print(args.task, "candidates", len(results), "seeded", sum(r["status"]=="SEEDED" for r in results))
