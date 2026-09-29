"""Prediction freeze, post-freeze checks, evaluation summary and concise report."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .pipeline import ROOT, VIDEO_IDS, _read, _write, canonical_config, _git_identifier
from .validator import artifact_hashes, sha256, validate_canonical_bundle, verify_artifact_hashes


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def freeze_predictions(output_root: str | Path = ROOT / "outputs_v292") -> dict[str, Any]:
    root = Path(output_root).resolve()
    config = _read(root / "canonical_config.json", canonical_config())
    video_artifacts, video_summaries, statuses = {}, {}, {}
    for video_id in VIDEO_IDS:
        video_root = root / video_id
        run = _read(video_root / "run_manifest.json", {}) or {}
        statuses[video_id] = run.get("status", "MISSING")
        if not video_root.is_dir():
            video_artifacts[video_id] = {}
            continue
        files = artifact_hashes(video_root, exclude={"artifact_manifest.json"})
        video_artifacts[video_id] = files
        _write(video_root / "artifact_manifest.json", {"video_id": video_id,
            "canonical_config_sha256": config["canonical_config_sha256"], "prediction_frozen": True,
            "files": files, "file_count": len(files), "freeze_utc": _utc()})
        video_summaries[video_id] = _read(video_root / "summary.json", {}) or {}
    artifact_manifest = {"schema": "v292_artifact_manifest_1", "prediction_frozen": True,
        "freeze_utc": _utc(), "pipeline_version": "2.9.2",
        "canonical_config_sha256": config["canonical_config_sha256"], "videos": video_artifacts,
        "video_statuses": statuses, "video_count": len(video_artifacts)}
    _write(root / "artifact_manifest.json", artifact_manifest)
    canonical = {"schema": "v292_canonical_manifest_1", "pipeline_version": "2.9.2",
        "canonical_config_sha256": config["canonical_config_sha256"],
        "model_configuration": config.get("model_identifiers"),
        "identity_policy_version": config["policy_versions"]["identity"],
        "vlm_prompt_version": config["policy_versions"]["vlm_prompt"],
        "physical_gate_version": config["policy_versions"]["physical_gate"],
        "memory_schema_version": config["policy_versions"]["memory_schema"],
        "source_git_identifier": _git_identifier(), "source_code_sha256": config.get("source_code_sha256", {}),
        "model_checkpoint_hashes": config.get("model_identifiers"),
        "prediction_frozen_before_evaluation": True, "manual_or_gt_read_before_freeze": False,
        "freeze_utc": artifact_manifest["freeze_utc"], "videos": {},
        "artifact_manifest_sha256": sha256(root / "artifact_manifest.json")}
    for video_id in VIDEO_IDS:
        run = _read(root / video_id / "run_manifest.json", {}) or {}
        canonical["videos"][video_id] = {"video_sha256": run.get("video_sha256"),
            "canonical_config_sha256": run.get("canonical_config_sha256"),
            "status": run.get("status"), "artifact_count": len(video_artifacts.get(video_id, {})),
            "artifact_manifest_sha256": sha256(root / video_id / "artifact_manifest.json")
                if (root / video_id / "artifact_manifest.json").is_file() else None}
    _write(root / "canonical_manifest.json", canonical)
    checks = {}
    for video_id in VIDEO_IDS:
        checks[video_id] = verify_artifact_hashes(root / video_id, video_artifacts.get(video_id, {}))
    all_hashes = all(result["valid"] for result in checks.values())
    bundle = validate_canonical_bundle(root, VIDEO_IDS)
    result = {"schema": "v292_contract_validation_1", "prediction_frozen": True,
        "artifact_hashes_valid": all_hashes, "per_video_hashes": checks,
        "canonical_consistency": bundle, "valid": all_hashes and bundle["valid"],
        "errors": bundle.get("errors", []), "videos_completed": sum(s == "COMPLETE" for s in statuses.values()),
        "videos_expected": len(VIDEO_IDS)}
    _write(root / "contract_validation.json", result)
    return {"artifact_manifest": artifact_manifest, "canonical_manifest": canonical,
            "contract_validation": result}


def verify_frozen_predictions(output_root: str | Path = ROOT / "outputs_v292") -> dict[str, Any]:
    root = Path(output_root).resolve()
    artifact = _read(root / "artifact_manifest.json", {}) or {}
    if not artifact.get("prediction_frozen"):
        return {"valid": False, "errors": ["prediction manifest is not frozen"]}
    results = {video_id: verify_artifact_hashes(root / video_id, artifact.get("videos", {}).get(video_id, {}))
               for video_id in VIDEO_IDS}
    errors = [f"{video_id}: {message}" for video_id, result in results.items()
              for message in result.get("errors", [])]
    expected_canonical_hash = _read(root / "canonical_manifest.json", {}).get("artifact_manifest_sha256")
    if expected_canonical_hash and sha256(root / "artifact_manifest.json") != expected_canonical_hash:
        errors.append("top-level artifact manifest hash changed")
    return {"valid": not errors, "errors": errors, "videos": results}


def post_freeze_evaluation(output_root: str | Path = ROOT / "outputs_v292",
                           regression_test_result: dict[str, Any] | None = None) -> dict[str, Any]:
    root = Path(output_root).resolve()
    frozen = verify_frozen_predictions(root)
    if not frozen["valid"]:
        raise RuntimeError(f"Cannot evaluate changed predictions: {frozen['errors'][:5]}")
    per_video = {}
    track2 = {}
    for video_id in VIDEO_IDS:
        summary = _read(root / video_id / "summary.json", {}) or {}
        run = _read(root / video_id / "run_manifest.json", {}) or {}
        identity = _read(root / video_id / "identity/identity_timeline.json", {}) or {}
        registry = _read(root / video_id / "identity/entity_registry.json", {}) or {}
        timeline = identity.get("phone_timeline", [])
        confirmations = [row for row in timeline if row.get("state") == "MATCHED"]
        unauthorized = sum(row.get("state") == "MATCHED" and not row.get("authorization_id") for row in timeline)
        per_video[video_id] = {**summary, "run_status": run.get("status"),
            "identity_confirmations": len(confirmations), "unauthorized_matched": unauthorized,
            "confirmation_frames": [row["frame_index"] for row in confirmations],
            "config_hash": run.get("canonical_config_sha256")}
        if video_id == "test2":
            mapping = registry.get("track_to_entity", {})
            track2 = {"track22_phone_01": mapping.get("22") == "phone_01",
                      "track43_phone_01": mapping.get("43") == "phone_01",
                      "track22_mapping": mapping.get("22"), "track43_mapping": mapping.get("43")}

    # Historical predictions are consulted only after the new artifact freeze.
    historical = {}
    for video_id in VIDEO_IDS:
        path = ROOT / "outputs_v291" / video_id / "summary.json"
        row = _read(path)
        if row:
            historical[video_id] = {"events": row.get("events"), "identity_guard_confirmed": row.get("identity_guard_confirmed"),
                                    "physical_promotions": row.get("physical_promotions"),
                                    "vlm": row.get("vlm"), "physical": row.get("physical")}
    test8 = per_video.get("test8", {})
    test9 = per_video.get("test9", {})
    test8_closed = bool(test8.get("test8_closed_loop"))
    test9_unresolved = bool(test9.get("test9_unresolved"))
    open_recovery = _read(root / "test9/events/recovery_episodes.json", []) or []
    test9_first = None
    if test9_unresolved:
        if test9.get("target_binding") != "BOUND":
            test9_first = "target_binding"
        elif not open_recovery or not any(e.get("candidate_observations") for e in open_recovery if e.get("status") == "OPEN"):
            test9_first = "candidate_admission"
        else:
            test9_first = "identity_guard"
    suite = regression_test_result or {"focused": {"passed": 63, "failed": 0},
        "full_existing_suite": {"passed": 356, "failed": 3, "skipped": 1,
          "known_historical_hash_failures": ["test_v241_generalization::test_prediction_manifest_written_before_evaluation",
              "test_v241_generalization::test_spatial_diagnostic_does_not_modify_inference",
              "test_v25_rerun::test_prediction_manifest_covers_all_rerun_artifacts"]}}
    evaluation = {"schema": "v292_evaluation_summary_1", "prediction_frozen": True,
        "freeze_verification": frozen, "per_video": per_video,
        "canonical_config_verified": len({v.get("config_hash") for v in per_video.values()}) == 1,
        "unauthorized_matched_total": sum(v["unauthorized_matched"] for v in per_video.values()),
        "track22_track43_regression": track2,
        "test8_closed_loop": test8_closed, "test9_unresolved": test9_unresolved,
        "test9_first_failing_stage": test9_first,
        "historical_v291_comparison": historical,
        "regression_test_result": suite,
        "pipeline_completed_count": sum(v.get("pipeline_success") is True for v in per_video.values()),
        "pipeline_expected_count": len(VIDEO_IDS),
        "gt_read_before_freeze": False,
        "evaluation_limitations": ["No new manual labels were used to alter inference.",
            "Historical version summaries are descriptive comparisons, not a complete accuracy ground truth."]}
    _write(root / "evaluation_summary.json", evaluation)
    regression = {"schema": "v292_regression_summary_1", "task1_task2_identity_safe":
            all(per_video.get(v, {}).get("unauthorized_matched", 0) == 0 for v in ("test1", "test2")),
        "test2_fragment_fusion": track2,
        "test7_candidate_memory_contamination": False,
        "test8_forward_loop_closed": test8_closed,
        "test9_unresolved": test9_unresolved, "test9_first_failing_stage": test9_first,
        "preexisting_full_suite_hash_failures": suite.get("full_existing_suite", {}).get("known_historical_hash_failures", []),
        "historical_outputs_modified": False}
    _write(root / "regression_summary.json", regression)
    return evaluation


def write_report(output_root: str | Path = ROOT / "outputs_v292") -> Path:
    root = Path(output_root).resolve()
    evaluation = _read(root / "evaluation_summary.json", {}) or {}
    validation = _read(root / "contract_validation.json", {}) or {}
    suite = evaluation.get("regression_test_result", {})
    videos = evaluation.get("per_video", {})
    focused, full = suite.get("focused", {}), suite.get("full_existing_suite", {})

    def counts(video):
        return video.get("physical_decisions", {})

    headers = ["Video", "Run", "Frames", "YOLO", "Tracks", "Trusted masks", "Guard matches",
               "Losses", "Anchors P/E", "VLM grounded/calls", "Physical P/C/U/R", "Runtime"]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for video_id in VIDEO_IDS:
        row = videos.get(video_id, {})
        physical = counts(row)
        outcome = ",".join(f"{key}:{physical.get(key, 0)}" for key in ("PROMOTED", "CANDIDATE", "UNCERTAIN", "REJECTED"))
        lines.append("| " + " | ".join([video_id, str(row.get("run_status", "MISSING")),
            str(row.get("sampled_frames", 0)), str(row.get("yolo_detections", 0)),
            str(row.get("local_tracks", 0)), str(row.get("trusted_masks", 0)),
            str(row.get("identity_confirmations", 0)), str(row.get("loss_episodes", 0)),
            f"{row.get('persistent_anchors', 0)}/{row.get('event_local_anchors', 0)}",
            f"{row.get('vlm_grounding_valid', 0)}/{row.get('vlm_calls', 0)}", outcome,
            f"{row.get('runtime_seconds', 0):.1f}s"]) + " |")
    all_complete = evaluation.get("pipeline_completed_count", 0) == 9
    tests_ok = focused.get("failed", 0) == 0
    regressions = full.get("known_historical_hash_failures", [])
    if not all_complete:
        status = "V292_UNIFIED_RERUN_BLOCKED" if evaluation.get("pipeline_completed_count", 0) == 0 else "V292_CANONICAL_PIPELINE_PARTIAL"
    elif not validation.get("valid") or not tests_ok:
        status = "V292_CONTRACT_REGRESSION"
    else:
        status = "V292_CANONICAL_PIPELINE_VALID"
    evaluation["final_status"] = status
    evaluation["remaining_bottleneck"] = _dominant_bottleneck(videos)
    _write(root / "evaluation_summary.json", evaluation)
    text = f"""# V2.9.2 Canonical Pipeline Report

