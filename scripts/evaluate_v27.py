"""Post-freeze narrative review. Never imported by V2.7 inference."""
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from memory_graph.v27.pipeline import OUT, sha, verify_freeze, write

# Qualitative user narrative, available only in this post-freeze evaluator.
REVIEWS = {
    "test3": ("box", "MISSING_FINAL_CONTEXT", "記憶只有較早的球類 image context，沒有支持 box 放置位置。"),
    "test4": ("basketball / blind spot", "PARTIAL_ANCHOR_ALIGNMENT", "球類 anchor 與敘述部分一致；沒有證據確認盲區位置或 BEHIND。"),
    "test5": ("box; placement incompletely observed", "MISSING_FINAL_CONTEXT", "保留球類 image context；沒有 box 位置證據，不推斷 INSIDE。"),
    "test6": ("microwave / doll", "MISSING_FINAL_CONTEXT", "可信 target 資料只支持先前球類 context，未建立微波爐或玩偶的最終 context。"),
    "test7": ("doll", "OLDER_CONTEXT_ONLY", "只有已結束的球類 context；PROVISIONAL_MATCH 未獲授權，無法寫入玩偶附近的記憶。"),
    "test8": ("multiple phone distractors", "IDENTITY_SAFE_BUT_CONTEXT_INCOMPLETE", "f804 確認更新 last seen，但單一影格不足以建立穩定新 anchor；後續不明手機不更新 memory。"),
    "test9": ("basketball occlusion; HomePad / bottle", "NO_STABLE_CONTEXT", "可信 target 與 anchor 的時間支持不足，沒有穩定 episode；不猜測物理遮擋。"),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    verify_freeze()
    summary = read(OUT / "summary.json")
    results = []
    checked_inputs = {}
    for row in summary["videos"]:
        for name, digest in row["input_sha256"].items():
            assert sha(ROOT / name) == digest, f"Upstream input changed: {name}"
            checked_inputs[name] = digest
        task = row["task"]
        folder = OUT / task
        obs = read(folder / "observations.json")
        episodes = read(folder / "relation_episodes.json")
        temporal = read(folder / "temporal_memory.json")
        memory = read(folder / "object_memory_phone_01.json")
        plan = read(folder / "search_candidates.json")
        audit = obs["identity_audit"]
        unauthorized = [a for a in audit if a["memory_update_authorized"] and a["identity"] not in {"TRUSTED", "CONFIRMED", "CONFIRMED_MATCH"}]
        blocked = Counter(a["identity"] for a in audit if not a["memory_update_authorized"])
        ep_by_id = {e["episode_id"]: e for e in episodes}
        provenance_ok = all(c["source_episode"] in ep_by_id and c["provenance"] and c["source_memory"] for c in plan["candidates"])
        physical_leaks = [e for e in episodes if e["kind"] == "PHYSICAL" and e["evidence_level"] != "TRUSTED_PHYSICAL_SUPPORT"]
        loss_checks = []
        for snapshot in temporal["snapshots"]:
            if any(e["event_type"] == "TARGET_DISAPPEARED" for e in snapshot["trigger_events"]):
                loss_checks.append({"frame": snapshot["frame"], "remembered_relations": len(snapshot["relations"]),
                                    "all_relations_last_trusted": all(e["status"] == "LAST_TRUSTED" for e in snapshot["relations"])})
        causal = all(e["start_frame"] <= e["end_frame"] and max(e["support_frames"]) <= e["end_frame"] for e in episodes)
        ordered = all(a["frame"] <= b["frame"] for a, b in zip(temporal["events"], temporal["events"][1:]))
        assert not unauthorized and not physical_leaks and provenance_ok and causal and ordered
        assert all(c["all_relations_last_trusted"] for c in loss_checks)
        assert memory == read(folder / "phone_01_lifetime.json")
        narrative, verdict, note = REVIEWS[task]
        result = {
            "task": task, "evaluation_phase": "after_prediction_freeze", "narrative_used_in_inference": False,
            "narrative": narrative, "qualitative_verdict": verdict, "review": note,
            "not_an_accuracy_measurement": True, "unauthorized_memory_updates": len(unauthorized),
            "blocked_observation_counts_by_identity": dict(blocked), "physical_evidence_leaks": len(physical_leaks),
            "search_provenance_valid": provenance_ok, "episode_support_causal": causal, "events_ordered": ordered,
            "loss_snapshot_checks": loss_checks, "upstream_entities": row["upstream_entities"],
            "memory_entities": row["memory_entities"], "snapshots": row["snapshots"],
            "last_trusted_anchors": row["last_trusted_anchors"], "search_candidates": len(plan["candidates"]),
            "search_priority_rules": [c["priority_rule"] for c in plan["candidates"]],
            "limitations": obs["provenance"]["limitations"],
        }
        write(folder / "evaluation.json", result)
        results.append(result)
    verify_freeze()
    result = {"schema": "v27_post_freeze_evaluation_1", "evaluated_utc": datetime.now(timezone.utc).isoformat(),
              "prediction_manifest_sha256": sha(OUT / "prediction_manifest.json"),
              "verified_upstream_files": len(checked_inputs), "videos": results,
              "videos_with_last_trusted_anchor": sum(bool(r["last_trusted_anchors"]) for r in results),
              "videos_with_search_fallback": sum(bool(r["search_candidates"]) for r in results),
              "physical_episodes": sum(r["physical_episodes"] for r in summary["videos"]),
              "scope": "Frozen-stream memory replay; qualitative narrative review, not end-to-end model accuracy"}
    write(OUT / "evaluation_summary.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "videos"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
