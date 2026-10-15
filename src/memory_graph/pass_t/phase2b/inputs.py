"""Content-addressed preparation of model-visible inputs and private mappings."""
from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image

from .builders import build_multi_image, build_storyboard, build_video
from .common import Phase2BBlocked, exclusive_tree, file_sha256, pretty_bytes, repository_root
from .model_visible import build_payload, inspect_payload, source_contract


def build_input_package(item: dict, *, secret: str, prompt_text: str, representations: list[str],
                        frame_count: int, storyboard_columns: int, video_fps: float,
                        reference_policy: str = "NONE", base: Path | None = None) -> Path:
    source = source_contract(item, secret=secret, reference_policy=reference_policy)
    files: dict[str, bytes] = {}
    summaries = []
    private = {"source_contract": source, "representations": {}}
    staging_root = repository_root() / "artifacts/pass_t/phase2b/.staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pass_t_phase2b_", dir=staging_root) as temporary:
        temp = Path(temporary)
        for representation in representations:
            out = temp / representation
            if representation == "MULTI_IMAGE":
                built = build_multi_image(source, out, frame_count)
            elif representation == "STORYBOARD":
                built = build_storyboard(source, out, frame_count, storyboard_columns)
            elif representation == "REENCODED_AUTHORIZED_VIDEO":
                built = build_video(source, out, video_fps)
            else:
                raise Phase2BBlocked("UNKNOWN_REPRESENTATION:" + representation)
            for reference_index, reference in enumerate(source["references"], start=1):
                reference_path = repository_root() / reference["private_path"]
                if file_sha256(reference_path) != reference["content_sha256"]:
                    raise Phase2BBlocked("REFERENCE_HASH_CHANGED_DURING_BUILD")
                destination = out / f"REFERENCE_{reference_index:02d}.png"
                with Image.open(reference_path) as image:
                    image.convert("RGB").save(destination, format="PNG", optimize=False)
                built["model_media"].append({"media_id": f"REFERENCE_{reference_index:02d}", "media_type": "image/png",
                                             "content_sha256": file_sha256(destination), "supplied_frame_aliases": []})
            built["information_budget"]["reference_image_count"] = len(source["references"])
            payload = build_payload(source, built, prompt_text)
            inspection = inspect_payload(payload, source)
            if not inspection["safe"]:
                raise Phase2BBlocked("UNSAFE_PREPARED_PAYLOAD")
            rep_private = {key: value for key, value in built.items() if key not in {"model_media"}}
            for mapping_row in rep_private.get("private_mapping", []):
                if "output_path" in mapping_row:
                    mapping_row["output_path"] = f"model_visible/{representation}/media/{Path(mapping_row['output_path']).name}"
            private["representations"][representation] = rep_private
            summaries.append({"representation": representation, "payload": payload, "inspection": inspection, "information_budget": built["information_budget"]})
            files[f"model_visible/{representation}/payload.json"] = pretty_bytes(payload)
            for path in sorted(p for p in out.rglob("*") if p.is_file()):
                files[f"model_visible/{representation}/media/{path.name}"] = path.read_bytes()
    files["model_visible/manifest.json"] = pretty_bytes({"schema_version": "PASS_T_PHASE2B_INPUT_MANIFEST_V1", "opaque_window_id": source["opaque_window_id"], "representations": summaries})
    files["private/mapping.json"] = pretty_bytes(private)
    receipt = {"schema_version": "PASS_T_PHASE2B_INPUT_RECEIPT_V1", "opaque_window_id": source["opaque_window_id"], "representations": representations,
               "reference_policy": reference_policy, "gt_independent_sampling": True, "audio_included": False}
    base = base or repository_root() / "artifacts/pass_t/phase2b/inputs"
    return exclusive_tree(base, files, receipt)


def load_package(folder: Path) -> dict:
    from .common import read_json
    receipt = read_json(folder / "completion_receipt.json")
    expected = receipt.get("files_sha256", {})
    actual = {path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()}
    if actual != set(expected) | {"completion_receipt.json"}:
        raise Phase2BBlocked("INPUT_PACKAGE_FILE_SET_MISMATCH")
    for name, expected_hash in expected.items():
        from .common import safe_join
        if file_sha256(safe_join(folder, name)) != expected_hash:
            raise Phase2BBlocked("INPUT_PACKAGE_HASH_MISMATCH:" + name)
    manifest = read_json(folder / "model_visible/manifest.json")
    private = read_json(folder / "private/mapping.json")
    representations = {}
    for row in manifest["representations"]:
        rep = row["representation"]
        representations[rep] = {"payload": read_json(folder / f"model_visible/{rep}/payload.json"), "private": private["representations"][rep]}
    return {"receipt": receipt, "manifest": manifest, "private": private, "representations": representations}

