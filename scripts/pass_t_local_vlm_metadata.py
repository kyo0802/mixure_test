"""Fetch only bounded public checkpoint metadata, never model weights."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from memory_graph.pass_t.phase2b.common import exclusive_tree, pretty_bytes

MODELS = {
    "qwen_awq": "Qwen/Qwen2.5-VL-7B-Instruct-AWQ",
    "videollama3_7b": "DAMO-NLP-SG/VideoLLaMA3-7B",
    "nemotron_nvfp4": "nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-NVFP4-QAD",
}

def fetch(url):
    with urllib.request.urlopen(url, timeout=40) as response:
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError("Metadata size bound exceeded")
    return raw

def main():
    files = {}; rows = []
    for key, model in MODELS.items():
        url = "https://huggingface.co/api/models/" + model + "?blobs=true"
        raw = fetch(url); info = json.loads(raw); revision = info["sha"]
        files[f"{key}/api.json"] = raw
        config_raw = fetch(f"https://huggingface.co/{model}/resolve/{revision}/config.json")
        files[f"{key}/config.json"] = config_raw
        card = fetch(f"https://huggingface.co/{model}/resolve/{revision}/README.md")
        files[f"{key}/README.md"] = card
        weights = [{"name": f["rfilename"], "bytes": f.get("size"), "lfs": f.get("lfs")}
                   for f in info.get("siblings", []) if f["rfilename"].endswith(".safetensors")]
        config = json.loads(config_raw)
        rows.append({"key": key, "model": model, "revision": revision,
                     "license": info.get("cardData", {}).get("license"), "weight_files": weights,
                     "weight_bytes": sum(f["bytes"] or 0 for f in weights),
                     "config": config, "source_url": url, "metadata_sha256": hashlib.sha256(raw).hexdigest()})
    files["manifest.json"] = pretty_bytes({"schema_version": "PASS_T_LOCAL_CHECKPOINT_MANIFEST_V1", "models": rows, "weights_downloaded": False})
    folder = exclusive_tree(ROOT / "artifacts/pass_t/phase2b/local_vlm/v1/checkpoints", files,
                            {"schema_version": "PASS_T_LOCAL_METADATA_RECEIPT_V1", "public_metadata_only": True})
    print(json.dumps({"path": str(folder), "models": [{k: r[k] for k in ("key", "model", "revision", "license", "weight_bytes")} for r in rows]}))

if __name__ == "__main__":
    main()
