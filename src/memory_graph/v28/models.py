"""Typed V2.8 records; V2.7 identity observations remain the frozen input contract."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Config:
    target_id: str = "phone_01"
    minimum_support_frames: int = 3
    minimum_support_seconds: float = 0.35
    maximum_support_gap_seconds: float = 0.65
    primary_local_distance_fraction: float = 0.30
    primary_gap_fraction: float = 0.20
    context_local_distance_fraction: float = 0.28
    context_gap_fraction: float = 0.18
    maximum_primary_anchors: int = 3
    maximum_context_per_primary: int = 2
    vlm_promotion_confidence: float = 0.80


@dataclass
class SpatialSegment:
    segment_id: str
    subject: str
    object: str
    hop: int
    start_frame: int
    end_frame: int
    start_time: float
    end_time: float
    support_frames: list[int]
    support_times: list[float]
    raw_label: str
    semantic_roles: list[str]
    observations: list[dict]
    via_primary: str | None = None
    status: str = "STABLE"


@dataclass
class PhysicalRelationCandidate:
    candidate_id: str
    target: str
    anchor: str
    candidate_relation: str
    start_frame: int
    end_frame: int
    identity_state: str
    geometry_evidence: dict
    temporal_evidence: dict
    semantic_evidence: dict
    vlm_evidence: dict
    decision: str
    reason: str
    source_observations: list[str]
    source_snapshots: list[str] = field(default_factory=list)
    segment_id: str | None = None


def record(value):
    return asdict(value)
