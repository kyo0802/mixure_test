"""CPU byte-file cache tests; no model load, visual fixtures or CUDA."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from memory_graph.integration.nemotron_assets import verify_assets, POLICY


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.model=self.root/'model';self.model.mkdir();self.asset=self.model/'config.json'
        self.asset.write_bytes(b'original')
        self.spec=dict(policy_version=POLICY,repository='CPU_MOCK',revision='mock_revision',
            assets=[dict(name='config.json',size=8,sha256=hashlib.sha256(b'original').hexdigest())])
        self.manifest=self.root/'manifest.json';self.receipt=self.root/'receipt.json';self.write()
    def tearDown(self):self.tmp.cleanup()
    def write(self):self.manifest.write_text(json.dumps(self.spec))
    def run_verify(self,**kw):return verify_assets(self.model,self.manifest,self.receipt,**kw)
    def test_cold_then_cached_no_second_hash(self):
        self.assertEqual(self.run_verify()['validation_kind'],'FRESH_SHA256')
        with patch('memory_graph.integration.nemotron_assets.digest',side_effect=AssertionError('Must not rehash')):
            self.assertEqual(self.run_verify()['validation_kind'],'CACHED_METADATA')
    def test_force_and_strict_rehash(self):
        self.run_verify()
        for args in [dict(force=True),dict(mode='strict')]:self.assertEqual(self.run_verify(**args)['fresh_files'],['config.json'])
    def test_modified_metadata_requires_full_hash(self):
        self.run_verify();s=self.asset.stat();os.utime(self.asset,ns=(s.st_atime_ns,s.st_mtime_ns+1000000))
        self.assertEqual(self.run_verify()['validation_kind'],'FRESH_SHA256')
    def test_known_mismatch_tombstones_success(self):
        self.run_verify();self.asset.write_bytes(b'wrong!!!')
        with self.assertRaisesRegex(ValueError,'SHA256_MISMATCH'):self.run_verify()
        self.assertEqual(json.loads(self.receipt.read_text())['outcome'],'FAILED')
        self.asset.write_bytes(b'original');self.assertEqual(self.run_verify()['validation_kind'],'FRESH_SHA256')
    def test_changed_revision_and_manifest_rehash(self):
        self.run_verify();self.spec['revision']='new_mock_revision';self.write()
        self.assertEqual(self.run_verify()['fresh_files'],['config.json'])
    def test_corrupt_or_wrong_receipt_rehashes(self):
        for raw in ['bad json','[]','null','{"outcome":"VERIFIED"}']:
            self.receipt.write_text(raw);self.assertEqual(self.run_verify()['validation_kind'],'FRESH_SHA256')
    def test_asset_set_size_and_policy_fail_closed(self):
        self.run_verify();extra=self.model/'extra.py';extra.write_text('x')
        with self.assertRaisesRegex(ValueError,'SET_CHANGED'):self.run_verify()
        extra.unlink();self.asset.write_bytes(b'x')
        with self.assertRaisesRegex(ValueError,'SIZE_MISMATCH'):self.run_verify()
        self.spec['policy_version']='other';self.write()
        with self.assertRaisesRegex(ValueError,'INVALID_ASSET_MANIFEST'):self.run_verify()
    def test_pinned_real_manifest_matches_historical_hashes(self):
        spec=json.loads((ROOT/'config/findmind_nemotron_assets.json').read_text())
        historical=ROOT/'artifacts/findmind_sessions/video_932b70d6ece1c5b31493_20261020T223911Z_3e1a9e/vlm/runtime.json'
        if not historical.exists():self.skipTest('Local historical receipt required')
        self.assertEqual({a['name']:a['sha256'] for a in spec['assets']},json.loads(historical.read_text())['model_asset_hashes'])

    def test_malformed_success_receipt_not_trusted(self):
        self.run_verify();r=json.loads(self.receipt.read_text());r['files']['config.json']['verified_utc']='invalid'
        self.receipt.write_text(json.dumps(r));self.assertEqual(self.run_verify()['validation_kind'],'FRESH_SHA256')

    def test_asset_moved_or_missing_fails_closed(self):
        self.run_verify();self.asset.unlink()
        with self.assertRaisesRegex(ValueError,'SET_CHANGED'):self.run_verify()

    def test_worker_still_uses_phase7_session_and_existing_timeout_policy(self):
        from unittest.mock import MagicMock
        sys.path.insert(0,str(ROOT/'artifacts/pass_i/runtime/vendor'))
        from memory_graph.integration.fresh_video import run_worker
        child=MagicMock();child.pid=123;child.wait.return_value=0
        session=self.root/'session';session.mkdir()
        with patch('memory_graph.integration.fresh_video.subprocess.Popen',return_value=child) as launch:
            r=run_worker(ROOT,session,'nemotron',900)
        self.assertEqual(r['status'],'COMPLETE')
        command=launch.call_args.args[0];self.assertTrue(any('run_findmind_nemotron.py' in s for s in command))
        self.assertIn('--session',command);child.wait.assert_called_once_with(timeout=900)
        if os.name=='nt':self.assertIn('FINDMIND_NEMOTRON_VERIFICATION=cached',command)
        events=[json.loads(l) for l in (session/'nemotron_process_timing.jsonl').read_text().splitlines()]
        self.assertEqual([e['stage'] for e in events],['parent_launch_begin','subprocess_created','subprocess_exited'])

    def test_worker_unavailable_not_retried(self):
        sys.path.insert(0,str(ROOT/'artifacts/pass_i/runtime/vendor'))
        from memory_graph.integration.fresh_video import run_worker
        session=self.root/'session';session.mkdir()
        with patch('memory_graph.integration.fresh_video.subprocess.Popen',side_effect=OSError('CPU_MOCK_MISSING_RUNTIME')) as launch:
            with self.assertRaisesRegex(OSError,'MISSING_RUNTIME'):run_worker(ROOT,session,'nemotron',900)
        self.assertEqual(launch.call_count,1)

    def test_strict_mode_forwarded_to_wsl_and_invalid_mode_rejected(self):
        from unittest.mock import MagicMock
        sys.path.insert(0,str(ROOT/'artifacts/pass_i/runtime/vendor'))
        from memory_graph.integration.fresh_video import run_worker
        session=self.root/'session';session.mkdir();child=MagicMock();child.pid=123;child.wait.return_value=0
        with patch.dict(os.environ,{'FINDMIND_NEMOTRON_VERIFICATION':'strict','FINDMIND_NEMOTRON_FORCE_VERIFY':'1'}),\
                patch('memory_graph.integration.fresh_video.subprocess.Popen',return_value=child) as launch:
            run_worker(ROOT,session,'nemotron',900)
            if os.name=='nt':
                self.assertIn('FINDMIND_NEMOTRON_VERIFICATION=strict',launch.call_args.args[0])
                self.assertIn('FINDMIND_NEMOTRON_FORCE_VERIFY=1',launch.call_args.args[0])
        with patch.dict(os.environ,{'FINDMIND_NEMOTRON_VERIFICATION':'disabled'}):
            with self.assertRaisesRegex(ValueError,'INVALID_NEMOTRON'):run_worker(ROOT,session,'nemotron',900)

    def test_temporal_prompt_and_generation_contract_unchanged(self):
        # Compare meaningful model-input ASTs to the already committed Phase9 baseline.
        import ast,subprocess
        f='src/memory_graph/integration/nemotron_video.py'
        old=subprocess.run(['git','show','10357b07:'+f],cwd=ROOT,capture_output=True,text=True,check=True).stdout
        new=(ROOT/f).read_text()
        def assignments(source):
            names={'mapping','body','messages','metadata','settings'}
            return {n.targets[0].id:ast.dump(n.value) for n in ast.walk(ast.parse(source))
                if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in names}
        self.assertEqual(assignments(old),assignments(new))
        def calls(source):return [ast.dump(n) for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call)
            and ((isinstance(n.func,ast.Name) and n.func.id=='SamplingParams')
                or (isinstance(n.func,ast.Attribute) and n.func.attr=='generate'))]
        self.assertEqual(calls(old),calls(new))

if __name__=='__main__':unittest.main()
