"""Post-freeze QA sheets of all later local phone tracks, not matcher input."""
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v241"
(OUT / "cache").mkdir(exist_ok=True)
for i in range(3, 10):
    task = f"test{i}"
    sam = json.loads((OUT / task / "sam" / "sam_propagation_log.json").read_text())
    tracks = json.loads((OUT / task / "upstream_v21" / "event_analysis" / "track_timelines.json").read_text())
    threshold = sam["initialization"]["frame_index"] + 180
    phones = [t for t in tracks if t["detector_class"] == "cell phone"
              and t["observations"][-1]["frame_index"] > threshold]
    columns, tile_w, tile_h = 4, 280, 240
    sheet = np.full((((len(phones)+columns-1)//columns)*tile_h, columns*tile_w, 3), 245, dtype=np.uint8)
    for index, track in enumerate(phones):
        det = max(track["observations"], key=lambda o: o["confidence"])
        cap = cv2.VideoCapture(str(ROOT / f"{task}.mp4"))
        cap.set(cv2.CAP_PROP_POS_FRAMES, det["frame_index"])
        okay, image = cap.read()
        cap.release()
        if not okay:
            continue
        h, w = image.shape[:2]
        x1, y1, x2, y2 = det["bbox"]
        pad = .5 * max(x2-x1, y2-y1)
        left, top = max(0, int(x1-pad)), max(0, int(y1-pad))
        right, bottom = min(w, int(x2+pad)), min(h, int(y2+pad))
        crop = cv2.resize(image[top:bottom, left:right], (260, 205))
        y, x = (index//columns)*tile_h, (index%columns)*tile_w
        sheet[y+30:y+235, x+10:x+270] = crop
        cv2.putText(sheet, f"{task} t{track['track_id']} f{det['frame_index']} n{len(track['observations'])}",
                    (x+10,y+20), cv2.FONT_HERSHEY_SIMPLEX,.46,(0,0,0),1)
    cv2.imwrite(str(OUT / "cache" / f"{task}_later_tracks.jpg"), sheet)
