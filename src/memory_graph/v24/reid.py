"""GT-free long-gap appearance matcher; parameters must be locked before challenge."""
from __future__ import annotations

from collections import Counter
import copy
import json
from pathlib import Path

import cv2
import numpy as np

from memory_graph.v22.sam_tracking import ROOT, decode_mask, read_json, sha256
from .appearance import (AppearanceBank, MobileNetEmbedder, bank_summary, compatible_semantics,
                         crop_rgb, eligible_trusted_views, frame_image, make_bank,
                         choose_diverse_views, sam_obs_by_frame, similarity_details)


MANIFEST = ROOT / "outputs_v24" / "reid_parameter_manifest.json"
LOCK = ROOT / "outputs_v24" / "cache" / "reid_parameter_manifest.sha256"


def locked_parameters():
    expected = LOCK.read_text(encoding="utf-8").strip().lower()
    actual = sha256(MANIFEST)
    if actual != expected:
        raise ValueError("Re-ID parameter manifest changed after freeze")
    params = read_json(MANIFEST)
    if not params["frozen_before_task2_late_candidate_inference"]:
        raise ValueError("Manifest is not frozen")
    return params, actual


def query_bank(task, embedder, registry):
    bank = make_bank(task, embedder, registry)
    if task == "task2" and any(p["frame_index"] >= 312 for p in bank.prototypes):
        raise ValueError("Conflict/late frame entered trusted appearance bank")
    return bank


def candidate_from_sam(task, source, entity_id, registry, embedder):
    source_rows = sam_obs_by_frame(task, source)
    if not source_rows:
        raise ValueError(f"Candidate crop unavailable: {source}")
    frame = min(source_rows)
    obs, rle = source_rows[frame]
    if rle is None or obs["mask_area"] <= 0:
        raise ValueError(f"Candidate mask unavailable: {source}")
    vector, key = embedder.embed(task, frame, obs["bbox"], decode_mask(rle))
    entity = next(e for e in registry["entities"] if e["entity_id"] == entity_id)
    return {"entity_id": entity_id, "source_id": source, "frame_index": frame,
            "timestamp": obs["timestamp"], "bbox": obs["bbox"], "semantic_label": entity["semantic_label"],
            "mask_used": True, "embedding_cache_key": key, "vector": vector,
            "quality": "frozen_yolo_seed_and_nonempty_sam_mask", "sam_obs": obs}


def candidate_from_yolo_track(task, track_id, entity_id, embedder):
    from memory_graph.v22.sam_tracking import frozen_inputs
    inputs, _ = frozen_inputs(task)
    track = next(t for t in inputs["track_timelines.json"] if t["track_id"] == track_id)
    obs = max(track["observations"], key=lambda o: o["confidence"])
    vector, key = embedder.embed(task, obs["frame_index"], obs["bbox"])
    return {"entity_id": entity_id, "source_id": f"track:{track_id}", "frame_index": obs["frame_index"],
            "timestamp": obs["timestamp"], "bbox": obs["bbox"], "semantic_label": obs["class_name"],
            "mask_used": False, "embedding_cache_key": key, "vector": vector,
            "quality": "trusted_yolo_crop_without_mask"}


def current_coexistence(query_entity, candidate_entity):
    """Only simultaneous trusted, spatially separate observations are a veto."""
    q = {o["frame_index"]: o for o in query_entity["observation_history"] if o["trusted"]}
    c = {o["frame_index"]: o for o in candidate_entity["observation_history"] if o["trusted"]}
    from memory_graph.v22.sam_tracking import box_iou
    return [frame for frame in sorted(q.keys() & c.keys()) if box_iou(q[frame]["bbox"], c[frame]["bbox"]) < .1]


