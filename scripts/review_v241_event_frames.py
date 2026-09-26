"""Post-freeze event strips for sparse manual visibility review."""
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v241" / "cache"
for i in range(3, 10):
    cap = cv2.VideoCapture(str(ROOT / f"test{i}.mp4"))
    end = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))-1
    indices = [min(end, frame) for frame in (450, 540, 630, 720, 810, 900, 990, 1080)]
    sheet = np.full((4*225, 2*400, 3), 245, dtype=np.uint8)
    for j, frame in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
        okay, image = cap.read()
        if not okay: continue
        image = cv2.resize(image, (390, 200))
        x, y = j%2*400, j//2*225
        sheet[y+20:y+220, x+5:x+395] = image
        cv2.putText(sheet, f"test{i} f{frame} ({frame/30:.1f}s)", (x+5,y+15),
                    cv2.FONT_HERSHEY_SIMPLEX,.48,(0,0,0),1)
    cap.release()
    cv2.imwrite(str(OUT / f"test{i}_event_frames.jpg"), sheet)
