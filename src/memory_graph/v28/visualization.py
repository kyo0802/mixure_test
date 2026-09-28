"""Readable relation-as-node figures for V2.8 local memory."""
from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


def _id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def mermaid(nodes: list[dict], edges: list[dict], title: str) -> str:
    lines = ["---", f"title: {title}", "---", "flowchart LR"]
    for node in nodes:
        key = _id(node["entity_id"])
        label = f"{node['entity_id']}<br/>{node.get('raw_label', '')}<br/>Hop {node.get('hop', '?')}"
        lines.append(f'    {key}["{label}"]')
    for index, edge in enumerate(edges, 1):
        relation = f"r{index}"
        details = [edge["relation"]]
        if edge.get("decision"):
            details.append(edge["decision"])
        if edge.get("status"):
            details.append(edge["status"])
        lines += [f'    {relation}(["{"<br/>".join(details)}"])',
                  f"    {_id(edge['source'])} --> {relation}", f"    {relation} --> {_id(edge['target'])}"]
    lines += ["    classDef target stroke-width:4px,font-weight:bold;",
              "    classDef relation stroke-dasharray: 4 2;", "    class phone_01 target;"]
    if edges:
        lines.append("    class " + ",".join(f"r{i}" for i in range(1, len(edges)+1)) + " relation;")
    return "\n".join(lines) + "\n"


def _positions(nodes: list[dict]) -> dict[str, tuple[float, float]]:
    positions = {}
    by_hop = {hop: [n for n in nodes if n.get("hop") == hop] for hop in (0, 1, 2)}
    for hop, values in by_hop.items():
        for index, node in enumerate(sorted(values, key=lambda n: n["entity_id"])):
            y = (len(values) - 1) / 2 - index
            positions[node["entity_id"]] = (hop * 4.0, y * 2.8)
    return positions


def _display_edges(edges: list[dict]) -> list[dict]:
    """Show one readable relation node per entity pair; JSON/Mermaid retain full evidence."""
    grouped = {}
    for edge in edges:
        grouped.setdefault((edge["source"], edge["target"]), []).append(edge)
    result = []
    status_order = {"LAST_TRUSTED": 0, "ACTIVE": 1, "STALE": 2, "ENDED": 3, "CONTEXT": 4}
    for values in grouped.values():
        physical = [edge for edge in values if edge.get("kind") == "PHYSICAL" or edge.get("decision")]
        chosen = dict(sorted(physical or values,
                             key=lambda edge: (edge.get("decision") != "PROMOTED",
                                               status_order.get(edge.get("status"), 9), edge["relation"]))[0])
        if physical and any(edge.get("kind") == "IMAGE_CONTEXT" for edge in values):
            chosen["context_retained"] = True
        statuses = sorted({edge.get("status") for edge in values if edge.get("status")},
                          key=lambda value: status_order.get(value, 9))
        chosen["status"] = "/".join(statuses[:2])
        result.append(chosen)
    return result


def _draw(ax, nodes: list[dict], edges: list[dict], title: str, compact: bool = False) -> None:
    edges = _display_edges(edges)
    positions = _positions(nodes)
    ax.set_title(title, fontsize=12 if compact else 15, fontweight="bold", loc="left")
    ax.axis("off")
    offsets = {}
    for index, edge in enumerate(edges):
        if edge["source"] not in positions or edge["target"] not in positions:
            continue
        sx, sy = positions[edge["source"]]
        tx, ty = positions[edge["target"]]
        key = (edge["source"], edge["target"])
        count = offsets.get(key, 0)
        offsets[key] = count + 1
        ry = (sy + ty) / 2 + (count - .5) * .55
        rx = (sx + tx) / 2
        status = edge.get("status", "")
        decision = edge.get("decision")
        dashed = status in {"ENDED", "STALE"} or decision == "CANDIDATE"
        relation_color = "#fff4d6" if decision == "CANDIDATE" else "#e7f1fa"
        relation = edge["relation"] + (f"\n{decision}" if decision else "")
        if edge.get("context_retained"):
            relation += "\n+ image context"
        relation += f"\n{status}" if status else ""
        line_count = 2 + bool(decision) + bool(edge.get("context_retained")) + bool(status)
        relation_height = max(.78, .23 * line_count)
        patch = FancyBboxPatch((rx - .72, ry - relation_height / 2), 1.44, relation_height,
                               boxstyle="round,pad=0.08,rounding_size=0.15",
                               facecolor=relation_color, edgecolor="#506070", linewidth=1.6,
                               linestyle="--" if dashed else "-")
        ax.add_patch(patch)
        ax.text(rx, ry, relation, ha="center", va="center", fontsize=7.5 if compact else 9)
        ax.add_patch(FancyArrowPatch((sx + .82, sy), (rx - .76, ry), arrowstyle="-|>", mutation_scale=11,
                                     color="#58636e", linewidth=1.2))
        ax.add_patch(FancyArrowPatch((rx + .76, ry), (tx - .82, ty), arrowstyle="-|>", mutation_scale=11,
                                     color="#58636e", linewidth=1.2))
    for node in nodes:
        x, y = positions[node["entity_id"]]
        target = node["entity_id"] == "phone_01"
        face = "#d9ecff" if target else ("#eef6ea" if node.get("hop") == 1 else "#f4f0fa")
        patch = FancyBboxPatch((x - .8, y - .45), 1.6, .9, boxstyle="round,pad=0.04,rounding_size=0.04",
                               facecolor=face, edgecolor="#1f2d3d", linewidth=3 if target else 1.5)
        ax.add_patch(patch)
        ax.text(x, y, f"{node['entity_id']}\n{node.get('raw_label','')}\nHop {node.get('hop','?')}",
                ha="center", va="center", fontsize=8 if compact else 10, fontweight="bold" if target else "normal")
    if positions:
        xs, ys = zip(*positions.values())
        ax.set_xlim(min(xs) - 1.4, max(xs) + 1.4)
        ax.set_ylim(min(ys) - 1.3, max(ys) + 1.5)
    else:
        ax.text(.5, .5, "No trusted local structure", transform=ax.transAxes, ha="center", va="center")


