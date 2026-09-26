import inspect
import importlib.util
from pathlib import Path

import numpy as np
import pytest

_module_path = Path(__file__).resolve().parents[1] / "src" / "memory_graph" / "v22" / "sam_tracking.py"
_spec = importlib.util.spec_from_file_location("v22_sam_tracking", _module_path)
sam_tracking = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sam_tracking)


def test_sam_adapter_produces_local_observation():
    mask = np.zeros((10, 10), dtype=bool)
    mask[2:5, 3:7] = True
    obs = sam_tracking.mask_to_observation(mask, 6, .2, "initial", "phone")
    assert obs["bbox"] == [3, 2, 7, 5]
    assert obs["mask_area"] == 12
    assert obs["center"] == [4.5, 3.0]
    assert obs["source"] == "sam2.1_propagation"
    assert obs["confidence"] is None
    assert np.array_equal(sam_tracking.decode_mask(sam_tracking.encode_mask(mask)), mask)


def test_gt_never_used_for_sam_initialization():
    source = inspect.getsource(sam_tracking)
    assert "evaluation/v21" not in source
    assert "task1_annotations" not in source
    assert "task2_annotations" not in source


def test_same_frozen_yolo_initialization_used_for_ab():
    detection = {"frame_index": 6, "class_name": "cell phone", "bbox": [1, 2, 5, 6], "confidence": .8}
    track = {"track_id": 17, "observations": [{"frame_index": 6, "bbox": [1, 2, 5, 6]}]}
    assert sam_tracking.yolo_box_for_track([track], [detection], 17, 6) is detection


def test_sam_lost_does_not_fabricate_observation():
    assert sam_tracking.mask_to_observation(np.zeros((4, 4), dtype=bool), 6, .2, "initial", "phone") is None


def test_reinitialization_requires_frozen_yolo_detection():
    assert sam_tracking.yolo_box_for_track([{"track_id": 17, "observations": [{"frame_index": 6, "bbox": [1, 2, 5, 6]}]}], [], 17, 6) is None
    with pytest.raises(ValueError, match="YOLO_INITIALIZATION_MISS"):
        sam_tracking.choose_seeds("task1", "initial", {"detections.json": [], "track_timelines.json": [{"track_id": 17, "observations": [{"frame_index": 240, "bbox": [1, 2, 5, 6]}]}]})
