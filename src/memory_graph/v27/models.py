"""Shared data model for both temporal and object lifetime memory views."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

PHYSICAL = {"NEAR", "ON", "INSIDE", "BEHIND", "OCCLUDED_BY", "HELD_BY"}
IMAGE = {"IMAGE_LEFT_OF", "IMAGE_RIGHT_OF", "IMAGE_ABOVE", "IMAGE_BELOW", "IMAGE_NEAR", "IMAGE_OVERLAP"}
ALLOWED_TRUST = {"TRUSTED", "CONFIRMED", "CONFIRMED_MATCH"}


@dataclass(frozen=True)
class Config:
    target_id: str = "phone_01"
    minimum_support_frames: int = 3
    minimum_support_seconds: float = 0.35
    maximum_support_gap_seconds: float = 0.65
    image_near_gap_fraction: float = 0.12
    maximum_current_anchors: int = 3
    relation_end_confirmed_frames: int = 3
    physical_evidence_confidence: float = 0.8


@dataclass
class EntityObservation:
    entity_id: str | None
    frame: int
    time: float
    bbox: list[float]
    label: str
    identity: str
    source: str
    source_id: str
    observation_id: str
    confidence: float | None = None

    def __post_init__(self):
        if self.entity_id is not None and (self.entity_id.isdigit() or self.entity_id.startswith(("track:", "track_"))):
            raise ValueError("Track ID is provenance, not a PersistentEntity ID")
        if len(self.bbox) != 4 or self.bbox[2] <= self.bbox[0] or self.bbox[3] <= self.bbox[1]:
            raise ValueError("Observation requires a positive xyxy bounding box")

    @property
    def trusted(self) -> bool:
        return self.identity in ALLOWED_TRUST and self.entity_id is not None


@dataclass
class RelationObservation:
    subject: str
    relation: str
    object: str
    frame: int
    time: float
    reference_frame: str
    source: list[str]
    metrics: dict
    state: str = "OBSERVATION_ONLY"


@dataclass
class RelationCandidate:
    subject: str
    relation: str
    object: str
    support_frames: list[int] = field(default_factory=list)
    support_times: list[float] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    state: str = "CANDIDATE"


@dataclass
class RelationEpisode:
    episode_id: str
    subject: str
    relation: str
    object: str
    kind: str
    start_frame: int
    end_frame: int
    start_time: float
    last_confirmed_time: float
    status: str
    evidence_level: str
    support_frames: list[int]
    evidence: list[dict]
    source: list[str]
    graph_snapshot_ids: list[str] = field(default_factory=list)
    ended_at_frame: int | None = None


@dataclass
class MemoryEvent:
    event_id: str
    event_type: str
    frame: int
    time: float
    details: dict


def record(value):
    return asdict(value)
