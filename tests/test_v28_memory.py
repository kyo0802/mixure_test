"""V2.8 local graph, physical reasoning, identity, memory, and search gates."""
from __future__ import annotations

import ast
from dataclasses import asdict
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from memory_graph.v27.models import EntityObservation
from memory_graph.v28.local_subgraph import build_local_subgraph
from memory_graph.v28.memory import build_memory, object_memory
from memory_graph.v28.models import SpatialSegment
from memory_graph.v28.physical_reasoner import reason_relation
from memory_graph.v28.pipeline import verify_v27_freeze
from memory_graph.v28.roles import semantic_roles
from memory_graph.v28.search_planner import find


SIZE = (1280, 720)


def obs(frame, entity="phone_01", label="cell phone", bbox=None, identity="TRUSTED"):
    return EntityObservation(entity, frame, frame / 30, bbox or [100, 100, 130, 130], label, identity,
                             "fixture", f"source:{entity}", f"fixture:{entity}:{frame}", .95)


def frame(frame, anchors=(), phone=True, identity="TRUSTED", state="VISIBLE_TRUSTED"):
    return {"frame": frame, "time": frame / 30, "upstream_state": state,
            "observations": [obs(frame, identity=identity, entity="phone_01" if identity in {"TRUSTED", "CONFIRMED_MATCH"} else None)] if phone else [],
            "anchors": list(anchors)}


def local_fixture(include_context=True, noise=0):
    rows = []
    for number in (0, 6, 12):
        anchors = [obs(number, "ball_A", "sports ball", [350, 95, 400, 150])]
        if include_context:
            anchors.append(obs(number, "chair_A", "chair", [600, 80, 800, 400]))
        anchors += [obs(number, f"noise_{i}", "person", [800 + i, 500, 820 + i, 650]) for i in range(noise)]
        rows.append(frame(number, anchors))
    return rows


def segment(label="sports ball", roles=None, boxes=None, **flags):
    boxes = boxes or [([100, 100, 130, 130], [135, 95, 190, 150]),
                      ([106, 100, 136, 130], [141, 95, 196, 150]),
                      ([112, 100, 142, 130], [147, 95, 202, 150])]
    observations = []
    for index, (target, anchor) in enumerate(boxes):
        observations.append({"frame": index * 6, "time": index * .2, "target_bbox": target, "anchor_bbox": anchor,
                             "target_observation": f"target:{index}", "anchor_observation": f"anchor:{index}",
                             "target_identity": flags.get("identity", "TRUSTED"),
                             "interaction_evidence": flags.get("interaction", False),
                             "independent_physical_support": flags.get("independent", False),
                             "target_disappears_after": flags.get("disappears", False),
                             "remains_unobserved": flags.get("remains", False),
                             "reappeared_consistently": flags.get("reappears", False),
                             "target_mask_ref": flags.get("mask_ref")})
    return SpatialSegment("P0001", "phone_01", "anchor_A", 1, 0, 12, 0, .4,
                          [0, 6, 12], [0, .2, .4], label, roles or semantic_roles(label), observations)


def lost_memory(physical_decision=None, with_context=True):
    frames = local_fixture(include_context=with_context) + [frame(18, [], phone=False, state="UNOBSERVED")]
    graph = build_local_subgraph(frames, SIZE)
    physical = []
    if physical_decision:
        physical = [asdict(physical_decision)]
        physical[0]["anchor"] = "ball_A"
        physical[0]["segment_id"] = graph["primary_segments"][0]["segment_id"]
    return object_memory(build_memory(frames, graph, physical))


def test_01_phone_hop0_always_exists():
    graph = build_local_subgraph([], SIZE)
    assert graph["nodes"] == [{"entity_id": "phone_01", "raw_label": "cell phone", "semantic_roles": ["TARGET"], "hop": 0, "via_primary": None}]


def test_02_trusted_direct_anchor_becomes_hop1():
    graph = build_local_subgraph(local_fixture(False), SIZE)
    assert any(node["entity_id"] == "ball_A" and node["hop"] == 1 for node in graph["nodes"])


def test_03_useful_anchor_of_anchor_becomes_hop2():
    graph = build_local_subgraph(local_fixture(True), SIZE)
    assert any(node["entity_id"] == "chair_A" and node["hop"] == 2 for node in graph["nodes"])


