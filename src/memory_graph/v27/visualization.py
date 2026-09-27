"""Readable relation-node graphs; theme defaults rather than a fixed color palette."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from PIL import Image, ImageDraw, ImageFont

from .pipeline import OUT


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def relation_label(row: dict, search: bool = False) -> str:
    relation = "ANCHOR CONTEXT\n(image-relative)" if row["relation"] == "ANCHOR_CONTEXT" else row["relation"]
    if search:
        return f"SEARCH {row['rank']} / rule {row['priority_rule']}\n{relation}\n{row['status']}"
    return f"{relation}\n{row['start_time']:.2f}-{row['last_confirmed_time']:.2f}s\n{row['status']}"


def graph_png(path: Path, title: str, target: dict, entities: dict, rows: list[dict], search: bool = False) -> None:
    n = max(1, len(rows))
    fig, ax = plt.subplots(figsize=(13, max(3.1, 1.7 * n + 1.2)))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    edge = plt.rcParams["axes.edgecolor"]
    face = plt.rcParams["axes.facecolor"]
    text_color = plt.rcParams["text.color"]

    def node(x, y, text, rounded=False, target_node=False, status="ACTIVE"):
        width, height = (.23, .66 if n == 1 else .76 / n)
        alpha = .55 if status in {"ENDED", "STALE"} else 1
        linewidth = 3.5 if target_node else (2.7 if status == "LAST_TRUSTED" else 1.4)
        style = "--" if status in {"ENDED", "STALE"} else "-"
        if rounded:
            patch = FancyBboxPatch((x-width/2, y-height/2), width, height,
                                   boxstyle="round,pad=0.012,rounding_size=0.045",
                                   facecolor=face, edgecolor=edge, linewidth=linewidth, linestyle=style, alpha=alpha)
        else:
            patch = Rectangle((x-width/2, y-height/2), width, height,
                              facecolor=face, edgecolor=edge, linewidth=linewidth, linestyle=style, alpha=alpha)
        ax.add_patch(patch)
        ax.text(x, y, text, ha="center", va="center", fontsize=12 if not target_node else 13,
                fontweight="bold" if target_node else "normal", color=text_color, alpha=alpha,
                linespacing=1.4)

    target_text = f"{target['entity_id']}\n{target['state']}"
    if target.get("last_seen_time") is not None:
        target_text += f"\nlast trusted: {target['last_seen_time']:.2f}s"
    node(.14, .5, target_text, target_node=True)
    object_rows = {}
    for i, row in enumerate(rows):
        object_id = row["search_anchor"] if search else row["object"]
        object_rows.setdefault(object_id, []).append((1 - (i + .5) / n, row["status"]))
    object_positions = {key: sum(y for y, _ in values) / len(values) for key, values in object_rows.items()}
    for object_id, values in object_rows.items():
        statuses = {status for _, status in values}
        status = "LAST_TRUSTED" if "LAST_TRUSTED" in statuses else ("ACTIVE" if "ACTIVE" in statuses else "ENDED")
        node(.87, object_positions[object_id], f"{entities[object_id]['label']}\n{object_id}", status=status)
    for i, row in enumerate(rows):
        y = 1 - (i + .5) / n
        object_id = row["search_anchor"] if search else row["object"]
        node(.51, y, relation_label(row, search), rounded=True, status=row["status"])
        for start, end in [((.26, .5), (.38, y)), ((.64, y), (.75, object_positions[object_id]))]:
            ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=17,
                                         linewidth=1.4, color=edge, connectionstyle="arc3,rad=0"))
    if not rows:
        ax.text(.62, .5, "No supported spatial anchor\nLocation remains uncertain", ha="center", va="center",
                fontsize=15, color=text_color)
    fig.suptitle(title, fontsize=17, fontweight="bold")
    fig.text(.5, .015, "Historical evidence does not assert the target's current location.  Dashed = ended/stale.",
             ha="center", fontsize=10)
    fig.subplots_adjust(left=.015, right=.985, top=.82 if n == 1 else .92, bottom=.12)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def graph_mmd(path: Path, target: dict, entities: dict, rows: list[dict], search: bool = False) -> None:
    lines = ["flowchart LR", f'  target["{target["entity_id"]}<br/>{target["state"]}"]:::target']
    objects = {}
    for index, row in enumerate(rows):
        object_id = row["search_anchor"] if search else row["object"]
        label = relation_label(row, search).replace("\n", "<br/>")
        cls = "historical" if row["status"] in {"STALE", "ENDED"} else ("last" if row["status"] == "LAST_TRUSTED" else "current")
        if object_id not in objects:
            objects[object_id] = len(objects)
            lines.append(f'  o{objects[object_id]}["{entities[object_id]["label"]}<br/>{object_id}"]')
        lines += [f'  r{index}(["{label}"]):::{cls}',
                  f"  target --> r{index}", f"  r{index} --> o{objects[object_id]}"]
    if not rows:
        lines.append('  note["No supported spatial anchor; location uncertain"]')
    lines += ["  classDef target stroke-width:4px", "  classDef last stroke-width:3px",
              "  classDef historical stroke-dasharray:6 4,opacity:0.55", "  classDef current stroke-width:1.5px"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def lifecycle(folder: Path, memory: dict) -> None:
    events = memory["lifecycle"]
    labels = []
    episodes = {row["episode_id"]: row for row in memory["episodes"]}
    for event in events:
        if event["event"] == "IMPORTANT_ANCHOR_CHANGED":
            continue
        label = event["event"].replace("TARGET_", "").replace("IMPORTANT_", "")
        ref = event["details"].get("episode")
        if ref in episodes:
            relation = episodes[ref]
            label += f"\n{relation['relation']} {memory['entities'][relation['object']]['label']}"
        labels.append(f"{event['time']:.2f}s | {label}")
    if not labels:
        labels = ["No trusted target event"]
    fig, ax = plt.subplots(figsize=(12, max(3, len(labels) * .8)))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(labels))
    ax.axis("off")
    lines = ["flowchart TD"]
    for i, label in enumerate(labels):
        y = len(labels) - i - .5
        ax.text(.5, y, label, ha="center", va="center", fontsize=12,
                bbox={"boxstyle": "round,pad=0.4", "facecolor": plt.rcParams["axes.facecolor"],
                      "edgecolor": plt.rcParams["axes.edgecolor"]})
        if i:
            ax.annotate("", xy=(.5, y + .3), xytext=(.5, y + .7), arrowprops={"arrowstyle": "->"})
        safe = label.replace("\n", "<br/>")
        lines.append(f'  E{i}["{safe}"]')
        if i:
            lines.append(f"  E{i-1} --> E{i}")
    fig.suptitle("phone_01 evidence-derived lifecycle", fontsize=17)
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(folder / "phone_01_lifecycle.png", dpi=150)
    plt.close(fig)
    (folder / "phone_01_lifecycle.mmd").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_video(task: str) -> None:
    base = OUT / task
    temporal = read(base / "temporal_memory.json")
    memory = read(base / "object_memory_phone_01.json")
    plan = read(base / "search_candidates.json")
    folder = base / "graphs"
    (folder / "temporal").mkdir(parents=True, exist_ok=True)
    thumbnails = []
    timeline_mmd = ["flowchart LR"]
    for i, snapshot in enumerate(temporal["snapshots"]):
        name = snapshot["snapshot_id"]
        png = folder / "temporal" / f"{name}.png"
        title = f"{task} / {name} @ {snapshot['time']:.2f}s / {snapshot['meaning']}"
        graph_png(png, title, snapshot["target"], snapshot["entities"], snapshot["relations"])
        graph_mmd(png.with_suffix(".mmd"), snapshot["target"], snapshot["entities"], snapshot["relations"])
        with Image.open(png) as image:
            image.thumbnail((900, 480))
            thumbnails.append(image.copy().convert("RGB"))
        timeline_mmd.append(f'  {name}["{name} @ {snapshot["time"]:.2f}s<br/>{snapshot["target"]["state"]}"]')
        if i:
            timeline_mmd.append(f"  {temporal['snapshots'][i-1]['snapshot_id']} --> {name}")
    if thumbnails:
        # Use the default figure background from the rendered graph.
        background = thumbnails[0].getpixel((0, 0))
        cell_height = max(image.height for image in thumbnails) + 40
        overview = Image.new("RGB", (1840, 60 + ((len(thumbnails)+1)//2) * cell_height), background)
        draw = ImageDraw.Draw(overview)
        font = ImageFont.truetype(str(Path(plt.matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"), 23)
        draw.text((20, 15), f"{task}: temporal memory / read left to right, then next row", fill=plt.rcParams["text.color"], font=font)
        for index, thumb in enumerate(thumbnails):
            overview.paste(thumb, (20 + (index % 2) * 920, 60 + (index // 2) * cell_height))
        overview.save(folder / "temporal_memory_timeline.png")
    (folder / "temporal_memory_timeline.mmd").write_text("\n".join(timeline_mmd) + "\n", encoding="utf-8")
    graph_png(folder / "phone_01_lifetime_memory.png", f"{task} / phone_01 lifetime memory",
              memory["target"], memory["entities"], memory["episodes"])
    graph_mmd(folder / "phone_01_lifetime_memory.mmd", memory["target"], memory["entities"], memory["episodes"])
    graph_png(folder / "phone_01_search_graph.png", f"{task} / explainable search order",
              memory["target"], memory["entities"], plan["candidates"], search=True)
    graph_mmd(folder / "phone_01_search_graph.mmd", memory["target"], memory["entities"], plan["candidates"], search=True)
    lifecycle(folder, memory)
    # Alternate requested lifetime filenames export the same underlying view.
    for suffix in ("png", "mmd"):
        shutil.copyfile(folder / f"phone_01_lifetime_memory.{suffix}", base / f"phone_01_lifetime.{suffix}")