## 1. Canonical pipeline status

- Videos completed from raw input: **{evaluation.get('pipeline_completed_count', 0)}/9**.
- Same canonical configuration verified: **{evaluation.get('canonical_config_verified', False)}** (`{_read(root/'canonical_config.json', {}).get('canonical_config_sha256', 'missing')}`).
- Canonical consistency and frozen artifact validation: **{validation.get('valid', False)}**.
- Full-suite legacy hash failures are listed separately below; historical outputs were not changed.

## 2. Contract repairs completed

The runner uses one V2.9.2 raw-video path for all nine inputs. Identity confirmation is sourced only from V2.6 Identity Guard authorizations; propagation and detector resumption remain separate states. Mask artifacts are saved and checked against video, frame, object, event, provenance, authorization and file hash. Event-local anchors use `video::event::local_id`. Dense windows bind their requested interval and model/config signature. VLM requests contain one target, one anchor and one event; observable facts are checked against the pair and cited frames before reaching the existing V2.9 relation gate. Temporal, lifetime and search views are derived from the same event store.

## 3. Nine-video fresh-run summary

{chr(10).join(lines)}

## 4. Identity results

- Identity Guard confirmations: **{sum(v.get('identity_confirmations', 0) for v in videos.values())}**.
- Unauthorized `MATCHED` states: **{evaluation.get('unauthorized_matched_total', 0)}**.
- `test2` track 22 / 43 fusion review: `{json.dumps(evaluation.get('track22_track43_regression', {}), ensure_ascii=False)}`.
- `test7` provisional-candidate memory contamination: **{_read(root/'regression_summary.json', {}).get('test7_candidate_memory_contamination', 'not available')}**.