def test_04_unrelated_same_frame_object_excluded():
    graph = build_local_subgraph(local_fixture(False, noise=1), SIZE)
    assert not any(node["entity_id"].startswith("noise") for node in graph["nodes"])


def test_05_hop2_has_traceable_hop1_path():
    graph = build_local_subgraph(local_fixture(True), SIZE)
    for node in (n for n in graph["nodes"] if n["hop"] == 2):
        assert any(edge["source"] == node["via_primary"] and edge["target"] == node["entity_id"] for edge in graph["edges"])


def test_06_graph_does_not_become_full_scene_graph():
    graph = build_local_subgraph(local_fixture(False, noise=100), SIZE)
    assert len(graph["nodes"]) <= 10


def test_07_person_requires_interaction_evidence():
    assert "INTERACTION_AGENT" in semantic_roles("person")
    graph = build_local_subgraph(local_fixture(False, noise=1), SIZE)
    assert not any("INTERACTION_AGENT" in node["semantic_roles"] for node in graph["nodes"])


@pytest.mark.parametrize("relation", ["NEAR", "ON", "INSIDE", "OCCLUDED_BY"])
def test_08_to_11_image_geometry_does_not_directly_promote(relation):
    label = {"ON": "table", "INSIDE": "box", "OCCLUDED_BY": "sports ball"}.get(relation, "sports ball")
    result = reason_relation(segment(label), relation, SIZE)
    assert result.decision != "PROMOTED"


def test_12_temporal_held_pattern_makes_candidate():
    boxes = [([100, 100, 130, 130], [90, 80, 180, 240]),
             ([120, 100, 150, 130], [110, 80, 200, 240]),
             ([140, 100, 170, 130], [130, 80, 220, 240])]
    result = reason_relation(segment("person", ["INTERACTION_AGENT"], boxes, interaction=True), "HELD_BY", SIZE)
    assert result.decision == "CANDIDATE"


def test_13_strong_held_evidence_promotes():
    boxes = [([100, 100, 130, 130], [90, 80, 180, 240]),
             ([120, 100, 150, 130], [110, 80, 200, 240]),
             ([140, 100, 170, 130], [130, 80, 220, 240])]
    result = reason_relation(segment("person", ["INTERACTION_AGENT"], boxes, interaction=True, independent=True), "HELD_BY", SIZE)
    assert result.decision == "PROMOTED"


def test_14_temporal_placement_makes_candidate_on():
    boxes = [([90, 55, 120, 92], [50, 100, 300, 300]),
             ([100, 60, 130, 96], [50, 100, 300, 300]),
             ([110, 65, 140, 100], [50, 100, 300, 300])]
    assert reason_relation(segment("table", boxes=boxes), "ON", SIZE).decision == "CANDIDATE"


def test_15_insufficient_on_does_not_promote():
    assert reason_relation(segment("table"), "ON", SIZE).decision != "PROMOTED"


def test_16_container_entry_makes_candidate_inside():
    boxes = [([0, 0, 30, 30], [50, 50, 200, 200]),
             ([40, 40, 75, 75], [50, 50, 200, 200]),
             ([70, 70, 105, 105], [50, 50, 200, 200])]
    assert reason_relation(segment("box", boxes=boxes), "INSIDE", SIZE).decision == "CANDIDATE"


def test_17_insufficient_inside_does_not_promote():
    assert reason_relation(segment("box"), "INSIDE", SIZE).decision != "PROMOTED"


def occlusion_segment(**flags):
    boxes = [([0, 0, 60, 60], [100, 0, 180, 180]),
             ([70, 0, 120, 45], [100, 0, 180, 180]),
             ([105, 5, 130, 30], [100, 0, 180, 180])]
    return segment("sports ball", boxes=boxes, disappears=True, **flags)


def test_18_occlusion_pattern_makes_candidate():
    assert reason_relation(occlusion_segment(), "OCCLUDED_BY", SIZE).decision == "CANDIDATE"


def test_19_behind_and_occluded_decisions_are_separate():
    seg = occlusion_segment(reappears=True, independent=True)
    assert reason_relation(seg, "OCCLUDED_BY", SIZE).decision == "PROMOTED"
    assert reason_relation(seg, "BEHIND", SIZE).decision != "PROMOTED"


