"""Continuous GT-free admission, registry persistence, and audit writing."""
from __future__ import annotations

import json
from pathlib import Path

from memory_graph.v22.sam_tracking import sha256
from memory_graph.v241.adapter import v21_inputs
from .candidates import CandidateStream
from .fusion import fuse_video, route_phone_observations

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs_v25"


def write(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_admission(task):
    output = OUT / task
    binding = json.loads((output / "target_binding_audit.json").read_text(encoding="utf-8"))
    from .binding import BoundTarget
    bound = BoundTarget(**binding["bound_target"]) if binding["bound_target"] else None
    fusion = fuse_video(task, bound)
    inputs, hashes = v21_inputs(task)
    if fusion["v21_hashes"] != hashes:
        raise ValueError("Fusion/stream inputs differ")
    stream = CandidateStream()
    if fusion["status"] == "COMPLETE":
        by_frame = route_phone_observations(inputs, fusion)
        for info in inputs["video_metadata.json"]["sampled_frames"]:
            frame = info["frame_index"]
            for obs in sorted(by_frame[frame], key=lambda o: (o["bbox"][0], o["raw_detection_index"])):
                if obs["target_association"]:
                    stream.events.append({"frame_index": frame, "timestamp": obs["timestamp"],
                                          "raw_detection_index": obs["raw_detection_index"],
                                          "source_track_id": obs["source_track_id"],
                                          "semantic_class": "cell phone", "admitted": True,
                                          "candidate_id": None, "entity_id": "phone_01",
                                          "reid_evaluated": False, "reid_decision": None,
                                          "reason": obs["target_association_reason"]})
                else:
                    stream.admit(obs)
            stream.finish_frame(frame)
    registry = fusion["registry"]
    registry_json = {"task": task, "target_entity_id": "phone_01" if registry else None,
                     "entities": list(registry.entities.values()) if registry else [],
                     "track_to_entity": registry.track_to_entity if registry else {},
                     "sam_to_entity": registry.sam_to_entity if registry else {},
                     "fusion_audit": registry.audit if registry else [],
                     "v21_input_sha256": hashes,
                     "sam_log_sha256": sha256(output / "sam" / "sam_continuity_log.json") if bound else None,
                     "gt_accessed": False}
    timeline = {"task": task, "phone_timeline": fusion["phone_timeline"],
                "candidate_lifecycles": [{"candidate_id": c.candidate_id,
                                          "first_frame": c.observations[0]["frame_index"],
                                          "last_frame": c.observations[-1]["frame_index"],
                                          "status": c.status} for c in stream.candidates.values()],
                "gt_accessed": False}
    write(output / "candidate_stream.json", stream.as_json())
    write(output / "candidate_grouping_audit.json", {"decisions": stream.grouping_audit,
                                                     "candidates": [c.summary() for c in stream.candidates.values()]})
    write(output / "entity_registry.json", registry_json)
    write(output / "identity_timeline.json", timeline)
    return fusion, stream
