import numpy as np
from ..config import AnchorsConfig
from ..models import AnchorInfo, ObjectTrack
from .geometry import normalized


def select_anchors(tracks: list[ObjectTrack], width: int, height: int, config: AnchorsConfig) -> list[AnchorInfo]:
    decisions = []
    for track in tracks:
        obs = track.observations
        boxes = [normalized(o.bbox, width, height) for o in obs]
        area = float(np.median([(b[2]-b[0])*(b[3]-b[1]) for b in boxes])) if boxes else 0
        confidence = float(np.mean([o.confidence for o in obs])) if obs else 0
        speeds = []
        for a, b in zip(obs, obs[1:]):
            dt = b.timestamp-a.timestamp
            if dt > 0:
                speeds.append(float(np.hypot((b.center[0]-a.center[0])/width,
                                             (b.center[1]-a.center[1])/height)/dt))
        speed = float(np.median(speeds)) if speeds else config.max_center_speed
        duration = track.last_seen-track.first_seen
        semantic = track.class_name in config.classes
        stability = max(0, 1-speed/config.max_center_speed)
        # Equal-weight explainable components, isolated here for later replacement.
        score = float(np.mean([float(semantic), confidence, stability,
            min(1, duration/config.duration_saturation_seconds), min(1, area/config.area_saturation_fraction)]))
        failures = []
        if not semantic:
            failures.append("class is not a configured semantic anchor")
        if len(obs) < config.min_observations:
            failures.append("insufficient observations")
        if duration < config.min_track_duration:
            failures.append("insufficient observed duration")
        if area < config.min_area_fraction:
            failures.append("median projected area too small")
        if speed > config.max_center_speed:
            failures.append("median camera-relative center speed too high")
        if score < config.min_anchor_score:
            failures.append("anchor score below threshold")
        decisions.append(AnchorInfo(object_id=track.object_id, is_anchor=not failures, anchor_score=score,
            metrics={"semantic_prior": float(semantic), "mean_detection_confidence": confidence,
                "median_center_speed": speed, "stability": stability, "median_area_fraction": area,
                "duration": duration, "observation_count": len(obs)}, reasons=failures or ["all anchor criteria passed"]))
    return decisions