def render_graph(nodes: list[dict], edges: list[dict], path: Path, title: str) -> None:
    height = max(4.2, 1.5 * max(1, max((sum(n.get("hop") == h for n in nodes) for h in (0, 1, 2)), default=1)))
    figure, axis = plt.subplots(figsize=(14, height), constrained_layout=True)
    _draw(axis, nodes, edges, title)
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)
    path.with_suffix(".mmd").write_text(mermaid(nodes, edges, title), encoding="utf-8")


def _lifetime_edges(memory: dict) -> list[dict]:
    collapsed = {}
    for episode in memory["episodes"]:
        key = (episode["subject"], episode["relation"], episode["object"], episode["decision"], episode["status"])
        edge = collapsed.get(key)
        if edge is None:
            collapsed[key] = {"source": episode["subject"], "relation": episode["relation"],
                              "target": episode["object"], "kind": episode["kind"],
                              "decision": episode["decision"] if episode["kind"] == "PHYSICAL" else None,
                              "status": episode["status"], "start_time": episode["start_time"],
                              "end_time": episode["last_confirmed_time"]}
        else:
            edge["start_time"] = min(edge["start_time"], episode["start_time"])
            edge["end_time"] = max(edge["end_time"], episode["last_confirmed_time"])
    return list(collapsed.values())


def render_video(folder: Path, task: str) -> None:
    temporal = json.loads((folder / "temporal_memory.json").read_text(encoding="utf-8"))
    memory = json.loads((folder / "object_memory_phone_01.json").read_text(encoding="utf-8"))
    plan = json.loads((folder / "search_candidates.json").read_text(encoding="utf-8"))
    graphs = folder / "graphs"
    stages = graphs / "temporal"
    stages.mkdir(parents=True, exist_ok=True)
    for snapshot in temporal["snapshots"]:
        title = f"{task} / {snapshot['snapshot_id']} @ {snapshot['time']:.2f}s / {snapshot['target_state']}"
        render_graph(snapshot["nodes"], snapshot["edges"], stages / f"{snapshot['snapshot_id']}.png", title)
    snapshots = temporal["snapshots"]
    columns = 2
    rows = max(1, (len(snapshots) + columns - 1) // columns)
    figure, axes = plt.subplots(rows, columns, figsize=(17, max(5, rows * 4.5)), constrained_layout=True)
    axes = list(getattr(axes, "flat", [axes]))
    for axis, snapshot in zip(axes, snapshots):
        _draw(axis, snapshot["nodes"], snapshot["edges"],
              f"{snapshot['snapshot_id']} @ {snapshot['time']:.2f}s / {snapshot['target_state']}", compact=True)
    for axis in axes[len(snapshots):]:
        axis.axis("off")
    figure.suptitle(f"{task}: target-centered temporal local memory", fontsize=18, fontweight="bold")
    figure.savefig(graphs / "temporal_memory_timeline.png", dpi=170, bbox_inches="tight")
    plt.close(figure)
    lifetime_nodes = memory["entities"]
    render_graph(lifetime_nodes, _lifetime_edges(memory), graphs / "phone_01_lifetime_memory.png",
                 f"{task}: phone_01 lifetime local memory")
    final = memory["last_trusted_local_subgraph"]
    render_graph(final["nodes"], final["edges"], graphs / "phone_01_local_subgraph_final.png",
                 f"{task}: final last-trusted local subgraph")
    entity_map = {e["entity_id"]: e for e in memory["entities"]}
    search_nodes = {"phone_01": entity_map["phone_01"]}
    search_edges = []
    shown_anchors = set()
    for row in plan["candidates"]:
        if row["search_anchor"] in shown_anchors or len(shown_anchors) >= 5:
            continue
        shown_anchors.add(row["search_anchor"])
        search_nodes[row["search_anchor"]] = entity_map[row["search_anchor"]]
        search_edges.append({"source": "phone_01", "relation": f"SEARCH #{row['rank']}\n{row['relation']}",
                             "target": row["search_anchor"], "decision": "CONFIRMED" if row["confirmed"] else "CANDIDATE",
                             "status": row["status"]})
        for context in row.get("context_anchors", []):
            search_nodes[context["entity_id"]] = entity_map[context["entity_id"]]
            search_edges.append({"source": row["search_anchor"], "relation": context["relation"],
                                 "target": context["entity_id"], "status": "CONTEXT"})
    render_graph(list(search_nodes.values()), search_edges, graphs / "phone_01_search_graph.png",
                 f"{task}: prioritized search graph")
