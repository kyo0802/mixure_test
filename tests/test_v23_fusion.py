import inspect
from pathlib import Path

import memory_graph

local_package = str(Path(__file__).resolve().parents[1] / "src" / "memory_graph")
if local_package not in memory_graph.__path__:
    memory_graph.__path__.insert(0, local_package)

from memory_graph.v23.fusion import EntityRegistry, Observation, sam_guard


def obs(source="yolo_track", frame=0, source_id="track:22", bbox=None, label="cell phone"):
    return Observation(source, frame, frame * .2, source_id, bbox or [10, 10, 30, 30],
                       label, .8 if source.startswith("yolo") else None, None, None, "synthetic_frozen_evidence")


def seeded():
    registry = EntityRegistry(22, {22: "v21_a", 43: "v21_b"})
    registry.begin_frame(0, 0.)
    registry.observe_yolo(obs(), 22, [])
    return registry


def test_yolo_and_sam_can_update_same_entity():
    r = seeded()
    result = r.observe_sam(obs("sam", 0, "phone_track22"), {}, [[10, 10, 30, 30]], True)
    assert result[0] == "phone_01"
    assert r.sam_to_entity["phone_track22"] == r.track_to_entity[22]
    assert len(r.entities) == 1


def test_sam_only_observation_does_not_create_duplicate_entity():
    r = seeded()
    r.observe_sam(obs("sam", 0, "phone_track22"), {}, [], True)
    r.begin_frame(6, 1.2)
    r.observe_sam(obs("sam", 6, "phone_track22"), {}, [], False)
    assert len(r.entities) == 1
    assert r.entities["phone_01"]["state"] == "VISIBLE_PROPAGATED"


def test_yolo_miss_does_not_delete_persistent_entity():
    r = seeded()
    r.begin_frame(6, 1.2)
    r.observe_sam(obs("sam", 6, "phone_track22"), {}, [], True)
    assert "phone_01" in r.entities


def test_unobserved_entity_remains_in_registry():
    r = seeded()
    r.begin_frame(6, 1.2)
    assert r.entities["phone_01"]["state"] == "UNOBSERVED"
    assert r.entities["phone_01"]["last_trusted_seen"] == 0.


def test_conflicting_sam_observation_does_not_update_trusted_memory():
    r = seeded()
    trusted = r.entities["phone_01"]["latest_trusted_observation"]
    r.begin_frame(6, 1.2)
    bad = obs("sam", 6, "phone_track22", [0, 0, 60, 60])
    assert sam_guard(bad, {}, [[0, 0, 20, 20]])[0] == "REJECT_PROPAGATION"
    assert r.observe_sam(bad, {}, [[0, 0, 20, 20]], True) is None
    assert r.entities["phone_01"]["latest_trusted_observation"] == trusted
    assert r.entities["phone_01"]["state"] == "CONFLICT"
    assert all(o["frame_index"] != 6 for o in r.entities["phone_01"]["observation_history"])


def test_distinct_phone_candidates_are_not_force_merged():
    r = seeded()
    r.begin_frame(528, 17.6)
    a = r.observe_sam(obs("sam", 528, "late_candidate_1", [100, 10, 130, 40]), {}, [], True)
    b = r.observe_sam(obs("sam", 528, "late_candidate_2", [300, 10, 330, 40]), {}, [], True)
    assert a[0] != b[0]
    assert "phone_01" not in {a[0], b[0]}
    assert any(x["decision"] == "AMBIGUOUS" for x in r.audit)


def test_graph_nodes_use_persistent_entity_ids():
    r = seeded()
    snapshot = r.graph_snapshot(0, 0.)
    assert [n["entity_id"] for n in snapshot["nodes"]] == ["phone_01"]
    assert all(not n["entity_id"].startswith(("track:", "phone_track")) for n in snapshot["nodes"])


def test_gt_not_used_by_fusion():
    import memory_graph.v23.fusion as fusion
    source = inspect.getsource(fusion)
    assert "evaluation/v21" not in source
    assert "task1_annotations" not in source
    assert "task2_annotations" not in source
