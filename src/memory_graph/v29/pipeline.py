"""V2.9 frozen-evidence experiment stages."""
from __future__ import annotations

from pathlib import Path
import json
from collections import Counter
from datetime import datetime, timezone

from memory_graph.v27.pipeline import ROOT, load_inputs, write, sha
from memory_graph.v28.pipeline import verify_freeze as verify_v28
from .mask_evidence import load_video_masks
from .placement_events import detect_events

OUT = ROOT / "outputs_v29"
TASKS = [f"test{i}" for i in range(3, 10)]


def stage_ab():
    if (OUT / "prediction_manifest.json").exists():
        raise RuntimeError("V2.9 predictions already frozen")
    verify_v28()
    audit = []
    for task in TASKS:
        rows, result = load_video_masks(task)
        write(OUT / task / "mask_evidence.json", rows)
        audit.append(result)
    write(OUT / "mask_evidence_audit.json", {"schema": "v29_mask_audit_1", "videos": audit,
          "finding": "Frozen SAM2.1 RLE and mask_ref exist; V2.8 did not admit V2.6 SAM history because trusted=False. V2.9 independently joins accepted fusion and contemporaneous identity state."})
    events = []
    for task in TASKS:
        frames, provenance = load_inputs(task)
        rows = json.loads((OUT/task/"mask_evidence.json").read_text(encoding="utf-8"))
        found = detect_events(frames, rows, tuple(provenance["frame_size"]), provenance["fps"])
        write(OUT / task / "placement_event_candidates.json", found)
        events.append({"task": task, "events": len(found), "peak_frames": [e["peak_frame"] for e in found]})
    write(OUT / "event_discovery_summary.json", events)
    return audit, events


def stage_dense(tasks: list[str] | None = None):
    if (OUT / "prediction_manifest.json").exists():
        raise RuntimeError("V2.9 predictions already frozen")
    verify_v28()
    from .dense_reinspection import DenseRunner
    runner = DenseRunner()
    summaries = []
    for task in tasks or TASKS:
        events = json.loads((OUT/task/"placement_event_candidates.json").read_text(encoding="utf-8"))
        masks = json.loads((OUT/task/"mask_evidence.json").read_text(encoding="utf-8"))
        _, provenance = load_inputs(task)
        windows = []
        for event in events:
            folder = OUT/task/"dense_windows"/event["event_id"]
            windows.append(runner.run(task, event, masks, provenance["fps"], folder))
        write(OUT/task/"dense_reinspection_summary.json", {"task": task, "windows": windows})
        summaries.append({"task": task, "windows": windows})
        print(task, [(w["event_id"], w["dense_frames"], w["trusted_dense_masks"]) for w in windows], flush=True)
    return summaries


def stage_candidates(tasks: list[str] | None = None):
    if (OUT / "prediction_manifest.json").exists():
        raise RuntimeError("V2.9 predictions already frozen")
    verify_v28()
    from .physical_candidates import generate_candidates
    summary = []
    for task in tasks or TASKS:
        _, provenance = load_inputs(task)
        events = json.loads((OUT/task/"placement_event_candidates.json").read_text(encoding="utf-8"))
        candidates = []
        for event in events:
            folder = OUT/task/"dense_windows"/event["event_id"]
            dense = json.loads((folder/"dense_observations.json").read_text(encoding="utf-8"))
            masks = json.loads((folder/"target_masks.json").read_text(encoding="utf-8"))
            new = generate_candidates(task, event, dense, masks, tuple(provenance["frame_size"]))
            for candidate in new:
                candidate["candidate_id"] = f"PRC{len(candidates)+1:04d}"
                candidates.append(candidate)
        write(OUT/task/"physical_relation_candidates.json", candidates)
        summary.append({"task": task, "candidates": len(candidates),
                        "vlm_eligible": sum(c["vlm_verification_required"] for c in candidates)})
        print(task, summary[-1], flush=True)
    write(OUT/"candidate_generation_summary.json", summary)
    return summary


def stage_vlm(tasks: list[str] | None = None):
    if (OUT / "prediction_manifest.json").exists():
        raise RuntimeError("V2.9 predictions already frozen")
    verify_v28()
    from .vlm_relation_verifier import CandidateVLM
    verifier = CandidateVLM()
    summary = []
    for task in tasks or TASKS:
        candidates = json.loads((OUT/task/"physical_relation_candidates.json").read_text(encoding="utf-8"))
        results = verifier.verify(task, candidates, OUT/task)
        summary.append({"task": task, "calls": len(results),
                        "valid": sum(r["status"] == "VALID" for r in results)})
    write(OUT/"vlm_verification_summary.json", summary)
    return summary


