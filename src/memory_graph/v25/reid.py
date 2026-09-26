"""Continuous candidate-to-entity evaluation using unchanged V2.4 gates."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from memory_graph.v22.sam_tracking import box_iou, decode_mask, read_json
from memory_graph.v24.appearance import (AppearanceBank, MobileNetEmbedder, bank_summary,
                                         choose_diverse_views, crop_rgb)
from memory_graph.v24.reid import decide, locked_parameters, registry_update
from .candidates import CandidateHypothesis
from .fusion import ROOT
from .sam_route import SamRouter

OUT = ROOT / "outputs_v25"


def load_candidates(task):
    summaries = read_json(OUT / task / "candidate_grouping_audit.json")["candidates"]
    result = {}
    for summary in summaries:
        candidate = CandidateHypothesis(summary["candidate_id"])
        for obs in summary["observations"]:
            candidate.add(obs)
        candidate.distinct_coexistence_with = set(summary["distinct_coexistence_with"])
        result[candidate.candidate_id] = candidate
    return result


def target_sam_rows(task):
    log = read_json(OUT / task / "sam" / "sam_continuity_log.json")
    result = {}
    for segment in log["segments"]:
        for obs in segment["observations"]:
            result[obs["frame_index"]] = (obs, segment["masks_rle"].get(f"{obs['frame_index']}:{obs['object_id']}"))
    return result


def candidate_sam_rows(task):
    log = read_json(OUT / task / "sam" / "candidate_sam_support.json")
    result = {}
    for entry in log["candidate_support"]:
        frames = {}
        if entry["segment"]:
            segment = entry["segment"]
            for obs in segment["observations"]:
                frames[obs["frame_index"]] = (obs, segment["masks_rle"].get(f"{obs['frame_index']}:{obs['object_id']}"))
        result[entry["candidate_id"]] = frames
    return result


def bank_at_frame(task, frame, query, sam_rows, accepted_frames, embedder):
    rows = []
    for obs in query["observation_history"]:
        f = obs["frame_index"]
        if f > frame or obs["source"] != "yolo_track" or (obs["detector_confidence"] or 0) < .5:
            continue
        if f not in accepted_frames or f not in sam_rows:
            continue
        mask_obs, rle = sam_rows[f]
        if rle is None or mask_obs["diagnostics"]["possible_mask_drift"]:
            continue
        if box_iou(obs["bbox"], mask_obs["bbox"]) < .5:
            continue
        rows.append({"frame_index": f, "timestamp": obs["timestamp"], "bbox": obs["bbox"],
                     "source": obs["source_object_id"], "detector_confidence": obs["detector_confidence"],
                     "mask": rle})
    bank = AppearanceBank("phone_01")
    for row in choose_diverse_views(rows):
        vector, key = embedder.embed_crop(task, row["frame_index"], row["bbox"], row["mask"])
        bank.add({"entity_id": "phone_01", "frame_index": row["frame_index"],
                  "timestamp": row["timestamp"], "source": row["source"],
                  "crop_reference": f"{task}:frame{row['frame_index']}:{row['source']}",
                  "mask_used": True, "embedding_cache_key": key, "embedding": vector.tolist()},
                 trusted=True, reason="V2.3 accepted SAM and confident local YOLO agree")
    return bank


class GenericEmbedder:
    def __init__(self):
        self.model = MobileNetEmbedder()
        self.model.cache_dir = OUT / "cache"
        self.model.cache_dir.mkdir(parents=True, exist_ok=True)
        self.frames = {}

    @property
    def weight_sha256(self):
        return self.model.weight_sha256

    def embed_crop(self, task, frame, bbox, mask_rle=None):
        import cv2
        if (task, frame) not in self.frames:
            cap = cv2.VideoCapture(str(ROOT / f"{task}.mp4"))
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, image = cap.read()
            cap.release()
            if not okay:
                raise OSError(f"Cannot decode {task} frame {frame}")
            self.frames[(task, frame)] = image
        mask = decode_mask(mask_rle) if mask_rle is not None else None
        crop = crop_rgb(self.frames[(task, frame)], bbox, mask)
        return self.model.embed_crop(crop)


def query_snapshot(full_query, frame):
    query = copy.deepcopy(full_query)
    query["observation_history"] = [o for o in query["observation_history"] if o["frame_index"] <= frame]
    trusted = [o for o in query["observation_history"] if o["trusted"]]
    if not trusted:
        return None
    latest = max(trusted, key=lambda o: (o["timestamp"], o["source"] == "yolo_track"))
    query["latest_trusted_observation"] = latest
    query["last_trusted_seen"] = latest["timestamp"]
    return query


def candidate_at_frame(task, candidate, frame, sam_rows, embedder, last_trusted_time):
    past = [o for o in candidate.observations if o["frame_index"] <= frame and o["timestamp"] > last_trusted_time]
    if not past:
        return None
    selected = sorted(past, key=lambda o: (-o["confidence"], o["frame_index"]))[0]
    rows = sam_rows.get(candidate.candidate_id, {})
    mask_entry = rows.get(selected["frame_index"])
    mask = mask_entry[1] if mask_entry and not mask_entry[0]["diagnostics"]["possible_mask_drift"] else None
    vector, key = embedder.embed_crop(task, selected["frame_index"], selected["bbox"], mask)
    supported = any(f <= frame and rle is not None and obs["mask_area"] > 0 and
                    not obs["diagnostics"]["possible_mask_drift"] for f, (obs, rle) in rows.items())
    history = [{"frame_index": o["frame_index"], "bbox": o["bbox"],
                "trusted": o["source_track_id"] is not None, "timestamp": o["timestamp"]}
               for o in past]
    entity = {"entity_id": candidate.candidate_id, "semantic_label": "cell phone",
              "observation_history": history, "association_history": [],
              "yolo_sources": [f"track:{tid}" for tid in sorted(candidate.source_track_ids)],
              "sam_sources": [f"sam_{candidate.candidate_id}"] if supported else [],
              "last_seen": max(o["timestamp"] for o in past), "state": candidate.status}
    return {"entity_id": candidate.candidate_id, "source_id": f"sam_{candidate.candidate_id}",
            "frame_index": selected["frame_index"], "timestamp": selected["timestamp"],
            "bbox": selected["bbox"], "semantic_label": "cell phone", "mask_used": mask is not None,
            "embedding_cache_key": key, "vector": vector,
            "quality": "frozen_yolo_seed_and_nonempty_sam_mask" if supported else "yolo_without_safe_sam_seed",
            "registry_entity": entity, "available_view_frames": sorted({o["frame_index"] for o in past}),
            "sam_support_frames": sorted(rows)}


def run_reid(task):
    params, parameter_hash = locked_parameters()
    embedder = GenericEmbedder()
    if embedder.weight_sha256 != params["checkpoint_sha256"]:
        raise ValueError("Frozen MobileNet checkpoint changed")
    output = OUT / task
    registry = read_json(output / "entity_registry.json")
    full_query = next((e for e in registry["entities"] if e["entity_id"] == "phone_01"), None)
    timeline = read_json(output / "identity_timeline.json")["phone_timeline"]
    candidates = load_candidates(task)
    target_sam = target_sam_rows(task)
    candidate_sam = candidate_sam_rows(task)
    accepted_frames = {a["frame_index"] for a in registry["fusion_audit"]
                       if a["observation_source"] == "sam" and a["entity_id"] == "phone_01"
                       and a["decision"] == "MATCH"}
    attempts, match, latest_bank = [], None, None
    if full_query is not None:
        for row in timeline:
            frame = row["frame_index"]
            if row["state"] != "UNOBSERVED":
                continue
            if not any(c.observations[-1]["frame_index"] >= frame and
                       any(o["frame_index"] == frame for o in c.observations)
                       for c in candidates.values()):
                continue
            query = query_snapshot(full_query, frame)
            if query is None:
                continue
            bank = bank_at_frame(task, frame, query, target_sam, accepted_frames, embedder)
            latest_bank = bank
            if len(bank.prototypes) < params["minimum_evidence_prototypes"]:
                attempts.append({"frame_index": frame, "decision": "NO_SAFE_MATCH",
                                 "reason": "insufficient trusted target appearance prototypes",
                                 "bank_prototype_count": len(bank.prototypes), "candidate_decisions": []})
                continue
            current = []
            for candidate in candidates.values():
                if candidate.status == "MATCHED":
                    continue
                item = candidate_at_frame(task, candidate, frame, candidate_sam, embedder,
                                          query["last_trusted_seen"])
                if item is not None:
                    current.append(item)
            if not current:
                continue
            context = {c["entity_id"]: {"match_sufficient": False, "world_fixed": False}
                       for c in current}
            scored = decide(query, bank, current, params, context)
            record = {"frame_index": frame, "timestamp": row["timestamp"],
                      "query_last_trusted_frame": query["latest_trusted_observation"]["frame_index"],
                      "bank_prototypes": bank_summary(bank), "candidate_decisions": scored,
                      "decision": "MATCH" if any(s["decision"] == "MATCH" for s in scored) else "NO_SAFE_MATCH"}
            attempts.append(record)
            for result in scored:
                candidate = candidates[result["candidate_entity_id"]]
                candidate.status = "MATCHED" if result["decision"] == "MATCH" else "AMBIGUOUS"
                candidate.reid_history.append({"frame_index": frame, "decision": result["decision"],
                                               "similarity": result["appearance"]["max_similarity"],
                                               "reason": result["reason"]})
            winner = next((s for s in scored if s["decision"] == "MATCH"), None)
            if winner:
                matched = next(c for c in current if c["entity_id"] == winner["candidate_entity_id"])
                candidate = candidates[matched["entity_id"]]
                match = {"candidate": candidate, "evidence": winner,
                         "registry_update": registry_update("phone_01", matched, "MATCH", query, bank),
                         "match_frame": frame}
                break
    # Audit/registry writes occur even when no bank or candidate can be scored.
    stream = read_json(output / "candidate_stream.json")
    for event in stream["observations"]:
        cid = event.get("candidate_id")
        if cid and candidates[cid].reid_history:
            applicable = [x for x in candidates[cid].reid_history if x["frame_index"] >= event["frame_index"]]
            if applicable:
                event["reid_evaluated"] = True
                event["reid_decision"] = applicable[0]["decision"]
    (output / "candidate_stream.json").write_text(json.dumps(stream, indent=2), encoding="utf-8")
    grouping = read_json(output / "candidate_grouping_audit.json")
    grouping["candidates"] = [c.summary() for c in candidates.values()]
    (output / "candidate_grouping_audit.json").write_text(json.dumps(grouping, indent=2), encoding="utf-8")
    reinit = {"status": "NONE_AUTHORIZED", "sam_reinitialization_executed": False}
    if match:
        router = SamRouter(task)
        reinit = router.reinitialize_after_match(match["candidate"], match["evidence"]["candidate_frame"])
        reinit["sam_reinitialization_executed"] = reinit["status"] == "EXECUTED"
        registry["entities"] = [match["registry_update"]["updated_entity"] if e["entity_id"] == "phone_01" else e
                                for e in registry["entities"]]
        registry.setdefault("reid_aliases", {})[match["candidate"].candidate_id] = "phone_01"
        for tid in match["candidate"].source_track_ids:
            registry["track_to_entity"][str(tid)] = "phone_01"
        registry["reidentified_at_frame"] = match["match_frame"]
        registry["reidentified_from_candidate"] = match["candidate"].candidate_id
        registry["reid_evidence"] = match["evidence"]
        registry["reid_confidence_state"] = "FROZEN_GATES_MATCH"
        (output / "entity_registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    (output / "sam_reinit_log.json").write_text(json.dumps(reinit, indent=2), encoding="utf-8")
    audit = {"task": task, "parameter_manifest_sha256": parameter_hash,
             "attempts": attempts, "decision": "MATCH" if match else "NO_SAFE_MATCH",
             "match_candidate_id": match["candidate"].candidate_id if match else None,
             "appearance_bank_last_attempt": bank_summary(latest_bank) if latest_bank else None,
             "sam_reinitialization_status": reinit["status"], "gt_accessed": False}
    (output / "reid_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return audit
