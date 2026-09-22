import json
import cv2
import numpy as np
from memory_graph.config import Config
from memory_graph.models import Detection, ObjectTrack
from memory_graph.pipeline import run_video, ARTIFACTS
from memory_graph.memory.memory_store import load_graph


class SyntheticDetector:
    """Known boxes for integration only; never used by the production CLI."""
    names = {0: "cup", 1: "dining table"}
    device = "synthetic test double"

    def detect(self, frame, info):
        return [Detection(class_id=cid, class_name=self.names[cid], confidence=.95, bbox=box,
                          frame_index=info.frame_index, timestamp=info.timestamp)
                for cid, box in [(0, (120, 70, 145, 115)), (1, (70, 120, 270, 210))]]


def test_complete_pipeline_artifacts(tmp_path):
    source = tmp_path/"SYNTHETIC_TEST.mp4"
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*"mp4v"), 10, (320, 240))
    assert writer.isOpened()
    for _ in range(60):
        image = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.rectangle(image, (120, 70), (145, 115), (255, 200, 80), -1)
        cv2.rectangle(image, (70, 120), (270, 210), (80, 130, 220), -1)
        writer.write(image)
    writer.release()
    config = Config()
    config.detector.model = "SYNTHETIC_TEST_DOUBLE_NOT_YOLO"
    output = tmp_path/"output"
    data = run_video(source, config, output, detector=SyntheticDetector())
    assert len(data.nodes) == 2 and any(n.node_type == "anchor" for n in data.nodes)
    assert data.relations and len(data.episodes) == 1
    assert data.metadata["decoded_frame_count"] == 60
    assert all((output/name).is_file() for name in ARTIFACTS)
    assert load_graph(output/"memory_graph.json").relations == data.relations
    for track in json.loads((output/"tracks.json").read_text()):
        assert ObjectTrack.model_validate(track).observations
    assert json.loads((output/"run_status.json").read_text())["status"] == "complete"
