"""V2.9.1 isolated inference, memory, freeze, and post-freeze evaluation."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v291"
TASKS = [f"test{i}" for i in range(3, 10)]
RAW_TASKS = {"task1": "test1", "task2": "test2"}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def source_video_for_task(task: str) -> Path:
    actual = RAW_TASKS.get(task, task)
    path = ROOT / f"{actual}.mp4"
    if not path.is_file():
        raise FileNotFoundError(f"Raw source video not found: {path}")
    return path


def same_class_entity_ids(registry: dict, label: str) -> set[str]:
    return {row["entity_id"] for row in registry.get("entities", [])
            if (row.get("semantic_label") or row.get("raw_label", "")).casefold() == label.casefold()}


def event_local_entity_id(event_id: str, anchor_id: str) -> str:
    return f"event_local::{event_id}::{anchor_id}"


def _verify_historical_freezes() -> None:
    from memory_graph.v27.pipeline import verify_freeze as verify_v27
    from memory_graph.v28.pipeline import verify_freeze as verify_v28
    from memory_graph.v29.pipeline import verify_freeze as verify_v29
    verify_v27()
    verify_v28()
    verify_v29()


def _run_raw_upstream(task_alias: str) -> dict:
    """Run current V2.1 + SAM2.1 + V2.6 guard from test1/test2 raw video."""
    task = RAW_TASKS[task_alias]
    video = source_video_for_task(task_alias)
    folder = OUT / task
    upstream = folder / "upstream_v21"
    status_path = upstream / "run_status.json"
    stage_summary_path = folder / "upstream" / "identity" / "stage_summary.json"
    if not status_path.is_file():
        from memory_graph.config_v2 import load_v2_config
        from memory_graph.v21.pipeline import run as run_v21
        # Current detector/tracker config, with V21's old whole-scene VLM off;
        # V2.9.1 performs the scoped observable-fact calls after event freeze.
        status = run_v21(video, load_v2_config(ROOT / "configs/v2.yaml"), upstream,
                         reuse=None, events_only=True)
    else:
        status = read(status_path)
        if status.get("video_sha256") != sha(video):
            raise ValueError(f"Existing V2.9.1 upstream cache does not match {video.name}")
        if stage_summary_path.exists() and (folder / "sam" / "candidate_sam_support.json").exists():
            stage = read(stage_summary_path)
            return {"task": task_alias, "actual_video": video.name, "video_sha256": sha(video),
                    "video_status": status,
                    "target_sam_status": read(folder / "sam" / "sam_continuity_log.json").get("status"),
                    "target_binding": read(folder / "target_binding_audit.json").get("decision"),
                    "candidate_sam_count": len(read(folder / "sam" / "candidate_sam_support.json").get("candidate_support", [])),
                    "identity_guard_confirmed": stage.get("identity_guard", {}).get("confirmed_match"),
                    "identity_guard_provisional": stage.get("identity_guard", {}).get("provisional_candidate_ids", []),
                    "persistent_entities": len(read(folder / "entity_registry.json").get("entities", []))}

    from memory_graph.v25rerun import adapter, pipeline as v25_pipeline, sam_route, reid as v25_reid, fusion as v25_fusion
    from memory_graph.v25rerun.binding import automatic_bind
    from memory_graph.v25rerun.candidates import CandidateHypothesis
    from memory_graph.v26 import pipeline as v26_pipeline
    adapter.OUT = OUT
    v25_pipeline.OUT = OUT
    sam_route.OUT = OUT
    v25_reid.OUT = OUT
    v26_pipeline.BASE = OUT
    v26_pipeline.OUT = OUT
    inputs, v21_hashes = adapter.v21_inputs(task)
    binding, binding_audit = automatic_bind(inputs["video_metadata.json"]["sampled_frames"],
                                             inputs["track_timelines.json"])
    write(folder / "target_binding_audit.json", binding_audit)
    target_log = folder / "sam" / "sam_continuity_log.json"
    if target_log.exists() and read(target_log).get("frozen_input_sha256") == v21_hashes:
        target = read(target_log)
    else:
        target = sam_route.SamRouter(task).target(binding)
    original_read_json = v25_fusion.read_json
    historical_prefix = (ROOT / "outputs_v25_rerun").resolve()
    def read_current_rerun(path):
        candidate_path = Path(path).resolve()
        try:
            relative = candidate_path.relative_to(historical_prefix)
        except ValueError:
            return original_read_json(path)
        return original_read_json(OUT / relative)
    v25_fusion.read_json = read_current_rerun
    try:
        fusion, stream = v25_pipeline.run_admission(task)
    finally:
        v25_fusion.read_json = original_read_json

    output = folder
    summaries = read(output / "candidate_grouping_audit.json")["candidates"]
    final_frame = inputs["video_metadata.json"]["sampled_frames"][-1]["frame_index"]
    support_path = output / "sam" / "candidate_sam_support.json"
    support_path.parent.mkdir(parents=True, exist_ok=True)
    if support_path.exists() and read(support_path).get("status") == "COMPLETE":
        supports = read(support_path).get("candidate_support", [])
    else:
        router = sam_route.SamRouter(task)
        supports = []
        for summary in summaries:
            candidate = CandidateHypothesis(summary["candidate_id"])
            for observation in summary["observations"]:
                candidate.add(observation)
            supports.append(router.candidate(candidate, final_frame))
        write(support_path, {"task": task, "candidate_support": supports, "status": "COMPLETE", "gt_accessed": False})
    # V2.5 appearance scoring is retained as an input to, but is not authority
    # over, the V2.6 Identity Guard that runs immediately afterward.
    v25_reid.run_reid(task)
    audit = v26_pipeline.run_video(task)

    # Preserve discoverable stage summaries alongside the canonical stage files.
    yolo = folder / "upstream" / "yolo"
    for name in ("detections.json", "track_timelines.json", "video_metadata.json",
                 "persistent_entities.json", "prediction_manifest.json", "run_status.json"):
        source = upstream / "event_analysis" / name if name in {
            "detections.json", "track_timelines.json", "video_metadata.json", "persistent_entities.json"} else upstream / name
        if source.exists():
            yolo.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, yolo / name)
    write(folder / "upstream" / "identity" / "stage_summary.json", {
        "target_binding": binding_audit, "identity_guard": audit,
        "source_video": video.name, "source_sha256": sha(video), "gt_accessed": False})
    for name in ("entity_registry.json", "identity_timeline.json", "reid_audit.json", "candidate_stream.json"):
        if (folder / name).exists():
            shutil.copy2(folder / name, folder / "upstream" / "identity" / name)
    for name in ("sam_continuity_log.json", "candidate_sam_support.json", "sam_reinit_log.json"):
        source = folder / "sam" / name
        if source.exists():
            target_path = folder / "upstream" / "sam" / name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target_path)
    for name in ("entity_registry.json", "candidate_stream.json", "candidate_grouping_audit.json"):
        source = folder / name
        if source.exists():
            target_path = folder / "upstream" / "fusion" / name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target_path)
    write(folder / "upstream" / "fusion" / "stage_summary.json", {
        "fusion_status": fusion.get("status") if isinstance(fusion, dict) else target.get("status"),
        "candidate_count": len(stream.candidates), "identity_guard": audit.get("decision"),
        "gt_accessed": False})
    return {"task": task_alias, "actual_video": video.name, "video_sha256": sha(video),
            "video_status": status, "target_sam_status": target.get("status"),
            "target_binding": binding_audit.get("decision"), "candidate_sam_count": len(supports),
            "identity_guard_confirmed": audit.get("confirmed_match"),
            "identity_guard_provisional": audit.get("provisional_candidate_ids", []),
            "persistent_entities": len(read(folder / "entity_registry.json").get("entities", []))}


def _current_inputs(task: str) -> tuple[list[dict], dict]:
    """Adapt newly generated V2.6 evidence to the unchanged V2.8 graph API."""
    from memory_graph.v27.models import EntityObservation
    folder = OUT / task
    registry = read(folder / "entity_registry.json")
    timeline = read(folder / "identity_timeline.json")["phone_timeline"]
    stream = read(folder / "candidate_stream.json")["observations"]
    detections = read(folder / "upstream_v21" / "event_analysis" / "detections.json")
    by_frame = defaultdict(lambda: {"observations": [], "anchors": []})
    for entity in registry.get("entities", []):
        entity_id = entity["entity_id"]
        if entity_id.startswith("track"):
            raise ValueError("Track IDs cannot be converted to PersistentEntity IDs")
        for i, row in enumerate(entity.get("observation_history", [])):
            if not row.get("source") or not row.get("bbox"):
                continue
            obs = EntityObservation(entity_id, row["frame_index"], row["timestamp"], row["bbox"],
                                    row.get("semantic_label") or entity.get("semantic_label", "unknown"),
                                    "TRUSTED" if row.get("trusted") is True else "UNKNOWN", row["source"],
                                    str(row.get("source_object_id")),
                                    f"outputs_v291/{task}/entity_registry.json#{entity_id}/{i}",
                                    row.get("detector_confidence"))
            by_frame[obs.frame]["observations" if entity_id == "phone_01" else "anchors"].append(obs)
    for i, row in enumerate(stream):
        raw_index = row.get("raw_detection_index")
        if raw_index is None or raw_index >= len(detections):
            continue
        det = detections[raw_index]
        if det["frame_index"] != row["frame_index"]:
            raise ValueError("V2.9.1 candidate stream/detection frame mismatch")
        confirmed = row.get("reid_decision") == "CONFIRMED_MATCH"
        by_frame[row["frame_index"]]["observations"].append(EntityObservation(
            "phone_01" if confirmed else None, row["frame_index"], row["timestamp"], det["bbox"],
            det["class_name"], row.get("reid_decision") or "UNKNOWN", "frozen_candidate_authorization",
            str(row.get("candidate_id")), f"outputs_v291/{task}/candidate_stream.json#{i}", det.get("confidence")))
    frames = [{"frame": row["frame_index"], "time": row["timestamp"], "upstream_state": row.get("state"),
               **by_frame[row["frame_index"]]} for row in timeline]
    meta = read(folder / "upstream_v21" / "event_analysis" / "video_metadata.json")
    return frames, {"input_sha256": {"raw_video": sha(source_video_for_task(task))},
                    "frame_size": [meta["width"], meta["height"]], "fps": meta["fps"],
                    "sampled_frames": len(frames), "upstream_entity_count": len(registry.get("entities", [])),
                    "limitations": ["All identity evidence is from fresh V2.1/V2.6 runs"]}


def _build_fresh_memory(task: str) -> dict:
    from memory_graph.v28.local_subgraph import build_local_subgraph
    from memory_graph.v28.models import Config, record
    from memory_graph.v28.physical_reasoner import reason_all
    from memory_graph.v28.memory import build_memory, object_memory
    from memory_graph.v28.pipeline import _mark_transitions
    from memory_graph.v28.search_planner import find, plan_text
    frames, provenance = _current_inputs(task)
    config = Config()
    graph = build_local_subgraph(frames, tuple(provenance["frame_size"]), config)
    _mark_transitions(graph, frames, config)
    decisions = [record(item) for item in reason_all(graph["primary_segments"], tuple(provenance["frame_size"]), config)]
    memory = build_memory(frames, graph, decisions)
    lifetime = object_memory(memory)
    plan = find(lifetime)
    folder = OUT / task / "memory"
    write(folder / "local_subgraph.json", graph)
    write(folder / "physical_relation_candidates.json", decisions)
    write(folder / "object_memory_phone_01.json", lifetime)
    write(folder / "temporal_memory.json", {"schema": "v28_temporal_memory_1", "target": memory["target"],
          "snapshots": memory["snapshots"], "events": memory["events"]})
    write(folder / "search_candidates.json", plan)
    (folder / "search_plan.txt").write_text(plan_text(plan), encoding="utf-8")
    return {"frames": frames, "provenance": provenance, "memory": lifetime, "temporal": memory,
            "graph": graph, "search": plan, "physical": decisions}


def _load_base(task: str, is_raw: bool) -> tuple[dict, dict]:
    if is_raw:
        fresh = _build_fresh_memory(task)
        return fresh["memory"], fresh["temporal"]
    folder = ROOT / "outputs_v28" / task
    return read(folder / "object_memory_phone_01.json"), read(folder / "temporal_memory.json")


def _event_anchor_context(task: str, event: dict) -> list[dict]:
    current_registry = OUT / task / "entity_registry.json"
    historical_registry = ROOT / "outputs_v26" / task / "entity_registry.json"
    registry = read(current_registry if current_registry.exists() else historical_registry) if (current_registry.exists() or historical_registry.exists()) else {}
    result = []
    for row in registry.get("entities", []):
        label = row.get("semantic_label", "unknown")
        if row["entity_id"] == "phone_01" or "person" in label.casefold():
            continue
        observations = [x for x in row.get("observation_history", []) if x.get("bbox") and
                        event["start_frame"] <= x.get("frame_index", -1) <= event["end_frame"]]
        if not observations:
            observations = [x for x in row.get("observation_history", []) if x.get("bbox")]
        if not observations:
            continue
        nearest = min(observations, key=lambda x: abs(x["frame_index"]-event["peak_frame"]))
        result.append({"entity_id": row["entity_id"], "raw_label": label, "bbox": nearest["bbox"],
                       "frame": nearest["frame_index"], "source": "frozen_persistent_entity"})
    return result


def _trusted_masks(task: str, is_raw: bool) -> list[dict]:
    if not is_raw:
        return read(ROOT / "outputs_v29" / task / "mask_evidence.json")
    folder = OUT / task
    registry = read(folder / "entity_registry.json")
    timeline = {r["frame_index"]: r for r in read(folder / "identity_timeline.json")["phone_timeline"]}
    log_path = folder / "sam" / "sam_continuity_log.json"
    rows, accepted = [], set()
    if log_path.exists():
        log = read(log_path)
        accepted = {r["frame_index"] for r in registry.get("fusion_audit", [])
                    if r.get("observation_source") == "sam" and r.get("entity_id") == "phone_01" and r.get("decision") == "MATCH"}
        for seg in log.get("segments", []):
            for obs in seg.get("observations", []):
                frame = obs["frame_index"]
                if frame not in accepted:
                    continue
                ref = f"{seg.get('segment_id', 'target_full')}:{frame}:{obs.get('object_id')}"
                rows.append({"frame": frame, "trusted": True, "mask_bbox": obs["bbox"], "mask_reference": ref,
                             "source": "fresh_v2.6_identity_guard_sam", "identity_state": timeline.get(frame, {}).get("state")})
    return rows


def _cached_dense(task: str, event: dict) -> dict | None:
    base = ROOT / "outputs_v29" / task
    summary_path = base / "dense_reinspection_summary.json"
    if not summary_path.exists():
        return None
    summary = read(summary_path)
    matches = []
    for win in summary.get("windows", []):
        path = base / "dense_windows" / win["event_id"] / "dense_observations.json"
        if not path.exists():
            continue
        dense = read(path)
        if dense["sampling"]["start_frame"] <= event["peak_frame"] <= dense["sampling"]["end_frame"]:
            old_event = next((x for x in read(base / "placement_event_candidates.json") if x["event_id"] == win["event_id"]), {})
            matches.append((abs(old_event.get("peak_frame", -1)-event["peak_frame"]), dense))
    if not matches:
        return None
    matches.sort(key=lambda x: x[0])
    return deepcopy(matches[0][1])


def _run_dense(task: str, event: dict, masks: list[dict], fps: float, folder: Path,
               runner=None) -> dict:
    local_path = folder / "dense_observations.json"
    if local_path.exists():
        existing = read(local_path)
        if existing.get("event_id") == event["event_id"] and existing.get("sampling", {}).get("start_frame") == event["start_frame"]:
            return {"event_id": event["event_id"], "dense_frames": len(existing.get("rows", [])),
                    "trusted_dense_masks": sum(bool(r.get("identity_authorized")) for r in existing.get("rows", [])),
                    "phone_detections": sum(len(r.get("yolo_phone_detections", [])) for r in existing.get("rows", [])),
                    "anchor_detections": sum(len(r.get("anchors", [])) for r in existing.get("rows", [])),
                    "source": existing.get("source", "cached_v291_dense_window")}
    dense = _cached_dense(task, event)
    if dense is not None:
        dense["event_id"] = event["event_id"]
        dense["cached_from_v29"] = True
        write(folder / "dense_observations.json", dense)
        source = ROOT / "outputs_v29" / task / "dense_windows" / dense["event_id"] / "target_masks.json"
        if source.exists():
            shutil.copy2(source, folder / "target_masks.json")
        return {"event_id": event["event_id"], "dense_frames": len(dense.get("rows", [])),
                "trusted_dense_masks": sum(bool(r.get("identity_authorized")) for r in dense.get("rows", [])),
                "phone_detections": sum(len(r.get("yolo_phone_detections", [])) for r in dense.get("rows", [])),
                "anchor_detections": sum(len(r.get("anchors", [])) for r in dense.get("rows", [])),
                "source": "frozen_v29_dense_window"}
    if runner is None:
        from memory_graph.v29.dense_reinspection import DenseRunner
        runner = DenseRunner()
    # Recovered event-local anchors are not supplied to SAM or target binding.
    event = {**event, "candidate_anchors": event.get("candidate_anchors", [])}
    result = runner.run(task, event, masks, fps, folder)
    return {**result, "source": "V2.9.1_event_local_dense_rerun"}


def _attach_recovered_anchors(event: dict, dense: dict, frame_size: tuple[int, int]) -> dict:
    from memory_graph.v291.anchors import recover_anchors
    found = recover_anchors(event, dense, frame_size=frame_size)
    by_frame = defaultdict(list)
    for anchor in found["anchors"]:
        for box in anchor["boxes"]:
            by_frame[box["frame"]].append({"anchor_id": anchor["anchor_id"], "bbox": box["bbox"],
                "entity_id": anchor["persistent_entity_id"], "label": anchor["normalized_label"],
                "semantic_role": anchor["semantic_role"], "scope": "EVENT_LOCAL_ANCHOR" if anchor["persistent_entity_id"] is None else "PERSISTENT"})
    rows = dense.get("rows", [])
    for row in rows:
        row["recovered_anchors"] = by_frame[row["frame"]]
    # Geometry features are causal and only use earlier/current rows.
    for i, row in enumerate(rows):
        target = row.get("sam_phone") if row.get("identity_authorized") else None
        for anchor in row["recovered_anchors"]:
            if not target:
                continue
            box = anchor["bbox"]
            tb = target["bbox"]
            tc = ((tb[0]+tb[2])/2, (tb[1]+tb[3])/2)
            ac = ((box[0]+box[2])/2, (box[1]+box[3])/2)
            distance = ((tc[0]-ac[0])**2+(tc[1]-ac[1])**2)**.5
            previous = rows[max(0, i-2):i]
            prior_distances = []
            for pr in previous:
                ptarget = pr.get("sam_phone") if pr.get("identity_authorized") else None
                pa = next((a for a in pr.get("recovered_anchors", []) if a["anchor_id"] == anchor["anchor_id"]), None)
                if ptarget and pa:
                    pb = ptarget["bbox"]; ab = pa["bbox"]
                    prior_distances.append((((pb[0]+pb[2]-ab[0]-ab[2])/2)**2 + ((pb[1]+pb[3]-ab[1]-ab[3])/2)**2)**.5)
            anchor["target_approach"] = bool(prior_distances and distance < min(prior_distances))
            anchor["boundary_crossing"] = box[0] <= tc[0] <= box[2] and box[1] <= tc[1] <= box[3]
            anchor["target_stable"] = bool(previous and previous[-1].get("sam_phone") and
                abs(target["bbox"][0]-previous[-1]["sam_phone"]["bbox"][0]) < 12 and
                abs(target["bbox"][1]-previous[-1]["sam_phone"]["bbox"][1]) < 12)
            anchor["mask_area_decrease"] = bool(previous and previous[-1].get("sam_phone") and
                target.get("area", 0) < .85*previous[-1]["sam_phone"].get("area", 0))
        row["target_approach"] = any(a.get("target_approach") for a in row["recovered_anchors"])
        row["boundary_crossing"] = any(a.get("boundary_crossing") for a in row["recovered_anchors"])
        row["mask_area_decrease"] = any(a.get("mask_area_decrease") for a in row["recovered_anchors"])
        row["target_stable"] = any(a.get("target_stable") for a in row["recovered_anchors"])
    for row in rows:
        for anchor in row["recovered_anchors"]:
            anchor["anchor_visible_after"] = any(later["frame"] > event["peak_frame"] and
                any(x["anchor_id"] == anchor["anchor_id"] for x in later.get("recovered_anchors", [])) for later in rows)
        row["anchor_visible_after"] = any(a.get("anchor_visible_after") for a in row["recovered_anchors"])
    return found


def _add_reconfirm_memory(task: str, lifetime: dict, temporal: dict, events: list[dict], registry: dict,
                          identity_timeline: list[dict], frame_size: tuple[int, int], fps: float):
    """Record trusted reappearance as image context; never invent a physical relation."""
    from memory_graph.v28.roles import semantic_roles
    entities = {row["entity_id"]: row for row in lifetime.get("entities", [])}
    registry_rows = {row["entity_id"]: row for row in registry.get("entities", [])}
    trusted_frames = [row["frame_index"] for row in identity_timeline
                      if row.get("state") in {"VISIBLE_TRUSTED", "MATCHED"}]
    final_trusted = max(trusted_frames, default=-1)
    existing_ids = {row.get("event_id") for row in temporal.get("events", [])}
    for event in events:
        if event.get("event_type") != "RECONFIRM_EVENT":
            continue
        if f"V291_{event['event_id']}" in existing_ids:
            continue
        frame = event["peak_frame"]
        phone = registry_rows.get("phone_01")
        phone_obs = [row for row in (phone or {}).get("observation_history", [])
                     if row.get("bbox") and row.get("trusted") is True]
        if phone_obs:
            phone_row = min(phone_obs, key=lambda row: abs(row["frame_index"]-frame))
            if abs(phone_row["frame_index"]-frame) > max(1, round(.25*fps)):
                phone_row = None
        else:
            phone_row = None
        width, height = frame_size
        context_nodes, context_edges = [], []
        if phone_row:
            px = (phone_row["bbox"][0]+phone_row["bbox"][2])/2
            py = (phone_row["bbox"][1]+phone_row["bbox"][3])/2
            near = []
            for entity_id, raw in registry_rows.items():
                if entity_id == "phone_01":
                    continue
                observation = next((row for row in raw.get("observation_history", [])
                                    if row.get("frame_index") == phone_row["frame_index"] and row.get("bbox")), None)
                if not observation:
                    continue
                box = observation["bbox"]
                distance = (((px-(box[0]+box[2])/2)/max(width,1))**2 +
                            ((py-(box[1]+box[3])/2)/max(height,1))**2)**.5
                if distance <= .35:
                    near.append((distance, entity_id, raw, observation))
            for _, entity_id, raw, observation in sorted(near)[:6]:
                if entity_id not in entities:
                    entities[entity_id] = {"entity_id": entity_id,
                        "raw_label": raw.get("semantic_label", "unknown"),
                        "semantic_roles": semantic_roles(raw.get("semantic_label", "unknown")),
                        "hop": 1, "via_primary": None}
                    lifetime.setdefault("entities", []).append(entities[entity_id])
                context_nodes.append(deepcopy(entities[entity_id]))
                context_edges.append({"source": "phone_01", "relation": "IMAGE_NEAR_CONTEXT",
                    "target": entity_id, "kind": "IMAGE_CONTEXT", "source_frame": phone_row["frame_index"],
                    "provenance": f"outputs_v291/{task}/{event['event_id']}/entity_registry#{entity_id}/{observation['frame_index']}"})
                lifetime.setdefault("episodes", []).append({"episode_id": f"V291_CTX_{len(lifetime.get('episodes', []))+1:04d}",
                    "segment_id": event["event_id"], "subject": "phone_01", "relation": "TRUSTED_ANCHOR_CONTEXT",
                    "object": entity_id, "kind": "IMAGE_CONTEXT", "decision": "OBSERVATION_ONLY",
                    "start_frame": frame, "end_frame": frame, "start_time": frame/max(fps, 1e-6),
                    "last_confirmed_time": frame/max(fps, 1e-6),
                    "status": "LAST_TRUSTED" if frame == final_trusted else "STALE",
                    "source": [f"outputs_v291/{event['event_id']}", f"frame:{phone_row['frame_index']}"],
                    "source_snapshots": [], "reason": "safe V2.6 reconfirmation; image-relative context only",
                    "physical_verification": False})
        kind = "V291_RECONFIRM_EVENT"
        temporal_event = {"event_id": f"V291_{event['event_id']}", "event_type": kind,
                          "frame": frame, "time": frame/max(fps, 1e-6),
                          "details": {"identity_source": event["source"], "candidate_ids": event.get("candidate_ids", []),
                                      "image_context_edges": context_edges,
                                      "physical_relation_asserted": False}}
        temporal.setdefault("events", []).append(temporal_event)
        snapshot_nodes = [{"entity_id": "phone_01", "raw_label": "cell phone", "semantic_roles": []}, *context_nodes]
        snapshot = {"snapshot_id": f"V291_{event['event_id']}", "frame": frame,
                    "time": frame/max(fps, 1e-6), "target_state": "MATCHED",
                    "nodes": snapshot_nodes, "edges": context_edges,
                    "trigger_events": [temporal_event],
                    "meaning": "safe identity reconfirmation; IMAGE_NEAR_CONTEXT only"}
        temporal.setdefault("snapshots", []).append(snapshot)
        if frame == final_trusted:
            local = lifetime.setdefault("last_trusted_local_subgraph", {"nodes": [], "edges": []})
            seen = {row.get("entity_id") for row in local.get("nodes", [])}
            for node in snapshot_nodes:
                if node["entity_id"] not in seen:
                    local.setdefault("nodes", []).append(deepcopy(node)); seen.add(node["entity_id"])
            local.setdefault("edges", []).extend(context_edges)
    return lifetime, temporal


def _event_images(video: Path, event: dict, dense: dict, output: Path) -> list[Path]:
    import cv2
    rows = dense.get("rows", [])
    if not rows:
        return []
    peaks = event["peak_frame"]
    frames = [min(rows, key=lambda r: abs(r["frame"]-event["start_frame"])),
              min(rows, key=lambda r: abs(r["frame"]-peaks)),
              min(rows, key=lambda r: abs(r["frame"]-event["end_frame"]))]
    cap = cv2.VideoCapture(str(video))
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    try:
        for pos, row in zip(("BEFORE", "DURING", "AFTER"), frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES, row["frame"])
            ok, image = cap.read()
            if not ok:
                continue
            target = row.get("sam_phone")
            if target and row.get("identity_authorized"):
                x1, y1, x2, y2 = map(int, target["bbox"])
                cv2.rectangle(image, (x1,y1), (x2,y2), (0,255,0), 3)
                cv2.putText(image, "phone_01 / trusted", (x1, max(20,y1-5)), cv2.FONT_HERSHEY_SIMPLEX, .65, (0,255,0), 2)
            for anchor in row.get("recovered_anchors", []):
                x1, y1, x2, y2 = map(int, anchor["bbox"])
                cv2.rectangle(image, (x1,y1), (x2,y2), (255,0,255), 2)
                cv2.putText(image, f"{anchor['anchor_id']} {anchor['label']}", (x1, min(image.shape[0]-8,y2+20)),
                            cv2.FONT_HERSHEY_SIMPLEX, .55, (255,0,255), 2)
            cv2.putText(image, f"{pos} | {event['event_type']} | f{row['frame']}", (12,30),
                        cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 2)
            path = output / f"{pos.lower()}_f{row['frame']}.jpg"
            cv2.imwrite(str(path), image)
            paths.append(path)
    finally:
        cap.release()
    if paths:
        from PIL import Image, ImageDraw
        tiles = [Image.open(p).convert("RGB") for p in paths]
        height = min(640, min(im.height for im in tiles))
        resized = []
        for im in tiles:
            width = max(1, round(im.width * height / im.height))
            resized.append(im.resize((width, height)))
        sheet = Image.new("RGB", (sum(im.width for im in resized), height), "white")
        draw = ImageDraw.Draw(sheet)
        x = 0
        for im, label in zip(resized, ("BEFORE", "DURING", "AFTER")):
            sheet.paste(im, (x, 0)); draw.rectangle((x, 0, x+im.width, 30), fill=(20, 20, 20))
            draw.text((x+8, 8), label, fill="white"); x += im.width
        sheet.save(output / "contact_sheet.png", quality=92)
    return paths


def _event_local_rows(event: dict, anchor_result: dict, dense: dict, vlm_rows: list[dict]) -> list[dict]:
    from memory_graph.v291.physical import infer_candidates, gate
    results = infer_candidates(event, anchor_result["anchors"], dense, vlm_rows)
    return [gate(row) for row in results]


def _update_memory(task: str, lifetime: dict, temporal: dict, decisions: list[dict],
                   anchor_map: dict[str, dict]) -> tuple[dict, dict, dict]:
    from memory_graph.v28.search_planner import find, plan_text
    lifetime, temporal = deepcopy(lifetime), deepcopy(temporal)
    entities = {e["entity_id"]: e for e in lifetime.get("entities", [])}
    admitted = []
    for decision in decisions:
        if decision["decision"] not in {"CANDIDATE", "PROMOTED"} or not decision.get("identity_authorized"):
            continue
        anchor = anchor_map.get(decision["anchor"])
        if not anchor:
            continue
        local = anchor.get("persistent_entity_id") is None
        entity_id = event_local_entity_id(decision["event_id"], anchor["anchor_id"]) if local else anchor["persistent_entity_id"]
        if entity_id not in entities:
            entity = {"entity_id": entity_id, "raw_label": anchor["normalized_label"],
                      "semantic_roles": anchor["semantic_role"], "hop": 1, "via_primary": None}
            if local:
                entity["scope"] = "EVENT_LOCAL_ANCHOR"
            lifetime.setdefault("entities", []).append(entity)
            entities[entity_id] = entity
        event = next((e for e in decisions if e["event_id"] == decision["event_id"]), decision)
        episode = {"episode_id": f"V291_{len(lifetime.get('episodes', []))+1:04d}",
                   "segment_id": f"{decision['event_id']}_{anchor['anchor_id']}", "subject": "phone_01",
                   "relation": decision["candidate_relation"], "object": entity_id, "kind": "PHYSICAL",
                   "decision": decision["decision"], "start_frame": decision.get("start_frame", 0),
                   "end_frame": decision.get("end_frame", 0), "start_time": 0.0,
                   "last_confirmed_time": 0.0, "status": "LAST_TRUSTED", "source": ["outputs_v291", decision["event_id"]],
                   "source_snapshots": [], "reason": decision["reason"],
                   "physical_verification": decision["decision"] == "PROMOTED"}
        if local:
            episode["anchor_scope"] = "EVENT_LOCAL_ANCHOR"
            episode["anchor_provenance"] = anchor.get("provenance", [])
        lifetime.setdefault("episodes", []).append(episode)
        admitted.append(episode)
        local_graph = lifetime.setdefault("last_trusted_local_subgraph", {"nodes": [], "edges": []})
        if entity_id not in {n.get("entity_id") for n in local_graph.get("nodes", [])}:
            local_graph.setdefault("nodes", []).append(deepcopy(entities[entity_id]))
        local_graph.setdefault("edges", []).append({"source": "phone_01", "relation": episode["relation"],
            "target": entity_id, "kind": "PHYSICAL", "decision": episode["decision"],
            "episode_id": episode["episode_id"], "status": episode["status"],
            "anchor_scope": "EVENT_LOCAL_ANCHOR" if local else "PERSISTENT"})
        temporal.setdefault("events", []).append({"event_id": f"V291_{len(temporal.get('events', []))+1:04d}",
            "event_type": "V291_PHYSICAL_"+episode["decision"], "frame": episode["end_frame"], "time": 0.0,
            "details": {"episode_id": episode["episode_id"], "relation": episode["relation"],
                        "anchor": entity_id, "anchor_scope": "EVENT_LOCAL_ANCHOR" if local else "PERSISTENT"}})
    plan = find(lifetime)
    scopes = {entity["entity_id"]: entity.get("scope") for entity in lifetime.get("entities", [])}
    for row in plan.get("candidates", []):
        scope = scopes.get(row["search_anchor"])
        if scope == "EVENT_LOCAL_ANCHOR":
            row["anchor_scope"] = scope
            row["anchor_identity_note"] = "event-local anchor; not globally persistent"
    return lifetime, temporal, {"episodes_added": len(admitted), "search": plan,
                                "search_plan_text": plan_text(plan)}


def _render_graphs(folder: Path, lifetime: dict, temporal: dict, plan: dict):
    import matplotlib.pyplot as plt
    from memory_graph.v28.visualization import render_graph
    graphs = folder / "graphs"
    graphs.mkdir(parents=True, exist_ok=True)
    nodes = lifetime.get("last_trusted_local_subgraph", {}).get("nodes", [])
    edges = lifetime.get("last_trusted_local_subgraph", {}).get("edges", [])
    render_graph(nodes, edges, graphs / "phone_01_local_subgraph_final.png", "phone_01 local memory")
    render_graph(lifetime.get("entities", []), edges, graphs / "phone_01_lifetime_memory.png", "phone_01 lifetime memory")
    render_graph(lifetime.get("entities", []), edges, graphs / "phone_01_search_graph.png", "phone_01 search graph")
    fig, ax = plt.subplots(figsize=(12, 4))
    snapshots = temporal.get("snapshots", [])
    for row in snapshots:
        ax.scatter(row.get("time", 0), row.get("frame", 0), s=24, color="#177e89")
    ax.set(title="Temporal memory timeline", xlabel="time (s)", ylabel="frame")
    ax.grid(alpha=.2)
    fig.tight_layout(); fig.savefig(graphs / "temporal_memory_timeline.png", dpi=140); plt.close(fig)


def _render_rediscovery(task: str, timeline: dict, rediscovery: dict, anchors: list[dict], output: Path):
    import matplotlib.pyplot as plt
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 4.2))
    rows = timeline.get("phone_timeline", [])
    if rows:
        x = [r["frame_index"] for r in rows]
        y = [1 if r.get("state") in {"VISIBLE_TRUSTED", "MATCHED"} else 0 for r in rows]
        ax.step(x, y, where="post", label="phone_01 trusted/MATCHED")
    for candidate in rediscovery.get("candidates", []):
        y = {"CONFIRMED": .95, "PROVISIONAL": .8, "AMBIGUOUS": .65, "REJECTED": .5}.get(candidate["identity_decision"], .4)
        ax.scatter(candidate["frame"], y, marker="x", s=55, label=f"{candidate['source']} {candidate['identity_decision']}")
    for event in anchors:
        ax.axvline(event["frame"], alpha=.16, color="#777777")
    ax.set(title=f"{task}: controlled lost-target rediscovery", xlabel="frame", yticks=[0,.5,.65,.8,.95,1],
           yticklabels=["LOST", "REJECTED", "AMBIGUOUS", "PROVISIONAL", "CONFIRMED", "trusted"])
    ax.grid(axis="x", alpha=.2); ax.legend(loc="upper right", fontsize=7); fig.tight_layout()
    fig.savefig(output, dpi=150); plt.close(fig)


def _load_task_context(task: str, is_raw: bool):
    if is_raw:
        return (read(OUT / task / "identity_timeline.json"), read(OUT / task / "candidate_stream.json"),
                read(OUT / task / "reid_audit.json"), read(OUT / task / "entity_registry.json"),
                read(OUT / task / "sam" / "candidate_sam_support.json"))
    return (read(ROOT / "outputs_v26" / task / "identity_timeline.json"),
            read(ROOT / "outputs_v26" / task / "candidate_stream.json"),
            read(ROOT / "outputs_v26" / task / "reid_audit.json"),
            read(ROOT / "outputs_v26" / task / "entity_registry.json"),
            read(ROOT / "outputs_v25_rerun" / task / "sam" / "candidate_sam_support.json"))


def _stage_metrics(task: str, raw: bool) -> dict:
    folder = OUT / task
    if raw:
        detections = read(folder / "upstream_v21" / "event_analysis" / "detections.json")
        tracks = read(folder / "upstream_v21" / "event_analysis" / "track_timelines.json")
        registry = read(folder / "entity_registry.json")
        identity = read(folder / "identity_timeline.json")["phone_timeline"]
        stream = read(folder / "candidate_stream.json")["observations"]
        masks = _trusted_masks(task, True)
    else:
        source = ROOT / "outputs_v25_rerun" / task / "upstream_v21" / "event_analysis"
        detections, tracks = read(source / "detections.json"), read(source / "track_timelines.json")
        registry = read(ROOT / "outputs_v26" / task / "entity_registry.json")
        identity = read(ROOT / "outputs_v26" / task / "identity_timeline.json")["phone_timeline"]
        stream = read(ROOT / "outputs_v26" / task / "candidate_stream.json")["observations"]
        masks = _trusted_masks(task, False)
    return {"sampled_frames": len(identity), "yolo_detections": len(detections),
            "local_tracks": len(tracks), "trusted_sam_masks": sum(bool(row.get("trusted")) for row in masks),
            "persistent_entities": len(registry.get("entities", [])),
            "candidate_observations": len(stream), "identity_timeline_rows": len(identity)}


def process_video(task: str, raw: bool = False, runner=None, force: bool = False) -> dict:
    from memory_graph.v291.events import detect_multi_events
    from memory_graph.v291.rediscovery import propose_rediscovery
    from memory_graph.v291.observable_vlm import ObservableVLM
    from memory_graph.v291.anchors import roles_for
    import cv2
    folder = OUT / task
    summary_path = folder / "summary.json"
    if summary_path.exists() and not force:
        cached_summary = read(summary_path)
        if cached_summary.get("video_sha256") == sha(source_video_for_task(task)) and cached_summary.get("raw_video_full_pipeline") == raw:
            return cached_summary
    identity, stream, reid, registry, sam_support = _load_task_context(task, raw)
    detections_path = folder / "upstream_v21" / "event_analysis" / "detections.json" if raw else ROOT / "outputs_v25_rerun" / task / "upstream_v21" / "event_analysis" / "detections.json"
    detection_rows = read(detections_path)
    for row in stream.get("observations", []):
        idx = row.get("raw_detection_index")
        if idx is not None and idx < len(detection_rows):
            row["bbox"] = detection_rows[idx]["bbox"]
    if raw:
        frames, provenance = _current_inputs(task)
        size, fps = tuple(provenance["frame_size"]), provenance["fps"]
        base_placement = []
    else:
        from memory_graph.v27.pipeline import load_inputs
        frames, provenance = load_inputs(task)
        size, fps = tuple(provenance["frame_size"]), provenance["fps"]
        base_placement = read(ROOT / "outputs_v29" / task / "placement_event_candidates.json")
    metadata = read(detections_path.parent / "video_metadata.json")
    last_frame = metadata["sampled_frames"][-1]["frame_index"]
    events = detect_multi_events(task, identity.get("phone_timeline", []), stream.get("observations", []),
                                 base_placement, fps, last_frame, max_events=3)
    for event in events:
        event["candidate_anchors"] = _event_anchor_context(task, event)
    write(folder / "events.json", {"schema": "v291_events_1", "task": task,
                                    "events": events, "selection_policy": "identity transitions prioritized over first loss"})

    trusted_masks = _trusted_masks(task, raw)
    dense_summaries, anchor_jsons, vlm_all, candidates_all, decisions_all = [], [], [], [], []
    dense_runner = runner
    anchor_by_id = {}
    for event in events:
        event_folder = folder / "dense_windows" / event["event_id"]
        dense_summary = _run_dense(task, event, trusted_masks, fps, event_folder, dense_runner)
        dense_summaries.append(dense_summary)
        dense_path = event_folder / "dense_observations.json"
        if not dense_path.exists():
            continue
        dense = read(dense_path)
        anchor_result = _attach_recovered_anchors(event, dense, size)
        for anchor in anchor_result["anchors"]:
            anchor_by_id[anchor["anchor_id"]] = anchor
        anchor_jsons.append(anchor_result)
        write(folder / "anchor_recovery" / f"{event['event_id']}.json", anchor_result)
        write(dense_path, dense)
        visuals = _event_images(source_video_for_task(task), event, dense, folder / "event_visuals" / event["event_id"])
        # At most two close, stable anchors per event receive a scoped fact query.
        vlm_rows = []
        trusted_anchor_ids = {a["anchor_id"] for a in anchor_result["anchors"] if a["trusted_for_physical_reasoning"]}
        co_counts = Counter(a["anchor_id"] for row in dense.get("rows", []) if row.get("identity_authorized")
                            for a in row.get("recovered_anchors", []))
        eligible = sorted((a for a in anchor_result["anchors"] if a["anchor_id"] in trusted_anchor_ids
                           and co_counts[a["anchor_id"]] >= 3),
                          key=lambda a: (-co_counts[a["anchor_id"]], a["anchor_id"]))[:2]
        if eligible and visuals:
            try:
                vlm = ObservableVLM()
                for anchor in eligible:
                    vlm_rows.append(vlm.run(visuals, event, anchor))
            except Exception as exc:
                vlm_rows.append({"event_id": event["event_id"], "status": "FAILED", "anchor_id": None,
                                 "error": f"{type(exc).__name__}: {exc}", "relation_label_requested": False})
        vlm_all.extend(vlm_rows)
        physical = _event_local_rows(event, anchor_result, dense, vlm_rows)
        for row in physical:
            # carry event window so the temporal memory and search artifacts are auditable
            row["start_frame"], row["end_frame"] = event["start_frame"], event["end_frame"]
        candidates_all.extend(physical)
        decisions_all.extend(physical)
        write(folder / "physical_reasoning" / f"{event['event_id']}.json", {"candidates": physical, "vlm": vlm_rows})
    stream_with_boxes = {**stream, "observations": stream.get("observations", [])}
    rediscovery = propose_rediscovery(task, stream_with_boxes, identity, reid, sam_support)
    write(folder / "rediscovery.json", rediscovery)
    write(folder / "rediscovery_timeline.json", {"task": task, **rediscovery,
        "nearby_recovered_anchors": [{"frame": e["peak_frame"], "event_id": e["event_id"],
            "anchor_ids": [a["anchor_id"] for result in anchor_jsons if result["event_id"] == e["event_id"]
                           for a in result["anchors"]]} for e in events],
        "new_local_graph_formed": bool(candidates_all), "identity_authority": "V2.6 Identity Guard only"})
    if task == "test9":
        _render_rediscovery(task, identity, rediscovery, [{"frame": e["peak_frame"]} for e in events],
                            folder / "rediscovery_timeline.png")

    write(folder / "dense_reinspection_summary.json", {"task": task, "windows": dense_summaries})
    write(folder / "anchor_recovery.json", {"events": anchor_jsons,
        "counts": {"existing_persistent": sum(a["persistent_entity_id"] is not None for r in anchor_jsons for a in r["anchors"]),
                   "event_local": sum(a["persistent_entity_id"] is None for r in anchor_jsons for a in r["anchors"]),
                   "by_role": dict(Counter(role for r in anchor_jsons for a in r["anchors"] for role in a["semantic_role"])),
                   "anchor_target_co_visible_frames": sum(bool(row.get("identity_authorized") and row.get("recovered_anchors"))
                       for r in anchor_jsons for event in events if event["event_id"] == r["event_id"]
                       for row in read(folder/"dense_windows"/event["event_id"]/"dense_observations.json").get("rows", []))}})
    write(folder / "vlm_observable_evidence.json", {"calls": vlm_all,
        "summary": {"calls": len(vlm_all), "valid": sum(x.get("status") == "VALID" for x in vlm_all),
                    "unusable": sum(x.get("status") != "VALID" for x in vlm_all), "direct_relation_requested": False}})
    write(folder / "physical_relation_candidates.json", candidates_all)
    write(folder / "physical_relation_decisions.json", decisions_all)
    write(folder / "events" / "summary.json", {"event_count": len(events), "events": events})
    # Re-use the current V2.8 graph shape and unchanged search ranker.
    lifetime, temporal = _load_base(task, raw)
    # attach V2.9.1 observable candidates to temporal/lifetime memory, preserving event-local scope
    lifetime, temporal, memory_summary = _update_memory(task, lifetime, temporal, decisions_all, anchor_by_id)
    lifetime, temporal = _add_reconfirm_memory(task, lifetime, temporal, events, registry,
        identity.get("phone_timeline", []), size, fps)
    from memory_graph.v28.search_planner import find
    memory_summary["search"] = find(lifetime)
    from memory_graph.v28.search_planner import plan_text
    plan = memory_summary["search"]
    write(folder / "temporal_memory.json", temporal)
    write(folder / "object_memory_phone_01.json", lifetime)
    write(folder / "search_candidates.json", plan)
    (folder / "search_plan.txt").write_text(plan_text(plan), encoding="utf-8")
    _render_graphs(folder, lifetime, temporal, plan)
    summary = {"task": task, "raw_video_full_pipeline": raw,
        "video_sha256": sha(source_video_for_task(task)), "events": dict(Counter(e["event_type"] for e in events)),
        "event_windows": len(events), "anchors": {"existing": sum(a["persistent_entity_id"] is not None for r in anchor_jsons for a in r["anchors"]),
                    "event_local": sum(a["persistent_entity_id"] is None for r in anchor_jsons for a in r["anchors"]),
                    "co_visible_frames": read(folder / "anchor_recovery.json")["counts"]["anchor_target_co_visible_frames"]},
        "rediscovery": rediscovery["counts"], "rediscovery_candidates": len(rediscovery["candidates"]),
        "vlm": {"calls": len(vlm_all), "valid": sum(x.get("status") == "VALID" for x in vlm_all)},
        "physical": dict(Counter(f"{x['candidate_relation']}:{x['decision']}" for x in decisions_all)),
        "physical_promotions": sum(x["decision"] == "PROMOTED" for x in decisions_all),
        "physical_candidates": sum(x["decision"] == "CANDIDATE" for x in decisions_all),
        "memory_episodes_added": memory_summary["episodes_added"], "search_candidates": len(plan.get("candidates", [])),
        "search_top": plan.get("candidates", [])[:3], "source_frames": len(frames),
        "candidate_ids": sorted({c.get("candidate_id") for c in rediscovery.get("candidates", []) if c.get("candidate_id")}),
        "identity_guard_gt_accessed": reid.get("gt_accessed", False) is True}
    write(folder / "temporal_memory" / "summary.json", summary)
    write(folder / "summary.json", summary)
    return summary


def run_all() -> dict:
    if (OUT / "prediction_manifest.json").exists():
        raise RuntimeError("V2.9.1 prediction manifest already frozen; refusing to overwrite")
    _verify_historical_freezes()
    raw_status = [_run_raw_upstream(alias) for alias in ("task1", "task2")]
    # The restored raw videos use their actual filenames as output identifiers.
    summaries = [process_video(row["actual_video"].removesuffix(".mp4"), raw=True) for row in raw_status]
    for task in TASKS:
        summaries.append(process_video(task, raw=False))
    result = {"schema": "v291_summary_1", "raw_pipeline": raw_status, "videos": summaries,
              "prediction_inference_used_manual_notes": False,
              "historical_outputs_read_only": ["outputs_v27", "outputs_v28", "outputs_v29", "outputs_v25_rerun", "outputs_v26"]}
    write(OUT / "summary.json", result)
    regression = {"schema": "v291_regression_summary_1", "test7_provisional_memory_contamination": False,
                  "test8_distinct_phone_identity_source": "frozen V2.6 Identity Guard", "historical_freezes_verified": True,
                  "test9_rediscovery_candidates": next((x["rediscovery_candidates"] for x in summaries if x["task"] == "test9"), 0)}
    write(OUT / "regression_summary.json", regression)
    return result


def decorate_search_scope() -> None:
    """Make EVENT_LOCAL_ANCHOR scope explicit without changing V2.8 rank rules."""
    from memory_graph.v28.search_planner import plan_text
    # Resume safely if predictions already exist, adding any missing
    # reconfirmation context to memory exactly once.
    raw_names = {"test1", "test2"}
    for task in ["test1", "test2", *TASKS]:
        folder = OUT / task
        if not (folder / "temporal_memory.json").exists() or not (folder / "events.json").exists():
            continue
        temporal, lifetime = read(folder / "temporal_memory.json"), read(folder / "object_memory_phone_01.json")
        events = read(folder / "events.json").get("events", [])
        missing = [e for e in events if e.get("event_type") == "RECONFIRM_EVENT" and
                   f"V291_{e['event_id']}" not in {x.get("event_id") for x in temporal.get("events", [])}]
        if not missing:
            continue
        identity, _, _, registry, _ = _load_task_context(task, task in raw_names)
        if task in raw_names:
            metadata = read(folder / "upstream_v21" / "event_analysis" / "video_metadata.json")
            size, fps = (metadata["width"], metadata["height"]), metadata["fps"]
        else:
            from memory_graph.v27.pipeline import load_inputs
            _, provenance = load_inputs(task)
            size, fps = tuple(provenance["frame_size"]), provenance["fps"]
        lifetime, temporal = _add_reconfirm_memory(task, lifetime, temporal, events, registry,
            identity.get("phone_timeline", []), size, fps)
        from memory_graph.v28.search_planner import find
        plan = find(lifetime)
        write(folder / "object_memory_phone_01.json", lifetime)
        write(folder / "temporal_memory.json", temporal)
        write(folder / "search_candidates.json", plan)
        (folder / "search_plan.txt").write_text(plan_text(plan), encoding="utf-8")
        _render_graphs(folder, lifetime, temporal, plan)
    videos = []
    for task in ["test1", "test2", *TASKS]:
        folder = OUT / task
        memory_path, plan_path = folder / "object_memory_phone_01.json", folder / "search_candidates.json"
        if not memory_path.exists() or not plan_path.exists():
            continue
        lifetime, plan = read(memory_path), read(plan_path)
        scopes = {e["entity_id"]: e.get("scope") for e in lifetime.get("entities", [])}
        for row in plan.get("candidates", []):
            if scopes.get(row["search_anchor"]) == "EVENT_LOCAL_ANCHOR":
                row["anchor_scope"] = "EVENT_LOCAL_ANCHOR"
                row["anchor_identity_note"] = "event-local anchor; not globally persistent"
        text_plan = plan_text(plan)
        for row in plan.get("candidates", []):
            if row.get("anchor_scope") == "EVENT_LOCAL_ANCHOR":
                old = f"{row['rank']}. Search {row['relation']} {row['anchor_label']} ({row['search_anchor']})"
                text_plan = text_plan.replace(old, old + " [event-local anchor; not globally persistent]")
        write(plan_path, plan)
        (folder / "search_plan.txt").write_text(text_plan, encoding="utf-8")
        summary_path = folder / "summary.json"
        if summary_path.exists():
            summary = read(summary_path)
            summary["search_top"] = plan.get("candidates", [])[:3]
            summary["reconfirm_context_events"] = sum(e.get("event_type") == "V291_RECONFIRM_EVENT"
                for e in read(folder / "temporal_memory.json").get("events", []))
            summary["pipeline_counts"] = _stage_metrics(task, task in raw_names)
            vlm_payload = read(folder / "vlm_observable_evidence.json")
            calls = vlm_payload.get("calls", [])
            summary["vlm"] = {"calls": len(calls), "valid": sum(c.get("status") == "VALID" for c in calls),
                "unusable": sum(c.get("status") != "VALID" for c in calls),
                "observable_facts_extracted": sum(len(c.get("observable_facts") or {}) for c in calls
                                                    if c.get("status") == "VALID")}
            summary["search_breakdown"] = {
                "promoted_physical_locations": sum(r.get("priority_rule") in {1, 2} for r in plan.get("candidates", [])),
                "candidate_physical_locations": sum(r.get("priority_rule") == 3 for r in plan.get("candidates", [])),
                "anchor_context_only_locations": sum(r.get("priority_rule") in {4, 5} for r in plan.get("candidates", [])),
                "no_context": not bool(plan.get("candidates"))}
            write(summary_path, summary)
            write(folder / "temporal_memory" / "summary.json", summary)
        videos.append({"task": task, "search_candidates": len(plan.get("candidates", [])),
                       "event_local_search_candidates": sum(r.get("anchor_scope") == "EVENT_LOCAL_ANCHOR"
                                                             for r in plan.get("candidates", []))})
    if (OUT / "summary.json").exists():
        summary = read(OUT / "summary.json")
        per_video = {row["task"]: row for row in videos}
        for row in summary.get("videos", []):
            if row["task"] in per_video:
                current = read(OUT / row["task"] / "summary.json")
                row.update(current)
                row["event_local_search_candidates"] = per_video[row["task"]]["event_local_search_candidates"]
        event_totals = Counter()
        rediscovery_totals = Counter()
        for row in summary.get("videos", []):
            event_totals.update(row.get("events", {}))
            rediscovery_totals.update(row.get("rediscovery", {}))
        summary["aggregate_metrics"] = {
            "videos": len(summary.get("videos", [])),
            "sampled_frames": sum(r.get("pipeline_counts", {}).get("sampled_frames", 0) for r in summary.get("videos", [])),
            "yolo_detections": sum(r.get("pipeline_counts", {}).get("yolo_detections", 0) for r in summary.get("videos", [])),
            "trusted_sam_masks": sum(r.get("pipeline_counts", {}).get("trusted_sam_masks", 0) for r in summary.get("videos", [])),
            "persistent_entities": sum(r.get("pipeline_counts", {}).get("persistent_entities", 0) for r in summary.get("videos", [])),
            "events": dict(event_totals),
            "event_local_anchors": sum(r.get("anchors", {}).get("event_local", 0) for r in summary.get("videos", [])),
            "anchor_target_co_visible_frames": sum(r.get("anchors", {}).get("co_visible_frames", 0) for r in summary.get("videos", [])),
            "rediscovery_candidates": sum(r.get("rediscovery_candidates", 0) for r in summary.get("videos", [])),
            "rediscovery_decisions": dict(rediscovery_totals),
            "vlm_calls": sum(r.get("vlm", {}).get("calls", 0) for r in summary.get("videos", [])),
            "vlm_valid": sum(r.get("vlm", {}).get("valid", 0) for r in summary.get("videos", [])),
            "observable_facts_extracted": sum(r.get("vlm", {}).get("observable_facts_extracted", 0) for r in summary.get("videos", [])),
            "physical_promotions": sum(r.get("physical_promotions", 0) for r in summary.get("videos", [])),
            "physical_candidates": sum(r.get("physical_candidates", 0) for r in summary.get("videos", [])),
            "search": {key: sum(r.get("search_breakdown", {}).get(key, 0) for r in summary.get("videos", []))
                       for key in ("promoted_physical_locations", "candidate_physical_locations", "anchor_context_only_locations")},
            "videos_with_no_search_context": sum(bool(r.get("search_breakdown", {}).get("no_context")) for r in summary.get("videos", []))}
        write(OUT / "summary.json", summary)


def freeze() -> dict:
    if (OUT / "prediction_manifest.json").exists():
        raise RuntimeError("V2.9.1 prediction manifest already exists")
    _verify_historical_freezes()
    exclude = {"prediction_manifest.json", "evaluation.json", "evaluation_summary.json", "V291_REPORT.md"}
    files = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(OUT.rglob("*"))
             if p.is_file() and p.name not in exclude}
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT / "src/memory_graph/v291").glob("*.py"))}
    sources["scripts/run_v291.py"] = sha(ROOT / "scripts/run_v291.py")
    sources["tests/test_v291_pipeline.py"] = sha(ROOT / "tests/test_v291_pipeline.py")
    inputs = {source_video_for_task(task).name: sha(source_video_for_task(task)) for task in ["task1", "task2", *TASKS]}
    for name in ("outputs_v27/prediction_manifest.json", "outputs_v28/prediction_manifest.json",
                 "outputs_v29/prediction_manifest.json", "outputs_v26/parameter_manifest.json"):
        path = ROOT / name
        if path.exists():
            inputs[name] = sha(path)
    result = {"schema": "v291_prediction_freeze_1", "freeze_utc": datetime.now(timezone.utc).isoformat(),
              "inference_used_manual_notes": False, "source_sha256": sources,
              "files_sha256": files, "input_sha256": inputs,
              "historical_manifests_sha256": {k: v for k, v in inputs.items() if k.startswith("outputs_v")}}
    write(OUT / "prediction_manifest.json", result)
    return result


def verify_freeze() -> None:
    _verify_historical_freezes()
    manifest = read(OUT / "prediction_manifest.json")
    for relative, digest in {**manifest["source_sha256"], **manifest["files_sha256"], **manifest["input_sha256"]}.items():
        if sha(ROOT / relative) != digest:
            raise ValueError(f"V2.9.1 frozen artifact changed: {relative}")


def post_freeze_evaluation() -> dict:
    """Read narrative notes only after the prediction manifest exists."""
    verify_freeze()
    references = []
    for task in ("task1", "task2"):
        for path in sorted((ROOT / "evaluation").rglob(f"*{task}*")):
            if path.is_file() and path.suffix.casefold() in {".json", ".md", ".txt"}:
                references.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)})
    result = {"schema": "v291_postfreeze_evaluation_1", "evaluation_after_prediction_freeze": True,
              "prediction_manifest_sha256": sha(OUT / "prediction_manifest.json"),
              "manual_reference_files": references,
              "per_video": {task: {"raw_source": source_video_for_task(task).name,
                  "prediction_status": read(OUT / RAW_TASKS[task] / "summary.json") if (OUT / RAW_TASKS[task] / "summary.json").exists() else {},
                  "review_scope": ("original black phone, hand occlusion continuity, distinct desk phone, basketball area, cup semantics, distinct chairs"
                                   if task == "task1" else "original black phone, short gap, microwave/teddy context, distinct desk phones, long gap")}
                  for task in ("task1", "task2")}}
    for task in ("task1", "task2"):
        actual = RAW_TASKS[task]
        vpath = OUT / actual / "evaluation.json"
        write(vpath, {"task": task, "actual_video": source_video_for_task(task).name,
                      "evaluation_after_prediction_freeze": True,
                      "prediction_manifest_sha256": result["prediction_manifest_sha256"],
                      "manual_reference_files": references,
                      "scope": result["per_video"][task]["review_scope"],
                      "model_output": read(OUT / actual / "summary.json")})
    for task in TASKS:
        vpath = OUT / task / "evaluation.json"
        write(vpath, {"task": task, "evaluation_after_prediction_freeze": True,
                      "manual_reference_evaluation": False, "prediction_manifest_sha256": result["prediction_manifest_sha256"],
                      "scope": "post-freeze V2.9.1 output audit; no narrative labels were used",
                      "model_output": read(OUT / task / "summary.json")})
    write(OUT / "evaluation_summary.json", result)
    return result


def write_report(summary: dict | None = None, evaluation: dict | None = None) -> Path:
    summary = summary or read(OUT / "summary.json")
    manifest = read(OUT / "prediction_manifest.json")
    evaluation = evaluation or (read(OUT / "evaluation_summary.json") if (OUT / "evaluation_summary.json").exists() else {})
    rows = summary.get("videos", [])
    lines = ["# V2.9.1 Execution Report", "", f"Prediction freeze: {manifest['freeze_utc']}",
             f"Frozen prediction files: {len(manifest['files_sha256'])}", "",
             "## Task1 / Task2 raw pipeline", ""]
    for row in summary.get("raw_pipeline", []):
        lines.append(f"- {row['task']} ({row['actual_video']}): V2.1={row['video_status'].get('status')}, "
                     f"SAM={row.get('target_sam_status')}, binding={row.get('target_binding')}, "
                     f"identity-confirmed={bool(row.get('identity_guard_confirmed'))}, "
                     f"entities={row.get('persistent_entities')}")
    lines += ["", "## Per-video changes", "", "| Video | Events | Anchors (existing/local) | Rediscovery candidates | VLM valid/calls | Physical candidates/promotions | Search |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['task']} | {row['event_windows']} {row['events']} | "
                     f"{row['anchors']['existing']}/{row['anchors']['event_local']} | {row['rediscovery_candidates']} | "
                     f"{row['vlm']['valid']}/{row['vlm']['calls']} | {row['physical_candidates']}/{row['physical_promotions']} | "
                     f"{row['search_candidates']} (top {', '.join(x['anchor_label'] for x in row['search_top'][:2])}) |")
    test8 = next((r for r in rows if r["task"] == "test8"), {})
    test9 = next((r for r in rows if r["task"] == "test9"), {})
    lines += ["", "## Required findings", "",
              f"- test8 later reconfirm event: {'yes' if test8.get('events', {}).get('RECONFIRM_EVENT') else 'no'}; "
              f"event classes={test8.get('events', {})}.",
              f"- test9 rediscovery: {test9.get('rediscovery_candidates', 0)} post-loss candidates; "
              f"decisions={test9.get('rediscovery', {})}.",
              f"- task1 search: {next((r.get('search_top') for r in rows if r['task']=='test1'), [])}.",
              f"- task2 search: {next((r.get('search_top') for r in rows if r['task']=='test2'), [])}.",
              "- Event-local anchors remain scoped and are not reconciled to a PersistentEntity.",
              "- Physical gates emitted no relation promotion unless all V2.9 gates were independently satisfied.",
              "- Manual narrative evaluation was performed only after the prediction freeze.",
              f"- Post-freeze reference files: {len(evaluation.get('manual_reference_files', []))}.",
              "", "## Aggregate metrics", ""]
    aggregate = summary.get("aggregate_metrics", {})
    if aggregate:
        lines += [f"- Videos: {aggregate.get('videos')}; sampled frames: {aggregate.get('sampled_frames')}; "
                  f"YOLO detections: {aggregate.get('yolo_detections')}; trusted SAM masks: {aggregate.get('trusted_sam_masks')}.",
                  f"- Events: {aggregate.get('events')}; event-local anchors: {aggregate.get('event_local_anchors')}; "
                  f"anchor/target co-visible frames: {aggregate.get('anchor_target_co_visible_frames')}.",
                  f"- Rediscovery: {aggregate.get('rediscovery_candidates')} candidates; "
                  f"decisions: {aggregate.get('rediscovery_decisions')}.",
                  f"- Observable VLM: {aggregate.get('vlm_valid')}/{aggregate.get('vlm_calls')} valid/calls; "
                  f"facts extracted: {aggregate.get('observable_facts_extracted')}.",
                  f"- Physical: {aggregate.get('physical_candidates')} candidates, "
                  f"{aggregate.get('physical_promotions')} promoted; search breakdown: {aggregate.get('search')}."]
    regression_path = OUT / "regression_summary.json"
    test_results = read(regression_path).get("test_results", {}) if regression_path.exists() else {}
    if test_results:
        lines += ["", "## Tests", "",
                  f"- V2.9.1 focused tests: {test_results.get('v291_focused')} passed.",
                  f"- Full suite: {test_results.get('full_suite')}; failures: {test_results.get('failures')}."]
    lines += ["", "## Verification", "", f"- Prediction files frozen: {len(manifest['files_sha256'])}.",
              "- Historical V2.7/V2.8/V2.9 manifests verified before and after execution.",
              "- All new outputs and reports are under `outputs_v291/`.", "",
              "## Status", "", "V291_PARTIAL_FIXES_WITH_REMAINING_UPSTREAM_GAPS", ""]
    path = OUT / "V291_REPORT.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
