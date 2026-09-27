"""Nonmutating SAM3 box-arm diagnostic for the frozen test8 reinitialization window."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from memory_graph.v262.adapters import normalized_xywh
from memory_graph.v262.paired import ROOT, extracted


def main() -> None:
    from sam3.model_builder import build_sam3_predictor

    out = ROOT / "outputs_v262"
    manifest = json.loads((out / "experiment_manifest.json").read_text(encoding="utf-8"))
    window = next(w for w in manifest["videos"]["test8"]["windows"] if w["name"] == "same_identity_reinit")
    frames = window["frames"]
    predictor = build_sam3_predictor(checkpoint_path=str(ROOT / ".models" / "sam3" / "sam3.pt"),
                                     version="sam3", compile=False, async_loading_frames=False,
                                     video_loader_type="cv2")
    try:
        with tempfile.TemporaryDirectory(prefix="v262_box_diagnostic_", dir=out / "smoke") as tmp:
            width, height = extracted(Path(tmp), ROOT / "test8.mp4", frames)
            session_id = predictor.handle_request({"type": "start_session", "resource_path": tmp,
                                                   "offload_video_to_cpu": True, "offload_state_to_cpu": True})["session_id"]
            box = normalized_xywh(window["source_detection"]["bbox"], width, height)
            response = predictor.handle_request({"type": "add_prompt", "session_id": session_id,
                                                 "frame_index": 0, "bounding_boxes": [box],
                                                 "bounding_box_labels": [1]})
            prompt = response["outputs"]
            diagnostic = {"schema": "v262_box_diagnostic_1", "window": "test8 same_identity_reinit",
                          "frames_in_session": len(frames), "source_frames_first_eight": frames[:8],
                          "prompt_ids": np.asarray(prompt.get("out_obj_ids", [])).astype(int).tolist(),
                          "prompt_boxes_xywh": np.asarray(prompt.get("out_boxes_xywh", [])).tolist(),
                          "prompt_areas": [int(np.count_nonzero(m)) for m in np.asarray(prompt.get("out_binary_masks", []))],
                          "first_eight": []}
            for response in predictor.handle_stream_request({"type": "propagate_in_video", "session_id": session_id,
                                                             "propagation_direction": "forward", "start_frame_index": 0,
                                                             "max_frame_num_to_track": len(frames)}):
                index = response["frame_index"]
                if index < 8:
                    output = response["outputs"]
                    diagnostic["first_eight"].append({
                        "frame": frames[index], "ids": np.asarray(output.get("out_obj_ids", [])).astype(int).tolist(),
                        "areas": [int(np.count_nonzero(m)) for m in np.asarray(output.get("out_binary_masks", []))]})
            predictor.handle_request({"type": "close_session", "session_id": session_id})
        (out / "smoke" / "sam3_box_long_window_diagnostic.json").write_text(
            json.dumps(diagnostic, indent=2), encoding="utf-8")
        print(json.dumps(diagnostic, indent=2))
    finally:
        predictor.shutdown()


if __name__ == "__main__":
    main()
