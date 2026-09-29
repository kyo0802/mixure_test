"""Canonical recovery episodes and exact-coverage dense cache checks."""
from __future__ import annotations

import hashlib
import json
from typing import Any


CANONICAL_STAGES = (
    "video_reader", "frame_sampling", "yolo_perception", "local_tracking", "quality_diagnostics",
    "target_binding", "sam_target_propagation", "source_neutral_observations", "persistent_entity_fusion",
    "candidate_admission", "candidate_sam_support", "appearance_extraction", "identity_guard",
    "identity_state_machine", "multi_event_detection", "placement_loss_recovery", "dense_reinspection",
    "event_local_anchor_recovery", "per_loss_rediscovery", "pair_grounded_vlm", "physical_gate",
    "authoritative_memory", "temporal_memory", "lifetime_memory", "local_graph", "search", "visualization",
)


def cache_signature(*, video_sha256: str, start_frame: int, end_frame: int,
                    pipeline_version: str, code_config_sha256: str,
                    yolo_model: str, yolo_config: dict, sam_model: str,
                    sam_config: dict, sampling_policy: dict) -> str:
    payload = {"video_sha256": video_sha256, "requested_interval": [start_frame, end_frame],
               "pipeline_version": pipeline_version, "code_config_sha256": code_config_sha256,
               "yolo": {"model": yolo_model, "config": yolo_config},
               "sam": {"model": sam_model, "config": sam_config},
               "sampling_policy": sampling_policy}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def cache_reusable(cache: dict[str, Any], *, requested_start_frame: int,
                   requested_end_frame: int, signature: str) -> bool:
    sampling = cache.get("sampling", {})
    return (sampling.get("start_frame", 1) <= requested_start_frame
            and sampling.get("end_frame", -1) >= requested_end_frame
            and cache.get("signature") == signature)


def recovery_episodes(timeline: list[dict[str, Any]], authorizations: list[dict[str, Any]],
                      fps: float) -> list[dict[str, Any]]:
    """Close an episode only on actual Identity Guard authorization."""
    confirmations = {int(a["frame"]): a for a in authorizations
                     if a.get("decision") == "CONFIRMED_MATCH"
                     and a.get("source_guard_decision") == "V2.6_IDENTITY_GUARD"}
    rows = sorted(timeline, key=lambda x: int(x["frame_index"]))
    result, active = [], None
    number = 0
    for row in rows:
        frame = int(row["frame_index"])
        state = row.get("state")
        if state in {"UNOBSERVED", "LOST"} and active is None:
            number += 1
            active = {"loss_episode_id": f"LOSS{number:02d}", "loss_start_frame": frame,
                      "loss_start_time": frame / max(float(fps), 1e-9), "candidate_observations": [],
                      "identity_decision": "SEARCHING", "authorization_id": None,
                      "status": "OPEN"}
        auth = confirmations.get(frame)
        if active is not None and auth:
            active.update(identity_decision="IDENTITY_CONFIRMED", authorization_id=auth.get("authorization_id"),
                          recovery_frame=frame, recovery_time=frame/max(float(fps), 1e-9), status="CLOSED")
            result.append(active)
            active = None
        elif active is not None and state in {"PROPAGATION_RESUMED", "DETECTION_RESUMED", "PROVISIONAL", "AMBIGUOUS", "REJECTED"}:
            active["candidate_observations"].append({"frame": frame, "state": state,
                "candidate_id": row.get("candidate_id"), "authorization_id": row.get("authorization_id")})
    if active is not None:
        result.append(active)
    return result


def stage_sequence(video_ids: list[str]) -> dict[str, tuple[str, ...]]:
    return {video_id: CANONICAL_STAGES for video_id in video_ids}
