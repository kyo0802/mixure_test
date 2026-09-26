"""Post-freeze visual diagnostic; reads predictions and source video only."""
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v241"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def frame(video, index):
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    okay, image = cap.read()
    cap.release()
    if not okay:
        raise OSError(f"Cannot read {video} frame {index}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def render(task):
    base = OUT / task
    pred = read(base / "identity_timeline.json")
    sam = read(base / "sam" / "sam_propagation_log.json")
    detections = read(base / "upstream_v21" / "event_analysis" / "detections.json")
    timeline = pred["phone_timeline"]
    target = pred["target_entity"]
    trusted = [o for o in target["observation_history"] if o["trusted"]]
    selected = [timeline[0]["frame_index"], pred["initialization"]["frame_index"],
                trusted[-1]["frame_index"] if trusted else pred["initialization"]["frame_index"],
                sam["late_selection"]["frame_index"] if sam["late_selection"] else timeline[-1]["frame_index"],
                timeline[-1]["frame_index"]]
    titles = ("start", "initial seed", "last trusted", "late candidates", "final sampled")
    fig, axes = plt.subplots(2, 5, figsize=(17, 5), gridspec_kw={"height_ratios": [2.7, 1]})
    for ax, index, title in zip(axes[0], selected, titles):
        ax.imshow(frame(ROOT / f"{task}.mp4", index))
        for det in detections:
            if det["frame_index"] == index and det["class_name"] == "cell phone":
                x1, y1, x2, y2 = det["bbox"]
                ax.add_patch(Rectangle((x1, y1), x2-x1, y2-y1, fill=False,
                                       edgecolor="cyan", linewidth=1.5))
        ax.set_title(f"{title}: f{index} ({index/30:.1f}s)", fontsize=9)
        ax.axis("off")
    ax = axes[1, 0]
    codes = {None: 0, "UNOBSERVED": 1, "AMBIGUOUS": 2, "CONFLICT": 3,
             "VISIBLE_PROPAGATED": 4, "VISIBLE_TRUSTED": 5}
    ax.plot([r["timestamp"] for r in timeline], [codes[r["state"]] for r in timeline], ".-", markersize=2)
    for index in selected:
        ax.axvline(index/30, alpha=.2, color="red")
    ax.set_yticks([0, 1, 2, 3, 4, 5], ["no entity", "unobserved", "ambiguous", "conflict", "SAM", "trusted"], fontsize=6)
    ax.set_xlabel("seconds")
    ax.grid(alpha=.2)
    for unused in axes[1, 1:]:
        unused.axis("off")
    fig.suptitle(f"{task} frozen prediction: cyan = raw YOLO phone box; image-plane only", fontsize=11)
    fig.tight_layout()
    fig.savefig(base / "timeline.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    manifest = read(OUT / "prediction_manifest.json")
    if manifest["stage"] != "A_BLIND_INFERENCE_COMPLETE":
        raise ValueError("Predictions not frozen")
    for i in range(3, 10):
        render(f"test{i}")
    print("Rendered seven post-freeze timelines")
