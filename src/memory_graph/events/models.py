from typing import Literal
from pydantic import Field, model_validator
from ..models import Model, Probability, Time

EventType = Literal["appearance", "disappearance_candidate", "proximity_change", "motion_coupling_candidate", "relation_change", "interaction_candidate"]


class EventProposal(Model):
    event_id: str = ""
    event_type: EventType
    episode_id: str
    start_time: Time
    peak_time: Time
    end_time: Time
    involved_track_ids: list[int]
    signals: list[str] = Field(default_factory=list)
    signal_evidence: list[dict] = Field(default_factory=list)
    confidence: Probability
    priority: float = Field(default=0, ge=0)
    selected: bool = False
    skip_reason: str | None = None

    @model_validator(mode="after")
    def ordered(self):
        if not self.start_time <= self.peak_time <= self.end_time:
            raise ValueError("Event times must be ordered")
        if not self.involved_track_ids or len(set(self.involved_track_ids)) != len(self.involved_track_ids):
            raise ValueError("Event requires distinct track IDs")
        return self


class Keyframe(Model):
    phase: Literal["before", "during", "after"]
    frame_index: int
    timestamp: Time
    desired_timestamp: Time
    image_path: str
    visible_track_ids: list[int]
    supplied_track_ids: list[int]
    sharpness: float
    selection_score: float
    notes: list[str] = Field(default_factory=list)
