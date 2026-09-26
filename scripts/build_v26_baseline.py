"""Read-only fresh V2.5 verification and pre-change identity visualizations."""
import hashlib
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs_v25_rerun"
OUT = ROOT / "outputs_v26"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def matches_pinned(path, expected):
    """Account for checkout hydration converting generated JSON/Python CRLF to LF."""
    if sha(path) == expected:
        return True
    if path.suffix.lower() not in {".json", ".py", ".yaml", ".txt"}:
        return False
    data = path.read_bytes()
    normalized = data.replace(b"\r\n", b"\n")
    if hashlib.sha256(normalized.replace(b"\n", b"\r\n")).hexdigest() == expected:
        return True
    # The prior test5 mask patch was applied with LF inside a CRLF file.
    if path.name == "reid.py" and "v25rerun" in str(path):
        lines = normalized.splitlines(keepends=True)
        start = next((i for i, line in enumerate(lines) if b"if mask is not None:" in line), None)
        if start is not None:
            end = next((i for i in range(start, len(lines)) if b"mask = None" in lines[i]), None)
            if end is not None:
                mixed = b"".join(line if start - 1 <= i <= end else line.replace(b"\n", b"\r\n")
                                 for i, line in enumerate(lines))
                return hashlib.sha256(mixed).hexdigest() == expected
    return False


