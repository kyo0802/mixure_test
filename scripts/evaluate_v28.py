"""Post-freeze qualitative review. This module is never imported by V2.8 inference."""
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from memory_graph.v28.pipeline import OUT, sha, verify_freeze, write

REVIEWS = {
    "test3": {"expected_context": "box", "verdict": "LOCAL_GRAPH_EXPANDED_BUT_FINAL_PLACEMENT_MISSING",
              "review": "No box entity or container-entry transition was available. The graph adds chair/ball/microwave context, but INSIDE is unsupported."},
    "test4": {"expected_context": "basketball / blind spot", "verdict": "BASKETBALL_CONTEXT_ONLY",
              "review": "A sports-ball primary anchor and potted-plant Hop2 context are retained. NEAR is candidate-only; BEHIND is rejected because overlap/visibility-loss placement evidence is absent."},
    "test5": {"expected_context": "box; final placement incomplete", "verdict": "UNCERTAINTY_CORRECTLY_RETAINED",
              "review": "No box or entry transition is present. The final local graph is ball→microwave context, so INSIDE is not invented."},
    "test6": {"expected_context": "microwave / doll", "verdict": "MICROWAVE_CONTEXT_WITHOUT_PLACEMENT",
              "review": "Microwave is a primary anchor and the local graph is richer, but no stable doll node or physical placement transition supports ON/INSIDE/BEHIND."},
    "test7": {"expected_context": "doll", "verdict": "IDENTITY_SAFETY_BLOCKS_FINAL_CONTEXT",
              "review": "The provisional re-identification remains observation-only. No doll relation is written to phone memory; retained anchors are older image contexts."},
    "test8": {"expected_context": "multiple phone distractors after f804", "verdict": "IDENTITY_SAFE_RECONFIRMATION_WITHOUT_NEW_CONTEXT",
              "review": "The sole f804 CONFIRMED_MATCH updates last-seen state, but one trusted frame cannot form a new segment. Other phones do not update phone_01; pre-f804 context is STALE."},
    "test9": {"expected_context": "basketball / HomePad / bottle", "verdict": "INSUFFICIENT_COVISIBILITY",
              "review": "Only three trusted sampled target frames and no stable target-anchor segment are available, so no local graph or physical relation is created."},
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    verify_freeze()
    summary = read(OUT / "summary.json")
    evaluations = []
    aggregate_decisions = Counter()
    search_categories = Counter()
    for row in summary["videos"]:
        task = row["task"]
        folder = OUT / task
        observations = read(folder / "observations.json")
        graph = read(folder / "local_subgraph.json")
        decisions = read(folder / "physical_relation_decisions.json")
        plan = read(folder / "search_candidates.json")
        temporal = read(folder / "temporal_memory.json")
        audit = read(folder / "evidence_availability.json")
        unauthorized = [a for a in observations["identity_audit"]
                        if a["memory_update_authorized"] and a["identity"] not in {"TRUSTED", "CONFIRMED", "CONFIRMED_MATCH"}]
        image_leaks = [d for d in decisions if d["decision"] == "PROMOTED"
                       and not d["temporal_evidence"]["independent_physical_support"]
                       and d["vlm_evidence"]["status"] != "VALID"]
        false_identity = [d for d in decisions if d["decision"] in {"PROMOTED", "CANDIDATE"}
                          and d["identity_state"] != "TRUSTED"]
        for decision in decisions:
            aggregate_decisions[f"{decision['candidate_relation']}:{decision['decision']}"] += 1
        priorities = {candidate["priority_rule"] for candidate in plan["candidates"]}
        if priorities & {1, 2}:
            search_category = "PROMOTED_PHYSICAL_LOCATION"
        elif 3 in priorities:
            search_category = "CANDIDATE_PHYSICAL_HYPOTHESIS"
        elif priorities & {4, 5}:
            search_category = "IMAGE_CONTEXT_ONLY"
        else:
            search_category = "NO_USEFUL_CONTEXT"
        search_categories[search_category] += 1
        review = REVIEWS[task]
        obvious_false = []
        if any(d["decision"] == "PROMOTED" for d in decisions):
            obvious_false.append("Requires manual relation-specific review")
        result = {"schema": "v28_post_freeze_video_evaluation_1", "task": task,
                  "evaluation_phase": "after_prediction_freeze", "reference_labels_used_in_inference": False,
                  **review, "not_an_accuracy_measurement": True,
                  "graph_quality": {"v27_entities": row["v27_memory_entities"], "v28_entities": row["entity_count"],
                                    "hop0": row["hop0_count"], "hop1": row["hop1_count"], "hop2": row["hop2_count"],
                                    "connected": row["disconnected_node_count"] == 0,
                                    "snapshots": row["temporal_snapshots"],
                                    "final_nodes": read(folder / "object_memory_phone_01.json")["last_trusted_local_subgraph"]["nodes"]},
                  "physical_reasoning": {"evidence_status": audit["status"],
                                         "candidate_count": sum(d["decision"] == "CANDIDATE" for d in decisions),
                                         "promoted_count": sum(d["decision"] == "PROMOTED" for d in decisions),
                                         "rejected_or_uncertain_count": sum(d["decision"] in {"REJECTED", "UNCERTAIN"} for d in decisions),
                                         "types": dict(Counter(f"{d['candidate_relation']}:{d['decision']}" for d in decisions)),
                                         "obvious_false_promotions": obvious_false},
                  "safety": {"unauthorized_memory_updates": len(unauthorized),
                             "direct_image_to_physical_leaks": len(image_leaks),
                             "false_identity_physical_relations": len(false_identity),
                             "disconnected_nodes": row["disconnected_node_count"],
                             "irrelevant_branches_detected": row["irrelevant_branch_count"]},
                  "search": {"category": search_category, "candidate_count": len(plan["candidates"]),
                             "top_result": plan["candidates"][0] if plan["candidates"] else None},
                  "event_order_valid": all(a["frame"] <= b["frame"] for a, b in zip(temporal["events"], temporal["events"][1:]))}
        assert not unauthorized and not image_leaks and not false_identity
        assert result["graph_quality"]["connected"] and result["event_order_valid"]
        write(folder / "evaluation.json", result)
        evaluations.append(result)
    verify_freeze()
    aggregate = {"schema": "v28_post_freeze_evaluation_summary_1",
                 "evaluated_utc": datetime.now(timezone.utc).isoformat(),
                 "prediction_manifest_sha256": sha(OUT / "prediction_manifest.json"),
                 "videos": evaluations, "decision_counts": dict(aggregate_decisions),
                 "search_categories": dict(search_categories),
                 "totals": {"v27_entities": sum(v["graph_quality"]["v27_entities"] for v in evaluations),
                            "v28_entities": sum(v["graph_quality"]["v28_entities"] for v in evaluations),
                            "hop1": sum(v["graph_quality"]["hop1"] for v in evaluations),
                            "hop2": sum(v["graph_quality"]["hop2"] for v in evaluations),
                            "candidates": sum(v["physical_reasoning"]["candidate_count"] for v in evaluations),
                            "promotions": sum(v["physical_reasoning"]["promoted_count"] for v in evaluations),
                            "obvious_false_promotions": sum(len(v["physical_reasoning"]["obvious_false_promotions"]) for v in evaluations),
                            "unauthorized_updates": sum(v["safety"]["unauthorized_memory_updates"] for v in evaluations),
                            "disconnected_nodes": sum(v["safety"]["disconnected_nodes"] for v in evaluations)},
                 "scope": "Frozen-stream qualitative comparison; no full ground-truth trajectory or accuracy claim"}
    write(OUT / "evaluation_summary.json", aggregate)
    print(json.dumps({"decision_counts": aggregate["decision_counts"], "search_categories": aggregate["search_categories"],
                      "totals": aggregate["totals"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
