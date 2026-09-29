"""Release checks for canonical V2.9.2 predictions and frozen artifacts."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .memory import validate_memory_views


HISTORICAL_TOKENS = tuple(f"outputs_v{x}" for x in ("21", "22", "23", "24", "241", "25", "25_rerun",
                                                       "26", "261", "262", "27", "28", "29", "291"))
_HISTORICAL_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:outputs_v25_rerun|outputs_v241|outputs_v291|outputs_v262|outputs_v261|"
    r"outputs_v21|outputs_v22|outputs_v23|outputs_v24|outputs_v25|outputs_v26|outputs_v27|"
    r"outputs_v28|outputs_v29)(?![A-Za-z0-9_])"
)
REQUIRED_CONSISTENCY_FIELDS = ("pipeline_version", "canonical_config_sha256", "model_configuration",
                              "identity_policy_version", "vlm_prompt_version", "physical_gate_version",
                              "memory_schema_version")


def sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path, default: Any = None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def has_historical_prediction_reference(value: str) -> bool:
    """Match an exact historical output directory token, excluding outputs_v292."""
    return _HISTORICAL_PATH_PATTERN.search(value) is not None


def artifact_hashes(root: str | Path, exclude: set[str] | None = None) -> dict[str, str]:
    base = Path(root)
    excluded = exclude or set()
    return {path.relative_to(base).as_posix(): sha256(path)
            for path in sorted(base.rglob("*")) if path.is_file()
            and path.relative_to(base).as_posix() not in excluded
            and not any(part.startswith(".") for part in path.relative_to(base).parts)}


def verify_artifact_hashes(root: str | Path, expected: dict[str, str]) -> dict[str, Any]:
    base = Path(root)
    errors = []
    for rel, digest in expected.items():
        path = base / Path(rel)
        if not path.is_file():
            errors.append(f"missing artifact: {rel}")
        elif sha256(path) != digest:
            errors.append(f"hash mismatch: {rel}")
    return {"valid": not errors, "errors": errors, "checked": len(expected)}


def validate_video_artifacts(video_root: str | Path) -> dict[str, Any]:
    root = Path(video_root)
    errors: list[str] = []
    manifest = _load(root / "run_manifest.json", {}) or {}
    for field in REQUIRED_CONSISTENCY_FIELDS:
        if not manifest.get(field):
            errors.append(f"run manifest missing {field}")
    for rel in ("identity/identity_timeline.json", "identity/identity_authorizations.json",
                "segmentation/mask_authorization.json", "segmentation/mask_references.json",
                "events/recovery_episodes.json", "physical/relation_decisions.json",
                "memory/memory_events.json", "memory/temporal_memory.json",
                "memory/lifetime_memory.json", "search/search_candidates.json"):
        if not (root / rel).is_file():
            errors.append(f"missing required artifact: {rel}")
    identity = _load(root / "identity/identity_timeline.json", {}) or {}
    auths = _load(root / "identity/identity_authorizations.json", []) or []
    auth_by_id = {a.get("authorization_id"): a for a in auths}
    for row in identity.get("phone_timeline", []):
        if row.get("state") == "MATCHED":
            auth = auth_by_id.get(row.get("authorization_id"))
            if not auth or auth.get("decision") != "CONFIRMED_MATCH" or auth.get("source_guard_decision") != "V2.6_IDENTITY_GUARD":
                errors.append(f"unauthorized MATCHED at frame {row.get('frame_index')}")
        frame = int(row.get("frame_index", 0))
        stamp = row.get("timestamp")
        if frame and (stamp is None or float(stamp) == 0):
            errors.append(f"placeholder timestamp at frame {frame}")
    refs = _load(root / "segmentation/mask_references.json", []) or []
    from .masks import validate_mask_reference
    for ref in refs:
        check = validate_mask_reference(ref, video_id=root.name, frame=ref.get("frame"),
                    object_id=ref.get("object_id"), event_id=ref.get("event_id"), root=root)
        if not check["valid"]:
            errors.append(f"invalid mask reference {ref.get('artifact_path')}: {check['mismatches']}")
    anchors = _load(root / "anchors/event_local_anchors.json", []) or []
    keys = [a.get("anchor_key") for a in anchors]
    if len(keys) != len(set(keys)) or any(not k or k.count("::") != 2 for k in keys):
        errors.append("event-local anchor namespace collision or malformed key")
    grounding = _load(root / "vlm/grounding_validation.json", []) or []
    for row in grounding:
        if row.get("status") == "GROUNDED" and not all(row.get(k) for k in ("target_id", "anchor_key", "event_id", "evidence_frames")):
            errors.append("grounded VLM result lacks pair references")
    bundle = {name: _load(root / f"memory/{name}.json", {}) or {} for name in
              ("memory_events", "temporal_memory", "lifetime_memory", "search")}
    errors.extend(validate_memory_views(bundle))
    for json_path in root.rglob("*.json"):
        if json_path.name in {"run_manifest.json", "artifact_manifest.json"}:
            continue
        payload = _load(json_path)
        for value in _strings(payload):
            if has_historical_prediction_reference(value):
                errors.append(f"historical prediction reference in {json_path.relative_to(root)}")
                break
    return {"video_id": root.name, "valid": not errors, "errors": errors}


def validate_canonical_bundle(output_root: str | Path, video_ids: list[str]) -> dict[str, Any]:
    root = Path(output_root)
    canonical = _load(root / "canonical_config.json", {}) or {}
    records, errors = [], []
    for video_id in video_ids:
        video = validate_video_artifacts(root / video_id)
        records.append(video)
        errors.extend(f"{video_id}: {error}" for error in video["errors"])
    manifests = [_load(root / video_id / "run_manifest.json", {}) or {} for video_id in video_ids]
    for field in REQUIRED_CONSISTENCY_FIELDS:
        observed = {json.dumps(m.get(field), sort_keys=True) for m in manifests}
        if len(observed) != 1 or (observed == {"null"}):
            errors.append(f"videos disagree on {field}")
    if canonical and any(m.get("canonical_config_sha256") != canonical.get("canonical_config_sha256") for m in manifests):
        errors.append("video run manifest config hash differs from canonical config")
    return {"valid": not errors, "videos": records, "errors": errors,
            "video_count": len(video_ids), "expected_video_count": 9}
