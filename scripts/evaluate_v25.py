"""Post-freeze manual review of V2.5. Never imported by inference."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v25"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_freeze():
    m = read(OUT / "prediction_manifest.json")
    assert m["stage"] == "A_BLIND_INFERENCE_COMPLETE" and not m["gt_read_before_freeze"]
    assert sha(OUT / "architecture_manifest.json") == m["architecture_manifest_sha256"]
    for name, expected in m["inference_code_sha256"].items():
        assert sha(ROOT / name) == expected, name
    for task, files in m["videos"].items():
        for name, expected in files.items():
            assert sha(OUT / task / name) == expected, f"{task}/{name}"
    a = read(OUT / "architecture_manifest.json")
    assert sha(ROOT / "outputs_v241/prediction_manifest.json") == a["v241_prediction_manifest_sha256"]
    for name, expected in a["frozen_component_sha256"].items():
        assert sha(ROOT / name) == expected, name
    for name, expected in a["v241_video_input_sha256"].items():
        assert sha(ROOT / name) == expected, name
    return sha(OUT / "prediction_manifest.json")


# Review labels are deliberately loaded only after verify_freeze().
REVIEW = {
    "test3": {"binding": True, "target_samples": [], "match_label": "none", "failure": "final_location_not_visible"},
    "test4": {"binding": True, "target_samples": [(1050, 107)], "match_label": "none", "failure": "ambiguous_appearance"},
    "test5": {"binding": False, "target_samples": [(288, 35), (366, 38)], "match_label": "wrong_initial_object_self_match", "failure": "target_binding"},
    "test6": {"binding": True, "target_samples": [], "match_label": "none", "failure": "target_detection_miss"},
    "test7": {"binding": True, "target_samples": [(720, 57), (888, 67)], "match_label": "false_distractor", "failure": "false_merge"},
    "test8": {"binding": True, "target_samples": [(804, None), (888, 73), (918, 74)], "match_label": "true_target", "failure": "post_match_continuity_unproven"},
    "test9": {"binding": True, "target_samples": [], "match_label": "none", "failure": "target_detection_miss"},
}


def frame_observation(stream, frame, track):
    rows = [o for o in stream["observations"] if o["frame_index"] == frame and
            (track is None or o["source_track_id"] == track)]
    if track is None and frame == 804:
        rows = [o for o in rows if o["candidate_id"] == "candidate_009"]
    return rows


def render_timeline(task, timeline, stream, audit, reviewed):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(5, 1, figsize=(13, 8), sharex=True, layout="constrained")
    rows = timeline["phone_timeline"]
    frames = [r["frame_index"] for r in rows]
    axes[0].step(frames, [int(r["raw_phone_count"] > 0) for r in rows], where="mid", label="any raw phone box")
    axes[0].step(frames, [int(bool(r["phone_track_ids"])) for r in rows], where="mid", label="phone local track")
    axes[0].legend(loc="upper right", fontsize=8)
    axes[0].set_ylabel("Observations")
    axes[1].step(frames, [int(r["accepted_sam_target"]) for r in rows], where="mid")
    axes[1].set_ylabel("Accepted SAM")
    states = {None: 0, "VISIBLE_TRUSTED": 2, "UNOBSERVED": 1}
    axes[2].step(frames, [states.get(r["state"], 1) for r in rows], where="mid")
    axes[2].set_yticks([0, 1, 2], ["unbound", "unobserved", "trusted"], fontsize=7)
    axes[2].set_ylabel("phone_01")
    candidates = {}
    for o in stream["observations"]:
        candidates.setdefault(o["candidate_id"], []).append(o["frame_index"])
    for i, (cid, fs) in enumerate(candidates.items()):
        axes[3].plot([min(fs), max(fs)], [i, i], linewidth=2)
    axes[3].set_ylabel("Candidates")
    for attempt in audit["attempts"]:
        f = attempt["frame_index"]
        color = "tab:green" if attempt["decision"] == "MATCH" else "tab:orange"
        axes[4].scatter(f, 1, s=16, color=color)
    for f, _ in reviewed["target_samples"]:
        for ax in axes:
            ax.axvline(f, color="tab:blue", alpha=.25, linewidth=1)
    axes[4].set_ylim(.5, 1.5)
    axes[4].set_yticks([1], ["Re-ID attempt"], fontsize=8)
    axes[4].set_xlabel("Frame (blue lines = reviewed visible target samples)")
    fig.suptitle(f"V2.5 {task} — frozen predictions + post-freeze sparse review")
    fig.savefig(OUT / task / "timeline.png", dpi=140)
    plt.close(fig)


def main():
    manifest_hash = verify_freeze()
    summary = {"prediction_manifest_sha256": manifest_hash, "review_scope": "sparse manually reviewed frames only", "videos": {}}
    failure = {}
    for task, reviewed in REVIEW.items():
        p = OUT / task
        binding = read(p / "target_binding_audit.json")
        stream = read(p / "candidate_stream.json")
        timeline = read(p / "identity_timeline.json")
        audit = read(p / "reid_audit.json")
        reinit = read(p / "sam_reinit_log.json")
        samples = []
        for frame, track in reviewed["target_samples"]:
            obs = frame_observation(stream, frame, track)
            assert obs, f"reviewed target box missing from stream: {task} {frame}"
            samples.append({"frame_index": frame, "track_id": track,
                            "candidate_ids": sorted({o["candidate_id"] for o in obs}),
                            "reid_evaluated": any(o["reid_evaluated"] for o in obs)})
        video = {"binding_decision": binding["decision"], "binding_correct_reviewed": reviewed["binding"],
                 "binding_track": binding["bound_target"]["source_track_id"],
                 "candidate_count": stream["candidate_count"], "reviewed_target_samples": samples,
                 "reid_decision": audit["decision"], "match_candidate_id": audit["match_candidate_id"],
                 "match_review_label": reviewed["match_label"], "reid_attempt_frames": len(audit["attempts"]),
                 "sam_reinit_executed": reinit["sam_reinitialization_executed"],
                 "primary_failure": reviewed["failure"]}
        if audit["decision"] == "MATCH":
            matches = [d for a in audit["attempts"] for d in a["candidate_decisions"] if d["decision"] == "MATCH"]
            assert len(matches) == 1
            video["match_frame"] = matches[0]["candidate_frame"]
            video["match_similarity"] = matches[0]["best_candidate_similarity"]
            video["match_margin"] = matches[0]["best_vs_second_margin"]
        summary["videos"][task] = video
        failure[task] = {"primary": reviewed["failure"], "binding_correct": reviewed["binding"],
                         "match_review_label": reviewed["match_label"]}
        render_timeline(task, timeline, stream, audit, reviewed)
        (p / "review.md").write_text(f"# {task} post-freeze review\n\n" +
            f"Binding correct: {reviewed['binding']}  \nRe-ID: {audit['decision']} ({reviewed['match_label']})  \n" +
            f"Primary failure: {reviewed['failure']}  \nReviewed target observations: {json.dumps(samples)}\n", encoding="utf-8")
    videos = summary["videos"]
    all_samples = [x for v in videos.values() for x in v["reviewed_target_samples"]]
    summary["aggregate"] = {"videos": len(videos), "correct_bindings": sum(v["binding_correct_reviewed"] for v in videos.values()),
        "candidate_hypotheses": sum(v["candidate_count"] for v in videos.values()),
        "reviewed_late_target_boxes_admitted": len(all_samples),
        "reviewed_late_target_boxes_reid_evaluated": sum(x["reid_evaluated"] for x in all_samples),
        "matches": sum(v["reid_decision"] == "MATCH" for v in videos.values()),
        "true_target_matches": sum(v["match_review_label"] == "true_target" for v in videos.values()),
        "false_distractor_matches": sum(v["match_review_label"] == "false_distractor" for v in videos.values()),
        "wrong_binding_self_matches": sum(v["match_review_label"] == "wrong_initial_object_self_match" for v in videos.values()),
        "sam_reinitializations": sum(v["sam_reinit_executed"] for v in videos.values())}
    (OUT / "fusion_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "failure_matrix.json").write_text(json.dumps(failure, indent=2), encoding="utf-8")
    print(json.dumps(summary["aggregate"], indent=2))


if __name__ == "__main__":
    main()
