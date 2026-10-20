"""Source-verified adapters for recorded and future results, with no GT imports."""
import hashlib
import json
import math
from pathlib import Path
from memory_graph.experiments.three_vlm_contract import validate_raw
from memory_graph.identity.contracts import digest as identity_digest


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def key(*parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:24]


def category(description):
    value = description.strip().lower()
    return "phone" if value in {"phone", "cell phone", "smartphone", "mobile phone"} else value


def observation(identifier, video, source, candidate, label, frames, refs, provenance):
    return dict(observation_id=identifier, video_id=video["video_id"],
        source_video_sha256=video["source_sha256"], source=source,
        source_frame_indices=[f["source_frame_index"] for f in frames],
        source_times_s=[f["native_pts_s"] for f in frames],
        object_category=category(label), object_description=label,
        object_instance_candidate=candidate, authorized_entity_id=None,
        identity_authorization=None, location_candidate=None,
        physical_state="UNKNOWN", physical_state_evidence=None, visibility="UNKNOWN",
        evidence_refs=refs, provenance=provenance)


def checked_frames(window, video, root=None):
    if window["video_id"] != video["video_id"] or window["source_video_sha256"] != video["source_sha256"]:
        raise ValueError("SOURCE_IDENTITY_MISMATCH")
    timeline = video["frame_timeline"]
    frames = window["frames"]
    aliases = [f["alias"] for f in frames]
    if len(set(aliases)) != len(aliases) or not frames:
        raise ValueError("DUPLICATE_OR_EMPTY_ALIASES")
    last_index, last_time = -1, -1
    bounds = window.get("source_frame_interval_closed", [0, len(timeline)-1])
    for frame in frames:
        idx = frame["source_frame_index"]
        if not isinstance(idx, int) or not 0 <= idx < len(timeline) or not bounds[0] <= idx <= bounds[1]:
            raise ValueError("SOURCE_FRAME_OUT_OF_BOUNDS")
        native = timeline[idx]
        t = frame["native_pts_s"]
        if not math.isfinite(t) or t < 0 or t > video["source_duration_s"]:
            raise ValueError("SOURCE_TIME_OUT_OF_BOUNDS")
        if abs(native["source_time_s"] - t) > 1e-9 or idx <= last_index or t <= last_time:
            raise ValueError("NATIVE_PTS_OR_ORDER_MISMATCH")
        if root is not None and sha(Path(root)/frame["path"]) != frame["sha256"]:
            raise ValueError("SOURCE_IMAGE_HASH_MISMATCH")
        last_index, last_time = idx, t
    return {f["alias"]: dict(f) for f in frames}


def adapt_nemotron(raw, window, video, raw_ref, root=None):
    """The same function accepts fresh raw responses with a source manifest."""
    frames = checked_frames(window, video, root)
    validation = validate_raw(raw, list(frames))
    status = validation["raw"]
    # Only schema-parseable content can become inspectable claims. Never repair.
    parsed = status["parsed"] if status["schema_valid"] else None
    normalized = validation.get("normalized_body")
    origin = "RAW"
    if parsed is None and normalized and normalized["validation"]["schema_valid"]:
        parsed = normalized["validation"]["parsed"]
        origin = "EXACT_OUTER_FENCE_NONAUTHORITATIVE"
    run_id = key(video["source_sha256"], window["window_id"], hashlib.sha256(raw.encode()).hexdigest())
    receipt = dict(run_id=run_id, window_id=window["window_id"], video_id=video["video_id"],
        raw_ref=raw_ref, raw_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        raw_output=raw, validation=validation, content_origin=origin,
        response_status=parsed["status"] if parsed else "INVALID_OUTPUT",
        invalid_is_not_no_event=True, frame_alias_mapping=frames)
    observations, hypotheses, by_object = [], [], {}
    if parsed:
        for index, obj in enumerate(parsed["observations"]):
            candidate = "vlm:" + key(video["source_sha256"], run_id, index)
            by_object[obj["object"]] = (candidate, obj["states"])
            for state_index, state in enumerate(obj["states"]):
                f = frames.get(state["frame"])
                obs = observation("obs:"+key(run_id,index,state_index), video, "VLM", candidate,
                    obj["object"], [f] if f else [], [raw_ref, f] if f else [raw_ref],
                    dict(run_id=run_id, window_id=window["window_id"], alias=state["frame"],
                         raw_strict_valid=status["full_valid"], content_origin=origin))
                obs["physical_state"] = state["state"]
                obs["assertion_kind"] = "VLM_CLAIM_NOT_INDEPENDENT_EVIDENCE"
                observations.append(obs)
        for index, event in enumerate(parsed["events"]):
            candidate, states = by_object.get(event["object"], (None, []))
            lookup = {s["frame"]: s["state"] for s in states}
            before = [frames.get(a) for a in event["before_frames"]]
            after = [frames.get(a) for a in event["after_frames"]]
            valid_time = all(before+after) and max(f["native_pts_s"] for f in before) < min(f["native_pts_s"] for f in after)
            hypotheses.append(dict(hypothesis_id="event:"+key(run_id,index), run_id=run_id,
                window_id=window["window_id"], video_id=video["video_id"],
                source_video_sha256=video["source_sha256"], object_category=category(event["object"]),
                object_description=event["object"], object_instance_candidate=candidate,
                type=event["type"], before_refs=before, after_refs=after,
                before_claims=[lookup.get(a,"UNKNOWN") for a in event["before_frames"]],
                after_claims=[lookup.get(a,"UNKNOWN") for a in event["after_frames"]],
                native_interval_s=[max(f["native_pts_s"] for f in before),min(f["native_pts_s"] for f in after)] if valid_time else None,
                interval_meaning="BEFORE_AFTER_EVIDENCE_BOUND_NOT_EVENT_DURATION",
                raw_ref=raw_ref, raw_strict_valid=status["full_valid"],
                validation_errors=status["errors"], temporal_valid=bool(valid_time)))
    return observations, hypotheses, receipt


