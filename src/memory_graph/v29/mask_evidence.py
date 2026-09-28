"""Join frozen SAM2.1 RLE to the exact V2.6 fusion and identity decisions."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json

from memory_graph.v27.pipeline import ROOT


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def authorize_mask(observation: dict, audit: dict | None, identity: dict | None,
                   rle: dict | None, reference: str) -> dict:
    """Segmentation acceptance and contemporaneous entity authorization are independent."""
    frame, object_id = observation["frame_index"], observation["object_id"]
    reasons = []
    if not rle or not rle.get("starts"):
        reasons.append("MASK_NOT_GENERATED")
    if observation.get("diagnostics", {}).get("possible_mask_drift"):
        reasons.append("MASK_REJECTED_DRIFT")
    if audit is None or audit.get("decision") not in {"MATCH", "NEW_ENTITY"}:
        reasons.append("MASK_REJECTED_BY_FUSION")
    if audit is None or audit.get("entity_id") != "phone_01" or object_id != "phone_target":
        reasons.append("IDENTITY_NOT_AUTHORIZED")
    if identity is None or not identity.get("accepted_sam_target") or identity.get("state") not in {"VISIBLE_PROPAGATED", "VISIBLE_TRUSTED"}:
        reasons.append("IDENTITY_NOT_AUTHORIZED_AT_FRAME")
    # V2.6 explicitly marks SAM-only history untrusted. V2.9 authorizes shape
    # evidence through the accepted fusion decision, not by mutating that history.
    area = observation.get("mask_area", 0)
    shape = rle.get("shape") if rle else None
    return {"entity_id": "phone_01" if not reasons else None, "frame": frame,
            "time": observation["timestamp"], "mask_source": "SAM2.1", "mask_reference": reference,
            "mask_bbox": observation.get("bbox"), "mask_area": area,
            "normalized_mask_area": area / (shape[0] * shape[1]) if shape else None,
            "visible_area_ratio": None, "mask_centroid": observation.get("center"),
            "identity_authorization": identity.get("state") if identity else None,
            "sam_status": audit.get("decision") if audit else "MISSING_AUDIT",
            "trusted": not reasons, "rejection_reason": ";".join(reasons) if reasons else None,
            "diagnostics": observation.get("diagnostics", {}),
            "provenance": [reference, f"outputs_v26/{reference.split('/')[1]}/entity_registry.json#fusion_audit",
                           f"outputs_v26/{reference.split('/')[1]}/identity_timeline.json#{frame}"]}


def load_video_masks(task: str) -> tuple[list[dict], dict]:
    sam_path = ROOT / f"outputs_v25_rerun/{task}/sam/sam_continuity_log.json"
    reg_path = ROOT / f"outputs_v26/{task}/entity_registry.json"
    timeline_path = ROOT / f"outputs_v26/{task}/identity_timeline.json"
    if not sam_path.exists():
        return [], {"task": task, "status": "MASK_NOT_GENERATED", "existing_sam_mask_files": []}
    sam, reg, timeline = read(sam_path), read(reg_path), read(timeline_path)
    audit = {(a["frame_index"], a["source_object_id"]): a for a in reg["fusion_audit"]
             if a["observation_source"] == "sam"}
    identity = {x["frame_index"]: x for x in timeline["phone_timeline"]}
    phone = next((e for e in reg["entities"] if e["entity_id"] == "phone_01"), {})
    yolo_reauthorized = {o["frame_index"] for o in phone.get("observation_history", [])
                         if o.get("trusted") and o.get("source") in {"yolo_track", "yolo_raw"}}
    rows = []
    for segment in sam["segments"]:
        masks = segment.get("masks_rle", {})
        previous_frame = None
        continuity_ok = True
        for obs in segment["observations"]:
            frame, oid = obs["frame_index"], obs["object_id"]
            key = f"{frame}:{oid}"
            ref = f"outputs_v25_rerun/{task}/sam/sam_continuity_log.json#{key}"
            row = authorize_mask(obs, audit.get((frame, oid)), identity.get(frame), masks.get(key), ref)
            if previous_frame is not None and frame-previous_frame > 12:
                continuity_ok = False
            if frame in yolo_reauthorized:
                continuity_ok = True
            if not continuity_ok:
                row["trusted"] = False
                row["entity_id"] = None
                row["rejection_reason"] = ";".join(filter(None, [row["rejection_reason"], "SAM_CONTINUITY_GAP_NOT_REAUTHORIZED"]))
            if row["rejection_reason"] and "MASK_REJECTED" in row["rejection_reason"]:
                continuity_ok = False
            previous_frame = frame
            rows.append(row)
    rows.sort(key=lambda x: (x["frame"], x["mask_reference"]))
    last = None
    for row in rows:
        if row["trusted"]:
            row["visible_area_ratio"] = row["mask_area"] / last if last else 1.0
            last = row["mask_area"]
    counts = Counter(row["rejection_reason"] or "TRUSTED" for row in rows)
    return rows, {"task": task, "status": "MASK_EXISTS_BUT_NOT_CONNECTED" if any(r["trusted"] for r in rows) else "MASK_REJECTED_OR_UNAUTHORIZED",
                  "existing_sam_mask_files": [sam_path.relative_to(ROOT).as_posix()],
                  "sam_observations": len(rows), "accepted_sam_masks": sum(a["decision"] in {"MATCH", "NEW_ENTITY"} for a in audit.values()),
                  "rejected_sam_masks": sum(a["decision"] not in {"MATCH", "NEW_ENTITY"} for a in audit.values()),
                  "identity_authorized_masks": sum(r["trusted"] for r in rows),
                  "trusted_phone_01_masks_available": sum(r["trusted"] for r in rows),
                  "rejection_counts": dict(counts),
                  "missing_link": "V2.6 SAM observation_history has mask_ref but trusted=False; V2.8 only counts trusted registry observations",
                  "new_sam_propagation_required_for_existing_frames": False}
