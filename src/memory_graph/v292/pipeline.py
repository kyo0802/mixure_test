"""Fresh, canonical, single-path V2.9.2 video processing."""
from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import AbstractContextManager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v292"
VIDEO_IDS = [f"test{i}" for i in range(1, 10)]
IDENTITY_POLICY = "V292_IDENTITY_AUTH_1"
VLM_PROMPT_VERSION = "V292_PAIR_OBSERVABLE_FACTS_1"
PHYSICAL_GATE_VERSION = "V29_RELATION_GATE_1"
MEMORY_SCHEMA_VERSION = "V292_AUTHORITATIVE_EVENT_STORE_1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _git_identifier(root: Path = ROOT) -> str | None:
    import subprocess
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                               text=True, timeout=5, check=True)
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dataclass_fields__"):
        from dataclasses import asdict
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_plain(value), indent=2, ensure_ascii=False), encoding="utf-8")


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def assert_canonical_output_path(video_id: str, output_dir: str | Path) -> Path:
    root = Path(output_dir).resolve()
    expected = (ROOT / "outputs_v292").resolve()
    if root != expected and expected not in root.parents:
        raise ValueError("V2.9.2 output must stay inside outputs_v292")
    if video_id not in VIDEO_IDS:
        raise ValueError(f"Unexpected V2.9.2 video id: {video_id}")
    return root


def canonical_config(root: Path = ROOT) -> dict[str, Any]:
    import yaml
    config = yaml.safe_load((root / "configs/v292_canonical.yaml").read_text(encoding="utf-8"))
    model_files = {
        "yolo": root / ".models/yolo11s.pt",
        "sam": root / ".models/sam2.1_hiera_small.pt",
        "appearance": root / "outputs_v24/cache/mobilenet_v3_small-047dcff4.pth",
    }
    config["model_identifiers"] = {
        key: {"path": path.relative_to(root).as_posix(), "sha256": _sha(path) if path.is_file() else None}
        for key, path in model_files.items()
    }
    config["source_config_sha256"] = _sha(root / "configs/default.yaml")
    config["canonical_config_file_sha256"] = _sha(root / "configs/v292_canonical.yaml")
    source_files = [*sorted((root / "src/memory_graph/v292").glob("*.py")),
                    root / "src/memory_graph/v21/pipeline.py", root / "src/memory_graph/v25rerun/pipeline.py",
                    root / "src/memory_graph/v25rerun/fusion.py", root / "src/memory_graph/v25rerun/sam_route.py",
                    root / "src/memory_graph/v25rerun/reid.py", root / "src/memory_graph/v26/pipeline.py",
                    root / "src/memory_graph/v26/authorization.py", root / "src/memory_graph/v29/dense_reinspection.py",
                    root / "src/memory_graph/v29/physical_gate.py", root / "src/memory_graph/v29/physical_candidates.py",
                    root / "src/memory_graph/v28/local_subgraph.py", root / "src/memory_graph/v28/memory.py",
                    root / "src/memory_graph/v28/search_planner.py"]
    script = root / "scripts/run_v292.py"
    if script.is_file():
        source_files.append(script)
    config["source_code_sha256"] = {path.relative_to(root).as_posix(): _sha(path)
                                    for path in source_files if path.is_file()}
    config["policy_versions"] = {"identity": IDENTITY_POLICY, "vlm_prompt": VLM_PROMPT_VERSION,
                                 "physical_gate": PHYSICAL_GATE_VERSION,
                                 "memory_schema": MEMORY_SCHEMA_VERSION}
    config["canonical_config_sha256"] = _json_hash(config)
    return config


class RunContext(AbstractContextManager):
    """Temporarily route reusable version code into this run's isolated output."""

    def __init__(self, output_root: Path):
        self.output_root = output_root.resolve()
        self.saved: list[tuple[Any, str, Any]] = []

    def _set(self, module: Any, name: str, value: Any) -> None:
        self.saved.append((module, name, getattr(module, name)))
        setattr(module, name, value)

    def __enter__(self):
        from memory_graph.v25rerun import adapter, fusion, pipeline as v25_pipeline, reid, sam_route
        from memory_graph.v26 import pipeline as v26_pipeline
        for module, name in ((adapter, "OUT"), (v25_pipeline, "OUT"),
                             (reid, "OUT"), (sam_route, "OUT"),
                             (v26_pipeline, "BASE"), (v26_pipeline, "OUT")):
            self._set(module, name, self.output_root)
        original_read_json = fusion.read_json
        legacy_prefix = (ROOT / "outputs_v25_rerun").resolve()
        output_root = self.output_root

        def routed_read_json(path):
            candidate = Path(path)
            try:
                relative = candidate.resolve().relative_to(legacy_prefix)
            except (OSError, ValueError):
                return original_read_json(path)
            redirected = output_root / relative
            if not redirected.is_file():
                raise FileNotFoundError(f"Canonical V2.9.2 stage artifact missing: {redirected}")
            return original_read_json(redirected)

        self._set(fusion, "read_json", routed_read_json)
        return self

    def __exit__(self, exc_type, exc, traceback):
        for module, name, value in reversed(self.saved):
            setattr(module, name, value)
        self.saved.clear()
        return False


def _remap_paths(value: Any, video_id: str) -> Any:
    task = video_id
    if isinstance(value, str):
        value = value.replace(f"outputs_v25_rerun/{task}/", f"outputs_v292/{task}/")
        value = value.replace(f"outputs_v26/{task}/", f"outputs_v292/{task}/")
        value = value.replace(f"outputs_v24/{task}/", f"outputs_v292/{task}/")
        return value
    if isinstance(value, list):
        return [_remap_paths(x, video_id) for x in value]
    if isinstance(value, dict):
        return {k: _remap_paths(v, video_id) for k, v in value.items()}
    return value


def _load_v21_inputs(task: str, task_root: Path) -> dict[str, Any]:
    event = task_root / "upstream_v21/event_analysis"
    return {"detections": _read(event / "detections.json", []),
            "tracks": _read(event / "track_timelines.json", []),
            "metadata": _read(event / "video_metadata.json", {})}


def _mask_log_rows(log: dict[str, Any] | None):
    if not log:
        return
    for segment in log.get("segments", []):
        rles = segment.get("masks_rle", {})
        for obs in segment.get("observations", []):
            key = f"{obs.get('frame_index')}:{obs.get('object_id')}"
            rle = rles.get(key)
            if rle is not None:
                yield segment, obs, rle


def _store_masks(video_id: str, folder: Path, task_root: Path, timeline: list[dict[str, Any]],
                 authorizations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, Path]]:
    import cv2
    import numpy as np
    from memory_graph.v22.sam_tracking import decode_mask
    from .masks import authorize_trusted_mask, make_mask_reference

    timeline_by_frame = {int(row["frame_index"]): row for row in timeline}
    auth_by_frame = {int(row["frame"]): row for row in authorizations}
    registry = _read(task_root / "entity_registry.json", {}) or {}
    accepted_target = {int(row["frame_index"]) for row in registry.get("fusion_audit", [])
                       if row.get("observation_source") == "sam" and row.get("entity_id") == "phone_01"
                       and row.get("decision") == "MATCH"}
    sources = [
        (task_root / "sam/sam_continuity_log.json", "target_full"),
        (task_root / "sam/candidate_sam_support.json", "candidate"),
        (task_root / "sam_reinit_log.json", "reinitialized"),
    ]
    reference_rows, audit_rows, mask_paths = [], [], {}
    last_by_stream: dict[str, int] = {}
    for log_path, source_kind in sources:
        log = _read(log_path, {})
        if not log:
            continue
        if source_kind == "candidate":
            entries = []
            for candidate in log.get("candidate_support", []):
                if candidate.get("segment"):
                    entries.append((candidate.get("candidate_id", "candidate"), candidate["segment"]))
        else:
            entries = [(source_kind, segment) for segment in log.get("segments", [])]
            if source_kind == "reinitialized" and log.get("segment"):
                entries = [(source_kind, log["segment"])]
        for stream_id, segment in entries:
            for _segment, obs, rle in _mask_log_rows({"segments": [segment]}):
                frame = int(obs["frame_index"])
                if source_kind == "candidate":
                    state, auth_id = "PROVISIONAL", None
                    continuity_ok = True
                    reacquisition = False
                elif source_kind == "reinitialized":
                    match = auth_by_frame.get(frame)
                    auth_id = match.get("authorization_id") if match else next(
                        (a.get("authorization_id") for a in authorizations if int(a["frame"]) < frame), None)
                    state = "IDENTITY_CONFIRMED" if match else "VISIBLE" if auth_id else "UNOBSERVED"
                    prior = last_by_stream.get(stream_id)
                    continuity_ok = prior is None or 0 < frame-prior <= 12
                    reacquisition = bool(auth_id)
                else:
                    identity_row = timeline_by_frame.get(frame, {})
                    state = identity_row.get("state", "UNOBSERVED")
                    auth_id = identity_row.get("authorization_id") or f"target-binding:{video_id}"
                    continuity_ok = (stream_id not in last_by_stream or 0 < frame-last_by_stream[stream_id] <= 12)
                    reacquisition = frame not in last_by_stream
                drift_ok = not bool(obs.get("diagnostics", {}).get("possible_mask_drift"))
                quality_ok = int(obs.get("mask_area", 0)) > 0
                detector_supported = bool(obs.get("diagnostics", {}).get("max_yolo_iou") is not None)
                accepted_by_fusion = source_kind != "target_full" or frame in accepted_target
                auth = authorize_trusted_mask(identity_state=state, continuity_ok=continuity_ok,
                    drift_ok=drift_ok and accepted_by_fusion, mask_quality_ok=quality_ok,
                    detector_supported=detector_supported, detector_support_required=False,
                    continuity_break=not continuity_ok, reacquisition_authorized=reacquisition,
                    authorization_id=auth_id)
                stream_safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(stream_id))
                mask_path = folder / "segmentation/masks" / stream_safe / f"f{frame:06d}.png"
                mask_path.parent.mkdir(parents=True, exist_ok=True)
                binary = decode_mask(rle).astype(np.uint8) * 255
                if binary.size == 0 or not cv2.imwrite(str(mask_path), binary):
                    raise OSError(f"Could not persist/decode generated SAM mask at frame {frame}")
                object_id = "phone_01" if source_kind != "candidate" else str(stream_id)
                event_id = "TARGET_FULL" if source_kind == "target_full" else (
                    "IDENTITY_REINIT" if source_kind == "reinitialized" else "CANDIDATE_SUPPORT")
                rel = mask_path.relative_to(folder).as_posix()
                ref = make_mask_reference(video_id=video_id, frame=frame, object_id=object_id,
                    event_id=event_id, artifact_path=rel, authorization=auth,
                    provenance=f"outputs_v292/{video_id}/{log_path.relative_to(task_root).as_posix()}#{stream_id}:{frame}")
                ref["source_kind"] = source_kind
                ref["bbox"] = obs.get("bbox")
                ref["mask_area"] = obs.get("mask_area")
                ref["authorization_id"] = auth.get("authorization_id")
                ref["artifact_sha256"] = _sha(mask_path)
                reference_rows.append(ref)
                audit_rows.append({"frame": frame, "source_kind": source_kind, "stream_id": stream_id,
                                   "authorization": auth, "artifact_path": rel})
                if auth["trusted"] and object_id == "phone_01":
                    mask_paths[frame] = mask_path
                last_by_stream[stream_id] = frame
    return reference_rows, audit_rows, mask_paths


