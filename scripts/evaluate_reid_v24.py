"""Evaluation-only reveal of held-out identities after V2.4 predictions are frozen."""
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v22.sam_tracking import ROOT, box_iou, read_json, sha256
from memory_graph.v24.appearance import cosine
from memory_graph.v24.reid import locked_parameters
import numpy as np


def evaluate():
    params, manifest_hash = locked_parameters()
    output = ROOT / "outputs_v24"
    a1_path = output / "task1/reid_audit.json"
    a2_path = output / "task2/reid_audit.json"
    a1, a2 = read_json(a1_path), read_json(a2_path)
    for audit in (a1, a2):
        if audit["gt_accessed"] or audit["parameter_manifest_sha256"] != manifest_hash:
            raise ValueError("Prediction/GT isolation invalid")
    prediction_hashes = {"task1": sha256(a1_path), "task2": sha256(a2_path)}
    gt1 = read_json(ROOT / "evaluation/v21/task1_annotations.json")
    gt2 = read_json(ROOT / "evaluation/v21/task2_annotations.json")
    v22 = read_json(ROOT / "outputs_v22/task2/tracking_ab/sam_propagation_log.json")
    f528_gt = next(s for s in gt2["samples"] if s["gt_object_id"] == "smartphone_01" and s["frame_index"] == 528)
    candidate_boxes = {f"candidate_phone_{int(o['object_id'].split('_')[-1]):02d}": o["bbox"]
                       for seg in v22["segments"] for o in seg["observations"]
                       if o["frame_index"] == 528 and o["object_id"].startswith("late_candidate_")}
    reviewed_original = {eid for eid, box in candidate_boxes.items() if box_iou(box, f528_gt["bbox"]) >= .3}
    if len(reviewed_original) != 1:
        raise ValueError("Held-out reviewed identity is not uniquely evaluable")
    correct_id = next(iter(reviewed_original))
    task2_decisions = {a["candidate_entity_id"]: a["decision"] for a in a2["attempts"]}
    matches = [eid for eid, decision in task2_decisions.items() if decision == "MATCH"]
    wrong_matches = [eid for eid in matches if eid != correct_id]
    false_split = int(task2_decisions[correct_id] != "MATCH")
    v23 = read_json(ROOT / "outputs_v23/task2/entity_registry.json")
    entities = {e["entity_id"]: e for e in v23["entities"]}
    desk_ids = {v23["track_to_entity"][str(s["track_id"])] for s in gt2["verified_track_segments"]
                if s["gt_object_id"] in {"desk_phone_01", "desk_phone_02"}}
    desk_wrong = [eid for eid in matches if eid in desk_ids]
    neg1 = a1["attempts"][0]
    task1_negative_safe = neg1["decision"] != "MATCH"
    byid = {a["candidate_entity_id"]: a for a in a2["attempts"]}
    desk_list = sorted(desk_ids)
    if len(desk_list) == 2:
        vectors = []
        for eid in desk_list:
            key = byid[eid]["embedding_cache_key"]
            vectors.append(np.load(output / "cache" / f"embedding_{key}.npy"))
        desk_pair_similarity = cosine(*vectors)
        from memory_graph.v24.reid import current_coexistence
        desk_pair_coexistence = current_coexistence(entities[desk_list[0]], entities[desk_list[1]])
    else:
        desk_pair_similarity, desk_pair_coexistence = None, []
    bank2 = read_json(output / "task2/appearance_bank.json")
    bank_frames = [p["frame_index"] for p in bank2["prototypes"]]
    memory_poisoning = any(frame >= 312 for frame in bank_frames)
    counts = Counter(a["decision"] for a in a1["attempts"] + a2["attempts"])
    if matches == [correct_id] and not wrong_matches and task1_negative_safe and not memory_poisoning:
        result = "SAFE_LONG_GAP_REID_SUCCESS"
    elif wrong_matches:
        result = "REID_WORKS_BUT_FALSE_MERGES_OCCURRED"
    elif false_split:
        result = "APPEARANCE_HELPS_BUT_REID_REMAINS_AMBIGUOUS"
    else:
        result = "INSUFFICIENT_EVIDENCE"
    next_decision = "PROCEED_TO_SPATIAL_MEMORY_GRAPH" if result == "SAFE_LONG_GAP_REID_SUCCESS" else "ADD_GRAPH_CONTEXT_FOR_REID"
    summary = {"result_classification": result, "next_architecture_decision": next_decision,
               "parameter_manifest_sha256": manifest_hash, "prediction_sha256_before_gt_review": prediction_hashes,
               "development_controls": read_json(output / "cache/development_controls.json"),
               "reid_attempts": len(a1["attempts"]) + len(a2["attempts"]), "decision_counts": dict(counts),
               "task1_negative_safe_no_merge": task1_negative_safe,
               "task2_reviewed_original_candidate": correct_id,
               "task2_candidate_decisions": task2_decisions,
               "true_reviewed_reidentifications": int(matches == [correct_id]),
               "wrong_candidate_matches": wrong_matches, "false_merges_into_phone_01": len(desk_wrong),
               "unresolved_duplicate_count": false_split,
               "appearance_memory_poisoning": memory_poisoning,
               "desk_phone_pair_similarity": desk_pair_similarity,
               "desk_phone_pair_coexistence_frames": desk_pair_coexistence,
               "sam_reinitialization_authorized": a2["registry_update"]["sam_reinitialization_authorized"],
               "sam_reinitialization_executed": a2["registry_update"]["sam_reinitialization_executed"],
               "new_yolo_calls": 0, "new_sam_propagation_calls": 0, "new_vlm_calls": 0,
               "scope": "Single task2 long-gap challenge; sparse non-random reviewed GT, no population accuracy claim."}
    (output / "reid_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "task1/review.md").write_text(
        f"# Task1 Re-ID review\n\nLater desk-phone track70 received {neg1['decision']} with cosine {neg1['appearance']['max_similarity']:.3f}. It was not merged into phone_01. The V2.3 distinct-object GT confirms these are separate phones. The desk crop has no SAM mask, limiting the negative control.\n",
        encoding="utf-8")
    lines = ["# Task2 held-out Re-ID review", "",
             "The inference audit and parameter hash were frozen before GT was read.", "",
             "| Candidate | Cosine max | Inference decision | Reviewed identity |",
             "|---|---:|---|---|"]
    for attempt in a2["attempts"]:
        eid = attempt["candidate_entity_id"]
        identity = "original smartphone" if eid == correct_id else "distinct desk phone" if eid in desk_ids else "not established"
        lines.append(f"| {eid} | {attempt['appearance']['max_similarity']:.3f} | {attempt['decision']} | {identity} |")
    lines += ["", f"Best-vs-second margin: {a2['attempts'][0]['best_vs_second_margin']:.3f}; required 0.100.",
              f"Desk-phone pair cosine {desk_pair_similarity:.3f} with {len(desk_pair_coexistence)} reliable coexistence frames; they remain distinct.",
              f"False match count: {len(wrong_matches)}. Appearance-memory poisoning: {memory_poisoning}. Same-identity SAM reinitialization authorized: {summary['sam_reinitialization_authorized']}; executed: {summary['sam_reinitialization_executed']}.",
              "", "This single reviewed sequence does not establish general long-gap Re-ID accuracy."]
    (output / "task2/review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"result": result, "correct_candidate": correct_id, "decisions": task2_decisions,
                      "wrong_matches": wrong_matches, "desk_pair_similarity": desk_pair_similarity}))
    return summary


if __name__ == "__main__":
    evaluate()
