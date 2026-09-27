"""Post-freeze sparse physical-target review and denominator-based metrics."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from memory_graph.v262.visualize import MODELS, OUT, ROOT, frozen, records


LABELS = {"CORRECT_TARGET", "PARTIAL_TARGET", "DRIFT_TO_OTHER_OBJECT", "EMPTY_OR_LOST", "NOT_REVIEWABLE"}


def metric(prediction: dict, reviewed: list[dict], model: str, task: str) -> dict:
    obs = records(prediction)
    visible = [item for item in reviewed if item.get("target_visible") is True]
    labels = [(item, item["model_labels"][model], obs[item["frame_index"]]) for item in visible if item["frame_index"] in obs]
    if any(label not in LABELS for _, label, _ in labels):
        raise ValueError(f"Invalid physical-target label in {task} {model}")
    count = lambda label: sum(value == label for _, value, _ in labels)
    correct = count("CORRECT_TARGET")
    # Drift remains a safety failure when the target has left the frame.
    all_reviewed = [(item, item["model_labels"][model], obs[item["frame_index"]])
                    for item in reviewed if item["frame_index"] in obs]
    drift_rows = [(item, row) for item, label, row in all_reviewed if label == "DRIFT_TO_OTHER_OBJECT"]
    opportunities = [(item, label, row) for item, label, row in labels if item.get("yolo_target_absent") is True]
    windows = prediction["windows"]
    total_frames = sum(len(window["observations"]) for window in windows.values())
    runtime = sum(window["timing_seconds"]["propagation"] for window in windows.values())
    reid = [(item, label, row) for item, label, row in labels if task == "test8" and item["frame_index"] >= 804]
    return {
        "reviewed_target_visible_frames": len(labels), "correct_target_masks": correct,
        "correct_target_coverage": correct / len(labels) if labels else None,
        "partial_target_masks": count("PARTIAL_TARGET"), "raw_drift_events": len(drift_rows),
        "guard_rejected_drift": sum(not row["accepted_by_guard"] for _, row in drift_rows),
        "accepted_drift": sum(row["accepted_by_guard"] for _, row in drift_rows),
        "lost_empty_events": count("EMPTY_OR_LOST"), "not_reviewable": count("NOT_REVIEWABLE"),
        "yolo_gap_opportunities": len(opportunities),
        "yolo_gap_recoveries": sum(label == "CORRECT_TARGET" and row["accepted_by_guard"] for _, label, row in opportunities),
        "yolo_gap_drifted": sum(label == "DRIFT_TO_OTHER_OBJECT" for _, label, row in opportunities),
        "post_reid_reviewed_target_visible": len(reid),
        "post_reid_correct_continuity": sum(label == "CORRECT_TARGET" and row["accepted_by_guard"] for _, label, row in reid),
        "reinitializations": sum(window["authorization"] == "CONFIRMED_MATCH" for window in windows.values()),
        "sampled_frames": total_frames,
        "all_frame_nonempty_masks": sum(row["area"] > 0 for row in obs.values()),
        "all_frame_guard_accepted": sum(row["accepted_by_guard"] for row in obs.values()),
        "propagation_seconds": runtime, "effective_sampled_fps": total_frames / runtime if runtime else None,
        "peak_reserved_bytes": max(window["peak_reserved_bytes"] for window in windows.values()),
    }


def aggregate(per_video: dict) -> dict:
    sums = {}
    for model in MODELS:
        rows = [per_video[task][model] for task in sorted(per_video)]
        fields = [key for key in rows[0] if key not in ("correct_target_coverage", "effective_sampled_fps", "peak_reserved_bytes")]
        merged = {key: sum(row[key] for row in rows) for key in fields}
        merged["correct_target_coverage"] = (merged["correct_target_masks"] / merged["reviewed_target_visible_frames"]
                                               if merged["reviewed_target_visible_frames"] else None)
        merged["effective_sampled_fps"] = merged["sampled_frames"] / merged["propagation_seconds"]
        merged["peak_reserved_bytes"] = max(row["peak_reserved_bytes"] for row in rows)
        sums[model] = merged
    return sums


def main() -> None:
    per_video = {}
    for number in range(3, 10):
        task = f"test{number}"
        predictions = frozen(task)
        review_path = OUT / task / "physical_review.json"
        review = json.loads(review_path.read_text(encoding="utf-8"))
        if not review.get("visually_confirmed"):
            raise RuntimeError(f"Physical mask labels not visually confirmed: {task}")
        reviewed = review["reviewed_frames"]
        per_video[task] = {model: metric(predictions[model], reviewed, model, task) for model in MODELS}
        result = {"schema": "v262_sam_comparison_1", "task": task, "metrics": per_video[task],
                  "reviewed_frames": reviewed, "prediction_freeze": "outputs_v262/prediction_manifest.json"}
        (OUT / task / "sam_comparison.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        lines = [f"# {task} V2.6.2 physical-target review", "", "Predictions were frozen before V2.6.2 mask review.", "",
                 "| Frame | Target visible | YOLO target absent | SAM 2.1 | SAM 3 box | SAM 3 point | Note |",
                 "|---:|---|---|---|---|---|---|"]
        for item in reviewed:
            labels = item["model_labels"]
            lines.append(f"| {item['frame_index']} | {item.get('target_visible')} | {item.get('yolo_target_absent')} | {labels['sam21']} | {labels['sam3']} | {labels['sam3point']} | {item.get('note','').replace('|','/')} |")
        (OUT / task / "review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {"schema": "v262_comparison_1", "stage_a": "PASS", "stage_b": "COMPLETE_7_VIDEOS",
               "videos": per_video, "aggregate": aggregate(per_video),
               "quality_scope": "Frozen V2.6 candidate review frames and selected visual checkpoints; sparse review, not exhaustive frame labels.",
               "primary_models": ["sam21", "sam3"], "secondary_model": "sam3point"}
    (OUT / "comparison_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Evaluated seven frozen videos")


if __name__ == "__main__":
    main()