def verified_guard_ledger(snapshot):
    """Recheck revocation, observation capability, exact scope and evidence digest."""
    aliases = {a["alias_id"]:a for a in snapshot["aliases"] if a["status"]=="CONFIRMED"}
    authorizations = {a["authorization_id"]:a for a in snapshot["authorizations"]}
    valid = {}
    for row in snapshot["final_ledger"]:
        obs = row["observation"]; auth = authorizations.get(row["authorization_id"], {})
        alias = aliases.get(row["alias_id"])
        if not row["active"] or not alias or "AUTHORIZE_OBSERVATION" not in auth.get("capabilities",[]):
            continue
        if (auth.get("alias_id") != row["alias_id"] or
            auth.get("candidate_id") != obs["candidate_id"] or
            obs["observation_id"] not in auth.get("source_observation_ids",[]) or
            auth.get("entity_id") != alias["entity_id"] or
            auth.get("evidence_hash") != identity_digest(obs) or
            row["evidence_hash"] != auth["evidence_hash"]):
            continue
        valid[obs["observation_id"]] = (row,auth)
    return valid


def adapt_cv(tracks, snapshot, video, refs, sam_rows=None):
    """Existing track geometry and guard ledger; geometry is not a physical state."""
    authorized = verified_guard_ledger(snapshot)
    result = []
    for track in tracks:
        candidate = f"cv:{video['source_sha256']}:{track['track_id']}"
        for raw in track["observations"]:
            idx = raw["frame_index"]
            if not 0 <= idx < len(video["frame_timeline"]):
                raise ValueError("CV_FRAME_OUT_OF_BOUNDS")
            native = video["frame_timeline"][idx]
            frame = dict(source_frame_index=idx, native_pts_s=native["source_time_s"])
            oid = f"track:{track['track_id']}@{idx}"
            obs = observation("obs:"+key(refs["tracks"],oid), video, "CV", candidate,
                track["detector_class"],[frame],[dict(path=refs["tracks"],record=oid)],
                dict(provider="YOLO_BYTETRACK", original_timestamp=raw.get("timestamp"),
                     native_timing_remapped=True, source_hashes=refs))
            obs.update(bbox=raw["bbox"], detector_confidence=raw["confidence"], visibility="VISIBLE")
            if oid in authorized:
                row, auth = authorized[oid]
                original = row["observation"]
                if original["frame"] == idx and original["bbox"] == raw["bbox"] and category(original["label"]) == obs["object_category"]:
                    obs["authorized_entity_id"] = f"{video['source_sha256']}::{auth['entity_id']}"
                    obs["identity_authorization"] = dict(auth, source_snapshot=refs["identity"])
                    obs["authorization_validation"] = "VERIFIED_FINAL_LEDGER_REPLAY"
            result.append(obs)
    for i, row in enumerate(sam_rows or []):
        idx=row["frame_index"]
        if not 0 <= idx < len(video["frame_timeline"]):raise ValueError("SAM_FRAME_OUT_OF_BOUNDS")
        frame=dict(source_frame_index=idx,native_pts_s=video["frame_timeline"][idx]["source_time_s"])
        obs=observation("obs:"+key(refs.get("sam"),i),video,"CV",
            f"sam:{video['source_sha256']}:{row.get('object_id','unresolved')}",
            row.get("class_name","unknown"),[frame],[dict(path=refs.get("sam"),record=i)],
            dict(provider="SAM_PROPAGATION", source_hashes=refs))
        obs.update(bbox=row.get("bbox"),visibility="UNKNOWN",mask_reference=row.get("mask_path"),
            segmentation_diagnostics=row.get("diagnostics",{}))
        result.append(obs)
    return result