def graph_context_evidence(task, query_id, candidate_id):
    graph = read_json(ROOT / "outputs_v23" / task / "graph_snapshots.json")
    by_entity = {}
    for snapshot in graph["snapshots"]:
        for entity_id in (query_id, candidate_id):
            neighbors = set()
            for edge in snapshot["edges"]:
                if edge["subject_entity_id"] == entity_id:
                    neighbors.add(edge["object_entity_id"])
                if edge["object_entity_id"] == entity_id:
                    neighbors.add(edge["subject_entity_id"])
            if entity_id in snapshot["active_visible_entities"]:
                by_entity[entity_id] = {"frame_index": snapshot["frame_index"], "neighbor_entity_ids": sorted(neighbors)}
    q, c = by_entity.get(query_id), by_entity.get(candidate_id)
    shared = sorted(set(q["neighbor_entity_ids"]) & set(c["neighbor_entity_ids"])) if q and c else []
    return {"query_last_visible_context": q, "candidate_context": c, "shared_image_plane_neighbor_ids": shared,
            "match_sufficient": False, "world_fixed": False}


def decide(query_entity, bank, candidates, params, contexts=None):
    """Gate contradictions, then appearance, then uniqueness. No argmax-only matching."""
    threshold = params["minimum_match_similarity"]
    margin = params["minimum_uniqueness_margin"]
    scored = []
    for candidate in candidates:
        entity = candidate["registry_entity"]
        semantic_ok = compatible_semantics(query_entity["semantic_label"], candidate["semantic_label"])
        coexist = current_coexistence(query_entity, entity)
        gap = candidate["timestamp"] - query_entity["last_trusted_seen"]
        appearance = similarity_details(bank, [candidate["vector"]])
        contradictions = []
        if not semantic_ok:
            contradictions.append("SEMANTIC_CONTRADICTION")
        if coexist:
            contradictions.append("COEXISTENCE_CONTRADICTION")
        if gap <= 0:
            contradictions.append("NON_FORWARD_TEMPORAL_ORDER")
        scored.append({"candidate_entity_id": candidate["entity_id"], "source_id": candidate["source_id"],
                       "candidate_frame": candidate["frame_index"], "candidate_time": candidate["timestamp"],
                       "query_entity_id": query_entity["entity_id"],
                       "query_last_trusted_frame": query_entity["latest_trusted_observation"]["frame_index"],
                       "query_last_trusted_time": query_entity["last_trusted_seen"], "gap_seconds": gap,
                       "semantic_compatible": semantic_ok, "appearance": appearance,
                       "temporal_evidence": {"forward_after_unobserved": gap > 0,
                                             "pixel_motion_extrapolation_used": False},
                       "coexistence_frames": coexist,
                       "graph_context": (contexts or {}).get(candidate["entity_id"]),
                       "hard_contradictions": contradictions,
                       "candidate_quality": candidate["quality"],
                       "embedding_cache_key": candidate["embedding_cache_key"]})
    eligible = sorted((s for s in scored if not s["hard_contradictions"]),
                      key=lambda s: s["appearance"]["max_similarity"], reverse=True)
    best = eligible[0] if eligible else None
    second_score = eligible[1]["appearance"]["max_similarity"] if len(eligible) > 1 else None
    best_margin = best["appearance"]["max_similarity"] - second_score if best and second_score is not None else None
    match_id = None
    if (best and best["appearance"]["max_similarity"] >= threshold
            and (best_margin is None or best_margin >= margin)
            and len(bank.prototypes) >= params["minimum_evidence_prototypes"]
            and best["candidate_quality"] == "frozen_yolo_seed_and_nonempty_sam_mask"):
        match_id = best["candidate_entity_id"]
    for s in scored:
        score = s["appearance"]["max_similarity"]
        s["match_threshold"] = threshold
        s["uniqueness_margin_required"] = margin
        s["best_vs_second_margin"] = best_margin
        s["best_candidate_similarity"] = best["appearance"]["max_similarity"] if best else None
        s["second_candidate_similarity"] = second_score
        if s["hard_contradictions"]:
            s["decision"], s["reason"] = "REJECT", ", ".join(s["hard_contradictions"])
        elif s["candidate_entity_id"] == match_id:
            s["decision"], s["reason"] = "MATCH", "semantic/temporal gates pass; appearance clears threshold and competitor margin"
        else:
            s["decision"], s["reason"] = "AMBIGUOUS", "appearance or candidate uniqueness insufficient; keep provisional hypothesis"
        s["sam_reinitialization_authorized"] = s["decision"] == "MATCH"
    return scored


