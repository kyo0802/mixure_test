from memory_graph.config import TemporalConfig, TransitionsConfig
from memory_graph.models import RelationObservation
from memory_graph.memory.temporal_filter import stabilize
from memory_graph.memory.graph_builder import derive_transitions


def sequence(anchors, step=.5):
    return [RelationObservation(subject_id="cup_01", object_id=f"{a}_01", predicate="NEAR",
                                reference_frame="camera_relative", confidence=.9, frame_index=i,
                                timestamp=i*step, episode_id="ep_0001") for i, a in enumerate(anchors)]


def test_single_frame_noise_rejected():
    stable = stabilize(sequence(["table", "table", "sofa", "table", "table"]), TemporalConfig())
    assert len(stable) == 1
    assert stable[0].object_id == "table_01"
    assert stable[0].support_count == 4
    assert stable[0].start_time == 0 and stable[0].end_time == 2


def test_persistent_change_produces_transition():
    stable = stabilize(sequence(["table"]*3 + ["sofa"]*3), TemporalConfig())
    events = derive_transitions(stable, TransitionsConfig())
    assert len(events) == 1
    assert events[0].from_anchor == "table_01" and events[0].to_anchor == "sofa_01"
    assert events[0].transition_time == 1.5


def test_episode_boundary_and_long_gap_do_not_merge():
    raw = sequence(["table"]*6)
    for r in raw[3:]:
        r.episode_id = "ep_0002"
    assert len(stabilize(raw, TemporalConfig())) == 2
    for r in raw[3:]:
        r.episode_id = "ep_0001"
        r.timestamp += 10
    assert len(stabilize(raw, TemporalConfig())) == 2


def test_simultaneous_anchors_do_not_imply_movement():
    raw = sequence(["table"]*4) + sequence(["sofa"]*4)
    assert derive_transitions(stabilize(raw, TemporalConfig()), TransitionsConfig()) == []


def test_duplicate_frame_cannot_inflate_support():
    raw = sequence(["table"])
    assert stabilize(raw*10, TemporalConfig()) == []
