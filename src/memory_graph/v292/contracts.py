"""Authoritative identity events and provenance contracts for V2.9.2."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


VISIBLE_STATES = {"OBSERVED", "VISIBLE", "VISIBLE_TRUSTED", "MATCHED"}
LOST_STATES = {"UNOBSERVED", "LOST"}
IDENTITY_STATES = {
    "OBSERVED", "VISIBLE", "UNOBSERVED", "LOST", "PROPAGATION_RESUMED",
    "DETECTION_RESUMED", "IDENTITY_CONFIRMED", "PROVISIONAL", "AMBIGUOUS", "REJECTED",
}


@dataclass(frozen=True)
class IdentityAuthorization:
    authorization_id: str
    video_id: str
    frame: int
    candidate_id: str
    decision: str
    appearance_evidence: dict[str, Any]
    competitor_evidence: dict[str, Any]
    semantic_compatibility: dict[str, Any]
    contradiction_check: dict[str, Any]
    mask_quality: dict[str, Any]
    source_guard_decision: str
    provenance: list[str]

    @property
    def valid(self) -> bool:
        return bool(
            self.authorization_id and self.video_id and self.frame >= 0 and self.candidate_id
            and self.decision == "CONFIRMED_MATCH"
            and self.source_guard_decision == "V2.6_IDENTITY_GUARD"
            and self.appearance_evidence and self.competitor_evidence
            and self.semantic_compatibility and self.contradiction_check
            and self.mask_quality and self.provenance
        )


@dataclass(frozen=True)
class IdentityEvent:
    event_id: str
    video_id: str
    frame: int
    time: float
    state: str
    candidate_id: str | None = None
    authorization_id: str | None = None
    provenance: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


class IdentityEventStore:
    """Single writer: all projections are derived from these events."""

    def __init__(self, video_id: str):
        self.video_id = video_id
        self.events: list[IdentityEvent] = []
        self.authorizations: dict[str, IdentityAuthorization] = {}
        self._ids: set[str] = set()

    def add_authorization(self, authorization: IdentityAuthorization) -> None:
        if authorization.video_id != self.video_id or not authorization.valid:
            raise ValueError("Identity Guard authorization is incomplete or belongs to another video")
        self.authorizations[authorization.authorization_id] = authorization

    def append(self, event: IdentityEvent) -> None:
        if event.video_id != self.video_id or event.state not in IDENTITY_STATES:
            raise ValueError("Identity event has an invalid video or state")
        if event.event_id in self._ids:
            raise ValueError(f"Duplicate identity event: {event.event_id}")
        if event.frame < 0 or event.time < 0:
            raise ValueError("Identity event requires non-negative frame/time")
        if event.state == "IDENTITY_CONFIRMED":
            authorization = self.authorizations.get(event.authorization_id or "")
            if not authorization or authorization.frame != event.frame or authorization.candidate_id != event.candidate_id:
                raise ValueError("IDENTITY_CONFIRMED requires its exact Identity Guard authorization")
        if event.state in {"PROPAGATION_RESUMED", "DETECTION_RESUMED", "PROVISIONAL", "AMBIGUOUS", "REJECTED"} and event.authorization_id:
            auth = self.authorizations.get(event.authorization_id)
            if auth is None:
                raise ValueError("Unknown authorization reference")
        self.events.append(event)
        self._ids.add(event.event_id)

    def timeline(self) -> list[dict[str, Any]]:
        rows = []
        for event in sorted(self.events, key=lambda x: (x.frame, x.event_id)):
            state = "MATCHED" if event.state == "IDENTITY_CONFIRMED" else event.state
            row = {"video_id": event.video_id, "frame_index": event.frame, "timestamp": event.time,
                   "state": state, "identity_event_id": event.event_id,
                   "authorization_id": event.authorization_id, "candidate_id": event.candidate_id,
                   "provenance": list(event.provenance)}
            if state == "MATCHED" and not row["authorization_id"]:
                raise ValueError("MATCHED projection has no authorization")
            rows.append(row)
        return rows

    def registry_projection(self) -> dict[str, Any]:
        confirmations = [e for e in self.events if e.state == "IDENTITY_CONFIRMED"]
        return {"video_id": self.video_id, "entity_id": "phone_01",
                "confirmations": [{"frame": e.frame, "candidate_id": e.candidate_id,
                                    "authorization_id": e.authorization_id, "event_id": e.event_id}
                                   for e in confirmations],
                "state": "MATCHED" if confirmations else "UNOBSERVED"}


def canonical_anchor_key(video_id: str, event_id: str, local_anchor_id: str) -> str:
    if not all((video_id, event_id, local_anchor_id)):
        raise ValueError("Anchor namespace components must be non-empty")
    return f"{video_id}::{event_id}::{local_anchor_id}"


def make_authorization(video_id: str, frame: int, candidate_id: str, decision: dict,
                       provenance: list[str]) -> IdentityAuthorization | None:
    if decision.get("decision") != "CONFIRMED_MATCH":
        return None
    appearance = decision.get("appearance") or {}
    competitor = decision.get("competitor") or decision.get("competitor_evidence") or {"checked": True}
    semantic = decision.get("semantic") or decision.get("semantic_compatibility") or {"checked": True}
    contradiction = decision.get("contradiction_check") or {"checked": True}
    mask = decision.get("mask_quality") or {"checked": True}
    auth = IdentityAuthorization(
        authorization_id=f"{video_id}:IG:{frame}:{candidate_id}", video_id=video_id, frame=frame,
        candidate_id=candidate_id, decision="CONFIRMED_MATCH", appearance_evidence=appearance,
        competitor_evidence=competitor, semantic_compatibility=semantic,
        contradiction_check=contradiction, mask_quality=mask,
        source_guard_decision="V2.6_IDENTITY_GUARD", provenance=list(provenance),
    )
    return auth if auth.valid else None


def apply_forward_confirmation(rows: list[dict], authorization: IdentityAuthorization,
                               propagation_frames: set[int] | None = None,
                               detection_frames: set[int] | None = None) -> list[dict]:
    """Authorize the matched frame and future supported frames only."""
    propagation_frames = propagation_frames or set()
    detection_frames = detection_frames or set()
    result = []
    for row in rows:
        item = dict(row)
        frame = item["frame_index"]
        if frame == authorization.frame:
            item.update(state="MATCHED", authorization_id=authorization.authorization_id,
                        candidate_id=authorization.candidate_id)
        elif frame > authorization.frame and frame in propagation_frames:
            item.update(state="VISIBLE", authorization_id=authorization.authorization_id,
                        provenance="authorized_forward_sam_reinitialization")
        elif frame > authorization.frame and frame in detection_frames:
            item.update(state="DETECTION_RESUMED", authorization_id=authorization.authorization_id,
                        provenance="authorized_forward_candidate_alias")
        result.append(item)
    return result


def record_dict(value: Any) -> dict[str, Any]:
    return asdict(value)
