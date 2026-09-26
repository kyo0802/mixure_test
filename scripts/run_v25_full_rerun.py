"""GT-free isolated V2.5 rerun using fresh V2.1 inputs from current videos."""
import argparse
import json
from pathlib import Path

from memory_graph.v25rerun.adapter import v21_inputs
from memory_graph.v25rerun.binding import automatic_bind
from memory_graph.v25rerun.sam_route import SamRouter
from memory_graph.v25rerun.pipeline import run_admission
from memory_graph.v25rerun.candidates import CandidateHypothesis
from memory_graph.v25rerun.reid import run_reid

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v25_rerun"


def run(task, stage):
    inputs, _ = v21_inputs(task)
    output = OUT / task
    output.mkdir(parents=True, exist_ok=True)
    if stage == "target":
        bound, audit = automatic_bind(inputs["video_metadata.json"]["sampled_frames"], inputs["track_timelines.json"])
        (output / "target_binding_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
        result = SamRouter(task).target(bound)
        print(task, stage, audit["decision"], bound.frame_index if bound else None,
              len(result["segments"][0]["observations"]) if result["segments"] else 0, flush=True)
    elif stage == "admission":
        fusion, stream = run_admission(task)
        print(task, stage, fusion["status"], len(stream.candidates), flush=True)
    elif stage == "candidate_sam":
        summaries = json.loads((output / "candidate_grouping_audit.json").read_text(encoding="utf-8"))["candidates"]
        last = inputs["video_metadata.json"]["sampled_frames"][-1]["frame_index"]
        router = SamRouter(task)
        path = output / "sam" / "candidate_sam_support.json"
        results = []
        for summary in summaries:
            candidate = CandidateHypothesis(summary["candidate_id"])
            for observation in summary["observations"]:
                candidate.add(observation)
            result = router.candidate(candidate, last)
            results.append(result)
            path.write_text(json.dumps({"task": task, "candidate_support": results, "status": "RUNNING"}, indent=2), encoding="utf-8")
        path.write_text(json.dumps({"task": task, "candidate_support": results, "status": "COMPLETE", "gt_accessed": False}, indent=2), encoding="utf-8")
        print(task, stage, len(results), sum(r["status"] == "SEEDED" for r in results), flush=True)
    elif stage == "reid":
        audit = run_reid(task)
        print(task, stage, audit["decision"], audit["match_candidate_id"], len(audit["attempts"]), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=[f"test{i}" for i in range(3, 10)])
    parser.add_argument("stage", choices=["target", "admission", "candidate_sam", "reid"])
    arguments = parser.parse_args()
    run(arguments.task, arguments.stage)
