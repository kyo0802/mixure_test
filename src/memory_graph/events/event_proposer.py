from copy import deepcopy
from .models import EventProposal
from .interaction_signals import sparse_pair_series


def persistent(track, config):
    return (len(track.observations) >= config.min_observations and
            track.last_seen-track.first_seen >= config.min_track_duration and
            track.mean_detector_confidence >= config.min_detector_confidence)


def propose_events(timelines, duration, config):
    eligible = {t.track_id: t for t in timelines if persistent(t, config)}
    proposals = []

    def add(kind, ids, start, peak, end, episode, confidence, evidence):
        persistence = min(1, sum(eligible[i].last_seen-eligible[i].first_seen for i in ids)/(5*len(ids)))
        person_pair = len(ids) > 1 and any(eligible[i].detector_class == "person" for i in ids)
        priority = confidence + persistence + float(person_pair) + (1 if kind in
            {"proximity_change", "motion_coupling_candidate", "relation_change"} else .3)
        proposals.append(EventProposal(event_id=f"raw_{len(proposals)+1:04d}", event_type=kind,
            start_time=max(0, start), peak_time=peak, end_time=min(duration, end), episode_id=episode,
            involved_track_ids=sorted(set(ids)), confidence=confidence, priority=priority,
            signals=[kind], signal_evidence=[evidence]))

    for tid, track in eligible.items():
        add("appearance", [tid], track.first_seen, track.first_seen,
            min(track.last_seen, track.first_seen+config.min_track_duration), track.observations[0].episode_id,
            track.mean_detector_confidence, {"persistence_observations": len(track.observations), "not_semantic_identity": True})
        # Detect sustained internal gaps as well as disappearance before the end of the recording.
        for i, obs in enumerate(track.observations):
            next_time = track.observations[i+1].timestamp if i+1 < len(track.observations) else duration
            if (next_time-obs.timestamp >= config.disappearance_seconds and i+1 >= config.min_observations
                    and obs.timestamp-track.first_seen >= config.min_track_duration):
                add("disappearance_candidate", [tid], obs.timestamp, obs.timestamp+config.disappearance_seconds,
                    obs.timestamp+config.disappearance_seconds, obs.episode_id, track.mean_detector_confidence,
                    {"last_visible": obs.timestamp, "next_visible_or_video_end": next_time,
                     "absence_seconds": next_time-obs.timestamp, "interpretation": "undetected, not lost or moved"})
    for pair, series in sparse_pair_series(timelines, set(eligible)).items():
        last_proximity = -float("inf")
        coupled = []
        last_coupling = -float("inf")
        for index, current in enumerate(series):
            window = [s for s in series[:index+1] if current["timestamp"]-s["timestamp"] <= config.proximity_window_seconds
                      and s["episode_id"] == current["episode_id"]]
            if len(window) >= config.min_observations:
                previous = window[0]
                change = previous["distance"]-current["distance"]
                if (abs(change) >= config.proximity_change_threshold and
                        current["timestamp"]-previous["timestamp"] >= config.signal_persistence_seconds and
                        current["timestamp"]-last_proximity >= config.cooldown_seconds):
                    add("proximity_change", pair, previous["timestamp"], current["timestamp"], current["timestamp"],
                        current["episode_id"], current["confidence"], {"distance_change": change,
                        "direction": "approaching" if change > 0 else "separating", "image_relative": True})
                    last_proximity = current["timestamp"]
            is_coupled = (current["bbox_distance"] <= config.near_threshold and
                current["cosine"] >= config.motion_coupling_threshold and current["min_speed"] >= config.min_motion_speed)
            if coupled and (current["timestamp"]-coupled[-1]["timestamp"] > config.signal_persistence_seconds or
                            current["episode_id"] != coupled[-1]["episode_id"]):
                coupled = []
            coupled = [*coupled, current] if is_coupled else []
            if (len(coupled) >= config.min_observations and current["timestamp"]-coupled[0]["timestamp"] >= config.signal_persistence_seconds
                    and current["timestamp"]-last_coupling >= config.cooldown_seconds):
                add("motion_coupling_candidate", pair, coupled[0]["timestamp"], current["timestamp"], current["timestamp"],
                    current["episode_id"], current["confidence"], {"cosine_similarity": current["cosine"],
                    "support": len(coupled), "camera_motion_can_explain_signal": True})
                last_coupling = current["timestamp"]
                coupled = []
    for tid, track in eligible.items():
        previous_stable = None
        run = []
        current_neighbor = None
        for obs in track.observations:
            neighbors = [n for n in obs.nearest_tracks if n["track_id"] in eligible and n["bbox_distance"] <= config.near_threshold]
            neighbor = min(neighbors, key=lambda n: n["center_distance"])["track_id"] if neighbors else None
            if neighbor != current_neighbor or (run and obs.timestamp-run[-1].timestamp > config.signal_persistence_seconds):
                run, current_neighbor = [], neighbor
            run.append(obs)
            if neighbor is not None and len(run) >= config.min_observations and obs.timestamp-run[0].timestamp >= config.signal_persistence_seconds:
                if previous_stable and previous_stable[0] != neighbor:
                    add("relation_change", [tid, previous_stable[0], neighbor], run[0].timestamp, obs.timestamp, obs.timestamp,
                        obs.episode_id, obs.confidence, {"from_nearest_track": previous_stable[0], "to_nearest_track": neighbor,
                        "meaning": "persistent nearest image-neighbor change"})
                previous_stable = (neighbor, obs.timestamp)
    return sorted(proposals, key=lambda e: (e.peak_time, e.event_id))


