"""Replay all seven frozen upstream streams; no models are loaded."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from memory_graph.v27.pipeline import OUT, run_video, write

if __name__ == "__main__":
    if (OUT / "prediction_manifest.json").exists():
        raise SystemExit("Predictions are already frozen; choose a new output version for another run")
    summary = {"schema": "v27_summary_1", "videos": [run_video(f"test{n}") for n in range(3, 10)]}
    write(OUT / "summary.json", summary)
    for video in summary["videos"]:
        print({key: value for key, value in video.items() if key != "input_sha256"})
