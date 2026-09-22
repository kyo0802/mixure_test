from pydantic import Field
from typing import Literal
from ..models import Model, Probability, Time
from ..vlm.schemas import Predicate, Phase


class SemanticEntity(Model):
    track_id: int
    entity_id: str
    detector_class: str
    semantic_class: str = "unknown"
    semantic_confidence: Probability = 0
    first_seen: Time
    last_seen: Time
    attributes: dict[str, str] = Field(default_factory=dict)
    is_anchor: bool = False
    anchor_score: Probability = 0
    admission_status: Literal["semantic_confirmed", "unknown"] = "unknown"
    evidence: list[dict] = Field(default_factory=list)


class Evidence(Model):
    vlm: bool = False
    tracking: bool = True
    geometry: Literal["supports", "conflicts", "not_testable", "not_applicable"] = "not_testable"
    details: dict = Field(default_factory=dict)


class GroundedRelation(Model):
    subject_track_id: int
    predicate: Predicate
    object_track_id: int | None = None
    confidence: Probability
    temporal_phase: Phase
    start_time: Time
    end_time: Time
    observed_times: list[float]
    event_ids: list[str]
    evidence: Evidence
    reference_frame: str = "image_relative"
    interval_meaning: str = "sparse visual support span, not continuous verified state"


class SceneGraph(Model):
    event_id: str
    analysis_status: str
    entities: list[SemanticEntity] = Field(default_factory=list)
    relations: list[GroundedRelation] = Field(default_factory=list)
    rejected_relations: list[dict] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TemporalMemory(Model):
    schema_version: str = "2.0"
    video: str
    metadata: dict = Field(default_factory=dict)
    entities: list[SemanticEntity] = Field(default_factory=list)
    attributes: list[dict] = Field(default_factory=list)
    relations: list[GroundedRelation] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    transitions: list[dict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=lambda: [
        "RGB and image-relative geometry, not world coordinates or true 3D",
        "Local track continuity, not object permanence or long-term ReID",
        "Semantic and interaction predicates require VLM evidence; unknown is valid",
        "Intervals summarize sparse sampled evidence, not continuously verified states"])