def stage_decisions():
    if (OUT / "prediction_manifest.json").exists():
        raise RuntimeError("V2.9 predictions already frozen")
    verify_v28()
    from memory_graph.v28.visualization import render_video
    from .physical_gate import decide
    from .memory_adapter import integrate
    from .diagnostics import test9_failure
    from .visualization import render_relation_explainer
    summary = []
    for task in TASKS:
        folder = OUT/task
        candidates = json.loads((folder/"physical_relation_candidates.json").read_text(encoding="utf-8"))
        verifications = json.loads((folder/"vlm_relation_verification.json").read_text(encoding="utf-8"))
        verified = {cid: row for row in verifications for cid in row["candidate_ids"]}
        decisions = [decide(c, verified.get(c["candidate_id"])) for c in candidates]
        write(folder/"physical_relation_decisions.json", decisions)
        masks = json.loads((folder/"mask_evidence.json").read_text(encoding="utf-8"))
        memory = integrate(task, decisions, candidates, masks, folder)
        render_relation_explainer(candidates, decisions, folder/"physical_relation_explainer.png")
        render_video(folder, task)
        events = json.loads((folder/"placement_event_candidates.json").read_text(encoding="utf-8"))
        if task == "test9":
            test9_failure(folder, masks, events)
        dense = json.loads((folder/"dense_reinspection_summary.json").read_text(encoding="utf-8"))["windows"]
        baseline = json.loads((ROOT/"outputs_v28"/task/"search_candidates.json").read_text(encoding="utf-8"))
        plan = json.loads((folder/"search_candidates.json").read_text(encoding="utf-8"))
        row = {"task": task, "trusted_masks": sum(m["trusted"] for m in masks),
               "placement_windows": len(events), "dense_frames": sum(w["dense_frames"] for w in dense),
               "dense_trusted_target_frames": sum(w["trusted_dense_masks"] for w in dense),
               "dense_phone_detections": sum(w["phone_detections"] for w in dense),
               "dense_anchor_detections": sum(w["anchor_detections"] for w in dense),
               "dense_known_anchor_covisibility": sum(w["known_anchor_covisible"] for w in dense),
               "relation_candidates": len(candidates), "vlm_calls": len(verifications),
               "vlm_valid": sum(v["status"] == "VALID" for v in verifications),
               "decisions": dict(Counter(d["decision"] for d in decisions)),
               "relation_breakdown": dict(Counter(f"{d['candidate_relation']}:{d['decision']}" for d in decisions)),
               "v28_search_candidates": len(baseline["candidates"]),
               "v29_search_candidates": len(plan["candidates"]), **memory}
        write(folder/"evidence_recovery.json", row)
        summary.append(row)
        print(task, row["decisions"], "search", row["v28_search_candidates"], "->", row["v29_search_candidates"], flush=True)
    write(OUT/"evidence_recovery_summary.json", {"schema": "v29_evidence_recovery_1", "videos": summary})
    return summary


def freeze():
    if (OUT/"prediction_manifest.json").exists():
        raise RuntimeError("V2.9 prediction manifest already exists")
    verify_v28()
    excludes = {"prediction_manifest.json", "evaluation_summary.json", "evaluation.json",
                "V29_REPORT.md", "V29_IMPLEMENTATION_PLAN.md"}
    files = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(OUT.rglob("*"))
             if p.is_file() and p.name not in excludes}
    source = {p.relative_to(ROOT).as_posix(): sha(p) for p in
              sorted((ROOT/"src/memory_graph/v29").glob("*.py"))}
    source["scripts/run_v29.py"] = sha(ROOT/"scripts/run_v29.py")
    source["tests/test_v29_evidence.py"] = sha(ROOT/"tests/test_v29_evidence.py")
    inputs = {f"test{i}.mp4": sha(ROOT/f"test{i}.mp4") for i in range(3, 10)}
    for name in ("sam2.1_hiera_small.pt", "yolo11s.pt"):
        inputs[f".models/{name}"] = sha(ROOT/".models"/name)
    inputs[".models/Qwen2.5-VL-3B-Instruct/download_provenance.json"] = sha(
        ROOT/".models/Qwen2.5-VL-3B-Instruct/download_provenance.json")
    result = {"schema": "v29_prediction_freeze_1", "freeze_utc": datetime.now(timezone.utc).isoformat(),
              "inference_used_reference_labels": False, "source_sha256": source,
              "files_sha256": files, "input_sha256": inputs,
              "v28_prediction_manifest_sha256": sha(ROOT/"outputs_v28/prediction_manifest.json")}
    write(OUT/"prediction_manifest.json", result)
    return result


def verify_freeze():
    verify_v28()
    manifest = json.loads((OUT/"prediction_manifest.json").read_text(encoding="utf-8"))
    if sha(ROOT/"outputs_v28/prediction_manifest.json") != manifest["v28_prediction_manifest_sha256"]:
        raise ValueError("V2.8 prediction manifest changed")
    for relative, digest in {**manifest["source_sha256"], **manifest["files_sha256"],
                             **manifest["input_sha256"]}.items():
        if sha(ROOT/relative) != digest:
            raise ValueError(f"Frozen V2.9 file changed: {relative}")
