from pathlib import Path
from .graph_visualizer import plt


def render_timeline(events, duration, path):
    figure, ax = plt.subplots(figsize=(16, max(5, len(events)*.25+2)))
    for i, event in enumerate(events):
        color = "#1976a3" if event.selected else "#a5adb5"
        ax.plot([event.start_time, event.end_time], [i, i], color=color, linewidth=3)
        ax.scatter([event.peak_time], [i], color=color, marker="^", s=35)
        ax.text(event.end_time+.15, i, f"{event.event_type} | IDs {','.join(map(str,event.involved_track_ids[:5]))}"
                + (" ..." if len(event.involved_track_ids) > 5 else ""), fontsize=7, va="center", clip_on=True)
    ax.set_yticks(range(len(events)), [e.event_id for e in events], fontsize=7)
    ax.set_xlim(0, duration*1.35)
    ax.set_xlabel("Video timestamp (seconds)")
    ax.set_title("V2 event proposals | blue: selected windows; grey: skipped by budget/duplicate suppression\nCandidates are not confirmed semantic actions")
    ax.grid(axis="x", alpha=.2)
    ax.invert_yaxis()
    figure.tight_layout()
    figure.savefig(path, dpi=130)
    plt.close(figure)
