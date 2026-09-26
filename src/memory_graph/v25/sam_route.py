"""Generic video routing into unchanged official SAM 2.1 propagation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from memory_graph.v22 import sam_tracking as frozen
from memory_graph.v241.adapter import v21_inputs

ROOT = frozen.ROOT
OUT = ROOT / "outputs_v25"


class SamRouter:
    def __init__(self, task):
        import torch
        self.task = task
        self.torch = torch
        self.inputs, self.hashes = v21_inputs(task)
        self.output = OUT / task / "sam"
        self.output.mkdir(parents=True, exist_ok=True)
        for path in (frozen.SAM_DEPS, frozen.SAM_SOURCE):
            if str(path) not in sys.path:
                sys.path.insert(0, str(path))
        from sam2.build_sam import build_sam2_video_predictor
        self.predictor = build_sam2_video_predictor(frozen.CONFIG, str(frozen.CHECKPOINT),
                                                      device="cuda", apply_postprocessing=False)

    def segment(self, name, first, last, seed_id, detection):
        """Only IO/seed routing differs from frozen V2.2 run_segment."""
        original_choose, original_extract = frozen.choose_seeds, frozen.extract_frames
        video = ROOT / f"{self.task}.mp4"
        if first != detection["frame_index"]:
            raise ValueError("Seed and segment start differ")

        def choose(_task, _segment, _inputs):
            return [(seed_id, detection)]

        def extract(_video, frames, folder):
            return original_extract(video, frames, folder)

        frozen.choose_seeds, frozen.extract_frames = choose, extract
        try:
            with self.torch.inference_mode(), self.torch.autocast("cuda", dtype=self.torch.bfloat16):
                result = frozen.run_segment(self.task, name, first, last, self.inputs,
                                            self.predictor, self.output)
        finally:
            frozen.choose_seeds, frozen.extract_frames = original_choose, original_extract
        return result

    def target(self, bound):
        if bound is None:
            return {"status": "TARGET_BINDING_AMBIGUOUS", "segments": [], "events": []}
        first = bound.frame_index
        last = self.inputs["video_metadata.json"]["sampled_frames"][-1]["frame_index"]
        detections = self.inputs["detections.json"]
        matches = [d for d in detections if d["frame_index"] == first and d["class_name"] == "cell phone"
                   and frozen.box_iou(d["bbox"], bound.bbox) >= .95]
        if not matches:
            raise ValueError("No frozen YOLO box for target binding")
        detection = max(matches, key=lambda d: d["confidence"])
        segment = self.segment("target_full", first, last, "phone_target", detection)
        payload = {"status": "COMPLETE", "task": self.task, "checkpoint_sha256": frozen.sha256(frozen.CHECKPOINT),
                   "config": frozen.CONFIG, "step_frames": frozen.STEP, "frozen_input_sha256": self.hashes,
                   "target_binding": vars(bound), "segments": [segment], "events": segment["events"],
                   "drift_guard": "unchanged V2.3 sam_guard applied downstream"}
        (self.output / "sam_continuity_log.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def candidate(self, candidate, last_frame):
        first_obs = next((o for o in candidate.observations if o["confidence"] >= .5), None)
        if first_obs is None:
            return {"candidate_id": candidate.candidate_id, "status": "NO_ELIGIBLE_YOLO_SEED", "segment": None}
        first = first_obs["frame_index"]
        raw_index = first_obs["raw_detection_index"]
        detection = self.inputs["detections.json"][raw_index]
        last = min(first + 18, last_frame)
        name = f"sam_{candidate.candidate_id}"
        result = self.segment(name, first, last, name, detection)
        return {"candidate_id": candidate.candidate_id, "status": "SEEDED", "segment": result}

    def reinitialize_after_match(self, candidate, matched_frame):
        """Actual same-identity propagation, called only after frozen MATCH."""
        viable = [o for o in candidate.observations if o["frame_index"] == matched_frame]
        if not viable:
            return {"status": "AUTHORIZED_NOT_EXECUTED", "reason": "no candidate box at match frame"}
        observation = max(viable, key=lambda o: o["confidence"])
        detection = self.inputs["detections.json"][observation["raw_detection_index"]]
        last = self.inputs["video_metadata.json"]["sampled_frames"][-1]["frame_index"]
        result = self.segment("same_identity_reinit", matched_frame, last, "phone_01_reinit", detection)
        return {"status": "EXECUTED", "candidate_id": candidate.candidate_id,
                "same_identity_entity_id": "phone_01", "segment": result}
