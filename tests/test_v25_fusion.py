"""V2.5 architecture and frozen-output regression checks."""
import json
from pathlib import Path

from memory_graph.v25.binding import TargetBinding, AutomaticTargetBinding
from memory_graph.v25.candidates import CandidateStream

ROOT = Path(__file__).resolve().parents[1]


def data(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def obs(frame, box, track=None, confidence=.8):
    return {"frame_index": frame, "timestamp": frame / 30, "bbox": box,
            "source_track_id": track, "confidence": confidence,
            "raw_detection_index": frame, "semantic_class": "cell phone"}


def test_no_task_specific_track_ids_in_v25():
    src = '\n'.join(p.read_text(encoding='utf-8') for p in (ROOT / 'src/memory_graph/v25').glob('*.py'))
    assert 'test3' not in src and 'test8' not in src


def test_no_fixed_late_candidate_frame():
    src = (ROOT / 'src/memory_graph/v25/reid.py').read_text(encoding='utf-8')
    assert 'late_candidate_frame' not in src and 'test7' not in src


def test_target_binding_does_not_use_future_gt():
    b = TargetBinding().bind_target(bbox_prompt={"frame_index": 12, "timestamp": .4, "bbox": [0, 0, 10, 10]})
    assert b.frame_index == 12 and b.source_kind == 'bbox_prompt'
    assert 'ground_truth' not in (ROOT / 'src/memory_graph/v25/binding.py').read_text()


def test_unobserved_entity_continues_candidate_monitoring():
    s = CandidateStream(); s.admit(obs(900, [0, 0, 10, 10])); assert len(s.events) == 1


def test_new_phone_observation_is_admitted_after_long_gap():
    s = CandidateStream(); a = s.admit(obs(0, [0, 0, 10, 10])); b = s.admit(obs(900, [0, 0, 10, 10]))
    assert a.candidate_id != b.candidate_id


def test_ambiguous_candidate_remains_active():
    s = CandidateStream(); c = s.admit(obs(30, [0, 0, 10, 10])); assert c.status == 'PROVISIONAL'


def test_ambiguous_candidate_can_accumulate_more_evidence():
    s = CandidateStream(); c = s.admit(obs(30, [0, 0, 10, 10])); s.admit(obs(36, [1, 1, 11, 11])); assert len(c.observations) == 2


def test_candidate_grouping_preserves_distinct_coexisting_phones():
    s = CandidateStream(); a = s.admit(obs(30, [0, 0, 10, 10])); b = s.admit(obs(30, [100, 0, 110, 10])); s.finish_frame(30)
    assert a.candidate_id != b.candidate_id and b.candidate_id in a.distinct_coexistence_with


def test_candidate_grouping_does_not_use_raw_track_id_as_physical_identity():
    s = CandidateStream(); a = s.admit(obs(30, [0, 0, 10, 10], 1)); b = s.admit(obs(36, [100, 0, 110, 10], 1))
    assert a.candidate_id != b.candidate_id


def test_reid_threshold_remains_v24_frozen():
    assert data('outputs_v25/architecture_manifest.json')['reid']['minimum_match_similarity'] == .6


def test_reid_margin_remains_v24_frozen():
    assert data('outputs_v25/architecture_manifest.json')['reid']['minimum_uniqueness_margin'] == .1


def test_yolo_miss_does_not_delete_entity():
    rows = data('outputs_v25/test8/identity_timeline.json')['phone_timeline']
    assert any(r['state'] == 'UNOBSERVED' for r in rows) and data('outputs_v25/test8/entity_registry.json')['target_entity_id'] == 'phone_01'


def test_trusted_sam_can_bridge_temporary_yolo_miss():
    src = (ROOT / 'src/memory_graph/v25/fusion.py').read_text()
    assert src.index('registry.observe_sam') < src.index('registry.observe_yolo(obs, tid, accepted)')
    assert 'registry.confirm_raw_yolo(det, accepted)' in src


def test_rejected_sam_cannot_update_candidate():
    src = (ROOT / 'src/memory_graph/v25/fusion.py').read_text()
    assert 'registry.observe_sam' in src and 'if result is not None' in src


def test_only_safe_match_can_merge_into_phone01():
    for t in ['test3', 'test4', 'test6', 'test9']:
        assert not data(f'outputs_v25/{t}/entity_registry.json').get('reid_aliases')


def test_only_safe_match_can_authorize_sam_reinitialization():
    for t in [f'test{i}' for i in range(3, 10)]:
        a = data(f'outputs_v25/{t}/reid_audit.json'); r = data(f'outputs_v25/{t}/sam_reinit_log.json')
        assert bool(r['sam_reinitialization_executed']) == (a['decision'] == 'MATCH')


def test_candidate_merge_preserves_provenance():
    r = data('outputs_v25/test8/entity_registry.json')
    assert r['reidentified_from_candidate'] == 'candidate_009' and r['reidentified_at_frame'] == 804


def test_gt_unavailable_before_prediction_freeze():
    assert data('outputs_v25/prediction_manifest.json')['gt_read_before_freeze'] is False
    for t in [f'test{i}' for i in range(3, 10)]:
        assert data(f'outputs_v25/{t}/reid_audit.json')['gt_accessed'] is False
