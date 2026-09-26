"""Sparse GT evaluation for frozen V2.1 and SAM 2.1 predictions."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .sam_tracking import ROOT, box_iou, decode_mask, frozen_inputs, read_json

NOT_MEASURABLE = "NOT_MEASURABLE_FROM_CURRENT_GT"


def reviewed_rows(task):
    gt = read_json(ROOT / "evaluation" / "v21" / f"{task}_annotations.json")
    inputs, hashes = frozen_inputs(task)
    log = read_json(ROOT / "outputs_v22" / task / "tracking_ab" / "sam_propagation_log.json")
    if log["frozen_input_sha256"] != hashes:
        raise ValueError("SAM and A branch frozen input hashes differ")
    detections = inputs["detections.json"]
    tracks = inputs["track_timelines.json"]
    rows = []
    for sample in gt["samples"]:
        if sample["gt_object_id"] != "smartphone_01":
            continue
        frame = sample["frame_index"]
        visible = sample["visibility"] in {"VISIBLE", "PARTIALLY_VISIBLE"} and sample.get("bbox") is not None
        if visible and not sample.get("manually_reviewed"):
            raise ValueError("Visible GT lacks manual review provenance")
        box = sample.get("bbox")
        raw = [d for d in detections if d["frame_index"] == frame and visible and box_iou(box, d["bbox"]) >= .3]
        local = [(t["track_id"], o) for t in tracks for o in t["observations"]
                 if o["frame_index"] == frame and visible and box_iou(box, o["bbox"]) >= .3]
        sam = [(o, seg) for seg in log["segments"] for o in seg["observations"]
               if o["frame_index"] == frame and visible and box_iou(box, o["bbox"]) >= .3]
        a = max(local, key=lambda x: box_iou(box, x[1]["bbox"]), default=None)
        b = max(sam, key=lambda x: box_iou(box, x[0]["bbox"]), default=None)
        rows.append({"frame_index": frame, "timestamp": sample["timestamp"], "visibility": sample["visibility"],
                     "gt_box": box, "scored": visible, "raw_present": bool(raw),
                     "a_track_id": a[0] if a else None, "a_iou": box_iou(box, a[1]["bbox"]) if a else None,
                     "b_object_id": b[0]["object_id"] if b else None,
                     "b_segment": b[0]["segment"] if b else None,
                     "b_iou": box_iou(box, b[0]["bbox"]) if b else None,
                     "b_possible_drift": b[0]["diagnostics"]["possible_mask_drift"] if b else False,
                     "all_sam": [{"object_id": o["object_id"], "segment": o["segment"],
                                  "iou": box_iou(box, o["bbox"]) if visible else None,
                                  "bbox": o["bbox"], "mask_area": o["mask_area"],
                                  "possible_mask_drift": o["diagnostics"]["possible_mask_drift"]}
                                 for seg in log["segments"] for o in seg["observations"] if o["frame_index"] == frame]})
    return rows, log, gt


def summarize(task, rows, log, gt):
    visible = [r for r in rows if r["scored"]]
    raw = [r for r in visible if r["raw_present"]]
    a_hits = sum(r["a_track_id"] is not None for r in visible)
    b_hits = sum(r["b_object_id"] is not None for r in visible)
    a_raw = sum(r["a_track_id"] is not None for r in raw)
    b_raw = sum(r["b_object_id"] is not None for r in raw)
    a_ids = sorted({r["a_track_id"] for r in visible if r["a_track_id"] is not None})
    b_ids = sorted({r["b_object_id"] for r in visible if r["b_object_id"] is not None})
    candidate_rows = [r for r in visible if r["b_segment"] == "late_candidates"]
    initial_rows = [r for r in visible if r["frame_index"] <= (420 if task == "task1" else 312)]
    all_obs = [o for seg in log["segments"] for o in seg["observations"]]
    possible = [o for o in all_obs if o["diagnostics"]["possible_mask_drift"]]
    # Visual review of the generated overlay: at task2 f312 the green phone
    # mask has moved to the hand below the manually reviewed phone box.
    confirmed_drift_frames = [312] if task == "task2" else []
    metrics = {"task": task, "target": "original_smartphone", "reviewed_visible_samples": len(visible),
               "raw_detection_present_samples": len(raw),
               "branch_a": {"local_observation_hits": a_hits,
                            "visibility_conditioned_local_coverage": a_hits / len(visible) if visible else None,
                            "raw_to_local_retention": a_raw / len(raw) if raw else None,
                            "reviewed_fragments_lower_bound": len(a_ids), "reviewed_track_ids": a_ids,
                            "confirmed_id_switches": NOT_MEASURABLE},
               "branch_b": {"sam_observation_hits": b_hits,
                            "visibility_conditioned_local_coverage": b_hits / len(visible) if visible else None,
                            "raw_to_local_retention": b_raw / len(raw) if raw else None,
                            "reviewed_fragments_lower_bound": len(b_ids), "reviewed_object_ids": b_ids,
                            "confirmed_id_switches": NOT_MEASURABLE,
                            "possible_drift_frames_all_propagated": len(possible),
                            "possible_drift_reviewed_frames": sorted({o["frame_index"] for o in possible if any(r["frame_index"] == o["frame_index"] and r["scored"] for r in visible)}),
                            "confirmed_drift_events": len(confirmed_drift_frames),
                            "confirmed_drift_frames": confirmed_drift_frames,
                            "false_identity_continuations": len(confirmed_drift_frames),
                            "reinitializations": sum(e["type"] == "REINITIALIZE" for seg in log["segments"] for e in seg["events"]),
                            "late_yolo_candidate_initializations": sum(e["type"] == "INIT" and e["segment"] == "late_candidates" for seg in log["segments"] for e in seg["events"]),
                            "late_candidate_reviewed_hits": len(candidate_rows),
                            "initial_window_hits": sum(r["b_object_id"] is not None for r in initial_rows),
                            "initial_window_visible_samples": len(initial_rows)},
               "comparison": {"coverage_delta": (b_hits - a_hits) / len(visible) if visible else None,
                              "raw_to_local_retention_delta": (b_raw - a_raw) / len(raw) if raw else None,
                              "continuity_interpretation": "Late candidates are independent YOLO-seeded hypotheses, not a continuous link from initial track.",
                              "drift_interpretation": "Automatic flags require visual review; raw mask existence alone is not a hit."},
               "sample_rows": rows,
               "compute": {"frames_processed": sum(s["compute"]["frames_processed"] for s in log["segments"]),
                           "sam_propagation_wall_seconds": sum(s["compute"]["wall_seconds"] for s in log["segments"]),
                           "peak_gpu_bytes_max_segment": max(s["compute"]["peak_gpu_bytes"] for s in log["segments"]),
                           "speed_comparison": "A/B SPEED COMPARISON NOT VALID"}}
    return metrics


def render_timeline(task, rows, log, output):
    fig, ax = plt.subplots(figsize=(15, 4.4))
    labels = ["GT reviewed visible", "Frozen YOLO raw", "A local", "B SAM"]
    for row in rows:
        t = row["timestamp"]
        values = [row["scored"], row["raw_present"], row["a_track_id"] is not None, row["b_object_id"] is not None]
        for y, value in enumerate(values):
            color = "#888888" if not row["scored"] else "#21885b" if value else "#d05252"
            ax.scatter(t, 3 - y, s=32, color=color)
    for seg in log["segments"]:
        for event in seg["events"]:
            if event["type"] in {"INIT", "REINITIALIZE", "LOST"}:
                t = event.get("timestamp", event["frame_index"] / 29.986)
                ax.axvline(t, color="#5276a2" if event["type"] != "LOST" else "#c67b24", alpha=.35)
                ax.annotate(event["type"], (t, 3.35), rotation=90, fontsize=7)
    for row in rows:
        if row["scored"] and row["b_possible_drift"]:
            ax.scatter(row["timestamp"], -.35, marker="^", color="#df8d16", s=32)
    ax.set_yticks([3, 2, 1, 0], labels)
    ax.set_ylim(-.6, 3.8)
    ax.set_xlabel("seconds; only sampled GT points are scored")
    ax.set_title(f"{task} smartphone A/B | green=present, red=missing, gray=excluded, triangle=drift flag")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def render_contact_sheet(task, rows, log, output):
    relevant = [r for r in rows if r["scored"]]
    selected = relevant if task == "task1" else [r for r in relevant if r["frame_index"] in {90, 120, 150, 180, 240, 288, 300, 306, 312, 528, 540, 558, 576, 594}]
    video = ROOT / ("test1.mp4" if task == "task1" else "test2.mp4")
    cap = cv2.VideoCapture(str(video))
    tiles = []
    for row in selected:
        frame = row["frame_index"]
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
        ok, image = cap.read()
        if not ok:
            continue
        overlay = image.copy()
        for seg in log["segments"]:
            for obs in seg["observations"]:
                if obs["frame_index"] != frame:
                    continue
                mask = decode_mask(seg["masks_rle"][f"{frame}:{obs['object_id']}"])
                color = (0, 210, 0) if obs["object_id"] == row["b_object_id"] else (210, 120, 0)
                overlay[mask] = .55 * overlay[mask] + .45 * np.array(color)
                cv2.rectangle(overlay, tuple(obs["bbox"][:2]), tuple(obs["bbox"][2:]), color, 2)
        cv2.rectangle(overlay, tuple(row["gt_box"][:2]), tuple(row["gt_box"][2:]), (0, 0, 255), 2)
        cv2.putText(overlay, f"f{frame} A={row['a_track_id']} B={row['b_object_id']} IoU={row['b_iou']}",
                    (15, 35), cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 255), 2)
        tile = cv2.resize(overlay, (512, 288))
        tiles.append(tile)
    cap.release()
    columns = 2
    rows_count = (len(tiles) + columns - 1) // columns
    canvas = np.full((rows_count * 288, columns * 512, 3), 240, np.uint8)
    for i, tile in enumerate(tiles):
        canvas[(i // columns) * 288:(i // columns + 1) * 288, (i % columns) * 512:(i % columns + 1) * 512] = tile
    cv2.imwrite(str(output), canvas, [cv2.IMWRITE_JPEG_QUALITY, 90])


def evaluate(task):
    rows, log, gt = reviewed_rows(task)
    metrics = summarize(task, rows, log, gt)
    output = ROOT / "outputs_v22" / task / "tracking_ab"
    (output / "ab_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    render_timeline(task, rows, log, output / "smartphone_ab_timeline.png")
    render_contact_sheet(task, rows, log, output / "smartphone_sam_contact_sheet.jpg")
    return metrics
