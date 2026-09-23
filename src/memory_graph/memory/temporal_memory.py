from collections import defaultdict
from ..scene_graph.models import TemporalMemory
from .transition_builder import build_transitions


def fuse_relations(scenes, admitted_ids, max_gap):
    groups = defaultdict(list)
    for scene in scenes:
        for relation in scene.relations:
            if relation.subject_track_id not in admitted_ids or (relation.object_track_id is not None and relation.object_track_id not in admitted_ids):
                continue
            key = (relation.subject_track_id, relation.predicate, relation.object_track_id,
                   relation.evidence.vlm, relation.reference_frame, relation.temporal_phase)
            groups[key].append(relation)
    fused = []
    for values in groups.values():
        current = None
        for relation in sorted(values, key=lambda r: (r.start_time, r.end_time)):
            if current is not None and relation.start_time-current.end_time <= max_gap:
                current.end_time = max(current.end_time, relation.end_time)
                current.start_time = min(current.start_time, relation.start_time)
                current.observed_times = sorted(set(current.observed_times+relation.observed_times))
                current.event_ids = sorted(set(current.event_ids+relation.event_ids))
                current.confidence = min(current.confidence, relation.confidence)
                current.evidence.details.setdefault("contributing_evidence", []).append(relation.evidence.model_dump())
            else:
                if current is not None:
                    fused.append(current)
                current = relation.model_copy(deep=True)
        if current is not None:
            fused.append(current)
    return sorted(fused, key=lambda r: (r.start_time, r.subject_track_id, r.predicate))


def build_memory(video, metadata, entities, scenes, events, config):
    relations = fuse_relations(scenes, {e.track_id for e in entities}, config.temporal_merge_gap_seconds)
    attributes = []
    # Preserve attribute changes as event-specific evidence even if no single aggregate value is safe.
    for entity in entities:
        for evidence in entity.evidence:
            for name, value in evidence.get("attributes", {}).items():
                event = next((e for e in events if e["event_id"] == evidence["event_id"]), None)
                if event:
                    attributes.append({"track_id": entity.track_id, "entity_id": entity.entity_id, "name": name, "value": value,
                        "confidence": evidence["confidence"], "event_ids": [event["event_id"]],
                        "start_time": event["start_time"], "end_time": event["end_time"], "source": "vlm",
                        "interval_meaning": "attribute interpreted from event keyframes"})
    return TemporalMemory(video=video, metadata=metadata, entities=entities, attributes=attributes,
        relations=relations, events=events, transitions=build_transitions(relations, config.transition_max_gap_seconds))
