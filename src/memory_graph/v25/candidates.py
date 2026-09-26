"""Continuous GT-free scene-phone admission and conservative tracklet grouping."""
from __future__ import annotations

from dataclasses import dataclass, field

from memory_graph.v22.sam_tracking import box_iou

MAX_GAP_SECONDS = .8
MIN_GROUP_IOU = .30
DISTINCT_IOU_BELOW = .10
MAX_VIEWS = 4


@dataclass
class CandidateHypothesis:
    candidate_id: str
    semantic_class: str = "cell phone"
    observations: list[dict] = field(default_factory=list)
    source_track_ids: set[int] = field(default_factory=set)
    distinct_coexistence_with: set[str] = field(default_factory=set)
    appearance_views: list[dict] = field(default_factory=list)
    sam_support: list[dict] = field(default_factory=list)
    reid_history: list[dict] = field(default_factory=list)
    status: str = "PROVISIONAL"

    @property
    def first_seen(self):
        return self.observations[0]["timestamp"]

    @property
    def last_seen(self):
        return self.observations[-1]["timestamp"]

    def add(self, observation):
        self.observations.append(observation)
        if observation["source_track_id"] is not None:
            self.source_track_ids.add(observation["source_track_id"])
        self.select_views()

    def select_views(self):
        """Confidence-first, temporally diverse views; no target similarity ranking."""
        ordered = sorted(self.observations,
                         key=lambda o: (-o["confidence"], o["frame_index"], o["raw_detection_index"]))
        chosen = []
        for obs in ordered:
            if all(abs(obs["frame_index"] - prior["frame_index"]) >= 12 for prior in chosen):
                chosen.append(obs)
            if len(chosen) >= MAX_VIEWS:
                break
        if len(chosen) < MAX_VIEWS:
            for obs in ordered:
                if obs not in chosen:
                    chosen.append(obs)
                if len(chosen) >= MAX_VIEWS:
                    break
        self.appearance_views = sorted(chosen, key=lambda o: o["frame_index"])

    def summary(self):
        return {"candidate_id": self.candidate_id, "semantic_class": self.semantic_class,
                "first_seen": self.first_seen, "last_seen": self.last_seen,
                "source_track_ids": sorted(self.source_track_ids),
                "observations": self.observations, "appearance_views": self.appearance_views,
                "sam_support": self.sam_support,
                "distinct_coexistence_with": sorted(self.distinct_coexistence_with),
                "reid_history": self.reid_history, "status": self.status}


class CandidateStream:
    def __init__(self):
        self.candidates: dict[str, CandidateHypothesis] = {}
        self.events: list[dict] = []
        self.grouping_audit: list[dict] = []
        self.next_id = 1

    def _new(self):
        cid = f"candidate_{self.next_id:03d}"
        self.next_id += 1
        self.candidates[cid] = CandidateHypothesis(cid)
        return self.candidates[cid]

    def _possible_groups(self, observation):
        groups = []
        for candidate in self.candidates.values():
            if candidate.status == "MATCHED":
                continue
            last = candidate.observations[-1]
            gap = observation["timestamp"] - last["timestamp"]
            if gap < 0 or gap > MAX_GAP_SECONDS:
                continue
            iou = box_iou(observation["bbox"], last["bbox"])
            same_track = observation["source_track_id"] is not None and observation["source_track_id"] in candidate.source_track_ids
            if (iou >= MIN_GROUP_IOU or same_track and iou >= .10) and not any(
                    prior["frame_index"] == observation["frame_index"] and
                    box_iou(prior["bbox"], observation["bbox"]) < DISTINCT_IOU_BELOW
                    for prior in candidate.observations):
                groups.append((iou, same_track, candidate))
        return sorted(groups, key=lambda x: (-x[0], -int(x[1]), x[2].candidate_id))

    def admit(self, observation):
        options = self._possible_groups(observation)
        if options and (len(options) == 1 or options[0][0] - options[1][0] >= .20):
            candidate = options[0][2]
            reason = "short-gap geometry/tracklet support"
        else:
            candidate = self._new()
            reason = "new provisional phone; grouping uncertain" if options else "new provisional phone"
        candidate.add(observation)
        self.events.append({"frame_index": observation["frame_index"], "timestamp": observation["timestamp"],
                            "raw_detection_index": observation["raw_detection_index"],
                            "source_track_id": observation["source_track_id"],
                            "semantic_class": observation["semantic_class"],
                            "admitted": True, "candidate_id": candidate.candidate_id,
                            "reid_evaluated": False, "reid_decision": None, "reason": reason})
        self.grouping_audit.append({"frame_index": observation["frame_index"],
                                    "candidate_id": candidate.candidate_id,
                                    "alternatives": [{"candidate_id": c.candidate_id, "iou": iou,
                                                      "same_track_support": same}
                                                     for iou, same, c in options],
                                    "decision": "GROUP" if options and candidate == options[0][2] else "NEW",
                                    "reason": reason})
        return candidate

    def finish_frame(self, frame):
        current = [c for c in self.candidates.values() if c.observations[-1]["frame_index"] == frame]
        for i, a in enumerate(current):
            for b in current[i+1:]:
                aa = next(o for o in reversed(a.observations) if o["frame_index"] == frame)
                bb = next(o for o in reversed(b.observations) if o["frame_index"] == frame)
                if box_iou(aa["bbox"], bb["bbox"]) < DISTINCT_IOU_BELOW:
                    a.distinct_coexistence_with.add(b.candidate_id)
                    b.distinct_coexistence_with.add(a.candidate_id)
                    self.grouping_audit.append({"frame_index": frame, "candidate_ids": [a.candidate_id, b.candidate_id],
                                                "decision": "DISTINCT_COEXISTENCE", "iou": box_iou(aa["bbox"], bb["bbox"])})

    def as_json(self):
        return {"observations": self.events, "candidate_count": len(self.candidates),
                "policy": {"continuous_all_sampled_frames": True, "max_gap_seconds": MAX_GAP_SECONDS,
                           "minimum_group_iou": MIN_GROUP_IOU, "distinct_coexistence_iou_below": DISTINCT_IOU_BELOW}}
