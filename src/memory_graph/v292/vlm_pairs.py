"""Pair-specific evidence construction and strict observable-fact grounding."""
from __future__ import annotations

from typing import Any


FACT_KEYS = (
    "target_visible_before", "target_visible_during", "target_visible_after",
    "target_moves_toward_anchor", "target_contacts_or_crosses_anchor_boundary",
    "target_visible_area_decreases", "anchor_remains_visible",
    "hand_or_person_releases_target", "target_stays_after_release",
)
VALUES = {"YES", "NO", "UNCERTAIN"}


def build_pair_request(*, video_id: str, event: dict, target_id: str,
                       anchor: dict, rows: list[dict]) -> dict[str, Any]:
    anchor_key = anchor["anchor_key"]
    peak = int(event["peak_frame"])
    tolerance = max(1, int(event.get("during_tolerance_frames", 3)))
    during_start, during_end = max(int(event["start_frame"]), peak-tolerance), min(int(event["end_frame"]), peak+tolerance)
    phase_windows = {"BEFORE": [int(event["start_frame"]), during_start-1],
                     "DURING": [during_start, during_end],
                     "AFTER": [during_end+1, int(event["end_frame"])]}
    evidence = {}
    for phase, (low, high) in phase_windows.items():
        eligible = []
        for row in rows:
            frame = int(row["frame"])
            if not low <= frame <= high or row.get("target_authorized") is not True:
                continue
            matched = next((a for a in row.get("anchors", []) if a.get("anchor_key") == anchor_key), None)
            if matched and matched.get("visible") is not False:
                eligible.append((abs(frame - (low+high)/2), frame, matched, row))
        if eligible:
            _, frame, matched, selected_row = min(eligible)
            evidence[phase] = {"frame": frame, "target_id": target_id, "target_bbox": selected_row.get("target_bbox"),
                               "anchor_key": anchor_key, "anchor_bbox": matched["bbox"],
                               "image_path": selected_row.get("image_path"),
                               "target_mask_path": selected_row.get("target_mask_path"),
                               "authorization_id": selected_row.get("authorization_id")}
    if set(evidence) != {"BEFORE", "DURING", "AFTER"}:
        missing = sorted({"BEFORE", "DURING", "AFTER"} - set(evidence))
        return {"video_id": video_id, "target_id": target_id, "anchor_key": anchor_key,
                "event_id": event["event_id"], "status": "EVIDENCE_UNAVAILABLE",
                "missing_phases": missing, "evidence": evidence}
    return {"video_id": video_id, "target_id": target_id, "anchor_key": anchor_key,
            "event_id": event["event_id"], "status": "READY", "evidence": evidence,
            "visual_policy": "one target and one queried anchor highlighted; all other anchors hidden/deemphasized"}


def validate_answer(request: dict[str, Any], answer: dict[str, Any] | None) -> dict[str, Any]:
    if request.get("status") != "READY":
        return {"status": "EVIDENCE_UNAVAILABLE", "grounding_valid": False,
                "reason": "pair evidence is incomplete"}
    if not isinstance(answer, dict) or any(answer.get(key) not in VALUES for key in FACT_KEYS):
        return {"status": "UNUSABLE_GROUNDING", "grounding_valid": False,
                "reason": "observable schema is incomplete or invalid"}
    expected = {"subject_reference": request["target_id"], "anchor_reference": request["anchor_key"],
                "event_reference": request["event_id"]}
    if any(answer.get(key) != value for key, value in expected.items()):
        return {"status": "UNUSABLE_GROUNDING", "grounding_valid": False,
                "reason": "answer subject/pair/event does not match the query"}
    frames = answer.get("evidence_frames")
    if not isinstance(frames, dict) or any(frames.get(phase) != pair["frame"]
                                          for phase, pair in request["evidence"].items()):
        return {"status": "UNUSABLE_GROUNDING", "grounding_valid": False,
                "reason": "answer evidence frames do not match pair-grounded inputs"}
    if any(not request["evidence"][phase].get("authorization_id") for phase in request["evidence"]):
        return {"status": "UNUSABLE_GROUNDING", "grounding_valid": False,
                "reason": "target identity is not authorized in all cited phases"}
    return {"status": "GROUNDED", "grounding_valid": True, "target_id": request["target_id"],
            "anchor_key": request["anchor_key"], "event_id": request["event_id"],
            "evidence_frames": frames}


def parse_observable(raw: str) -> dict[str, Any]:
    import json, re
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON observable facts")
    value = json.loads(match.group(0))
    if any(value.get(key) not in VALUES for key in FACT_KEYS):
        raise ValueError("Missing or invalid observable fact")
    return value


def prompt_for_pair(request: dict[str, Any], anchor_label: str) -> str:
    return ("Inspect exactly three frames in BEFORE, DURING, AFTER order. Green box and label identify "
            f"{request['target_id']}; magenta box and label identify {request['anchor_key']} ({anchor_label}). "
            "Report visible facts only. Do not infer hidden objects or choose a physical relation. "
            "Return JSON with subject_reference, anchor_reference, event_reference, evidence_frames "
            "and these YES/NO/UNCERTAIN fields: " + ", ".join(FACT_KEYS) +
            ". Also include evidence_summary and uncertainty.")
