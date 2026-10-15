"""Strict parsing, schema validation, citation checks and semantic guards."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from .common import Phase2BBlocked, repository_root


def schema() -> dict:
    path = Path(__file__).parent / "contracts/prediction_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def parse_raw(raw: bytes, *, max_bytes: int = 256_000) -> dict:
    if len(raw) > max_bytes:
        raise Phase2BBlocked("MODEL_OUTPUT_SIZE_LIMIT")
    def pairs(rows):
        out = {}
        for key, value in rows:
            if key in out:
                raise Phase2BBlocked("DUPLICATE_MODEL_OUTPUT_KEY:" + key)
            out[key] = value
        return out
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda token: (_ for _ in ()).throw(Phase2BBlocked("NONFINITE_MODEL_OUTPUT:" + token)))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise Phase2BBlocked("MALFORMED_MODEL_OUTPUT:" + str(error)) from error
    if not isinstance(value, dict):
        raise Phase2BBlocked("MODEL_OUTPUT_OBJECT_REQUIRED")
    return value


def validate_prediction(prediction: dict, supplied_aliases: list[str]) -> dict:
    structural: list[str] = []
    semantic: list[str] = []
    validator = jsonschema.Draft202012Validator(schema())
    for error in sorted(validator.iter_errors(prediction), key=lambda e: list(e.absolute_path)):
        structural.append(f"/{'/'.join(map(str, error.absolute_path))}:{error.message}")
    if structural:
        return {"valid": False, "structural_errors": structural, "citation_errors": [], "semantic_errors": []}
    supplied = set(supplied_aliases)
    order = {alias: index for index, alias in enumerate(supplied_aliases)}
    citations: list[str] = []
    for alias in prediction["window_cited_frame_aliases"]:
        if alias not in supplied:
            citations.append("OUT_OF_PAYLOAD_WINDOW_CITATION:" + alias)
    event_ids = [event["event_id"] for event in prediction["events"]]
    if len(event_ids) != len(set(event_ids)):
        semantic.append("DUPLICATE_EVENT_ID")
    for event in prediction["events"]:
        for alias in event["cited_frame_aliases"]:
            if alias not in supplied:
                citations.append(f"OUT_OF_PAYLOAD_CITATION:{event['event_id']}:{alias}")
        timing = event["timing"]
        timed = []
        if timing["status"] == "EXACT_SUPPLIED_FRAME":
            timed = [timing["frame_alias"]]
        elif timing["status"] == "BOUNDED_SUPPLIED_FRAMES":
            timed = [timing["start_frame_alias"], timing["end_frame_alias"]]
            if all(alias in order for alias in timed) and order[timed[0]] > order[timed[1]]:
                semantic.append(f"REVERSED_TIME_INTERVAL:{event['event_id']}")
        for alias in timed:
            if alias not in supplied:
                citations.append(f"OUT_OF_PAYLOAD_TIMING:{event['event_id']}:{alias}")
        for key in ("before_state", "after_state"):
            state = event[key]
            alias = state["supporting_frame_alias"]
            if state["state"] == "STATE_UNKNOWN" and alias is not None:
                semantic.append(f"UNKNOWN_STATE_HAS_SUPPORT:{event['event_id']}:{key}")
            if state["state"] != "STATE_UNKNOWN" and alias is None:
                semantic.append(f"KNOWN_STATE_MISSING_SUPPORT:{event['event_id']}:{key}")
            if alias is not None and alias not in supplied:
                citations.append(f"OUT_OF_PAYLOAD_STATE:{event['event_id']}:{alias}")
    last = prediction["last_directly_supported_state"]
    if last["state"] == "STATE_UNKNOWN" and last["supporting_frame_alias"] is not None:
        semantic.append("UNKNOWN_LAST_STATE_HAS_SUPPORT")
    if last["state"] != "STATE_UNKNOWN" and last["supporting_frame_alias"] is None:
        semantic.append("KNOWN_LAST_STATE_MISSING_SUPPORT")
    if last["supporting_frame_alias"] is not None and last["supporting_frame_alias"] not in supplied:
        citations.append("OUT_OF_PAYLOAD_LAST_STATE")
    if prediction["window_outcome"] == "CONFIRMED_EVENTS" and not prediction["events"]:
        semantic.append("CONFIRMED_EVENTS_REQUIRES_EVENT")
    if prediction["window_outcome"] != "CONFIRMED_EVENTS" and prediction["events"]:
        semantic.append("NON_CONFIRMED_OUTCOME_REQUIRES_EMPTY_EVENTS")
    return {"valid": not structural and not citations and not semantic,
            "structural_errors": structural, "citation_errors": citations, "semantic_errors": semantic}


def parse_and_validate(raw: bytes, supplied_aliases: list[str]) -> tuple[dict, dict]:
    prediction = parse_raw(raw)
    result = validate_prediction(prediction, supplied_aliases)
    if not result["valid"]:
        raise Phase2BBlocked("MODEL_OUTPUT_VALIDATION_FAILED:" + json.dumps(result, sort_keys=True))
    return prediction, result

