from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from memory_graph.v292.contracts import (
    IdentityAuthorization, IdentityEvent, IdentityEventStore, apply_forward_confirmation,
    canonical_anchor_key,
)
from memory_graph.v292.events import (
    CANONICAL_STAGES, cache_reusable, cache_signature, recovery_episodes, stage_sequence,
)
from memory_graph.v292.masks import authorize_trusted_mask, make_mask_reference, validate_mask_reference
from memory_graph.v292.memory import MemoryEventStore, validate_memory_views
from memory_graph.v292.physical import gate as physical_gate
from memory_graph.v292.pipeline import (
    _build_memory, _identity_memory_frames, assert_canonical_output_path, canonical_config,
)
from memory_graph.v292.vlm_pairs import FACT_KEYS, build_pair_request, validate_answer
from memory_graph.v292.validator import HISTORICAL_TOKENS, has_historical_prediction_reference


def _auth(frame=20, candidate="cand-1", video="test1"):
    return IdentityAuthorization(
        authorization_id=f"{video}:IG:{frame}:{candidate}", video_id=video, frame=frame,
        candidate_id=candidate, decision="CONFIRMED_MATCH", appearance_evidence={"score": .8},
        competitor_evidence={"margin": .15}, semantic_compatibility={"cell_phone": True},
        contradiction_check={"checked": True}, mask_quality={"valid": True},
        source_guard_decision="V2.6_IDENTITY_GUARD", provenance=["outputs_v292/test1/identity/reid_audit.json"],
    )


def _pair_rows(anchor_key="test1::E1::A1"):
    rows = []
    for frame in (8, 10, 12):
        rows.append({"frame": frame, "target_authorized": True, "authorization_id": f"auth-{frame}",
            "target_bbox": [10, 10, 20, 20], "anchors": [{"anchor_key": anchor_key,
            "bbox": [25, 10, 40, 30], "visible": True}]})
    return rows


def _physical_candidate(relation="INSIDE", **features):
    base = {"support_frames": 3, "support_seconds": .5, "mask_available": True,
            "distance_change": .08, "containment_trend": .2, "final_containment": .72,
            "visible_area_ratio": .5, "target_disappears_after": True, "post_anchor_without_target": 2,
            "final_distance": .2, "target_motion_px": [8, 6, 2, 1], "velocity_coupling": .9}
    base.update(features)
    roles = {"INSIDE": ["CONTAINER"], "ON": ["SUPPORT"], "BEHIND": ["OCCLUDER"],
             "OCCLUDED_BY": ["OCCLUDER"], "HELD_BY": ["INTERACTION_AGENT"], "NEAR": ["LANDMARK"]}[relation]
    return {"candidate_id": "P1", "event_id": "E1", "candidate_relation": relation,
        "target": "phone_01", "anchor": "test1::E1::A1", "start_frame": 1, "end_frame": 4,
        "semantic_roles": roles, "features": base, "positive_evidence": ["pair geometry"],
        "negative_evidence": [], "missing_evidence": [], "provenance": ["outputs_v292/test1/evidence.json"],
        "identity_authorized": True}


def _grounding():
    return {"grounding_valid": True, "target_id": "phone_01", "anchor_key": "test1::E1::A1",
            "event_id": "E1", "evidence_frames": {"BEFORE": 1, "DURING": 2, "AFTER": 3}}


def _facts(**updates):
    value = {key: "YES" for key in FACT_KEYS}
    value.update({"subject_reference": "phone_01", "anchor_reference": "test1::E1::A1",
                  "event_reference": "E1", "evidence_frames": {"BEFORE": 1, "DURING": 2, "AFTER": 3}})
    value.update(updates)
    return value


# Identity authorization and transitions (8 focused cases)
def test_propagation_resumption_is_not_confirmation():
    store = IdentityEventStore("test1")
    store.append(IdentityEvent("e1", "test1", 1, .1, "PROPAGATION_RESUMED"))
    assert store.timeline()[0]["state"] == "PROPAGATION_RESUMED"
    assert store.registry_projection()["confirmations"] == []