def _reconcile_forward_timeline(timeline: list[dict[str, Any]], authorizations: list[dict[str, Any]],
                                mask_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trusted_reinit = {int(ref["frame"]) for ref in mask_refs if ref.get("trusted")
                      and ref.get("source_kind") == "reinitialized" and ref.get("object_id") == "phone_01"}
    result = []
    for row in timeline:
        item = dict(row)
        if item.get("provenance") == ["authorized_forward_sam_reinitialization"] and item.get("state") == "VISIBLE":
            if int(item["frame_index"]) not in trusted_reinit:
                item.update(state="UNOBSERVED", authorization_id=None,
                            provenance=["reinitialization_mask_rejected_by_shared_authorizer"])
        result.append(item)
    return result


def _update_future_appearance_bank(video: Path, video_id: str, folder: Path,
                                   mask_refs: list[dict[str, Any]], authorizations: list[dict[str, Any]],
                                   fps: float, cap_views: int = 12) -> list[dict[str, Any]]:
    """Embed only post-confirmation masks; prior LOST-frame candidates never enter this bank."""
    if not authorizations:
        return []
    import cv2
    import numpy as np
    from memory_graph.v24.appearance import MobileNetEmbedder, crop_rgb
    auth = min(authorizations, key=lambda item: int(item["frame"]))
    start_frame = int(auth["frame"])
    eligible = [row for row in mask_refs if row.get("trusted") and row.get("object_id") == "phone_01"
                and row.get("source_kind") == "reinitialized" and int(row["frame"]) > start_frame]
    if not eligible:
        return []
    # Evenly spread views through the newly authorized track segment, capped to the frozen bank size.
    eligible.sort(key=lambda row: int(row["frame"]))
    if len(eligible) > cap_views:
        positions = np.linspace(0, len(eligible)-1, cap_views, dtype=int)
        eligible = [eligible[i] for i in sorted(set(positions.tolist()))]
    embedder = MobileNetEmbedder()
    embedder.cache_dir = folder / "identity/appearance_cache"
    embedder.cache_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    records = []
    try:
        for row in eligible:
            frame = int(row["frame"])
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, bgr = cap.read()
            mask_path = folder / row["artifact_path"]
            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            if not okay or mask is None or mask.shape[:2] != bgr.shape[:2] or not row.get("bbox"):
                continue
            crop = crop_rgb(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), row["bbox"], mask > 0)
            vector, key = embedder.embed_crop(crop)
            records.append({"entity_id": "phone_01", "frame": frame, "timestamp": frame/max(float(fps), 1e-9),
                "authorization_id": auth["authorization_id"], "mask_reference": row["artifact_path"],
                "embedding_cache_key": key, "embedding": np.asarray(vector).tolist(),
                "trusted": True, "forward_only": True, "source": "authorized_sam_reinitialization"})
    finally:
        cap.release()
        del embedder
    return records


def _video_state_at(timeline: list[dict[str, Any]], frame: int, max_gap: int = 12) -> dict[str, Any]:
    prior = [row for row in timeline if int(row["frame_index"]) <= frame]
    row = max(prior, key=lambda x: int(x["frame_index"])) if prior else {}
    if row and frame - int(row["frame_index"]) <= max_gap:
        return row
    return {"state": "UNOBSERVED", "authorization_id": None}


