"""Measure all frozen V292 unavailable requests before changing eligibility."""
from collections import Counter
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "outputs_v292"
OUT = ROOT / "outputs_v293"
VIDEOS = [f"test{i}" for i in range(1, 10)]
TAXONOMY = ["DENSE_MASK_ARTIFACT_LOST", "TRUSTED_REINIT_SEED_OMITTED", "WINDOW_HAS_NO_TRUSTED_TARGET",
    "NO_TARGET_BEFORE", "NO_ANCHOR_BEFORE", "NO_TARGET_DURING", "NO_ANCHOR_DURING",
    "NO_TRANSITION_EVIDENCE", "NO_ANCHOR_AFTER", "TARGET_AFTER_REQUIRED_BUT_NOT_VISIBLE",
    "TARGET_CONTINUITY_BROKEN", "MASK_UNAVAILABLE", "MASK_UNTRUSTWORTHY", "ANCHOR_NOT_AUTHORIZED",
    "PAIR_NEVER_COVISIBLE", "SCENE_BREAK", "WINDOW_COVERAGE_INSUFFICIENT", "ANCHOR_EVIDENCE_MISSING", "OTHER"]

def read(path, default=None):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).is_file() else default

def write(path, data):
    path = Path(path)
    if OUT.resolve() not in path.resolve().parents:
        raise ValueError("V293 artifacts must remain inside outputs_v293")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def run_audit():
    from memory_graph.v292.finalize import verify_frozen_predictions
    verified = verify_frozen_predictions(BASE)
    if not verified["valid"]:
        raise RuntimeError("Frozen V292 hash validation failed")
    records = []
    for video in VIDEOS:
        folder = BASE / video
        refs = read(folder / "segmentation/mask_references.json", [])
        events = {e["event_id"]: e for e in read(folder / "events/selected_events.json", [])}
        for request in read(folder / "vlm/pair_requests.json", []):
            if request["status"] != "EVIDENCE_UNAVAILABLE":
                continue
            event = events[request["event_id"]]
            dense_dir = folder / "events/dense" / event["event_id"]
            dense = read(dense_dir / "dense_observations.json", {})
            rows = dense["rows"]
            rles = read(dense_dir / "target_masks.json", {})
            trusted = [r for r in refs if r["trusted"] and event["start_frame"] <= r["frame"] <= event["end_frame"]]
            latent = [r for r in rows if r.get("sam_phone") and r["sam_phone"].get("trusted")]
            reasons = []
            if latent and not rles:
                primary = "DENSE_MASK_ARTIFACT_LOST"
            elif any(r["source_kind"] == "reinitialized" for r in trusted) and dense.get("seed") is None:
                primary = "TRUSTED_REINIT_SEED_OMITTED"
            else:
                primary = "WINDOW_HAS_NO_TRUSTED_TARGET" if not latent else "OTHER"
            phase_counts = {}
            for phase, lo, hi in [("BEFORE", event["start_frame"], event["peak_frame"]-4),
                                  ("DURING", event["peak_frame"]-3, event["peak_frame"]+3),
                                  ("AFTER", event["peak_frame"]+4, event["end_frame"])]:
                phase_rows = [r for r in rows if lo <= r["frame"] <= hi]
                target = sum(bool(r.get("identity_authorized")) for r in phase_rows)
                anchor = sum(any(a["anchor_key"] == request["anchor_key"] for a in r.get("anchors", [])) for r in phase_rows)
                phase_counts[phase] = {"rows": len(phase_rows), "target_usable": target, "anchor_present": anchor,
                    "latent_trusted_sam": sum(r in latent for r in phase_rows)}
                if not target:
                    reasons.append("TARGET_AFTER_REQUIRED_BUT_NOT_VISIBLE" if phase == "AFTER" else f"NO_TARGET_{phase}")
                if not anchor:
                    reasons.append(f"NO_ANCHOR_{phase}")
            if not rles: reasons.append("MASK_UNAVAILABLE")
            if not any(r.get("identity_authorized") and any(a["anchor_key"] == request["anchor_key"] for a in r.get("anchors", [])) for r in rows):
                reasons.append("PAIR_NEVER_COVISIBLE")
            if any(r.get("sam_phone") and r["sam_phone"].get("sam_status") == "DRIFT_REJECTED" for r in rows):
                reasons.append("MASK_UNTRUSTWORTHY")
            if not dense["sampling"].get("requested_interval_fully_covered", False):
                reasons.append("WINDOW_COVERAGE_INSUFFICIENT")
            records.append({"video_id": video, "event_id": event["event_id"], "anchor_id": request["anchor_key"],
                "primary_failure_reason": primary, "secondary_reasons": reasons, "phase_counts": phase_counts,
                "latent_trusted_sam_frames": [r["frame"] for r in latent], "persisted_rle_count": len(rles),
                "frozen_trusted_masks_in_window": len(trusted), "dense_seed": dense.get("seed"),
                "scene_continuity": "NOT_MEASURED_IN_V292", "provenance": str(dense_dir.relative_to(ROOT))})
    per_video = {v: dict(Counter(r["primary_failure_reason"] for r in records if r["video_id"] == v)) for v in VIDEOS}
    result = {"schema": "v293_baseline_audit_1", "upstream_frozen_hashes_valid": True, "taxonomy": TAXONOMY,
        "total_requests": len(records), "primary_counts": dict(Counter(r["primary_failure_reason"] for r in records)),
        "secondary_counts": dict(Counter(reason for r in records for reason in r["secondary_reasons"])),
        "per_video": per_video, "requests": records,
        "code_findings": ["V292 _authorize_dense_rows reads video_root/target_masks.json instead of events/dense/event/target_masks.json, then overwrites the event RLE with an empty mapping.",
            "V292 accepted_masks includes only target_full; authorized reinitialized masks are omitted.",
            "V292 pair rows discard all non-authorized target frames before anchor/AFTER assessment.",
            "V292 fixed peak +/-3 phase partition and both-visible requirement hide independent anchor coverage."]}
    write(OUT / "evidence_failure_audit.json", result)
    lines = ["# V2.9.2 unavailable evidence audit", "", f"Audited {len(records)} unavailable requests before eligibility changes.",
             "", "## Primary causes", ""] + [f"- {k}: {v}" for k,v in result["primary_counts"].items()]
    lines += ["", "## Per video", "", "| Video | Primary failure counts |", "|---|---|"]
    lines += [f"| {v} | {json.dumps(counts)} |" for v,counts in per_video.items()]
    lines += ["", "## Independent phase / mask findings", ""] + [f"- {k}: {v}" for k,v in result["secondary_counts"].items()]
    lines += ["", "Secondary counts overlap. Missing target authorization does not establish physical absence. Scene continuity was not measured by V292.", "", *result["code_findings"]]
    (OUT / "evidence_failure_audit.md").write_text("\n".join(lines), encoding="utf-8")
    return result
