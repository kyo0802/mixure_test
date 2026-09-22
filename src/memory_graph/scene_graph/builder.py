from collections import defaultdict
from ..vlm.schemas import VLMRelation
from .models import SemanticEntity, GroundedRelation, Evidence, SceneGraph
from .validator import validate_relation


def observation_index(timelines):
    frames = defaultdict(dict)
    for track in timelines:
        for obs in track.observations:
            frames[obs.frame_index][track.track_id] = obs
    return frames


def build_scene(event, frames, timelines, metadata, config, result=None, status="skipped_disabled"):
    lookup = {t.track_id: t for t in timelines}
    supplied = set(frames[0].supplied_track_ids) if frames else set()
    semantic = {e.track_id: e for e in result.entities} if result else {}
    entities = []
    for tid in sorted(supplied):
        track, evidence = lookup[tid], semantic.get(tid)
        confirmed = evidence is not None and evidence.confidence >= config.vlm.confidence_threshold and evidence.semantic_class != "unknown"
        entities.append(SemanticEntity(track_id=tid, entity_id=f"track_{tid:04d}", detector_class=track.detector_class,
            semantic_class=evidence.semantic_class if confirmed else "unknown",
            semantic_confidence=evidence.confidence if confirmed else 0, attributes=evidence.attributes if confirmed else {},
            first_seen=track.first_seen, last_seen=track.last_seen, is_anchor=track.is_anchor, anchor_score=track.anchor_score,
            admission_status="semantic_confirmed" if confirmed else "unknown",
            evidence=[{"event_id": event.event_id, **evidence.model_dump()}] if evidence else []))
    scene = SceneGraph(event_id=event.event_id, analysis_status=status, entities=entities)
    observations = observation_index(timelines)
    entity_map = {e.track_id: e for e in entities}
    if result:
        for relation in result.relations:
            grounded, reason = validate_relation(relation, frames, observations, metadata.width, metadata.height, config.graph, entity_map)
            if reason:
                scene.rejected_relations.append({"relation": relation.model_dump(), "reason": reason})
                continue
            times = grounded["times"]
            scene.relations.append(GroundedRelation(subject_track_id=relation.subject_track_id, predicate=relation.predicate,
                object_track_id=relation.object_track_id, confidence=grounded["confidence"], temporal_phase=relation.temporal_phase,
                start_time=min(times), end_time=max(times), observed_times=times, event_ids=[event.event_id],
                evidence=Evidence(vlm=True, geometry=grounded["geometry"], details=grounded["details"])))
    # Independent sparse geometry evidence, explicitly NOT a semantic VLM substitute.
    geometric = defaultdict(list)
    existing = {(r.subject_track_id, r.predicate, r.object_track_id) for r in scene.relations}
    for frame in frames:
        visible = observations.get(frame.frame_index, {})
        for tid in supplied & set(visible):
            a = visible[tid]
            neighbors = [n for n in a.nearest_tracks if n["track_id"] in supplied and n["track_id"] in visible
                         and n["bbox_distance"] <= config.graph.near_threshold]
            for neighbor in neighbors[:config.graph.max_geometric_neighbors]:
                b = visible[neighbor["track_id"]]
                names = ["NEAR"]
                if neighbor["overlap_fraction"] >= .05:
                    names.append("OVERLAPPING")
                if abs(neighbor["dx"]) > config.graph.direction_margin:
                    names.append("LEFT_OF" if neighbor["dx"] < 0 else "RIGHT_OF")
                if abs(neighbor["dy"]) > config.graph.direction_margin:
                    names.append("ABOVE" if neighbor["dy"] < 0 else "BELOW")
                for name in names:
                    key = (tid, name, b.track_id)
                    confidence = min(a.confidence, b.confidence)
                    if key not in existing and confidence >= config.graph.min_relation_confidence:
                        geometric[key].append((frame.timestamp, confidence))
    for (subject, predicate, obj), values in geometric.items():
        times = sorted(set(t for t, _ in values))
        if len(times) < 2 or times[-1]-times[0] < config.events.signal_persistence_seconds:
            continue
        scene.relations.append(GroundedRelation(subject_track_id=subject, predicate=predicate, object_track_id=obj,
            confidence=sum(c for _, c in values)/len(values), temporal_phase="persistent", start_time=times[0],
            end_time=times[-1], observed_times=times, event_ids=[event.event_id],
            evidence=Evidence(vlm=False, geometry="supports", details={"support_frames": len(times), "physical_verification": False})))
    if result is None:
        scene.notes.append("No VLM analysis: entity semantics are unknown; edges are separately identified 2D geometry only")
    return scene
