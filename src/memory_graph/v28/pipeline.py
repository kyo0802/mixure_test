"""Replay frozen V2.6/V2.7 evidence into V2.8; no perception model or reference label is loaded."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from memory_graph.v27.pipeline import load_inputs, verify_freeze as verify_v27_freeze

from .local_subgraph import build_local_subgraph
from .memory import build_memory, object_memory
from .models import Config, record
from .physical_reasoner import reason_all
from .search_planner import find, plan_text

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v28"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write(path: Path, value: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def _mark_transitions(graph: dict, frames: list[dict], config: Config) -> None:
    target_frames = {row["frame"] for row in frames
                     if any(o.entity_id == config.target_id and o.trusted for o in row["observations"])}
    frame_rows = {row["frame"]: row for row in frames}
    ordered = [row["frame"] for row in frames]
    for segment in graph["primary_segments"]:
        later = [frame for frame in ordered if frame > segment["end_frame"]]
        loss = next((frame for frame in later if frame_rows[frame].get("upstream_state") == "UNOBSERVED"
                     and frame not in target_frames), None)
        disappears = loss is not None and frame_rows[loss]["time"] - segment["end_time"] <= config.maximum_support_gap_seconds + .01
        later_seen = any(frame > (loss or segment["end_frame"]) for frame in target_frames)
        for row in segment["observations"]:
            row["target_disappears_after"] = disappears
            row["remains_unobserved"] = disappears and not later_seen
            row["reappeared_consistently"] = False


def _mask_audit(task: str) -> dict:
    registry = json.loads((ROOT / f"outputs_v26/{task}/entity_registry.json").read_text(encoding="utf-8"))
    target = next(e for e in registry["entities"] if e["entity_id"] == "phone_01")
    trusted = [row for row in target.get("observation_history", []) if row.get("trusted") is True]
    refs = [row["mask_ref"] for row in trusted if row.get("mask_ref")]
    return {"trusted_target_observations_in_registry": len(trusted), "trusted_mask_references": len(refs),
            "mask_evidence_exists": bool(refs)}


def _evidence_audit(task: str, frames: list[dict], graph: dict, decisions: list[dict]) -> dict:
    trusted_frames = sorted({row["frame"] for row in frames
                             if any(o.entity_id == "phone_01" and o.trusted for o in row["observations"])})
    anchor_rows = []
    for segment in graph["primary_segments"]:
        anchor_rows.append({"entity_id": segment["object"], "raw_label": segment["raw_label"],
                            "semantic_roles": segment["semantic_roles"],
                            "co_visible_frames": len(segment["support_frames"]),
                            "max_continuous_support_seconds": segment["end_time"] - segment["start_time"],
                            "segment_id": segment["segment_id"]})
    transition = [d for d in decisions if d["candidate_relation"] != "NEAR"
                  and d["temporal_evidence"]["pattern_present"]]
    usable_candidates = [d for d in decisions if d["decision"] in {"CANDIDATE", "PROMOTED"}]
    status = ("EVALUABLE_RELATION_PATTERN" if transition else
              "EVALUABLE_CONTEXT_ONLY" if usable_candidates else "INSUFFICIENT_EVIDENCE")
    reasons = []
    if not trusted_frames:
        reasons.append("no trusted target frames")
    if not anchor_rows:
        reasons.append("no stable target-anchor temporal segment")
    if anchor_rows and not transition:
        reasons.append("stable context exists but no relation-specific placement/interaction transition pattern")
    mask = _mask_audit(task)
    if not mask["mask_evidence_exists"]:
        reasons.append("no trusted target mask references in frozen registry")
    reasons.append("no cached candidate-scoped VLM verification")
    return {"schema": "v28_evidence_availability_1", "task": task,
            "trusted_target_frames": len(trusted_frames), "trusted_target_frame_indices": trusted_frames,
            "candidate_primary_anchors": anchor_rows,
            "target_anchor_co_visible_frames": sum(row["co_visible_frames"] for row in anchor_rows),
            "max_continuous_support_seconds": max((r["max_continuous_support_seconds"] for r in anchor_rows), default=0),
            **mask, "placement_transition_evidence_exists": bool(transition),
            "placement_transition_candidates": [d["candidate_id"] for d in transition],
            "vlm_candidate_verification_available": False,
            "physical_reasoning_evaluable": bool(usable_candidates), "status": status, "reasons": reasons}


def _connected_metrics(graph: dict) -> dict:
    nodes = {n["entity_id"] for n in graph["nodes"]}
    reachable = {graph["target"]}
    changed = True
    while changed:
        before = len(reachable)
        reachable |= {e["target"] for e in graph["edges"] if e["source"] in reachable}
        changed = len(reachable) != before
    return {"entity_count": len(nodes), "hop0_count": sum(n["hop"] == 0 for n in graph["nodes"]),
            "hop1_count": sum(n["hop"] == 1 for n in graph["nodes"]),
            "hop2_count": sum(n["hop"] == 2 for n in graph["nodes"]),
            "relation_count": len(graph["edges"]), "disconnected_node_count": len(nodes - reachable),
            "irrelevant_branch_count": 0}


def run_video(task: str, config: Config | None = None) -> dict:
    config = config or Config()
    verify_v27_freeze()
    frames, provenance = load_inputs(task)
    size = tuple(provenance["frame_size"])
    graph = build_local_subgraph(frames, size, config)
    _mark_transitions(graph, frames, config)
    candidates = reason_all(graph["primary_segments"], size, config)
    decisions = [record(c) for c in candidates]
    memory = build_memory(frames, graph, decisions)
    for decision in decisions:
        decision["source_snapshots"] = memory["source_snapshot_by_segment"].get(decision["segment_id"], [])
    lifetime = object_memory(memory)
    plan = find(lifetime)
    audit = _evidence_audit(task, frames, graph, decisions)
    folder = OUT / task
    folder.mkdir(parents=True, exist_ok=True)
    identity_counts = Counter(row["identity"] for row in graph["identity_audit"] if not row["memory_update_authorized"])
    write(folder / "evidence_availability.json", audit)
    write(folder / "observations.json", {"schema": "v28_observations_1", "config": asdict(config),
          "provenance": provenance, "identity_audit": graph["identity_audit"],
          "blocked_identity_counts": dict(identity_counts),
          "observation_relations_are_physical": False})
    write(folder / "local_subgraph.json", graph)
    write(folder / "anchor_candidates.json", {"primary": graph["primary_segments"], "context": graph["context_segments"]})
    write(folder / "physical_relation_candidates.json", decisions)
    write(folder / "physical_relation_decisions.json", decisions)
    write(folder / "relation_episodes.json", memory["episodes"])
    write(folder / "temporal_memory.json", {"schema": "v28_temporal_memory_1", "target": memory["target"],
          "snapshots": memory["snapshots"], "events": memory["events"]})
    write(folder / "object_memory_phone_01.json", lifetime)
    write(folder / "phone_01_lifetime.json", lifetime)
    write(folder / "search_candidates.json", plan)
    (folder / "search_plan.txt").write_text(plan_text(plan), encoding="utf-8")
    metrics = _connected_metrics(graph)
    return {"task": task, "sampled_frames": len(frames), "target_state": memory["target"]["state"],
            "last_trusted_time": memory["target"]["last_seen_time"], "upstream_entities": provenance["upstream_entity_count"],
            "v27_memory_entities": json.loads((ROOT / f"outputs_v27/{task}/object_memory_phone_01.json").read_text(encoding="utf-8"))["entities"].__len__(),
            **metrics, "temporal_snapshots": len(memory["snapshots"]),
            "physical_candidates": sum(d["decision"] == "CANDIDATE" for d in decisions),
            "physical_promotions": sum(d["decision"] == "PROMOTED" for d in decisions),
            "uncertain_or_rejected": sum(d["decision"] in {"UNCERTAIN", "REJECTED"} for d in decisions),
            "relation_decisions": dict(Counter(f"{d['candidate_relation']}:{d['decision']}" for d in decisions)),
            "search_candidates": len(plan["candidates"]), "evidence_status": audit["status"],
            "input_sha256": provenance["input_sha256"]}


def run_all() -> dict:
    if (OUT / "prediction_manifest.json").exists():
        raise RuntimeError("V2.8 predictions are frozen; use a new version for another inference run")
    verify_v27_freeze()
    videos = [run_video(f"test{number}") for number in range(3, 10)]
    summary = {"schema": "v28_summary_1", "videos": videos,
               "scope": "Frozen observation replay; no detector, SAM, Re-ID, VLM, or reference-label inference"}
    evidence = [json.loads((OUT / row["task"] / "evidence_availability.json").read_text(encoding="utf-8")) for row in videos]
    write(OUT / "summary.json", summary)
    write(OUT / "evidence_availability.json", evidence)
    write(OUT / "evidence_availability_summary.json", {
        "schema": "v28_evidence_availability_summary_1", "videos": evidence,
        "evaluable_videos": sum(v["physical_reasoning_evaluable"] for v in evidence),
        "videos_with_mask_evidence": sum(v["mask_evidence_exists"] for v in evidence),
        "videos_with_vlm_verification": sum(v["vlm_candidate_verification_available"] for v in evidence)})
    return summary


def freeze() -> dict:
    verify_v27_freeze()
    files = {}
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name not in {"prediction_manifest.json", "evaluation.json", "evaluation_summary.json", "V28_REPORT.md"}:
            files[path.relative_to(ROOT).as_posix()] = sha(path)
    source = {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted((ROOT / "src/memory_graph/v28").glob("*.py"))}
    for name in ("run_v28.py", "render_v28_graphs.py"):
        source[f"scripts/{name}"] = sha(ROOT / "scripts" / name)
    result = {"schema": "v28_prediction_freeze_1", "freeze_utc": datetime.now(timezone.utc).isoformat(),
              "inference_used_reference_labels": False, "perception_models_run": False,
              "vlm_verification_run": False, "files_sha256": files, "source_sha256": source,
              "v27_prediction_manifest_sha256": sha(ROOT / "outputs_v27/prediction_manifest.json")}
    write(OUT / "prediction_manifest.json", result)
    return result


def verify_freeze() -> None:
    verify_v27_freeze()
    manifest = json.loads((OUT / "prediction_manifest.json").read_text(encoding="utf-8"))
    if sha(ROOT / "outputs_v27/prediction_manifest.json") != manifest["v27_prediction_manifest_sha256"]:
        raise ValueError("V2.7 prediction manifest changed")
    for relative, digest in {**manifest["files_sha256"], **manifest["source_sha256"]}.items():
        if sha(ROOT / relative) != digest:
            raise ValueError(f"Frozen V2.8 file changed: {relative}")
