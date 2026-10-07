from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import cv2

from memory_graph.v2101_deploy.contracts import schema_sha256


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/v2.10.1/smoke"
SOURCE_REQUESTS = "outputs/reference_qwen/model_7b/requests.json"
SOURCE_RESPONSES = "outputs/reference_qwen/model_7b/responses.json"
SOURCE_PACKS = "outputs/reference_qwen/event_packs/event_pack_manifest.json"
SAMPLE_INTERVAL_S = 0.4  # fixed 2.5 FPS target


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_sha(value) -> str:
    return sha_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def select_indices(times: list[float]) -> list[int]:
    if not times:
        return []
    start, end = times[0], times[-1]
    targets = [start]
    slot = start + SAMPLE_INTERVAL_S
    while slot < end - SAMPLE_INTERVAL_S * 0.45:
        targets.append(slot)
        slot += SAMPLE_INTERVAL_S
    if end - targets[-1] > SAMPLE_INTERVAL_S * 0.45:
        targets.append(end)
    chosen: list[int] = []
    for target in targets:
        idx = min(range(len(times)), key=lambda i: (abs(times[i] - target), i))
        if idx not in chosen:
            chosen.append(idx)
    return sorted(chosen)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    clip_root = OUT / "temporal_clips"
    clip_root.mkdir(parents=True, exist_ok=True)
    requests = json.loads((ROOT / SOURCE_REQUESTS).read_text(encoding="utf-8"))
    responses = json.loads((ROOT / SOURCE_RESPONSES).read_text(encoding="utf-8"))
    packs = json.loads((ROOT / SOURCE_PACKS).read_text(encoding="utf-8"))
    input_path = OUT / "input_manifest.json"
    prior_manifest = json.loads(input_path.read_text(encoding="utf-8")) if input_path.exists() else None
    if not (len(requests) == len(responses) == len(packs) == 9):
        raise RuntimeError(f"Frozen control must contain exactly 9 requests/responses/packs; got {len(requests)}/{len(responses)}/{len(packs)}")
    req_by_id = {x["pack_id"]: x for x in requests}
    resp_by_id = {x["pack_id"]: x for x in responses}
    events = []
    for pack in packs:
        event_id = pack["pack_id"]
        req = req_by_id[event_id]
        prior = resp_by_id[event_id]
        if not pack.get("identity_authorized") or not pack.get("provenance_valid"):
            raise RuntimeError(f"Frozen reference pack is not authorized/provenance-valid: {event_id}")
        if not prior.get("actual_inference") or prior.get("parse_or_runtime_error"):
            raise RuntimeError(f"Frozen reference pack does not have a completed historical Qwen response: {event_id}")
        frames = pack.get("frames", [])
        images = req.get("images", [])
        image_hashes = req.get("image_sha256", [])
        if not frames or len(frames) != len(images) or len(images) != len(image_hashes):
            raise RuntimeError(f"Frozen frame/image mapping is incomplete for {event_id}: {len(frames)}/{len(images)}/{len(image_hashes)}")
        reference_prompt_hash_matches = sha_bytes(req["prompt"].encode("utf-8")) == req["prompt_sha256"]
        markers = list((pack.get("markers") or {}).keys())
        schema_hash = schema_sha256(markers)
        media_candidates = [ROOT / f"{pack['video_id']}.mp4", ROOT / "videos" / f"{pack['video_id']}.mp4"]
        media_path = next((candidate for candidate in media_candidates if candidate.is_file()), None)
        if media_path is None:
            raise FileNotFoundError(f"Frozen source video not found for {event_id}: {media_candidates}")
        source_media = {"path": relative(media_path), "sha256": sha_file(media_path), "size_bytes": media_path.stat().st_size}
        frame_times = [float(row["time"]) for row in frames]
        start_time, end_time = frame_times[0], frame_times[-1]
        selected = select_indices(frame_times)
        if len(selected) > 16:
            # The deterministic interval is already bounded; retain evenly spaced samples if a future source pack grows.
            selected = [selected[round(i * (len(selected) - 1) / 15)] for i in range(16)]
            selected = sorted(set(selected))
        image_records = []
        for index in selected:
            image_path = (ROOT / images[index]).resolve() if not Path(images[index]).is_absolute() else Path(images[index])
            if not image_path.is_file():
                raise FileNotFoundError(f"Frozen event image missing: {image_path}")
            actual_hash = sha_file(image_path)
            if actual_hash != image_hashes[index]:
                raise RuntimeError(f"Frozen event image hash mismatch: {event_id}:{index}")
            frame = frames[index]
            image_records.append({
                "sequence_index": len(image_records), "original_frame": frame["frame"],
                "timestamp_seconds": frame["time"], "phase": frame["phase"],
                "image_path": relative(image_path), "image_sha256": actual_hash,
            })
        selected_phases = ", ".join(frame["phase"] for frame in image_records)
        actual_prompt, phase_replacements = re.subn(
            r"Image phases in order: .*?\. Same-image reference panels repeat that image\.",
            f"Image phases in order: {selected_phases}. Same-image reference panels repeat that image.",
            req["prompt"],
            count=1,
        )
        if phase_replacements != 1:
            raise RuntimeError(f"Could not adapt the frozen phase line for the reduced ordered sequence: {event_id}")
        actual_prompt_hash = sha_bytes(actual_prompt.encode("utf-8"))

        clip_path = clip_root / f"{event_id}.mp4"
        if clip_path.exists():
            old_event = next((row for row in (prior_manifest or {}).get("events", []) if row.get("pack_id") == event_id), None)
            if not old_event or old_event.get("temporal_clip", {}).get("sha256") != sha_file(clip_path):
                raise RuntimeError(f"Existing clip does not match a prior v2.10.1 input manifest: {event_id}")
        first = cv2.imread(str(ROOT / image_records[0]["image_path"]), cv2.IMREAD_COLOR)
        if first is None:
            raise RuntimeError(f"OpenCV could not decode frozen event image: {image_records[0]['image_path']}")
        height, width = first.shape[:2]
        writer = cv2.VideoWriter(str(clip_path), cv2.VideoWriter_fourcc(*"mp4v"), 1.0 / SAMPLE_INTERVAL_S, (width, height))
        if not writer.isOpened():
            raise RuntimeError(f"OpenCV MP4 writer unavailable for {relative(clip_path)}")
        try:
            for image in image_records:
                frame = cv2.imread(str(ROOT / image["image_path"]), cv2.IMREAD_COLOR)
                if frame is None or frame.shape[:2] != (height, width):
                    raise RuntimeError(f"Frozen frame decode/shape mismatch: {image['image_path']}")
                writer.write(frame)
        finally:
            writer.release()
        if not clip_path.is_file() or clip_path.stat().st_size <= 0:
            raise RuntimeError(f"Temporal clip creation failed: {relative(clip_path)}")

        representation = {
            "pack_id": event_id, "event_id": pack["event_id"], "video_id": pack["video_id"],
            "source_media_path": source_media["path"], "source_media_sha256": source_media["sha256"],
            "start_frame": frames[0]["frame"], "end_frame": frames[-1]["frame"],
            "start_timestamp_seconds": start_time, "end_timestamp_seconds": end_time,
            "requested_fps": 1.0 / SAMPLE_INTERVAL_S, "sampling_interval_seconds": SAMPLE_INTERVAL_S,
            "selected_frames": image_records, "prompt_sha256": actual_prompt_hash,
            "schema_sha256": schema_hash,
        }
        events.append({
            **representation,
            "target_id": pack.get("target_id"), "target_marker": pack.get("target_marker"),
            "markers": markers,
            "source_media": source_media,
            "frozen_source": {
                "event_pack_manifest": SOURCE_PACKS,
                "reference_qwen_request": SOURCE_REQUESTS,
                "reference_qwen_response": SOURCE_RESPONSES,
                "qwen_historical_revision": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
                "identity_authorized": pack["identity_authorized"],
                "provenance_valid": pack["provenance_valid"],
                "identity_write_authorized": pack.get("identity_write_authorized"),
                "historical_qwen_actual_inference": prior.get("actual_inference"),
            },
            "frame_selection_note": (
                "Selected only from existing frozen rendered event images; no video decode, new annotation, GT, or relabeling. "
                "The request targets 2.5 FPS. Existing pack durations/frame inventory limit some events below 8 frames."
            ),
            "representation_sha256": canonical_sha(representation),
            "temporal_clip": {
                "path": relative(clip_path), "size_bytes": clip_path.stat().st_size,
                "sha256": sha_file(clip_path), "container": "MP4", "codec": "mp4v",
                "fps": 1.0 / SAMPLE_INTERVAL_S, "width": width, "height": height,
                "frame_count": len(image_records),
            },
            "prompt": actual_prompt,
            "historical_reference_prompt_sha256": req["prompt_sha256"],
            "historical_reference_prompt_hash_matches_rendered_text": reference_prompt_hash_matches,
            "historical_prompt_hash_note": (None if reference_prompt_hash_matches else
                "The frozen request's recorded prompt_sha256 differs from SHA-256 of its stored prompt text; the historical request artifact is preserved, and v2.10.1 hashes the exact prompt bytes it sends."),
            "request_source_sha256": sha_file(ROOT / SOURCE_REQUESTS),
        })

    crop_root = ROOT / "outputs/v295_reid/crops/test1"
    crop_candidates = sorted(p for p in crop_root.glob("*.png") if "_mask" not in p.name) if crop_root.is_dir() else []
    if len(crop_candidates) < 3:
        raise RuntimeError("Expected at least three existing clean development crops for the multi-image smoke test")
    multi_images = [{"order": idx, "path": relative(path), "sha256": sha_file(path), "size_bytes": path.stat().st_size}
                    for idx, path in enumerate(crop_candidates[:3])]

    input_manifest = {
        "schema": "findmind_v2101_stage0_input_manifest_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "event_set": {
            "source": SOURCE_PACKS,
            "canonical_reference": "V2.9.4.5 frozen Qwen control: 9 canonical requests / 9 recorded actual inference responses",
            "pack_count": len(events),
            "all_reference_packs_identity_authorized_and_provenance_valid": True,
            "explicit_complete_enum": "The event-pack manifest does not carry a COMPLETE enum; no COMPLETE label is inferred. The frozen 9-request/9-response reference set is used verbatim.",
        },
        "sampling": {
            "policy": "fixed 2.5 FPS target via deterministic nearest-existing-frame selection within the frozen rendered sequence",
            "requested_fps": 1.0 / SAMPLE_INTERVAL_S,
            "min_frames_when_possible": 8, "max_frames": 16,
            "selected_frames_are_not_augmented": True,
            "same_frame_sequence_for_both_models": True,
        },
        "events": events,
        "multi_image_smoke": {
            "purpose": "input ordering and request compatibility only; no identity accuracy evaluation",
            "source": "outputs/v295_reid/crops/test1",
            "ordered_images": multi_images,
        },
        "frozen_controls": {
            "qwen_model": "Qwen/Qwen2.5-VL-7B-Instruct",
            "qwen_revision": "cc594898137f460bfe9f0759e9844b3ce807cfb5",
            "qwen_status": "HISTORICAL_FROZEN_CONTROL",
            "qwen_not_rerun": True,
        },
    }
    path = input_path
    if prior_manifest is not None:
        old_ids = [row.get("pack_id") for row in prior_manifest.get("events", [])]
        new_ids = [row.get("pack_id") for row in events]
        old_clips = {row.get("pack_id"): row.get("temporal_clip", {}).get("sha256") for row in prior_manifest.get("events", [])}
        if old_ids != new_ids or any(old_clips.get(row["pack_id"]) != row["temporal_clip"]["sha256"] for row in events):
            raise RuntimeError("Refusing to update the input manifest if its frozen event/clip set differs")
    path.write_text(json.dumps(input_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("events", len(events), "frames", sum(len(e["selected_frames"]) for e in events))
    for event in events:
        print(event["pack_id"], "frames", len(event["selected_frames"]), "clip", event["temporal_clip"]["size_bytes"], "sha256", event["temporal_clip"]["sha256"])
    print("multi_image_crops", len(multi_images))
    print("input_manifest_sha256", sha_file(path))


if __name__ == "__main__":
    main()
