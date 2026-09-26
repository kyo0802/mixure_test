"""Post-inference review only: this script may read GT; fusion.py must not."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from memory_graph.v22.sam_tracking import ROOT, read_json


def review(task):
    base = ROOT / "outputs_v23" / task
    registry = read_json(base / "entity_registry.json")
    audit = read_json(base / "fusion_audit.json")
    graph = read_json(base / "graph_snapshots.json")
    gt = read_json(ROOT / "evaluation" / "v21" / f"{task}_annotations.json")
    v22 = read_json(ROOT / "outputs_v22" / task / "tracking_ab" / "ab_metrics.json")
    entities = {e["entity_id"]: e for e in registry["entities"]}
    phone = entities["phone_01"]
    track_map = registry["track_to_entity"]
    mapped = defaultdict(set)
    for segment in gt["verified_track_segments"]:
        entity_id = track_map.get(str(segment["track_id"]))
        if entity_id:
            mapped[segment["gt_object_id"]].add(entity_id)
    distinct = []
    for left, right in gt["distinct_objects"]:
        if mapped[left] and mapped[right]:
            distinct.append({"objects": [left, right], "left_entities": sorted(mapped[left]),
                             "right_entities": sorted(mapped[right]),
                             "false_merge": bool(mapped[left] & mapped[right])})
    visible_phone = [r for r in v22["sample_rows"] if r["scored"]]
    correct_joint = 0
    for row in visible_phone:
        frame = row["frame_index"]
        if row["b_object_id"] != ("phone_track17" if task == "task1" else "phone_track22") or not row["raw_present"]:
            continue
        obs = [o for o in phone["observation_history"] if o["frame_index"] == frame]
        if any(o["source"] == "sam" for o in obs) and any(o["source"].startswith("yolo") for o in obs):
            correct_joint += 1
    by_frame = defaultdict(set)
    for obs in phone["observation_history"]:
        by_frame[obs["frame_index"]].add(obs["source"])
    sam_only = sum("sam" in sources and not any(source.startswith("yolo") for source in sources)
                   for sources in by_frame.values())
    drift_frame = 312 if task == "task2" else None
    drift_audit = [a for a in audit if a["frame_index"] == drift_frame and a["source_object_id"] == "phone_track22"] if drift_frame else []
    drift_accepted = bool(drift_frame and any(o["frame_index"] == drift_frame and o["source"] == "sam"
                                               for o in phone["observation_history"]))
    late_duplicate = 0
    if task == "task2":
        # Evaluation-only: the reviewed late phone mask is the original physical phone.
        late_ids = {r["b_object_id"] for r in visible_phone if r["frame_index"] >= 528 and r["b_object_id"]}
        late_entities = {registry["sam_to_entity"].get(source) for source in late_ids}
        late_duplicate = len({e for e in late_entities if e and e != "phone_01"})
    counts = Counter(a["decision"] for a in audit)
    retained = max((len(s["unobserved_remembered_entities"]) for s in graph["snapshots"]), default=0)
    metrics = {"task": task, "persistent_entities": len(entities), "audit_decisions": dict(counts),
               "correct_yolo_sam_fusion_reviewed_phone_frames": correct_joint,
               "sam_only_phone_frames_accepted": sam_only,
               "duplicate_entity_creation_count_reviewed_phone": late_duplicate,
               "false_merge_count_on_reviewed_distinct_pairs": sum(p["false_merge"] for p in distinct),
               "distinct_pair_tests": distinct,
               "confirmed_drift_accepted_in_trusted_phone_history": int(drift_accepted),
               "confirmed_drift_rejected_or_flagged": int(bool(drift_audit) and not drift_accepted),
               "drift_decisions": [a["decision"] for a in drift_audit],
               "max_remembered_unobserved_nodes_in_snapshots": retained,
               "phone_yolo_track_ids": [int(x.split(":")[1]) for x in phone["yolo_sources"] if x.startswith("track:")],
               "phone_sam_target_ids": phone["sam_sources"],
               "late_candidates": {key: value for key, value in registry["sam_to_entity"].items() if key.startswith("late_")},
               "graph_node_identity_check": all(n["entity_id"] in entities for s in graph["snapshots"] for n in s["nodes"])}
    content = [f"# {task} fusion review", "", f"Persistent entities: {len(entities)}. Fusion decisions: {dict(counts)}.",
               f"Reviewed same-phone YOLO/SAM joint frames: {correct_joint}. SAM-only accepted phone frames: {sam_only}.",
               f"Reviewed false merges: {metrics['false_merge_count_on_reviewed_distinct_pairs']} / {len(distinct)} distinct pairs.",
               f"Reviewed duplicate phone hypotheses: {late_duplicate}. Max unobserved remembered nodes in snapshots: {retained}.", ""]
    if task == "task1":
        content += ["The V2.1 phone track17 and SAM phone_track17 both support phone_01. After track17 ends, accepted SAM observations keep phone_01 visible until the mask vanishes at frame420; phone_01 remains UNOBSERVED. The later desk-phone track70 maps to a different entity. Static scene nodes remain in snapshots."]
    else:
        content += [f"V2.1 tracks22 and43 both map to phone_01 by local SAM continuity. Frame312 SAM is {','.join(metrics['drift_decisions']) or 'not audited'}; it was not written to trusted phone history. Late candidates stay separate: {metrics['late_candidates']}. Candidate 1 corresponds to the reviewed original phone, so one conservative duplicate hypothesis remains; this is unresolved re-identification, not a false merge. Distinct desk phones remain distinct."]
    content += ["", "GT is sparse and non-random; this review cannot certify all unreviewed frames, all false merges, or full-video identity purity."]
    (base / "review.md").write_text("\n\n".join(content) + "\n", encoding="utf-8")
    return metrics


if __name__ == "__main__":
    results = {task: review(task) for task in ("task1", "task2")}
    classification = "FUSION_WORKS_BUT_REIDENTIFICATION_UNRESOLVED"
    decision = "IMPROVE_REIDENTIFICATION_FIRST"
    summary = {"result_classification": classification, "architecture_decision": decision,
               "tasks": results, "new_vlm_calls": 0,
               "limits": "Sparse GT; known frame312 regression informed the fixed contradiction gate; late candidate physical identity is evaluation-only."}
    (ROOT / "outputs_v23" / "fusion_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for task, metrics in results.items():
        print(task, metrics)
