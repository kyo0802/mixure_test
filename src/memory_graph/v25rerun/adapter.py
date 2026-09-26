"""Read only fresh V2.1 detections/tracks with input hash validation."""
from pathlib import Path
from memory_graph.v22.sam_tracking import read_json, sha256

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v25_rerun"

def v21_inputs(task):
    base = OUT / task / "upstream_v21"
    manifest = read_json(base / "prediction_manifest.json")
    status = read_json(base / "run_status.json")
    video = ROOT / f"{task}.mp4"
    if status["video_sha256"] != sha256(video):
        raise ValueError(f"Fresh V2.1 cache does not match current video: {task}")
    names = ("detections.json", "track_timelines.json", "video_metadata.json")
    paths = {name: base / "event_analysis" / name for name in names}
    for name, path in paths.items():
        if sha256(path) != manifest[f"event_analysis/{name}"]:
            raise ValueError(f"V2.1 prediction hash mismatch: {path}")
    return {name: read_json(path) for name, path in paths.items()}, {name: sha256(path) for name, path in paths.items()}
