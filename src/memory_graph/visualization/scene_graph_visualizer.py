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
    graph, labels, attributes = nx.DiGraph(), {}, []
    for tid in sorted(ids):
        e = lookup[tid]
        graph.add_node(tid)
        labels[tid] = f"{e.entity_id}\nID:{tid}" + (f"\nYOLO? {e.detector_class}" if e.semantic_class == "unknown" else "")
        for key, value in list(e.attributes.items())[:config.max_attributes_per_entity]:
            attribute_id = f"attr:{tid}:{key}"
            attributes.append(attribute_id)
            graph.add_edge(tid, attribute_id)
            labels[attribute_id] = "\n".join(textwrap.wrap(f"{key}: {value}", 20))
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
        local = nx.kamada_kawai_layout(sub.to_undirected()) if len(sub) > 2 else nx.circular_layout(sub)
        for node, xy in local.items():
            positions[node] = (float(xy[0])+3.4*(index%cols), float(xy[1])-3.4*(index//cols))
    figure, ax = plt.subplots(figsize=(18, 12) if len(graph) > 8 else (12, 8))
    ax.axis("off")
    if graph:
        entity_ids = sorted(ids)
        colors = ["#85c8e8" if lookup[tid].semantic_class != "unknown" else "#c6cbd1" for tid in entity_ids]
        borders = ["#c89518" if lookup[tid].is_anchor else "#52606d" for tid in entity_ids]
        nx.draw_networkx_nodes(graph, positions, nodelist=entity_ids, node_color=colors,
                               edgecolors=borders, linewidths=2, node_size=2200, ax=ax)
        nx.draw_networkx_nodes(graph, positions, nodelist=attributes, node_shape="D", node_color="#d3bbef", node_size=1400, ax=ax)
        nx.draw_networkx_labels(graph, positions, labels=labels, font_size=8, ax=ax)
        for edge, values in edge_data.items():
            vlm = any(r.evidence.vlm for r in values)
            nx.draw_networkx_edges(graph, positions, edgelist=[edge], style="solid" if vlm else "dashed",
                edge_color="#3c5570" if vlm else "#99a4ae", arrowsize=15, node_size=2200, ax=ax,
                connectionstyle="arc3,rad=0.08")
        attribute_edges = [(a, b) for a, b in graph.edges if b in attributes]
        nx.draw_networkx_edges(graph, positions, edgelist=attribute_edges, edge_color="#9573ba", node_size=2200, ax=ax)
        edge_labels = {}
        for edge, values in edge_data.items():
            predicates = "/".join(dict.fromkeys(r.predicate for r in values))
            edge_labels[edge] = "\n".join(textwrap.wrap(predicates, 28))+f"\n{min(r.start_time for r in values):.1f}-{max(r.end_time for r in values):.1f}s"
        nx.draw_networkx_edge_labels(graph, positions, edge_labels=edge_labels, font_size=6.5, rotate=False,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": .9}, ax=ax)
        ax.margins(.2)
    else:
        ax.text(.5, .5, "No admitted entities / relations.\nInspect rejection and analysis-status records.", ha="center", transform=ax.transAxes)
    ax.set_title(f"{title}\n{status}\n{len(entities)} entities, {len(relations)} relation intervals; "
                 f"rendering {len(ids)} entities, {len(chosen)} intervals", fontsize=13, loc="left", pad=20)
    figure.legend(handles=[Patch(color="#85c8e8", label="VLM semantic entity"), Patch(color="#c6cbd1", label="Unknown entity"),
                           Patch(color="#d3bbef", label="VLM attribute")], loc="lower center", ncol=3, frameon=False)
    figure.text(.02, .045, "Dashed edges: geometry only. Gold border: anchor prior (metadata only). All data retained in JSON; edge times summarize sparse evidence.", fontsize=8)
    figure.tight_layout(rect=(0, .08, 1, 1))
    figure.savefig(path, dpi=150, facecolor="white")
    plt.close(figure)
    save_json(str(path)+".render.json", {"displayed_track_ids": sorted(ids), "omitted_track_ids": sorted(set(lookup)-ids),
        "displayed_relation_count": len(chosen), "total_relation_count": len(relations), "edge_labels": "predicate union and outer time span; see JSON for exact intervals"})