def test_detector_resumption_is_not_confirmation():
    store = IdentityEventStore("test1")
    store.append(IdentityEvent("e1", "test1", 1, .1, "DETECTION_RESUMED"))
    assert store.timeline()[0]["state"] == "DETECTION_RESUMED"


def test_confirmation_without_authorization_is_rejected():
    store = IdentityEventStore("test1")
    with pytest.raises(ValueError, match="authorization"):
        store.append(IdentityEvent("e1", "test1", 10, .5, "IDENTITY_CONFIRMED", "cand"))


def test_trusted_non_target_registry_entity_does_not_require_identity_authorization():
    frames = _identity_memory_frames(
        "test1", Path("."),
        {"metadata": {"sampled_frames": [{"frame_index": 1, "timestamp": 0.1}]}, "tracks": []},
        {"entities": [{"entity_id": "entity-2", "semantic_label": "cup",
                        "observation_history": [{"frame_index": 1, "timestamp": 0.1,
                                                 "bbox": [1, 2, 3, 4], "trusted": True}]}]},
        [{"frame_index": 1, "state": "VISIBLE", "timestamp": 0.1}], 10.0, [],
    )
    assert len(frames[0]["anchors"]) == 1
    assert frames[0]["anchors"][0].identity == "TRUSTED"


def test_memory_builder_reads_canonical_identity_timestamp(tmp_path):
    from memory_graph.v27.models import EntityObservation

    observation = EntityObservation("phone_01", 1, 0.1, [1, 2, 10, 12], "cell phone", "TRUSTED",
                                    "sam", "target_full", "test1:phone_01:1")
    frames = [{"frame": 1, "time": 0.1, "upstream_state": "VISIBLE_TRUSTED",
               "observations": [observation], "anchors": []}]
    timeline = [{"frame_index": 1, "timestamp": 0.1, "state": "VISIBLE", "provenance": ["identity audit"]}]
    result = _build_memory("test1", tmp_path, frames, [], timeline, 10.0)
    assert result["lifetime_memory"]["target"]["last_seen_time"] == 0.1


def test_identity_guard_authorization_projects_matched():
    store = IdentityEventStore("test1")
    auth = _auth()
    store.add_authorization(auth)
    store.append(IdentityEvent("e1", "test1", auth.frame, 1., "IDENTITY_CONFIRMED", auth.candidate_id,
                               auth.authorization_id, ("guard audit",)))
    assert store.timeline()[0]["state"] == "MATCHED"
    assert store.timeline()[0]["authorization_id"] == auth.authorization_id


def test_authorization_from_wrong_guard_is_invalid():
    auth = _auth()
    forged = IdentityAuthorization(**{**auth.__dict__, "source_guard_decision": "SAM_PROPAGATION"})
    assert not forged.valid


def test_confirmation_cannot_cross_video_or_frame():
    store = IdentityEventStore("test1")
    auth = _auth(frame=20)
    store.add_authorization(auth)
    with pytest.raises(ValueError, match="exact"):
        store.append(IdentityEvent("e1", "test1", 21, 1., "IDENTITY_CONFIRMED", auth.candidate_id,
                                   auth.authorization_id, ("audit",)))


def test_forward_confirmation_never_changes_pre_loss_rows():
    auth = _auth(frame=20)
    rows = [{"frame_index": i, "state": "UNOBSERVED"} for i in (10, 20, 30)]
    result = apply_forward_confirmation(rows, auth, {30})
    assert result[0]["state"] == "UNOBSERVED"
    assert result[1]["state"] == "MATCHED"
    assert result[2]["state"] == "VISIBLE"


def test_second_loss_creates_a_new_episode():
    rows = [{"frame_index": 0, "state": "VISIBLE"}, {"frame_index": 10, "state": "UNOBSERVED"},
            {"frame_index": 20, "state": "MATCHED"}, {"frame_index": 30, "state": "VISIBLE"},
            {"frame_index": 40, "state": "UNOBSERVED"}]
    episodes = recovery_episodes(rows, [{"frame": 20, "decision": "CONFIRMED_MATCH",
                    "source_guard_decision": "V2.6_IDENTITY_GUARD", "authorization_id": "a"}], 10)
    assert [e["loss_episode_id"] for e in episodes] == ["LOSS01", "LOSS02"]
    assert episodes[0]["status"] == "CLOSED" and episodes[1]["status"] == "OPEN"


