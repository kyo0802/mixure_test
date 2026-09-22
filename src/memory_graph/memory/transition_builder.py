from collections import defaultdict
from ..vlm.schemas import INTERACTIONS


def build_transitions(relations, max_gap):
    groups = defaultdict(list)
    for relation in relations:
        # Only semantic evidence can generate semantic state transitions; geometry alone stays geometry.
        if relation.evidence.vlm and relation.predicate != "UNKNOWN":
            groups[relation.subject_track_id].append(relation)
    events = []
    for subject, values in groups.items():
        previous = None
        for current in sorted(values, key=lambda r: (r.start_time, r.end_time)):
            if any(other is not current and (other.predicate, other.object_track_id) != (current.predicate, current.object_track_id)
                   and other.start_time <= current.end_time and current.start_time <= other.end_time for other in values):
                previous = None
                continue
            if previous and 0 <= current.start_time-previous.end_time <= max_gap and (
                current.predicate, current.object_track_id) != (previous.predicate, previous.object_track_id):
                events.append({"type": "observed_relation_transition", "subject_track_id": subject,
                    "from_predicate": previous.predicate, "from_object_track_id": previous.object_track_id,
                    "to_predicate": current.predicate, "to_object_track_id": current.object_track_id,
                    "previous_end_time": previous.end_time, "transition_time": current.start_time,
                    "event_ids": sorted(set(previous.event_ids+current.event_ids)),
                    "confidence": min(previous.confidence, current.confidence), "causal_claim": False})
            previous = current
    return events
