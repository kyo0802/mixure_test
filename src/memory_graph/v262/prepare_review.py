"""Prepare post-freeze physical-target review records for visual checking."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from memory_graph.v22.sam_tracking import box_iou
from memory_graph.v262.visualize import MODELS, OUT, frozen, records


def propose_label(row: dict | None, target_box: list[float] | None) -> str:
    if row is None or row["area"] == 0:
        return "EMPTY_OR_LOST"
    if target_box is None or row["bbox"] is None:
        return "NOT_REVIEWABLE"
    iou = box_iou(row["bbox"], target_box)
    if iou >= 0.35:
        return "CORRECT_TARGET"
    if iou >= 0.10:
        return "PARTIAL_TARGET"
    return "DRIFT_TO_OTHER_OBJECT"


def main(task: str) -> None:
    predictions = frozen(task)
    frame_info = json.loads((OUT / task / "visual_review_frames.json").read_text(encoding="utf-8"))
    obs = {model: records(predictions[model]) for model in MODELS}
    reviewed = []
    for frame in frame_info["frames"]:
        candidate = frame_info["frozen_identity_labels"].get(str(frame))
        target_box = frame_info["candidate_boxes"].get(str(frame)) if candidate == "TARGET" else None
        visible = True if candidate == "TARGET" else None
        labels = {model: propose_label(obs[model].get(frame), target_box) if visible else "NOT_REVIEWABLE" for model in MODELS}
        reviewed.append({"frame_index": frame, "source_candidate_label": candidate,
                         "target_visible": visible, "yolo_target_absent": False if visible else None,
                         "target_box_from_frozen_reviewed_candidate": target_box,
                         "model_labels": labels, "note": "Geometric proposal; inspect original and overlays before final use."})
    result = {"schema": "v262_physical_review_1", "task": task,
              "proposal_method": "Frozen V2.6 reviewed identity plus mask/bbox IoU; post-freeze visual confirmation required",
              "visually_confirmed": False, "reviewed_frames": reviewed}
    (OUT / task / "physical_review.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(task, len(reviewed), "post-freeze review proposals")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=[f"test{i}" for i in range(3, 10)])
    main(parser.parse_args().task)