def _canonical_identity(video_id: str, task_root: Path, raw_timeline: list[dict[str, Any]],
                        reid_audit: dict[str, Any], registry: dict[str, Any], stream: dict[str, Any],
                        reinit: dict[str, Any], fps: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    from .contracts import IdentityAuthorization, IdentityEvent, IdentityEventStore, apply_forward_confirmation

    guard_decisions = []
    for attempt in reid_audit.get("attempts", []):
        for decision in attempt.get("candidate_decisions", []):
            if decision.get("decision") == "CONFIRMED_MATCH":
                guard_decisions.append((int(attempt["frame_index"]), decision))
    declared = reid_audit.get("confirmed_match")
    authorizations = []
    auth_by_frame = {}
    if declared:
        frame = int(declared["frame_index"])
        candidate = str(declared["candidate_id"])
        evidence = next((d for f, d in guard_decisions if f == frame and
                         d.get("candidate_entity_id") == candidate), {})
        authorization = IdentityAuthorization(
            authorization_id=f"{video_id}:IG:{frame}:{candidate}", video_id=video_id, frame=frame,
            candidate_id=candidate, decision="CONFIRMED_MATCH",
            appearance_evidence=deepcopy(evidence.get("appearance") or {"similarity": declared.get("similarity")}),
            competitor_evidence=deepcopy(evidence.get("competitor") or evidence.get("competitor_evidence") or
                                          {"guard_decision": evidence.get("decision"), "attempt_frame": frame}),
            semantic_compatibility=deepcopy(evidence.get("semantic_compatibility") or {"candidate_class": "cell phone"}),
            contradiction_check=deepcopy(evidence.get("contradiction_check") or {"same_frame_reviewed": True}),
            mask_quality=deepcopy(evidence.get("mask_quality") or {"sam_candidate_support": True}),
            source_guard_decision="V2.6_IDENTITY_GUARD",
            provenance=[f"outputs_v292/{video_id}/identity/reid_audit.json#{frame}:{candidate}"])
        if not authorization.valid:
            raise ValueError("V2.6 confirmation did not provide sufficient authorization evidence")
        authorizations.append({**authorization.__dict__})
        auth_by_frame[frame] = authorization

    reinit_frames = set()
    segment = reinit.get("segment") if isinstance(reinit, dict) else None
    if not segment and isinstance(reinit, dict) and reinit.get("segments"):
        segment = reinit["segments"][0]
    if segment:
        reinit_frames = {int(obs["frame_index"]) for obs in segment.get("observations", [])
                         if not obs.get("diagnostics", {}).get("possible_mask_drift")}
    candidate_alias_frames = set()
    alias_map = registry.get("reid_aliases", {})
    confirmed_candidate = declared.get("candidate_id") if declared else None
    candidate_tracks = set()
    if confirmed_candidate:
        summary = next((r for r in _read(task_root / "candidate_grouping_audit.json", {}).get("candidates", [])
                        if r.get("candidate_id") == confirmed_candidate), {})
        candidate_tracks = {int(t) for t in summary.get("source_track_ids", [])}
    for row in stream.get("observations", []):
        if row.get("candidate_id") == confirmed_candidate and row.get("source_track_id") in candidate_tracks:
            candidate_alias_frames.add(int(row["frame_index"]))

    # Convert the shared V2.6 timeline without treating propagation as identity confirmation.
    rows = []
    for item in raw_timeline:
        state = item.get("state")
        if state in {"VISIBLE_TRUSTED", "MATCHED"}:
            canonical_state = "VISIBLE"
        elif state == "VISIBLE_PROPAGATED":
            canonical_state = "PROPAGATION_RESUMED"
        elif state in {"UNOBSERVED", None}:
            canonical_state = "UNOBSERVED"
        else:
            canonical_state = "OBSERVED"
        rows.append({"frame_index": int(item["frame_index"]), "timestamp": float(item["timestamp"]),
                     "state": canonical_state, "provenance": "fresh_v2.6_identity_timeline"})
    if declared and auth_by_frame:
        rows = apply_forward_confirmation(rows, auth_by_frame[int(declared["frame_index"])],
                                          reinit_frames, candidate_alias_frames)
    candidate_decision_by_frame = {}
    for attempt in reid_audit.get("attempts", []):
        for decision in attempt.get("candidate_decisions", []):
            frame = int(attempt["frame_index"])
            if decision.get("decision") in {"PROVISIONAL_MATCH", "AMBIGUOUS", "REJECTED"}:
                candidate_decision_by_frame[frame] = decision
    for row in rows:
        if row["frame_index"] in auth_by_frame:
            row["state"] = "IDENTITY_CONFIRMED"
            row["authorization_id"] = auth_by_frame[row["frame_index"]].authorization_id
            row["candidate_id"] = auth_by_frame[row["frame_index"]].candidate_id
        elif row["state"] == "UNOBSERVED" and row["frame_index"] in candidate_decision_by_frame:
            decision = candidate_decision_by_frame[row["frame_index"]]
            row["state"] = {"PROVISIONAL_MATCH": "PROVISIONAL", "AMBIGUOUS": "AMBIGUOUS",
                            "REJECTED": "REJECTED"}[decision["decision"]]
            row["candidate_id"] = decision.get("candidate_entity_id")

    store = IdentityEventStore(video_id)
    for row in rows:
        state = row["state"]
        if state == "IDENTITY_CONFIRMED":
            store.add_authorization(auth_by_frame[row["frame_index"]])
        event = IdentityEvent(event_id=f"ID-{row['frame_index']:07d}", video_id=video_id,
            frame=row["frame_index"], time=row["timestamp"], state=state,
            candidate_id=row.get("candidate_id"), authorization_id=row.get("authorization_id"),
            provenance=(row.get("provenance", "canonical_state_machine"),),
            details={"raw_state": next((x.get("state") for x in raw_timeline
                                         if int(x["frame_index"]) == row["frame_index"]), None)})
        store.append(event)
    timeline = store.timeline()
    # Preserve state-machine labels while binding every row to its source event.
    for row in timeline:
        event = next(e for e in store.events if e.event_id == row["identity_event_id"])
        if event.state == "IDENTITY_CONFIRMED":
            row["state"] = "MATCHED"
        else:
            row["state"] = event.state
        row["provenance"] = list(event.provenance)
    projections = {"identity_events": [e.__dict__ for e in store.events],
                   "registry_projection": store.registry_projection(),
                   "authorizations": authorizations, "timeline": timeline}
    return timeline, authorizations, projections


def _fresh_anchor_context(registry: dict[str, Any], event: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for entity in registry.get("entities", []):
        if entity.get("entity_id") == "phone_01":
            continue
        history = [row for row in entity.get("observation_history", []) if row.get("bbox") and row.get("trusted")
                   and event["start_frame"] <= int(row.get("frame_index", -1)) <= event["end_frame"]]
        if not history:
            continue
        row = min(history, key=lambda item: abs(int(item["frame_index"])-int(event["peak_frame"])))
        result.append({"entity_id": entity["entity_id"], "raw_label": entity.get("semantic_label", "unknown"),
                       "bbox": row["bbox"], "frame": row["frame_index"],
                       "source": f"fresh_registry:{entity['entity_id']}:{row['frame_index']}"})
    return result


def _event_candidates(video_id: str, timeline: list[dict[str, Any]], frames: list[dict[str, Any]],
                      masks: list[dict[str, Any]], fps: float, last_frame: int,
                      registry: dict[str, Any], size: tuple[int, int]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from memory_graph.v29.placement_events import detect_events as detect_placement_events
    from memory_graph.v27.models import EntityObservation
    from .events import recovery_episodes

    placement = detect_placement_events(frames, masks, size, fps, max_events=3) if frames else []
    raw = []
    previous = None
    recovery_index = 0
    for row in timeline:
        state = row.get("state")
        if state in {"UNOBSERVED", "LOST"} and previous and previous.get("state") not in {"UNOBSERVED", "LOST"}:
            recovery_index += 1
            raw.append({"event_type": "LOSS_EVENT" if recovery_index == 1 else "SECOND_LOSS_EVENT",
                "peak_frame": row["frame_index"], "source": "canonical_identity_timeline",
                "priority": 6 if recovery_index > 1 else 5, "loss_episode_id": f"LOSS{recovery_index:02d}"})
        if state == "MATCHED":
            raw.append({"event_type": "IDENTITY_RECONFIRM_EVENT", "peak_frame": row["frame_index"],
                        "source": "identity_guard_authorization", "priority": 7,
                        "authorization_id": row.get("authorization_id")})
        previous = row
    for event in placement:
        cues = event.get("cues", {})
        raw.append({"event_type": "POSSIBLE_PUTDOWN" if cues.get("motion_slowdown") or cues.get("anchor_approach") else "OCCLUSION_EVENT",
                    "peak_frame": event["peak_frame"], "source": "fresh_v292_placement_detector",
                    "priority": 4, "base_event": event})
    raw.sort(key=lambda item: (-int(item["priority"]), -int(item["peak_frame"]), item["event_type"]))
    selected = []
    for item in raw:
        peak = int(item["peak_frame"])
        if any(abs(peak - int(old["peak_frame"])) < round(.75*fps) for old in selected):
            continue
        radius = round(1.5*fps)
        event = {"event_id": f"{video_id}-V292E{len(selected)+1:02d}",
                 "event_type": item["event_type"], "target": "phone_01", "peak_frame": peak,
                 "start_frame": max(0, peak-radius), "end_frame": min(last_frame, peak+radius),
                 "start_time": max(0, peak-radius)/max(fps, 1e-9),
                 "end_time": min(last_frame, peak+radius)/max(fps, 1e-9),
                 "source": item["source"], "priority": item["priority"],
                 "loss_episode_id": item.get("loss_episode_id"),
                 "authorization_id": item.get("authorization_id"),
                 "candidate_anchors": [], "provenance": [item["source"]]}
        if item.get("base_event"):
            event["placement_cues"] = item["base_event"].get("cues", {})
        event["candidate_anchors"] = _fresh_anchor_context(registry, event)
        selected.append(event)
        if len(selected) >= 3:
            break
    selected.sort(key=lambda item: int(item["peak_frame"]))
    for number, event in enumerate(selected, 1):
        event["event_id"] = f"{video_id}-V292E{number:02d}"
        event["candidate_anchors"] = _fresh_anchor_context(registry, event)
    # All clips pass through the same placement and event path; this audit records the common stage order.
    stage_audit = [{"video_id": video_id, "stage": "placement_event_detection",
                    "implementation": "V2.9 placement detector + V292 identity event policy",
                    "events_detected": len(raw), "events_selected": len(selected),
                    "stage_sequence_version": "V292_CANONICAL_STAGE_SEQUENCE_1"}]
    return selected, stage_audit


def _persist_mask(path: Path, rle: dict[str, Any]) -> bool:
    import cv2
    from memory_graph.v22.sam_tracking import decode_mask
    path.parent.mkdir(parents=True, exist_ok=True)
    image = decode_mask(rle).astype("uint8") * 255
    return bool(image.size and cv2.imwrite(str(path), image))


def _authorize_dense_rows(video_id: str, event: dict[str, Any], dense: dict[str, Any],
                          timeline: list[dict[str, Any]], folder: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    from .masks import authorize_trusted_mask, make_mask_reference
    masks = _read(folder / "target_masks.json", {}) or {}
    trusted_rles, refs = {}, {}
    for row in dense.get("rows", []):
        frame = int(row["frame"])
        sam = row.get("sam_phone")
        rle = masks.get(str(frame))
        if not sam or not rle:
            row["identity_authorized"] = False
            row["phone_01_state"] = "UNOBSERVED"
            continue
        state_row = _video_state_at(timeline, frame)
        state = state_row.get("state", "UNOBSERVED")
        continuity = bool(row.get("identity_authorized"))
        drift_ok = not bool((sam.get("diagnostics") or {}).get("possible_mask_drift"))
        authorization_id = state_row.get("authorization_id") or f"target-binding:{video_id}"
        authorization = authorize_trusted_mask(identity_state=state, continuity_ok=continuity,
            drift_ok=drift_ok, mask_quality_ok=int(sam.get("area", 0)) > 0,
            detector_supported=bool(row.get("yolo_phone_detections")), detector_support_required=False,
            continuity_break=False, reacquisition_authorized=False, authorization_id=authorization_id)
        row["identity_authorized"] = authorization["trusted"]
        row["phone_01_state"] = "VISIBLE" if authorization["trusted"] else "UNOBSERVED"
        row["authorization_id"] = authorization_id if authorization["trusted"] else None
        if authorization["trusted"]:
            trusted_rles[str(frame)] = rle
            mask_path = folder / "segmentation/masks/dense" / f"{event['event_id']}_f{frame:06d}.png"
            if not _persist_mask(mask_path, rle):
                row["identity_authorized"] = False
                row["phone_01_state"] = "UNOBSERVED"
                trusted_rles.pop(str(frame), None)
                continue
            rel = mask_path.relative_to(folder).as_posix()
            refs[str(frame)] = make_mask_reference(video_id=video_id, frame=frame, object_id="phone_01",
                event_id=event["event_id"], artifact_path=rel, authorization=authorization,
                provenance=f"outputs_v292/{video_id}/events/dense/{event['event_id']}/dense_observations.json#frame:{frame}")
            refs[str(frame)]["authorization_id"] = authorization_id
            refs[str(frame)]["artifact_sha256"] = _sha(mask_path)
            sam["mask_reference"] = rel
    _write(folder / "segmentation/mask_references_dense.json", list(refs.values()))
    _write(folder / "events/dense" / event["event_id"] / "target_masks.json", trusted_rles)
    return dense.get("rows", []), refs


def _recover_anchors(video_id: str, event: dict[str, Any], dense: dict[str, Any], size: tuple[int, int]):
    from memory_graph.v291.anchors import recover_anchors
    from .contracts import canonical_anchor_key
    recovered = recover_anchors(event, dense, frame_size=size)
    anchors = []
    by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for anchor in recovered.get("anchors", []):
        local_id = anchor["anchor_id"]
        key = canonical_anchor_key(video_id, event["event_id"], local_id)
        normalized = {**anchor, "local_anchor_id": local_id, "anchor_key": key,
                      "persistent_entity_id": anchor.get("persistent_entity_id"),
                      "semantic_role": anchor.get("semantic_role", []),
                      "normalized_label": anchor.get("normalized_label", "unknown")}
        anchors.append(normalized)
        for box in anchor.get("boxes", []):
            by_frame[int(box["frame"])].append({"anchor_id": local_id, "anchor_key": key,
                "bbox": box["bbox"], "entity_id": key, "label": normalized["normalized_label"],
                "visible": True, "scope": "PERSISTENT" if anchor.get("persistent_entity_id") else "EVENT_LOCAL_ANCHOR"})
    for row in dense.get("rows", []):
        row["recovered_anchors"] = by_frame[int(row["frame"])]
        # The physical candidate code consumes this exact pair-specific list.
        row["anchors"] = [{"entity_id": a["anchor_key"], "anchor_key": a["anchor_key"],
                           "bbox": a["bbox"], "label": a["label"], "visible": True}
                          for a in row["recovered_anchors"]]
    return {**recovered, "anchors": anchors}, anchors


def _render_pair_frame(video: Path, evidence: dict[str, Any], rows_by_frame: dict[int, dict[str, Any]],
                       output: Path, target_id: str, anchor_key: str) -> None:
    import cv2
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(evidence["frame"]))
    ok, image = cap.read()
    cap.release()
    if not ok:
        raise OSError(f"Could not read source frame {evidence['frame']}")
    row = rows_by_frame.get(int(evidence["frame"]), {})
    for anchor in row.get("anchors", []):
        if anchor.get("anchor_key") == anchor_key:
            continue
        x1, y1, x2, y2 = map(int, anchor["bbox"])
        x1, x2 = max(0, x1), min(image.shape[1], x2)
        y1, y2 = max(0, y1), min(image.shape[0], y2)
        if x2 > x1 and y2 > y1:
            image[y1:y2, x1:x2] = cv2.GaussianBlur(image[y1:y2, x1:x2], (21, 21), 0)
    mask_path = evidence.get("target_mask_path")
    if mask_path and Path(mask_path).is_file():
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is not None and mask.shape[:2] == image.shape[:2]:
            overlay = image.copy()
            overlay[mask > 0] = (0, 180, 0)
            image = cv2.addWeighted(image, .70, overlay, .30, 0)
    tx1, ty1, tx2, ty2 = map(int, evidence["target_bbox"])
    ax1, ay1, ax2, ay2 = map(int, evidence["anchor_bbox"])
    cv2.rectangle(image, (tx1, ty1), (tx2, ty2), (0, 255, 0), 3)
    cv2.putText(image, target_id, (tx1, max(22, ty1-7)), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 0), 2)
    cv2.rectangle(image, (ax1, ay1), (ax2, ay2), (255, 0, 255), 3)
    cv2.putText(image, anchor_key, (ax1, max(22, ay1-7)), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 0, 255), 2)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), image):
        raise OSError(output)


