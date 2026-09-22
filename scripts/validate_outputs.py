"""Audit real-video artifacts without re-running perception or downloading a model."""
import json
from pathlib import Path
import cv2
from memory_graph.memory.memory_store import load_graph, save_json
from memory_graph.models import ObjectTrack, Detection, StableRelation


def validate(name):
    root = Path("outputs")/name
    required = ["video_metadata.json", "episodes.json", "detections.json", "tracks.json", "anchors.json",
                "relation_observations.json", "stable_relations.json", "transitions.json", "memory_graph.json",
                "memory_graph.png", "annotated.mp4", "run_config.json", "run_status.json", "run.log"]
    for file in required:
        assert (root/file).is_file() and (root/file).stat().st_size > 0, f"Missing/empty artifact: {root/file}"
    read = lambda file: json.loads((root/file).read_text(encoding="utf-8"))
    status = read("run_status.json")
    assert status["status"] == "complete"
    metadata = read("video_metadata.json")
    assert metadata["decoded_frame_count"] == metadata["frame_count"]
    assert metadata["sampled_frames"][0]["frame_index"] == 0
    assert metadata["sampled_frames"][-1]["frame_index"] == metadata["frame_count"]-1
    episodes = read("episodes.json")
    assert episodes and episodes[0]["start_frame"] == 0
    assert episodes[-1]["end_frame"] == metadata["frame_count"]-1
    assert all(a["end_frame"]+1 == b["start_frame"] for a, b in zip(episodes, episodes[1:]))
    detections = [Detection.model_validate(d) for d in read("detections.json")]
    tracks = [ObjectTrack.model_validate(t) for t in read("tracks.json")]
    anchors = [a for a in read("anchors.json") if a["is_anchor"]]
    raw = read("relation_observations.json")
    stable = [StableRelation.model_validate(r) for r in read("stable_relations.json")]
    graph = load_graph(root/"memory_graph.json")
    assert detections and tracks and anchors and raw and stable, "Insufficient real-video graph evidence"
    assert len(graph.nodes) == len(tracks) and len(graph.relations) == len(stable)
    assert {n.id for n in graph.nodes} == {t.object_id for t in tracks}
    assert [event.model_dump(mode="json") for event in graph.transitions] == read("transitions.json")
    for relation in stable:
        supporting = {r["frame_index"] for r in raw if
            (r["subject_id"], r["object_id"], r["predicate"], r["episode_id"], r["reference_frame"]) ==
            (relation.subject_id, relation.object_id, relation.predicate, relation.episode_id, relation.reference_frame)
            and relation.start_frame <= r["frame_index"] <= relation.end_frame}
        assert len(supporting) == relation.support_count
    cap = cv2.VideoCapture(str(root/"annotated.mp4"))
    try:
        assert cap.isOpened()
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == metadata["frame_count"]
        assert abs(cap.get(cv2.CAP_PROP_FPS)-metadata["fps"]) < .01
        cap.set(cv2.CAP_PROP_POS_FRAMES, metadata["frame_count"]-1)
        assert cap.read()[0], "Final annotated frame did not decode"
        for seconds in [10, 25]:
            cap.set(cv2.CAP_PROP_POS_MSEC, seconds*1000)
            ok, frame = cap.read()
            assert ok
            cv2.imwrite(str(root/f"validation_frame_{seconds}s.png"), frame)
    finally:
        cap.release()
    image = cv2.imread(str(root/"memory_graph.png"))
    assert image is not None and image.std() > 1
    return {"video": name+".mp4", "passed": True, "episodes": len(episodes), "tracks": len(tracks),
            "anchors": len(anchors), "detections": len(detections), "relation_observations": len(raw),
            "stable_relations": len(stable), "transitions": len(graph.transitions),
            "decoded_frames": metadata["decoded_frame_count"], "sampled_frames": len(metadata["sampled_frames"]),
            "duration_seconds": metadata["duration"], "required_artifacts": required,
            "graph_detail_pages": len(list(root.glob("memory_graph_page_*.png")))}


if __name__ == "__main__":
    results = [validate(name) for name in ["task1", "task2"]]
    save_json("outputs/validation_report.json", results)
    print(json.dumps(results, indent=2))
