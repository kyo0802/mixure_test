"""Backend boundary. Only the mock backend is configured in this delivery."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .common import Phase2BBlocked, canonical_bytes


_BACKEND_FACTORIES = {}


def register_backend(name: str, factory) -> None:
    """Register an explicitly configured backend factory; no implicit fallback."""
    if not isinstance(name, str) or not name or name in _BACKEND_FACTORIES:
        raise Phase2BBlocked("INVALID_OR_DUPLICATE_BACKEND_REGISTRATION")
    _BACKEND_FACTORIES[name] = factory


class Backend(Protocol):
    name: str
    def invoke(self, request: dict, media: dict[str, bytes], timeout_seconds: float) -> bytes: ...


def _state(state: str, alias: str | None) -> dict:
    return {"state": state, "supporting_frame_alias": alias}


def _base(outcome: str, events: list[dict], aliases: list[str]) -> dict:
    last_alias = aliases[-1] if aliases else None
    return {
        "schema_version": "PASS_T_PHASE2B_PREDICTION_V1",
        "target_id": "TARGET_A",
        "window_outcome": outcome,
        "window_cited_frame_aliases": [aliases[0], aliases[-1]] if aliases else [],
        "events": events,
        "last_directly_supported_state": _state("OTHER_OBSERVED", last_alias) if last_alias else _state("STATE_UNKNOWN", None),
        "end_visibility": "VISIBLE" if last_alias else "UNKNOWN",
        "subsequent_state": "UNKNOWN",
        "rationale": "Bounded mock response for infrastructure validation.",
        "uncertainty": "Mock output; no physical claim.",
        "safety_assertions": {"global_identity_claimed": False, "state_persisted_across_unobserved_interval": False, "container_or_handover_auto_classified": False},
    }


def _event(kind: str, aliases: list[str], exact: bool = False) -> dict:
    if len(aliases) < 3:
        raise Phase2BBlocked("MOCK_EVENT_REQUIRES_THREE_FRAMES")
    timing = {"status": "EXACT_SUPPLIED_FRAME", "frame_alias": aliases[1]} if exact else {
        "status": "BOUNDED_SUPPLIED_FRAMES", "start_frame_alias": aliases[0], "end_frame_alias": aliases[2]}
    states = ("ON_SURFACE", "HELD_BY_PERSON") if kind == "PICKUP" else ("HELD_BY_PERSON", "ON_SURFACE")
    return {
        "event_id": "PRED_EVT_001", "event_type": kind, "timing": timing,
        "cited_frame_aliases": aliases[:3],
        "before_state": _state(states[0], aliases[0]), "after_state": _state(states[1], aliases[2]),
        "target_association_uncertainty": "NONE", "timing_uncertainty": "Bounded by supplied mock frames.",
        "rationale": "Mock state transition used only to validate contracts.",
    }


@dataclass
class MockBackend:
    scenario: str
    name: str = "MOCK_BACKEND"

    def invoke(self, request: dict, media: dict[str, bytes], timeout_seconds: float) -> bytes:
        aliases = [alias for row in request.get("media", []) for alias in row.get("supplied_frame_aliases", [])]
        aliases = list(dict.fromkeys(aliases))
        if self.scenario == "timeout":
            raise TimeoutError("MOCK_TIMEOUT")
        if self.scenario == "malformed_json":
            return b'{"broken":'
        if self.scenario == "missing_fields":
            return canonical_bytes({"schema_version": "PASS_T_PHASE2B_PREDICTION_V1"})
        if self.scenario == "out_of_payload_citation":
            value = _base("CONFIRMED_EVENTS", [_event("PICKUP", aliases)], aliases)
            value["events"][0]["cited_frame_aliases"].append("F9999")
            return canonical_bytes(value)
        if self.scenario == "fabricated_exact_timing":
            value = _base("CONFIRMED_EVENTS", [_event("PICKUP", aliases, exact=True)], aliases)
            value["events"][0]["timing"]["frame_alias"] = "F9999"
            return canonical_bytes(value)
        if self.scenario == "global_identity_claim":
            value = _base("NO_CONFIRMED_EVENT", [], aliases)
            value["safety_assertions"]["global_identity_claimed"] = True
            return canonical_bytes(value)
        if self.scenario == "persisted_state":
            value = _base("NO_CONFIRMED_EVENT", [], aliases)
            value["safety_assertions"]["state_persisted_across_unobserved_interval"] = True
            return canonical_bytes(value)
        if self.scenario == "extra_events":
            value = _base("CONFIRMED_EVENTS", [_event("PICKUP", aliases), _event("PLACEMENT", aliases)], aliases)
            value["events"][1]["event_id"] = "PRED_EVT_002"
            return canonical_bytes(value)
        outcomes = {
            "valid_pickup": _base("CONFIRMED_EVENTS", [_event("PICKUP", aliases)], aliases),
            "valid_placement": _base("CONFIRMED_EVENTS", [_event("PLACEMENT", aliases)], aliases),
            "no_event": _base("NO_CONFIRMED_EVENT", [], aliases),
            "insufficient": _base("INSUFFICIENT_EVIDENCE", [], aliases),
            "target_not_observable": _base("TARGET_NOT_OBSERVABLE", [], aliases),
        }
        if self.scenario not in outcomes:
            raise Phase2BBlocked("UNKNOWN_MOCK_SCENARIO:" + self.scenario)
        return canonical_bytes(outcomes[self.scenario])


def real_backend(config: dict) -> Backend:
    name = config.get("backend")
    if name not in _BACKEND_FACTORIES and isinstance(name, str) and name.startswith("LOCAL_"):
        from .local_vlm.transport import register_local_backends
        register_local_backends(register_backend)
    if name not in _BACKEND_FACTORIES:
        raise Phase2BBlocked("REAL_VLM_BACKEND_NOT_CONFIGURED:" + str(name))
    backend = _BACKEND_FACTORIES[name](config)
    if getattr(backend, "name", None) != name or not callable(getattr(backend, "invoke", None)):
        raise Phase2BBlocked("REGISTERED_BACKEND_CONTRACT_MISMATCH")
    return backend

