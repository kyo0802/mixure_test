"""Replay frozen identity evidence. This module never runs a perception model."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from .models import Config, EntityObservation, record
from .search_planner import find, plan_text
from .temporal_memory import TemporalMemory

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v27"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def load_inputs(task: str) -> tuple[list[dict], dict]:
    hashes = {}

    def read(relative: str):
        path = ROOT / relative
        hashes[relative] = sha(path)
        return json.loads(path.read_text(encoding="utf-8"))

    base = f"outputs_v26/{task}"
    upstream = f"outputs_v25_rerun/{task}/upstream_v21/event_analysis"
    registry = read(f"{base}/entity_registry.json")
    timeline = read(f"{base}/identity_timeline.json")["phone_timeline"]
    stream = read(f"{base}/candidate_stream.json")["observations"]
    detections = read(f"{upstream}/detections.json")
    metadata = read(f"{upstream}/video_metadata.json")
    by_frame = defaultdict(lambda: {"observations": [], "anchors": []})
    for entity in registry["entities"]:
        entity_id = entity["entity_id"]
        if entity_id.startswith("track"):
            raise ValueError("Track IDs cannot be used as persistent entity IDs")
        for index, row in enumerate(entity.get("observation_history", [])):
            # V2.6's appended match placeholder has no source and trusted=False.
            # The exact CONFIRMED_MATCH event below is the authoritative update.
            if not row.get("source") or not row.get("bbox"):
                continue
            observation = EntityObservation(entity_id, row["frame_index"], row["timestamp"], row["bbox"],
                                             row.get("semantic_label") or entity["semantic_label"],
                                             "TRUSTED" if row.get("trusted") is True else "UNKNOWN",
                                             row["source"], str(row.get("source_object_id")),
                                             f"{base}/entity_registry.json#{entity_id}/observation_history/{index}",
                                             row.get("detector_confidence"))
            key = "observations" if entity_id == "phone_01" else "anchors"
            by_frame[observation.frame][key].append(observation)
    for index, event in enumerate(stream):
        raw_index = event.get("raw_detection_index")
        if raw_index is None or not 0 <= raw_index < len(detections):
            continue
        raw = detections[raw_index]
        if raw["frame_index"] != event["frame_index"]:
            raise ValueError("Candidate source detection/frame mismatch")
        decision = event.get("reid_decision", "UNKNOWN")
        confirmed = decision == "CONFIRMED_MATCH"
        by_frame[event["frame_index"]]["observations"].append(EntityObservation(
            "phone_01" if confirmed else None, event["frame_index"], event["timestamp"], raw["bbox"],
            raw["class_name"], decision, "frozen_candidate_authorization", str(event.get("candidate_id")),
            f"{base}/candidate_stream.json#observations/{index}", raw.get("confidence")))
    # Inventory existing model evidence without treating image-only relations as physical.
    inventory = []
    for path in sorted((ROOT / upstream / "events").glob("*/scene_graph.json")):
        relative = path.relative_to(ROOT).as_posix()
        graph = read(relative)
        inventory.append({"path": relative, "analysis_status": graph.get("analysis_status"),
                          "physical_relations_available": sum(r.get("evidence", {}).get("details", {}).get("physical_verification") is True
                                                              for r in graph.get("relations", []))})
    if any(row["physical_relations_available"] for row in inventory):
        raise ValueError("New physical evidence needs an explicit causal subject/object adapter before use")
    frames = []
    for row in timeline:
        frame = row["frame_index"]
        current = by_frame[frame]
        # A target gap is determined by the frozen upstream timeline, never by an unconfirmed candidate.
        frames.append({"frame": frame, "time": row["timestamp"], "upstream_state": row.get("state"),
                       "observations": current["observations"], "anchors": current["anchors"]})
    return frames, {"input_sha256": hashes, "frame_size": [metadata["width"], metadata["height"]],
                    "fps": metadata["fps"], "sampled_frames": len(frames),
                    "upstream_entity_count": len(registry["entities"]), "existing_event_evidence": inventory,
                    "limitations": ["Existing event graphs contain no verified physical relations",
                                    "SAM observations marked untrusted remain observation-only",
                                    "Final track aliases are not used to retroactively authorize identity"]}


def run_video(task: str, config: Config | None = None) -> dict:
    config = config or Config()
    frames, provenance = load_inputs(task)
    memory = TemporalMemory(config, tuple(provenance["frame_size"]))
    for frame in frames:
        memory.step(**frame)
    folder = OUT / task
    folder.mkdir(parents=True, exist_ok=True)
    lifetime = memory.build_object_memory()
    plan = find(lifetime)
    write(folder / "observations.json", {"schema": "v27_observations_1", "config": asdict(config),
                                        "provenance": provenance, "target_and_candidate_observations": memory.observations,
                                        "relation_observations": memory.relation_observations,
                                        "identity_audit": memory.identity_audit, "node_admission_audit": memory.admission_audit,
                                        "relation_candidates": [record(c) for c in memory.candidates.values()]})
    write(folder / "relation_episodes.json", [record(e) for e in memory.episodes])
    write(folder / "temporal_memory.json", {"target": memory.target, "snapshots": memory.snapshots,
                                           "events": [record(e) for e in memory.events]})
    write(folder / "object_memory_phone_01.json", lifetime)
    write(folder / "phone_01_lifetime.json", lifetime)
    write(folder / "search_candidates.json", plan)
    (folder / "search_plan.txt").write_text(plan_text(plan), encoding="utf-8")
    return {"task": task, "sampled_frames": len(frames), "target_state": memory.target["state"],
            "last_trusted_time": memory.target["last_seen_time"], "upstream_entities": provenance["upstream_entity_count"],
            "memory_entities": len(memory.entities), "snapshots": len(memory.snapshots),
            "episodes": len(memory.episodes), "physical_episodes": sum(e.kind == "PHYSICAL" for e in memory.episodes),
            "search_candidates": len(plan["candidates"]),
            "last_trusted_anchors": memory.target["last_trusted_anchors"],
            "input_sha256": provenance["input_sha256"]}


def freeze() -> dict:
    from datetime import datetime, timezone
    files = {"outputs_v27/summary.json": sha(OUT / "summary.json")}
    for number in range(3, 10):
        folder = OUT / f"test{number}"
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.name != "evaluation.json":
                files[path.relative_to(ROOT).as_posix()] = sha(path)
    source = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT / "src/memory_graph/v27").glob("*.py"))}
    for name in ("run_v27.py", "render_v27_graphs.py"):
        source[f"scripts/{name}"] = sha(ROOT / "scripts" / name)
    result = {"schema": "v27_prediction_freeze_1", "freeze_utc": datetime.now(timezone.utc).isoformat(),
              "inference_used_gt": False, "operator_exposed_to_user_narrative": True,
              "files_sha256": files, "source_sha256": source}
    write(OUT / "prediction_manifest.json", result)
    return result


def verify_freeze() -> None:
    manifest = json.loads((OUT / "prediction_manifest.json").read_text(encoding="utf-8"))
    for relative, digest in {**manifest["files_sha256"], **manifest["source_sha256"]}.items():
        if sha(ROOT / relative) != digest:
            raise ValueError(f"Frozen prediction/source changed: {relative}")
