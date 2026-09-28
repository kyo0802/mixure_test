"""Derive temporal and lifetime views from one V2.8 local episode/event store."""
from __future__ import annotations

from copy import deepcopy


def _authorized(frame: dict, target_id: str) -> bool:
    return any(o.entity_id == target_id and o.trusted for o in frame["observations"])


def _visibility_windows(frames: list[dict], target_id: str) -> list[dict]:
    windows, current = [], None
    for row in frames:
        seen = _authorized(row, target_id)
        if seen and current is None:
            current = {"start_frame": row["frame"], "start_time": row["time"],
                       "end_frame": row["frame"], "end_time": row["time"], "loss_frame": None, "loss_time": None}
        elif seen:
            current["end_frame"], current["end_time"] = row["frame"], row["time"]
        elif current is not None and row.get("upstream_state") == "UNOBSERVED":
            current["loss_frame"], current["loss_time"] = row["frame"], row["time"]
            windows.append(current)
            current = None
    if current is not None:
        windows.append(current)
    return windows


def _segment_status(segment: dict, windows: list[dict]) -> str:
    containing = next((w for w in windows if w["start_frame"] <= segment["end_frame"] <= w["end_frame"]), None)
    if containing is None:
        return "ENDED"
    candidates = [w for w in windows if w["loss_frame"] is not None]
    if containing not in candidates:
        return "ACTIVE"
    final_window = candidates[-1]
    if containing is not final_window:
        return "STALE"
    return "LAST_TRUSTED"


def _select_snapshot_graph(frame: int, segments: list[dict], nodes: dict, primary_limit: int,
                           context_limit: int, remembered: list[dict] | None = None) -> dict:
    active = remembered if remembered is not None else [s for s in segments if s["start_frame"] <= frame <= s["end_frame"]]
    primaries = sorted([s for s in active if s["hop"] == 1],
                       key=lambda s: (-s["end_time"], -(s["end_time"] - s["start_time"]), s["object"]))[:primary_limit]
    primary_ids = {s["object"] for s in primaries}
    contexts = []
    for primary in primaries:
        matching = sorted([s for s in active if s["hop"] == 2 and s["via_primary"] == primary["object"]],
                          key=lambda s: (-s["end_time"], s["object"]))[:context_limit]
        contexts.extend(matching)
    selected = primaries + contexts
    node_ids = {"phone_01"} | {s["object"] for s in selected}
    edges = [{"source": s["subject"], "relation": "TRUSTED_ANCHOR_CONTEXT" if s["hop"] == 1 else "IMAGE_NEAR_CONTEXT",
              "target": s["object"], "kind": "IMAGE_CONTEXT", "segment_id": s["segment_id"],
              "status": "LAST_TRUSTED" if remembered is not None else "ACTIVE", "physical_verification": False}
             for s in selected]
    return {"nodes": [deepcopy(nodes[key]) for key in sorted(node_ids, key=lambda k: (nodes[k]["hop"], k))],
            "edges": edges, "connected": all(e["source"] in node_ids and e["target"] in node_ids for e in edges)}


