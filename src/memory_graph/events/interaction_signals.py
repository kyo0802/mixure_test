"""Sparse, image-relative candidate signals. Co-motion is not proof of carrying."""
from collections import defaultdict
from math import hypot


def sparse_pair_series(timelines, allowed_ids):
    frames = defaultdict(dict)
    for timeline in timelines:
        if timeline.track_id in allowed_ids:
            for obs in timeline.observations:
                frames[obs.frame_index][obs.track_id] = obs
    pairs = defaultdict(list)
    for _, visible in sorted(frames.items()):
        seen = set()
        for obs in visible.values():
            for neighbor in obs.nearest_tracks:
                other_id = neighbor["track_id"]
                if other_id not in visible:
                    continue
                pair = tuple(sorted((obs.track_id, other_id)))
                if pair in seen:
                    continue
                seen.add(pair)
                a, b = visible[pair[0]], visible[pair[1]]
                denominator = a.speed*b.speed
                cosine = sum(x*y for x, y in zip(a.velocity, b.velocity))/denominator if denominator > 1e-10 else 0
                pairs[pair].append({"timestamp": obs.timestamp, "episode_id": obs.episode_id,
                    "distance": hypot(a.normalized_center[0]-b.normalized_center[0], a.normalized_center[1]-b.normalized_center[1]),
                    "bbox_distance": neighbor["bbox_distance"], "overlap": neighbor["iou"],
                    "cosine": max(-1, min(1, cosine)), "min_speed": min(a.speed, b.speed),
                    "confidence": min(a.confidence, b.confidence)})
    return pairs
