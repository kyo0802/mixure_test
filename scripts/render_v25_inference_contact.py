"""Inference-ID-only contact sheet; no reviewed physical identity labels."""
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v25"


def render(task):
    output = OUT / task
    groups = json.loads((output / "candidate_grouping_audit.json").read_text())["candidates"]
    meta = json.loads((ROOT / "outputs_v241" / task / "upstream_v21" / "event_analysis" / "video_metadata.json").read_text())
    first_late = int(meta["sampled_frames"][-1]["frame_index"] * .6)
    selected = [g for g in groups if any(o["frame_index"] >= first_late for o in g["observations"])]
    cols, tile_w, tile_h = 4, 270, 230
    sheet = np.full((((len(selected)+cols-1)//cols)*tile_h, cols*tile_w, 3), 245, dtype=np.uint8)
    for n, group in enumerate(selected):
        views = [o for o in group["appearance_views"] if o["frame_index"] >= first_late]
        obs = max(views or group["appearance_views"], key=lambda o: o["confidence"])
        cap = cv2.VideoCapture(str(ROOT / f"{task}.mp4"))
        cap.set(cv2.CAP_PROP_POS_FRAMES, obs["frame_index"])
        okay, image = cap.read()
        cap.release()
        if not okay:
            continue
        h, w = image.shape[:2]
        x1, y1, x2, y2 = obs["bbox"]
        pad = .5*max(x2-x1,y2-y1)
        left, top = max(0,int(x1-pad)), max(0,int(y1-pad))
        right, bottom = min(w,int(x2+pad)), min(h,int(y2+pad))
        crop = cv2.resize(image[top:bottom,left:right], (250,190))
        y,x = (n//cols)*tile_h, (n%cols)*tile_w
        sheet[y+30:y+220,x+10:x+260] = crop
        cv2.putText(sheet, f"{group['candidate_id']} f{obs['frame_index']}", (x+10,y+20),
                    cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,0),1)
    cv2.imwrite(str(output / "contact_sheet.png"), sheet)
    print(task, "shown candidates", len(selected))


if __name__ == "__main__":
    render("test8")
