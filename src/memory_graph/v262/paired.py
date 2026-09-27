"""Run label-blind, frozen-window SAM 2.1 or SAM 3 predictions for one video."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from memory_graph.v22.sam_tracking import mask_to_observation
from memory_graph.v23.fusion import Observation, sam_guard
from memory_graph.v262.adapters import SAMObservation, can_reinitialize, choose_box_overlap_id, normalized_xywh


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def require_stage_b(stage: dict) -> None:
    if stage.get("decision") != "PASS":
        raise RuntimeError("Stage B requires Stage A PASS")


def extracted(folder: Path, video: Path, frames: list[int]) -> tuple[int, int]:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {video}")
    width = height = 0
    for local, source in enumerate(frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, source)
        ok, image = cap.read()
        if not ok:
            raise RuntimeError(f"Cannot extract {video.name} f{source}")
        height, width = image.shape[:2]
        if not cv2.imwrite(str(folder / f"{local:05d}.jpg"), image, [cv2.IMWRITE_JPEG_QUALITY, 95]):
            raise RuntimeError("Sampled JPEG write failed")
    cap.release()
    return width, height


def guard_record(mask: np.ndarray, task: str, frame: int, timestamp: float, segment: str,
                 source_model: str, local_id: int | None, initialization_frame: int,
                 initialized_from: str, yolo_boxes: list[list[float]], previous: dict | None,
                 mask_ref: str) -> tuple[dict, dict | None]:
    geometry = mask_to_observation(mask, frame, timestamp, segment, str(local_id), previous, yolo_boxes)
    if geometry is None:
        decision, reason, bbox, area = False, "EMPTY_OR_LOST", None, 0
    else:
        bbox, area = geometry["bbox"], geometry["mask_area"]
        obs = Observation(source=source_model, frame_index=frame, timestamp=timestamp,
                          source_object_id=str(local_id), bbox=bbox, semantic_label=None,
                          detector_confidence=None, mask_ref=mask_ref, observation_quality=None,
                          provenance="v262_frozen_box_propagation")
        guard, evidence = sam_guard(obs, geometry["diagnostics"], yolo_boxes)
        decision = guard == "ACCEPT_PROPAGATION"
        reason = None if decision else f"{guard}: {evidence['reason']}"
    record = SAMObservation(
        frame_index=frame, timestamp=timestamp, source_model=source_model,
        source_object_id=str(local_id) if local_id is not None else None,
        target_persistent_entity="phone_01", mask=mask_ref, bbox=bbox, area=area,
        confidence_if_available=None, initialization_frame=initialization_frame,
        initialized_from=initialized_from, accepted_by_guard=decision, rejection_reason=reason,
    ).record()
    record["yolo_phone_boxes"] = yolo_boxes
    record["possible_mask_drift"] = geometry["diagnostics"]["possible_mask_drift"] if geometry else None
    return record, geometry


def predict_sam21(predictor, folder: Path, frames: list[int], box: list[float]):
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        start = time.perf_counter()
        state = predictor.init_state(str(folder), offload_video_to_cpu=True, offload_state_to_cpu=True)
        session = time.perf_counter() - start
        torch.cuda.reset_peak_memory_stats()
        start = time.perf_counter()
        predictor.add_new_points_or_box(state, frame_idx=0, obj_id=1, box=np.asarray(box, dtype=np.float32))
        prompt = time.perf_counter() - start
        start = time.perf_counter()
        for local, ids, logits in predictor.propagate_in_video(state, start_frame_idx=0, max_frame_num_to_track=len(frames)):
            index = list(ids).index(1) if 1 in ids else None
            mask = (logits[index, 0] > 0).cpu().numpy() if index is not None else np.zeros(logits.shape[-2:], dtype=bool)
            yield local, 1, mask, {"session": session, "prompt": prompt, "propagation_elapsed": time.perf_counter() - start}
        predictor.reset_state(state)


def predict_sam3(predictor, folder: Path, frames: list[int], box: list[float], width: int, height: int):
    start = time.perf_counter()
    session_id = predictor.handle_request({"type": "start_session", "resource_path": str(folder),
                                           "offload_video_to_cpu": True, "offload_state_to_cpu": True})["session_id"]
    session = time.perf_counter() - start
    torch.cuda.reset_peak_memory_stats()
    prompt_box = normalized_xywh(box, width, height)
    start = time.perf_counter()
    response = predictor.handle_request({"type": "add_prompt", "session_id": session_id, "frame_index": 0,
                                         "bounding_boxes": [prompt_box], "bounding_box_labels": [1]})
    prompt = time.perf_counter() - start
    output = response["outputs"]
    ids = np.asarray(output.get("out_obj_ids", [])).astype(int).tolist()
    boxes = np.asarray(output.get("out_boxes_xywh", [])).tolist()
    chosen = choose_box_overlap_id(ids, boxes, prompt_box)
    start = time.perf_counter()
    for response in predictor.handle_stream_request({"type": "propagate_in_video", "session_id": session_id,
                                                       "propagation_direction": "forward", "start_frame_index": 0,
                                                       "max_frame_num_to_track": len(frames)}):
        local = response["frame_index"]
        output = response["outputs"]
        ids_now = np.asarray(output.get("out_obj_ids", [])).astype(int).tolist()
        masks = np.asarray(output.get("out_binary_masks", []))
        index = ids_now.index(chosen) if chosen is not None and chosen in ids_now else None
        mask = masks[index] if index is not None else np.zeros((height, width), dtype=bool)
        if local < 2:
            print("sam3_debug", local, "chosen", chosen, "ids", ids_now,
                  "areas", [int(np.count_nonzero(m)) for m in masks],
                  "selected", int(np.count_nonzero(mask)), flush=True)
        yield local, chosen, mask, {"session": session, "prompt": prompt,
                                    "propagation_elapsed": time.perf_counter() - start,
                                    "prompt_ids": ids, "selected_id": chosen, "all_ids": ids_now}
    predictor.handle_request({"type": "close_session", "session_id": session_id})


def predict_sam3point(predictor, folder: Path, frames: list[int], box: list[float], width: int, height: int):
    """Secondary instance-tracker arm, deterministic point from frozen YOLO box."""
    start = time.perf_counter()
    session_id = predictor.handle_request({"type": "start_session", "resource_path": str(folder),
                                           "offload_video_to_cpu": True, "offload_state_to_cpu": True})["session_id"]
    session = time.perf_counter() - start
    torch.cuda.reset_peak_memory_stats()
    x1, y1, x2, y2 = box
    point = [[(x1 + x2) / (2 * width), (y1 + y2) / (2 * height)]]
    start = time.perf_counter()
    response = predictor.handle_request({"type": "add_prompt", "session_id": session_id, "frame_index": 0,
                                         "points": point, "point_labels": [1], "obj_id": 1,
                                         "rel_coordinates": True})
    prompt = time.perf_counter() - start
    ids = np.asarray(response["outputs"].get("out_obj_ids", [])).astype(int).tolist()
    start = time.perf_counter()
    for response in predictor.handle_stream_request({"type": "propagate_in_video", "session_id": session_id,
                                                       "propagation_direction": "forward", "start_frame_index": 0,
                                                       "max_frame_num_to_track": len(frames),
                                                       "force_tracker_propagation": True}):
        local = response["frame_index"]
        output = response["outputs"]
        ids_now = np.asarray(output.get("out_obj_ids", [])).astype(int).tolist()
        masks = np.asarray(output.get("out_binary_masks", []))
        mask = masks[ids_now.index(1)] if 1 in ids_now else np.zeros((height, width), dtype=bool)
        yield local, 1, mask, {"session": session, "prompt": prompt,
                               "propagation_elapsed": time.perf_counter() - start,
                               "prompt_ids": ids, "selected_id": 1, "all_ids": ids_now,
                               "point": point}
    predictor.handle_request({"type": "close_session", "session_id": session_id})


def run(model: str, task: str) -> None:
    out = ROOT / "outputs_v262"
    stage = read(out / "stage_a_feasibility.json")
    require_stage_b(stage)
    manifest = read(out / "experiment_manifest.json")
    item = manifest["videos"][task]
    assert task != "test7" or all(w["init_frame"] != 636 for w in item["windows"])
    frozen_v21 = ROOT / "outputs_v25_rerun" / task / "upstream_v21" / "event_analysis"
    detections = read(frozen_v21 / "detections.json")
    fps = read(frozen_v21 / "video_metadata.json")["fps"]
    # The frozen YOLO detections are inputs; physical-target review files are not read here.
    by_frame: dict[int, list[list[float]]] = {}
    for det in detections:
        if det["class_name"] == "cell phone":
            by_frame.setdefault(det["frame_index"], []).append(det["bbox"])
    result = {"schema": "v262_prediction_1", "task": task, "model": model,
              "video_sha256": item["video_sha256"], "label_blind": True,
              "windows": {}, "status": "RUNNING"}
    write(out / task / f"{model}_predictions.json", result)
    if model == "sam21":
        for path in (ROOT / ".sam2_deps", ROOT / ".sam2_official"):
            sys.path.insert(0, str(path))
        from sam2.build_sam import build_sam2_video_predictor
        start = time.perf_counter()
        predictor = build_sam2_video_predictor("configs/sam2.1/sam2.1_hiera_s.yaml",
                                                str(ROOT / ".models" / "sam2.1_hiera_small.pt"),
                                                device="cuda", apply_postprocessing=False)
    else:
        from sam3.model_builder import build_sam3_predictor
        start = time.perf_counter()
        predictor = build_sam3_predictor(checkpoint_path=str(ROOT / ".models" / "sam3" / "sam3.pt"),
                                          version="sam3", compile=False, async_loading_frames=False,
                                          video_loader_type="cv2")
        assert "Multiplex" not in type(predictor.model).__name__
    result["model_build_seconds"] = time.perf_counter() - start
    try:
        for window in item["windows"]:
            name = window["name"]
            frames = window["frames"]
            init = window["init_frame"]
            assert frames[0] == init and window["persistent_entity_id"] == "phone_01"
            assert window.get("authorization") is None or can_reinitialize(window["authorization"])
            box = window["source_detection"]["bbox"]
            folder_out = out / task / "predictions" / name / model
            folder_out.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=f"v262_{task}_{name}_{model}_", dir=out / "smoke") as temporary:
                width, height = extracted(Path(temporary), ROOT / f"{task}.mp4", frames)
                started = time.perf_counter()
                if model == "sam21":
                    sequence = predict_sam21(predictor, Path(temporary), frames, box)
                elif model == "sam3":
                    sequence = predict_sam3(predictor, Path(temporary), frames, box, width, height)
                else:
                    sequence = predict_sam3point(predictor, Path(temporary), frames, box, width, height)
                observations = []
                previous = None
                last_meta = {}
                for local, local_id, mask, meta in sequence:
                    source = frames[local]
                    mask = np.asarray(mask, dtype=bool)
                    mask_path = folder_out / f"{source:06d}.png"
                    if not cv2.imwrite(str(mask_path), mask.astype(np.uint8) * 255):
                        raise RuntimeError(f"Could not save mask {mask_path}")
                    record, geometry = guard_record(mask, task, source, source/fps,
                                                    name, model, local_id, init, window["init_source"],
                                                    by_frame.get(source, []), previous,
                                                    str(mask_path.relative_to(ROOT)).replace("\\", "/"))
                    observations.append(record)
                    if geometry is not None:
                        previous = geometry
                    last_meta = meta
                result["windows"][name] = {
                    "frames": frames, "initialization_frame": init, "frozen_box_xyxy": box,
                    "authorization": window.get("authorization", "FROZEN_TARGET_BINDING"),
                    "source_detection": window["source_detection"],
                    "timing_seconds": {"session": last_meta.get("session"), "prompt": last_meta.get("prompt"),
                                       "propagation": last_meta.get("propagation_elapsed"),
                                       "total_window": time.perf_counter() - started},
                    "sam3_prompt_ids": last_meta.get("prompt_ids"), "sam3_selected_id": last_meta.get("selected_id"),
                    "sam3_point": last_meta.get("point"),
                    "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                    "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
                    "observations": observations,
                }
                write(out / task / f"{model}_predictions.json", result)
                print(task, model, name, len(observations), "frames", flush=True)
        result["status"] = "COMPLETE"
        write(out / task / f"{model}_predictions.json", result)
    finally:
        if model in ("sam3", "sam3point"):
            predictor.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["sam21", "sam3", "sam3point"], required=True)
    parser.add_argument("--task", choices=[f"test{i}" for i in range(3, 10)], required=True)
    args = parser.parse_args()
    run(args.model, args.task)
