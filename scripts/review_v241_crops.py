"""Temporary visual QA sheet; does not feed back into inference."""
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v241"
(OUT / "cache").mkdir(exist_ok=True)
sheet = np.full((7 * 240, 4 * 280, 3), 245, dtype=np.uint8)
for row, i in enumerate(range(3, 10)):
    task = f"test{i}"
    sam = json.loads((OUT / task / "sam" / "sam_propagation_log.json").read_text())
    entries = [("seed", sam["initialization"]["detection"])]
    entries += [(f"late{j}", d) for j, d in enumerate(sam["late_selection"]["detections"], 1)]
    for col, (label, det) in enumerate(entries):
        cap = cv2.VideoCapture(str(ROOT / f"{task}.mp4"))
        cap.set(cv2.CAP_PROP_POS_FRAMES, det["frame_index"])
        ok, image = cap.read()
        cap.release()
        if not ok:
            continue
        h, w = image.shape[:2]
        x1, y1, x2, y2 = det["bbox"]
        pad = .5 * max(x2-x1, y2-y1)
        left, top = max(0, int(x1-pad)), max(0, int(y1-pad))
        right, bottom = min(w, int(x2+pad)), min(h, int(y2+pad))
        crop = cv2.resize(image[top:bottom, left:right], (260, 205))
        y, x = row*240, col*280
        sheet[y+30:y+235, x+10:x+270] = crop
        cv2.putText(sheet, f"{task} {label} f{det['frame_index']}", (x+10, y+20),
                    cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,0), 1)
cv2.imwrite(str(OUT / "cache" / "review_crops.jpg"), sheet)
