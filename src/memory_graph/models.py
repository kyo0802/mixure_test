"""Validated, JSON-serializable contracts shared by all pipeline stages."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Time = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Predicate = Literal["LEFT_OF", "RIGHT_OF", "ABOVE", "BELOW", "NEAR", "OVERLAPS", "ON_OR_ABOVE", "INSIDE"]
ReferenceFrame = Literal["camera", "camera_relative"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class FrameInfo(Model):
    frame_index: int = Field(ge=0)
    timestamp: Time


class VideoMetadata(Model):
    fps: float = Field(gt=0)
    frame_count: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    duration: float = Field(gt=0)
    decoded_frame_count: int = 0
    sampled_frames: list[FrameInfo] = Field(default_factory=list)


class Episode(Model):
    episode_id: str
    start_time: Time
    end_time: Time
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_time < self.start_time or self.end_frame < self.start_frame:
            raise ValueError("Episode end must not precede its start")
        return self


class Detection(FrameInfo):
    class_id: int = Field(ge=0)
    class_name: str
    confidence: Probability
    bbox: tuple[float, float, float, float]

    @model_validator(mode="before")
    @classmethod
    def read_derived_center(cls, value):
        if isinstance(value, dict) and "center" in value:
            value = dict(value)
            center = value.pop("center")
            box = value.get("bbox")
            if box and (abs(center[0]-(box[0]+box[2])/2) > 1e-5 or abs(center[1]-(box[1]+box[3])/2) > 1e-5):
                raise ValueError("Serialized center disagrees with bbox")
        return value

    @model_validator(mode="after")
    def ordered_box(self):
        x1, y1, x2, y2 = self.bbox
        if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
            raise ValueError("bbox must be a positive-area xyxy box with nonnegative coordinates")
        return self

    @computed_field
    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1+x2)/2, (y1+y2)/2)


class ObjectObservation(Detection):
    object_id: str
    tracker_id: int
    episode_id: str


class ObjectTrack(Model):
    object_id: str
    class_name: str
    first_seen: Time
    last_seen: Time
    observations: list[ObjectObservation] = Field(default_factory=list)


class AnchorInfo(Model):
    object_id: str
    anchor_score: Probability
    is_anchor: bool
    metrics: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)


class RelationObservation(FrameInfo):
    subject_id: str
    predicate: Predicate
    object_id: str
    reference_frame: ReferenceFrame
    confidence: Probability
    episode_id: str
    signals: dict[str, float] = Field(default_factory=dict)


class StableRelation(Model):
    subject_id: str
    predicate: Predicate
    object_id: str
    reference_frame: ReferenceFrame
    start_time: Time
    end_time: Time
    support_count: int = Field(ge=1)
    confidence: Probability
    episode_id: str
    start_frame: int = Field(default=0, ge=0)
    end_frame: int = Field(default=0, ge=0)
    max_observed_gap: Time = 0

    @model_validator(mode="after")
    def ordered(self):
        if self.end_time < self.start_time or self.end_frame < self.start_frame:
            raise ValueError("Relation interval must be ordered")
        return self


class RelationTransition(Model):
    event_type: Literal["anchor_transition"] = "anchor_transition"
    object_id: str
    from_anchor: str
    to_anchor: str
    from_relation: Predicate
    to_relation: Predicate
    transition_time: Time
    previous_end_time: Time
    confidence: Probability
    from_episode: str
    to_episode: str


class MemoryNode(Model):
    id: str
    node_type: Literal["object", "anchor"]
    class_name: str
    first_seen: Time
    last_seen: Time
    observation_count: int = 0
    anchor_score: Probability | None = None


class MemoryEdge(Model):
    subject: str
    predicate: Predicate
    object: str
    reference_frame: ReferenceFrame
    start_time: Time
    end_time: Time
    support_count: int
    confidence: Probability
    episode_id: str
    start_frame: int
    end_frame: int
    max_observed_gap: Time


class MemoryGraphData(Model):
    schema_version: str = "1.0"
    video: str
    geometry: str = "RGB-only normalized 2D bounding boxes; no world-coordinate or metric 3D claims"
    metadata: dict = Field(default_factory=dict)
    episodes: list[Episode] = Field(default_factory=list)
    nodes: list[MemoryNode] = Field(default_factory=list)
    relations: list[MemoryEdge] = Field(default_factory=list)
    transitions: list[RelationTransition] = Field(default_factory=list)

    @model_validator(mode="after")
    def endpoints_exist(self):
        ids = {n.id for n in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("Duplicate graph node IDs")
        if any(e.subject not in ids or e.object not in ids for e in self.relations):
            raise ValueError("Relation endpoint missing from graph")
        return self