def test_20_disappearance_without_temporal_pattern_is_not_behind():
    assert reason_relation(segment("sports ball", disappears=True, remains=True), "BEHIND", SIZE).decision != "PROMOTED"


@pytest.mark.parametrize("identity", ["PROVISIONAL_MATCH", "AMBIGUOUS"])
def test_21_22_untrusted_identity_cannot_update_physical_memory(identity):
    result = reason_relation(segment(identity=identity), "NEAR", SIZE)
    assert result.decision == "REJECTED" and result.identity_state == "UNAUTHORIZED"


def test_23_confirmed_target_can_update():
    assert reason_relation(segment(identity="CONFIRMED_MATCH"), "NEAR", SIZE).decision == "CANDIDATE"


def test_24_unobserved_retains_last_trusted_subgraph():
    memory = lost_memory()
    assert memory["target"]["state"] == "UNOBSERVED"
    assert memory["last_trusted_local_subgraph"]["edges"]


def test_25_candidate_search_is_explicitly_unconfirmed():
    decision = reason_relation(segment(), "NEAR", SIZE)
    plan = find(lost_memory(decision))
    row = next(row for row in plan["candidates"] if row["relation"] == "NEAR")
    assert row["priority_rule"] == 3 and row["confirmed"] is False and "unconfirmed" in row["reason"].lower()


def test_26_promoted_placement_outranks_image_context():
    decision = reason_relation(segment("box", boxes=[([0, 0, 30, 30], [50, 50, 200, 200]),
                                                       ([40, 40, 75, 75], [50, 50, 200, 200]),
                                                       ([70, 70, 105, 105], [50, 50, 200, 200])], independent=True), "INSIDE", SIZE)
    plan = find(lost_memory(decision, False))
    assert plan["candidates"][0]["priority_rule"] == 1


def test_27_hop2_context_localizes_search_anchor():
    plan = find(lost_memory())
    context_row = next(row for row in plan["candidates"] if row["search_anchor"] == "ball_A")
    assert context_row["context_anchors"][0]["entity_id"] == "chair_A"


def test_28_held_by_is_not_search_location():
    decision = reason_relation(segment("person", ["INTERACTION_AGENT"],
        [([100, 100, 130, 130], [90, 80, 180, 240]), ([120, 100, 150, 130], [110, 80, 200, 240]),
         ([140, 100, 170, 130], [130, 80, 220, 240])], interaction=True, independent=True), "HELD_BY", SIZE)
    memory = lost_memory()
    memory["entities"].append({"entity_id": "person_A", "raw_label": "person", "semantic_roles": ["INTERACTION_AGENT"], "hop": 1})
    memory["episodes"].append({"episode_id": "held", "segment_id": "held", "subject": "phone_01", "relation": "HELD_BY",
        "object": "person_A", "kind": "PHYSICAL", "decision": decision.decision, "start_frame": 0, "end_frame": 12,
        "start_time": 0, "last_confirmed_time": .4, "status": "LAST_TRUSTED", "source": [], "source_snapshots": []})
    assert all(row["search_anchor"] != "person_A" for row in find(memory)["candidates"])


def test_29_same_frame_multiple_phones_do_not_alias():
    rows = local_fixture(False)
    rows[0]["observations"].append(obs(0, None, "cell phone", [300, 300, 330, 330], "AMBIGUOUS"))
    graph = build_local_subgraph(rows, SIZE)
    assert [node["entity_id"] for node in graph["nodes"]].count("phone_01") == 1
    assert any(row["identity"] == "AMBIGUOUS" and not row["memory_update_authorized"] for row in graph["identity_audit"])


def test_30_inference_does_not_import_gt_or_narrative():
    for path in (ROOT / "src/memory_graph/v28").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names]
                assert not any("evaluation" in name or name == "gt" for name in names)
        text = path.read_text(encoding="utf-8").casefold()
        assert "narrative" not in text and "if task == \"test" not in text


def test_31_outputs_v27_remain_hash_valid():
    verify_v27_freeze()


def test_32_v27_regression_suite_is_retained():
    assert (ROOT / "tests/test_v27_memory.py").is_file()
