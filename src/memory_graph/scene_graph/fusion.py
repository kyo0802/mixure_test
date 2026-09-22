"""Aggregate semantic evidence per fixed track; never merge by semantic class."""
from collections import defaultdict, Counter
from statistics import mean
from ..perception.object_classifier import id_prefix
from .models import SemanticEntity


def aggregate_entities(timelines, events, results, config):
    evidence = defaultdict(list)
    for result in results:
        for entity in result.entities:
            evidence[entity.track_id].append({"event_id": result.event_id, **entity.model_dump()})
    involved = {tid for event in events for tid in event.involved_track_ids}
    admitted, rejected, aggregation = [], [], []
    names = Counter()
    for track in timelines:
        reasons = []
        if len(track.observations) < config.admission.min_observations:
            reasons.append("insufficient observation count")
        if track.last_seen-track.first_seen < config.admission.min_track_duration:
            reasons.append("insufficient track duration")
        if track.mean_detector_confidence < config.admission.min_mean_confidence:
            reasons.append("low mean detector confidence")
        if mean(o.area_fraction for o in track.observations) < config.admission.min_area_fraction:
            reasons.append("projected size too small")
        if track.track_id not in involved:
            reasons.append("no persistent event participation")
        entries = evidence[track.track_id]
        labels = defaultdict(list)
        for entry in entries:
            if entry["confidence"] >= config.vlm.confidence_threshold and entry["semantic_class"] != "unknown":
                labels[entry["semantic_class"]].append(entry)
        ordered = sorted(labels, key=lambda label: (-sum(e["confidence"] for e in labels[label]), label))
        chosen, confidence, attributes = "unknown", 0, {}
        ambiguity = None
        if ordered:
            winner = ordered[0]
            total = sum(sum(e["confidence"] for e in values) for values in labels.values())
            winner_mass = sum(e["confidence"] for e in labels[winner])/total
            runner_mass = sum(e["confidence"] for e in labels[ordered[1]])/total if len(ordered) > 1 else 0
            if winner_mass-runner_mass >= config.vlm.semantic_margin:
                chosen = winner
                confidence = mean(e["confidence"] for e in labels[winner])*winner_mass
                if confidence < config.vlm.confidence_threshold:
                    chosen, confidence = "unknown", 0
                else:
                    for key in {k for e in labels[winner] for k in e["attributes"]}:
                        values = {e["attributes"][key] for e in labels[winner] if key in e["attributes"]}
                        if len(values) == 1:
                            attributes[key] = next(iter(values))
            else:
                ambiguity = "conflicting semantic evidence; no class promoted"
        aggregation.append({"track_id": track.track_id, "detector_class": track.detector_class,
            "semantic_class": chosen, "semantic_confidence": confidence, "evidence": entries,
            "ambiguity": ambiguity, "admitted": not reasons})
        if reasons:
            rejected.append({"track_id": track.track_id, "detector_class": track.detector_class, "reasons": reasons})
            continue
        names[id_prefix(chosen)] += 1
        admitted.append(SemanticEntity(track_id=track.track_id, entity_id=f"{id_prefix(chosen)}_{names[id_prefix(chosen)]:02d}",
            detector_class=track.detector_class, semantic_class=chosen, semantic_confidence=confidence,
            attributes=attributes, first_seen=track.first_seen, last_seen=track.last_seen,
            is_anchor=track.is_anchor, anchor_score=track.anchor_score,
            admission_status="semantic_confirmed" if chosen != "unknown" else "unknown", evidence=entries))
    return admitted, rejected, aggregation
