"""Compact evidence visualizations; original frames stay inside temporary storage."""
from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np


def _box(image, bbox, color, label):
    x1, y1, x2, y2 = [int(v) for v in bbox]
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 3)
    cv2.putText(image, label, (max(2, x1), max(25, y1-8)), cv2.FONT_HERSHEY_SIMPLEX,
                .7, color, 2, cv2.LINE_AA)


def render_event_sheet(images: list[Path], numbers: list[int], rows: list[dict],
                       event: dict, folder: Path) -> None:
    if not images:
        return
    peak = min(range(len(numbers)), key=lambda i: abs(numbers[i]-event["peak_frame"]))
    indices = [max(0, peak-len(images)//3), peak, min(len(images)-1, peak+len(images)//3)]
    tiles = []
    for caption, i in zip(("BEFORE", "DURING", "AFTER"), indices):
        image = cv2.imread(str(images[i]))
        if image is None:
            continue
        image = cv2.resize(image, (640, 360))
        original = cv2.imread(str(images[i]))
        sx, sy = 640/original.shape[1], 360/original.shape[0]
        def scaled(box):
            return [box[0]*sx, box[1]*sy, box[2]*sx, box[3]*sy]
        row = rows[i]
        if row["sam_phone"]:
            label = "TARGET phone_01" if row["identity_authorized"] else "SAM candidate / UNAUTHORIZED"
            _box(image, scaled(row["sam_phone"]["bbox"]), (0, 255, 0) if row["identity_authorized"] else (0, 165, 255), label)
        for j, anchor in enumerate(row["anchors"][:3]):
            if anchor["entity_id"]:
                _box(image, scaled(anchor["bbox"]), (255, 0, 255), f"ANCHOR {anchor['entity_id']} {anchor['label']}")
        header = np.zeros((50, 640, 3), dtype=np.uint8)
        cv2.putText(header, f"{caption} | f{numbers[i]} | {event['event_id']}", (12, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, .85, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(np.vstack((header, image)))
    if tiles:
        cv2.imwrite(str(folder/f"placement_event_{event['event_id']}_contact_sheet.png"), np.hstack(tiles))


def render_failure_timeline(rows: list[dict], first: dict, path: Path) -> None:
    width, step = 1600, 30
    height = max(180, 100+len(rows)*step)
    canvas = np.full((height, width, 3), 250, np.uint8)
    cv2.putText(canvas, "test9 evidence chain after last trusted phone", (20, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
    for i, row in enumerate(rows):
        y = 85+i*step
        line = (f"f{row['frame']:04d}  YOLO:{row['yolo_phone']}  SAM:{row['sam_phone']}  "
                f"candidate:{row['candidate_phone']}  authorized:{row['identity_authorized']}  "
                f"anchors:{row['anchor_count']}  event:{row['placement_event']}")
        color = (0, 0, 200) if row["frame"] == first.get("frame") else (30, 30, 30)
        cv2.putText(canvas, line, (20, y), cv2.FONT_HERSHEY_SIMPLEX, .52, color, 1, cv2.LINE_AA)
    cv2.imwrite(str(path), canvas)


def render_relation_explainer(candidates: list[dict], decisions: list[dict], path: Path) -> None:
    rows = list(zip(candidates, decisions))[:18]
    image = np.full((max(180, 90+65*len(rows)), 1600, 3), 255, np.uint8)
    cv2.putText(image, "Candidate -> evidence -> VLM -> physical gate", (20, 42),
                cv2.FONT_HERSHEY_SIMPLEX, .9, (20, 20, 20), 2)
    for i, (candidate, decision) in enumerate(rows):
        y = 90+65*i
        line = (f"{candidate['candidate_id']} {candidate['candidate_relation']} {candidate['anchor']}  |  "
                f"temporal {int(bool(decision['temporal_gate']))} mask {int(bool(decision['mask_gate']))}  |  "
                f"VLM {decision['vlm_gate']['status']}  |  {decision['decision']}")
        cv2.putText(image, line, (20, y), cv2.FONT_HERSHEY_SIMPLEX, .54,
                    (0, 100, 0) if decision["decision"] == "PROMOTED" else (30, 30, 30), 1, cv2.LINE_AA)
    cv2.imwrite(str(path), image)
