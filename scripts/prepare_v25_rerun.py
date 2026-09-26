"""Create an isolated, GT-free rerun of the frozen V2.5 inference implementation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v25_rerun"
PACKAGE = ROOT / "src/memory_graph/v25rerun"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    PACKAGE.mkdir(exist_ok=True)
    source = ROOT / "src/memory_graph/v25"
    for path in source.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        text = text.replace("from memory_graph.v241.adapter import v21_inputs", "from memory_graph.v25rerun.adapter import v21_inputs")
        text = text.replace('"outputs_v241"', '"outputs_v25_rerun"')
        text = text.replace('"outputs_v25"', '"outputs_v25_rerun"')
        text = text.replace('f"outputs_v25/', 'f"outputs_v25_rerun/')
        text = text.replace('f"outputs_v241/', 'f"outputs_v25_rerun/')
        target = PACKAGE / path.name
        if target.exists() and target.read_text(encoding="utf-8") != text:
            raise ValueError(f"Rerun implementation already exists with different content: {target}")
        target.write_text(text, encoding="utf-8")
    adapter = '''"""Read only fresh V2.1 detections/tracks with input hash validation."""
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
'''
    (PACKAGE / "adapter.py").write_text(adapter, encoding="utf-8")
    old = ROOT / "outputs_v25/architecture_manifest.json"
    architecture = json.loads(old.read_text(encoding="utf-8"))
    architecture["schema"] = "v25-full-rerun-architecture-1"
    architecture["source_v25_architecture_sha256"] = sha(old)
    architecture["current_video_sha256"] = {f"test{i}.mp4": sha(ROOT / f"test{i}.mp4") for i in range(3, 10)}
    architecture["rerun_inference_code_sha256"] = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p)
        for p in PACKAGE.glob("*.py")}
    architecture["fresh_v21_required"] = True
    path = OUT / "architecture_manifest.json"
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != architecture:
        raise ValueError("Rerun architecture changed after freeze")
    path.write_text(json.dumps(architecture, indent=2), encoding="utf-8")
    print("Rerun architecture frozen", sha(path))


if __name__ == "__main__":
    main()