# Temporal memory and cache contracts (8 cases)
def test_nonzero_frame_zero_timestamp_is_rejected():
    store = MemoryEventStore("test1", 10)
    with pytest.raises(ValueError, match="timestamp"):
        store.add_observation({"observation_id": "o", "entity_id": "phone_01", "frame": 5,
                               "time": 0, "status": "TRUSTED", "provenance": ["source"]})


def test_actual_frame_time_is_derived_from_fps():
    store = MemoryEventStore("test1", 10)
    store.add_observation({"observation_id": "o", "entity_id": "phone_01", "frame": 30,
                           "status": "TRUSTED", "provenance": ["source"]})
    assert store.observations[0]["time"] == 3


def test_nonzero_memory_event_zero_time_is_rejected():
    store = MemoryEventStore("test1", 10)
    with pytest.raises(ValueError):
        store.add_event({"event_id": "e", "event_type": "PHYSICAL_RELATION", "frame": 30,
                         "time": 0, "provenance": ["source"]})


def test_untrusted_candidate_does_not_become_last_trusted():
    store = MemoryEventStore("test1", 10)
    store.add_event({"event_id": "r", "event_type": "PHYSICAL_RELATION", "frame": 10,
        "start_frame": 8, "end_frame": 10, "time": 1, "end_time": 1, "status": "CANDIDATE",
        "decision": "CANDIDATE", "trusted": False, "provenance": ["evidence"]})
    view = store.derive([])
    assert view["relation_episodes"][0]["status"] == "CANDIDATE"


def test_older_trusted_relation_becomes_stale():
    store = MemoryEventStore("test1", 10)
    for event_id, frame in (("old", 10), ("new", 20)):
        store.add_event({"event_id": event_id, "event_type": "IMAGE_CONTEXT_RELATION", "frame": frame,
            "start_frame": frame, "end_frame": frame, "time": frame/10, "end_time": frame/10,
            "trusted": True, "provenance": [event_id]})
    view = store.derive([])
    assert [e["status"] for e in view["relation_episodes"]] == ["STALE", "LAST_TRUSTED"]


def test_temporal_lifetime_and_search_views_round_trip_one_store():
    store = MemoryEventStore("test1", 10)
    store.add_event({"event_id": "r", "event_type": "IMAGE_CONTEXT_RELATION", "frame": 20,
        "start_frame": 10, "end_frame": 20, "time": 2, "start_time": 1, "end_time": 2,
        "trusted": True, "provenance": ["source"]})
    bundle = store.derive([])
    assert validate_memory_views(bundle) == []
    assert bundle["temporal_memory"]["episodes"] == bundle["lifetime_memory"]["episodes"]
    assert bundle["search"]["source_event_ids"] == ["r"]


def test_cache_requires_requested_end_coverage():
    assert not cache_reusable({"sampling": {"start_frame": 10, "end_frame": 20}, "signature": "s"},
                              requested_start_frame=10, requested_end_frame=21, signature="s")


def test_cache_requires_requested_start_coverage():
    assert not cache_reusable({"sampling": {"start_frame": 11, "end_frame": 30}, "signature": "s"},
                              requested_start_frame=10, requested_end_frame=20, signature="s")


def test_cache_signature_change_rejects_reuse():
    assert not cache_reusable({"sampling": {"start_frame": 0, "end_frame": 100}, "signature": "old"},
                              requested_start_frame=1, requested_end_frame=90, signature="new")


def test_cache_signature_binds_video_and_models():
    kwargs = dict(video_sha256="raw", start_frame=1, end_frame=20, pipeline_version="2.9.2",
        code_config_sha256="cfg", yolo_model="yolo", yolo_config={"imgsz": 960},
        sam_model="sam2.1", sam_config={"step": 6}, sampling_policy={"fps": 15})
    first = cache_signature(**kwargs)
    kwargs["sam_model"] = "sam3"
    assert first != cache_signature(**kwargs)


