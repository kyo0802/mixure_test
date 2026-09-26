"""GT-free V2.6 safe authorization over frozen fresh-input V2.5 evidence."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from memory_graph.v22 import sam_tracking as frozen
from memory_graph.v22.sam_tracking import read_json
from memory_graph.v24.appearance import MobileNetEmbedder, bank_summary
from memory_graph.v24.reid import decide, locked_parameters, registry_update
from memory_graph.v25rerun import reid as v25
from memory_graph.v25rerun.sam_route import SamRouter
from .authorization import authorize

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "outputs_v25_rerun"
OUT = ROOT / "outputs_v26"


class V26Embedder(v25.GenericEmbedder):
    def __init__(self):
        # Keep every new embedding cache entry outside the immutable V2.5 rerun.
        self.model = MobileNetEmbedder()
        self.model.cache_dir = OUT / "cache"
        self.model.cache_dir.mkdir(parents=True, exist_ok=True)
        self.frames = {}


class V26SamRouter(SamRouter):
    def __init__(self, task):
        import torch
        self.task = task
        self.torch = torch
        base = BASE / task / "upstream_v21" / "event_analysis"
        names = ("detections.json", "track_timelines.json", "video_metadata.json")
        self.inputs = {name: read_json(base / name) for name in names}
        self.hashes = {name: frozen.sha256(base / name) for name in names}
        self.output = OUT / task / "sam"
        self.output.mkdir(parents=True, exist_ok=True)
        for path in (frozen.SAM_DEPS, frozen.SAM_SOURCE):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        from sam2.build_sam import build_sam2_video_predictor
        self.predictor = build_sam2_video_predictor(frozen.CONFIG, str(frozen.CHECKPOINT),
                                                     device="cuda", apply_postprocessing=False)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def original_query_registry(task):
    registry = copy.deepcopy(read_json(BASE / task / "entity_registry.json"))
    query = next((e for e in registry["entities"] if e["entity_id"] == "phone_01"), None)
    if query is None:
        return registry, None
    # V2.5 appended its matched candidate to this saved entity. Those rows lack
    # an original observation source; remove them for a clean V2.6 comparison.
    original = [o for o in query["observation_history"] if o.get("source") is not None]
    query["observation_history"] = original
    query["last_seen"] = max((o["timestamp"] for o in original), default=query["last_seen"])
    trusted = [o for o in original if o["trusted"]]
    query["last_trusted_seen"] = max((o["timestamp"] for o in trusted), default=None)
    query.pop("appearance_memory", None)
    baseline_states = read_json(BASE / task / "identity_timeline.json")["phone_timeline"]
    query["state"] = baseline_states[-1]["state"] if baseline_states else "UNOBSERVED"
    registry.pop("reid_aliases", None)
    registry.pop("reidentified_at_frame", None)
    registry.pop("reidentified_from_candidate", None)
    registry.pop("reid_evidence", None)
    registry.pop("reid_confidence_state", None)
    old_match = read_json(BASE / task / "reid_audit.json").get("match_candidate_id")
    if old_match:
        summaries = read_json(BASE / task / "candidate_grouping_audit.json")["candidates"]
        prior = next(g for g in summaries if g["candidate_id"] == old_match)
        query["sam_sources"] = [source for source in query.get("sam_sources", [])
                                if source != f"sam_{old_match}"]
        for tid in prior["source_track_ids"]:
            key = str(tid)
            if registry["track_to_entity"].get(key) == "phone_01":
                registry["track_to_entity"].pop(key)
            query["yolo_sources"] = [source for source in query.get("yolo_sources", [])
                                    if source != f"track:{tid}"]
    return registry, query


def post_match_role(candidate_id, confirmed_id, candidate, scored_row):
    if candidate_id == confirmed_id:
        return "CONTINUATION_EVIDENCE"
    if confirmed_id in candidate.distinct_coexistence_with:
        return "NEW_DISTINCT_CANDIDATE"
    if scored_row["decision"] == "CONFIRMED_MATCH":
        return "CONFLICTING_IDENTITY_EVIDENCE"
    return "INSUFFICIENT_EVIDENCE"


def run_video(task):
    params, parameter_hash = locked_parameters()
    embedder = V26Embedder()
    if embedder.weight_sha256 != params["checkpoint_sha256"]:
        raise ValueError("Frozen MobileNet weights changed")
    output = OUT / task
    output.mkdir(parents=True, exist_ok=True)
    registry, full_query = original_query_registry(task)
    timeline = read_json(BASE / task / "identity_timeline.json")["phone_timeline"]
    candidates = v25.load_candidates(task)
    target_sam = v25.target_sam_rows(task)
    candidate_sam = v25.candidate_sam_rows(task)
    accepted_frames = {a["frame_index"] for a in registry["fusion_audit"]
        if a["observation_source"] == "sam" and a["entity_id"] == "phone_01" and a["decision"] == "MATCH"}
    attempts = []
    confirmed = None
    provisional_ids = set()
    reinit = {"status": "NONE_AUTHORIZED", "sam_reinitialization_executed": False,
              "guard_result": "POST_MATCH_CONTINUITY_NOT_FULLY_INTEGRATED"}
    if full_query is not None:
        for state_row in timeline:
            frame = state_row["frame_index"]
            current_ids = {cid for cid, c in candidates.items() if any(o["frame_index"] == frame for o in c.observations)}
            if not current_ids:
                continue
            if state_row["state"] != "UNOBSERVED":
                attempts.append({"frame_index": frame, "decision": "AUDIT_ONLY_TRUSTED_TARGET",
                                 "new_candidate_ids": sorted(current_ids), "candidate_decisions": [],
                                 "reason": "target still has trusted source evidence"})
                continue
            query = v25.query_snapshot(full_query, frame)
            if query is None:
                attempts.append({"frame_index": frame, "decision": "INSUFFICIENT_EVIDENCE",
                                 "new_candidate_ids": sorted(current_ids), "candidate_decisions": [],
                                 "reason": "no original trusted target history"})
                continue
            bank = v25.bank_at_frame(task, frame, query, target_sam, accepted_frames, embedder)
            if len(bank.prototypes) < params["minimum_evidence_prototypes"]:
                attempts.append({"frame_index": frame, "decision": "INSUFFICIENT_EVIDENCE",
                                 "new_candidate_ids": sorted(current_ids), "candidate_decisions": [],
                                 "bank_prototype_count": len(bank.prototypes),
                                 "reason": "insufficient frozen trusted appearance bank"})
                continue
            active = []
            for candidate in candidates.values():
                item = v25.candidate_at_frame(task, candidate, frame, candidate_sam, embedder, query["last_trusted_seen"])
                if item is not None:
                    active.append(item)
            if not active:
                continue
            contexts = {item["entity_id"]: {"match_sufficient": False, "world_fixed": False} for item in active}
            scored = decide(query, bank, active, params, contexts)
            decisions = authorize(scored, current_ids, params["minimum_match_similarity"],
                                  params["minimum_uniqueness_margin"])
            for row in decisions:
                cid = row["candidate_entity_id"]
                if confirmed is not None:
                    row["post_match_role"] = post_match_role(cid, confirmed["candidate_id"], candidates[cid], row)
                    row["authorization_decision"] = row["decision"]
                    if cid != confirmed["candidate_id"]:
                        row["decision"] = "AMBIGUOUS"
                        row["alias_authorized"] = False
                        row["trusted_bank_update_authorized"] = False
                        row["sam_reinitialization_authorized"] = False
                candidate = candidates[cid]
                if row["decision"] == "PROVISIONAL_MATCH":
                    provisional_ids.add(cid)
                    candidate.status = "PROVISIONAL_MATCH"
                elif row["decision"] == "CONFIRMED_MATCH" and confirmed is None:
                    candidate.status = "CONFIRMED_MATCH"
                elif candidate.status != "PROVISIONAL_MATCH" and candidate.status != "CONFIRMED_MATCH":
                    candidate.status = "AMBIGUOUS" if row["decision"] != "REJECTED" else "REJECTED"
                candidate.reid_history.append({"frame_index": frame, "decision": row["decision"],
                    "similarity": row["appearance"]["max_similarity"], "reason": row["v26_reason"]})
            new_confirmation = next((row for row in decisions if row["decision"] == "CONFIRMED_MATCH" and
                row["candidate_entity_id"] in current_ids), None) if confirmed is None else None
            attempts.append({"frame_index": frame, "timestamp": state_row["timestamp"],
                "query_last_trusted_frame": query["latest_trusted_observation"]["frame_index"],
                "bank_prototypes": bank_summary(bank), "new_candidate_ids": sorted(current_ids),
                "candidate_decisions": decisions,
                "decision": "CONFIRMED_MATCH" if new_confirmation else
                    ("PROVISIONAL_MATCH" if any(d["decision"] == "PROVISIONAL_MATCH" for d in decisions) else "AMBIGUOUS"),
                "after_first_confirmed_match": confirmed is not None})
            if new_confirmation is not None:
                cid = new_confirmation["candidate_entity_id"]
                matched = next(item for item in active if item["entity_id"] == cid)
                updated = registry_update("phone_01", matched, "MATCH", query, bank)
                updated["updated_entity"]["state"] = "MATCHED"
                registry["entities"] = [updated["updated_entity"] if e["entity_id"] == "phone_01" else e
                                        for e in registry["entities"]]
                registry.setdefault("reid_aliases", {})[cid] = "phone_01"
                for tid in candidates[cid].source_track_ids:
                    registry["track_to_entity"][str(tid)] = "phone_01"
                registry["reidentified_at_frame"] = frame
                registry["reidentified_from_candidate"] = cid
                confirmed = {"candidate_id": cid, "frame_index": frame, "similarity": new_confirmation["appearance"]["max_similarity"]}
                reinit = V26SamRouter(task).reinitialize_after_match(candidates[cid], new_confirmation["candidate_frame"])
                reinit["sam_reinitialization_executed"] = reinit["status"] == "EXECUTED"
                reinit["guard_result"] = "POST_MATCH_CONTINUITY_NOT_FULLY_INTEGRATED"
                reinit["authorized_by"] = "CONFIRMED_MATCH"
    stream = copy.deepcopy(read_json(BASE / task / "candidate_stream.json"))
    for event in stream["observations"]:
        cid = event.get("candidate_id")
        event["v25_reid_evaluated"] = event.get("reid_evaluated", False)
        event["v25_reid_decision"] = event.get("reid_decision")
        event["reid_evaluated"] = False
        event["reid_decision"] = "NOT_EVALUATED"
        if cid:
            history = [h for h in candidates[cid].reid_history if h["frame_index"] == event["frame_index"]]
            if history:
                event["reid_evaluated"] = True
                event["reid_decision"] = history[-1]["decision"]
    grouping = copy.deepcopy(read_json(BASE / task / "candidate_grouping_audit.json"))
    grouping["candidates"] = [c.summary() for c in candidates.values()]
    output_timeline = {"task": task, "phone_timeline": timeline,
        "candidate_lifecycles": [{"candidate_id": cid, "status": c.status,
                                  "first_frame": c.observations[0]["frame_index"],
                                  "last_frame": c.observations[-1]["frame_index"]} for cid,c in candidates.items()],
        "reid_event_frames": [a["frame_index"] for a in attempts], "gt_accessed": False}
    audit = {"task": task, "parameter_manifest_sha256": parameter_hash,
        "authorization_policy": "no second candidate => provisional; fresh winning evidence + frozen competitor margin => confirmed",
        "attempts": attempts, "confirmed_match": confirmed,
        "provisional_candidate_ids": sorted(provisional_ids), "gt_accessed": False}
    registry["v26_provisional_candidates"] = sorted(provisional_ids - ({confirmed["candidate_id"]} if confirmed else set()))
    registry["gt_accessed"] = False
    write(output / "reid_audit.json", audit)
    write(output / "candidate_stream.json", stream)
    write(output / "candidate_grouping_audit.json", grouping)
    write(output / "entity_registry.json", registry)
    write(output / "sam_reinit_log.json", reinit)
    write(output / "identity_timeline.json", output_timeline)
    return audit
