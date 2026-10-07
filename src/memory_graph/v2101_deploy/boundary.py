"""Non-authoritative candidate artifact contract for v2.10.1 smoke tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


AUTHORITY = "NONE_DEPLOYMENT_EXPERIMENT_ONLY"
ARTIFACT_ROOT = Path("artifacts/v2.10.1").resolve()


def make_candidate_record(
    *, model_id: str, model_revision: str, event_id: str, raw_response: str,
    completed: bool, json_valid: bool, schema_valid: bool,
    semantic_validator_valid: bool | None, metrics: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a detached raw-candidate record; accepts no identity/memory object."""
    return {
        "authority": AUTHORITY,
        "model_id": model_id,
        "model_revision": model_revision,
        "event_id": event_id,
        "raw_response": raw_response,
        "request_completed": bool(completed),
        "json_valid": bool(json_valid),
        "schema_valid": bool(schema_valid),
        "semantic_validator_valid": semantic_validator_valid,
        "metrics": dict(metrics),
    }


def require_v2101_artifact_path(path: str | Path) -> Path:
    """Reject output paths outside the new experiment namespace."""
    candidate = Path(path).resolve()
    try:
        candidate.relative_to(ARTIFACT_ROOT)
    except ValueError as exc:
        raise ValueError("v2.10.1 experiment output must stay under artifacts/v2.10.1") from exc
    return candidate
