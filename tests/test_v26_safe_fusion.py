"""V2.6 safety behavior on synthetic frozen-scorer decisions."""
from memory_graph.v26.authorization import authorize
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v26"


def artifact(task, name):
    return json.loads((OUT / task / name).read_text(encoding="utf-8"))


def scored(candidate="candidate_001", score=.611, second=None, margin=None, base="MATCH"):
    return {"candidate_entity_id": candidate, "appearance": {"max_similarity": score},
            "second_candidate_similarity": second, "best_vs_second_margin": margin,
            "hard_contradictions": [], "decision": base, "candidate_quality": "frozen_yolo_seed_and_nonempty_sam_mask"}


def test_single_candidate_does_not_bypass_uniqueness():
    assert authorize([scored()], {"candidate_001"})[0]["decision"] != "CONFIRMED_MATCH"


def test_single_candidate_above_base_threshold_is_provisional():
    assert authorize([scored()], {"candidate_001"})[0]["decision"] == "PROVISIONAL_MATCH"


def test_provisional_match_does_not_alias_phone01():
    assert not authorize([scored()], {"candidate_001"})[0]["alias_authorized"]


def test_provisional_match_does_not_update_trusted_bank():
    assert not authorize([scored()], {"candidate_001"})[0]["trusted_bank_update_authorized"]


def test_provisional_match_does_not_authorize_sam_reinit():
    assert not authorize([scored()], {"candidate_001"})[0]["sam_reinitialization_authorized"]


def test_candidate_audit_continues_after_provisional_match():
    first = authorize([scored()], {"candidate_001"})
    second = authorize([scored("candidate_002", .35, base="AMBIGUOUS")], {"candidate_002"})
    assert first[0]["decision"] == "PROVISIONAL_MATCH" and second[0]["decision"] == "AMBIGUOUS"


def test_candidate_audit_continues_after_confirmed_match():
    first = authorize([scored(score=.681, second=.422, margin=.259)], {"candidate_001"})
    second = authorize([scored("candidate_002", .35, base="AMBIGUOUS")], {"candidate_002"})
    assert first[0]["decision"] == "CONFIRMED_MATCH" and len(second) == 1


def test_multi_candidate_unique_match_can_confirm():
    rows = [scored(score=.7, second=.4, margin=.3), scored("candidate_002", .4, second=.4, margin=.3, base="AMBIGUOUS")]
    assert authorize(rows, {"candidate_001", "candidate_002"})[0]["decision"] == "CONFIRMED_MATCH"


def test_test8_style_unique_match_remains_confirmable():
    assert authorize([scored(score=.681, second=.422, margin=.259)], {"candidate_001"})[0]["decision"] == "CONFIRMED_MATCH"


def test_stale_candidate_cannot_gain_confirmation_from_later_competitor():
    assert authorize([scored(score=.7, second=.4, margin=.3)], {"candidate_002"})[0]["decision"] == "PROVISIONAL_MATCH"


def test_reid_visualization_contains_candidate_decisions():
    for task in ("test7", "test8"):
        image = Image.open(OUT / task / "reid_timeline.png")
        assert image.width >= 2000 and image.height >= 900
        assert any(row["v26_decision"] in ("PROVISIONAL_MATCH", "CONFIRMED_MATCH")
                   for row in artifact(task, "v25_vs_v26_candidates.json"))


def test_reid_visualization_contains_similarity():
    rows = artifact("test7", "v25_vs_v26_candidates.json")
    assert next(r for r in rows if r["candidate_id"] == "candidate_004")["v26_similarity"] > .6
    assert (OUT / "test7/reid_contact_sheet.png").is_file()


def test_reid_visualization_contains_not_evaluated_candidates():
    rows = artifact("test7", "v25_vs_v26_candidates.json")
    assert any(r["v25_decision"] == "NOT_EVALUATED" and r["v26_similarity"] is not None for r in rows)
    assert (OUT / "test7/test7_identity_failure_explainer.png").is_file()


def test_gt_not_used_before_prediction_freeze():
    manifest = json.loads((OUT / "prediction_manifest.json").read_text(encoding="utf-8"))
    initial = json.loads((OUT / "initial_blind/prediction_manifest.json").read_text(encoding="utf-8"))
    assert initial["stage"] == "A_BLIND_INFERENCE_COMPLETE" and not initial["gt_read_before_freeze"]
    assert manifest["stage"] == "B_POSTFREEZE_PROVENANCE_REPAIR"
    assert manifest["categorical_reid_decisions_identical_to_initial_blind"]
    assert not manifest["gt_labels_used_in_repair"]
    for i in range(3, 10):
        assert not artifact(f"test{i}", "reid_audit.json")["gt_accessed"]


def test_test7_provisional_prevents_false_alias_and_keeps_later_audit():
    audit = artifact("test7", "reid_audit.json")
    registry = artifact("test7", "entity_registry.json")
    assert audit["confirmed_match"] is None and "candidate_004" in audit["provisional_candidate_ids"]
    assert not registry.get("reid_aliases")
    query = next(e for e in registry["entities"] if e["entity_id"] == "phone_01")
    assert "sam_candidate_004" not in query.get("sam_sources", [])
    assert "appearance_memory" not in query
    for frame, candidate in ((720, "candidate_014"), (888, "candidate_015")):
        attempt = next(a for a in audit["attempts"] if a["frame_index"] == frame)
        assert any(d["candidate_entity_id"] == candidate for d in attempt["candidate_decisions"])
    assert not artifact("test7", "sam_reinit_log.json")["sam_reinitialization_executed"]


def test_test8_confirmed_match_preserved_with_sam_reinit():
    audit = artifact("test8", "reid_audit.json")
    assert audit["confirmed_match"]["candidate_id"] == "candidate_009"
    assert artifact("test8", "sam_reinit_log.json")["sam_reinitialization_executed"]
    assert artifact("test8", "entity_registry.json")["reid_aliases"] == {"candidate_009": "phone_01"}
