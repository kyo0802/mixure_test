from collections import defaultdict
from statistics import mean
from ..config import TemporalConfig
from ..models import RelationObservation, StableRelation


def stabilize(observations: list[RelationObservation], config: TemporalConfig) -> list[StableRelation]:
    groups = defaultdict(dict)
    for obs in observations:
        if obs.confidence < config.confidence_threshold:
            continue
        key = (obs.subject_id, obs.predicate, obs.object_id, obs.episode_id, obs.reference_frame)
        previous = groups[key].get(obs.frame_index)
        if previous is None or obs.confidence > previous.confidence:
            groups[key][obs.frame_index] = obs
    stable = []

    def emit(segment):
        if len(segment) < config.min_support or segment[-1].timestamp-segment[0].timestamp+1e-9 < config.min_duration_seconds:
            return
        first, last = segment[0], segment[-1]
        stable.append(StableRelation(subject_id=first.subject_id, object_id=first.object_id,
            predicate=first.predicate, reference_frame=first.reference_frame, episode_id=first.episode_id,
            start_time=first.timestamp, end_time=last.timestamp, start_frame=first.frame_index,
            end_frame=last.frame_index, support_count=len(segment), confidence=mean(o.confidence for o in segment),
            max_observed_gap=max((b.timestamp-a.timestamp for a, b in zip(segment, segment[1:])), default=0)))

    for values in groups.values():
        segment = []
        for obs in sorted(values.values(), key=lambda o: (o.timestamp, o.frame_index)):
            if segment and obs.timestamp-segment[-1].timestamp > config.max_gap_seconds+1e-9:
                emit(segment)
                segment = []
            segment.append(obs)
        if segment:
            emit(segment)
    return sorted(stable, key=lambda r: (r.start_time, r.subject_id, r.object_id, r.predicate))
