"""Isolated test8 SAM3 native-text candidate discovery; no identity merge.

Run with the existing .venv_sam3. All writes stay beside this script.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROMPT = "smartphone"
IMPORTANT = (804, 840, 852, 864, 900, 924, 942)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def extract(folder: Path, frames: list[int]) -> tuple[int, int]:
    cap = cv2.VideoCapture(str(ROOT / "test8.mp4"))
    if not cap.isOpened():
        raise RuntimeError("Cannot open test8.mp4")
    width = height = 0
    try:
        for local, frame in enumerate(frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, bgr = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode test8 f{frame}")
            height, width = bgr.shape[:2]
            if not cv2.imwrite(str(folder / f"{local:05d}.jpg"), bgr, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                raise RuntimeError(f"Cannot save sampled test8 f{frame}")
    finally:
        cap.release()
    return width, height


def bbox(mask: np.ndarray) -> list[int]:
    ys, xs = np.nonzero(mask)
    return [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]


def as_candidates(output: dict, window: str, frame: int, where: str) -> list[dict]:
    ids = np.asarray(output.get("out_obj_ids", []), dtype=np.int64).tolist()
    masks = np.asarray(output.get("out_binary_masks", []))
    probs = np.asarray(output.get("out_probs", []), dtype=float).tolist()
    if len(ids) != len(masks):
        raise RuntimeError(f"SAM3 output ID/mask length differs: {window} f{frame}")
    records = []
    for index, local_id in enumerate(ids):
        mask = np.asarray(masks[index], dtype=bool)
        area = int(np.count_nonzero(mask))
        if not area:
            continue
        mask_rel = f"masks/{window}/{where}/{frame:06d}_id{local_id}.png"
        mask_path = HERE / mask_rel
        mask_path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(mask_path), mask.astype(np.uint8) * 255):
            raise RuntimeError(f"Could not write {mask_path}")
        probability = float(probs[index]) if index < len(probs) and np.isfinite(probs[index]) else None
        records.append({
            "schema": "SAM3Candidate", "concept": PROMPT, "window": window,
            "local_id": int(local_id), "frame": int(frame), "mask": mask_rel,
            "bbox": bbox(mask), "area": area, "confidence_or_probability": probability,
            "output_stage": where,
        })
    return records


def run_window(predictor, spec: dict) -> dict:
    import tempfile

    window = spec["name"]
    frames = [int(n) for n in spec["frames"]]
    with tempfile.TemporaryDirectory(prefix=f"v262_sam3_concept_{window}_", dir=HERE) as tmp:
        width, height = extract(Path(tmp), frames)
        started = time.perf_counter()
        response = predictor.handle_request({
            "type": "start_session", "resource_path": tmp,
            "offload_video_to_cpu": True, "offload_state_to_cpu": True,
        })
        session_id = response["session_id"]
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        session_seconds = time.perf_counter() - started
        try:
            started = time.perf_counter()
            response = predictor.handle_request({
                "type": "add_prompt", "session_id": session_id,
                "frame_index": 0, "text": PROMPT,
            })
            torch.cuda.synchronize()
            prompt_seconds = time.perf_counter() - started
            prompt_candidates = as_candidates(response["outputs"], window, frames[0], "prompt")
            observations = []
            started = time.perf_counter()
            for response in predictor.handle_stream_request({
                "type": "propagate_in_video", "session_id": session_id,
                "propagation_direction": "forward", "start_frame_index": 0,
                "max_frame_num_to_track": len(frames),
            }):
                local = int(response["frame_index"])
                observations.append({
                    "frame": frames[local],
                    "candidates": as_candidates(response["outputs"], window, frames[local], "propagation"),
                })
            torch.cuda.synchronize()
            propagation_seconds = time.perf_counter() - started
            if len(observations) != len(frames):
                raise RuntimeError(f"Propagation returned {len(observations)} of {len(frames)} frames in {window}")
            result = {
                "window": window, "source_frames": frames, "frame_size": [width, height],
                "local_id_namespace": window,
                "prompt_candidates": prompt_candidates,
                "observations": observations,
                "timing_seconds": {"session": session_seconds, "prompt": prompt_seconds,
                                   "propagation": propagation_seconds},
                "peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
                "peak_reserved_bytes": int(torch.cuda.max_memory_reserved()),
            }
            return result
        finally:
            predictor.handle_request({"type": "close_session", "session_id": session_id})


def continuity(window: dict) -> list[dict]:
    by_id: dict[int, list[int]] = defaultdict(list)
    for index, row in enumerate(window["observations"]):
        for candidate in row["candidates"]:
            by_id[candidate["local_id"]].append(index)
    tracks = []
    for local_id, positions in sorted(by_id.items()):
        longest = run = 1
        reappearances = 0
        for old, new in zip(positions, positions[1:]):
            if new == old + 1:
                run += 1
            else:
                reappearances += 1
                run = 1
            longest = max(longest, run)
        tracks.append({
            "window": window["window"], "local_id": local_id,
            "first_frame": window["observations"][positions[0]]["frame"],
            "last_frame": window["observations"][positions[-1]]["frame"],
            "frames_present": len(positions), "longest_consecutive_sampled_run": longest,
            "reappearance_after_gap_count": reappearances,
        })
    return tracks


def draw_contact(window: dict) -> None:
    cap = cv2.VideoCapture(str(ROOT / "test8.mp4"))
    if not cap.isOpened():
        raise RuntimeError("Cannot open test8 for contact sheet")
    colors = [(20, 220, 40), (20, 140, 250), (235, 90, 220), (245, 205, 35), (110, 50, 245)]
    rows = []
    by_frame = {r["frame"]: r for r in window["observations"]}
    try:
        for frame in IMPORTANT:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, original = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode contact frame {frame}")
            overlay = original.copy()
            labels = []
            for candidate in by_frame[frame]["candidates"]:
                local_id = candidate["local_id"]
                color = colors[local_id % len(colors)]
                mask = cv2.imread(str(HERE / candidate["mask"]), cv2.IMREAD_GRAYSCALE)
                if mask is None:
                    raise RuntimeError(f"Cannot read mask {candidate['mask']}")
                overlay[mask > 0] = (0.48 * overlay[mask > 0] + 0.52 * np.asarray(color)).astype(np.uint8)
                x1, y1, x2, y2 = candidate["bbox"]
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 3)
                prob = candidate["confidence_or_probability"]
                name = f"ID {local_id}" + (f" p={prob:.2f}" if prob is not None else "")
                cv2.putText(overlay, name, (max(0, x1), max(25, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 5, cv2.LINE_AA)
                cv2.putText(overlay, name, (max(0, x1), max(25, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2, cv2.LINE_AA)
                labels.append(name)
            banner = np.zeros((72, original.shape[1] * 2, 3), dtype=np.uint8)
            cv2.putText(banner, f"test8 f{frame} | original", (15, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.9, (255, 255, 255), 2, cv2.LINE_AA)
            summary = f"SAM3 text: {len(labels)} candidate(s) | " + (", ".join(labels) if labels else "none")
            cv2.putText(banner, summary[:105], (original.shape[1] + 15, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.75, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(banner, f"Local IDs belong only to the f804 session; no phone_01 assignment", (15, 62),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.64, (180, 180, 180), 2, cv2.LINE_AA)
            rows.append(np.vstack((banner, np.hstack((original, overlay)))))
    finally:
        cap.release()
    sheet = np.vstack(rows)
    if not cv2.imwrite(str(HERE / "test8_sam3_concept_contact_sheet.png"), sheet):
        raise RuntimeError("Could not write contact sheet")


def existing_arm(model: str) -> dict:
    prediction = read(ROOT / "outputs_v262" / "test8" / f"{model}_predictions.json")
    windows = prediction["windows"]
    rows = [row for w in windows.values() for row in w["observations"]]
    unique_frames = {row["frame_index"] for row in rows}
    unique_nonempty = {row["frame_index"] for row in rows if row["area"] > 0}
    return {
        "sampled_frames": len(rows),
        "distinct_video_frames": len(unique_frames),
        "frames_with_any_mask": sum(row["area"] > 0 for row in rows),
        "distinct_video_frames_with_any_mask": len(unique_nonempty),
        "total_candidate_ids": len({(name, row["source_object_id"]) for name, w in windows.items()
                                    for row in w["observations"] if row["area"] > 0}),
        "propagation_seconds": sum(w["timing_seconds"]["propagation"] for w in windows.values()),
        "peak_reserved_bytes": max(w["peak_reserved_bytes"] for w in windows.values()),
        "source": f"outputs_v262/test8/{model}_predictions.json",
    }


def main() -> None:
    from sam3.model_builder import build_sam3_predictor

    manifest = read(ROOT / "outputs_v262" / "experiment_manifest.json")
    windows = manifest["videos"]["test8"]["windows"]
    expected = [("target_full", 150, 204), ("same_identity_reinit", 50, 804)]
    if [(w["name"], len(w["frames"]), w["frames"][0]) for w in windows] != expected:
        raise RuntimeError("Frozen test8 windows differ from expected V2.6.2 baseline")
    checkpoint = ROOT / ".models" / "sam3" / "sam3.pt"
    model_sha = sha256(checkpoint)
    if model_sha != "9999e2341ceef5e136daa386eecb55cb414446a00ac2b55eb2dfd2f7c3cf8c9e":
        raise RuntimeError("Official SAM3 checkpoint hash differs from V2.6.2")
    provenance = {
        "video_sha256": sha256(ROOT / "test8.mp4"), "checkpoint_sha256": model_sha,
        "frozen_manifest_sha256": sha256(ROOT / "outputs_v262" / "experiment_manifest.json"),
        "official_source_revision": "2345a4ad109ac29c569da749c91d84f10dc08c40",
        "prompt": PROMPT, "identity_merge": False, "gt_used": False,
    }
    if provenance["video_sha256"] != manifest["videos"]["test8"]["video_sha256"]:
        raise RuntimeError("test8 video differs from frozen manifest")
    predictor = build_sam3_predictor(checkpoint_path=str(checkpoint), version="sam3",
                                     compile=False, async_loading_frames=False, video_loader_type="cv2")
    if "Multiplex" in type(predictor.model).__name__:
        raise RuntimeError("This experiment requires SAM3, not SAM3.1")
    result = {"schema": "v262_supplementary_sam3_concept_1", "provenance": provenance,
              "status": "RUNNING", "windows": {}}
    save(HERE / "candidates.json", result)
    try:
        for spec in windows:
            window = run_window(predictor, spec)
            result["windows"][spec["name"]] = window
            save(HERE / "candidates.json", result)
            print(f"{spec['name']}: {len(window['observations'])} sampled frames; "
                  f"{sum(bool(row['candidates']) for row in window['observations'])} frames with candidates", flush=True)
        result["status"] = "COMPLETE"
        save(HERE / "candidates.json", result)
    finally:
        predictor.shutdown()
    reinit = result["windows"]["same_identity_reinit"]
    draw_contact(reinit)
    all_rows = [row for window in result["windows"].values() for row in window["observations"]]
    tracks = [track for window in result["windows"].values() for track in continuity(window)]
    important_rows = {str(frame): next(row["candidates"] for row in reinit["observations"]
                                      if row["frame"] == frame) for frame in IMPORTANT}
    comparison = {
        "schema": "v262_supplementary_comparison_1", "scope": "test8 only, two frozen sampled windows",
        "provenance": provenance, "models": {
            "sam3_box_existing": existing_arm("sam3"),
            "sam3_point_existing": existing_arm("sam3point"),
            "sam3_text_smartphone": {
                "sampled_frames": len(all_rows),
                "distinct_video_frames": len({row["frame"] for row in all_rows}),
                "frames_with_any_mask": sum(bool(row["candidates"]) for row in all_rows),
                "distinct_video_frames_with_any_mask": len({row["frame"] for row in all_rows if row["candidates"]}),
                "total_candidate_ids": len(tracks),
                "candidate_id_namespace": "local to each window, never phone_01",
                "total_candidate_observations": sum(len(row["candidates"]) for row in all_rows),
                "propagation_seconds": sum(w["timing_seconds"]["propagation"] for w in result["windows"].values()),
                "prompt_seconds": sum(w["timing_seconds"]["prompt"] for w in result["windows"].values()),
                "peak_reserved_bytes": max(w["peak_reserved_bytes"] for w in result["windows"].values()),
                "source": "outputs_v262/supplementary_sam3_concept/candidates.json",
            },
        },
        "per_window": {name: {
            "sampled_frames": len(w["observations"]),
            "frames_with_any_mask": sum(bool(row["candidates"]) for row in w["observations"]),
            "prompt_candidate_ids": [row["local_id"] for row in w["prompt_candidates"]],
            "candidate_ids_in_propagation": sorted({c["local_id"] for row in w["observations"] for c in row["candidates"]}),
            "peak_reserved_bytes": w["peak_reserved_bytes"],
            "propagation_seconds": w["timing_seconds"]["propagation"],
        } for name, w in result["windows"].items()},
        "important_frame_candidates": important_rows,
        "local_id_continuity": tracks,
        "physical_identity_review": "PENDING_MANUAL_VISUAL_REVIEW",
    }
    save(HERE / "comparison.json", comparison)
    print("Wrote candidate records, comparison, and one contact sheet", flush=True)


def render_existing() -> None:
    result = read(HERE / "candidates.json")
    if result["status"] != "COMPLETE":
        raise RuntimeError("Inference is not complete")
    reinit = result["windows"]["same_identity_reinit"]
    draw_contact(reinit)
    comparison = read(HERE / "comparison.json")
    comparison["important_frame_candidates"] = {
        str(frame): next(row["candidates"] for row in reinit["observations"] if row["frame"] == frame)
        for frame in IMPORTANT
    }
    comparison["models"]["sam3_box_existing"] = existing_arm("sam3")
    comparison["models"]["sam3_point_existing"] = existing_arm("sam3point")
    all_rows = [row for w in result["windows"].values() for row in w["observations"]]
    text_arm = comparison["models"]["sam3_text_smartphone"]
    text_arm["distinct_video_frames"] = len({row["frame"] for row in all_rows})
    text_arm["distinct_video_frames_with_any_mask"] = len({row["frame"] for row in all_rows if row["candidates"]})
    save(HERE / "comparison.json", comparison)
    print("Regenerated one contact sheet and candidate table without model inference")


if __name__ == "__main__":
    if sys.argv[1:] == ["--render-only"]:
        render_existing()
    elif not sys.argv[1:]:
        main()
    else:
        raise SystemExit("Usage: run_concept.py [--render-only]")
