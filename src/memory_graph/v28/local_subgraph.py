"""Build stable, connected Hop 0/1/2 local spatial structure from trusted observations."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict

from .geometry import bbox_features
from .models import Config, SpatialSegment
from .roles import context_compatible, primary_compatible, semantic_roles


def _target(frame: dict, target_id: str):
    rows = [o for o in frame["observations"] if o.entity_id == target_id and o.trusted]
    return max(rows, key=lambda o: (o.identity == "CONFIRMED_MATCH", o.confidence or 0), default=None)


def _split(rows: list[dict], config: Config) -> list[list[dict]]:
    groups = []
    for row in sorted(rows, key=lambda x: (x["time"], x["frame"])):
        if not groups or row["time"] - groups[-1][-1]["time"] > config.maximum_support_gap_seconds:
            groups.append([row])
        elif row["frame"] != groups[-1][-1]["frame"]:
            groups[-1].append(row)
    return [group for group in groups if len(group) >= config.minimum_support_frames
            and group[-1]["time"] - group[0]["time"] >= config.minimum_support_seconds]


def _order(segment: SpatialSegment) -> tuple:
    duration = segment.end_time - segment.start_time
    distances = [o["geometry"]["normalized_center_distance"] for o in segment.observations]
    stability = max(distances) - min(distances) if distances else 1.0
    return (-segment.end_time, -duration, stability, segment.object)


def build_local_subgraph(frames: list[dict], size: tuple[int, int], config: Config | None = None,
                         interaction_entities: set[str] | None = None) -> dict:
    config = config or Config()
    interaction_entities = interaction_entities or set()
    by_frame = {row["frame"]: row for row in frames}
    pair_rows = defaultdict(list)
    identity_audit = []
    for frame in frames:
        target = _target(frame, config.target_id)
        for observation in frame["observations"]:
            identity_audit.append({"frame": frame["frame"], "observation_id": observation.observation_id,
                                   "identity": observation.identity,
                                   "memory_update_authorized": bool(observation is target)})
        if target is None:
            continue
        for anchor in frame["anchors"]:
            if not anchor.trusted or anchor.entity_id == config.target_id:
                continue
            geometry = bbox_features(target.bbox, anchor.bbox, size)
            local = (geometry["normalized_center_distance"] <= config.primary_local_distance_fraction
                     or geometry["box_gap_fraction"] <= config.primary_gap_fraction
                     or geometry["bbox_iou"] > 0)
            if not local or not primary_compatible(anchor.label, anchor.entity_id in interaction_entities):
                continue
            pair_rows[anchor.entity_id].append({
                "frame": frame["frame"], "time": frame["time"], "target_bbox": list(target.bbox),
                "anchor_bbox": list(anchor.bbox), "target_observation": target.observation_id,
                "anchor_observation": anchor.observation_id, "target_identity": target.identity,
                "anchor_identity": anchor.identity, "raw_label": anchor.label, "geometry": geometry,
                "target_mask_ref": None, "anchor_remains_visible": True,
                "interaction_evidence": anchor.entity_id in interaction_entities,
            })
    primary_segments = []
    for entity_id in sorted(pair_rows):
        for group in _split(pair_rows[entity_id], config):
            primary_segments.append(SpatialSegment(
                "", config.target_id, entity_id, 1, group[0]["frame"], group[-1]["frame"],
                group[0]["time"], group[-1]["time"], [r["frame"] for r in group],
                [r["time"] for r in group], group[-1]["raw_label"], semantic_roles(group[-1]["raw_label"]), group))
    primary_segments.sort(key=lambda s: (s.start_frame, *_order(s)))
    for index, segment in enumerate(primary_segments, 1):
        segment.segment_id = f"P{index:04d}"

    # Expand around each primary only while that primary segment is supported.
    context_segments = []
    primary_entities = {s.object for s in primary_segments}
    for primary in primary_segments:
        rows = defaultdict(list)
        for frame_index in primary.support_frames:
            frame = by_frame[frame_index]
            primary_obs = next((a for a in frame["anchors"] if a.entity_id == primary.object and a.trusted), None)
            if primary_obs is None:
                continue
            for context in frame["anchors"]:
                if (not context.trusted or context.entity_id in {config.target_id, primary.object}
                        or context.entity_id in primary_entities or not context_compatible(context.label)):
                    continue
                geometry = bbox_features(primary_obs.bbox, context.bbox, size)
                local = (geometry["normalized_center_distance"] <= config.context_local_distance_fraction
                         or geometry["box_gap_fraction"] <= config.context_gap_fraction
                         or geometry["bbox_iou"] > 0)
                if local:
                    rows[context.entity_id].append({
                        "frame": frame_index, "time": frame["time"], "target_bbox": list(primary_obs.bbox),
                        "anchor_bbox": list(context.bbox), "target_observation": primary_obs.observation_id,
                        "anchor_observation": context.observation_id, "raw_label": context.label, "geometry": geometry})
        candidates = []
        for entity_id in sorted(rows):
            for group in _split(rows[entity_id], config):
                candidates.append(SpatialSegment(
                    "", primary.object, entity_id, 2, group[0]["frame"], group[-1]["frame"],
                    group[0]["time"], group[-1]["time"], [r["frame"] for r in group],
                    [r["time"] for r in group], group[-1]["raw_label"], semantic_roles(group[-1]["raw_label"]),
                    group, via_primary=primary.object))
        for segment in sorted(candidates, key=_order)[:config.maximum_context_per_primary]:
            context_segments.append(segment)
    context_segments.sort(key=lambda s: (s.start_frame, s.via_primary or "", *_order(s)))
    for index, segment in enumerate(context_segments, 1):
        segment.segment_id = f"C{index:04d}"

    nodes = {config.target_id: {"entity_id": config.target_id, "raw_label": "cell phone",
                                "semantic_roles": ["TARGET"], "hop": 0, "via_primary": None}}
    edges = []
    for segment in primary_segments:
        nodes.setdefault(segment.object, {"entity_id": segment.object, "raw_label": segment.raw_label,
                                         "semantic_roles": segment.semantic_roles, "hop": 1, "via_primary": None})
        edges.append({"source": config.target_id, "relation": "TRUSTED_ANCHOR_CONTEXT", "target": segment.object,
                      "kind": "IMAGE_CONTEXT", "segment_id": segment.segment_id,
                      "start_frame": segment.start_frame, "end_frame": segment.end_frame,
                      "status": segment.status, "physical_verification": False})
    for segment in context_segments:
        nodes.setdefault(segment.object, {"entity_id": segment.object, "raw_label": segment.raw_label,
                                         "semantic_roles": segment.semantic_roles, "hop": 2,
                                         "via_primary": segment.via_primary})
        edges.append({"source": segment.via_primary, "relation": "IMAGE_NEAR_CONTEXT", "target": segment.object,
                      "kind": "IMAGE_CONTEXT", "segment_id": segment.segment_id,
                      "start_frame": segment.start_frame, "end_frame": segment.end_frame,
                      "status": segment.status, "physical_verification": False})
    return {"schema": "v28_local_subgraph_1", "target": config.target_id,
            "nodes": [nodes[key] for key in sorted(nodes, key=lambda k: (nodes[k]["hop"], k))],
            "edges": edges, "primary_segments": [asdict(s) for s in primary_segments],
            "context_segments": [asdict(s) for s in context_segments], "identity_audit": identity_audit,
            "limits": {"primary_per_snapshot": config.maximum_primary_anchors,
                       "context_per_primary": config.maximum_context_per_primary}}
