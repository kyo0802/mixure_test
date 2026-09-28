"""Add only gate-admitted V2.9 episodes to the frozen V2.8 memory shape."""
from __future__ import annotations

from copy import deepcopy
import json

from memory_graph.v27.pipeline import ROOT, write
from memory_graph.v28.roles import semantic_roles
from memory_graph.v28.search_planner import find, plan_text


def integrate(task: str, decisions: list[dict], candidates: list[dict],
              trusted_masks: list[dict], folder) -> dict:
    baseline = ROOT/"outputs_v28"/task
    lifetime = deepcopy(json.loads((baseline/"object_memory_phone_01.json").read_text(encoding="utf-8")))
    temporal = deepcopy(json.loads((baseline/"temporal_memory.json").read_text(encoding="utf-8")))
    registry = json.loads((ROOT/"outputs_v26"/task/"entity_registry.json").read_text(encoding="utf-8"))
    entities = {e["entity_id"]: e for e in lifetime["entities"]}
    registry_entities = {e["entity_id"]: e for e in registry["entities"]}
    candidate_map = {c["candidate_id"]: c for c in candidates}
    final_trusted = max((m["frame"] for m in trusted_masks if m["trusted"]), default=-1)
    appended = []
    for decision in decisions:
        if decision["decision"] not in {"PROMOTED", "CANDIDATE"}:
            continue
        candidate = candidate_map[decision["candidate_id"]]
        anchor = decision["anchor"]
        if anchor not in registry_entities:
            continue  # no invented persistent anchor
        if anchor not in entities:
            raw = registry_entities[anchor]["semantic_label"]
            entity = {"entity_id": anchor, "raw_label": raw, "semantic_roles": semantic_roles(raw),
                      "hop": 1, "via_primary": None}
            lifetime["entities"].append(entity)
            entities[anchor] = entity
        episode = {"episode_id": f"E{len(lifetime['episodes'])+1:04d}",
                   "segment_id": f"V29_{decision['event_id']}_{anchor}",
                   "subject": "phone_01", "relation": decision["candidate_relation"],
                   "object": anchor, "kind": "PHYSICAL", "decision": decision["decision"],
                   "start_frame": candidate["start_frame"], "end_frame": candidate["end_frame"],
                   "start_time": candidate["features"]["sampled"][0]["time"],
                   "last_confirmed_time": candidate["features"]["sampled"][-1]["time"],
                   "status": "LAST_TRUSTED" if candidate["end_frame"] >= final_trusted-6 else "STALE",
                   "source": candidate["provenance"], "source_snapshots": [],
                   "reason": decision["final_reason"], "physical_verification": decision["decision"] == "PROMOTED"}
        lifetime["episodes"].append(episode)
        appended.append(episode)
    # The V2.8 temporal and image context survives verbatim. Append a compact
    # event/snapshot only when a physical candidate has been gate admitted.
    for episode in appended:
        event = {"event_id": f"EV{len(temporal['events'])+1:04d}",
                 "event_type": "V29_PHYSICAL_"+episode["decision"],
                 "frame": episode["end_frame"], "time": episode["last_confirmed_time"],
                 "details": {"episode_id": episode["episode_id"], "relation": episode["relation"],
                             "anchor": episode["object"], "source": episode["source"]}}
        temporal["events"].append(event)
        if episode["status"] == "LAST_TRUSTED":
            local = lifetime["last_trusted_local_subgraph"]
            if episode["object"] not in {n["entity_id"] for n in local["nodes"]}:
                local["nodes"].append(deepcopy(entities[episode["object"]]))
            local["edges"].append({"source": "phone_01", "relation": episode["relation"],
                                   "target": episode["object"], "kind": "PHYSICAL",
                                   "decision": episode["decision"], "episode_id": episode["episode_id"],
                                   "status": episode["status"],
                                   "physical_verification": episode["decision"] == "PROMOTED"})
            temporal["snapshots"].append({"snapshot_id": f"G{len(temporal['snapshots'])+1:03d}",
                                          "frame": episode["end_frame"], "time": episode["last_confirmed_time"],
                                          "target_state": lifetime["target"]["state"],
                                          "nodes": deepcopy(local["nodes"]), "edges": deepcopy(local["edges"]),
                                          "trigger_events": [event],
                                          "meaning": "V2.9 last trusted physical candidate"})
    lifetime["schema"] = "v29_lifetime_memory_1"
    temporal["schema"] = "v29_temporal_memory_1"
    plan = find(lifetime)
    write(folder/"temporal_memory.json", temporal)
    write(folder/"object_memory_phone_01.json", lifetime)
    write(folder/"search_candidates.json", plan)
    (folder/"search_plan.txt").write_text(plan_text(plan), encoding="utf-8")
    return {"admitted_episodes": len(appended), "search_candidates": len(plan["candidates"]),
            "top_search_relation": plan["candidates"][0]["relation"] if plan["candidates"] else None}
