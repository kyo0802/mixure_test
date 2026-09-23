"""One general semantic network, with attributes; no per-anchor panels."""
import math
import textwrap
from collections import defaultdict
import networkx as nx
from matplotlib.patches import Patch
from .graph_visualizer import plt
from ..vlm.schemas import INTERACTIONS
from ..memory.memory_store import save_json


def render_semantic_graph(entities, relations, path, title, config, status=""):
    lookup = {e.track_id: e for e in entities}
    ordered = sorted(relations, key=lambda r: (not r.evidence.vlm, r.predicate not in INTERACTIONS,
        r.predicate not in {"NEAR", "ON", "INSIDE", "OVERLAPPING"}, -r.confidence, r.start_time))
    chosen, ids = [], set()
    for relation in ordered:
        endpoints = {relation.subject_track_id} | ({relation.object_track_id} if relation.object_track_id is not None else set())
        if endpoints <= set(lookup) and len(ids | endpoints) <= config.max_render_entities and len(chosen) < config.max_render_relations:
            ids.update(endpoints)
            chosen.append(relation)
    for entity in sorted(entities, key=lambda e: (e.semantic_class == "unknown", -e.semantic_confidence, e.track_id)):
        if len(ids) < config.max_render_entities:
            ids.add(entity.track_id)
    graph, labels = nx.DiGraph(), {}
    for tid in sorted(ids):
        e = lookup[tid]
        graph.add_node(tid)
        name = e.semantic_class if e.entity_id.startswith("track_") else e.entity_id
        labels[tid] = f"{name}\nID:{tid}" + (f"\nYOLO? {e.detector_class}" if e.semantic_class == "unknown" else "")
    edge_data = defaultdict(list)
    for r in chosen:
        if r.object_track_id is None:
            labels[r.subject_track_id] += f"\n{r.predicate}"
        else:
            graph.add_edge(r.subject_track_id, r.object_track_id)
            edge_data[(r.subject_track_id, r.object_track_id)].append(r)
    # Lay out connected components independently so isolates do not compress meaningful subnetworks.
    components = sorted(nx.weakly_connected_components(graph), key=len, reverse=True) if graph else []
    positions = {}
    cols = max(1, math.ceil(math.sqrt(len(components))))
    for index, component in enumerate(components):
        sub = graph.subgraph(component)
        local = nx.circular_layout(sub)
        for node, xy in local.items():
            positions[node] = (float(xy[0])+3.4*(index%cols), float(xy[1])-3.4*(index//cols))
    figure, (ax, attribute_ax) = plt.subplots(1, 2, figsize=(20, 13) if len(graph) > 8 else (16, 10),
                                            gridspec_kw={"width_ratios": [3.5, 1.2]})
    ax.axis("off")
    attribute_ax.axis("off")
    attribute_entities = [lookup[tid] for tid in sorted(ids) if lookup[tid].attributes][:12]
    attribute_ax.set_title("VLM attributes (unverified)", fontsize=10, loc="left")
    for index, entity in enumerate(attribute_entities):
        lines = [f"ID:{entity.track_id} | {entity.semantic_class}"]
        for key, value in list(entity.attributes.items())[:min(2, config.max_attributes_per_entity)]:
            lines.extend(textwrap.wrap(f"{key}: {value[:70]}", 32))
        attribute_ax.text(0, 1-index/max(1,len(attribute_entities)), '\n'.join(lines),
                          transform=attribute_ax.transAxes, fontsize=8, va="top")
    attribute_ax.text(0, -.06, "Full attributes and all relation intervals\nare retained in the JSON artifact.",
                      transform=attribute_ax.transAxes, fontsize=8)
    if graph:
        entity_ids = sorted(ids)
        colors = ["#85c8e8" if lookup[tid].semantic_class != "unknown" else "#c6cbd1" for tid in entity_ids]
        borders = ["#c89518" if lookup[tid].is_anchor else "#52606d" for tid in entity_ids]
        nx.draw_networkx_nodes(graph, positions, nodelist=entity_ids, node_color=colors,
                               edgecolors=borders, linewidths=2, node_size=1800, ax=ax)
        nx.draw_networkx_labels(graph, positions, labels=labels, font_size=8, ax=ax)
        for edge, values in edge_data.items():
            vlm = any(r.evidence.vlm for r in values)
            nx.draw_networkx_edges(graph, positions, edgelist=[edge], style="solid" if vlm else "dashed",
                edge_color="#3c5570" if vlm else "#99a4ae", arrowsize=15, node_size=1800, ax=ax,
                connectionstyle="arc3,rad=0.08")
        edge_labels = {}
        for edge, values in edge_data.items():
            names = list(dict.fromkeys(r.predicate for r in values))
            predicates = "/".join(names[:2])+(f" (+{len(names)-2})" if len(names)>2 else "")
            edge_labels[edge] = "\n".join(textwrap.wrap(predicates, 28))+f"\n{min(r.start_time for r in values):.1f}-{max(r.end_time for r in values):.1f}s"
        nx.draw_networkx_edge_labels(graph, positions, edge_labels=edge_labels, font_size=6.5, rotate=False, label_pos=.3,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": .9}, ax=ax)
        ax.margins(.2)
    else:
        ax.text(.5, .5, "No admitted entities / relations.\nInspect rejection and analysis-status records.", ha="center", transform=ax.transAxes)
    figure.suptitle(f"{title}\n{status}\n{len(entities)} entities, {len(relations)} relation intervals; "
                   f"rendering {len(ids)} entities, {len(chosen)} intervals", fontsize=12, x=.02, ha="left")
    figure.legend(handles=[Patch(color="#85c8e8", label="VLM semantic entity"), Patch(color="#c6cbd1", label="Unknown entity"),
                           Patch(color="#99a4ae", label="Dashed: geometry only")], loc="lower center", ncol=3, frameon=False)
    figure.text(.02, .045, "Dashed edges: geometry only. Gold border: anchor prior (metadata only). All data retained in JSON; edge times summarize sparse evidence.", fontsize=8)
    figure.tight_layout(rect=(0, .08, 1, .89))
    figure.savefig(path, dpi=150, facecolor="white")
    plt.close(figure)
    save_json(str(path)+".render.json", {"displayed_track_ids": sorted(ids), "omitted_track_ids": sorted(set(lookup)-ids),
        "displayed_relation_count": len(chosen), "total_relation_count": len(relations),
        "attribute_sidebar_track_ids": [e.track_id for e in attribute_entities],
        "edge_labels": "up to two predicates plus remaining count and outer time span; see JSON for exact intervals"})
