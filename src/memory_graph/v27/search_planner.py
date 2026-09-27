"""Explainable ordering from memory status; no weighted score."""
from __future__ import annotations

LOCATION = {"ON", "INSIDE", "BEHIND", "OCCLUDED_BY"}


def find(memory: dict, entity_id: str = "phone_01") -> dict:
    if entity_id != memory["target"]["entity_id"]:
        raise KeyError(entity_id)
    target = memory["target"]
    if target["state"] != "UNOBSERVED":
        return {"target": entity_id, "state": target["state"], "candidates": [],
                "reason": "Lost-object search applies when the target is UNOBSERVED"}
    episodes = [e for e in memory["episodes"] if e["relation"] != "HELD_BY"
                and memory["entities"][e["object"]]["label"] != "person"]
    older = [e for e in episodes if e["status"] in {"ENDED", "STALE"}]
    latest_old = max((e["last_confirmed_time"] for e in older), default=None)
    rows = []
    for episode in episodes:
        recent = episode["status"] == "LAST_TRUSTED"
        if recent and episode["kind"] == "PHYSICAL" and episode["relation"] in LOCATION:
            priority, why = 1, "Last trusted physical location relation before loss"
        elif recent:
            priority, why = 2, "Last trusted anchor/context before loss"
        elif episode["last_confirmed_time"] == latest_old:
            priority, why = 3, "Immediately preceding stable trusted context"
        else:
            priority, why = 4, "Older trusted spatial memory"
        rows.append({"target": entity_id, "search_anchor": episode["object"],
                     "anchor_label": memory["entities"][episode["object"]]["label"],
                     "relation": episode["relation"], "priority_rule": priority,
                     "source_episode": episode["episode_id"],
                     "source_memory": episode["graph_snapshot_ids"][-1] if episode["graph_snapshot_ids"] else None,
                     "last_confirmed_time": episode["last_confirmed_time"], "reason": why,
                     "evidence_level": episode["evidence_level"], "status": episode["status"],
                     "uncertainty": ("Image-relative localization context; no physical relation or current location verified"
                                     if episode["kind"] == "CONTEXT" else
                                     "Historical supported relation; current location after loss is unknown"),
                     "provenance": episode["source"]})
    rows.sort(key=lambda row: (row["priority_rule"], -row["last_confirmed_time"], row["search_anchor"], row["relation"]))
    unique = []
    seen = set()
    for row in rows:
        key = (row["search_anchor"], row["relation"])
        if key not in seen:
            seen.add(key)
            row["rank"] = len(unique) + 1
            unique.append(row)
    return {"target": entity_id, "state": target["state"], "last_seen_time": target["last_seen_time"],
            "candidates": unique, "reason": "Ordered by graph provenance and recency within each priority rule",
            "uncertainty": "No trustworthy spatial context available" if not unique else "Last memory is not current physical truth"}


def plan_text(plan: dict) -> str:
    lines = [f"TARGET {plan['target']}", f"STATE {plan['state']}",
             f"LAST TRUSTED SEEN {plan.get('last_seen_time')}", "", "SEARCH PLAN"]
    for row in plan["candidates"]:
        lines += [f"{row['rank']}. {row['relation']} {row['anchor_label']} ({row['search_anchor']})",
                  f"   Rule {row['priority_rule']}: {row['reason']}",
                  f"   Evidence: {row['source_memory']} / {row['source_episode']} at {row['last_confirmed_time']:.2f}s",
                  f"   Uncertainty: {row['uncertainty']}"]
    if not plan["candidates"]:
        lines.append(plan.get("uncertainty", plan["reason"]))
    return "\n".join(lines) + "\n"
