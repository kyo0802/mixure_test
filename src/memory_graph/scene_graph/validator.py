from ..spatial.geometry import pair_signals
from ..vlm.schemas import INTERACTIONS


def geometry_verdict(predicate, a, b, width, height, config):
    if b is None:
        return "not_applicable", {}
    s = pair_signals(a.bbox, b.bbox, width, height)
    if predicate == "LEFT_OF":
        supported, conflict = s["dx"] < -config.direction_margin, s["dx"] > config.direction_margin
    elif predicate == "RIGHT_OF":
        supported, conflict = s["dx"] > config.direction_margin, s["dx"] < -config.direction_margin
    elif predicate == "ABOVE":
        supported, conflict = s["dy"] < -config.direction_margin, s["dy"] > config.direction_margin
    elif predicate == "BELOW":
        supported, conflict = s["dy"] > config.direction_margin, s["dy"] < -config.direction_margin
    elif predicate == "NEAR":
        supported, conflict = s["bbox_distance"] <= config.near_threshold, s["bbox_distance"] > config.near_threshold
    elif predicate == "OVERLAPPING":
        supported, conflict = s["overlap_fraction"] >= .05, s["overlap_fraction"] == 0
    elif predicate == "INSIDE":
        supported, conflict = s["subject_containment"] >= .9, s["subject_containment"] < .2
    elif predicate == "ON":
        supported = s["horizontal_overlap"] > .2 and abs(s["top_gap"]) <= .15 and s["dy"] < 0
        conflict = s["bbox_distance"] > config.near_threshold
    elif predicate in INTERACTIONS:
        # Geometry can reject an implausibly distant pair; it cannot confirm the action itself.
        supported, conflict = False, s["bbox_distance"] > config.near_threshold
    else:
        supported, conflict = False, False
    return ("conflicts" if conflict else "supports" if supported else "not_testable"), s


def validate_relation(relation, frames, observations, width, height, config, entities):
    phases = [f for f in frames if relation.temporal_phase in {"persistent", "transition"} or f.phase == relation.temporal_phase]
    evidence = []
    times = []
    for frame in phases:
        lookup = observations.get(frame.frame_index, {})
        a, b = lookup.get(relation.subject_track_id), lookup.get(relation.object_track_id)
        if a is None or (relation.object_track_id is not None and b is None):
            continue
        verdict, signals = geometry_verdict(relation.predicate, a, b, width, height, config)
        evidence.append({"phase": frame.phase, "timestamp": frame.timestamp, "verdict": verdict, "signals": signals})
        times.append(frame.timestamp)
    if not evidence:
        return None, "relation endpoints not co-visible in the claimed phase"
    if relation.predicate == "UNKNOWN":
        return None, "UNKNOWN is not promoted as an asserted relation"
    if relation.predicate in INTERACTIONS:
        actor = entities.get(relation.subject_track_id)
        if actor is None or actor.semantic_class not in {"person", "human", "man", "woman", "child"}:
            return None, "human-object interaction actor lacks VLM person semantics"
    verdicts = [e["verdict"] for e in evidence]
    conflicts = verdicts.count("conflicts")
    confidence = relation.confidence*(config.conflict_multiplier if conflicts else 1)
    if confidence < config.min_relation_confidence:
        return None, "geometry conflict or relation confidence below threshold"
    geometry = "conflicts" if conflicts else "supports" if "supports" in verdicts else "not_testable"
    return {"confidence": confidence, "times": sorted(set(times)), "geometry": geometry, "details": {"phase_checks": evidence,
            "physical_or_action_verification": False}}, None
