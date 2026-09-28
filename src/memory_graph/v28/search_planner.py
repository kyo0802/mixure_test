"""Five-rule explainable search ordering over V2.8 memory."""
from __future__ import annotations

PLACEMENT = {"INSIDE", "BEHIND", "ON"}


def find(memory: dict, entity_id: str = "phone_01") -> dict:
    target = memory["target"]
    if entity_id != target["entity_id"]:
        raise KeyError(entity_id)
    if target["state"] != "UNOBSERVED":
        return {"target": entity_id, "state": target["state"], "candidates": [],
                "reason": "Lost-object search applies only while target is UNOBSERVED"}
    entities = {e["entity_id"]: e for e in memory["entities"]}
    hop2 = {}
    for edge in memory["last_trusted_local_subgraph"]["edges"]:
        if edge["source"] != entity_id:
            hop2.setdefault(edge["source"], []).append({"entity_id": edge["target"],
                                                        "label": entities[edge["target"]]["raw_label"],
                                                        "relation": edge["relation"]})
    rows = []
    for episode in memory["episodes"]:
        label = entities[episode["object"]]["raw_label"]
        if episode["relation"] == "HELD_BY" or "INTERACTION_AGENT" in entities[episode["object"]]["semantic_roles"]:
            continue
        last = episode["status"] == "LAST_TRUSTED"
        if episode["kind"] == "PHYSICAL" and episode["decision"] == "PROMOTED" and last and episode["relation"] in PLACEMENT:
            priority, reason, confirmed = 1, "Last trusted promoted physical placement", True
        elif episode["kind"] == "PHYSICAL" and episode["decision"] == "PROMOTED" and last:
            priority, reason, confirmed = 2, "Last trusted promoted search-useful physical relation", True
        elif episode["kind"] == "PHYSICAL" and episode["decision"] == "CANDIDATE" and last:
            priority, reason, confirmed = 3, "Possible physical relation; unconfirmed", False
        elif episode["kind"] == "IMAGE_CONTEXT" and episode["relation"] == "TRUSTED_ANCHOR_CONTEXT" and last:
            priority, reason, confirmed = 4, "Last trusted image-relative anchor context", False
        elif episode["kind"] == "IMAGE_CONTEXT" and episode["relation"] == "TRUSTED_ANCHOR_CONTEXT":
            priority, reason, confirmed = 5, "Recent ended or stale stable context", False
        else:
            continue
        rows.append({"target": entity_id, "search_anchor": episode["object"], "anchor_label": label,
                     "relation": episode["relation"], "priority_rule": priority, "confirmed": confirmed,
                     "status": episode["status"], "source_episode": episode["episode_id"],
                     "source_memory": episode["source_snapshots"][-1] if episode["source_snapshots"] else None,
                     "last_confirmed_time": episode["last_confirmed_time"], "reason": reason,
                     "uncertainty": None if confirmed else "Possible/unconfirmed; image geometry or temporal pattern is not physical proof",
                     "context_anchors": hop2.get(episode["object"], []), "provenance": episode["source"]})
    rows.sort(key=lambda r: (r["priority_rule"], -r["last_confirmed_time"], r["search_anchor"], r["relation"]))
    unique, seen = [], set()
    for row in rows:
        key = (row["search_anchor"], row["relation"])
        if key not in seen:
            seen.add(key)
            row["rank"] = len(unique) + 1
            unique.append(row)
    return {"target": entity_id, "state": target["state"], "last_seen_time": target["last_seen_time"],
            "candidates": unique, "reason": "Deterministic graph priority rules; no weighted score",
            "uncertainty": "No useful connected spatial memory" if not unique else "Candidate is not a verified current location"}


def plan_text(plan: dict) -> str:
    lines = [f"TARGET {plan['target']}", f"STATE {plan['state']}",
             f"LAST TRUSTED SEEN {plan.get('last_seen_time')}", "", "SEARCH PLAN"]
    for row in plan["candidates"]:
        qualifier = "confirmed" if row["confirmed"] else "possible / unconfirmed"
        lines += [f"{row['rank']}. Search {row['relation']} {row['anchor_label']} ({row['search_anchor']})",
                  f"   Rule {row['priority_rule']} / {qualifier}: {row['reason']}",
                  f"   Evidence: {row['source_memory']} / {row['source_episode']} at {row['last_confirmed_time']:.2f}s"]
        if row["context_anchors"]:
            lines.append("   Locate anchor using: " + ", ".join(
                f"{c['relation']} {c['label']} ({c['entity_id']})" for c in row["context_anchors"]))
        if row["uncertainty"]:
            lines.append(f"   Uncertainty: {row['uncertainty']}")
    if not plan["candidates"]:
        lines.append(plan["uncertainty"])
    return "\n".join(lines) + "\n"
