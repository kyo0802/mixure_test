"""Opaque model-visible contract with structural and serialized leakage checks."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import jsonschema

from .common import Phase2BBlocked, canonical_bytes, digest, file_sha256, repository_root, safe_join


VISIBLE_KEYS = {"schema_version", "request_id", "target", "ontology", "representation", "media", "instructions", "output_contract"}
FORBIDDEN_KEYS = {
    "annotation_item_id", "original_pack_ids", "source_video_identifier", "source_frame_index", "image_path",
    "selected_local_candidate_id", "bbox", "events", "window_outcome", "event_list_exhaustiveness", "evaluation",
    "human_rationale", "annotator_id", "reviewer_id", "challenge_tags", "physical_gt", "gt", "identity_guard",
    "dino", "lightglue", "exhaustive_review_readiness", "local_candidate_id", "original_response_valid",
}
FORBIDDEN_PATTERNS = [
    re.compile(r"PT2A_[0-9a-f]{16}", re.I),
    re.compile(r"test[0-9]+(?:__W[0-9]+)?", re.I),
    re.compile(r"(?:^|[\\/])artifacts[\\/]", re.I),
    re.compile(r"(?:^|[\\/])val_set[\\/]", re.I),
    re.compile(r"annotat(?:or|er)|reviewer", re.I),
]


def opaque_id(secret: str, purpose: str, value: str) -> str:
    return hashlib.sha256(f"PASS_T_PHASE2B|{secret}|{purpose}|{value}".encode("utf-8")).hexdigest()[:20]


def _walk_keys(value: object) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))
    return keys


def inspect_payload(payload: dict, private_mapping: dict | None = None) -> dict:
    errors: list[str] = []
    schema_path = Path(__file__).parent / "contracts/model_visible_payload_v1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for error in sorted(jsonschema.Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.absolute_path)):
        errors.append("SCHEMA:/" + "/".join(map(str, error.absolute_path)) + ":" + error.message)
    if set(payload) != VISIBLE_KEYS:
        errors.append("TOP_LEVEL_ALLOWLIST_MISMATCH")
    keys = set(_walk_keys(payload))
    overlap = sorted(keys & FORBIDDEN_KEYS)
    if overlap:
        errors.append("FORBIDDEN_KEYS:" + ",".join(overlap))
    raw = canonical_bytes(payload).decode("utf-8")
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(raw):
            errors.append("FORBIDDEN_SERIALIZED_PATTERN:" + pattern.pattern)
    if private_mapping:
        for value in _sensitive_values(private_mapping):
            if len(value) >= 4 and value in raw:
                errors.append("PRIVATE_MAPPING_VALUE_LEAK")
                break
    return {"safe": not errors, "errors": errors, "serialized_sha256": digest(raw.encode("utf-8")), "serialized_bytes": len(raw.encode("utf-8"))}


def _sensitive_values(value: object) -> set[str]:
    out: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key not in {"opaque_alias", "content_sha256"} and isinstance(child, (str, int, float)):
                out.add(str(child))
            out.update(_sensitive_values(child))
    elif isinstance(value, list):
        for child in value:
            out.update(_sensitive_values(child))
    return out


def source_contract(item: dict, *, secret: str, reference_policy: str = "NONE",
                    approved_neutral_reference: dict | None = None) -> dict:
    if reference_policy not in {"NONE", "AUTHORIZED_STATIC_REFERENCE", "APPROVED_NEUTRAL_LOCALIZATION"}:
        raise Phase2BBlocked("INVALID_REFERENCE_POLICY")
    root = repository_root()
    window = opaque_id(secret, "window", item["annotation_item_id"])
    frames = []
    for position, row in enumerate(item["visual"]["frames"], start=1):
        path = safe_join(root, row["image_path"])
        if file_sha256(path) != row["sha256"]:
            raise Phase2BBlocked("AUTHORIZED_FRAME_HASH_MISMATCH")
        frames.append({
            "opaque_alias": f"F{position:04d}",
            "private_source_frame_index": row["source_frame_index"],
            "private_source_timestamp_s": row["source_timestamp_s"],
            "private_path": row["image_path"],
            "content_sha256": row["sha256"],
        })
    refs = []
    reference_rows = []
    if reference_policy == "AUTHORIZED_STATIC_REFERENCE":
        reference_rows = item["visual"].get("references", [])
        if not reference_rows:
            raise Phase2BBlocked("AUTHORIZED_STATIC_REFERENCE_UNAVAILABLE")
    elif reference_policy == "APPROVED_NEUTRAL_LOCALIZATION":
        if (not isinstance(approved_neutral_reference, dict)
                or approved_neutral_reference.get("provenance") != "APPROVED_NEUTRAL_LOCALIZATION"
                or approved_neutral_reference.get("event_specific") is not False
                or not isinstance(approved_neutral_reference.get("references"), list)
                or not approved_neutral_reference["references"]):
            raise Phase2BBlocked("NEUTRAL_LOCALIZATION_REFERENCE_NOT_CONFIGURED")
        reference_rows = approved_neutral_reference["references"]
    if reference_rows:
        for position, row in enumerate(reference_rows, start=1):
            path = safe_join(root, row["image_path"])
            if file_sha256(path) != row["sha256"]:
                raise Phase2BBlocked("AUTHORIZED_REFERENCE_HASH_MISMATCH")
            refs.append({
                "opaque_alias": f"R{position:02d}",
                "private_source_frame_index": row["source_frame_index"],
                "private_source_timestamp_s": row["source_timestamp_s"],
                "private_path": row["image_path"],
                "content_sha256": row["sha256"],
                "role": "STATIC_TARGET_REFERENCE_ONLY",
            })
    return {
        "private_schema_version": "PASS_T_PHASE2B_SOURCE_CONTRACT_V1",
        "private_annotation_item_id": item["annotation_item_id"],
        "opaque_window_id": "W_" + window,
        "frames": frames,
        "references": refs,
        "width": item["visual"]["width"],
        "height": item["visual"]["height"],
        "reference_policy": reference_policy,
    }


def build_payload(source: dict, representation: dict, prompt_text: str) -> dict:
    media = []
    for row in representation["model_media"]:
        media.append({key: row[key] for key in ("media_id", "media_type", "content_sha256", "supplied_frame_aliases")})
    payload = {
        "schema_version": "PASS_T_PHASE2B_MODEL_PAYLOAD_V1",
        "request_id": "REQ_" + source["opaque_window_id"][2:],
        "target": {"opaque_id": "TARGET_A", "description": "the authorized target object"},
        "ontology": {
            "event_types": ["PICKUP", "PLACEMENT"],
            "window_outcomes": ["CONFIRMED_EVENTS", "NO_CONFIRMED_EVENT", "INSUFFICIENT_EVIDENCE", "TARGET_NOT_OBSERVABLE"],
        },
        "representation": representation["representation"],
        "media": media,
        "instructions": prompt_text,
        "output_contract": "PASS_T_PHASE2B_PREDICTION_V1",
    }
    inspection = inspect_payload(payload, source)
    if not inspection["safe"]:
        raise Phase2BBlocked("MODEL_PAYLOAD_LEAKAGE:" + ";".join(inspection["errors"]))
    return payload


def serialized_request(payload: dict) -> bytes:
    inspection = inspect_payload(payload)
    if not inspection["safe"]:
        raise Phase2BBlocked("UNSAFE_MODEL_REQUEST")
    return canonical_bytes(payload)

