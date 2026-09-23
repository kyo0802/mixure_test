"""V2 orchestration; V1 source, CLI and output directories are not modified."""
import json
import logging
from pathlib import Path
import re
import time
from .memory.memory_store import save_json
from .perception.track_manager import collect_tracks
from .events.event_proposer import propose_events, merge_events
from .events.keyframe_selector import prepare_windows
from .vlm.base import create_backend
from .vlm.hardware import hardware_report
from .vlm.cache import analyze_cached
from .scene_graph.builder import build_scene, observation_index
from .scene_graph.fusion import aggregate_entities
from .memory.temporal_memory import build_memory
from .visualization.event_visualizer import render_timeline
from .visualization.scene_graph_visualizer import render_semantic_graph
from .visualization.memory_graph_visualizer import render_memory
from .visualization.video_visualizer_v2 import render_video_v2
from .vlm.schemas import INTERACTIONS
from .vlm.schemas import VLMSceneGraphResult
from .vlm.prompts import make_prompt

log = logging.getLogger(__name__)


def _prepare_output(output):
    output = Path(output).resolve()
    v1 = Path("outputs").resolve()
    if output == v1 or v1 in output.parents or output in [Path.cwd(), Path.cwd().parent]:
        raise ValueError("V2 output must be separate from V1 outputs and project root")
    output.mkdir(parents=True, exist_ok=True)
    # Invalidate only known previous presentation artifacts. Perception and content-addressed VLM caches survive.
    for name in ["memory_graph.json", "memory_graph.png", "annotated_v2.mp4", "event_timeline.png", "run_status.json"]:
        (output/name).unlink(missing_ok=True)
    events_dir = output/"events"
    if events_dir.exists():
        for directory in events_dir.iterdir():
            if directory.is_dir() and re.fullmatch(r"evt_\d+", directory.name):
                for name in ["before.jpg", "during.jpg", "after.jpg", "event.json", "vlm_raw.json", "scene_graph.json",
                             "scene_graph.png", "scene_graph.png.render.json", "analysis_error.json", "keyframes.json", "vlm_input.json",
                             "vlm_validated.json", "prompt.txt", "track_crops.jpg", "track_crops.json"]:
                    (directory/name).unlink(missing_ok=True)
                for crop in directory.glob("identity_*.jpg"):
                    if re.fullmatch(r"identity_\d+_(before|during|after)\.jpg", crop.name):
                        crop.unlink()
                if not any(directory.iterdir()):
                    directory.rmdir()
    return output


def _track_metadata(event, frames, timelines):
    tracks = {t.track_id: t for t in timelines}
    observations = observation_index(timelines)
    result = []
    for tid in frames[0].supplied_track_ids:
        positions = []
        for frame in frames:
            obs = observations.get(frame.frame_index, {}).get(tid)
            positions.append({"phase": frame.phase, "timestamp": frame.timestamp, "visible": obs is not None,
                              "bbox": obs.bbox if obs else None})
        result.append({"track_id": tid, "detector_hypothesis": tracks[tid].detector_class,
                       "detector_confidence": tracks[tid].mean_detector_confidence, "observations": positions})
    return result


