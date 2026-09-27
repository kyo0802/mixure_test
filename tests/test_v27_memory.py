"""Identity, evidence, temporal and search invariants for the V2.7 store."""
from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from memory_graph.v27.models import EntityObservation
from memory_graph.v27.temporal_memory import TemporalMemory
from memory_graph.v27.search_planner import find


def observation(frame, identity="TRUSTED", entity="phone_01", label="cell phone", box=None):
    return EntityObservation(entity, frame, frame / 30, box or [100, 100, 130, 130], label,
                             identity, "synthetic_fixture", "track:7", f"fixture:{entity}:{frame}", 0.95)


def anchor(frame, entity="table_A", label="table", box=None):
    return observation(frame, entity=entity, label=label, box=box or [50, 80, 500, 400])


def evidence(frame, relation="ON", entity="table_A", **extra):
    return {"subject": "phone_01", "object": entity, "relation": relation, "frame": frame,
            "time": frame / 30, "source_kind": "interaction", "confidence": .95,
            "independent_physical_support": True, "source_ref": f"fixture_event:{frame}", **extra}


def stable(memory, start=0, relation=None, entity="table_A", label="table"):
    for frame in range(start, start + 18, 6):
        memory.step(frame, frame / 30, [observation(frame)], [anchor(frame, entity, label)],
                    "VISIBLE_TRUSTED", [evidence(frame, relation, entity)] if relation else [])


def loss(memory, frame=18):
    memory.step(frame, frame / 30, [], [anchor(frame)], "UNOBSERVED")


def test_confirmed_observation_can_update_memory():
    memory = TemporalMemory()
    memory.step(0, 0, [observation(0, "CONFIRMED_MATCH")], [])
    assert memory.target["last_seen_frame"] == 0
    assert memory.snapshots[0]["trigger_events"][0]["event_type"] == "TARGET_APPEARED"


@pytest.mark.parametrize("identity", ["PROVISIONAL_MATCH", "AMBIGUOUS", "UNKNOWN"])
def test_unconfirmed_identity_cannot_update_or_end_memory(identity):
    memory = TemporalMemory()
    stable(memory, relation="ON")
    before = deepcopy(memory.build_object_memory())
    memory.step(18, .6, [observation(18, identity)], [anchor(18, "new_A")], "VISIBLE_TRUSTED",
                [evidence(18, entity="new_A")])
    assert memory.build_object_memory() == before
    assert not memory.identity_audit[-1]["memory_update_authorized"]


def test_unobserved_retains_last_trusted_memory():
    memory = TemporalMemory()
    stable(memory, relation="ON")
    loss(memory)
    assert memory.target["state"] == "UNOBSERVED"
    assert memory.target["last_seen_frame"] == 12
    assert "table_A" in memory.target["last_trusted_anchors"]
    assert all(e.status == "LAST_TRUSTED" for e in memory.episodes)
    count = len(memory.snapshots)
    memory.step(24, .8, [], [], "UNOBSERVED")
    assert len(memory.snapshots) == count


@pytest.mark.parametrize("observed,forbidden", [("IMAGE_NEAR", "NEAR"), ("IMAGE_ABOVE", "ON"), ("IMAGE_OVERLAP", "OCCLUDED_BY")])
def test_image_geometry_never_auto_promotes(observed, forbidden):
    memory = TemporalMemory()
    stable(memory)
    assert observed in {r["relation"] for r in memory.relation_observations}
    assert forbidden not in {e.relation for e in memory.episodes}
    assert all(e.kind == "CONTEXT" for e in memory.episodes)


def test_irrelevant_node_excluded():
    memory = TemporalMemory()
    stable(memory, entity="chair_A", label="chair")
    assert "chair_A" not in memory.entities
    assert memory.relation_observations


def test_adjacent_repeated_relation_merges_episode():
    memory = TemporalMemory()
    stable(memory, relation="ON")
    stable(memory, start=18, relation="ON")
    physical = [e for e in memory.episodes if e.relation == "ON"]
    assert len(physical) == 1
    assert physical[0].support_frames == [0, 6, 12, 18, 24, 30]


def test_important_relation_change_creates_snapshot():
    memory = TemporalMemory()
    stable(memory, relation="ON")
    count = len(memory.snapshots)
    stable(memory, start=18, relation="ON", entity="shelf_B", label="shelf")
    assert len(memory.snapshots) > count
    assert any(e.event_type == "IMPORTANT_RELATION_ENDED" for e in memory.events)
    assert any(e.object == "shelf_B" and e.status == "ACTIVE" for e in memory.episodes)


def test_lifetime_preserves_history_and_ended_relations():
    memory = TemporalMemory()
    stable(memory, relation="ON")
    stable(memory, start=18, relation="ON", entity="shelf_B", label="shelf")
    life = memory.build_object_memory()
    assert any(e["object"] == "table_A" and e["status"] == "ENDED" for e in life["episodes"])
    assert any(e["object"] == "shelf_B" for e in life["episodes"])
    assert life["lifecycle"]


