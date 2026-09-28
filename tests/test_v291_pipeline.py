import json
import re
from pathlib import Path

from memory_graph.v291.anchors import recover_anchors
from memory_graph.v291.events import detect_multi_events
from memory_graph.v291.observable_vlm import FACT_KEYS, OBSERVABLE_PROMPT, parse_observable
from memory_graph.v291.physical import gate
from memory_graph.v291.rediscovery import propose_rediscovery


def _facts(**overrides):
    value = {key: "NO" for key in FACT_KEYS}
    value.update(overrides)
    return value


def test_unknown_event_local_anchor_is_retained_without_global_identity():
    event = {"event_id": "E1"}
    rows = [{"frame": f, "anchors": [{"label": "mystery object", "bbox": [100 + f, 100, 200 + f, 200],
                                        "entity_id": None, "source": None}]}
            for f in (1, 2, 3)]
    anchors = recover_anchors(event, {"rows": rows}, frame_size=(640, 480))["anchors"]
    assert len(anchors) == 1
    assert anchors[0]["scope"] == "EVENT_LOCAL_ANCHOR"
    assert anchors[0]["semantic_role"] == ["UNKNOWN_LANDMARK"]
    assert anchors[0]["persistent_entity_id"] is None
    assert not anchors[0]["trusted_for_physical_reasoning"]


def test_container_role_assignment_is_video_independent():
    rows = [{"frame": f, "anchors": [{"label": "box", "bbox": [100, 100, 200, 200],
                                      "entity_id": None}]}
            for f in (1, 2, 3)]
    result = recover_anchors({"event_id": "E"}, {"rows": rows}, frame_size=(640, 480))
    assert result["anchors"][0]["semantic_role"] == ["CONTAINER"]
    assert result["anchors"][0]["persistent_entity_id"] is None


def test_existing_anchor_remains_explicit_persistent_entity():
    rows = [{"frame": 1, "anchors": [{"label": "chair", "bbox": [1, 2, 8, 9], "entity_id": "entity_1"}]}]
    item = recover_anchors({"event_id": "E"}, {"rows": rows})["anchors"][0]
    assert item["persistent_entity_id"] == "entity_1"
    assert item["source"] == "EXISTING_ENTITY"


def test_reconfirm_and_loss_are_both_detected_and_later_event_survives_priority():
    timeline = [{"frame_index": 0, "state": "VISIBLE_TRUSTED"},
                {"frame_index": 30, "state": "UNOBSERVED"},
                {"frame_index": 60, "state": "MATCHED"},
                {"frame_index": 90, "state": "UNOBSERVED"}]
    candidates = [{"frame_index": 60, "reid_decision": "CONFIRMED_MATCH", "candidate_id": "c1"}]
    events = detect_multi_events("test8", timeline, candidates, [], 30, 100, max_events=3)
    kinds = {e["event_type"] for e in events}
    assert "LOSS_EVENT" in kinds
    assert "RECONFIRM_EVENT" in kinds
    assert "SECOND_LOSS_EVENT" in kinds
    assert next(e for e in events if e["event_type"] == "RECONFIRM_EVENT")["peak_frame"] == 60


def test_confirmed_match_after_unobserved_creates_reconfirm_without_fixed_frame():
    rows = [{"frame_index": 101, "state": "UNOBSERVED"}, {"frame_index": 1001, "state": "MATCHED"}]
    events = detect_multi_events("any_video", rows,
                                 [{"frame_index": 1001, "reid_decision": "CONFIRMED_MATCH"}], [], 30, 1200)
    assert any(e["event_type"] == "RECONFIRM_EVENT" and e["peak_frame"] == 1001 for e in events)


def test_unconfirmed_identity_does_not_create_reconfirm():
    rows = [{"frame_index": 0, "state": "UNOBSERVED"}, {"frame_index": 100, "state": "UNOBSERVED"}]
    events = detect_multi_events("test", rows,
                                 [{"frame_index": 100, "reid_decision": "PROVISIONAL_MATCH"}], [], 30, 120)
    assert all(e["event_type"] != "RECONFIRM_EVENT" for e in events)


