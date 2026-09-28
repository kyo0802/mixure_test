"""Read-only audit of frozen FindMind outputs; writes only alongside this script."""
from __future__ import annotations
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4*1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def main():
    result = {"audit_date": "2026-09-28", "scope": "read-only frozen artifact checks; no inference", "videos": {}}
    for n in range(1, 10):
        task = f"test{n}"
        p = ROOT / "outputs_v291" / task
        upstream = p if n < 3 else ROOT / "outputs_v26" / task
        timeline = read(upstream / "identity_timeline.json")["phone_timeline"]
        states = {r["frame_index"]: r["state"] for r in timeline}
        stream = read(upstream / "candidate_stream.json")["observations"]
        confirmed = sorted({r["frame_index"] for r in stream if r.get("reid_decision") == "CONFIRMED_MATCH"})
        registry = read(upstream / "entity_registry.json")
        phone = next((e for e in registry["entities"] if e["entity_id"] == "phone_01"), {})
        events = read(p / "events.json")["events"]
        memory = read(p / "object_memory_phone_01.json")
        temporal = read(p / "temporal_memory.json")
        search = read(p / "search_candidates.json")
        anchors = read(p / "anchor_recovery.json")["events"]
        by_event = {(e["event_id"], a["anchor_id"]): a for e in anchors for a in e["anchors"]}
        final_entities = {e["entity_id"]: e for e in memory["entities"]}
        wrong_local_labels = []
        wrong_local_provenance = []
        for key, anchor in by_event.items():
            event, aid = key
            eid = f"event_local::{event}::{aid}"
            final = final_entities.get(eid)
            if final and final["raw_label"] != anchor["normalized_label"]:
                wrong_local_labels.append({"entity": eid, "event_label": anchor["normalized_label"], "memory_label": final["raw_label"]})
            for ep in memory["episodes"]:
                if ep["object"] == eid and ep.get("anchor_provenance") != anchor.get("provenance"):
                    wrong_local_provenance.append({"entity": eid, "episode": ep["episode_id"], "expected": anchor.get("provenance"), "actual": ep.get("anchor_provenance")})
        dense_checks = []
        for event in events:
            folder = p / "dense_windows" / event["event_id"]
            d = read(folder / "dense_observations.json")
            s = d["sampling"]
            dense_checks.append({"event": event["event_id"], "requested": [event["start_frame"], event["end_frame"]],
                "actual": [s["start_frame"], s["end_frame"]], "covers_requested": s["start_frame"] <= event["start_frame"] and s["end_frame"] >= event["end_frame"],
                "cached_from_v29": d.get("cached_from_v29", False), "target_masks_exists": (folder/"target_masks.json").exists(),
                "authorized_rows": sum(bool(r.get("identity_authorized")) for r in d["rows"])})
        vlm = read(p / "vlm_observable_evidence.json")["calls"]
        vlm_same_images = []
        vlm_visual_grounding = []
        grouped = defaultdict(list)
        for c in vlm:
            grouped[c["event_id"]].append(c)
            dense_rows = read(p / "dense_windows" / c["event_id"] / "dense_observations.json")["rows"]
            image_frames = [int(re.search(r"_f(\d+)\.", Path(ip).name).group(1)) for ip in c.get("images", [])]
            selected = [next(r for r in dense_rows if r["frame"] == f) for f in image_frames]
            vlm_visual_grounding.append({"event": c["event_id"], "anchor": c.get("anchor_id"),
                "image_frames": image_frames,
                "images_with_authorized_target_box": sum(bool(r.get("identity_authorized") and r.get("sam_phone")) for r in selected),
                "images_with_queried_anchor": sum(any(a["anchor_id"] == c.get("anchor_id") for a in r.get("recovered_anchors", [])) for r in selected)})
        for eid, calls in grouped.items():
            if len(calls) > 1 and len({tuple(c.get("images", [])) for c in calls}) == 1:
                vlm_same_images.append({"event": eid, "anchors": [c.get("anchor_id") for c in calls]})
        new_eps = [e for e in memory["episodes"] if e["episode_id"].startswith("V291_") and e["kind"] == "PHYSICAL"]
        temporal_ep_ids = {e["episode_id"] for e in temporal.get("episodes", [])}
        redis = read(p / "rediscovery.json")
        decisions = read(p / "physical_relation_decisions.json")
        result["videos"][task] = {
            "summary": read(p / "summary.json"),
            "confirmed_match_frames": confirmed,
            "reconfirm_events": [{"frame": e["peak_frame"], "timeline_state": states.get(e["peak_frame"]),
                "guard_confirmed_same_frame": e["peak_frame"] in confirmed, "source": e["source"],
                "snapshot_state": next((s.get("target_state") for s in temporal["snapshots"] if s.get("snapshot_id") == f"V291_{e['event_id']}"), None)}
                for e in events if e["event_type"] == "RECONFIRM_EVENT"],
            "target_yolo_sources": phone.get("yolo_sources"), "target_sam_sources": phone.get("sam_sources"),
            "track_mappings": {str(i): registry.get("track_to_entity", {}).get(str(i)) for i in ((17,70,58,60) if n==1 else (22,43,78,80,81) if n==2 else ())},
            "new_physical_episodes": len(new_eps),
            "zero_time_new_physical_episodes": sum(e["start_frame"] > 0 and e["start_time"] == 0 and e["last_confirmed_time"] == 0 for e in new_eps),
            "new_physical_episode_statuses": dict(Counter(e["status"] for e in new_eps)),
            "temporal_schema": temporal["schema"],
            "new_physical_episodes_missing_from_temporal_memory": sum(e["episode_id"] not in temporal_ep_ids for e in new_eps) if "episodes" in temporal else None,
            "search_zero_time_count": sum(e.get("last_confirmed_time") == 0 for e in search["candidates"]),
            "anchor_label_mismatches": wrong_local_labels,
            "anchor_provenance_mismatches": wrong_local_provenance,
            "dense_windows": dense_checks,
            "vlm_same_images_for_different_anchors": vlm_same_images,
            "vlm_visual_grounding": vlm_visual_grounding,
            "vlm_summaries": [{"event": c["event_id"], "anchor": c.get("anchor_id"), "status": c["status"],
                "summary": c.get("observable_facts", {}).get("evidence_summary")} for c in vlm],
            "rediscovery_observations": len(redis["candidates"]),
            "rediscovery_unique_candidate_ids": len({c.get("candidate_id") for c in redis["candidates"]}),
            "physical_decisions": dict(Counter(d["decision"] for d in decisions)),
        }
    manifest = read(ROOT / "outputs_v291/prediction_manifest.json")
    verify = {"checked": {}, "mismatches": [], "errors": []}
    for section in ("source_sha256", "files_sha256", "input_sha256", "historical_manifests_sha256"):
        values = manifest.get(section, {})
        verify["checked"][section] = len(values)
        for name, expected in values.items():
            try:
                actual = sha(ROOT / name)
                if actual != expected:
                    verify["mismatches"].append({"section": section, "path": name, "expected": expected, "actual": actual})
            except OSError as error:
                verify["errors"].append({"path": name, "error": str(error)})
    verify["source_paths"] = list(manifest["source_sha256"])
    verify["input_paths"] = list(manifest["input_sha256"])
    result["manifest_verification"] = verify
    result["source_inventory"] = {"python_files": len(list((ROOT/"src").rglob("*.py"))),
                                   "test_files": len(list((ROOT/"tests").glob("test_*.py")))}
    (OUT / "audit_findings.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    compact = {task: {k: v for k,v in data.items() if k in {"reconfirm_events", "new_physical_episodes", "zero_time_new_physical_episodes", "new_physical_episodes_missing_from_temporal_memory", "search_zero_time_count", "anchor_label_mismatches", "rediscovery_unique_candidate_ids", "track_mappings"}} for task,data in result["videos"].items()}
    print(json.dumps({"videos": compact, "manifest": verify, "inventory": result["source_inventory"]}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
