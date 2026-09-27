"""Render V2.7 views, then freeze predictions before narrative review."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from memory_graph.v27.pipeline import OUT, freeze
from memory_graph.v27.visualization import render_video

if __name__ == "__main__":
    if (OUT / "prediction_manifest.json").exists():
        raise SystemExit("Predictions already frozen")
    if sys.argv[1:] == ["--freeze"]:
        manifest = freeze()
        print(f"Frozen {len(manifest['files_sha256'])} artifacts before review")
    elif not sys.argv[1:]:
        for n in range(3, 10):
            render_video(f"test{n}")
            print(f"Rendered test{n}", flush=True)
    else:
        raise SystemExit("Usage: render_v27_graphs.py [--freeze]")