def test_putdown_and_occlusion_candidates_are_event_local():
    placement = [{"event_id": "PE1", "peak_frame": 40, "reason": "cues",
                  "cues": {"motion_slowdown": True, "anchor_approach": True,
                           "overlap_increase": True, "visibility_loss": True}}]
    events = detect_multi_events("test", [], [], placement, 30, 100)
    assert {x["event_type"] for x in events} == {"POSSIBLE_PUTDOWN", "OCCLUSION_EVENT"}


def test_rediscovery_proposal_never_aliases_without_guard_confirmation():
    result = propose_rediscovery("test9", {"observations": [{"frame_index": 20, "candidate_id": "c1"}]},
                                 {"phone_timeline": [{"frame_index": 10, "state": "VISIBLE_TRUSTED"}]}, {}, {})
    item = result["candidates"][0]
    assert item["identity_decision"] == "AMBIGUOUS"
    assert item["memory_update_authorized"] is False
    assert result["backward_authorization"] is False


def test_rediscovery_confirmed_only_authorizes_forward_observation():
    result = propose_rediscovery("test", {"observations": [{"frame_index": 20, "candidate_id": "c1",
                                                              "reid_decision": "CONFIRMED_MATCH"}]},
                                 {"phone_timeline": [{"frame_index": 10, "state": "VISIBLE_TRUSTED"}]}, {}, {})
    item = result["candidates"][0]
    assert item["identity_decision"] == "CONFIRMED"
    assert item["memory_update_authorized"] is True
    assert result["last_trusted_frame"] == 10


def test_provisional_rediscovery_does_not_update_memory():
    for decision in ("PROVISIONAL_MATCH", "AMBIGUOUS", "REJECTED"):
        row = {"frame_index": 20, "candidate_id": "c1", "reid_decision": decision}
        result = propose_rediscovery("test", {"observations": [row]},
                                     {"phone_timeline": [{"frame_index": 10, "state": "VISIBLE_TRUSTED"}]}, {}, {})
        assert result["candidates"][0]["memory_update_authorized"] is False


def test_retroactive_candidate_before_last_trusted_frame_is_omitted():
    result = propose_rediscovery("test", {"observations": [{"frame_index": 5, "candidate_id": "old"}]},
                                 {"phone_timeline": [{"frame_index": 10, "state": "VISIBLE_TRUSTED"}]}, {}, {})
    assert result["candidates"] == []


def test_observable_parser_accepts_fact_schema_and_discards_no_relation():
    value = _facts(target_visible_before="YES")
    parsed = parse_observable(json.dumps(value))
    assert parsed["target_visible_before"] == "YES"
    assert "relation" not in parsed


def test_observable_parser_rejects_direct_relation_choice():
    value = _facts()
    value["relation"] = "BEHIND"
    try:
        parse_observable(json.dumps(value))
        assert False, "relation must be rejected"
    except ValueError:
        pass


def test_observable_prompt_asks_only_facts():
    assert "INSIDE" not in OBSERVABLE_PROMPT
    assert "BEHIND" not in OBSERVABLE_PROMPT
    assert re.search(r"\bON\b", OBSERVABLE_PROMPT) is None
    assert "target_contacts_or_crosses_anchor_boundary" in OBSERVABLE_PROMPT


def test_inside_gate_requires_observable_facts_and_never_promotes():
    candidate = {"candidate_relation": "INSIDE", "identity_authorized": True,
                 "positive_evidence": ["geometry", "mask"], "observable_facts": _facts(
                     target_moves_toward_anchor="YES", target_contacts_or_crosses_anchor_boundary="YES",
                     target_visible_area_decreases="YES", anchor_remains_visible="YES", target_visible_after="NO")}
    result = gate(candidate)
    assert result["decision"] == "CANDIDATE"
    assert result["physical_promotion"] is False
    candidate["observable_facts"]["target_contacts_or_crosses_anchor_boundary"] = "NO"
    assert gate(candidate)["decision"] == "UNCERTAIN"


