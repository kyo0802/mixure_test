"""Relocation, actual Tk startup and isolated synthetic return/save checks."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
QA = REPO / 'artifacts/pass_t/phase2a/v2/stage_b/handoff_qa'


class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QA.mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(prefix='relocated_', dir=QA)
        cls.base = Path(cls.temp.name).resolve()
        assert cls.base.is_relative_to(QA.resolve())
        cls.bundle = cls.base / 'collaborator folder'
        shutil.copytree(REPO / 'annotation_handoff/pass_t_phase2a_v2', cls.bundle)
        spec = importlib.util.spec_from_file_location('portable_review', cls.bundle / 'review.py')
        cls.review = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.review)
        from memory_graph.pass_t.phase2a_v2 import policy, projection, storage, viewer
        cls.p, cls.proj, cls.s, cls.v = policy, projection, storage, viewer
        assert cls.p.ROOT == cls.bundle
        cls.results = {'interpreter': sys.version, 'relocation': 'directory with spaces',
                       'dependencies_from': 'independent minimal virtual environment'}

    @classmethod
    def tearDownClass(cls):
        cls.results['production_progress'] = cls.s.progress()
        (QA / 'portable_checks.json').write_text(json.dumps(cls.results, indent=2), encoding='utf-8')
        assert cls.base.is_relative_to(QA.resolve())
        cls.temp.cleanup()

    def test_01_relocated_release_and_exact_original_bytes(self):
        result = self.review.check_release()
        self.assertEqual(result['status'], 'HANDOFF_INTEGRITY_OK')
        self.assertEqual(result['eligible_windows'], 7)
        self.assertEqual(result['valid_round1'], 0)
        self.assertEqual(result['invalid_records'], 0)
        receipt = self.p.read(self.bundle / 'release_receipt.json')
        self.assertEqual((receipt['frames'], receipt['references']), (728, 16))
        self.assertEqual(receipt['source_manifest_sha256'], self.p.sha(REPO / 'artifacts/pass_t/phase2a/v2/manifest.json'))
        for name in ('policy.py', 'projection.py', 'validation.py', 'storage.py', 'finalize.py', 'viewer.py', 'cli.py'):
            rel = 'src/memory_graph/pass_t/phase2a_v2/' + name
            self.assertEqual(self.p.sha(self.bundle / rel), self.p.sha(REPO / rel))
        for name in receipt['files_sha256']:
            self.assertNotIn('.venv', name)
            self.assertNotIn('Frozen', name)
            self.assertFalse(name.endswith(('.pt', '.safetensors', '.mp4')))
        self.results['integrity'] = result

    def test_02_real_gui_all_seven_windows_starts_blank(self):
        import tkinter as tk
        root = tk.Tk(); root.withdraw()
        app = self.v.Viewer(root)
        try:
            for index in range(len(app.entries)):
                app.index = index; app.load(); root.update_idletasks(); root.update()
                self.assertEqual(app.form.controls['reviewer_id'].get(), '')
                self.assertEqual(app.form.controls['window_outcome'].get(), '')
                self.assertFalse(any(v.get() for v in app.attests.values()))
                self.assertEqual(app.draft()['events'], [])
                self.assertEqual(app.overlay.get(), 'SELECTED_CANDIDATE_ONLY')
                app.position = len(app.item['visual']['frames']) - 1
                app.draw(); root.update_idletasks()
                self.assertEqual(app.current()['frame_id'], app.item['visual']['frames'][-1]['frame_id'])
            self.results['actual_tk_windows_opened'] = 7
            self.results['blank_answers_verified'] = True
        finally:
            app.stop_play(); root.destroy()

    def test_03_tamper_detection(self):
        entry = self.proj.load_manifest()['items'][0]
        item = self.proj.load_item(entry)
        path = self.p.within(self.bundle, item['visual']['frames'][0]['image_path'])
        original = path.read_bytes()
        try:
            path.write_bytes(original + b'SYNTHETIC_TAMPER')
            with self.assertRaisesRegex(ValueError, 'HANDOFF_FILE_CHANGED'):
                self.review.check_release()
        finally:
            path.write_bytes(original)

    def synthetic(self):
        # Coloured artificial frames and explicit synthetic text; never a production answer.
        from PIL import Image
        out = self.bundle / 'SYNTHETIC_ONLY'
        out.mkdir()
        p, s = self.p, self.s
        receipt = p.verify_gate()
        p.exclusive(out / 'stage_b/approval.json', p.read(p.OUT / 'stage_b/approval.json'), out)
        p.exclusive(out / 'stage_b/protected_before.json', {}, out)
        id_ = 'PT2A_' + 'a' * 16
        frames = []
        for j in range(6):
            path = out / f'S{10+j:06d}.png'
            Image.new('RGB', (1280, 720), (j*20, 0, 0)).save(path)
            frames.append({'frame_id': path.stem, 'source_frame_index': 10+j, 'source_timestamp_s': 1+j/10,
                           'timestamp_provenance': 'NATIVE_PTS', 'image_path': str(path), 'sha256': p.sha(path)})
        visual = {'frames': frames, 'references': [], 'width': 1280, 'height': 720,
                  'coordinate_system_id': 'REVIEW_FRAME_PIXELS_V1', 'frame_to_source_transform': [[1,0,0],[0,1,0]]}
        item = {'annotation_item_id': id_, 'original_pack_ids': ['SYNTHETIC_ONLY'], 'source_video_identifier': 'synthetic',
                'source_video_sha256': 'b'*64, 'window_start_s': 1., 'window_end_s': 1.6,
                'authorized_half_open_frames': [10,16], 'selected_local_candidate_id': '7', 'stratum': 'HUMAN_SEEDED_DEV',
                'dev_eligible': True, 'seed_provenance_scope': 'HUMAN_VISUAL_LOCALIZATION_ONLY',
                'binding_causality_status': 'CAUSALITY_UNVERIFIED', 'overlap_group_id': 'SYNTHETIC_GROUP',
                'formal_eligible': False, 'observations': [], 'visual': visual,
                'authorized_visual_manifest_sha256': p.object_sha(visual)}
        backend = {'phase1c_response_sha256': 'c'*64, 'phase1c_reviewer_id': 'SYNTHETIC_REVIEWER'}
        ip = out / 'items' / id_ / 'item.json'
        entry = {'annotation_item_id': id_, 'item_path': ip.relative_to(out).as_posix(),
                 'item_sha256': p.exclusive(ip, item, out), 'stratum': item['stratum'],
                 'original_pack_ids': item['original_pack_ids'], 'source_video_identifier': 'synthetic',
                 'overlap_group_id': 'SYNTHETIC_GROUP',
                 'backend_sha256': p.exclusive(out / 'private' / (id_+'.json'), backend, out)}
        manifest = {'items': [entry], 'repeat_subset': self.proj.repeat_subset([id_]), 'excluded': [],
                    'policy_md_sha256': receipt['policy_md_sha256'], 'formal_eligible': 0}
        p.exclusive(out / 'manifest.json', manifest, out)
        p.exclusive(out / 'manifest.freeze.json', {'manifest_sha256': p.sha(out / 'manifest.json')}, out)
        draft = {'reviewer_id': 'SYNTHETIC_REVIEWER', 'window_outcome': 'INSUFFICIENT_EVIDENCE', 'events': [],
                 'unmodeled_observations': [], 'observation_coverage_frame_ids': [], 'coverage_citations': [],
                 'coverage_assessment': 'UNKNOWN', 'last_confirmed_state': 'STATE_UNKNOWN',
                 'last_confirmed_state_description': None, 'last_confirmed_frame_id': None, 'last_confirmed_timestamp': None,
                 'last_confirmed_state_evidence': [], 'last_confirmed_location_description': None,
                 'location_marker': None, 'location_evidence_frame_ids': [],
                 'visibility_at_window_end': {'visibility': 'VISIBILITY_UNKNOWN', 'frame_id': 'S000015', 'source_timestamp_s': 1.5,
                                              'observed_reason': None, 'evidence': [], 'rationale': 'Synthetic unknown.'},
                 'unknown_or_unobserved_afterward': True, 'subsequent_location': 'UNKNOWN',
                 'subsequent_location_description': None, 'subsequent_location_evidence_frame_ids': [], 'subsequent_location_evidence': [],
                 'target_identification_event_dependence': 'NOT_DEPENDENT',
                 'target_identification_event_dependence_rationale': 'Synthetic artificial frame fixture.',
                 'target_recognition_used_pre_window_reference': False,
                 'uncertainty': {'status': 'UNKNOWN', 'description': 'SYNTHETIC TEST ONLY'}, 'confidence': 'UNKNOWN',
                 'human_rationale': 'SYNTHETIC TEST ONLY; no actual human judgment.',
                 'attestations': {key: key=='human_attestation' for key in p.frozen_schema()['$defs']['attestations']['properties']},
                 'interaction_metadata': {'initial_overlay_mode': 'SELECTED_CANDIDATE_ONLY', 'references_opened': [],
                                          'overlay_toggles': [], 'metadata_is_advisory': True}}
        return out, entry, draft

    def test_04_isolated_synthetic_save_duplicate_return_and_hashes(self):
        with self.assertRaisesRegex(ValueError, 'NO_VALID_SUBMISSIONS'):
            self.review.export_return()
        out, entry, draft = self.synthetic()
        result = self.s.submit(draft, entry, out=out)
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_ITEM_ROUND'):
            self.s.submit(draft, entry, out=out)
        exported = self.review.export_return(out=out, returns=out / 'returns')
        self.assertTrue(exported['complete_round1'])
        with ZipFile(exported['path']) as archive:
            data = json.loads(archive.read('return_manifest.json'))
            self.assertEqual(data['source_manifest_sha256'], self.p.sha(out / 'manifest.json'))
            import hashlib
            for name, digest in data['files_sha256'].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest)
            self.assertFalse(any(name.endswith('.png') for name in archive.namelist()))
        self.assertEqual(self.s.progress()['valid_round1'], 0)
        self.results['synthetic_save_duplicate_guard_and_return'] = 'PASS; production answers untouched'


if __name__ == '__main__':
    unittest.main(verbosity=2)
