"""Explicitly authorized synthetic local smoke, never Phase 2a DEV inference."""
import argparse
import io
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
for relative in ("src", "artifacts/pass_i/runtime/vendor"):
    sys.path.insert(0, str(ROOT / relative))
from memory_graph.pass_t.phase2b.common import Phase2BBlocked, read_json, environment_bool, digest, exclusive_tree, pretty_bytes
from memory_graph.pass_t.phase2b.mocks import mock_payload
from memory_graph.pass_t.phase2b.local_vlm.transport import LocalModelAdapter, request_json

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True); parser.add_argument("--deployment", required=True)
    parser.add_argument("--representation", choices=["MULTI_IMAGE", "STORYBOARD"], required=True)
    parser.add_argument("--approve-smoke", action="store_true")
    args = parser.parse_args()
    if not args.approve_smoke or not environment_bool("PASS_T_LOCAL_SMOKE_APPROVAL"):
        raise Phase2BBlocked("EXPLICIT_MODEL_SMOKE_APPROVAL_REQUIRED")
    adapter = LocalModelAdapter(read_json(Path(args.config)), read_json(Path(args.deployment)))
    payload = mock_payload(); payload["representation"] = args.representation; payload["media"] = []
    payload["instructions"] = "Assess only the illustrated red rectangle. No actor is depicted; use uncertainty if physical transitions cannot be established. Return the supplied JSON contract."
    images = []
    for index in range(3):
        image = Image.new("RGB", (224, 224), "white")
        ImageDraw.Draw(image).rectangle((80, 80, 140, 140), fill="red")
        images.append(image)
    media = {}
    if args.representation == "STORYBOARD":
        montage = Image.new("RGB", (672, 248), "white")
        for index, image in enumerate(images):
            montage.paste(image, (224 * index, 24))
            ImageDraw.Draw(montage).text((224 * index + 5, 5), f"F{index+1:04d}", fill="black")
        images = [montage]
    for index, image in enumerate(images):
        stream = io.BytesIO(); image.save(stream, format="PNG"); blob = stream.getvalue()
        media_id = f"MEDIA_{index+1:03d}"; media[media_id] = blob
        aliases = ["F0001", "F0002", "F0003"] if args.representation == "STORYBOARD" else [f"F{index+1:04d}"]
        payload["media"].append({"media_id": media_id, "media_type": "image/png", "content_sha256": digest(blob), "supplied_frame_aliases": aliases})
    request = adapter.construct_request(payload, media)
    response = request_json(adapter.endpoint + "/smoke", request, adapter.config["transport"]["timeout_seconds"])
    folder = exclusive_tree(ROOT / "artifacts/pass_t/phase2b/local_vlm/v1/smoke",
                            {"request.json": pretty_bytes(request), "response.json": pretty_bytes(response)},
                            {"schema_version": "PASS_T_LOCAL_SYNTHETIC_SMOKE_V1", "phase2a_dev_used": False})
    print(json.dumps({"path": str(folder), "error": response.get("error"), "validation": response.get("prediction_validation")}))

if __name__ == "__main__":
    main()
