"""Readable anchor-centered graph panels; repeated IDs represent the same node."""
import os
import math
import textwrap
from pathlib import Path
from collections import defaultdict
os.environ.setdefault("MPLCONFIGDIR", str(Path(".runtime/matplotlib").resolve()))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import networkx as nx
from ..models import MemoryGraphData
from ..memory.graph_builder import to_networkx

ANCHOR_COLOR = "#f4b942"
OBJECT_COLOR = "#80c9ef"
MAX_OVERVIEW_PANELS = 8
MAX_SUBJECTS_PER_PANEL = 6


def _edge_text(edges):
    predicates = list(dict.fromkeys(e["predicate"] for e in edges))
    windows = list(dict.fromkeys(f"{e['start_time']:.1f}-{e['end_time']:.1f}s" for e in edges))
    label = "\n".join(textwrap.wrap(" / ".join(predicates), width=38, break_long_words=False))
    label += "\n" + ", ".join(windows[:3])
    if len(windows) > 3:
        label += f" (+{len(windows)-3} spans)"
    return label


def _draw_anchor(graph, anchor, subjects, ax):
    ax.axis("off")
    ax.set_title(f"Anchor: {anchor}", loc="left", fontsize=12, pad=12)
    group = nx.DiGraph()
    group.add_node(anchor)
    group.add_nodes_from(subjects)
    group.add_edges_from((subject, anchor) for subject in subjects)
    positions = {subject: (0, -i) for i, subject in enumerate(subjects)}
    positions[anchor] = (3, -(len(subjects)-1)/2)
    nx.draw_networkx_nodes(group, positions, nodelist=subjects, node_color=OBJECT_COLOR, node_size=1600, ax=ax)
    nx.draw_networkx_nodes(group, positions, nodelist=[anchor], node_color=ANCHOR_COLOR,
                           node_shape="s", node_size=2100, ax=ax)
    nx.draw_networkx_labels(group, positions, font_size=9, ax=ax)
    nx.draw_networkx_edges(group, positions, node_size=2100, arrowsize=18,
                           edge_color="#708090", width=1.4, ax=ax)
    for subject in subjects:
        edges = list(graph.get_edge_data(subject, anchor).values())
        y = positions[subject][1]*.72+positions[anchor][1]*.28
        ax.text(.84, y, _edge_text(edges), fontsize=8, ha="left", va="center",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": .94, "pad": 3})
    ax.set_xlim(-.6, 3.65)
    ax.set_ylim(-max(len(subjects)-1, 0)-.65, .65)


def render_graph(data: MemoryGraphData, path: str | Path, nodes_per_page: int = 24) -> list[Path]:
    path = Path(path)
    graph = to_networkx(data)
    panels = []
    covered = set()
    chunk_size = min(MAX_SUBJECTS_PER_PANEL, nodes_per_page-1)
    for anchor, attrs in graph.nodes(data=True):
        subjects = sorted(graph.predecessors(anchor))
        if attrs["node_type"] == "anchor" and subjects:
            for start in range(0, len(subjects), chunk_size):
                group = subjects[start:start+chunk_size]
                panels.append((anchor, group))
                covered.update([anchor, *group])
    isolated = sorted(set(graph)-covered)
    for old in path.parent.glob(f"{path.stem}_page_*.png"):
        old.unlink()
    overview = panels[:MAX_OVERVIEW_PANELS]
    count = max(len(overview), 1)
    cols = min(2, count)
    rows = math.ceil(count/cols)
    heights = [max(3.0, 1.25*max((len(subjects) for _, subjects in overview[i*cols:(i+1)*cols]), default=1)+1)
               for i in range(rows)]
    figure, axes = plt.subplots(rows, cols, figsize=(10*cols, sum(heights)+1.5), squeeze=False,
                                gridspec_kw={"height_ratios": heights})
    for ax in axes.flat:
        ax.axis("off")
    for ax, (anchor, subjects) in zip(axes.flat, overview):
        _draw_anchor(graph, anchor, subjects, ax)
    if not panels:
        axes[0, 0].text(.5, .5, "No temporally stable relations.\nTrack nodes are in detail pages and JSON.",
                        ha="center", transform=axes[0, 0].transAxes, fontsize=12)
    figure.suptitle(f"{Path(data.video).name} | RGB-relative temporal memory\n"
        f"{len(data.nodes)} track IDs | {sum(n.node_type == 'anchor' for n in data.nodes)} anchors | "
        f"{len(data.relations)} stable intervals | {len(data.transitions)} transitions", fontsize=16, y=.99)
    figure.text(.02, .055,
        f"Same ID across panels = same graph node. {len(isolated)} unlinked nodes are shown in detail pages. "
        "Full predicate-specific intervals: JSON.", fontsize=9)
    figure.text(.02, .035, "RGB 2D only: ON_OR_ABOVE is not physical support; INSIDE is projected containment.", fontsize=9)
    figure.legend(handles=[Patch(color=ANCHOR_COLOR, label="Anchor"), Patch(color=OBJECT_COLOR, label="Tracked object")],
                  loc="lower center", ncol=2, frameon=False)
    figure.tight_layout(rect=(0, .08, 1, .93))
    figure.savefig(path, dpi=150, facecolor="white")
    plt.close(figure)
    paths = [path]
    for anchor, subjects in panels:
        output = path.with_name(f"{path.stem}_page_{len(paths):03d}.png")
        figure, ax = plt.subplots(figsize=(12, max(4, len(subjects)*1.3+1)))
        _draw_anchor(graph, anchor, subjects, ax)
        figure.suptitle(f"{Path(data.video).name} | anchor detail | RGB 2D relations", fontsize=14)
        figure.tight_layout(rect=(0, .02, 1, .92))
        figure.savefig(output, dpi=150, facecolor="white")
        plt.close(figure)
        paths.append(output)
    for start in range(0, len(isolated), nodes_per_page):
        names = isolated[start:start+nodes_per_page]
        output = path.with_name(f"{path.stem}_page_{len(paths):03d}.png")
        figure, ax = plt.subplots(figsize=(14, max(4, math.ceil(len(names)/4)*1.5)))
        ax.axis("off")
        ax.set_title(f"{Path(data.video).name} | nodes without stable relation edges", fontsize=14, pad=20)
        positions = {name: (i%4, -(i//4)) for i, name in enumerate(names)}
        colors = [ANCHOR_COLOR if graph.nodes[name]["node_type"] == "anchor" else OBJECT_COLOR for name in names]
        nx.draw_networkx_nodes(graph.subgraph(names), positions, node_color=colors, node_size=2200, ax=ax)
        nx.draw_networkx_labels(graph.subgraph(names), positions, font_size=9, ax=ax)
        ax.set_xlim(-.5, 3.5)
        ax.set_ylim(-math.ceil(len(names)/4)+.3, .7)
        figure.tight_layout()
        figure.savefig(output, dpi=150, facecolor="white")
        plt.close(figure)
        paths.append(output)
    return paths
