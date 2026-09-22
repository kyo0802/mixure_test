import pytest
from pydantic import ValidationError
from memory_graph.models import Detection, MemoryGraphData


def test_detection_rejects_inverted_box():
    with pytest.raises(ValidationError):
        Detection(class_id=0, class_name="cup", confidence=.8, bbox=(20, 0, 10, 10),
                  frame_index=0, timestamp=0)


def test_detection_center_is_derived():
    d = Detection(class_id=0, class_name="cup", confidence=.8, bbox=(10, 20, 30, 60),
                  frame_index=0, timestamp=0)
    assert d.center == (20, 40)
    assert d.model_dump(mode="json")["center"] == [20, 40]


def test_graph_round_trip():
    graph = MemoryGraphData(video="example.mp4", metadata={"duration": 3})
    assert MemoryGraphData.model_validate_json(graph.model_dump_json()) == graph
