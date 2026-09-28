"""V2.9 safety and causal-evidence regressions; no model inference in tests."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from memory_graph.v27.pipeline import ROOT
from memory_graph.v28.pipeline import verify_freeze as verify_v28
from memory_graph.v28.search_planner import find
from memory_graph.v29.mask_evidence import authorize_mask
from memory_graph.v29.placement_events import detect_events
from memory_graph.v29.dense_reinspection import frame_numbers
from memory_graph.v29.physical_gate import decide
from memory_graph.v29.vlm_relation_verifier import _parse


OBS = {"frame_index": 12, "timestamp": .4, "object_id": "phone_target",
       "bbox": [10, 10, 20, 20], "mask_area": 80, "center": [15, 15],
       "diagnostics": {"possible_mask_drift": False}}
AUDIT = {"decision": "MATCH", "entity_id": "phone_01"}
IDENTITY = {"accepted_sam_target": True, "state": "VISIBLE_PROPAGATED"}
RLE = {"shape": [30, 30], "starts": [310], "lengths": [80]}
REF = "outputs_v25_rerun/test3/sam/sam_continuity_log.json#12:phone_target"


@pytest.mark.parametrize("change,expected", [
    ({}, None),
    ({"rle": None}, "MASK_NOT_GENERATED"),
    ({"drift": True}, "MASK_REJECTED_DRIFT"),
    ({"state": "PROVISIONAL"}, "IDENTITY_NOT_AUTHORIZED_AT_FRAME"),
    ({"state": "AMBIGUOUS"}, "IDENTITY_NOT_AUTHORIZED_AT_FRAME"),
    ({"decision": "CONFLICT"}, "MASK_REJECTED_BY_FUSION"),
    ({"entity": "candidate_phone_01"}, "IDENTITY_NOT_AUTHORIZED"),
])
def test_mask_authorization_cases(change, expected):
    obs, audit, identity = deepcopy(OBS), deepcopy(AUDIT), deepcopy(IDENTITY)
    obs["diagnostics"]["possible_mask_drift"] = change.get("drift", False)
    audit["decision"] = change.get("decision", audit["decision"])
    audit["entity_id"] = change.get("entity", audit["entity_id"])
    identity["state"] = change.get("state", identity["state"])
    row = authorize_mask(obs, audit, identity, change.get("rle", RLE), REF)
    assert row["trusted"] is (expected is None)
    assert (row["entity_id"] == "phone_01") is (expected is None)
    if expected:
        assert expected in row["rejection_reason"]


def _frame(number, box=None, anchor=True):
    target = [SimpleNamespace(entity_id="phone_01", trusted=True, bbox=box,
                              observation_id=f"trusted:{number}")] if box else []
    anchors = [SimpleNamespace(entity_id="entity_0001", label="box", bbox=[45, 40, 72, 70],
                               observation_id=f"anchor:{number}")] if anchor else []
    return {"frame": number, "time": number/6, "observations": target, "anchors": anchors}


def _event_frames(anchor=True):
    return [_frame(0, [1, 40, 11, 50], anchor), _frame(6, [22, 40, 32, 50], anchor),
            _frame(12, [43, 40, 53, 50], anchor), _frame(18, None, anchor),
            _frame(24, None, anchor)]


def test_synthetic_approach_overlap_disappearance_detected():
    events = detect_events(_event_frames(), [], (100, 100), 6)
    assert len(events) == 1 and events[0]["cues"]["anchor_approach"]
    assert events[0]["cues"]["target_disappearance"]


def test_disappearance_alone_is_not_placement():
    assert detect_events(_event_frames(anchor=False), [], (100, 100), 6) == []


def test_window_has_before_during_after():
    event = detect_events(_event_frames(), [], (100, 100), 6)[0]
    assert event["start_frame"] < event["peak_frame"] < event["end_frame"]
    assert event["candidate_anchors"][0]["entity_id"] == "entity_0001"


@pytest.mark.parametrize("native,expected_step", [(30, 2), (24, 2), (12, 1)])
def test_dense_frame_sampling_is_event_bounded(native, expected_step):
    selected = frame_numbers({"start_frame": 120, "end_frame": 150}, native, native)
    assert selected[0] == 120 and selected[-1] <= 150
    assert all(b-a == expected_step for a, b in zip(selected, selected[1:]))
    assert len(selected) < 32  # never full-video processing


def _candidate(relation, roles, **changes):
    features = {"support_frames": 5, "support_seconds": .5, "mask_available": True,
                "distance_change": .1, "containment_trend": .3, "final_containment": .8,
                "visible_area_ratio": .5, "target_disappears_after": True,
                "post_anchor_without_target": 3, "target_motion_px": [20, 12, 1, 1],
                "velocity_coupling": .9, "final_distance": .1}
    features.update(changes)
    return {"candidate_id": "PRC0001", "event_id": "PE0001", "candidate_relation": relation,
            "target": "phone_01", "anchor": "entity_0001", "start_frame": 0, "end_frame": 30,
            "semantic_roles": roles, "features": features, "positive_evidence": [],
            "negative_evidence": [], "missing_evidence": [], "provenance": []}


def _good_vlm(relation):
    return {"status": "VALID", "structured_output": {"relation": relation, "confidence": .95,
            "temporal_evidence": "Target approaches and crosses the anchor boundary over several frames.",
            "visual_evidence": "The target mask progressively overlaps the anchor while remaining distinct.",
            "counterevidence": "No conflicting object is seen.", "uncertainty": "low"}}


@pytest.mark.parametrize("relation,roles,changes", [
    ("INSIDE", ["CONTAINER"], {}),
    ("OCCLUDED_BY", ["OCCLUDER"], {}),
    ("BEHIND", ["OCCLUDER"], {}),
    ("HELD_BY", ["INTERACTION_AGENT"], {}),
    ("ON", ["SUPPORT"], {"visible_area_ratio": .9}),
])
def test_relation_specific_positive_gates(relation, roles, changes):
    assert decide(_candidate(relation, roles, **changes), _good_vlm(relation))["decision"] == "PROMOTED"


@pytest.mark.parametrize("relation,roles,changes", [
    ("INSIDE", ["CONTAINER"], {"distance_change": 0}),
    ("INSIDE", ["CONTAINER"], {"containment_trend": 0}),
    ("INSIDE", ["CONTAINER"], {"target_disappears_after": False}),
    ("ON", ["SUPPORT"], {"visible_area_ratio": .9, "target_motion_px": [20, 12, 10, 10]}),
    ("OCCLUDED_BY", ["OCCLUDER"], {"visible_area_ratio": 1}),
    ("OCCLUDED_BY", ["OCCLUDER"], {"target_disappears_after": False}),
    ("BEHIND", ["OCCLUDER"], {"distance_change": 0}),
    ("HELD_BY", ["INTERACTION_AGENT"], {"velocity_coupling": 0}),
    ("INSIDE", ["OCCLUDER"], {}),
])
def test_relation_specific_negative_gates(relation, roles, changes):
    assert decide(_candidate(relation, roles, **changes), _good_vlm(relation))["decision"] != "PROMOTED"


def test_image_overlap_alone_cannot_promote_inside():
    row = decide(_candidate("INSIDE", ["CONTAINER"], distance_change=0,
                            containment_trend=0, visible_area_ratio=1), _good_vlm("INSIDE"))
    assert row["decision"] != "PROMOTED"


def test_mask_containment_without_transition_cannot_promote():
    row = decide(_candidate("INSIDE", ["CONTAINER"], distance_change=0,
                            containment_trend=0), _good_vlm("INSIDE"))
    assert row["decision"] != "PROMOTED"


def test_detector_miss_alone_is_not_occlusion():
    row = decide(_candidate("OCCLUDED_BY", ["OCCLUDER"], containment_trend=0,
                            visible_area_ratio=1), _good_vlm("OCCLUDED_BY"))
    assert row["decision"] != "PROMOTED"


def test_vlm_uncertain_cannot_promote():
    vlm = _good_vlm("BEHIND")
    vlm["structured_output"]["uncertainty"] = "UNCERTAIN"
    assert decide(_candidate("BEHIND", ["OCCLUDER"]), vlm)["decision"] != "PROMOTED"


def test_vlm_thin_rationale_cannot_promote():
    vlm = _good_vlm("BEHIND")
    vlm["structured_output"]["temporal_evidence"] = "['BEFORE']"
    assert decide(_candidate("BEHIND", ["OCCLUDER"]), vlm)["vlm_gate"]["support"] is False


def test_near_is_visibly_unconfirmed():
    row = decide(_candidate("NEAR", ["OCCLUDER"]), _good_vlm("NEAR"))
    assert row["decision"] == "CANDIDATE"


@pytest.mark.parametrize("raw,valid", [
    ('{"relation":"ON","confidence":0.9}', True),
    ('{"relation":"TELEPORTED","confidence":0.9}', False),
    ('{"relation":"ON","confidence":1.5}', False),
])
def test_vlm_structured_output_validation(raw, valid):
    if valid:
        assert _parse(raw)["relation"] == "ON"
    else:
        with pytest.raises(ValueError):
            _parse(raw)


def test_promoted_search_outranks_candidate():
    memory = {"target": {"entity_id": "phone_01", "state": "UNOBSERVED", "last_seen_time": 1.0},
              "entities": [{"entity_id": "phone_01", "raw_label": "cell phone", "semantic_roles": ["TARGET"]},
                           {"entity_id": "a", "raw_label": "box", "semantic_roles": ["CONTAINER"]},
                           {"entity_id": "b", "raw_label": "chair", "semantic_roles": ["OCCLUDER"]}],
              "last_trusted_local_subgraph": {"edges": []},
              "episodes": [{"episode_id": "E1", "object": "b", "subject": "phone_01", "relation": "BEHIND",
                            "kind": "PHYSICAL", "decision": "CANDIDATE", "status": "LAST_TRUSTED",
                            "last_confirmed_time": 2.0, "source": [], "source_snapshots": []},
                           {"episode_id": "E2", "object": "a", "subject": "phone_01", "relation": "INSIDE",
                            "kind": "PHYSICAL", "decision": "PROMOTED", "status": "LAST_TRUSTED",
                            "last_confirmed_time": 1.0, "source": [], "source_snapshots": []}]}
    plan = find(memory)
    assert plan["candidates"][0]["search_anchor"] == "a"
    assert plan["candidates"][0]["confirmed"] is True
    assert plan["candidates"][1]["confirmed"] is False


def test_test7_provisional_does_not_enter_physical_memory():
    decisions = json.loads((ROOT/"outputs_v29/test7/physical_relation_decisions.json").read_text())
    assert not any(d["decision"] == "PROMOTED" for d in decisions)


def test_test8_multiple_phones_do_not_force_identity_merge():
    rows = json.loads((ROOT/"outputs_v29/test8/dense_windows/PE0001/dense_observations.json").read_text())["rows"]
    assert all(c["entity_id"] is None for row in rows for c in row["phone_candidates"])
    assert not any(d["decision"] == "PROMOTED" for d in
                   json.loads((ROOT/"outputs_v29/test8/physical_relation_decisions.json").read_text()))


def test_test9_has_first_failure_category():
    report = json.loads((ROOT/"outputs_v29/test9/test9_failure_timeline.json").read_text())
    assert report["first_failure_point"]["category"] in {
        "DETECTION_FAILURE", "SAM_CONTINUITY_FAILURE", "LOCAL_TRACK_FAILURE",
        "CANDIDATE_ADMISSION_FAILURE", "IDENTITY_AUTHORIZATION_FAILURE",
        "ANCHOR_DETECTION_FAILURE", "NO_COVISIBILITY", "PLACEMENT_EVENT_NOT_DETECTED"}
    assert report["first_failure_point"]["frame"] > report["last_stable_trusted_mask_frame"]


def test_v28_predictions_remain_frozen():
    verify_v28()


def test_v29_inference_never_reads_reference_labels():
    source = "\n".join(p.read_text(encoding="utf-8") for p in
                       (ROOT/"src/memory_graph/v29").glob("*.py"))
    assert "ground_truth" not in source and "gt_labels" not in source


def test_vlm_only_scoped_to_eligible_candidates():
    for number in range(3, 10):
        folder = ROOT/f"outputs_v29/test{number}"
        candidates = json.loads((folder/"physical_relation_candidates.json").read_text())
        calls = json.loads((folder/"vlm_relation_verification.json").read_text())
        eligible = {c["candidate_id"] for c in candidates if c["vlm_verification_required"]}
        called = {cid for call in calls for cid in call["candidate_ids"]}
        assert called == eligible
