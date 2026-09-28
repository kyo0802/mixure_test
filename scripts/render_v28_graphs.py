"""Render V2.8 artifacts and freeze only after all figures are complete."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from memory_graph.v28.pipeline import OUT, freeze
from memory_graph.v28.visualization import render_video

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        result = freeze()
        print(f"Frozen {len(result['files_sha256'])} artifacts before review")
    else:
        if (OUT / "prediction_manifest.json").exists():
            raise SystemExit("Predictions already frozen; figures cannot be replaced")
        for number in range(3, 10):
            render_video(OUT / f"test{number}", f"test{number}")
            print(f"Rendered test{number}")
