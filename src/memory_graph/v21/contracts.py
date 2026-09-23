from typing import Literal
from pydantic import Field, model_validator
from ..models import Model, Probability


class IdentityConfig(Model):
    min_observations: int = Field(default=2, ge=2)
    min_duration: float = Field(default=.19, ge=0)
    min_confidence: Probability = .3
    max_association_gap: float = Field(default=2, gt=0)
    max_center_distance: float = Field(default=.12, gt=0)
    min_appearance_similarity: Probability = .85
    min_match_score: Probability = .83
    ambiguity_margin: Probability = .08
    lost_after_seconds: float = Field(default=4, gt=0)
    missed_context_seconds: float = Field(default=4, gt=0)
    max_missing_context: int = Field(default=2, ge=0)


class PersistentEntity(Model):
    entity_id: str
    local_track_ids: list[int]
    semantic_class: str = 'unknown'
    semantic_evidence: list[dict] = Field(default_factory=list)
    first_seen: float
    last_confirmed_seen: float
    last_confirmed_bbox: tuple[float, float, float, float]
    current_bbox: tuple[float, float, float, float] | None = None
    visibility: Literal['VISIBLE', 'UNOBSERVED', 'LOST']
    uncertainty: Probability
    visibility_history: list[dict] = Field(default_factory=list)
    association_history: list[dict] = Field(default_factory=list)
    future_evidence: dict = Field(default_factory=lambda: dict.fromkeys([
        'mask_continuity', 'coarse_3d_size', 'relative_3d_position',
        'anchor_relative_3d_position', 'camera_motion_compensated_continuity']))

    @model_validator(mode='after')
    def no_fake_box(self):
        if self.visibility != 'VISIBLE' and self.current_bbox is not None:
            raise ValueError('Unobserved entities cannot have a current bbox')
        return self


class ContextClaim(Model):
    subject_entity_id: str
    object_entity_id: str
    predicate: Literal['HOLDING', 'TOUCHING', 'ON', 'INSIDE', 'PICKING_UP', 'PUTTING_DOWN', 'CARRYING']
    confidence: Probability
    supporting_phases: list[Literal['before', 'during', 'after']]
    explanation: str = Field(max_length=500)


class ContextResult(Model):
    event_id: str
    decision: Literal['NONE', 'UNCERTAIN', 'SUPPORTED']
    claims: list[ContextClaim] = Field(default_factory=list)
    explanation: str = Field(max_length=1000)

    @model_validator(mode='after')
    def consistent(self):
        if self.decision == 'NONE' and self.claims:
            raise ValueError('NONE must have no claims')
        if self.decision == 'SUPPORTED' and not self.claims:
            raise ValueError('SUPPORTED requires a claim')
        return self
