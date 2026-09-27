"""Make paired timelines and same-frame contact sheets after prediction freeze."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v262"
MODELS = ("sam21", "sam3", "sam3point")
COLORS = {"sam21": (43, 165, 250), "sam3": (247, 117, 67), "sam3point": (70, 206, 87)}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen(task: str) -> dict:
    freeze = read(OUT / "prediction_manifest.json")
    if not freeze["frozen_before_v262_mask_review"]:
        raise RuntimeError("Predictions not frozen")
    result = {}
    for model in MODELS:
        path = OUT / task / f"{model}_predictions.json"
        relative = str(path.relative_to(ROOT)).replace("\\", "/")
        if freeze["prediction_files_sha256"][relative] != sha(path):
            raise RuntimeError(f"Prediction changed since freeze: {path}")
        result[model] = read(path)
        for row in records(result[model]).values():
            mask = ROOT / row["mask"]
            if freeze["prediction_files_sha256"][row["mask"]] != sha(mask):
                raise RuntimeError(f"Mask changed since freeze: {mask}")
    return result


def review_frames(task: str) -> dict[int, str]:
    """Post-freeze labels only; used to choose a bounded visual audit sample."""
    labels = {}
    for line in (ROOT / "outputs_v26" / task / "review.md").read_text(encoding="utf-8").splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) >= 7 and parts[1].startswith("candidate_"):
            try:
                labels[int(parts[2])] = parts[6]
            except ValueError:
                pass
    return labels


def reviewed_candidate_boxes(task: str, labels: dict[int, str]) -> dict[int, list[float]]:
    reviewed_ids = {}
    for line in (ROOT / "outputs_v26" / task / "review.md").read_text(encoding="utf-8").splitlines():
        parts = [part.strip() for part in line.split("|")]
        if len(parts) >= 7 and parts[1].startswith("candidate_"):
            try:
                reviewed_ids[int(parts[2])] = parts[1]
            except ValueError:
                pass
    candidates = read(ROOT / "outputs_v26" / task / "candidate_stream.json")["observations"]
    detections = read(ROOT / "outputs_v25_rerun" / task / "upstream_v21" / "event_analysis" / "detections.json")
    boxes = {}
    for row in candidates:
        frame = row["frame_index"]
        index = row.get("raw_detection_index")
        if frame in labels and row.get("candidate_id") == reviewed_ids.get(frame) and index is not None and 0 <= index < len(detections) and detections[index]["frame_index"] == frame:
            boxes[frame] = detections[index]["bbox"]
    return boxes


def records(prediction: dict) -> dict[int, dict]:
    return {row["frame_index"]: row for window in prediction["windows"].values() for row in window["observations"]}


def selected_frames(task: str, predictions: dict, labels: dict[int, str]) -> list[int]:
    available = set(records(predictions["sam21"]))
    chosen = {frame for frame in labels if frame in available}
    for window in predictions["sam21"]["windows"].values():
        frames = window["frames"]
        chosen.update((frames[0], frames[len(frames)//3], frames[2*len(frames)//3], frames[-1]))
    # Keep all frozen reviewed candidates, then at most four periodic frames per window.
    return sorted(chosen)


def overlay(frame: np.ndarray, mask: np.ndarray | None, color: tuple[int, int, int], row: dict | None) -> np.ndarray:
    out = frame.copy()
    if mask is not None and mask.any():
        paint = np.empty_like(out)
        paint[:] = color
        out[mask] = cv2.addWeighted(out, 0.5, paint, 0.5, 0)[mask]
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(out, contours, -1, color, 2)
    if row and row["bbox"]:
        x1, y1, x2, y2 = row["bbox"]
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
    return out


def panel(image: np.ndarray, title: str, subtitle: str, width=480, height=270) -> np.ndarray:
    canvas = np.zeros((height + 45, width, 3), dtype=np.uint8)
    canvas[:height] = cv2.resize(image, (width, height))
    cv2.putText(canvas, title, (8, height + 17), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(canvas, subtitle[:64], (8, height + 36), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (194, 194, 194), 1, cv2.LINE_AA)
    return canvas


def timeline(rows: dict[str, dict[int, dict]], models: tuple[str, ...], path: Path) -> None:
    all_frames = sorted(set.union(*(set(rows[model]) for model in models)))
    first, last = all_frames[0], all_frames[-1]
    width, height = 1500, 100 + 90 * len(models)
    image = np.full((height, width, 3), 31, dtype=np.uint8)
    cv2.putText(image, f"V2.6.2 sampled frames {first}-{last}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (250, 250, 250), 2)
    for index, model in enumerate(models):
        y = 75 + index * 90
        cv2.putText(image, model, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLORS[model], 2)
        cv2.line(image, (150, y), (width-25, y), (90, 90, 90), 1)
        for frame, row in rows[model].items():
            x = 150 + int((width - 175) * (frame - first) / max(1, last - first))
            color = COLORS[model] if row["area"] > 0 and row["accepted_by_guard"] else ((35, 35, 225) if row["area"] > 0 else (80, 80, 80))
            cv2.line(image, (x, y - 21), (x, y + 21), color, 3)
    cv2.imwrite(str(path), image)


def main(task: str) -> None:
    predictions = frozen(task)
    label_map = review_frames(task)
    candidate_boxes = reviewed_candidate_boxes(task, label_map)
    rows = {model: records(predictions[model]) for model in MODELS}
    folder = OUT / task
    timeline(rows, ("sam21",), folder / "sam21_timeline.png")
    timeline(rows, ("sam3",), folder / "sam3_timeline.png")
    timeline(rows, ("sam21", "sam3"), folder / "sam21_vs_sam3_timeline.png")
    timeline(rows, MODELS, folder / "sam21_vs_sam3point_timeline.png")
    frames = selected_frames(task, predictions, label_map)
    cap = cv2.VideoCapture(str(ROOT / f"{task}.mp4"))
    sheets = []
    frame_folder = folder / "visual_review_frames"
    frame_folder.mkdir(exist_ok=True)
    zoom_folder = folder / "candidate_zoom"
    zoom_folder.mkdir(exist_ok=True)
    for frame_index in frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, original = cap.read()
        if not ok:
            raise RuntimeError(f"Could not render {task} f{frame_index}")
        annotated_original = original.copy()
        if frame_index in candidate_boxes:
            box = list(map(int, candidate_boxes[frame_index]))
            color = (30, 220, 30) if label_map[frame_index] == "TARGET" else (30, 30, 220)
            cv2.rectangle(annotated_original, (box[0], box[1]), (box[2], box[3]), color, 3)
        line = [panel(annotated_original, f"ORIGINAL f{frame_index}", f"frozen candidate: {label_map.get(frame_index, 'unlabeled')}")]
        for model in MODELS:
            row = rows[model].get(frame_index)
            mask = cv2.imread(str(ROOT / row["mask"]), cv2.IMREAD_GRAYSCALE) > 0 if row else None
            subtitle = "empty/lost" if row is None or row["area"] == 0 else f"area {row['area']} | guard {'ACCEPT' if row['accepted_by_guard'] else 'REJECT'}"
            line.append(panel(overlay(original, mask, COLORS[model], row), model.upper(), subtitle))
        row_image = np.hstack(line)
        sheets.append(row_image)
        cv2.imwrite(str(frame_folder / f"f{frame_index:06d}.png"), row_image)
        if frame_index in candidate_boxes:
            x1, y1, x2, y2 = candidate_boxes[frame_index]
            center_x, center_y = (x1+x2)/2, (y1+y2)/2
            radius = int(max(x2-x1, y2-y1) * 1.35 + 40)
            left, top = max(0, int(center_x-radius)), max(0, int(center_y-radius))
            right, bottom = min(original.shape[1], int(center_x+radius)), min(original.shape[0], int(center_y+radius))
            zoom_images = [annotated_original]
            for model in MODELS:
                row = rows[model].get(frame_index)
                mask = cv2.imread(str(ROOT / row["mask"]), cv2.IMREAD_GRAYSCALE) > 0 if row else None
                zoom_images.append(overlay(original, mask, COLORS[model], row))
            zoom = np.hstack([cv2.resize(img[top:bottom, left:right], (360, 360)) for img in zoom_images])
            cv2.imwrite(str(zoom_folder / f"f{frame_index:06d}.png"), zoom)
    cap.release()
    image = np.vstack(sheets)
    cv2.imwrite(str(folder / "sam21_vs_sam3_contact_sheet.png"), image)
    (folder / "visual_review_frames.json").write_text(json.dumps({"frames": frames, "frozen_identity_labels": {str(k):v for k,v in label_map.items() if k in frames}, "candidate_boxes": {str(k):v for k,v in candidate_boxes.items() if k in frames}}, indent=2), encoding="utf-8")
    print(task, "contact rows", len(frames))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=[f"test{i}" for i in range(3, 10)])
    main(parser.parse_args().task)
