"""Single mask authorization and resolvable artifact provenance."""
from __future__ import annotations

from pathlib import Path
import hashlib
from typing import Any


TRUSTED_IDENTITY_STATES = {"OBSERVED", "VISIBLE", "VISIBLE_TRUSTED", "MATCHED", "IDENTITY_CONFIRMED"}


def authorize_trusted_mask(*, identity_state: str, continuity_ok: bool, drift_ok: bool,
                           mask_quality_ok: bool, detector_supported: bool = True,
                           detector_support_required: bool = False, continuity_break: bool = False,
                           reacquisition_authorized: bool = False,
                           authorization_id: str | None = None) -> dict[str, Any]:
    checks = {
        "identity_state": identity_state in TRUSTED_IDENTITY_STATES,
        "continuity": bool(continuity_ok), "drift_conflict": bool(drift_ok),
        "mask_quality": bool(mask_quality_ok),
        "same_frame_detector": (not detector_support_required or bool(detector_supported)),
        "continuity_break": (not continuity_break or bool(reacquisition_authorized and authorization_id)),
    }
    approved = all(checks.values())
    return {"trusted": approved, "decision": "AUTHORIZED" if approved else "REJECTED",
            "checks": checks, "authorization_id": authorization_id,
            "reason": "all shared authorization checks passed" if approved else
                      ", ".join(name for name, passed in checks.items() if not passed)}


def make_mask_reference(*, video_id: str, frame: int, object_id: str, event_id: str,
                        artifact_path: str | Path, authorization: dict[str, Any],
                        provenance: str) -> dict[str, Any]:
    return {"video_id": video_id, "frame": int(frame), "object_id": object_id,
            "event_id": event_id, "artifact_path": str(artifact_path),
            "trusted": authorization.get("trusted") is True,
            "authorization": authorization, "provenance": provenance}


def validate_mask_reference(reference: dict[str, Any], *, video_id: str, frame: int,
                            object_id: str, event_id: str, root: str | Path | None = None) -> dict[str, Any]:
    mismatches = [key for key, expected in (("video_id", video_id), ("frame", frame),
                  ("object_id", object_id), ("event_id", event_id))
                  if reference.get(key) != expected]
    path = Path(reference.get("artifact_path", ""))
    base = Path(root).resolve() if root is not None else None
    if base is not None and not path.is_absolute():
        path = base / path
    if root is not None:
        try:
            path.resolve().relative_to(base)
        except (OSError, ValueError):
            mismatches.append("artifact_path_outside_root")
    if not path.is_file():
        mismatches.append("artifact_missing")
    else:
        try:
            import cv2
            decoded = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if decoded is None or decoded.size == 0:
                mismatches.append("artifact_decode_failed")
        except Exception:
            mismatches.append("artifact_decode_failed")
    if not reference.get("provenance") or not isinstance(reference.get("authorization"), dict):
        mismatches.append("provenance_missing")
    authorization = reference.get("authorization")
    if isinstance(authorization, dict) and reference.get("trusted") is not (authorization.get("trusted") is True):
        mismatches.append("authorization_state_mismatch")
    expected_hash = reference.get("artifact_sha256")
    if expected_hash and path.is_file():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected_hash:
            mismatches.append("artifact_hash_mismatch")
    return {"valid": not mismatches, "mismatches": mismatches,
            "trusted": reference.get("trusted") is True and not mismatches}
