"""Deterministic CPU tests; mock labels never enter human collections."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import consolidate_findmind_gt as c
import evaluate_consolidated_vlm as e


def rec(name='a', start=1., end=2., typ='PICKUP', identity='CERTAIN', certainty='CONFIRMED'):
    return {'ref': name, 'reviewer_id': name, 'session_id': name, 'submission_sha256': 'mock', 'video_id': 'test1',
            'event': {'event_id': name, 'start_s': start, 'end_s': end, 'type': typ, 'object_category': 'Phone',
                      'local_instance_id': name, 'target_identity_certainty': identity, 'evidence_certainty': certainty,
                      'before_state': 'ON_SURFACE', 'after_state': 'HELD_BY_PERSON', 'before_visibility': 'VISIBLE',
                      'after_visibility': 'VISIBLE', 'before_evidence_times_s': [.5], 'after_evidence_times_s': [2.5]}}


def scope(a=0., b=5.):
    return {'scope_id': 'S1', 'video_id': 'test1', 'start_s': a, 'end_s': b, 'object_categories': ['phone'], 'object_ids': ['obj1']}


def pred(pid='p1', group='evt1', supported=True, strict=True, eligible=True, time=None):
    return {'proposal_id': pid, 'model': 'mock', 'window_id': 'W1', 'event_index': 0, 'video_id': 'test1', 'video_sha256': 'sha',
            'type': 'PICKUP', 'reviewed_object_id': 'obj1', 'reviewed_object_category': 'phone', 'reviewed_event_group': group,
            'time_interval': [1., 2.] if time is None else time, 'strict_accepted': strict, 'review_eligible': eligible,
            'physical_review_status': 'HUMAN_SUPPORTED' if supported else 'HUMAN_UNSUPPORTED',
            'review': {'wrong_target': 'NO', 'owner_reviewer_id': 'TEST_ONLY'}}


def truth():
    return {'final_event_id': 'GT1', 'video_id': 'test1', 'video_sha256': 'sha', 'type': 'PICKUP',
            'object_category': 'Phone', 'reviewed_object_id': 'obj1', 'time_interval': [1.5, 1.5]}


class AlignmentTests(unittest.TestCase):
    def test_native_timing_mismatch_rejected(self):
        manifest = {'videos': [{'video_id': 'test1', 'source_sha256': 'sha', 'frame_count': 1, 'frame_timeline': [{'index': 0, 'source_time_s': .5}]}]}
        dataset = {'windows': [{'video_id': 'test1', 'source_video_sha256': 'sha', 'frames': [{'source_frame_index': 0, 'native_pts_s': .5}]}]}
        self.assertEqual(c.verify_timing(manifest, dataset), 1)
        dataset['windows'][0]['frames'][0]['native_pts_s'] = .6
        with self.assertRaisesRegex(ValueError, 'PTS mismatch'): c.verify_timing(manifest, dataset)

    def test_all_classification_branches(self):
        a, b = rec('a'), rec('b')
        self.assertEqual(c.classify([a, b])[0], 'AGREED_CANDIDATE')
        self.assertEqual(c.classify([a])[0], 'ONE_REVIEWER_ONLY')
        self.assertEqual(c.classify([a, rec('b', end=3.)])[0], 'TIMING_DISAGREEMENT')
        self.assertEqual(c.classify([a, rec('b', typ='PLACEMENT')])[0], 'EVENT_TYPE_DISAGREEMENT')
        self.assertEqual(c.classify([a, rec('b', typ='CONTACT_ONLY')])[0], 'NON_EVENT_CONFLICT')
        self.assertEqual(c.classify([a, rec('b', identity='UNKNOWN')])[0], 'IDENTITY_DISAGREEMENT')
        self.assertEqual(c.classify([a, rec('b', certainty='UNCERTAIN')])[0], 'UNCERTAIN_EVIDENCE')

    def test_different_reviewer_local_names_are_not_conflict(self):
        self.assertEqual(c.classify([rec('phone_1'), rec('object_X')])[0], 'AGREED_CANDIDATE')

    def test_ambiguous_overlap_never_unions_three_real_events(self):
        groups, _ = c.align([rec('a')], [rec('b'), rec('c')])
        self.assertEqual([len(g) for g in groups], [1, 1, 1])

    def test_distinct_overlapping_events_stay_two_groups(self):
        groups, _ = c.align([rec('a', 1, 3), rec('b', 2, 4)], [rec('c', 1, 3), rec('d', 2, 4)])
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(len(g) == 2 for g in groups))

    def test_contact_alternative_is_flagged_without_merging(self):
        registry = {'G1': [rec('a')], 'G2': [rec('b', typ='CONTACT_ONLY')]}
        rows = [{'group_id': 'G1', 'all_flags': 'ONE_REVIEWER_ONLY', 'related_groups': 'G2'}, {'group_id': 'G2', 'all_flags': 'ONE_REVIEWER_ONLY', 'related_groups': 'G1'}]
        c.cross_group_conflicts(rows, registry)
        self.assertEqual(rows[0]['classification'], 'NON_EVENT_CONFLICT')
        self.assertEqual(len(registry), 2)


class EvaluationTests(unittest.TestCase):
    def test_temporal_boundaries_one_to_one(self):
        g = truth(); g['time_interval'] = [1., 2.]
        for point, tol, count in [(1., 0, 1), (2., 0, 1), (.8, .2, 1), (.799, .2, 0), (2.5, .5, 1), (2.501, .5, 0)]:
            p = pred(time=[point, point])
            self.assertEqual(len(e.match_one_to_one([p], [g], tol)), count)
        self.assertEqual(len(e.match_one_to_one([pred(), pred('p2')], [g], .2)), 1)

    def test_separate_event_groups_not_collapsed_on_overlap(self):
        self.assertEqual(len(e.deduplicate([pred(), pred('p2', 'evt2')])), 2)
        self.assertEqual(len(e.deduplicate([pred(), pred('p2')])), 1)

    def test_group_identity_conflict_rejected(self):
        b = pred('p2'); b['reviewed_object_id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'Conflicting'): e.deduplicate([pred(), b])

    def test_unsupported_and_wrong_target_never_tp(self):
        x = e.score([pred(supported=False)], [truth()], [.2])['0.2']['PICKUP']
        self.assertEqual((x['tp'], x['fp'], x['fn']), (0, 1, 1))
        p = pred(); p['review']['wrong_target'] = 'YES'
        self.assertEqual(e.score([p], [truth()], [.2])['0.2']['PICKUP']['tp'], 0)

    def test_partial_scope_excludes_unreviewed_outside(self):
        p = pred('outside', eligible=False, time=[7., 8.]); p['window_id'] = 'W2'
        windows = [{'window_id': 'W1', 'video_id': 'test1', 'interval': [0, 5], 'strict': True}, {'window_id': 'W2', 'video_id': 'test1', 'interval': [6, 9], 'strict': True}]
        result = e.metric_view([pred(), p], {'coverage': [scope()], 'truth': [truth()]}, windows, 'physical_candidates', [0, .2, .5], [])
        self.assertEqual(result['metrics_by_tolerance']['0']['PICKUP']['tp'], 1)
        self.assertIsNone(result['overall_full_dataset_f1'])

    def test_invalid_predictions_not_no_event_and_strict_gated(self):
        windows = [{'window_id': 'W1', 'video_id': 'test1', 'interval': [0, 5], 'strict': False}]
        gt = {'coverage': [scope()], 'truth': [truth()]}
        self.assertIsNone(e.metric_view([pred(strict=False)], gt, windows, 'strict_valid', [.2], [])['metrics_by_tolerance'])
        self.assertIsNone(e.metric_view([], gt, windows, 'physical_candidates', [.2], [('test1', [0, 5])])['metrics_by_tolerance'])

    def test_unknown_time_and_scope_boundary_block(self):
        p = pred(eligible=False); p['time_interval'] = None
        windows = [{'window_id': 'W1', 'video_id': 'test1', 'interval': [0, 5], 'strict': True}]
        gt = {'coverage': [scope()], 'truth': [truth()]}
        self.assertIsNone(e.metric_view([p], gt, windows, 'physical_candidates', [.2], [])['metrics_by_tolerance'])
        gt['coverage'] = [scope(1.2, 5)]
        self.assertIsNone(e.metric_view([pred()], gt, windows, 'physical_candidates', [.2], [])['metrics_by_tolerance'])


class FinalizeTests(unittest.TestCase):
    def setUp(self):
        test_root = ROOT / '.annotation_test_tmp'; test_root.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=test_root, prefix='FINDMIND_CPU_MOCK_')
        assert Path(self.tmp.name).resolve().is_relative_to(test_root.resolve())
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name); self.r = rec()
        c.save(self.out / 'alignment_registry.json', {'G1': [self.r]}); c.save(self.out / 'original_state_evidence.json', [])
        c.save(self.out / 'preservation_manifest.json', {})
        self.manifest = {'dataset_manifest_sha256': 'mock', 'videos': [{'video_id': 'test1', 'source_sha256': 'sha', 'source_duration_s': 10}]}
        self.bundle = {'videos': [{'video_id': 'test1', 'uncertain_intervals': [], 'event_list_exhaustiveness': 'NOT_ATTESTED'}]}
        self.row = {'group_id': 'G1', 'decision_id': 'G1', 'source_refs': 'a', 'video_id': 'test1', 'owner_decision': 'ACCEPT', 'owner_reviewer_id': 'MOCK_OWNER',
                    'decision_notes': 'TEST ONLY visible evidence reviewed', 'final_event_type': 'PICKUP', 'final_object_category': 'Phone', 'final_start_s': 1, 'final_end_s': 2,
                    'physical_transition_confirmed': 'YES', 'identity_resolved': 'YES', 'same_real_event_confirmed': '', 'final_object_id': 'obj1', 'final_event_id': 'GT1',
                    'final_before_state': 'ON_SURFACE', 'final_after_state': 'HELD_BY_PERSON', 'final_before_visibility': 'VISIBLE', 'final_after_visibility': 'VISIBLE',
                    'final_before_evidence_times_s': '[0.5]', 'final_after_evidence_times_s': '[2.5]'}
        self.scope = {'scope_id': 'S1', 'video_id': 'test1', 'start_s': 0, 'end_s': 5, 'owner_decision': '', 'owner_reviewer_id': 'MOCK_OWNER',
                      'decision_notes': 'TEST ONLY', 'object_category_scope': 'Phone', 'object_ids_scope': 'obj1',
                      'full_scope_reviewed': 'YES', 'all_events_verified': 'YES', 'event_visibility_sufficient': 'YES', 'object_identity_resolved': 'YES', 'known_gaps_resolved': ''}

    def run_final(self):
        c.csv_write(self.out / 'adjudication.csv', [self.row]); c.csv_write(self.out / 'coverage_adjudication.csv', [self.scope])
        with patch.object(c, 'records', return_value=(self.manifest, [self.bundle], [[self.r]])), patch.object(c, 'verify_timing', return_value=0):
            return c.finalize(self.out, self.out / 'final')

    def test_not_attested_never_auto_negative(self):
        result = self.run_final(); self.assertEqual(result['eligible_scopes'], 0); self.assertEqual(result['events'], 1)

    def test_explicit_partial_scope_with_provenance(self):
        self.scope['owner_decision'] = 'ACCEPT'; self.run_final()
        gt = c.load_json(self.out / 'final/final_gt.json')
        self.assertEqual(gt['coverage'][0]['end_s'], 5)
        self.assertTrue(gt['coverage'][0]['original_NOT_ATTESTED_preserved'])
        self.assertEqual(gt['truth'][0]['source_records'][0], self.r)
        receipt = c.load_json(self.out / 'final/finalization_receipt.json')
        self.assertEqual(receipt['final_gt_sha256'], c.file_sha(self.out / 'final/final_gt.json'))

    def test_no_owner_decisions_cannot_finalize(self):
        self.row['owner_decision'] = ''
        with self.assertRaisesRegex(ValueError, 'No owner'): self.run_final()

    def test_unknown_gap_cannot_be_attested_without_resolution(self):
        self.scope['owner_decision'] = 'ACCEPT'
        self.bundle['videos'][0]['uncertain_intervals'] = [{'start_s': 3, 'end_s': 4, 'could_conceal_event': True, 'identity_uncertain': False}]
        with self.assertRaisesRegex(ValueError, 'Known obscured'): self.run_final()

    def test_uncertain_annotation_blocks_its_partial_scope(self):
        self.row['owner_decision'] = 'UNCERTAIN'; self.scope['owner_decision'] = 'ACCEPT'
        with self.assertRaisesRegex(ValueError, 'Unresolved annotation'): self.run_final()

    def test_disappearance_cannot_confirm_transition(self):
        self.row['final_after_visibility'] = 'NOT_VISIBLE'
        with self.assertRaisesRegex(ValueError, 'Invisible'): self.run_final()

    def test_changed_accept_requires_modify(self):
        self.row['final_start_s'] = 1.1
        with self.assertRaisesRegex(ValueError, 'require MODIFY'): self.run_final()

    def test_original_registry_tampering_rejected(self):
        fake = copy.deepcopy(self.r); fake['event']['start_s'] = 0
        (self.out / 'alignment_registry.json').write_text(json.dumps({'G1': [fake]}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'differs from original'): self.run_final()


if __name__ == '__main__': unittest.main()