# Mask provenance and shared authorization (8 cases)
def _mask_ref(tmp_path, **updates):
    image = np.zeros((8, 9), np.uint8); image[2:5, 3:7] = 255
    path = tmp_path / "mask.png"
    assert cv2.imwrite(str(path), image)
    auth = authorize_trusted_mask(identity_state="VISIBLE", continuity_ok=True, drift_ok=True,
                                  mask_quality_ok=True, authorization_id="bind")
    ref = make_mask_reference(video_id="test1", frame=10, object_id="phone_01", event_id="E1",
                              artifact_path=path, authorization=auth, provenance="source")
    ref.update(updates)
    return ref


def test_mask_reference_requires_existing_decodable_file(tmp_path):
    ref = _mask_ref(tmp_path)
    assert validate_mask_reference(ref, video_id="test1", frame=10, object_id="phone_01", event_id="E1")["valid"]


def test_mask_reference_missing_file_rejected(tmp_path):
    ref = _mask_ref(tmp_path); ref["artifact_path"] = tmp_path / "missing.png"
    check = validate_mask_reference(ref, video_id="test1", frame=10, object_id="phone_01", event_id="E1")
    assert not check["valid"] and "artifact_missing" in check["mismatches"]


def test_mask_reference_decode_failure_rejected(tmp_path):
    path = tmp_path / "broken.png"; path.write_text("not an image")
    ref = _mask_ref(tmp_path); ref["artifact_path"] = path
    assert "artifact_decode_failed" in validate_mask_reference(ref, video_id="test1", frame=10,
        object_id="phone_01", event_id="E1")["mismatches"]


@pytest.mark.parametrize("key,value", [("video_id", "test2"), ("frame", 11),
    ("object_id", "other"), ("event_id", "E2")])
def test_mask_provenance_mismatch_rejected(tmp_path, key, value):
    ref = _mask_ref(tmp_path); ref[key] = value
    check = validate_mask_reference(ref, video_id="test1", frame=10, object_id="phone_01", event_id="E1")
    assert not check["valid"]


def test_mask_path_must_remain_inside_video_output(tmp_path):
    ref = _mask_ref(tmp_path)
    assert not validate_mask_reference(ref, video_id="test1", frame=10, object_id="phone_01",
        event_id="E1", root=tmp_path / "other")["valid"]


@pytest.mark.parametrize("state,expected", [("VISIBLE", True), ("MATCHED", True), ("UNOBSERVED", False),
                                             ("PROVISIONAL", False), ("PROPAGATION_RESUMED", False)])
def test_one_mask_authorizer_is_identity_state_sensitive(state, expected):
    result = authorize_trusted_mask(identity_state=state, continuity_ok=True, drift_ok=True,
                                    mask_quality_ok=True, authorization_id="a")
    assert result["trusted"] is expected


def test_mask_continuity_break_requires_reacquisition_authorization():
    result = authorize_trusted_mask(identity_state="VISIBLE", continuity_ok=False, drift_ok=True,
        mask_quality_ok=True, continuity_break=True, reacquisition_authorized=False)
    assert not result["trusted"]


# Anchor namespace and VLM grounding (9 cases)
def test_anchor_key_namespaces_video_event_and_local_id():
    assert canonical_anchor_key("test1", "E1", "event_anchor_001") == "test1::E1::event_anchor_001"


def test_same_local_anchor_id_in_distinct_events_does_not_collide():
    a = canonical_anchor_key("test1", "E1", "event_anchor_001")
    b = canonical_anchor_key("test1", "E2", "event_anchor_001")
    assert a != b


def test_pair_request_contains_one_target_and_one_anchor():
    key = "test1::E1::A1"
    request = build_pair_request(video_id="test1", event={"event_id": "E1", "peak_frame": 10,
        "start_frame": 5, "end_frame": 15, "during_tolerance_frames": 0}, target_id="phone_01", anchor={"anchor_key": key},
        rows=_pair_rows(key))
    assert request["status"] == "READY"
    assert request["target_id"] == "phone_01" and request["anchor_key"] == key
    assert len(request["evidence"]) == 3


def test_missing_target_evidence_returns_unavailable():
    rows = _pair_rows(); rows = [{**r, "target_authorized": False} for r in rows]
    request = build_pair_request(video_id="test1", event={"event_id": "E1", "peak_frame": 10,
        "start_frame": 5, "end_frame": 15, "during_tolerance_frames": 0}, target_id="phone_01", anchor={"anchor_key": "test1::E1::A1"}, rows=rows)
    assert request["status"] == "EVIDENCE_UNAVAILABLE"


