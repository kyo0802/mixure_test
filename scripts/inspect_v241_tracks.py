import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for i in range(3, 10):
    path = root / "outputs_v241" / f"test{i}" / "upstream_v21" / "event_analysis" / "track_timelines.json"
    if not path.exists():
        continue
    tracks = json.loads(path.read_text(encoding="utf-8"))
    phones = [track for track in tracks if track["detector_class"] == "cell phone"]
    print(i, [(t["track_id"], len(t["observations"]), t["observations"][0]["frame_index"],
               t["observations"][-1]["frame_index"], round(max(o["confidence"] for o in t["observations"]), 2))
              for t in phones])
