from typing import Literal, Annotated
from pydantic import Field, StrictInt, field_validator, model_validator
from ..models import Model, Probability

TrackID = Annotated[StrictInt, Field(ge=1)]
Predicate = Literal["LEFT_OF", "RIGHT_OF", "ABOVE", "BELOW", "NEAR", "OVERLAPPING", "ON", "INSIDE",
    "HOLDING", "PICKING_UP", "PUTTING_DOWN", "CARRYING", "TOUCHING", "VISIBLE", "PARTIALLY_OCCLUDED", "UNKNOWN"]
Phase = Literal["before", "during", "after", "persistent", "transition"]
INTERACTIONS = {"HOLDING", "PICKING_UP", "PUTTING_DOWN", "CARRYING", "TOUCHING"}
SPATIAL = {"LEFT_OF", "RIGHT_OF", "ABOVE", "BELOW", "NEAR", "OVERLAPPING", "ON", "INSIDE"}


class VLMEntity(Model):
    track_id: TrackID
    semantic_class: str = Field(min_length=1, max_length=64)
    confidence: Probability
    attributes: dict[str, str] = Field(default_factory=dict)

    @field_validator("semantic_class")
    @classmethod
    def normalize_class(cls, value):
        value = " ".join(value.lower().strip().split())
        return value or "unknown"

    @field_validator("attributes")
    @classmethod
    def visible_attributes_only(cls, values):
        if set(values)-{"color", "appearance", "state", "motion_state"}:
            raise ValueError("Only visible color/appearance/state/motion_state attributes are allowed")
        if any(len(v) > 120 for v in values.values()):
            raise ValueError("Attribute description too long")
        return values


class VLMRelation(Model):
    subject_track_id: TrackID
    predicate: Predicate
    object_track_id: TrackID | None = None
    confidence: Probability
    temporal_phase: Phase
    explanation: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def arity(self):
        if self.predicate in {"VISIBLE", "PARTIALLY_OCCLUDED"}:
            if self.object_track_id is not None:
                raise ValueError("Visibility predicates are unary states; object_track_id must be null")
        elif self.object_track_id is None or self.object_track_id == self.subject_track_id:
            raise ValueError("Binary relation requires two distinct supplied IDs")
        return self


class VLMSceneGraphResult(Model):
    event_id: str
    entities: list[VLMEntity] = Field(default_factory=list)
    relations: list[VLMRelation] = Field(default_factory=list)
    summary: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def unique_entities(self):
        if len({e.track_id for e in self.entities}) != len(self.entities):
            raise ValueError("Duplicate track IDs in entity list")
        return self