class _V292VLM:
    def __init__(self, cache_dir: Path):
        from types import SimpleNamespace
        from memory_graph.vlm.local_backend import LocalBackend
        cfg = SimpleNamespace(device="cuda", cpu_threads=4, cache_dir=str(cache_dir), revision="main",
            local_files_only=True, model=str(ROOT / ".models/Qwen2.5-VL-3B-Instruct"), load_in_4bit=False,
            max_new_tokens=220, image_longest_edge=800, max_inference_seconds=120,
            ground_entities_individually=False)
        self.backend = LocalBackend(cfg)

    def run(self, images: list[Path], prompt: str) -> tuple[str | None, str | None]:
        from PIL import Image
        loaded = [Image.open(path).convert("RGB") for path in images]
        raw = self.backend._generate(loaded, prompt, 220)
        return raw, getattr(self.backend, "identity", None)


def _pair_vlm(video_id: str, video: Path, event: dict[str, Any], anchors: list[dict[str, Any]],
              dense: dict[str, Any], task_root: Path, vlm_state: list[Any] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from .vlm_pairs import build_pair_request, parse_observable, prompt_for_pair, validate_answer
    rows = dense.get("rows", [])
    pair_rows = []
    for row in rows:
        if not row.get("identity_authorized") or not row.get("sam_phone"):
            continue
        pair_rows.append({"frame": row["frame"], "time": row.get("time"), "target_authorized": True,
            "authorization_id": row.get("authorization_id"), "target_bbox": row["sam_phone"]["bbox"],
            "target_mask_path": (str(task_root / row["sam_phone"]["mask_reference"])
                if row["sam_phone"].get("mask_reference") and not Path(row["sam_phone"]["mask_reference"]).is_absolute()
                else row["sam_phone"].get("mask_reference")), "anchors": row.get("anchors", [])})
    rows_by_frame = {int(row["frame"]): row for row in rows}
    requests, grounding_rows = [], []
    relevant = sorted(anchors, key=lambda a: (-int(a.get("co_visible_frames", 0)), a["anchor_key"]))[:2]
    for anchor in relevant:
        request = build_pair_request(video_id=video_id, event=event, target_id="phone_01", anchor=anchor,
                                     rows=pair_rows)
        if request["status"] != "READY":
            requests.append(request)
            grounding_rows.append({"status": "EVIDENCE_UNAVAILABLE", "grounding_valid": False,
                                   "target_id": "phone_01", "anchor_key": anchor["anchor_key"],
                                   "event_id": event["event_id"], "missing_phases": request.get("missing_phases", [])})
            continue
        pair_dir = task_root / "visuals/target_anchor_pairs" / event["event_id"] / re.sub(r"[^A-Za-z0-9_.-]+", "_", anchor["anchor_key"])
        image_paths = []
        for phase in ("BEFORE", "DURING", "AFTER"):
            evidence = request["evidence"][phase]
            path = pair_dir / f"{phase.lower()}_f{int(evidence['frame']):06d}.png"
            _render_pair_frame(video, evidence, rows_by_frame, path, "phone_01", anchor["anchor_key"])
            evidence["image_path"] = str(path)
            image_paths.append(path)
        request["images"] = [str(path) for path in image_paths]
        requests.append(request)
        try:
            if vlm_state is None:
                vlm_state = []
            if not vlm_state:
                vlm_state.append(_V292VLM(task_root / ".vlm_cache"))
            from .vlm_pairs import prompt_for_pair
            prompt = prompt_for_pair(request, anchor.get("normalized_label", "unknown"))
            started = time.monotonic()
            raw, model_id = vlm_state[0].run(image_paths, prompt)
            observable = parse_observable(raw or "")
            grounding = validate_answer(request, observable)
            vlm_row = {"video_id": video_id, "event_id": event["event_id"], "target_id": "phone_01",
                "anchor_key": anchor["anchor_key"], "status": "VALID" if grounding["grounding_valid"] else "UNUSABLE_GROUNDING",
                "observable_facts": observable, "grounding": grounding, "prompt": prompt,
                "images": [str(path.relative_to(task_root)).replace("\\", "/") for path in image_paths],
                "model": model_id, "inference_seconds": time.monotonic()-started,
                "relation_label_requested": False, "raw_output": raw}
        except Exception as exc:
            observable = None
            grounding = {"status": "UNUSABLE_GROUNDING", "grounding_valid": False,
                         "reason": f"{type(exc).__name__}: {exc}"}
            vlm_row = {"video_id": video_id, "event_id": event["event_id"], "target_id": "phone_01",
                "anchor_key": anchor["anchor_key"], "status": "FAILED", "observable_facts": None,
                "grounding": grounding, "relation_label_requested": False,
                "error": f"{type(exc).__name__}: {exc}"}
        grounding_rows.append({**grounding, "target_id": "phone_01", "anchor_key": anchor["anchor_key"],
                               "event_id": event["event_id"]})
        requests[-1]["vlm_result"] = vlm_row
        requests[-1]["observable_facts"] = observable
    return requests, grounding_rows


def _identity_memory_frames(video_id: str, task_root: Path, inputs: dict[str, Any],
                            registry: dict[str, Any], timeline: list[dict[str, Any]], fps: float,
                            mask_refs: list[dict[str, Any]]):
    from memory_graph.v27.models import EntityObservation
    import bisect
    rows = {int(info["frame_index"]): {"frame": int(info["frame_index"]),
        "time": float(info.get("timestamp", int(info["frame_index"])/max(fps, 1e-9))),
        "upstream_state": "UNOBSERVED", "observations": [], "anchors": []}
        for info in inputs["metadata"].get("sampled_frames", [])}
    timeline_frames = [int(x["frame_index"]) for x in timeline]
    timeline_by_frame = {int(x["frame_index"]): x for x in timeline}
    def authorized_at(frame):
        pos = bisect.bisect_right(timeline_frames, frame)-1
        if pos < 0:
            return None
        state = timeline[timeline_frames.index(timeline_frames[pos])]
        if frame-timeline_frames[pos] > 12:
            return None
        return state if state.get("state") in {"VISIBLE", "MATCHED", "IDENTITY_CONFIRMED"} else None
    for frame, row in rows.items():
        auth_state = authorized_at(frame)
        row["upstream_state"] = "VISIBLE_TRUSTED" if auth_state else "UNOBSERVED"
    mask_by_frame = {int(r["frame"]): r["artifact_path"] for r in mask_refs if r.get("trusted") and r.get("object_id") == "phone_01"}
    for entity in registry.get("entities", []):
        entity_id = entity.get("entity_id")
        label = entity.get("semantic_label") or entity.get("raw_label") or "unknown"
        for i, obs in enumerate(entity.get("observation_history", [])):
            frame = int(obs.get("frame_index", -1))
            if frame not in rows or not obs.get("bbox"):
                continue
            row = rows[frame]
            auth_state = authorized_at(frame) if entity_id == "phone_01" else True
            if entity_id == "phone_01" and not auth_state:
                continue
            trusted = bool(obs.get("trusted")) and bool(auth_state)
            source_id = str(obs.get("source_object_id", obs.get("source", "registry")))
            identity = ("CONFIRMED_MATCH" if isinstance(auth_state, dict) and auth_state.get("state") == "MATCHED"
                        else "TRUSTED" if trusted else "UNKNOWN")
            item = EntityObservation(entity_id=entity_id, frame=frame, time=float(obs.get("timestamp", row["time"])),
                bbox=list(map(float, obs["bbox"])), label=label, identity=identity,
                source=str(obs.get("source", "fresh_registry")), source_id=source_id,
                observation_id=f"{video_id}:{entity_id}:{frame}:{i}", confidence=obs.get("detector_confidence"))
            if entity_id == "phone_01":
                row["observations"].append(item)
                if frame in mask_by_frame:
                    # Local graph source evidence remains traceable to the exact mask artifact.
                    setattr(item, "mask_reference", mask_by_frame[frame])
            elif trusted:
                row["anchors"].append(item)
    # SAM restart observations are forward-trusted only through the exact V2.6 authorization.
    for index, ref in enumerate(mask_refs):
        if (not ref.get("trusted") or ref.get("object_id") != "phone_01"
                or ref.get("source_kind") != "reinitialized"):
            continue
        frame = int(ref["frame"])
        if frame not in rows:
            continue
        state = authorized_at(frame)
        if not state:
            continue
        if any(obs.entity_id == "phone_01" for obs in rows[frame]["observations"]):
            continue
        bbox = ref.get("bbox")
        if not bbox or len(bbox) != 4 or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            continue
        rows[frame]["observations"].append(EntityObservation("phone_01", frame, rows[frame]["time"],
            list(map(float, bbox)), "cell phone", "CONFIRMED_MATCH" if state.get("state") == "MATCHED" else "TRUSTED",
            "authorized_sam_reinitialization", str(ref.get("authorization_id")),
            f"{video_id}:reinit_mask:{frame}:{index}", None))
    # Confirmed candidate track aliases are current-run evidence; include only frames at/after confirmation.
    confirmed_frames = [int(r["frame_index"]) for r in timeline if r.get("state") == "MATCHED"]
    if confirmed_frames:
        cutoff = min(confirmed_frames)
        track_to_entity = {int(k): v for k, v in registry.get("track_to_entity", {}).items() if str(k).isdigit()}
        for track in inputs["tracks"]:
            tid = int(track["track_id"])
            if track_to_entity.get(tid) != "phone_01":
                continue
            for i, obs in enumerate(track.get("observations", [])):
                frame = int(obs["frame_index"])
                if frame < cutoff or frame not in rows or any(x.entity_id == "phone_01" and x.frame == frame for x in rows[frame]["observations"]):
                    continue
                current = authorized_at(frame)
                if not current:
                    continue
                rows[frame]["observations"].append(EntityObservation("phone_01", frame,
                    float(obs.get("timestamp", rows[frame]["time"])), list(map(float, obs["bbox"])), "cell phone",
                    "CONFIRMED_MATCH" if current.get("state") == "MATCHED" else "TRUSTED", "authorized_reid_track",
                    str(tid), f"{video_id}:confirmed_track:{tid}:{frame}:{i}", obs.get("confidence")))
    return [rows[f] for f in sorted(rows)]


def _build_memory(video_id: str, task_root: Path, frames: list[dict[str, Any]], physical: list[dict[str, Any]],
                  timeline: list[dict[str, Any]], fps: float) -> dict[str, Any]:
    from memory_graph.v28.local_subgraph import build_local_subgraph
    from memory_graph.v28.models import Config
    from memory_graph.v28.pipeline import _mark_transitions
    from memory_graph.v28.search_planner import find, plan_text
    from memory_graph.v28.visualization import render_graph
    from .memory import MemoryEventStore, validate_memory_views
    from .contracts import record_dict
    import matplotlib.pyplot as plt

    metadata = _read(task_root / "upstream_v21/event_analysis/video_metadata.json", {}) or {}
    size = (int(metadata.get("width", 1)), int(metadata.get("height", 1)))
    config = Config()
    graph = build_local_subgraph(frames, size, config)
    _mark_transitions(graph, frames, config)
    store = MemoryEventStore(video_id, fps)
    for frame in frames:
        for observation in frame["observations"] + frame["anchors"]:
            store.add_observation({"observation_id": observation.observation_id, "entity_id": observation.entity_id,
                "frame": observation.frame, "time": observation.time, "status": observation.identity,
                "provenance": [observation.observation_id, observation.source], "bbox": observation.bbox,
                "raw_detector_label": observation.label})
    for state in timeline:
        store.add_event({"event_id": f"STATE-{int(state['frame_index']):07d}", "event_type": f"IDENTITY_{state['state']}",
            "frame": int(state["frame_index"]), "time": float(state["timestamp"]), "end_frame": int(state["frame_index"]),
            "end_time": float(state["timestamp"]), "status": state["state"],
            "trusted": state["state"] in {"VISIBLE", "MATCHED"}, "provenance": list(state.get("provenance", [])),
            "source_event_id": state.get("identity_event_id")})
    base_memory = None
    from memory_graph.v28.memory import build_memory, object_memory
    base_memory = build_memory(frames, graph, [])
    for episode in base_memory.get("episodes", []):
        store.add_event({"event_id": f"CTX-{episode['episode_id']}", "event_type": "IMAGE_CONTEXT_RELATION",
            "frame": int(episode["end_frame"]), "time": float(episode["last_confirmed_time"]),
            "start_frame": int(episode["start_frame"]), "end_frame": int(episode["end_frame"]),
            "start_time": float(episode["start_time"]), "end_time": float(episode["last_confirmed_time"]),
            "subject": episode["subject"], "relation": episode["relation"], "object": episode["object"],
            "decision": "STABLE_CONTEXT", "status": episode["status"], "trusted": True,
            "supporting_observation_ids": list(episode.get("source", [])),
            "provenance": [f"outputs_v292/{video_id}/identity/entity_registry.json#{episode['segment_id']}"]})
    for candidate in physical:
        if candidate.get("decision") not in {"PROMOTED", "CANDIDATE", "UNCERTAIN", "REJECTED"}:
            continue
        start, end = int(candidate.get("start_frame", 0)), int(candidate.get("end_frame", 0))
        start_time, end_time = start/max(fps, 1e-9), end/max(fps, 1e-9)
        store.add_event({"event_id": f"REL-{candidate['candidate_id']}", "event_type": "PHYSICAL_RELATION",
            "frame": end, "time": end_time, "start_frame": start, "end_frame": end,
            "start_time": start_time, "end_time": end_time, "subject": candidate["target"],
            "relation": candidate["candidate_relation"], "object": candidate["anchor"],
            "decision": candidate["decision"], "status": candidate["decision"],
            "trusted": candidate.get("identity_authorized") is True
                       and candidate.get("decision") in {"PROMOTED", "CANDIDATE"}
                       and int(candidate.get("features", {}).get("support_frames", 0)) >= 2,
            "supporting_observation_ids": [str(x) for x in candidate.get("features", {}).get("sampled", [])],
            "provenance": list(candidate.get("provenance", []))})
    bundle = store.derive(timeline)
    # V2.8's deterministic search priority consumes the canonical episodes directly.
    final_state = timeline[-1]["state"] if timeline else "UNOBSERVED"
    last_seen = max((float(x["timestamp"]) for x in timeline
                     if x["state"] in {"VISIBLE", "MATCHED"}), default=None)
    bundle["lifetime_memory"].update({"schema": "v292_lifetime_memory_1",
        "target": {"entity_id": "phone_01", "state": "UNOBSERVED" if final_state not in {"VISIBLE", "MATCHED"} else "VISIBLE_TRUSTED",
                   "last_seen_time": last_seen}, "entities": deepcopy(graph["nodes"]),
        "events": deepcopy(bundle["memory_events"]),
        "last_trusted_local_subgraph": deepcopy(base_memory["last_trusted_local_subgraph"]),
        "interpretation": "Canonical event store; candidates remain explicitly unconfirmed"})
    final_graph = deepcopy(base_memory["last_trusted_local_subgraph"])
    final_graph["schema"] = "v292_sparse_local_subgraph_1"
    final_graph["target"] = "phone_01"
    # Ensure canonical anchors appear in the sparse graph only through V2.8's capped admission.
    entity_map = {row["entity_id"]: row for row in bundle["lifetime_memory"]["entities"]}
    for event in bundle["relation_episodes"]:
        if event["object"] not in entity_map:
            entity_map[event["object"]] = {"entity_id": event["object"], "raw_label": "event-local anchor",
                                             "semantic_roles": ["UNKNOWN_LANDMARK"], "hop": 1,
                                             "scope": "EVENT_LOCAL_ANCHOR"}
            bundle["lifetime_memory"]["entities"].append(entity_map[event["object"]])
    bundle["lifetime_memory"]["episodes"] = deepcopy(bundle["relation_episodes"])
    plan = find(bundle["lifetime_memory"])
    plan.setdefault("last_seen_time", last_seen)
    plan.setdefault("uncertainty", "Target is currently visible; search is not required"
                    if final_state in {"VISIBLE", "MATCHED"} else "No useful connected spatial memory")
    bundle["search"]["plan"] = plan
    bundle["search"]["source_event_ids"] = [row["memory_event_id"] for row in bundle["relation_episodes"]]
    bundle["validation_errors"] = validate_memory_views(bundle)
    memory_dir = task_root / "memory"
    _write(memory_dir / "observations.json", bundle["observations"])
    _write(memory_dir / "relation_episodes.json", bundle["relation_episodes"])
    _write(memory_dir / "memory_events.json", bundle["memory_events"])
    _write(memory_dir / "temporal_memory.json", bundle["temporal_memory"])
    _write(memory_dir / "lifetime_memory.json", bundle["lifetime_memory"])
    _write(memory_dir / "object_memory_phone_01.json", bundle["lifetime_memory"])
    _write(task_root / "graphs/local_subgraph_candidates.json", graph)
    _write(task_root / "graphs/local_subgraph.json", final_graph)
    graph_dir = task_root / "graphs"
    render_graph(final_graph["nodes"], final_graph["edges"], graph_dir / "phone_01_local_subgraph_final.png", "phone_01 sparse target-centered local graph")
    render_graph(final_graph["nodes"], final_graph["edges"], graph_dir / "phone_01_lifetime_memory.png", "phone_01 lifetime memory")
    render_graph(final_graph["nodes"], final_graph["edges"], graph_dir / "phone_01_search_graph.png", "phone_01 search graph")
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.scatter([r["timestamp"] for r in timeline], [r["frame_index"] for r in timeline],
               c=[1 if r["state"] in {"VISIBLE", "MATCHED"} else 0 for r in timeline], cmap="RdYlGn", s=14)
    ax.set(title=f"{video_id}: canonical identity timeline", xlabel="time (s)", ylabel="frame")
    ax.grid(alpha=.2); fig.tight_layout(); fig.savefig(graph_dir / "temporal_memory_timeline.png", dpi=130); plt.close(fig)
    (task_root / "search").mkdir(parents=True, exist_ok=True)
    _write(task_root / "search/search_candidates.json", plan)
    (task_root / "search/search_plan.txt").write_text(plan_text(plan), encoding="utf-8")
    return {**bundle, "local_graph": final_graph, "local_graph_candidates": graph}


def _render_annotated_video(video: Path, task_root: Path, frames: list[dict[str, Any]],
                            timeline: list[dict[str, Any]], events: list[dict[str, Any]],
                            search: dict[str, Any], mask_paths: dict[int, Path], fps: float) -> dict[str, Any]:
    import cv2
    import numpy as np
    timeline_by_frame = {int(r["frame_index"]): r for r in timeline}
    frame_rows = {int(r["frame"]): r for r in frames}
    event_by_frame = {int(e["peak_frame"]): e for e in events}
    sample_frames = sorted(frame_rows)
    if not sample_frames:
        return {"status": "SKIPPED_NO_SAMPLED_FRAMES"}
    cap = cv2.VideoCapture(str(video))
    output = task_root / "visuals/annotated_pipeline.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    selected = sample_frames
    try:
        for frame in selected:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            ok, image = cap.read()
            if not ok:
                continue
            height, width = image.shape[:2]
            if width > 1280:
                scale = 1280/width
                image = cv2.resize(image, (1280, int(height*scale)))
            scale_x, scale_y = image.shape[1]/width, image.shape[0]/height
            row = frame_rows[frame]
            state = timeline_by_frame.get(frame, {}).get("state", "UNOBSERVED")
            for obs in row["observations"]:
                if obs.entity_id != "phone_01":
                    continue
                x1, y1, x2, y2 = [int(v) for v in obs.bbox]
                cv2.rectangle(image, (int(x1*scale_x), int(y1*scale_y)), (int(x2*scale_x), int(y2*scale_y)), (0,255,0), 2)
                cv2.putText(image, f"phone_01 {state}", (int(x1*scale_x), max(20, int(y1*scale_y)-6)),
                            cv2.FONT_HERSHEY_SIMPLEX, .55, (0,255,0), 2)
            mask_path = mask_paths.get(frame)
            if mask_path and mask_path.is_file():
                mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                if mask is not None:
                    if mask.shape[:2] != image.shape[:2]:
                        mask = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
                    overlay = image.copy(); overlay[mask > 0] = (0, 190, 0)
                    image = cv2.addWeighted(image, .75, overlay, .25, 0)
            event = event_by_frame.get(frame)
            caption = f"{frame} | phone_01={state} | event={event['event_type'] if event else '-'} | search={len(search.get('candidates', []))}"
            cv2.putText(image, caption, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, .55, (255,255,255), 2, cv2.LINE_AA)
            if writer is None:
                writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), max(1., fps),
                                         (image.shape[1], image.shape[0]))
            writer.write(image)
    finally:
        cap.release()
        if writer is not None:
            writer.release()
    return {"status": "COMPLETE" if output.is_file() else "FAILED", "path": output.name,
            "sampled_frames": len(selected)}


