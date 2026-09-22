from collections import defaultdict
from ..config import Config, RelationsConfig
from ..models import AnchorInfo, ObjectObservation, ObjectTrack, RelationObservation
from ..perception.object_classifier import is_subject
from .geometry import pair_signals


def extract_pair(subject: ObjectObservation, anchor: ObjectObservation, width: int, height: int,
                 config: RelationsConfig) -> list[RelationObservation]:
    if subject.frame_index != anchor.frame_index or subject.episode_id != anchor.episode_id:
        raise ValueError("Relations require co-visible observations in the same episode")
    signals = pair_signals(subject.bbox, anchor.bbox, width, height)
    distance = signals["bbox_distance"]
    if distance > config.near_threshold:
        return []
    candidates = [("NEAR", .5+.5*(1-distance/config.near_threshold))]
    for axis, negative, positive in [("dx", "LEFT_OF", "RIGHT_OF"), ("dy", "ABOVE", "BELOW")]:
        delta = signals[axis]
        if abs(delta) > config.direction_margin:
            candidates.append((negative if delta < 0 else positive,
                               min(1, abs(delta)/(2*config.direction_margin))))
    if signals["overlap_fraction"] >= config.overlap_threshold:
        candidates.append(("OVERLAPS", .5+.5*signals["subject_containment"]))
    if signals["subject_containment"] >= config.containment_threshold:
        candidates.append(("INSIDE", signals["subject_containment"]))
    if signals["horizontal_overlap"] > 0 and signals["dy"] < 0 and abs(signals["top_gap"]) <= config.on_above_max_gap:
        candidates.append(("ON_OR_ABOVE", .5+.5*signals["horizontal_overlap"]*(1-abs(signals["top_gap"])/config.on_above_max_gap)))
    relations = []
    evidence_confidence = min(subject.confidence, anchor.confidence)
    for predicate, geometry_confidence in candidates:
        confidence = evidence_confidence*geometry_confidence
        if confidence >= config.min_confidence:
            relations.append(RelationObservation(subject_id=subject.object_id, predicate=predicate,
                object_id=anchor.object_id, reference_frame="camera" if predicate in
                {"LEFT_OF", "RIGHT_OF", "ABOVE", "BELOW"} else "camera_relative", confidence=confidence,
                frame_index=subject.frame_index, timestamp=subject.timestamp, episode_id=subject.episode_id,
                signals=signals))
    return relations


def extract_relations(tracks: list[ObjectTrack], anchors: list[AnchorInfo], width: int, height: int,
                      config: Config) -> list[RelationObservation]:
    anchor_ids = {a.object_id for a in anchors if a.is_anchor}
    frames = defaultdict(list)
    for track in tracks:
        for observation in track.observations:
            frames[observation.frame_index].append(observation)
    result = []
    for _, observations in sorted(frames.items()):
        references = [o for o in observations if o.object_id in anchor_ids]
        for subject in observations:
            if subject.object_id in anchor_ids or not is_subject(subject.class_name, config.anchors.classes, config.objects):
                continue
            nearby = sorted(references, key=lambda a: pair_signals(subject.bbox, a.bbox, width, height)["bbox_distance"])
            for anchor in nearby[:config.relations.max_anchors_per_object]:
                result.extend(extract_pair(subject, anchor, width, height, config.relations))
    return result