def test_missing_queried_anchor_evidence_returns_unavailable():
    rows = [{**r, "anchors": []} for r in _pair_rows()]
    request = build_pair_request(video_id="test1", event={"event_id": "E1", "peak_frame": 10,
        "start_frame": 5, "end_frame": 15, "during_tolerance_frames": 0}, target_id="phone_01", anchor={"anchor_key": "test1::E1::A1"}, rows=rows)
    assert request["status"] == "EVIDENCE_UNAVAILABLE"


def test_wrong_subject_valid_observable_json_is_rejected():
    request = build_pair_request(video_id="test1", event={"event_id": "E1", "peak_frame": 10,
        "start_frame": 5, "end_frame": 15, "during_tolerance_frames": 0}, target_id="phone_01", anchor={"anchor_key": "test1::E1::A1"}, rows=_pair_rows())
    wrong = _facts(subject_reference="someone_else", evidence_frames={p: request["evidence"][p]["frame"] for p in request["evidence"]})
    assert validate_answer(request, wrong)["status"] == "UNUSABLE_GROUNDING"


def test_wrong_anchor_valid_observable_json_is_rejected():
    request = build_pair_request(video_id="test1", event={"event_id": "E1", "peak_frame": 10,
        "start_frame": 5, "end_frame": 15, "during_tolerance_frames": 0}, target_id="phone_01", anchor={"anchor_key": "test1::E1::A1"}, rows=_pair_rows())
    wrong = _facts(anchor_reference="test1::E1::A2", evidence_frames={p: request["evidence"][p]["frame"] for p in request["evidence"]})
    assert validate_answer(request, wrong)["status"] == "UNUSABLE_GROUNDING"


def test_answer_citing_other_frames_is_rejected():
    request = build_pair_request(video_id="test1", event={"event_id": "E1", "peak_frame": 10,
        "start_frame": 5, "end_frame": 15, "during_tolerance_frames": 0}, target_id="phone_01", anchor={"anchor_key": "test1::E1::A1"}, rows=_pair_rows())
    wrong = _facts(evidence_frames={"BEFORE": 100, "DURING": 101, "AFTER": 102})
    assert validate_answer(request, wrong)["status"] == "UNUSABLE_GROUNDING"


def test_usable_vlm_facts_must_not_directly_choose_relation():
    # No relation key is accepted by the VLM observable schema.
    result = physical_gate(_physical_candidate("INSIDE"), _facts(relation="INSIDE"), _grounding())
    assert result["decision"] != "PROMOTED"


# Relation gate outcome reachability (4 cases)
def test_v29_relation_gate_reaches_promoted_for_strong_ordered_evidence():
    rows = [{"frame": 1, "target_authorized": True, "target_bbox": [0, 0, 2, 2], "anchors": [{"anchor_key": "test1::E1::A1", "bbox": [5, 5, 10, 10]}]},
            {"frame": 2, "target_authorized": True, "target_bbox": [5, 5, 7, 7], "contact": True, "anchors": [{"anchor_key": "test1::E1::A1", "bbox": [5, 5, 10, 10]}]},
            {"frame": 3, "target_authorized": True, "target_bbox": [6, 6, 8, 8], "anchors": [{"anchor_key": "test1::E1::A1", "bbox": [5, 5, 10, 10]}]}]
    candidate = _physical_candidate("INSIDE"); candidate["rows"] = rows
    result = physical_gate(candidate, _facts(), _grounding())
    assert result["decision"] == "PROMOTED"


def test_insufficient_temporal_evidence_reaches_uncertain():
    result = physical_gate(_physical_candidate("INSIDE", support_frames=2, support_seconds=.1), None, None)
    assert result["decision"] == "UNCERTAIN"


def test_relation_counterevidence_reaches_rejected():
    facts = _facts(target_contacts_or_crosses_anchor_boundary="NO")
    result = physical_gate(_physical_candidate("INSIDE"), facts, _grounding())
    assert result["decision"] == "REJECTED"