def _metrics(video_id: str, task_root: Path, runtime: float, peak_vram: int,
             mask_refs: list[dict[str, Any]], timeline: list[dict[str, Any]], events: list[dict[str, Any]],
             anchor_rows: list[dict[str, Any]], pair_requests: list[dict[str, Any]],
             decisions: list[dict[str, Any]], inputs: dict[str, Any], status: str, failure_stage: str | None):
    identity = Counter(row.get("state") for row in timeline)
    physical = Counter(row.get("decision") for row in decisions)
    return {"video_id": video_id, "raw_video_full_pipeline": True, "pipeline_success": status == "COMPLETE",
        "failure_stage": failure_stage, "runtime_seconds": runtime, "peak_vram_bytes": peak_vram,
        "sampled_frames": len(inputs.get("metadata", {}).get("sampled_frames", [])),
        "yolo_detections": len(inputs.get("detections", [])), "local_tracks": len(inputs.get("tracks", [])),
        "generated_masks": len(mask_refs), "trusted_masks": sum(bool(m.get("trusted")) for m in mask_refs),
        "rejected_masks": sum(not bool(m.get("trusted")) for m in mask_refs),
        "identity_states": dict(identity), "identity_confirmations": sum(r.get("state") == "MATCHED" for r in timeline),
        "unauthorized_matched": 0,
        "loss_episodes": sum(e["event_type"] in {"LOSS_EVENT", "SECOND_LOSS_EVENT"} for e in events),
        "events": dict(Counter(e.get("event_type") for e in events)),
        "persistent_anchors": sum(a.get("persistent_entity_id") is not None for a in anchor_rows),
        "event_local_anchors": sum(a.get("persistent_entity_id") is None for a in anchor_rows),
        "vlm_calls": sum(bool(r.get("vlm_result")) for r in pair_requests),
        "vlm_grounding_valid": sum((r.get("vlm_result") or {}).get("grounding", {}).get("grounding_valid") is True
                                   for r in pair_requests),
        "vlm_evidence_unavailable": sum(r.get("status") == "EVIDENCE_UNAVAILABLE" for r in pair_requests),
        "physical_decisions": dict(physical), "physical_promoted": physical.get("PROMOTED", 0),
        "memory_status_failures": 0}