def registry_update(query_id, candidate, decision, query_entity=None, bank=None):
    if decision != "MATCH":
        return {"merge_executed": False, "query_entity_id": query_id,
                "candidate_entity_id": candidate["entity_id"], "sam_reinitialization_authorized": False,
                "sam_reinitialization_executed": False}
    if query_entity is None:
        raise ValueError("MATCH requires the existing registry entity")
    merged = copy.deepcopy(query_entity)
    source = candidate["registry_entity"]
    merged["observation_history"].extend(copy.deepcopy(source["observation_history"]))
    merged["association_history"].extend(copy.deepcopy(source["association_history"]))
    merged["yolo_sources"] = sorted(set(merged["yolo_sources"] + source["yolo_sources"]))
    merged["sam_sources"] = sorted(set(merged["sam_sources"] + source["sam_sources"]))
    merged["last_seen"] = max(merged["last_seen"], source["last_seen"])
    merged["state"] = source["state"]
    if bank is not None:
        merged["appearance_memory"] = bank_summary(bank)["prototypes"] + [
            {"entity_id": query_id, "frame_index": candidate["frame_index"],
             "timestamp": candidate["timestamp"], "source": candidate["source_id"],
             "crop_reference": f"frame{candidate['frame_index']}:{candidate['source_id']}",
             "mask_used": candidate["mask_used"], "embedding_cache_key": candidate["embedding_cache_key"],
             "trust_reason": "safe Re-ID MATCH after parameter-locked gates"}]
    return {"merge_executed": True, "query_entity_id": query_id,
            "candidate_entity_id": candidate["entity_id"], "reidentified_at_frame": candidate["frame_index"],
            "reidentified_from_candidate": candidate["entity_id"],
            "sam_reinitialization_authorized": True, "sam_reinitialization_executed": False,
            "candidate_removed_from_active_registry": True,
            "updated_entity": merged,
            "inference_registry_action": "candidate observations appended to existing query entity; source ID remains provenance"}