def test_proximity_candidate_reaches_candidate_without_promotion():
    result = physical_gate(_physical_candidate("NEAR"), None, None)
    assert result["decision"] == "CANDIDATE"


# Recovery, canonical runner path, and configuration controls (8 cases)
def test_canonical_stage_sequence_same_for_all_nine_videos():
    sequences = stage_sequence([f"test{i}" for i in range(1, 10)])
    assert len(sequences) == 9 and len({value for value in sequences.values()}) == 1


def test_pipeline_stage_contract_includes_all_major_phases():
    required = {"target_binding", "candidate_admission", "identity_guard", "dense_reinspection",
                "pair_grounded_vlm", "physical_gate", "authoritative_memory", "search"}
    assert required.issubset(set(CANONICAL_STAGES))


def test_runner_output_path_is_confined_to_v292(tmp_path):
    root = Path(__file__).resolve().parents[1]
    allowed = root / "outputs_v292"
    assert assert_canonical_output_path("test1", allowed) == allowed.resolve()
    with pytest.raises(ValueError, match="outputs_v292"):
        assert_canonical_output_path("test1", tmp_path)


def test_runner_rejects_unknown_video_id():
    with pytest.raises(ValueError, match="video id"):
        assert_canonical_output_path("test10", Path(__file__).resolve().parents[1] / "outputs_v292")


def test_run_context_routes_reusable_modules_and_restores_them():
    from memory_graph.v25rerun import adapter, pipeline as v25_pipeline, reid, sam_route
    from memory_graph.v26 import pipeline as v26_pipeline
    from memory_graph.v292.pipeline import RunContext
    saved = (adapter.OUT, v25_pipeline.OUT, reid.OUT, sam_route.OUT, v26_pipeline.BASE, v26_pipeline.OUT)
    target = Path(__file__).resolve().parents[1] / "outputs_v292"
    with RunContext(target):
        assert adapter.OUT == target.resolve()
        assert v25_pipeline.OUT == target.resolve()
        assert reid.OUT == target.resolve()
        assert sam_route.OUT == target.resolve()
        assert v26_pipeline.BASE == target.resolve() and v26_pipeline.OUT == target.resolve()
    assert (adapter.OUT, v25_pipeline.OUT, reid.OUT, sam_route.OUT, v26_pipeline.BASE, v26_pipeline.OUT) == saved


@pytest.mark.parametrize("video_id", [f"test{i}" for i in range(1, 10)])
def test_all_nine_raw_inputs_exist(video_id):
    root = Path(__file__).resolve().parents[1]
    assert (root / f"{video_id}.mp4").is_file()


def test_canonical_config_fixes_all_shared_policy_versions():
    config = canonical_config()
    assert config["canonical_config_sha256"]
    assert config["policy_versions"]["identity"] == "V292_IDENTITY_AUTH_1"
    assert config["policy_versions"]["physical_gate"] == "V29_RELATION_GATE_1"


def test_historical_output_paths_are_marked_as_forbidden_inference_sources():
    assert "outputs_v291" in HISTORICAL_TOKENS and "outputs_v25_rerun" in HISTORICAL_TOKENS


def test_historical_path_detector_uses_exact_output_directory_token():
    assert has_historical_prediction_reference("outputs_v29/test1/prediction.json")
    assert has_historical_prediction_reference("C:/runs/outputs_v25_rerun/test1/file.json")
    assert not has_historical_prediction_reference("outputs_v292/test1/memory.json")


def test_timeline_has_no_unauthorized_matched_projection():
    store = IdentityEventStore("test1")
    store.append(IdentityEvent("e", "test1", 5, .5, "AMBIGUOUS"))
    assert all(row["state"] != "MATCHED" for row in store.timeline())


def test_mask_provenance_records_explicit_decision():
    auth = authorize_trusted_mask(identity_state="VISIBLE", continuity_ok=True, drift_ok=True,
                                  mask_quality_ok=True, authorization_id="bind")
    ref = make_mask_reference(video_id="test1", frame=1, object_id="phone_01", event_id="E1",
                              artifact_path="mask.png", authorization=auth, provenance="source")
    assert ref["trusted"] is True and ref["authorization"]["decision"] == "AUTHORIZED"