def build_memory(frames: list[dict], local_graph: dict, physical: list[dict]) -> dict:
    target_id = local_graph["target"]
    windows = _visibility_windows(frames, target_id)
    nodes = {node["entity_id"]: deepcopy(node) for node in local_graph["nodes"]}
    segments = deepcopy(local_graph["primary_segments"] + local_graph["context_segments"])
    for segment in segments:
        segment["status"] = _segment_status(segment, windows)
    status_by_segment = {s["segment_id"]: s["status"] for s in segments}
    episodes = []
    for segment in segments:
        episodes.append({"episode_id": f"E{len(episodes)+1:04d}", "segment_id": segment["segment_id"],
                         "subject": segment["subject"],
                         "relation": "TRUSTED_ANCHOR_CONTEXT" if segment["hop"] == 1 else "IMAGE_NEAR_CONTEXT",
                         "object": segment["object"], "kind": "IMAGE_CONTEXT", "decision": "STABLE_CONTEXT",
                         "start_frame": segment["start_frame"], "end_frame": segment["end_frame"],
                         "start_time": segment["start_time"], "last_confirmed_time": segment["end_time"],
                         "status": segment["status"], "source": sorted({ref for row in segment["observations"]
                             for ref in (row.get("target_observation"), row.get("anchor_observation")) if ref}),
                         "source_snapshots": []})
    for candidate in physical:
        if candidate["decision"] not in {"PROMOTED", "CANDIDATE"}:
            continue
        episodes.append({"episode_id": f"E{len(episodes)+1:04d}", "segment_id": candidate["segment_id"],
                         "subject": candidate["target"], "relation": candidate["candidate_relation"],
                         "object": candidate["anchor"], "kind": "PHYSICAL", "decision": candidate["decision"],
                         "start_frame": candidate["start_frame"], "end_frame": candidate["end_frame"],
                         "start_time": next(s["start_time"] for s in segments if s["segment_id"] == candidate["segment_id"]),
                         "last_confirmed_time": next(s["end_time"] for s in segments if s["segment_id"] == candidate["segment_id"]),
                         "status": status_by_segment.get(candidate["segment_id"], "ENDED"),
                         "source": candidate["source_observations"], "source_snapshots": [],
                         "reason": candidate["reason"]})

    event_rows = []
    appeared = False
    for window in windows:
        event_rows.append((window["start_frame"], window["start_time"],
                           "TARGET_RECONFIRMED" if appeared else "TARGET_APPEARED", {}))
        appeared = True
        if window["loss_frame"] is not None:
            event_rows.append((window["loss_frame"], window["loss_time"], "TARGET_UNOBSERVED", {}))
    for segment in segments:
        event_rows.append((segment["start_frame"], segment["start_time"],
                           "PRIMARY_ANCHOR_CHANGED" if segment["hop"] == 1 else "IMPORTANT_CONTEXT_CHANGED",
                           {"segment_id": segment["segment_id"], "anchor": segment["object"]}))
    for candidate in physical:
        if candidate["decision"] in {"PROMOTED", "CANDIDATE"}:
            event_rows.append((candidate["end_frame"], next(s["end_time"] for s in segments
                              if s["segment_id"] == candidate["segment_id"]),
                              "PHYSICAL_RELATION_PROMOTED" if candidate["decision"] == "PROMOTED"
                              else "PHYSICAL_RELATION_CANDIDATE",
                              {"candidate_id": candidate["candidate_id"], "relation": candidate["candidate_relation"]}))
    event_rows.sort(key=lambda r: (r[0], r[2], str(r[3])))

    final_loss_window = next((w for w in reversed(windows) if w["loss_frame"] is not None), None)
    final_segments = []
    if final_loss_window:
        candidates = [s for s in segments if s["hop"] == 1 and final_loss_window["start_frame"] <= s["end_frame"] <= final_loss_window["end_frame"]]
        if candidates:
            latest = max(s["end_time"] for s in candidates)
            selected_primary = sorted([s for s in candidates if latest - s["end_time"] <= .65],
                                      key=lambda s: (-s["end_time"], s["object"]))[:local_graph["limits"]["primary_per_snapshot"]]
            selected_ids = {s["object"] for s in selected_primary}
            final_segments = selected_primary + [s for s in segments if s["hop"] == 2 and s["via_primary"] in selected_ids
                                                  and s["end_time"] <= latest and latest - s["end_time"] <= .65]
    final_graph = _select_snapshot_graph(final_loss_window["loss_frame"] if final_loss_window else -1, segments, nodes,
                                         local_graph["limits"]["primary_per_snapshot"],
                                         local_graph["limits"]["context_per_primary"], final_segments)
    for edge in final_graph["edges"]:
        edge["status"] = "LAST_TRUSTED"
    final_node_ids = {node["entity_id"] for node in final_graph["nodes"]}
    for episode in episodes:
        if (episode["kind"] == "PHYSICAL" and episode["status"] == "LAST_TRUSTED"
                and episode["object"] in final_node_ids):
            final_graph["edges"].append({"source": target_id, "relation": episode["relation"],
                "target": episode["object"], "kind": "PHYSICAL", "decision": episode["decision"],
                "episode_id": episode["episode_id"], "status": "LAST_TRUSTED",
                "physical_verification": episode["decision"] == "PROMOTED"})

    snapshots, events = [], []
    last_visible_graph = {"nodes": [deepcopy(nodes[target_id])], "edges": [], "connected": True}
    for frame, time, event_type, details in event_rows:
        event = {"event_id": f"EV{len(events)+1:04d}", "event_type": event_type,
                 "frame": frame, "time": time, "details": details}
        events.append(event)
        if event_type == "TARGET_UNOBSERVED":
            if final_loss_window and frame == final_loss_window["loss_frame"]:
                graph = deepcopy(final_graph)
            else:
                graph = deepcopy(last_visible_graph)
                for edge in graph["edges"]:
                    edge["status"] = "LAST_TRUSTED"
            state = "UNOBSERVED"
        else:
            graph = _select_snapshot_graph(frame, segments, nodes,
                                           local_graph["limits"]["primary_per_snapshot"],
                                           local_graph["limits"]["context_per_primary"])
            state = "VISIBLE_TRUSTED"
        graph_node_ids = {node["entity_id"] for node in graph["nodes"]}
        for episode in episodes:
            relevant = episode["start_frame"] <= frame <= episode["end_frame"]
            relevant |= state == "UNOBSERVED" and episode["status"] == "LAST_TRUSTED"
            if episode["kind"] == "PHYSICAL" and relevant and episode["object"] in graph_node_ids:
                edge = {"source": target_id, "relation": episode["relation"], "target": episode["object"],
                        "kind": "PHYSICAL", "decision": episode["decision"],
                        "episode_id": episode["episode_id"], "status": "LAST_TRUSTED" if state == "UNOBSERVED" else "ACTIVE",
                        "physical_verification": episode["decision"] == "PROMOTED"}
                if edge not in graph["edges"]:
                    graph["edges"].append(edge)
        if state == "VISIBLE_TRUSTED" and graph["edges"]:
            last_visible_graph = deepcopy(graph)
        signature = (state, tuple((e["source"], e["relation"], e["target"], e["status"]) for e in graph["edges"]))
        if snapshots and snapshots[-1]["signature"] == list(signature):
            snapshots[-1]["trigger_events"].append(event)
            continue
        snapshot_id = f"G{len(snapshots)+1:03d}"
        for episode in episodes:
            if episode["start_frame"] <= frame <= episode["end_frame"] or (state == "UNOBSERVED" and episode["status"] == "LAST_TRUSTED"):
                episode["source_snapshots"].append(snapshot_id)
        snapshots.append({"snapshot_id": snapshot_id, "frame": frame, "time": time, "target_state": state,
                          "nodes": graph["nodes"], "edges": graph["edges"], "trigger_events": [event],
                          "signature": list(signature),
                          "meaning": "Remembered last trusted local subgraph" if state == "UNOBSERVED"
                          else "Current trusted local subgraph"})
    for snapshot in snapshots:
        snapshot.pop("signature", None)
    source_snapshot_by_segment = {e["segment_id"]: e["source_snapshots"] for e in episodes if e.get("segment_id")}
    target_last_frame = max((w["end_frame"] for w in windows), default=None)
    target_last_time = max((w["end_time"] for w in windows), default=None)
    target_state = "UNOBSERVED" if final_loss_window else ("VISIBLE_TRUSTED" if windows else "NOT_YET_OBSERVED")
    target = {"entity_id": target_id, "state": target_state, "last_seen_frame": target_last_frame,
              "last_seen_time": target_last_time,
              "last_trusted_snapshot": snapshots[-1]["snapshot_id"] if snapshots else None,
              "last_trusted_primary_anchors": sorted({e["target"] for e in final_graph["edges"] if e["source"] == target_id}),
              "visibility_assessment": "UNOBSERVED_UNCERTAIN" if target_state == "UNOBSERVED" else "VISIBLE"}
    return {"schema": "v28_memory_store_1", "target": target, "entities": list(nodes.values()),
            "episodes": episodes, "events": events, "snapshots": snapshots,
            "last_trusted_local_subgraph": final_graph, "visibility_windows": windows,
            "source_snapshot_by_segment": source_snapshot_by_segment}


def object_memory(memory: dict) -> dict:
    return {"schema": "v28_object_memory_1", "target": deepcopy(memory["target"]),
            "entities": deepcopy(memory["entities"]), "episodes": deepcopy(memory["episodes"]),
            "events": deepcopy(memory["events"]),
            "last_trusted_local_subgraph": deepcopy(memory["last_trusted_local_subgraph"]),
            "interpretation": "Historical target-centered local evidence; candidates are not confirmed physical truth"}
