"""One authoritative memory-event store with derived temporal/lifetime/search views."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


class MemoryEventStore:
    def __init__(self, video_id: str, fps: float):
        self.video_id, self.fps = video_id, float(fps)
        self.observations: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self._ids: set[str] = set()

    def add_observation(self, row: dict[str, Any]) -> None:
        frame = int(row["frame"])
        timestamp = float(row.get("time", frame / max(self.fps, 1e-9)))
        if frame < 0 or timestamp < 0 or (frame > 0 and timestamp == 0):
            raise ValueError("Observation has an invalid frame-derived timestamp")
        required = ("observation_id", "entity_id", "status", "provenance")
        if any(not row.get(key) for key in required):
            raise ValueError("Observation is missing identity/status/provenance")
        self.observations.append({**deepcopy(row), "video_id": self.video_id, "time": timestamp})

    def add_event(self, row: dict[str, Any]) -> None:
        event_id = row.get("event_id")
        if not event_id or event_id in self._ids:
            raise ValueError("Memory event requires a unique event_id")
        frame = int(row["frame"])
        timestamp = float(row.get("time", frame / max(self.fps, 1e-9)))
        if frame > 0 and timestamp == 0:
            raise ValueError("Non-zero frame memory event cannot use placeholder time zero")
        if not row.get("provenance"):
            raise ValueError("Memory event must round-trip to source evidence")
        self.events.append({**deepcopy(row), "video_id": self.video_id, "time": timestamp})
        self._ids.add(event_id)

    def derive(self, identity_timeline: list[dict[str, Any]], search: dict[str, Any] | None = None) -> dict[str, Any]:
        ordered = sorted(self.events, key=lambda x: (x["frame"], x["event_id"]))
        relations = [e for e in ordered if e.get("event_type") in {"PHYSICAL_RELATION", "IMAGE_CONTEXT_RELATION"}]
        trusted_events = [e for e in ordered if e.get("trusted") is True]
        episodes = []
        latest_trusted_frame = max((int(e["frame"]) for e in trusted_events), default=-1)
        for i, event in enumerate(relations, 1):
            status = event.get("status", "CANDIDATE")
            if event.get("trusted"):
                status = "LAST_TRUSTED" if int(event["frame"]) == latest_trusted_frame else "STALE"
            elif status not in {"CANDIDATE", "UNCERTAIN", "REJECTED"}:
                status = "UNCERTAIN"
            end_frame = int(event.get("end_frame", event["frame"]))
            start_frame = int(event.get("start_frame", event["frame"]))
            start_time = float(event.get("start_time", start_frame / max(self.fps, 1e-9)))
            end_time = float(event.get("end_time", event["time"]))
            episodes.append({"episode_id": f"ME{i:04d}", "memory_event_id": event["event_id"],
                "video_id": self.video_id, "start_frame": start_frame, "end_frame": end_frame,
                "start_time": start_time, "last_confirmed_time": end_time,
                "last_supported_frame": end_frame,
                "last_supported_time": end_time,
                "source_event_id": event.get("source_event_id", event["event_id"]),
                "supporting_observation_ids": list(event.get("supporting_observation_ids", [])),
                "status": status, "decision": event.get("decision", "CANDIDATE"),
                "kind": "PHYSICAL" if event["event_type"] == "PHYSICAL_RELATION" else "IMAGE_CONTEXT",
                "subject": event.get("subject", "phone_01"),
                "relation": event.get("relation", "TRUSTED_ANCHOR_CONTEXT"),
                "object": event.get("object", "unknown"),
                "source": list(event["provenance"]), "source_snapshots": [],
                "provenance": list(event["provenance"])})
        event_view = [{"event_id": e["event_id"], "event_type": e["event_type"],
                       "frame": e["frame"], "time": e["time"], "provenance": list(e["provenance"])}
                      for e in ordered]
        return {"observations": deepcopy(self.observations), "relation_episodes": episodes,
                "memory_events": deepcopy(ordered),
                "temporal_memory": {"video_id": self.video_id, "events": event_view,
                                    "episodes": deepcopy(episodes), "identity_timeline": deepcopy(identity_timeline)},
                "lifetime_memory": {"video_id": self.video_id, "episodes": deepcopy(episodes)},
                "search": {"video_id": self.video_id, "source_event_ids": [e["memory_event_id"] for e in episodes],
                           "plan": deepcopy(search or {})}}


def validate_memory_views(bundle: dict[str, Any]) -> list[str]:
    errors = []
    source_ids = {e["event_id"] for e in bundle.get("memory_events", [])}
    for view_name in ("temporal_memory", "lifetime_memory"):
        view = bundle.get(view_name, {})
        for episode in view.get("episodes", []):
            if episode.get("memory_event_id") not in source_ids:
                errors.append(f"{view_name}: orphan episode {episode.get('episode_id')}")
    search_ids = set(bundle.get("search", {}).get("source_event_ids", []))
    if not search_ids.issubset(source_ids):
        errors.append("search: provenance does not round-trip to memory events")
    return errors