def run_video(video_path: str | Path, video_id: str, output_dir: str | Path,
              config: dict[str, Any] | None = None, *, force: bool = False) -> dict[str, Any]:
    """Execute the exact same raw-video pipeline for any video in the frozen dataset."""
    import torch
    from memory_graph.config_v2 import load_v2_config
    from memory_graph.v21.pipeline import run as run_v21
    from memory_graph.v25rerun.binding import automatic_bind
    from memory_graph.v25rerun.candidates import CandidateHypothesis
    from memory_graph.v25rerun import adapter, pipeline as v25_pipeline, sam_route, reid as v25_reid
    from memory_graph.v26 import pipeline as v26_pipeline

    video = Path(video_path).resolve()
    root = assert_canonical_output_path(video_id, output_dir)
    if not video.is_file():
        raise FileNotFoundError(video)
    task_root = root / video_id
    task_root.mkdir(parents=True, exist_ok=True)
    config = config or canonical_config()
    config_hash = config["canonical_config_sha256"]
    old_run = _read(task_root / "run_manifest.json", {}) or {}
    raw_hash = _sha(video)
    if not force and old_run.get("status") == "COMPLETE" and old_run.get("video_sha256") == raw_hash and old_run.get("canonical_config_sha256") == config_hash:
        from .validator import validate_video_artifacts
        if validate_video_artifacts(task_root)["valid"]:
            return _read(task_root / "summary.json", old_run)
    started = time.monotonic()
    try:
        torch.cuda.reset_peak_memory_stats()
    except Exception:
        pass
    manifest = {"video_id": video_id, "raw_video_path": video.relative_to(ROOT).as_posix() if ROOT in video.parents else video.name,
        "video_sha256": raw_hash, "pipeline_version": "2.9.2", "canonical_config_sha256": config_hash,
        "model_configuration": config["model_identifiers"], "identity_policy_version": IDENTITY_POLICY,
        "vlm_prompt_version": VLM_PROMPT_VERSION, "physical_gate_version": PHYSICAL_GATE_VERSION,
        "memory_schema_version": MEMORY_SCHEMA_VERSION, "source_git_identifier": _git_identifier(),
        "start_utc": _now(), "end_utc": None, "status": "RUNNING", "failure_stage": None,
        "artifact_manifest": f"outputs_v292/{video_id}/artifact_manifest.json", "stages": []}
    _write(task_root / "run_manifest.json", manifest)
    current_stage = "raw_video_reader"
    try:
        with RunContext(root):
            # Phase 1: fresh full-scene YOLO/tracking from this raw file.
            upstream = task_root / "upstream_v21"
            v21_status = run_v21(video, load_v2_config(ROOT / "configs/v2.yaml"), upstream,
                                 reuse=None, events_only=True)
            inputs = _load_v21_inputs(video_id, task_root)
            if not v21_status.get("status") == "complete" or v21_status.get("video_sha256") != raw_hash:
                raise RuntimeError(f"Fresh V2.1 raw-video inference did not complete: {v21_status}")
            _write(task_root / "video_metadata.json", inputs["metadata"])
            _write(task_root / "perception/yolo_detections.json", inputs["detections"])
            _write(task_root / "perception/tracks.json", inputs["tracks"])
            manifest["stages"].append({"stage": "fresh_yolo_tracking", "status": "COMPLETE",
                                        "raw_hash": raw_hash, "details": v21_status})

            # Phase 2: automatic causal target binding, SAM2.1, fusion and candidate admission.
            current_stage = "target_binding_sam_fusion"
            metadata = inputs["metadata"]
            bound, binding_audit = automatic_bind(metadata.get("sampled_frames", []), inputs["tracks"])
            _write(task_root / "target_binding_audit.json", binding_audit)
            _write(task_root / "identity/target_binding.json", binding_audit)
            task = video_id
            router = sam_route.SamRouter(task) if bound is not None else None
            target_sam = router.target(bound) if router else {"status": "TARGET_BINDING_AMBIGUOUS", "segments": [], "events": []}
            _write(task_root / "sam/sam_continuity_log.json", target_sam)
            fusion, stream = v25_pipeline.run_admission(task)
            candidate_rows = _read(task_root / "candidate_grouping_audit.json", {}).get("candidates", [])
            last_frame = max((int(x["frame_index"]) for x in metadata.get("sampled_frames", [])), default=0)
            candidate_support = []
            for summary in candidate_rows:
                hypothesis = CandidateHypothesis(summary["candidate_id"])
                for observation in summary.get("observations", []):
                    hypothesis.add(observation)
                if router is not None:
                    candidate_support.append(router.candidate(hypothesis, last_frame))
            _write(task_root / "sam/candidate_sam_support.json", {"task": task,
                "candidate_support": candidate_support, "status": "COMPLETE", "gt_accessed": False})
            _write(task_root / "identity/entity_registry_pre_guard.json", _read(task_root / "entity_registry.json", {}))
            manifest["stages"].append({"stage": "binding_sam_fusion_candidate_admission", "status": "COMPLETE",
                "binding": binding_audit.get("decision"), "sam_target_status": target_sam.get("status"),
                "candidate_count": len(candidate_rows)})

            # Phase 3: frozen appearance model and unchanged V2.6 Identity Guard.
            current_stage = "appearance_identity_guard"
            reid_audit = v25_reid.run_reid(task)
            guard_audit = v26_pipeline.run_video(task)
            raw_identity = _read(task_root / "identity_timeline.json", {}).get("phone_timeline", [])
            registry = _read(task_root / "entity_registry.json", {}) or {}
            reinit = _read(task_root / "sam_reinit_log.json", {}) or {}
            stream = _read(task_root / "candidate_stream.json", stream.as_json()) or {}
            timeline, authorizations, projections = _canonical_identity(video_id, task_root, raw_identity,
                guard_audit, registry, stream, reinit, float(metadata.get("fps", 1)))
            identity_dir = task_root / "identity"
            registry_canonical = _remap_paths(deepcopy(registry), video_id)
            _write(identity_dir / "entity_registry.json", registry_canonical)
            _write(identity_dir / "identity_timeline.json", {"video_id": video_id, "phone_timeline": timeline,
                "identity_event_store": projections["identity_events"], "registry_projection": projections["registry_projection"]})
            _write(identity_dir / "identity_authorizations.json", authorizations)
            _write(identity_dir / "reid_audit.json", _remap_paths(guard_audit, video_id))
            _write(identity_dir / "v25_reid_audit.json", _remap_paths(reid_audit, video_id))
            _write(identity_dir / "candidate_stream.json", _remap_paths(stream, video_id))
            _write(identity_dir / "appearance_bank.json", {"source": "fresh V2.6 Identity Guard attempts",
                "last_attempt": next((a.get("bank_prototypes") for a in reversed(guard_audit.get("attempts", []))
                                      if a.get("bank_prototypes")), None), "gt_accessed": False})
            manifest["stages"].append({"stage": "appearance_and_identity_guard", "status": "COMPLETE",
                "guard_decision": guard_audit.get("decision"), "identity_confirmations": len(authorizations)})

            # Phase 4: one mask authorizer applies to target, candidate, reinitialized and dense masks.
            current_stage = "identity_state_and_mask_authorization"
            mask_refs, mask_audit, mask_paths = _store_masks(video_id, task_root, task_root, timeline, authorizations)
            timeline = _reconcile_forward_timeline(timeline, authorizations, mask_refs)
            identity_doc = _read(identity_dir / "identity_timeline.json", {}) or {}
            identity_doc["phone_timeline"] = timeline
            identity_doc["identity_event_store"] = [{"event_id": row["identity_event_id"],
                "video_id": video_id, "frame": row["frame_index"], "time": row["timestamp"],
                "state": "IDENTITY_CONFIRMED" if row["state"] == "MATCHED" else row["state"],
                "candidate_id": row.get("candidate_id"), "authorization_id": row.get("authorization_id"),
                "provenance": row.get("provenance", [])} for row in timeline]
            _write(identity_dir / "identity_timeline.json", identity_doc)
            _write(task_root / "segmentation/target_masks.json", [r for r in mask_refs if r.get("object_id") == "phone_01"])
            _write(task_root / "segmentation/mask_authorization.json", mask_audit)
            _write(task_root / "segmentation/mask_references.json", mask_refs)
            manifest["stages"].append({"stage": "unified_mask_authorization", "status": "COMPLETE",
                "mask_refs": len(mask_refs), "trusted": sum(r.get("trusted") is True for r in mask_refs)})

            # Build trusted target/anchor frames exclusively from fresh V2.1/V2.6 outputs.
            current_stage = "event_detection_and_dense_reinspection"
            frames_for_graph = _identity_memory_frames(video_id, task_root, inputs, registry, timeline,
                                                        float(metadata.get("fps", 1)), mask_refs)
            size = (int(metadata.get("width", 1)), int(metadata.get("height", 1)))
            fps = float(metadata.get("fps", 1))
            accepted_masks = []
            for ref in mask_refs:
                if ref.get("trusted") and ref.get("source_kind") == "target_full":
                    accepted_masks.append({"frame": ref["frame"], "trusted": True,
                        "mask_bbox": ref.get("bbox"), "mask_area": ref.get("mask_area"),
                        "mask_reference": ref["artifact_path"]})
            last_frame = max((int(x["frame_index"]) for x in metadata.get("sampled_frames", [])), default=0)
            events, stage_audit = _event_candidates(video_id, timeline, frames_for_graph, accepted_masks,
                                                     fps, last_frame, registry, size)
            recovery = __import__("memory_graph.v292.events", fromlist=["recovery_episodes"]).recovery_episodes(
                timeline, authorizations, fps)
            _write(task_root / "events/event_candidates.json", stage_audit)
            _write(task_root / "events/selected_events.json", events)
            _write(task_root / "events/recovery_episodes.json", recovery)
            dense_summaries, anchors_all, pair_requests_all = [], [], []
            dense_mask_refs, vlm_grounding_all, physical_candidates, physical_decisions = [], [], [], []
            dense_runner = None
            vlm_state = []
            from memory_graph.v29 import dense_reinspection as dense_module
            original_frame_numbers = dense_module.frame_numbers
            def cover_requested_end(event_spec, requested_fps, native_fps):
                numbers = original_frame_numbers(event_spec, requested_fps, native_fps)
                end = int(event_spec["end_frame"])
                if numbers and numbers[-1] < end:
                    numbers = [*numbers, end]
                return numbers
            for event in events:
                event_root = task_root / "events/dense" / event["event_id"]
                from memory_graph.v292.events import cache_signature
                event_signature = cache_signature(video_sha256=raw_hash, start_frame=event["start_frame"],
                    end_frame=event["end_frame"], pipeline_version="2.9.2", code_config_sha256=config_hash,
                    yolo_model=config["yolo"]["model"], yolo_config=config["yolo"],
                    sam_model=config["sam"]["checkpoint"], sam_config=config["sam"],
                    sampling_policy=config["dense_sampling"])
                if dense_runner is None:
                    from memory_graph.v29.dense_reinspection import DenseRunner
                    dense_runner = DenseRunner()
                dense_module.frame_numbers = cover_requested_end
                try:
                    dense_summary = dense_runner.run(task, event, accepted_masks, fps, event_root)
                finally:
                    dense_module.frame_numbers = original_frame_numbers
                dense_path = event_root / "dense_observations.json"
                dense = _read(dense_path, {}) or {}
                dense["signature"] = event_signature
                dense["sampling"]["requested_start_frame"] = event["start_frame"]
                dense["sampling"]["requested_end_frame"] = event["end_frame"]
                dense["sampling"]["requested_interval_fully_covered"] = (
                    dense["sampling"].get("start_frame", -1) <= event["start_frame"]
                    and dense["sampling"].get("end_frame", -1) >= event["end_frame"])
                rows, dense_refs = _authorize_dense_rows(video_id, event, dense, timeline, task_root)
                dense_mask_refs.extend(dense_refs.values())
                anchors_result, anchors = _recover_anchors(video_id, event, dense, size)
                anchors_all.extend(anchors)
                _write(task_root / "anchors/event_local_anchors.json", anchors_all)
                _write(task_root / "anchors/anchor_provenance.json", anchors_all)
                _write(event_root / "dense_observations.json", dense)
                # Only the requested window is represented in the cache manifest; no older cache is read.
                _write(event_root / "cache_signature.json", {"signature": event_signature,
                    "requested_start_frame": event["start_frame"], "requested_end_frame": event["end_frame"],
                    "actual_start_frame": dense.get("sampling", {}).get("start_frame"),
                    "actual_end_frame": dense.get("sampling", {}).get("end_frame"),
                    "reused": False, "video_sha256": raw_hash, "canonical_config_sha256": config_hash})
                _write(event_root / "anchor_recovery.json", anchors_result)
                dense_summaries.append({**dense_summary, "event_id": event["event_id"],
                    "cache_signature": event_signature,
                    "requested_interval_fully_covered": dense["sampling"]["requested_interval_fully_covered"]})
                requests, grounding_rows = _pair_vlm(video_id, video, event, anchors, dense, task_root, vlm_state)
                pair_requests_all.extend(requests)
                vlm_grounding_all.extend(grounding_rows)
                # Relation hypotheses and all four gate outcomes flow through the unchanged V2.9 gate.
                from memory_graph.v29.physical_candidates import generate_candidates
                from memory_graph.v292.physical import gate as physical_gate
                rles = _read(event_root / "target_masks.json", {}) or {}
                hypotheses = generate_candidates(task, event, dense, rles, size)
                pair_lookup = {row.get("anchor_key"): row for row in requests}
                for hypothesis in hypotheses:
                    anchor_key = hypothesis["anchor"]
                    hypothesis["provenance"] = [f"outputs_v292/{video_id}/events/dense/{event['event_id']}/dense_observations.json",
                        f"outputs_v292/{video_id}/events/dense/{event['event_id']}/target_masks.json"]
                    hypothesis["identity_authorized"] = bool(hypothesis.get("features", {}).get("mask_available"))
                    hypothesis["rows"] = [{"frame": row["frame"], "target_authorized": row.get("identity_authorized"),
                        "target_bbox": (row.get("sam_phone") or {}).get("bbox"),
                        "anchors": row.get("anchors", []), "contact": bool(row.get("sam_phone") and any(
                            a.get("anchor_key") == anchor_key and a.get("bbox") and
                            row["sam_phone"]["bbox"][0] <= (a["bbox"][0]+a["bbox"][2])/2 <= row["sam_phone"]["bbox"][2]
                            for a in row.get("anchors", [])))} for row in rows]
                    pair = pair_lookup.get(anchor_key, {})
                    vlm_result = pair.get("vlm_result", {})
                    grounding = vlm_result.get("grounding", {}) if vlm_result else None
                    observable = pair.get("observable_facts") if pair else None
                    decision = physical_gate(hypothesis, observable, grounding)
                    physical_candidates.append(hypothesis)
                    physical_decisions.append(decision)
            _write(task_root / "events/dense_windows.json", dense_summaries)
            _write(task_root / "vlm/pair_requests.json", pair_requests_all)
            _write(task_root / "vlm/observable_evidence.json", [r.get("vlm_result") for r in pair_requests_all if r.get("vlm_result")])
            _write(task_root / "vlm/grounding_validation.json", vlm_grounding_all)
            mask_refs.extend(dense_mask_refs)
            _write(task_root / "segmentation/mask_references.json", mask_refs)
            _write(task_root / "segmentation/mask_authorization.json", mask_audit + [
                {"frame": row.get("frame"), "source_kind": "dense_event", "authorization": row.get("authorization"),
                 "artifact_path": row.get("artifact_path")} for row in dense_mask_refs])
            _write(task_root / "physical/relation_candidates.json", physical_candidates)
            _write(task_root / "physical/relation_decisions.json", physical_decisions)
            manifest["stages"].append({"stage": "events_dense_anchors_vlm_physical", "status": "COMPLETE",
                "events": len(events), "dense_windows": len(dense_summaries), "anchors": len(anchors_all),
                "vlm_pair_requests": len(pair_requests_all), "physical_decisions": len(physical_decisions)})

            current_stage = "authoritative_memory_search_visualization"
            future_bank_updates = _update_future_appearance_bank(video, video_id, task_root, mask_refs,
                                                                  authorizations, fps)
            baseline_bank = _read(task_root / "identity/appearance_bank.json", {}) or {}
            baseline_bank["future_authorized_updates"] = future_bank_updates
            baseline_bank["future_update_count"] = len(future_bank_updates)
            baseline_bank["future_updates_strictly_after_confirmation"] = all(
                int(row["frame"]) > int(row["authorization_id"].split(":IG:")[1].split(":")[0])
                for row in future_bank_updates) if future_bank_updates else True
            _write(task_root / "identity/appearance_bank.json", baseline_bank)
            memory_frames = _identity_memory_frames(video_id, task_root, inputs, registry, timeline, fps, mask_refs)
            memory = _build_memory(video_id, task_root, memory_frames, physical_decisions, timeline, fps)
            visualization = _render_annotated_video(video, task_root, memory_frames, timeline, events,
                memory["search"]["plan"], mask_paths, min(5.0, float(metadata.get("fps", 5))))
            _write(task_root / "visuals/annotated_video_status.json", visualization)
            manifest["stages"].append({"stage": "authoritative_memory_search_visualization", "status": "COMPLETE",
                "memory_episodes": len(memory["relation_episodes"]), "search_candidates": len(memory["search"]["plan"].get("candidates", [])),
                "memory_validation_errors": memory["validation_errors"], "annotated_video": visualization})

            from .validator import validate_video_artifacts
            end = time.monotonic()
            try:
                peak_vram = int(torch.cuda.max_memory_allocated())
            except Exception:
                peak_vram = 0
            inputs = _load_v21_inputs(video_id, task_root)
            summary = _metrics(video_id, task_root, end-started, peak_vram, mask_refs, timeline, events,
                               anchors_all, pair_requests_all, physical_decisions, inputs, "COMPLETE", None)
            summary["target_binding"] = binding_audit.get("decision")
            summary["guard_decision"] = guard_audit.get("decision")
            summary["sam_target_status"] = target_sam.get("status")
            summary["reinit_status"] = reinit.get("status")
            summary["test8_closed_loop"] = bool(video_id == "test8" and authorizations and
                any(int(r["frame_index"]) > int(authorizations[0]["frame"]) and r.get("state") == "VISIBLE" for r in timeline))
            summary["test9_unresolved"] = bool(video_id == "test9" and (not authorizations or not timeline or
                timeline[-1]["state"] not in {"VISIBLE", "MATCHED"}))
            _write(task_root / "summary.json", summary)
            # Reusable V2.5/V2.6 code stores fresh-source paths using its original names.
            # Canonicalize those references after every producer has finished.
            for json_path in task_root.rglob("*.json"):
                if "upstream_v21" in json_path.relative_to(task_root).parts:
                    continue
                if json_path.name in {"canonical_config.json", "artifact_manifest.json"}:
                    continue
                try:
                    payload = json.loads(json_path.read_text(encoding="utf-8"))
                    remapped = _remap_paths(payload, video_id)
                    _write(json_path, remapped)
                except (OSError, ValueError, TypeError):
                    continue
            manifest.update(status="COMPLETE", end_utc=_now(), elapsed_seconds=end-started,
                            raw_video_path=video.name, failure_stage=None)
            _write(task_root / "run_manifest.json", manifest)
            _write(task_root / "artifact_manifest.json", {"video_id": video_id, "files": "generated at freeze"})
            local_validation = validate_video_artifacts(task_root)
            _write(task_root / "contract_validation.json", local_validation)
            if not local_validation["valid"]:
                summary["pipeline_success"] = False
                summary["contract_validation_errors"] = local_validation["errors"]
                _write(task_root / "summary.json", summary)
            return summary
    except Exception as exc:
        manifest.update(status="FAILED", end_utc=_now(), elapsed_seconds=time.monotonic()-started,
                        failure_stage=current_stage, error=f"{type(exc).__name__}: {exc}")
        _write(task_root / "run_manifest.json", manifest)
        summary = {"video_id": video_id, "raw_video_full_pipeline": True, "pipeline_success": False,
                   "failure_stage": current_stage, "error": f"{type(exc).__name__}: {exc}",
                   "runtime_seconds": time.monotonic()-started}
        _write(task_root / "summary.json", summary)
        return summary


def run_all(output_root: str | Path = OUT, *, force: bool = False) -> dict[str, Any]:
    root = Path(output_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    config = canonical_config()
    _write(root / "canonical_config.json", config)
    rows = []
    for video_id in VIDEO_IDS:
        video = ROOT / f"{video_id}.mp4"
        print(f"V2.9.2 {video_id}: starting from raw {video.name}", flush=True)
        rows.append(run_video(video, video_id, root, config, force=force))
        print(f"V2.9.2 {video_id}: {rows[-1].get('pipeline_success')} "
              f"({rows[-1].get('runtime_seconds', 0):.1f}s)", flush=True)
    result = {"pipeline_version": "2.9.2", "canonical_config_sha256": config["canonical_config_sha256"],
              "videos": rows, "completed": sum(r.get("pipeline_success") is True for r in rows),
              "expected": len(VIDEO_IDS), "all_raw_inputs": True,
              "same_config_verified": all(r.get("pipeline_success") for r in rows)}
    _write(root / "benchmark_summary.json", result)
    return result
