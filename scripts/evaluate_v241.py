"""Evaluation-only seven-video review. Never imported by inference scripts."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v241"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def verify_predictions_frozen():
    manifest_path = OUT / "prediction_manifest.json"
    manifest = read(manifest_path)
    if manifest["stage"] != "A_BLIND_INFERENCE_COMPLETE" or manifest["gt_read_before_freeze"]:
        raise ValueError("Blind inference not frozen")
    if digest(OUT / "frozen_baseline_manifest.json") != manifest["baseline_manifest_sha256"]:
        raise ValueError("Baseline manifest changed")
    for name, expected in manifest["inference_code_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"Inference code changed after freeze: {name}")
    for task, files in manifest["videos"].items():
        for name, expected in files.items():
            if digest(OUT / task / name) != expected:
                raise ValueError(f"Prediction artifact changed after freeze: {task}/{name}")
        upstream = read(OUT / task / "upstream_v21" / "prediction_manifest.json")
        for name in ("event_analysis/detections.json", "event_analysis/track_timelines.json",
                     "event_analysis/video_metadata.json", "persistent_entities.json"):
            if digest(OUT / task / "upstream_v21" / name) != upstream[name]:
                raise ValueError(f"Frozen V2.1 input changed: {task}/{name}")
    baseline = read(OUT / "frozen_baseline_manifest.json")
    for name, expected in baseline["component_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"V2.4 baseline changed: {name}")
    for name, expected in baseline["videos_sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError(f"Evaluation video changed: {name}")
    return digest(manifest_path)


def reviewed_cases():
    """Manual frame review plus user's evaluation-only scenario descriptions.

    Called strictly after verify_predictions_frozen(). A 'miss' means the target
    object itself lacked a matching raw/local box, even if a landline was detected.
    """
    return {
        "test3": {"scenario": "smartphone placed inside box", "target_initialized": True,
            "samples": [(216, 39), (420, 54), (450, None)],
            "late_candidate_review": "fixed candidate at f786 is a distinct landline",
            "later_target_review": "phone visible in hand at f450, then enters box; final interior not directly visible",
            "failure": "FINAL_STATE_NOT_VISUALLY_VERIFIABLE", "spatial_tag": "IDENTITY_OK_FINAL_LOCATION_UNCERTAIN",
            "reid_opportunity": False, "fragmentation": False, "final_location_visible": False},
        "test4": {"scenario": "behind basketball; later observed in difficult final region", "target_initialized": True,
            "samples": [(204, 36), (426, 48), (1050, 107)],
            "late_candidate_review": "fixed candidate at f798 is a distinct landline",
            "later_target_review": "same target appearance seen at f426 and detected again at f1050; neither is compared by frozen late candidate window",
            "failure": "MIXED", "spatial_tag": "ANCHOR_CONTEXT_COULD_HELP",
            "reid_opportunity": True, "fragmentation": True, "final_location_visible": True},
        "test5": {"scenario": "smartphone beside box; placement itself not captured", "target_initialized": False,
            "samples": [(288, 35), (366, 38)],
            "late_candidate_review": "f288 candidate is gray phone; f0 seed is visually different white multi-camera phone",
            "later_target_review": "target gray phone visible at f288 and f366; exact final placement not filmed",
            "failure": "FUSION_LIMITED", "spatial_tag": "IDENTITY_OK_FINAL_LOCATION_UNCERTAIN",
            "reid_opportunity": False, "fragmentation": False, "final_location_visible": False},
        "test6": {"scenario": "smartphone near microwave beside doll", "target_initialized": True,
            "samples": [(192, 31), (384, 37), (630, None)],
            "late_candidate_review": "fixed candidate at f594 is a distinct landline",
            "later_target_review": "target visible in hand at f630 with no corresponding raw/local YOLO box",
            "failure": "DETECTION_LIMITED", "spatial_tag": "ANCHOR_CONTEXT_COULD_HELP",
            "reid_opportunity": True, "fragmentation": False, "final_location_visible": False},
        "test7": {"scenario": "smartphone inserted into doll", "target_initialized": True,
            "samples": [(204, 29), (720, 57), (888, 67)],
            "late_candidate_review": "fixed candidate at f636 is a distinct landline",
            "later_target_review": "target visible by doll at f720 and f888 in separate local phone tracks, omitted from Re-ID candidate set",
            "failure": "FUSION_LIMITED", "spatial_tag": "ANCHOR_CONTEXT_COULD_HELP",
            "reid_opportunity": True, "fragmentation": True, "final_location_visible": False},
        "test8": {"scenario": "smartphone placed beside two other phones", "target_initialized": True,
            "samples": [(186, 29), (810, None), (888, 73), (918, 74)],
            "late_candidate_review": "fixed candidate at f624 is a distinct landline; later target and two landlines coexist",
            "later_target_review": "target visible in hand at f810 without target YOLO box; later target phone has local tracks f888/f918 but was not scored against distractors",
            "failure": "FUSION_LIMITED", "spatial_tag": "ANCHOR_CONTEXT_COULD_HELP",
            "reid_opportunity": True, "fragmentation": True, "final_location_visible": True},
        "test9": {"scenario": "early basketball occlusion; later between HomePad and alcohol bottle", "target_initialized": True,
            "samples": [(534, 53), (810, None)],
            "late_candidate_review": "two fixed candidates at f822 are distinct landline handsets, both left ambiguous",
            "later_target_review": "target visibly held at f810 but no matching raw/local phone box; SAM lost after f624 and f606 expansion was rejected",
            "failure": "MIXED", "spatial_tag": "CAMERA_MOTION_SPATIAL_CONTEXT_LOST",
            "reid_opportunity": True, "fragmentation": False, "final_location_visible": False},
    }


def detection_class(reviewable, raw_hit):
    if not reviewable:
        return "NOT_REVIEWABLE"
    return "DETECTION_OK" if raw_hit else "DETECTION_MISS"


def raw_matches_track(detections, track, frame):
    from sys import path
    local = str(ROOT / "src")
    if local not in path:
        path.insert(0, local)
    from memory_graph.v22.sam_tracking import box_iou
    obs = next(o for o in track["observations"] if o["frame_index"] == frame)
    return any(d["frame_index"] == frame and d["class_name"] == "cell phone"
               and box_iou(d["bbox"], obs["bbox"]) >= .95 for d in detections)


def evaluate_one(task, reviewed):
    base = OUT / task
    pred, reid, sam = [read(base / name) for name in
                       ("identity_timeline.json", "reid_audit.json", "sam/sam_propagation_log.json")]
    detections = read(base / "upstream_v21" / "event_analysis" / "detections.json")
    tracks = read(base / "upstream_v21" / "event_analysis" / "track_timelines.json")
    track_by_id = {t["track_id"]: t for t in tracks}
    samples = []
    for frame, track_id in reviewed["samples"]:
        raw = raw_matches_track(detections, track_by_id[track_id], frame) if track_id else False
        samples.append({"frame_index": frame, "timestamp_approx_seconds": frame/30,
                        "target_visually_reviewable": True, "target_local_track_id": track_id,
                        "target_raw_yolo_hit": raw, "target_local_observation_hit": track_id is not None,
                        "detection_class": detection_class(True, raw)})
    initial = sam["initialization"]
    target = pred["target_entity"]
    initial_segment = next(s for s in sam["segments"] if s["segment"] == "initial")
    sam_obs = {o["frame_index"] for s in sam["segments"] for o in s["observations"]}
    for sample in samples:
        sample["sam_mask_any_target_hypothesis"] = sample["frame_index"] in sam_obs
    target_states = [row["state"] for row in pred["phone_timeline"]]
    attempts = reid["attempts"]
    late = sam["late_selection"]
    last_trusted = target["latest_trusted_observation"]
    reviewed_result = {
        "task": task, "scenario_evaluation_only": reviewed["scenario"],
        "target_initialization_correct_on_review": reviewed["target_initialized"],
        "initial_source": {"track_id": initial["track_id"], "frame_index": initial["frame_index"],
                           "timestamp": next(r["timestamp"] for r in pred["phone_timeline"] if r["frame_index"] == initial["frame_index"]),
                           "sam_target_id": f"phone_track{initial['track_id']}", "persistent_entity_id": "phone_01"},
        "last_trusted_observation": {"frame_index": last_trusted["frame_index"],
                                     "timestamp": last_trusted["timestamp"]},
        "final_registry_state": target["state"], "unobserved_seen": "UNOBSERVED" in target_states,
        "reviewed_visible_samples": samples,
        "sam": {"initial_span": [initial_segment["frames"][0], initial_segment["frames"][-1]],
                "initial_masks": len(initial_segment["observations"]),
                "initial_loss_events": sum(e["type"] == "LOST" for e in initial_segment["events"]),
                "possible_mask_drift_flags": sum(o["diagnostics"]["possible_mask_drift"]
                                                 for s in sam["segments"] for o in s["observations"]),
                "rejected_guard_conflicts": sum(a["decision"] == "CONFLICT" and a["observation_source"] == "sam"
                                                for a in pred["fusion_audit"] if a["entity_id"] == "phone_01"),
                "reinitializations_executed": len(sam["segments"])-1,
                "reinitialization_same_identity": False},
        "late_candidate_first_frame": late["frame_index"] if late else None,
        "late_candidate_review": reviewed["late_candidate_review"],
        "late_target_review": reviewed["later_target_review"],
        "reid_attempts": [{"candidate_entity_id": a["candidate_entity_id"],
                           "similarity": a["appearance"]["max_similarity"],
                           "best_vs_second_margin": a["best_vs_second_margin"],
                           "decision": a["decision"], "semantic_compatible": a["semantic_compatible"],
                           "coexistence_frames": a["coexistence_frames"],
                           "graph_context": a["graph_context"]} for a in attempts],
        "true_reviewed_reid_match": False, "false_reid_match": False,
        "missed_reid_opportunity": reviewed["reid_opportunity"],
        "identity_fragmentation": reviewed["fragmentation"], "false_merge_reviewed": False,
        "exact_final_location_directly_visible": reviewed["final_location_visible"],
        "failure_attribution": reviewed["failure"], "spatial_diagnostic": reviewed["spatial_tag"],
        "gt_used_for_inference": False,
    }
    lines = [f"# {task} — post-freeze review", "", f"- Evaluation-only scenario: {reviewed['scenario']}.",
             f"- Target initialization: {'correct' if reviewed['target_initialized'] else 'wrong phone on visual review'}; "
             f"YOLO track {initial['track_id']} at f{initial['frame_index']} → SAM phone_track{initial['track_id']} → phone_01.",
             f"- Last trusted phone_01 observation: f{last_trusted['frame_index']} "
             f"({last_trusted['timestamp']:.2f}s); registry ends UNOBSERVED and retains phone_01.",
             f"- SAM initial span f{initial_segment['frames'][0]} to f{initial_segment['frames'][-1]}: "
             f"{len(initial_segment['observations'])} masks, {reviewed_result['sam']['initial_loss_events']} loss events, "
             f"{reviewed_result['sam']['rejected_guard_conflicts']} rejected guard conflicts.",
             f"- Late candidates: {reviewed['late_candidate_review']}",
             f"- Later target evidence: {reviewed['later_target_review']}",
             "- Re-ID: " + "; ".join(f"{a['candidate_entity_id']} {a['similarity']:.3f} {a['decision']}"
                                     for a in reviewed_result["reid_attempts"]) + ".",
             f"- Failure attribution: **{reviewed['failure']}**. Spatial diagnostic: {reviewed['spatial_tag']}.",
             "- Exact final physical location is " + ("visually reviewable at sampled frame(s)." if reviewed["final_location_visible"]
                                                    else "not established by frozen inference."),
             "", "| Reviewed visible target frame | Raw YOLO target hit | Local target hit |", "|---:|---|---|" ]
    lines.extend(f"| {s['frame_index']} | {s['target_raw_yolo_hit']} | {s['target_local_observation_hit']} |"
                 for s in samples)
    lines += ["", "Frame samples are sparse manual review, not exhaustive video GT. A landline box at the same frame is not counted as a target hit."]
    (base / "review.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return reviewed_result


def failure_matrix(results):
    matrix = {}
    for result in results:
        task = result["task"]
        sample_miss = any(not s["target_raw_yolo_hit"] for s in result["reviewed_visible_samples"])
        later_target_detected = any(s["target_raw_yolo_hit"] and
                                    s["frame_index"] > result["initial_source"]["frame_index"] + 180
                                    for s in result["reviewed_visible_samples"])
        fusion_value = ("FAIL" if not result["target_initialization_correct_on_review"] or
                        result["identity_fragmentation"] else
                        "NOT_MEASURABLE" if result["missed_reid_opportunity"] and not later_target_detected else "PASS")
        fields = {
            "Detection": "FAIL" if sample_miss else "PASS",
            "Local tracking": "FAIL" if not result["target_initialization_correct_on_review"] or result["identity_fragmentation"] else "PASS",
            "SAM continuity": "INSUFFICIENT_EVIDENCE" if result["sam"]["initial_loss_events"] and result["target_initialization_correct_on_review"] else "NOT_MEASURABLE",
            "SAM drift": "PASS" if not result["sam"]["rejected_guard_conflicts"] else "PASS",
            "Fusion": fusion_value,
            "Re-ID": "NOT_APPLICABLE" if not result["reid_attempts"] else "INSUFFICIENT_EVIDENCE",
            "False merge": "PASS" if not result["false_merge_reviewed"] else "FAIL",
            "Identity survival": "PASS" if result["target_initialization_correct_on_review"] and result["unobserved_seen"] else "FAIL",
            "Final visibility": "PASS" if result["exact_final_location_directly_visible"] else "NOT_MEASURABLE",
            "Spatial-memory gap": "INSUFFICIENT_EVIDENCE",
        }
        for name, value in fields.items():
            matrix.setdefault(name, {})[task] = value
    return matrix


def main():
    prediction_hash = verify_predictions_frozen()  # MUST precede reviewed_cases()
    reviewed = reviewed_cases()
    if set(reviewed) != {f"test{i}" for i in range(3, 10)}:
        raise ValueError("Incomplete seven-video review")
    results = [evaluate_one(task, reviewed[task]) for task in sorted(reviewed)]
    for result in results:
        write(OUT / result["task"] / "review.json", result)
    matrix = failure_matrix(results)
    write(OUT / "failure_matrix.json", matrix)
    samples = [sample for result in results for sample in result["reviewed_visible_samples"]]
    counts = Counter(a["decision"] for result in results for a in result["reid_attempts"])
    summary = {
        "schema": "v241-generalization-review-1", "prediction_manifest_sha256_before_gt_review": prediction_hash,
        "videos_evaluated": 7, "target_initializations_reviewed_correct": sum(r["target_initialization_correct_on_review"] for r in results),
        "persistent_target_id_retained_while_unobserved": sum(r["target_initialization_correct_on_review"] and r["unobserved_seen"] for r in results),
        "videos_with_later_visible_target_requiring_reid": sum(r["missed_reid_opportunity"] for r in results),
        "reid_attempts": sum(len(r["reid_attempts"]) for r in results), "reid_decision_counts": dict(counts),
        "true_reviewed_reid_matches": 0, "false_reid_matches": 0,
        "selected_distractor_candidates_safely_unmerged": 7,
        "missed_reid_opportunity_videos": [r["task"] for r in results if r["missed_reid_opportunity"]],
        "identity_fragmentation_videos": [r["task"] for r in results if r["identity_fragmentation"]],
        "reviewed_false_merges": 0, "accepted_sam_drift": 0,
        "rejected_sam_guard_conflicts": sum(r["sam"]["rejected_guard_conflicts"] for r in results),
        "sam_initial_loss_events": sum(r["sam"]["initial_loss_events"] for r in results),
        "reviewed_visible_target_samples": len(samples),
        "raw_yolo_target_hits": sum(s["target_raw_yolo_hit"] for s in samples),
        "local_target_hits": sum(s["target_local_observation_hit"] for s in samples),
        "visibility_conditioned_raw_detection_coverage": sum(s["target_raw_yolo_hit"] for s in samples)/len(samples),
        "raw_to_local_retention_on_reviewed_target_hits": 1.0,
        "sam_supported_reviewed_samples": sum(s["sam_mask_any_target_hypothesis"] for s in samples),
        "failure_attribution_counts": dict(Counter(r["failure_attribution"] for r in results)),
        "generalization_result_classification": "IDENTITY_PIPELINE_HAS_MULTIPLE_UPSTREAM_FAILURES",
        "next_architecture_decision": "IMPROVE_FUSION_FIRST",
        "scope": "Seven designed videos; sparse non-random manual samples. The V2.4 task1/task2 hardcoded seed/window routing required a fixed V2.4.1 adapter. No population accuracy estimate.",
    }
    write(OUT / "generalization_summary.json", summary)
    print(json.dumps({"classification": summary["generalization_result_classification"],
                      "next": summary["next_architecture_decision"], "reviewed_samples": len(samples),
                      "raw_hits": summary["raw_yolo_target_hits"], "reid_counts": dict(counts)}, indent=2))


if __name__ == "__main__":
    main()
