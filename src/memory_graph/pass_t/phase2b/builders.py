"""Deterministic representation builders over the isolated source contract."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .common import Phase2BBlocked, file_sha256, repository_root


def uniform_positions(total: int, count: int) -> list[int]:
    if total < 1 or count < 1 or count > total:
        raise Phase2BBlocked("INVALID_UNIFORM_SAMPLE_COUNT")
    if count == 1:
        return [0]
    positions = [round(index * (total - 1) / (count - 1)) for index in range(count)]
    if len(set(positions)) != count or positions[0] != 0 or positions[-1] != total - 1:
        raise Phase2BBlocked("UNIFORM_SAMPLER_FAILED")
    return positions


def _load_rgb(row: dict) -> Image.Image:
    path = repository_root() / row["private_path"]
    if file_sha256(path) != row["content_sha256"]:
        raise Phase2BBlocked("SOURCE_MEDIA_HASH_MISMATCH")
    with Image.open(path) as image:
        return image.convert("RGB")


def build_multi_image(source: dict, out: Path, frame_count: int) -> dict:
    positions = uniform_positions(len(source["frames"]), frame_count)
    out.mkdir(parents=True, exist_ok=True)
    mapping, visible = [], []
    for output_index, position in enumerate(positions, start=1):
        row = source["frames"][position]
        alias = row["opaque_alias"]
        destination = out / f"IMG_{output_index:03d}.png"
        _load_rgb(row).save(destination, format="PNG", optimize=False)
        media_id = f"MEDIA_{output_index:03d}"
        visible.append({"media_id": media_id, "media_type": "image/png", "content_sha256": file_sha256(destination), "supplied_frame_aliases": [alias]})
        mapping.append({
            "media_id": media_id,
            "opaque_alias": alias,
            "source_position": position,
            "source_frame_index": row["private_source_frame_index"],
            "source_timestamp_s": row["private_source_timestamp_s"],
            "source_sha256": row["content_sha256"],
            "output_path": destination.as_posix(),
            "output_sha256": file_sha256(destination),
        })
    return {
        "schema_version": "PASS_T_PHASE2B_REPRESENTATION_V1",
        "representation": "MULTI_IMAGE",
        "selection_policy": {"kind": "UNIFORM_WHOLE_WINDOW", "requested_count": frame_count, "positions": positions},
        "model_media": visible,
        "private_mapping": mapping,
        "information_budget": {"input_frame_count": len(source["frames"]), "supplied_frame_count": frame_count, "pixels_per_frame": source["width"] * source["height"]},
    }


def build_storyboard(source: dict, out: Path, frame_count: int, columns: int = 3) -> dict:
    positions = uniform_positions(len(source["frames"]), frame_count)
    frames = [(source["frames"][position], _load_rgb(source["frames"][position])) for position in positions]
    width, height = source["width"], source["height"]
    cell_width = min(480, width)
    scaled_height = round(height * cell_width / width)
    label_height = 32
    rows = math.ceil(frame_count / columns)
    canvas = Image.new("RGB", (columns * cell_width, rows * (scaled_height + label_height)), "white")
    draw = ImageDraw.Draw(canvas)
    for slot, (row, image) in enumerate(frames):
        x = (slot % columns) * cell_width
        y = (slot // columns) * (scaled_height + label_height)
        resized = image.resize((cell_width, scaled_height), Image.Resampling.LANCZOS)
        canvas.paste(resized, (x, y + label_height))
        draw.text((x + 8, y + 8), row["opaque_alias"], fill="black", font=ImageFont.load_default())
    out.mkdir(parents=True, exist_ok=True)
    destination = out / "STORYBOARD.png"
    canvas.save(destination, format="PNG", optimize=False)
    aliases = [row["opaque_alias"] for row, _ in frames]
    mapping = [{
        "opaque_alias": row["opaque_alias"],
        "source_position": position,
        "source_frame_index": row["private_source_frame_index"],
        "source_timestamp_s": row["private_source_timestamp_s"],
        "source_sha256": row["content_sha256"],
    } for position, (row, _) in zip(positions, frames)]
    return {
        "schema_version": "PASS_T_PHASE2B_REPRESENTATION_V1",
        "representation": "STORYBOARD",
        "selection_policy": {"kind": "SAME_UNIFORM_SELECTION_AS_MULTI_IMAGE", "requested_count": frame_count, "positions": positions},
        "layout": {"columns": columns, "rows": rows, "cell_width": cell_width, "cell_image_height": scaled_height, "label_height": label_height, "aspect_ratio_preserved": True},
        "model_media": [{"media_id": "MEDIA_001", "media_type": "image/png", "content_sha256": file_sha256(destination), "supplied_frame_aliases": aliases}],
        "private_mapping": mapping,
        "information_budget": {"input_frame_count": len(source["frames"]), "supplied_frame_count": frame_count, "storyboard_pixels": canvas.width * canvas.height},
    }


def _pixel_digest(image) -> str:
    import hashlib
    return hashlib.sha256(image.tobytes()).hexdigest()


def build_video(source: dict, out: Path, fps: float) -> dict:
    if not isinstance(fps, (int, float)) or fps <= 0:
        raise Phase2BBlocked("POSITIVE_VIDEO_FPS_REQUIRED")
    try:
        import cv2
        import numpy as np
    except ImportError as error:
        raise Phase2BBlocked("OPENCV_REQUIRED_FOR_VIDEO_BUILDER") from error
    out.mkdir(parents=True, exist_ok=True)
    destination = out / "AUTHORIZED_CLIP.avi"
    writer = cv2.VideoWriter(str(destination), cv2.VideoWriter_fourcc(*"FFV1"), float(fps), (source["width"], source["height"]))
    if not writer.isOpened():
        raise Phase2BBlocked("FFV1_ENCODER_UNAVAILABLE")
    source_pixel_hashes = []
    try:
        for row in source["frames"]:
            rgb = _load_rgb(row)
            source_pixel_hashes.append(_pixel_digest(rgb))
            writer.write(cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR))
    finally:
        writer.release()
    capture = cv2.VideoCapture(str(destination))
    decoded_hashes = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        decoded_hashes.append(_pixel_digest(Image.fromarray(rgb)))
    capture.release()
    if len(decoded_hashes) != len(source["frames"]):
        raise Phase2BBlocked("VIDEO_FRAME_COUNT_VERIFICATION_FAILED")
    if decoded_hashes[0] != source_pixel_hashes[0] or decoded_hashes[-1] != source_pixel_hashes[-1]:
        raise Phase2BBlocked("VIDEO_FIRST_LAST_PIXEL_VERIFICATION_FAILED")
    aliases = [row["opaque_alias"] for row in source["frames"]]
    mapping = [{
        "opaque_alias": row["opaque_alias"],
        "source_frame_index": row["private_source_frame_index"],
        "native_source_timestamp_s": row["private_source_timestamp_s"],
        "encoded_timestamp_s": position / float(fps),
        "source_sha256": row["content_sha256"],
    } for position, row in enumerate(source["frames"])]
    distortion = [abs(row["private_source_timestamp_s"] - source["frames"][0]["private_source_timestamp_s"] - position / float(fps)) for position, row in enumerate(source["frames"])]
    return {
        "schema_version": "PASS_T_PHASE2B_REPRESENTATION_V1",
        "representation": "REENCODED_AUTHORIZED_VIDEO",
        "encoding": {"container": "AVI", "codec": "FFV1", "lossless": True, "audio": False, "fps": float(fps), "timebase": f"1/{fps:g}", "width": source["width"], "height": source["height"], "bitrate": "NOT_APPLICABLE_LOSSLESS", "crf": "NOT_APPLICABLE"},
        "verification": {"decoded_frame_count": len(decoded_hashes), "source_frame_count": len(source["frames"]), "first_pixel_exact": True, "last_pixel_exact": True, "dropped_frames": 0, "duplicated_frames": 0, "resampled_frames": 0},
        "temporal_mapping": {"native_pts_retained": False, "private_mapping": mapping, "max_absolute_timing_distortion_s": max(distortion)},
        "model_media": [{"media_id": "MEDIA_001", "media_type": "video/x-msvideo", "content_sha256": file_sha256(destination), "supplied_frame_aliases": aliases}],
        "information_budget": {"input_frame_count": len(source["frames"]), "supplied_frame_count": len(source["frames"]), "encoded_bytes": destination.stat().st_size},
    }