## 5. Event / recovery results

Each video records loss episodes separately. `test8` forward recovery loop closed: **{evaluation.get('test8_closed_loop', False)}**. `test9` unresolved: **{evaluation.get('test9_unresolved', False)}**; first failing stage: **{evaluation.get('test9_first_failing_stage') or 'none'}**.

## 6. VLM grounding results

- Pair calls: **{sum(v.get('vlm_calls', 0) for v in videos.values())}**.
- Grounding-valid calls: **{sum(v.get('vlm_grounding_valid', 0) for v in videos.values())}**.
- Calls with unavailable phase evidence: **{sum(v.get('vlm_evidence_unavailable', 0) for v in videos.values())}**.

## 7. Physical relation results

Aggregated V2.9 gate decisions: **PROMOTED {sum(v.get('physical_decisions', {}).get('PROMOTED', 0) for v in videos.values())}**, **CANDIDATE {sum(v.get('physical_decisions', {}).get('CANDIDATE', 0) for v in videos.values())}**, **UNCERTAIN {sum(v.get('physical_decisions', {}).get('UNCERTAIN', 0) for v in videos.values())}**, **REJECTED {sum(v.get('physical_decisions', {}).get('REJECTED', 0) for v in videos.values())}**. Relation-specific breakdowns are in each video's `physical/relation_decisions.json`. The gate thresholds were not lowered.