def verify():
    manifest = read(BASE / "prediction_manifest.json")
    architecture = read(BASE / "architecture_manifest.json")
    if manifest["stage"] != "A_BLIND_INFERENCE_COMPLETE" or manifest["gt_read_before_freeze"]:
        raise ValueError("V2.5 rerun is not blind/frozen")
    if not matches_pinned(BASE / "architecture_manifest.json", manifest["architecture_manifest_sha256"]):
        raise ValueError("V2.5 architecture changed")
    for name, expected in architecture["frozen_component_sha256"].items():
        if not matches_pinned(ROOT / name, expected):
            raise ValueError(f"Frozen model/config changed: {name}")
    for name, expected in architecture["rerun_inference_code_sha256"].items():
        if not matches_pinned(ROOT / name, expected):
            raise ValueError(f"V2.5 inference code changed: {name}")
    for task, entry in manifest["videos"].items():
        if sha(ROOT / f"{task}.mp4") != entry["video_sha256"]:
            raise ValueError(f"Video changed: {task}")
        upstream = BASE / task / "upstream_v21"
        if not matches_pinned(upstream / "prediction_manifest.json", entry["v21_manifest_sha256"]):
            raise ValueError(f"V2.1 input manifest changed: {task}")
        if read(upstream / "run_status.json")["video_sha256"] != entry["video_sha256"]:
            raise ValueError(f"V2.1 input is stale: {task}")
        for name, expected in entry["predictions"].items():
            if not matches_pinned(BASE / task / name, expected):
                raise ValueError(f"V2.5 prediction changed: {task}/{name}")
    payload = {"schema": "v26-baseline-1", "v25_prediction_manifest_sha256": sha(BASE / "prediction_manifest.json"),
        "v25_architecture_manifest_sha256": sha(BASE / "architecture_manifest.json"),
        "pinned_manifest_newline_note": "Pinned Windows text validates after original CRLF restoration (including one mixed-LF patch in v25rerun/reid.py); binary videos and images match byte-for-byte.",
        "video_sha256": {f"{t}.mp4": e["video_sha256"] for t, e in manifest["videos"].items()},
        "v25_v21_input_manifest_sha256": {t: e["v21_manifest_sha256"] for t, e in manifest["videos"].items()},
        "frozen_component_sha256": architecture["frozen_component_sha256"],
        "v25_reid": architecture["reid"], "gt_used": False}
    OUT.mkdir(exist_ok=True)
    path = OUT / "baseline_manifest.json"
    if path.exists() and read(path) != payload:
        raise ValueError("V2.6 baseline manifest differs")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def frame(task, index):
    cap = cv2.VideoCapture(str(ROOT / f"{task}.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(index))
    okay, image = cap.read()
    cap.release()
    if not okay:
        raise OSError(f"Cannot decode {task} frame {index}")
    return image


def box_crop(task, index, bbox, mask=None):
    from memory_graph.v22.sam_tracking import decode_mask
    from memory_graph.v24.appearance import crop_rgb
    image = frame(task, index)
    decoded = decode_mask(mask) if mask else None
    try:
        crop = crop_rgb(image, bbox, decoded)
    except ValueError:
        crop = crop_rgb(image, bbox)
    return cv2.cvtColor(crop, cv2.COLOR_RGB2BGR)


def important_candidates(task, groups):
    chosen = {"test7": [("candidate_004", 636), ("candidate_014", 720), ("candidate_015", 888)],
              "test8": [("candidate_009", 804), ("candidate_014", 888),
                        ("candidate_018", 888), ("candidate_020", 888)]}.get(task)
    if chosen is not None:
        return [(next(g for g in groups if g["candidate_id"] == cid), f) for cid, f in chosen]
    return [(g, g["observations"][0]["frame_index"]) for g in groups[:8]]


def candidate_observation(group, index):
    rows = [o for o in group["observations"] if o["frame_index"] == index]
    return max(rows or group["observations"], key=lambda o: o["confidence"])


def baseline_decisions(audit):
    result = {}
    for attempt in audit["attempts"]:
        for row in attempt.get("candidate_decisions", []):
            result.setdefault(row["candidate_entity_id"], row)
            if row["decision"] == "MATCH":
                result[row["candidate_entity_id"]] = row
    return result


def identity_timeline(task, output):
    timeline = read(BASE / task / "identity_timeline.json")["phone_timeline"]
    binding = read(BASE / task / "target_binding_audit.json")["bound_target"]
    stream = read(BASE / task / "candidate_stream.json")["observations"]
    audit = read(BASE / task / "reid_audit.json")
    meta = read(BASE / task / "upstream_v21/event_analysis/video_metadata.json")
    selected = {0, binding["frame_index"], meta["sampled_frames"][-1]["frame_index"]}
    trusted = [r["frame_index"] for r in timeline if r["state"] == "VISIBLE_TRUSTED"]
    if trusted:
        selected.add(max(trusted))
    selected.update(a["frame_index"] for a in audit["attempts"] if a["decision"] == "MATCH")
    if task == "test7": selected.update((636, 720, 888))
    if task == "test8": selected.update((804, 888, 918))
    selected = sorted(selected)
    if len(selected) > 8:
        selected = selected[:4] + selected[-4:]
    detections = read(BASE / task / "upstream_v21/event_analysis/detections.json")
    fig = plt.figure(figsize=(max(15, len(selected) * 3), 7.5), layout="constrained")
    grid = fig.add_gridspec(2, len(selected), height_ratios=[2, 1])
    for i, f in enumerate(selected):
        img = frame(task, f)
        for d in detections:
            if d["frame_index"] == f and d["class_name"] == "cell phone":
                x1,y1,x2,y2 = map(int, d["bbox"])
                cv2.rectangle(img, (x1,y1), (x2,y2), (0, 230, 255), 3)
        ax = fig.add_subplot(grid[0, i])
        ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        candidates = sorted({e["candidate_id"] for e in stream if e["frame_index"] == f and e.get("candidate_id")})
        ax.set_title(f"f{f} / {f/meta['fps']:.1f}s\n" + (", ".join(candidates[:3]) or "YOLO phone boxes: yellow"), fontsize=10)
        ax.axis("off")
    ax = fig.add_subplot(grid[1, :])
    map_state = {None: 0, "UNOBSERVED": 1, "VISIBLE_TRUSTED": 3}
    ax.step([r["frame_index"] for r in timeline], [map_state.get(r["state"], 2) for r in timeline], where="mid")
    ax.set_yticks([0,1,2,3], ["NO_ENTITY", "UNOBSERVED", "SAM_SUPPORTED/OTHER", "TRUSTED"])
    ax.set_xlabel("Video frame"); ax.set_ylabel("phone_01 observed state")
    for attempt in audit["attempts"]:
        if attempt["decision"] == "MATCH":
            ax.axvline(attempt["frame_index"], color="green", linewidth=2, label="V2.5 MATCH/SAM reinit")
    for e in stream:
        if e.get("candidate_id"):
            ax.scatter(e["frame_index"], .4, color="orange", s=5)
    if any(a["decision"] == "MATCH" for a in audit["attempts"]): ax.legend()
    fig.suptitle(f"{task}: V2.5 persistent identity timeline (yellow boxes = raw YOLO phone)")
    fig.savefig(output / "identity_timeline.png", dpi=150)
    plt.close(fig)


def reid_timeline(task, output):
    stream = read(BASE / task / "candidate_stream.json")["observations"]
    audit = read(BASE / task / "reid_audit.json")
    timeline = read(BASE / task / "identity_timeline.json")["phone_timeline"]
    decisions = baseline_decisions(audit)
    candidates = read(BASE / task / "candidate_grouping_audit.json")["candidates"]
    fig, ax = plt.subplots(figsize=(18, 8), layout="constrained")
    all_ids = [g["candidate_id"] for g in candidates]
    for i, g in enumerate(candidates):
        fs = [o["frame_index"] for o in g["observations"]]
        ax.plot([min(fs), max(fs)], [i, i], color="#b0b0b0", linewidth=3)
        row = decisions.get(g["candidate_id"])
        if row:
            f = row["candidate_frame"]
            color = "green" if row["decision"] == "MATCH" else "#d18400"
            ax.scatter(f, i, color=color, marker="D" if row["decision"] == "MATCH" else "o", s=80)
            sim = row["appearance"]["max_similarity"]
            second = row["second_candidate_similarity"]
            margin = row["best_vs_second_margin"]
            label = f"{g['candidate_id']} trk{g['source_track_ids']} sim={sim:.3f} second={second:.3f} margin={margin:.3f}" if second is not None else f"{g['candidate_id']} trk{g['source_track_ids']} sim={sim:.3f} second=N/A margin=N/A"
            ax.annotate(f"{label} {row['decision']}", (f,i), xytext=(6,5), textcoords="offset points", fontsize=7)
        else:
            f = fs[0]
            ax.scatter(f, i, color="#777777", marker="x", s=50)
            ax.annotate(f"{g['candidate_id']} trk{g['source_track_ids']} NOT_EVALUATED", (f,i), xytext=(6,3), textcoords="offset points", fontsize=7)
    unobserved = [r["frame_index"] for r in timeline if r["state"] == "UNOBSERVED"]
    if unobserved: ax.axvline(min(unobserved), color="blue", linestyle="--", label="target UNOBSERVED")
    for attempt in audit["attempts"]:
        if attempt["decision"] == "MATCH": ax.axvline(attempt["frame_index"], color="green", alpha=.45, label="MATCH / SAM reinit")
    ax.set_ylim(-1, max(1, len(all_ids))); ax.set_yticks(range(len(all_ids)), all_ids, fontsize=7)
    ax.set_xlabel("Frame / time progression"); ax.set_ylabel("Candidate hypotheses")
    ax.set_title(f"{task}: V2.5 Re-ID events — all admitted candidates; x = not evaluated")
    ax.grid(axis="x", alpha=.2); ax.legend(loc="upper right")
    fig.savefig(output / "reid_timeline.png", dpi=160)
    plt.close(fig)


def contact_sheet(task, output):
    groups = read(BASE / task / "candidate_grouping_audit.json")["candidates"]
    audit = read(BASE / task / "reid_audit.json")
    registry = read(BASE / task / "entity_registry.json")
    decisions = baseline_decisions(audit)
    bank = next((a.get("bank_prototypes") for a in reversed(audit["attempts"]) if a.get("bank_prototypes")), None)
    prototypes = bank["prototypes"] if bank else []
    target_sam = read(BASE / task / "sam/sam_continuity_log.json")
    masks = {}
    for segment in target_sam["segments"]:
        masks.update(segment["masks_rle"])
    trusted = next((e for e in registry["entities"] if e["entity_id"] == "phone_01"), None)
    selected = important_candidates(task, groups)
    cols = 4; tile_w = 365; tile_h = 320
    rows = 1 + (len(selected)+cols-1)//cols
    sheet = np.full((rows*tile_h, cols*tile_w, 3), 250, np.uint8)
    cv2.putText(sheet, "PHONE_01 TRUSTED APPEARANCE BANK", (12,28), cv2.FONT_HERSHEY_SIMPLEX,.75,(0,0,0),2)
    for i, proto in enumerate(prototypes[:4]):
        f = proto["frame_index"]
        obs = next((o for o in trusted["observation_history"] if o["frame_index"] == f and o["source_object_id"] == proto["source"]), None)
        if not obs: continue
        mask = next((value for key,value in masks.items() if key.startswith(f"{f}:")), None)
        crop = box_crop(task, f, obs["bbox"], mask)
        x=i*tile_w;y=0
        sheet[y+65:y+270,x+12:x+tile_w-12]=cv2.resize(crop,(tile_w-24,205))
        cv2.putText(sheet,f"f{f} {proto['source']} conf={obs['detector_confidence']:.2f}",(x+12,y+292),cv2.FONT_HERSHEY_SIMPLEX,.48,(0,0,0),1)
        cv2.putText(sheet,f"SAM supported: {proto['mask_used']}",(x+12,y+310),cv2.FONT_HERSHEY_SIMPLEX,.48,(0,0,0),1)
    for n,(group,f) in enumerate(selected):
        obs = candidate_observation(group,f)
        crop = box_crop(task,obs["frame_index"],obs["bbox"])
        x=(n%cols)*tile_w;y=(1+n//cols)*tile_h
        sheet[y+30:y+235,x+12:x+tile_w-12]=cv2.resize(crop,(tile_w-24,205))
        row = decisions.get(group["candidate_id"])
        decision = row["decision"] if row else "NOT_EVALUATED"
        sim = f"{row['appearance']['max_similarity']:.3f}" if row else "N/A"
        margin = f"{row['best_vs_second_margin']:.3f}" if row and row["best_vs_second_margin"] is not None else "N/A"
        cv2.putText(sheet,f"{group['candidate_id']} f{obs['frame_index']} trk{obs['source_track_id']}",(x+12,y+20),cv2.FONT_HERSHEY_SIMPLEX,.53,(0,0,0),1)
        cv2.putText(sheet,f"V2.5 {decision} sim={sim} margin={margin}",(x+12,y+258),cv2.FONT_HERSHEY_SIMPLEX,.46,(0,0,0),1)
        cv2.putText(sheet,"V2.6 pending | review pending",(x+12,y+283),cv2.FONT_HERSHEY_SIMPLEX,.47,(0,0,0),1)
    cv2.imwrite(str(output / "reid_contact_sheet.png"), sheet)


def main():
    verify()
    for i in range(3,10):
        task=f"test{i}"; output=OUT / "baseline_visualization" / task
        output.mkdir(parents=True, exist_ok=True)
        identity_timeline(task,output)
        reid_timeline(task,output)
        contact_sheet(task,output)
        print(task,"baseline visualizations complete",flush=True)


if __name__ == "__main__":
    main()