def render_contact_sheet(task, bank, candidates, output):
    tiles = []
    for p in bank.prototypes:
        frame = p["frame_index"]
        source = p["source"]
        rows = eligible_trusted_views(task, "phone_track17" if task == "task1" else "phone_track22",
                                      read_json(ROOT / "outputs_v23" / task / "entity_registry.json"))
        row = next(r for r in rows if r["frame_index"] == frame and r["source"] == source)
        crop = crop_rgb(frame_image(task, frame), row["bbox"], decode_mask(row["mask"]))
        tiles.append((f"phone_01 {source} f{frame}", crop))
    for c in candidates:
        frame = c["frame_index"]
        if c["source_id"].startswith("late_"):
            _, rle = sam_obs_by_frame(task, c["source_id"])[frame]
            mask = decode_mask(rle)
        else:
            mask = None
        crop = crop_rgb(frame_image(task, frame), c["bbox"], mask)
        tiles.append((f"{c['entity_id']} {c['source_id']} f{frame}", crop))
    columns, tile_w, tile_h = 4, 240, 260
    canvas = np.full((((len(tiles) + columns - 1) // columns) * tile_h, columns * tile_w, 3), 240, dtype=np.uint8)
    for i, (label, crop) in enumerate(tiles):
        image = cv2.resize(crop, (220, 220))
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        y, x = (i // columns) * tile_h, (i % columns) * tile_w
        canvas[y + 30:y + 250, x + 10:x + 230] = image
        cv2.putText(canvas, label[:33], (x + 5, y + 20), cv2.FONT_HERSHEY_SIMPLEX, .38, (0, 0, 0), 1)
    cv2.imwrite(str(output), canvas, [cv2.IMWRITE_JPEG_QUALITY, 90])


def run(task):
    params, manifest_hash = locked_parameters()
    registry = read_json(ROOT / "outputs_v23" / task / "entity_registry.json")
    query = next(e for e in registry["entities"] if e["entity_id"] == "phone_01")
    if query["state"] != "UNOBSERVED":
        raise ValueError("Long-gap query is not unobserved")
    embedder = MobileNetEmbedder()
    if embedder.weight_sha256 != params["checkpoint_sha256"]:
        raise ValueError("Appearance checkpoint differs from frozen manifest")
    bank = query_bank(task, embedder, registry)
    output = ROOT / "outputs_v24" / task
    output.mkdir(parents=True, exist_ok=True)
    (output / "appearance_bank.json").write_text(json.dumps(bank_summary(bank), indent=2), encoding="utf-8")
    if task == "task2":
        source_ids = ["late_candidate_1", "late_candidate_2", "late_candidate_3"]
        candidates = [candidate_from_sam(task, source, registry["sam_to_entity"][source], registry, embedder)
                      for source in source_ids]
    else:
        candidates = [candidate_from_yolo_track(task, 70, registry["track_to_entity"]["70"], embedder)]
    entity_lookup = {e["entity_id"]: e for e in registry["entities"]}
    for c in candidates:
        c["registry_entity"] = entity_lookup[c["entity_id"]]
    contexts = {c["entity_id"]: graph_context_evidence(task, "phone_01", c["entity_id"]) for c in candidates}
    scored = decide(query, bank, candidates, params, contexts)
    matches = [s for s in scored if s["decision"] == "MATCH"]
    if matches:
        winner = next(c for c in candidates if c["entity_id"] == matches[0]["candidate_entity_id"])
        update = registry_update("phone_01", winner, "MATCH", query, bank)
    else:
        update = {"merge_executed": False, "query_entity_id": "phone_01",
                  "sam_reinitialization_authorized": False, "sam_reinitialization_executed": False}
    post_registry = None
    if update["merge_executed"]:
        post_registry = copy.deepcopy(registry)
        post_registry["entities"] = [update["updated_entity"] if e["entity_id"] == "phone_01" else e
                                     for e in post_registry["entities"] if e["entity_id"] != update["candidate_entity_id"]]
        post_registry["sam_to_entity"][winner["source_id"]] = "phone_01"
        post_registry["track_to_entity"] = {track: ("phone_01" if eid == update["candidate_entity_id"] else eid)
                                           for track, eid in post_registry["track_to_entity"].items()}
    audit = {"task": task, "parameter_manifest_sha256": manifest_hash,
             "upstream_v23_registry_sha256": sha256(ROOT / "outputs_v23" / task / "entity_registry.json"),
             "query_entity_id": "phone_01", "attempts": scored, "registry_update": update,
             "post_reid_registry": post_registry,
             "gt_accessed": False}
    (output / "reid_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    similarity = {"task": task, "query_prototype_frames": [p["frame_index"] for p in bank.prototypes],
                  "candidate_matrix": {s["candidate_entity_id"]: s["appearance"] for s in scored},
                  "threshold": params["minimum_match_similarity"], "required_margin": params["minimum_uniqueness_margin"],
                  "best_vs_second_margin": scored[0]["best_vs_second_margin"] if scored else None}
    (output / "appearance_similarity.json").write_text(json.dumps(similarity, indent=2), encoding="utf-8")
    render_contact_sheet(task, bank, candidates, output / "reid_contact_sheet.jpg")
    return audit