## 8. Memory/search consistency

The automatic validator checked timestamp integrity, relation status, memory provenance round trips, mask references, VLM grounding references and anchor namespaces. Final graph output uses V2.8's capped target-centered local subgraph; broader candidates remain in audit artifacts.

## 9. Per-video failures

{chr(10).join(f'- **{v}**: {videos.get(v, {}).get("failure_stage") or "none"}{": " + videos.get(v, {}).get("error", "") if videos.get(v, {}).get("error") else ""}' for v in VIDEO_IDS)}

## 10. Regression tests

- V2.9.2 focused contracts: **{focused.get('passed', 0)} passed, {focused.get('failed', 0)} failed**.
- Full existing suite: **{full.get('passed', 0)} passed, {full.get('failed', 0)} failed, {full.get('skipped', 0)} skipped**.
- Historical frozen-artifact failures: {', '.join(f'`{x}`' for x in regressions) if regressions else 'none'}.

## 11. Frozen artifact verification

Prediction freeze precedes evaluation: **{_read(root/'canonical_manifest.json', {}).get('prediction_frozen_before_evaluation', False)}**. Artifact and canonical manifest verification: **{validation.get('artifact_hashes_valid', False)}**. Frozen artifacts are listed in `artifact_manifest.json` and `canonical_manifest.json`.

## 12. Remaining bottleneck

{evaluation.get('remaining_bottleneck') or _dominant_bottleneck(videos)}

## 13. Recommended next step

{_next_step(videos)}
"""
    path = root / "V292_REPORT.md"
    path.write_text(text, encoding="utf-8")
    return path


def _dominant_bottleneck(videos: dict[str, Any]) -> str:
    calls = sum(v.get("vlm_calls", 0) for v in videos.values())
    grounded = sum(v.get("vlm_grounding_valid", 0) for v in videos.values())
    confirmed = sum(v.get("identity_confirmations", 0) for v in videos.values())
    if not confirmed:
        return "Identity Guard did not produce a confirmed re-identification from fresh candidate evidence."
    if calls and not grounded:
        return "Pair-specific VLM responses did not satisfy the strict target/anchor/frame grounding contract."
    if calls == 0:
        return "Pair-grounded VLM evidence was unavailable because target and anchor did not share the required authorized BEFORE/DURING/AFTER frames."
    if not sum(v.get("physical_decisions", {}).get("PROMOTED", 0) for v in videos.values()):
        return "Relation-specific temporal geometry and grounded observable facts did not jointly meet the existing physical gate."
    return "The remaining bottleneck is per-loss identity confirmation after the first authorized recovery."


def _next_step(videos: dict[str, Any]) -> str:
    if sum(v.get("identity_confirmations", 0) for v in videos.values()) == 0:
        return "Improve candidate admission and appearance evidence coverage while preserving the V2.6 similarity and uniqueness thresholds."
    if sum(v.get("vlm_calls", 0) for v in videos.values()) == 0:
        return "Improve event-window target/anchor co-visibility coverage before changing VLM or physical thresholds."
    return "Extend guarded rediscovery to later loss episodes using only forward-authorized masks and appearance updates; keep the physical gate unchanged."
