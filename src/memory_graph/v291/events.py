"""Label blind event-state transitions; a first loss never suppresses later events."""
from __future__ import annotations


TRUSTED = {"VISIBLE_TRUSTED", "MATCHED", "VISIBLE_PROPAGATED"}


def detect_multi_events(task: str, identity_rows: list[dict], candidate_rows: list[dict],
                        placement_events: list[dict], fps: float, last_frame: int,
                        max_events: int = 3) -> list[dict]:
    timeline = sorted(identity_rows, key=lambda r: r["frame_index"])
    confirmed = {}
    for row in candidate_rows:
        if row.get("reid_decision") == "CONFIRMED_MATCH":
            confirmed.setdefault(row["frame_index"], []).append(row)
    raw = []
    last_reconfirm = None
    for i, row in enumerate(timeline):
        frame, state = row["frame_index"], row.get("state")
        prior = timeline[i-1] if i else None
        if state == "UNOBSERVED" and prior and prior.get("state") in TRUSTED | {"VISIBLE_PROPAGATED"}:
            kind = "SECOND_LOSS_EVENT" if last_reconfirm is not None and frame > last_reconfirm else "LOSS_EVENT"
            raw.append({"event_type": kind, "peak_frame": frame, "evidence": "trusted identity timeline transitions to UNOBSERVED",
                        "source": "frozen_identity_timeline", "priority": 5 if kind == "SECOND_LOSS_EVENT" else 1})
        if confirmed.get(frame):
            raw.append({"event_type": "RECONFIRM_EVENT", "peak_frame": frame,
                        "evidence": "frozen V2.6 Identity Guard CONFIRMED_MATCH", "source": "candidate_stream",
                        "candidate_ids": [r.get("candidate_id") for r in confirmed[frame]], "priority": 6})
            last_reconfirm = frame
        elif (state in TRUSTED and prior and prior.get("state") == "UNOBSERVED"):
            raw.append({"event_type": "RECONFIRM_EVENT", "peak_frame": frame,
                        "evidence": "trusted identity timeline returns after UNOBSERVED",
                        "source": "frozen_identity_timeline", "priority": 6})
            last_reconfirm = frame
    for event in placement_events:
        cues = event.get("cues", {})
        if cues.get("motion_slowdown") and (cues.get("anchor_approach") or cues.get("overlap_increase")):
            raw.append({"event_type": "POSSIBLE_PUTDOWN", "peak_frame": event["peak_frame"],
                        "evidence": event.get("reason"), "source": "v29_placement_detector", "priority": 3,
                        "base_event_id": event["event_id"]})
        if cues.get("overlap_increase") and cues.get("visibility_loss"):
            raw.append({"event_type": "OCCLUSION_EVENT", "peak_frame": event["peak_frame"],
                        "evidence": event.get("reason"), "source": "v29_placement_detector", "priority": 4,
                        "base_event_id": event["event_id"]})
    # Remove same-frame duplicates, retaining the semantically richer transition.
    dedup = {}
    for event in raw:
        key = (event["event_type"], event["peak_frame"])
        if key not in dedup or event["priority"] > dedup[key]["priority"]:
            dedup[key] = event
    # Select high-value transitions first. Within the same event class and
    # priority, prefer the later event so the first loss cannot dominate.
    prioritized = sorted(dedup.values(), key=lambda e: (-e["priority"], -e["peak_frame"], e["event_type"]))
    chosen = []
    for item in prioritized:
        if any(item["event_type"] == x["event_type"] and
               abs(item["peak_frame"]-x["peak_frame"]) < round(.75*fps) for x in chosen):
            continue
        peak = item["peak_frame"]
        radius = round(1.5*fps)
        event = {**item, "event_id": "", "target": "phone_01",
                 "start_frame": max(0, peak-radius), "end_frame": min(last_frame, peak+radius),
                 "start_time": max(0, peak-radius)/fps, "end_time": min(last_frame, peak+radius)/fps,
                 "candidate_anchors": [], "provenance": [item["source"]]}
        chosen.append(event)
        if len(chosen) == max_events:
            break
    chosen.sort(key=lambda e: e["peak_frame"])
    for number, event in enumerate(chosen, 1):
        event["event_id"] = f"V291E{number:02d}"
    return chosen