def merge_events(proposals, config):
    merged = []
    for proposal in sorted(proposals, key=lambda e: (e.start_time, e.peak_time)):
        current = deepcopy(proposal)
        changed = True
        while changed:
            changed = False
            for other in list(merged):
                start, end = min(current.start_time, other.start_time), max(current.end_time, other.end_time)
                overlap = (current.start_time <= other.end_time+config.merge_window_seconds and
                           other.start_time <= current.end_time+config.merge_window_seconds)
                if (overlap and set(current.involved_track_ids) & set(other.involved_track_ids)
                        and current.episode_id == other.episode_id and end-start <= config.max_merged_duration):
                    peak = current.peak_time if current.priority >= other.priority else other.peak_time
                    current.start_time, current.end_time, current.peak_time = start, end, peak
                    current.involved_track_ids = sorted(set(current.involved_track_ids+other.involved_track_ids))
                    current.signals = sorted(set(current.signals+other.signals))
                    current.signal_evidence.extend(other.signal_evidence)
                    current.confidence = max(current.confidence, other.confidence)
                    current.priority = max(current.priority, other.priority)
                    current.event_type = current.signals[0] if len(current.signals) == 1 else "interaction_candidate"
                    merged.remove(other)
                    changed = True
                    break
        merged.append(current)
    for i, event in enumerate(sorted(merged, key=lambda e: e.peak_time), 1):
        event.event_id = f"evt_{i:03d}"
        event.priority += .4*(len(event.signals)-1)
    selected = []
    for event in sorted(merged, key=lambda e: (-e.priority, e.peak_time)):
        # Selection is a property of this budget pass, never inherited input state.
        event.selected = False
        event.skip_reason = None
        duplicate = any(abs(e.peak_time-event.peak_time) < config.cooldown_seconds and
                        set(e.involved_track_ids) & set(event.involved_track_ids) for e in selected)
        if len(selected) < config.max_vlm_events and not duplicate:
            event.selected = True
            selected.append(event)
        else:
            event.skip_reason = "near-duplicate selected window" if duplicate else "max_vlm_events budget"
    return sorted(merged, key=lambda e: e.peak_time)
