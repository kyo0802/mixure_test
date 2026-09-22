from memory_graph.config import RelationsConfig
from memory_graph.models import ObjectObservation
from memory_graph.spatial.relation_extractor import extract_pair


def observation(object_id, bbox):
    return ObjectObservation(object_id=object_id, tracker_id=1, class_id=0,
                             class_name=object_id.split('_')[0], bbox=bbox,
                             confidence=.95, frame_index=0, timestamp=0, episode_id="ep_0001")


def test_above_table():
    rels = extract_pair(observation("cup_01", (40, 25, 50, 45)),
                        observation("table_01", (20, 50, 90, 90)), 100, 100, RelationsConfig())
    names = {r.predicate for r in rels}
    assert {"ABOVE", "NEAR", "ON_OR_ABOVE"} <= names
    assert all(r.reference_frame in {"camera", "camera_relative"} for r in rels)


def test_left_and_resolution_invariance():
    a, b = (10, 50, 20, 60), (25, 40, 75, 90)
    first = extract_pair(observation("cup_01", a), observation("table_01", b), 100, 100, RelationsConfig())
    second = extract_pair(observation("cup_01", tuple(v*10 for v in a)),
                          observation("table_01", tuple(v*10 for v in b)), 1000, 1000, RelationsConfig())
    assert "LEFT_OF" in {r.predicate for r in first}
    assert [(r.predicate, r.confidence) for r in first] == [(r.predicate, r.confidence) for r in second]


def test_inside_is_only_projected_containment():
    rels = extract_pair(observation("cup_01", (40, 40, 50, 50)),
                        observation("cabinet_01", (20, 20, 90, 90)), 100, 100, RelationsConfig())
    assert {"INSIDE", "OVERLAPS", "NEAR"} <= {r.predicate for r in rels}
    assert next(r for r in rels if r.predicate == "INSIDE").reference_frame == "camera_relative"


def test_far_pair_has_no_relations():
    assert not extract_pair(observation("cup_01", (0, 0, 5, 5)),
                            observation("table_01", (80, 80, 100, 100)), 100, 100, RelationsConfig())
