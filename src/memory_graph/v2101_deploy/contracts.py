"""Frozen V2945 response contract adapters for isolated v2.10.1 smoke calls."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


EVENT_TYPES = (
    "STATIC", "PICKED_UP", "CARRIED_OR_HELD", "PLACED_OR_PUT_DOWN",
    "BECAME_OCCLUDED", "REAPPEARED", "NO_CLEAR_INTERACTION", "UNCERTAIN",
)
RELATIONS = ("ON", "INSIDE", "BEHIND", "OCCLUDED_BY", "NEAR", "HELD_BY", "NONE", "UNCERTAIN")
FIELDS = (
    "event_type", "interaction_anchor", "released", "target_visible_after",
    "final_relation", "final_relation_anchor", "confidence",
)


def event_json_schema(markers: Sequence[str]) -> dict[str, Any]:
    anchors = list(dict.fromkeys([*markers, "NONE", "UNCERTAIN"]))
    return {
        "type": "object",
        "properties": {
            "event_type": {"type": "string", "enum": list(EVENT_TYPES)},
            "interaction_anchor": {"type": "string", "enum": anchors},
            "released": {"type": "string", "enum": ["YES", "NO", "UNCERTAIN"]},
            "target_visible_after": {"type": "string", "enum": ["YES", "PARTIAL", "NO", "UNCERTAIN"]},
            "final_relation": {"type": "string", "enum": list(RELATIONS)},
            "final_relation_anchor": {"type": "string", "enum": anchors},
            "confidence": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
        },
        "required": list(FIELDS),
        "additionalProperties": False,
    }


def schema_sha256(markers: Sequence[str]) -> str:
    body = json.dumps(event_json_schema(markers), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def schema_valid(markers: Sequence[str], value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != set(FIELDS):
        return False
    schema = event_json_schema(markers)["properties"]
    return all(isinstance(value[k], str) and value[k] in schema[k]["enum"] for k in FIELDS)
