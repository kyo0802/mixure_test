"""Swappable, online target binding. No scenario descriptions or future frames."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class BoundTarget:
    entity_id: str
    source_track_id: int | None
    frame_index: int
    timestamp: float
    bbox: list[float]
    source_kind: str


class TargetBinding:
    """Downstream code consumes BoundTarget, independent of selection mode."""

    def bind_target(self, observation=None, tracklet=None, bbox_prompt=None):
        supplied = sum(value is not None for value in (observation, tracklet, bbox_prompt))
        if supplied != 1:
            raise ValueError("Provide exactly one target evidence source")
        if tracklet is not None:
            observation = tracklet["observations"][-1]
            track_id = tracklet["track_id"]
            source = "tracklet"
        elif bbox_prompt is not None:
            observation = bbox_prompt
            track_id = None
            source = "bbox_prompt"
        else:
            track_id = observation.get("track_id")
            source = "observation"
        if observation.get("class_name", "cell phone") != "cell phone":
            raise ValueError("Target binding requires phone-compatible evidence")
        return BoundTarget("phone_01", track_id, observation["frame_index"],
                           observation["timestamp"], list(observation["bbox"]), source)


class AutomaticTargetBinding(TargetBinding):
    """First mature local phone track, with tie ambiguity; uses only seen frames."""

    MIN_OBSERVATIONS = 3
    MIN_SPAN_SECONDS = .4
    MIN_MEAN_CONFIDENCE = .5
    TIE_QUALITY_MARGIN = .1

    def __init__(self):
        self.seen = defaultdict(list)
        self.bound = None
        self.audit = []

    @staticmethod
    def quality(rows):
        return sum(row["confidence"] for row in rows) / len(rows)

    def observe_frame(self, frame, local_phone_rows):
        if self.bound is not None:
            return self.bound
        for track_id, obs in sorted(local_phone_rows, key=lambda item: item[0]):
            self.seen[track_id].append(obs)
        eligible = []
        for track_id, rows in sorted(self.seen.items()):
            span = rows[-1]["timestamp"] - rows[0]["timestamp"]
            mean_conf = self.quality(rows)
            ready = (len(rows) >= self.MIN_OBSERVATIONS and span >= self.MIN_SPAN_SECONDS
                     and mean_conf >= self.MIN_MEAN_CONFIDENCE)
            self.audit.append({"frame_index": frame, "track_id": track_id,
                               "semantic": "cell phone", "observations_seen": len(rows),
                               "duration_seconds_seen": span, "mean_detector_confidence": mean_conf,
                               "quality": mean_conf, "ready": ready})
            if ready:
                eligible.append((mean_conf, track_id, rows[-1]))
        if not eligible:
            return None
        eligible.sort(key=lambda item: (-item[0], item[1]))
        if len(eligible) > 1 and eligible[0][0] - eligible[1][0] < self.TIE_QUALITY_MARGIN:
            return None
        _, track_id, obs = eligible[0]
        self.bound = self.bind_target(observation={**obs, "track_id": track_id})
        return self.bound

    def result(self):
        return {"decision": "BOUND" if self.bound else "TARGET_BINDING_AMBIGUOUS",
                "bound_target": vars(self.bound) if self.bound else None,
                "policy": {"minimum_observations": self.MIN_OBSERVATIONS,
                           "minimum_span_seconds": self.MIN_SPAN_SECONDS,
                           "minimum_mean_confidence": self.MIN_MEAN_CONFIDENCE,
                           "tie_quality_margin": self.TIE_QUALITY_MARGIN,
                           "no_future_frames_or_gt": True},
                "candidate_initial_tracks": self.audit,
                "selection_evidence": "first mature local phone track; ambiguous if simultaneous quality tie"}


def automatic_bind(sampled_frames, tracks):
    by_frame = defaultdict(list)
    for track in tracks:
        if track["detector_class"] != "cell phone":
            continue
        for obs in track["observations"]:
            by_frame[obs["frame_index"]].append((track["track_id"], obs))
    binder = AutomaticTargetBinding()
    for row in sampled_frames:
        bound = binder.observe_frame(row["frame_index"], by_frame[row["frame_index"]])
        if bound is not None:
            break
    return bound, binder.result()