def test_behind_gate_requires_observable_facts_not_vlm_label():
    candidate = {"candidate_relation": "BEHIND", "identity_authorized": True,
                 "positive_evidence": ["geometry", "mask"], "observable_facts": _facts(
                     target_moves_toward_anchor="YES", target_visible_area_decreases="YES",
                     anchor_remains_visible="YES")}
    assert gate(candidate)["decision"] == "CANDIDATE"
    candidate["observable_facts"]["anchor_remains_visible"] = "UNCERTAIN"
    assert gate(candidate)["decision"] == "UNCERTAIN"


def test_non_identity_authorized_candidate_stays_uncertain():
    candidate = {"candidate_relation": "NEAR", "identity_authorized": False,
                 "positive_evidence": ["close"], "observable_facts": _facts()}
    assert gate(candidate)["decision"] == "UNCERTAIN"


def test_raw_task_mapping_uses_actual_test_video_filenames():
    from memory_graph.v291.pipeline import source_video_for_task
    assert source_video_for_task("task1").name == "test1.mp4"
    assert source_video_for_task("task2").name == "test2.mp4"


def test_current_fresh_registry_adapter_keeps_distinct_phone_entities():
    from memory_graph.v291.pipeline import same_class_entity_ids
    registry = {"entities": [{"entity_id": "phone_01", "semantic_label": "cell phone"},
                             {"entity_id": "entity_2", "semantic_label": "cell phone"}]}
    assert same_class_entity_ids(registry, "cell phone") == {"phone_01", "entity_2"}


def test_event_local_identity_keys_are_scoped():
    from memory_graph.v291.pipeline import event_local_entity_id
    assert event_local_entity_id("V291E01", "event_anchor_001") != event_local_entity_id("V291E02", "event_anchor_001")


def test_safe_reconfirmation_adds_image_context_without_physical_relation():
    from memory_graph.v291.pipeline import _add_reconfirm_memory
    lifetime = {"target": {"entity_id": "phone_01", "state": "UNOBSERVED"},
                "entities": [{"entity_id": "phone_01", "raw_label": "cell phone", "semantic_roles": []}],
                "episodes": [], "last_trusted_local_subgraph": {"nodes": [], "edges": []}}
    temporal = {"events": [], "snapshots": []}
    registry = {"entities": [
        {"entity_id": "phone_01", "semantic_label": "cell phone", "observation_history": [
            {"frame_index": 20, "bbox": [100, 100, 140, 140], "trusted": True}]},
        {"entity_id": "entity_2", "semantic_label": "table", "observation_history": [
            {"frame_index": 20, "bbox": [150, 110, 250, 210]}]}]}
    lifetime, temporal = _add_reconfirm_memory("test8", lifetime, temporal,
        [{"event_id": "V291E01", "event_type": "RECONFIRM_EVENT", "peak_frame": 20,
          "source": "candidate_stream", "candidate_ids": ["candidate_1"]}], registry,
        [{"frame_index": 20, "state": "MATCHED"}], (640, 480), 30)
    assert temporal["events"][0]["event_type"] == "V291_RECONFIRM_EVENT"
    assert temporal["events"][0]["details"]["physical_relation_asserted"] is False
    context = [row for row in lifetime["episodes"] if row["kind"] == "IMAGE_CONTEXT"]
    assert context and context[0]["relation"] == "TRUSTED_ANCHOR_CONTEXT"
    assert all(edge["kind"] != "PHYSICAL" for edge in temporal["snapshots"][0]["edges"])


def test_pipeline_never_targets_historical_output_directories():
    source = Path(__file__).parents[1] / "src/memory_graph/v291/pipeline.py"
    body = source.read_text(encoding="utf-8")
    assert 'OUT = ROOT / "outputs_v291"' in body
    assert 'OUT = ROOT / "outputs_v29"' not in body
    assert 'OUT = ROOT / "outputs_v28"' not in body
