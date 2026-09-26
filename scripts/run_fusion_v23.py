"""GT-free V2.3 fusion run from frozen V2.1 and V2.2 artifacts."""
from collections import Counter
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v22.sam_tracking import ROOT
from memory_graph.v23.fusion import run


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def render_timeline(rows, audit, output, task):
    fig, ax = plt.subplots(figsize=(16, 4))
    codes = {None: 0, "UNOBSERVED": 1, "AMBIGUOUS": 2, "CONFLICT": 3,
             "VISIBLE_PROPAGATED": 4, "VISIBLE_TRUSTED": 5}
    colors = {0: "#d3d3d3", 1: "#8e959c", 2: "#e6a23c", 3: "#c84242", 4: "#2f88bd", 5: "#2ca26f"}
    for row in rows:
        t, state = row["timestamp"], row["state"]
        ax.scatter(t, 2, color="#5b666e" if row["raw_phone_boxes"] else "#dedede", s=17)
        ax.scatter(t, 1, color="#4169e1" if row["sam_initial_present"] else "#dedede", s=17)
        ax.scatter(t, 0, color=colors[codes[state]], s=30)
    for item in audit:
        if item["entity_id"] == "phone_01" and item["decision"] in {"CONFLICT", "AMBIGUOUS"}:
            ax.annotate(item["decision"], (item["timestamp"], 0), xytext=(0, 8),
                        textcoords="offset points", fontsize=6, rotation=90)
    if task == "task2":
        ax.axvline(312 / 29.986, color="red", linestyle="--", alpha=.55)
        ax.annotate("f312 review", (312 / 29.986, 2.3), rotation=90, fontsize=7)
    ax.set_yticks([0, 1, 2], ["phone_01 registry state", "initial SAM target", "any raw YOLO cell-phone"])
    ax.set_ylim(-.5, 2.8)
    ax.set_xlabel("seconds; sampled inference frames (no GT interpolation)")
    ax.set_title(f"{task} YOLO + SAM persistent entity fusion")
    legend = [Line2D([0], [0], marker="o", color="w", markerfacecolor=colors[codes[state]], markersize=7,
                     label=state) for state in ["VISIBLE_TRUSTED", "VISIBLE_PROPAGATED", "AMBIGUOUS", "CONFLICT", "UNOBSERVED"]]
    ax.legend(handles=legend, loc="upper right", ncol=3, fontsize=7)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def main():
    for task in ("task1", "task2"):
        result = run(task)
        registry = result["registry"]
        output = ROOT / "outputs_v23" / task
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / "entity_registry.json", {
            "task": task, "target_entity_id": "phone_01", "provenance": result["provenance"],
            "entities": list(registry.entities.values()), "track_to_entity": registry.track_to_entity,
            "sam_to_entity": registry.sam_to_entity, "phone_timeline": result["phone_states"]})
        write_json(output / "fusion_audit.json", registry.audit)
        write_json(output / "graph_snapshots.json", {
            "task": task, "reference_frame": "image_plane", "snapshots": result["snapshots"]})
        render_timeline(result["phone_states"], registry.audit, output / "entity_timeline.png", task)
        counts = Counter(a["decision"] for a in registry.audit)
        print(task, "entities", len(registry.entities), "audit", dict(counts),
              "phone_sam", registry.entities["phone_01"]["sam_sources"])


if __name__ == "__main__":
    main()
