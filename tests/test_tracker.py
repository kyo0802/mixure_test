from memory_graph.config import ObjectsConfig, TrackingConfig
from memory_graph.models import Detection
from memory_graph.perception.tracker import ObjectTracker


def detection(i, cid=0):
    return Detection(class_id=cid, class_name={0: "cup", 1: "dining table"}[cid], confidence=.95,
                     bbox=(40, 40, 80, 80), frame_index=i*10, timestamp=i/3)


def test_tracker_keeps_identity_through_miss_and_separates_classes():
    tracker = ObjectTracker(TrackingConfig(), {0: "cup", 1: "dining table"}, ObjectsConfig(), 3)
    a = tracker.update([detection(0), detection(0, 1)], "ep_0001", (240, 320))
    tracker.update([], "ep_0001", (240, 320))
    b = tracker.update([detection(2), detection(2, 1)], "ep_0001", (240, 320))
    assert {o.object_id for o in a} == {o.object_id for o in b} == {"cup_01", "table_01"}
    assert len(tracker.tracks["cup_01"].observations) == 2


def test_scene_cut_does_not_reuse_graph_identity():
    tracker = ObjectTracker(TrackingConfig(), {0: "cup"}, ObjectsConfig(), 3)
    first = tracker.update([detection(0)], "ep_0001", (240, 320))
    second = tracker.update([detection(1)], "ep_0002", (240, 320))
    assert first[0].object_id == "cup_01" and second[0].object_id == "cup_02"
