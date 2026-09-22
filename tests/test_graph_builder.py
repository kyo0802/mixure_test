from memory_graph.models import AnchorInfo, ObjectTrack, StableRelation, MemoryGraphData
from memory_graph.memory.graph_builder import build_graph, to_networkx


def test_multiedges_and_timestamps_survive_serialization():
    tracks = [ObjectTrack(object_id=x, class_name=x.split('_')[0], first_seen=0, last_seen=5)
              for x in ["cup_01", "table_01"]]
    anchors = [AnchorInfo(object_id="table_01", is_anchor=True, anchor_score=.9)]
    rels = [StableRelation(subject_id="cup_01", object_id="table_01", predicate=p,
                           reference_frame="camera_relative", start_time=1, end_time=4,
                           support_count=8, confidence=.85, episode_id="ep_0001")
            for p in ["NEAR", "ON_OR_ABOVE"]]
    data = build_graph("x.mp4", {"duration": 5}, [], tracks, anchors, rels, [])
    graph = to_networkx(data)
    assert graph.number_of_nodes() == 2 and graph.number_of_edges() == 2
    assert graph.nodes["table_01"]["node_type"] == "anchor"
    loaded = MemoryGraphData.model_validate_json(data.model_dump_json())
    assert loaded.relations[0].start_time == 1
    assert loaded.relations[1].object == "table_01"
