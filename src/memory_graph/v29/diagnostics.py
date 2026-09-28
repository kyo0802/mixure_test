"""Trace test9's target evidence chain without using narrative labels."""
from __future__ import annotations

import json

from memory_graph.v27.pipeline import ROOT, write
from .visualization import render_failure_timeline


def test9_failure(folder, trusted_masks: list[dict], events: list[dict]) -> dict:
    task = "test9"
    last = max((m["frame"] for m in trusted_masks if m["trusted"]), default=-1)
    timeline = json.loads((ROOT/"outputs_v26/test9/identity_timeline.json").read_text(encoding="utf-8"))["phone_timeline"]
    candidates = json.loads((ROOT/"outputs_v26/test9/candidate_stream.json").read_text(encoding="utf-8"))["observations"]
    candidates_by_frame = {}
    for c in candidates:
        candidates_by_frame.setdefault(c["frame_index"], []).append(c)
    dense = {}
    for event in events:
        path = folder/"dense_windows"/event["event_id"]/"dense_observations.json"
        if path.exists():
            for row in json.loads(path.read_text(encoding="utf-8"))["rows"]:
                dense[row["frame"]] = row
    by_frame = {r["frame_index"]: r for r in timeline}
    rows = []
    # Densely show the discovered placement window, then preserve every later
    # frozen sample. No future candidate is silently promoted to phone_01.
    frames = sorted({f for f in dense if f >= last} | {f for f in by_frame if f >= last})
    for frame in frames:
        d = dense.get(frame)
        upstream = by_frame.get(frame, {})
        admitted = [c for c in candidates_by_frame.get(frame, []) if c.get("reid_decision") == "CONFIRMED_MATCH"]
        row = {"frame": frame, "time": d["time"] if d else upstream.get("timestamp"),
               "yolo_phone": len(d["yolo_phone_detections"]) if d else upstream.get("raw_phone_count", 0),
               "sam_phone": bool(d and d["sam_phone"]),
               "candidate_phone": len(d["phone_candidates"]) if d else len(candidates_by_frame.get(frame, [])),
               "candidate_admission": [c.get("reid_decision") for c in candidates_by_frame.get(frame, [])],
               "identity_authorized": bool(d and d["identity_authorized"]) or bool(admitted) or
                                      upstream.get("state") == "VISIBLE_TRUSTED",
               "phone_01_state": d["phone_01_state"] if d else upstream.get("state"),
               "anchor_count": len(d["anchors"]) if d else None,
               "candidate_anchors": [a.get("entity_id") or "UNKNOWN_ANCHOR" for a in d["anchors"]] if d else [],
               "placement_event": next((e["event_id"] for e in events if e["start_frame"] <= frame <= e["end_frame"]), None),
               "sam_identity_reason": d["sam_phone"]["identity_authorization"] if d and d["sam_phone"] else None}
        rows.append(row)
    first = None
    for row in rows:
        if row["frame"] <= last or row["identity_authorized"]:
            continue
        if row["sam_phone"]:
            category = "IDENTITY_AUTHORIZATION_FAILURE"
            reason = "SAM mask continues, but frozen identity support/short causal continuity no longer authorizes phone_01"
        elif row["yolo_phone"]:
            category = "SAM_CONTINUITY_FAILURE"
            reason = "YOLO phone is present but trusted SAM target mask is absent"
        else:
            category = "DETECTION_FAILURE" if not row["candidate_phone"] else "CANDIDATE_ADMISSION_FAILURE"
            reason = ("Neither dense YOLO nor SAM2.1 has a phone observation after the final trusted mask; "
                      "candidate admission and identity authorization cannot proceed")
        first = {"frame": row["frame"], "time": row["time"], "category": category, "reason": reason}
        break
    if first is None:
        first = {"frame": None, "time": None, "category": "NO_COVISIBILITY" if events else "PLACEMENT_EVENT_NOT_DETECTED",
                 "reason": "No post-trust break was observed in the examined evidence"}
    result = {"schema": "v29_test9_failure_chain_1", "last_stable_trusted_mask_frame": last,
              "first_failure_point": first, "dense_window_ids": [e["event_id"] for e in events],
              "rows": rows, "later_candidate_merges_authorized": bool(any(c.get("reid_decision") == "CONFIRMED_MATCH" and c["frame_index"] > last for c in candidates)),
              "narrative_used": False}
    write(folder/"test9_failure_timeline.json", result)
    render_failure_timeline(rows[:80], first, folder/"test9_failure_timeline.png")
    return result