def test_old_relation_never_outranks_last_trusted():
    memory = TemporalMemory()
    stable(memory, relation="ON")
    stable(memory, start=18, relation="ON", entity="shelf_B", label="shelf")
    loss(memory, frame=36)
    rows = find(memory.build_object_memory())["candidates"]
    assert rows[0]["search_anchor"] == "shelf_B"
    assert rows[0]["priority_rule"] == 1
    assert all(r["priority_rule"] >= 3 for r in rows if r["search_anchor"] == "table_A")


def test_held_by_person_is_not_search_location():
    memory = TemporalMemory()
    stable(memory, relation="HELD_BY", entity="person_A", label="person")
    loss(memory)
    assert any(e.relation == "HELD_BY" for e in memory.episodes)
    assert not find(memory.build_object_memory())["candidates"]


def test_search_candidates_have_provenance_and_reason():
    memory = TemporalMemory()
    stable(memory)
    loss(memory)
    row = find(memory.build_object_memory())["candidates"][0]
    assert row["source_memory"] and row["source_episode"] and row["reason"] and row["provenance"]
    assert "Image-relative" in row["uncertainty"]


def test_same_frame_phones_do_not_alias_target():
    memory = TemporalMemory()
    memory.step(0, 0, [observation(0), observation(0, "AMBIGUOUS", None)], [])
    assert sum(r["memory_update_authorized"] for r in memory.identity_audit) == 1
    assert set(memory.entities) == {"phone_01"}


@pytest.mark.parametrize("entity", ["track:7", "track_0007", "7"])
def test_track_id_is_not_persistent_entity_id(entity):
    with pytest.raises(ValueError, match="PersistentEntity"):
        observation(0, entity=entity)


def test_inference_cannot_import_gt_or_evaluation():
    for path in (ROOT / "src/memory_graph/v27").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not any(x in (node.module or "").split(".") for x in ("evaluation", "evaluate_v27", "gt"))
            if isinstance(node, ast.Import):
                assert not any("evaluation" in alias.name or "evaluate_v27" in alias.name for alias in node.names)
        assert "narrative" not in path.read_text(encoding="utf-8").replace('"operator_exposed_to_user_narrative"', '')


def test_future_physical_evidence_rejected():
    memory = TemporalMemory()
    for frame in (0, 6, 12):
        memory.step(frame, frame / 30, [observation(frame)], [anchor(frame)],
                    "VISIBLE_TRUSTED", [evidence(frame + 30)])
    assert not any(e.kind == "PHYSICAL" for e in memory.episodes)


def test_disappearance_and_overlap_only_make_occlusion_candidate():
    memory = TemporalMemory()
    stable(memory)
    loss(memory)
    assert memory.target["possible_occluders"][0]["status"] == "CANDIDATE"
    assert not any(e.relation == "OCCLUDED_BY" for e in memory.episodes)


def test_reconfirmation_stales_previous_memory_without_retroactive_alias():
    memory = TemporalMemory()
    stable(memory)
    loss(memory)
    memory.step(30, 1, [observation(30, "CONFIRMED_MATCH")], [], "UNOBSERVED")
    assert memory.target["last_seen_frame"] == 30
    assert all(e.status == "STALE" for e in memory.episodes)
    assert memory.target["last_trusted_anchors"] == []
    assert memory.events[-1].event_type == "TARGET_RECONFIRMED"


def test_snapshots_are_immutable_and_not_per_frame():
    memory = TemporalMemory()
    stable(memory, relation="ON")
    old = deepcopy(memory.snapshots)
    stable(memory, start=18, relation="ON")
    assert memory.snapshots == old
    assert len(memory.snapshots) == 2


def test_one_frame_duplicate_sources_do_not_fake_temporal_support():
    memory = TemporalMemory()
    memory.step(0, 0, [observation(0) for _ in range(5)], [anchor(0)],
                "VISIBLE_TRUSTED", [evidence(0)] * 5)
    assert not memory.episodes


def test_unconfirmed_candidate_does_not_change_search_priority():
    memory = TemporalMemory()
    stable(memory, relation="ON")
    loss(memory)
    before = find(memory.build_object_memory())
    memory.step(24, .8, [observation(24, "PROVISIONAL_MATCH")], [anchor(24, "shelf_B")], "UNOBSERVED")
    assert find(memory.build_object_memory()) == before


def test_real_upstream_provisional_and_confirmed_are_causal():
    from memory_graph.v27.pipeline import load_inputs
    frames, _ = load_inputs("test7")
    provisional = [o for row in frames for o in row["observations"] if o.identity == "PROVISIONAL_MATCH"]
    assert provisional and all(o.entity_id is None and not o.trusted for o in provisional)
    frames, _ = load_inputs("test8")
    confirmed = [o for row in frames for o in row["observations"] if o.identity == "CONFIRMED_MATCH"]
    assert len(confirmed) == 1 and confirmed[0].frame == 804 and confirmed[0].trusted
    candidate_rows = [o for row in frames for o in row["observations"] if o.source_id == "candidate_009"]
    assert all(o.frame == 804 or not o.trusted for o in candidate_rows)