def run_video_v2(source, config, output=None, events_only=False, backend=None):
    source = Path(source).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Missing video: {source}")
    output = _prepare_output(output or Path("outputs_v2")/source.stem)
    handler = logging.FileHandler(output/"run.log", mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(handler)
    start = time.monotonic()
    save_json(output/"run_status.json", {"status": "running"})
    try:
        log.info("Processing %s with V2; VLM=%s", source.name, "events-only" if events_only else config.vlm.backend)
        hardware = hardware_report()
        save_json(output/"hardware.json", hardware)
        save_json(output/"run_config.json", config)
        save_json(output/"vlm_schema.json", VLMSceneGraphResult.model_json_schema())
        metadata, episodes, timelines = collect_tracks(source, output, config)
        log.info("Building track timelines: %d fixed numeric track IDs", len(timelines))
        raw = propose_events(timelines, metadata.duration, config.events)
        events = merge_events(raw, config.events)
        save_json(output/"raw_event_proposals.json", raw)
        save_json(output/"merged_events.json", events)
        log.info("Events: %d raw signals, %d merged, %d selected windows", len(raw), len(events), sum(e.selected for e in events))
        windows = prepare_windows(source, output, events, timelines, metadata, config)
        render_timeline(events, metadata.duration, output/"event_timeline.png")
        save_json(output/"active_event_ids.json", list(windows))
        backend_error = None
        if not events_only and backend is None and config.vlm.backend != "disabled":
            try:
                backend = create_backend(config.vlm)
            except Exception as error:
                backend_error = str(error)
                log.error("VLM unavailable; keeping event/geometry outputs: %s", error)
        results, scenes, event_records = [], [], []
        attempted = cache_hits = failures = partial_events = generation_calls = component_failures = 0
        for event in events:
            record = event.model_dump()
            if not event.selected:
                event_records.append({**record, "analysis_status": "skipped_budget"})
                continue
            directory = output/"events"/event.event_id
            frames = windows[event.event_id]
            save_json(directory/"event.json", event)
            save_json(directory/"keyframes.json", frames)
            track_metadata = _track_metadata(event, frames, timelines)
            event_metadata = {"event_id": event.event_id, "event_type": event.event_type, "signals": event.signals,
                "start_time": event.start_time, "peak_time": event.peak_time, "end_time": event.end_time,
                "bbox_coordinate_system": "original video pixels; images may be resized; match the drawn numeric IDs",
                "original_image_size": {"width": metadata.width, "height": metadata.height},
                "frames": [{"phase": f.phase, "timestamp": f.timestamp, "visible_ids": f.visible_track_ids} for f in frames]}
            save_json(directory/"vlm_input.json", {"tracks": track_metadata, "event": event_metadata})
            (directory/"prompt.txt").write_text(make_prompt(track_metadata, event_metadata), encoding="utf-8")
            result = None
            status = "skipped_events_only" if events_only else "unavailable" if backend_error else "skipped_disabled"
            error_message = backend_error
            if backend is not None and not events_only:
                attempted += 1
                log.info("Analyzing event %s (%d/%d)", event.event_id, attempted, len(windows))
                try:
                    result, hit = analyze_cached(backend, [*[directory/f.image_path for f in frames], directory/"track_crops.jpg"], track_metadata,
                        event_metadata, output/".vlm_cache", directory/"vlm_raw.json")
                    results.append(result)
                    save_json(directory/"vlm_validated.json", result)
                    cache_hits += int(hit)
                    raw_record = json.loads((directory/"vlm_raw.json").read_text(encoding="utf-8"))
                    errors = raw_record.get("component_errors", [])
                    component_failures += len(errors)
                    generation_calls += 0 if hit else max(1, len(raw_record.get("generation_trace", [])))
                    status = "partial" if errors else "success"
                    partial_events += int(bool(errors))
                except Exception as error:
                    failures += 1
                    status, error_message = "failed", str(error)
                    log.error("Event %s VLM failure; continuing: %s", event.event_id, error)
                    save_json(directory/"analysis_error.json", {"error": error_message, "status": status})
            if not (directory/"vlm_raw.json").exists():
                save_json(directory/"vlm_raw.json", {"status": status, "response": None, "error": error_message,
                          "reason": "VLM skipped/failed; no synthetic or heuristic semantic substitution"})
            scene = build_scene(event, frames, timelines, metadata, config, result, status)
            save_json(directory/"scene_graph.json", scene)
            render_semantic_graph(scene.entities, scene.relations, directory/"scene_graph.png",
                                 f"{source.name} | {event.event_id}", config.graph, status)
            scenes.append(scene)
            event_records.append({**record, "analysis_status": status, "analysis_error": error_message,
                                  "keyframe_times": [f.timestamp for f in frames]})
        entities, rejected, aggregation = aggregate_entities(timelines, events, results, config)
        save_json(output/"confirmed_entities.json", [e for e in entities if e.semantic_class != "unknown"])
        save_json(output/"unknown_entities.json", [e for e in entities if e.semantic_class == "unknown"])
        save_json(output/"rejected_tracks.json", rejected)
        save_json(output/"semantic_aggregation.json", aggregation)
        save_json(output/"entity_id_mapping.json", [{"track_id": e.track_id, "entity_id": e.entity_id} for e in entities])
        memory = build_memory(source.name, {**metadata.model_dump(), "hardware": hardware,
            "vlm_backend": backend.identity if backend else {"backend": "disabled" if not backend_error else "unavailable"},
            "events_only": events_only}, entities, scenes, event_records, config.graph)
        save_json(output/"memory_graph.json", memory)
        render_memory(memory, output/"memory_graph.png", config.graph)
        render_video_v2(source, output/"annotated_v2.mp4", timelines, memory, events, metadata.sampled_frames)
        report = {"status": "complete", "semantic_status": "validated_results_available" if results else "not_analyzed_or_validated",
            "video": source.name, "raw_track_ids": len(timelines), "raw_event_signals": len(raw), "merged_events": len(events),
            "selected_events": len(windows), "vlm_attempted_events": attempted, "vlm_analyzed_events": len(results),
            "vlm_failed_events": failures, "cache_hits": cache_hits, "skipped_events": len(events)-len(results),
            "vlm_partial_events": partial_events, "vlm_component_failures": component_failures,
            "vlm_generation_calls": generation_calls,
            "confirmed_semantic_entities": sum(e.semantic_class != "unknown" for e in entities),
            "unknown_entities": sum(e.semantic_class == "unknown" for e in entities), "rejected_tracks": len(rejected),
            "semantic_corrections": [{"track_id": e.track_id, "detector_class": e.detector_class, "semantic_class": e.semantic_class}
                for e in entities if e.semantic_class not in {"unknown", e.detector_class}],
            "semantic_relations": sum(r.evidence.vlm for r in memory.relations),
            "geometry_only_relations": sum(not r.evidence.vlm for r in memory.relations),
            "interaction_relations": sum(r.predicate in INTERACTIONS for r in memory.relations),
            "transitions": len(memory.transitions), "decoded_frames": metadata.decoded_frame_count,
            "elapsed_seconds": time.monotonic()-start, "backend_error": backend_error}
        save_json(output/"run_status.json", report)
        log.info("Completed: %d semantic entities, %d unknown, %d rejected; %d semantic / %d geometric relations",
                 report["confirmed_semantic_entities"], report["unknown_entities"], len(rejected),
                 report["semantic_relations"], report["geometry_only_relations"])
        return memory
    except Exception as error:
        save_json(output/"run_status.json", {"status": "failed", "error": str(error)})
        log.exception("V2 pipeline failed")
        raise
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()
