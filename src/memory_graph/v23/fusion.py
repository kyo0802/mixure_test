"""Conservative YOLO/SAM evidence fusion; this module never imports GT."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import defaultdict
from pathlib import Path
import json
import math

from memory_graph.v22.sam_tracking import ROOT, box_iou, frozen_inputs, read_json, sha256


@dataclass(frozen=True)
class Observation:
    source: str
    frame_index: int
    timestamp: float
    source_object_id: str
    bbox: list[float]
    semantic_label: str | None
    detector_confidence: float | None
    mask_ref: str | None
    observation_quality: str | None
    provenance: str


def sam_guard(sam: Observation, diagnostics: dict, raw_phone_boxes: list[list[float]]):
    """Hard contradiction first; no GT, class-only match, or fitted score."""
    overlaps = [(box_iou(sam.bbox, box), box) for box in raw_phone_boxes]
    near = [(iou, box) for iou, box in overlaps if iou >= .05]
    if near:
        iou, box = max(near, key=lambda pair: pair[0])
        sam_area = (sam.bbox[2] - sam.bbox[0]) * (sam.bbox[3] - sam.bbox[1])
        raw_area = (box[2] - box[0]) * (box[3] - box[1])
        ratio = sam_area / raw_area if raw_area else math.inf
        if iou < .30 and ratio > 3:
            return "REJECT_PROPAGATION", {"reason": "near phone YOLO box contradicts expanded SAM bbox", "max_iou": iou, "bbox_area_ratio_to_yolo": ratio}
    if diagnostics.get("possible_mask_drift"):
        return "UNCERTAIN_PROPAGATION", {"reason": "fixed SAM area/motion drift flag", "max_iou": max((x[0] for x in overlaps), default=None)}
    return "ACCEPT_PROPAGATION", {"reason": "no hard contradiction", "max_iou": max((x[0] for x in overlaps), default=None)}


class EntityRegistry:
    def __init__(self, target_track_id: int, v21_track_groups: dict[int, str]):
        self.target_track_id = target_track_id
        self.v21_track_groups = v21_track_groups
        self.entities: dict[str, dict] = {}
        self.track_to_entity: dict[int, str] = {}
        self.group_to_entity: dict[str, str] = {}
        self.sam_to_entity: dict[str, str] = {}
        self.audit: list[dict] = []
        self.next_id = 1
        self.next_candidate = 1
        self.current_frame = -1
        self.current_time = 0.

    def _new(self, entity_id, obs: Observation, provisional=False):
        self.entities[entity_id] = {"entity_id": entity_id, "semantic_label": obs.semantic_label or "unknown",
            "state": "UNOBSERVED", "first_seen": obs.timestamp, "last_seen": obs.timestamp,
            "last_trusted_seen": None, "latest_trusted_observation": None,
            "yolo_sources": [], "sam_sources": [], "appearance_memory": [],
            "observation_history": [], "association_history": [],
            "anchor_candidate": "unknown", "anchor_evidence": {},
            "uncertainty": [], "provisional": provisional}
        return entity_id

    def _id(self):
        value = f"entity_{self.next_id:04d}"
        self.next_id += 1
        return value

    def _record(self, obs, candidate_ids, decision, entity_id, reason, semantic=None, spatial=None,
                temporal=None, contradictions=None, appearance=None, graph_context=None):
        item = {"frame_index": obs.frame_index, "timestamp": obs.timestamp, "observation_source": obs.source,
                "source_object_id": obs.source_object_id, "candidate_entity_ids": candidate_ids,
                "semantic_evidence": semantic, "spatial_evidence": spatial,
                "appearance_evidence": appearance, "temporal_evidence": temporal,
                "graph_context_evidence": graph_context, "contradictions": contradictions or [],
                "decision": decision, "entity_id": entity_id, "reason": reason}
        self.audit.append(item)
        if entity_id is not None:
            self.entities[entity_id]["association_history"].append(item)
        return item

    def begin_frame(self, frame, timestamp):
        self.current_frame = frame
        self.current_time = timestamp
        for entity in self.entities.values():
            entity["state"] = "UNOBSERVED"

    def _attach(self, entity_id, obs: Observation, state, trusted):
        entity = self.entities[entity_id]
        entity["state"] = state
        entity["last_seen"] = obs.timestamp
        entity["observation_history"].append({**asdict(obs), "trusted": trusted, "state": state})
        source_list = "yolo_sources" if obs.source.startswith("yolo") else "sam_sources"
        if obs.source_object_id not in entity[source_list]:
            entity[source_list].append(obs.source_object_id)
        if trusted:
            entity["last_trusted_seen"] = obs.timestamp
            entity["latest_trusted_observation"] = asdict(obs)
        if entity["semantic_label"] == "unknown" and obs.semantic_label:
            entity["semantic_label"] = obs.semantic_label
        self._anchor_metadata(entity)

    def _anchor_metadata(self, entity):
        label = entity["semantic_label"]
        stable = label in {"chair", "dining table", "table", "microwave", "refrigerator", "couch", "tv"}
        count = sum(o["source"] == "yolo_track" for o in entity["observation_history"])
        entity["anchor_candidate"] = True if stable and count >= 3 else False if label in {"cell phone", "person", "sports ball"} else "unknown"
        entity["anchor_evidence"] = {"semantic_suitability": stable, "trusted_yolo_observations": count,
                                      "world_fixed_claim": False}

    def observe_yolo(self, obs: Observation, track_id: int, accepted_sam: list[tuple[str, Observation]]):
        if track_id in self.track_to_entity:
            entity_id = self.track_to_entity[track_id]
            decision = "MATCH"
            reason = "existing local track mapping"
            spatial = None
        else:
            matches = [(entity_id, box_iou(obs.bbox, sam.bbox)) for entity_id, sam in accepted_sam
                       if obs.semantic_label == "cell phone" and box_iou(obs.bbox, sam.bbox) >= .30]
            matches.sort(key=lambda x: -x[1])
            if len(matches) == 1 or len(matches) > 1 and matches[0][1] - matches[1][1] >= .20:
                entity_id, score = matches[0]
                decision, reason, spatial = "MATCH", "same-frame YOLO/SAM spatial and semantic support", {"iou": score}
            elif len(matches) > 1:
                entity_id, decision, reason, spatial = None, "AMBIGUOUS", "multiple SAM hypotheses overlap", {"candidates": matches}
            elif track_id == self.target_track_id:
                entity_id, decision, reason, spatial = "phone_01", "NEW_ENTITY", "selected YOLO target establishes registry identity", None
            else:
                group = self.v21_track_groups.get(track_id)
                entity_id = self.group_to_entity.get(group) if group else None
                if entity_id:
                    decision, reason = "MATCH", "frozen V2.1 conservative identity hypothesis"
                else:
                    entity_id, decision, reason = self._id(), "NEW_ENTITY", "new YOLO local object hypothesis"
                    if group:
                        self.group_to_entity[group] = entity_id
                spatial = None
            if entity_id is not None:
                self.track_to_entity[track_id] = entity_id
        if entity_id is None:
            self._record(obs, [x[0] for x in matches], decision, None, reason,
                         semantic=obs.semantic_label, spatial=spatial)
            return None
        if entity_id not in self.entities:
            self._new(entity_id, obs)
        # A later V2.1 group may contain more track IDs. Keep the registry choice.
        group = self.v21_track_groups.get(track_id)
        if group and group not in self.group_to_entity:
            self.group_to_entity[group] = entity_id
        self._attach(entity_id, obs, "VISIBLE_TRUSTED", trusted=True)
        self._record(obs, [entity_id], decision, entity_id, reason, semantic=obs.semantic_label,
                     spatial=spatial, temporal={"source_track_id": track_id})
        return entity_id

    def observe_sam(self, obs: Observation, diagnostics: dict, raw_phone_boxes: list[list[float]],
                    initializing: bool):
        target = obs.source_object_id
        if target not in self.sam_to_entity:
            if target.startswith("late_candidate_"):
                entity_id = f"candidate_phone_{self.next_candidate:02d}"
                self.next_candidate += 1
                self._new(entity_id, obs, provisional=True)
                decision, reason = "NEW_ENTITY", "late YOLO-supported candidate kept separate; original phone association unresolved"
                self._record(obs, ["phone_01"], "AMBIGUOUS", None,
                             "long gap and multiple phone candidates; do not force re-identification",
                             semantic="cell phone", temporal={"long_gap": True})
            else:
                entity_id = self.track_to_entity.get(self.target_track_id)
                if entity_id is None:
                    raise ValueError("SAM target initialized before trusted YOLO entity")
                decision, reason = "MATCH", "SAM target inherits selected YOLO entity hypothesis"
            self.sam_to_entity[target] = entity_id
        else:
            entity_id = self.sam_to_entity[target]
            decision, reason = "MATCH", "SAM target retains inherited entity hypothesis"
        guard, evidence = sam_guard(obs, diagnostics, raw_phone_boxes)
        if guard == "REJECT_PROPAGATION":
            self.entities[entity_id]["state"] = "CONFLICT"
            self.entities[entity_id]["uncertainty"].append({"frame_index": obs.frame_index, "reason": evidence})
            self._record(obs, [entity_id], "CONFLICT", entity_id, evidence["reason"],
                         semantic="cell phone", spatial=evidence,
                         temporal={"inherited_target": target}, contradictions=[evidence["reason"]])
            return None
        if guard == "UNCERTAIN_PROPAGATION":
            self.entities[entity_id]["state"] = "AMBIGUOUS"
            self.entities[entity_id]["uncertainty"].append({"frame_index": obs.frame_index, "reason": evidence})
            self._record(obs, [entity_id], "AMBIGUOUS", entity_id, evidence["reason"],
                         semantic="cell phone", spatial=evidence, temporal={"inherited_target": target})
            return None
        state = "VISIBLE_PROPAGATED"
        self._attach(entity_id, obs, state, trusted=False)
        self._record(obs, [entity_id], decision, entity_id, reason,
                     semantic="cell phone", spatial=evidence, temporal={"inherited_target": target})
        return entity_id, obs

    def confirm_raw_yolo(self, detection: dict, sam_attached: list[tuple[str, Observation]]):
        if detection["class_name"] != "cell phone":
            return
        matches = [(eid, box_iou(detection["bbox"], sam.bbox)) for eid, sam in sam_attached
                   if box_iou(detection["bbox"], sam.bbox) >= .3]
        if len(matches) != 1:
            return
        eid, overlap = matches[0]
        obs = Observation("yolo_raw", detection["frame_index"], detection["timestamp"],
                          f"raw:{detection['frame_index']}:{round(detection['bbox'][0])}", detection["bbox"],
                          "cell phone", detection["confidence"], None, "raw_detection", "frozen_v21_detections")
        self._attach(eid, obs, "VISIBLE_TRUSTED", trusted=True)
        self._record(obs, [eid], "MATCH", eid, "raw YOLO phone box confirms inherited SAM hypothesis",
                     semantic="cell phone", spatial={"iou": overlap})

    def graph_snapshot(self, frame, timestamp):
        nodes = [{"entity_id": e["entity_id"], "semantic_label": e["semantic_label"], "state": e["state"],
                  "current_evidence_source": e["observation_history"][-1]["source"] if e["observation_history"] and e["observation_history"][-1]["frame_index"] == frame else None,
                  "anchor_candidate": e["anchor_candidate"]} for e in self.entities.values()]
        active = [e for e in self.entities.values() if e["state"] in {"VISIBLE_TRUSTED", "VISIBLE_PROPAGATED"}
                  and e["observation_history"] and e["observation_history"][-1]["frame_index"] == frame]
        edges = []
        for i, a in enumerate(active):
            for b in active[i + 1:]:
                aa = a["observation_history"][-1]["bbox"]
                bb = b["observation_history"][-1]["bbox"]
                ca = ((aa[0] + aa[2]) / 2, (aa[1] + aa[3]) / 2)
                cb = ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
                if math.dist(ca, cb) < .12 * math.hypot(1280, 720):
                    edges.append({"subject_entity_id": a["entity_id"], "object_entity_id": b["entity_id"],
                                  "predicate": "IMAGE_NEAR", "reference_frame": "image_plane"})
        return {"frame_index": frame, "timestamp": timestamp, "nodes": nodes, "edges": edges,
                "active_visible_entities": [e["entity_id"] for e in active],
                "unobserved_remembered_entities": [e["entity_id"] for e in self.entities.values() if e["state"] == "UNOBSERVED"]}

    def get_entity_context(self, entity_id, snapshot=None):
        if entity_id not in self.entities:
            raise KeyError(entity_id)
        snapshot = snapshot or self.graph_snapshot(self.current_frame, self.current_time)
        nearby = [e["object_entity_id"] if e["subject_entity_id"] == entity_id else e["subject_entity_id"]
                  for e in snapshot["edges"] if entity_id in {e["subject_entity_id"], e["object_entity_id"]}]
        return {"entity_id": entity_id, "nearby_entity_ids": nearby,
                "anchor_candidate": self.entities[entity_id]["anchor_candidate"],
                "reference_frame": "image_plane"}


def load_inputs(task):
    v21, hashes = frozen_inputs(task)
    base = ROOT / "outputs_v21" / task
    manifest = read_json(base / "prediction_manifest.json")
    for name in ("persistent_entities.json", "track_entity_associations.json"):
        if sha256(base / name) != manifest[name]:
            raise ValueError(f"V2.1 source changed: {name}")
    v21_entities = read_json(base / "persistent_entities.json")
    groups = {track: e["entity_id"] for e in v21_entities for track in e["local_track_ids"]}
    sam_path = ROOT / "outputs_v22" / task / "tracking_ab" / "sam_propagation_log.json"
    sam = read_json(sam_path)
    if sam["frozen_input_sha256"] != hashes:
        raise ValueError("V2.2 SAM source does not match frozen V2.1 inputs")
    return v21, sam, groups, {"v21": hashes, "sam_log_sha256": sha256(sam_path)}


def run(task):
    v21, sam, groups, provenance = load_inputs(task)
    target_track = 17 if task == "task1" else 22
    registry = EntityRegistry(target_track, groups)
    tracks_by_frame = defaultdict(list)
    for track in v21["track_timelines.json"]:
        for o in track["observations"]:
            tracks_by_frame[o["frame_index"]].append((track["track_id"], o))
    raw_by_frame = defaultdict(list)
    for d in v21["detections.json"]:
        raw_by_frame[d["frame_index"]].append(d)
    sam_by_frame = defaultdict(list)
    sam_initial = set()
    for segment in sam["segments"]:
        for event in segment["events"]:
            if event["type"] == "INIT":
                sam_initial.add((event["frame_index"], event["object_id"]))
        for o in segment["observations"]:
            sam_by_frame[o["frame_index"]].append(o)
    representatives = ({0, 240, 348, 360, 408, 420, 720} if task == "task1" else
                       {0, 78, 144, 288, 306, 312, 528, 594, 660})
    snapshots = []
    phone_states = []
    for info in v21["video_metadata.json"]["sampled_frames"]:
        frame, timestamp = info["frame_index"], info["timestamp"]
        registry.begin_frame(frame, timestamp)
        phone_boxes = [d["bbox"] for d in raw_by_frame[frame] if d["class_name"] == "cell phone"]
        # The target is already created from its YOLO local track before its SAM seed.
        if frame == (240 if task == "task1" else 78) and "phone_01" not in registry.entities:
            selected = next((o for tid, o in tracks_by_frame[frame] if tid == target_track), None)
            if selected is None:
                raise ValueError("selected YOLO target unavailable at SAM seed")
            obs = Observation("yolo_track", frame, timestamp, f"track:{target_track}", selected["bbox"],
                              selected["class_name"], selected["confidence"], None, "trusted_local", "frozen_v21_track")
            registry.observe_yolo(obs, target_track, [])
        accepted = []
        for s in sam_by_frame[frame]:
            obs = Observation("sam", frame, timestamp, s["object_id"], s["bbox"], "cell phone", None,
                              f"outputs_v22/{task}/tracking_ab/sam_propagation_log.json#{frame}:{s['object_id']}",
                              "fixed_v22_diagnostics", "official_sam2.1_frozen_v22")
            result = registry.observe_sam(obs, s["diagnostics"], phone_boxes,
                                          (frame, s["object_id"]) in sam_initial)
            if result is not None:
                accepted.append(result)
        for track_id, y in sorted(tracks_by_frame[frame]):
            obs = Observation("yolo_track", frame, timestamp, f"track:{track_id}", y["bbox"],
                              y["class_name"], y["confidence"], None, "trusted_local", "frozen_v21_track")
            registry.observe_yolo(obs, track_id, accepted)
        for d in raw_by_frame[frame]:
            registry.confirm_raw_yolo(d, accepted)
        phone = registry.entities.get("phone_01")
        phone_states.append({"frame_index": frame, "timestamp": timestamp, "state": phone["state"] if phone else None,
                             "raw_phone_boxes": len(phone_boxes),
                             "sam_initial_present": any(s["segment"] == "initial" for s in sam_by_frame[frame])})
        if frame in representatives:
            snapshots.append(registry.graph_snapshot(frame, timestamp))
    return {"task": task, "registry": registry, "snapshots": snapshots, "phone_states": phone_states,
            "provenance": provenance}
