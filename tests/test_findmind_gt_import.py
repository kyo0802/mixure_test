"""Isolated synthetic labels only. Never writes to real human GT collections."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from findmind_gt_contract import TOOL,ATTESTATIONS,exhaustiveness,load_json,validate_bundle
from import_findmind_gt import collect,finalize

class OfflineGTTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=load_json(TOOL/'manifest.json')
        cls.fixture=json.loads(subprocess.check_output(['node','tests/test_findmind_gt_contract.cjs','--export-fixture'],cwd=ROOT,text=True,encoding='utf8'))
        cls.tmp_root=ROOT/'.annotation_test_tmp';cls.tmp_root.mkdir(exist_ok=True)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=self.tmp_root,prefix='ISOLATED_SOFTWARE_TEST_');self.base=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup);self.input=self.base/'input';self.input.mkdir()
    def put(self,name,data):
        p=self.input/name;p.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8');return p
    def full(self,d):
        v=d['videos'][0];v['review_status']='EXHAUSTIVELY_REVIEWED';v['reviewed_intervals']=[{'interval_id':'MOCK_FULL_INTERVAL','start_s':0,'end_s':v['source_duration_s'],'notes':'SOFTWARE TEST ONLY'}]
        for k in ATTESTATIONS:v['coverage_attestations'][k]=True
        v['event_list_exhaustiveness']=exhaustiveness(v)
        return d
    def collection(self,data=None):
        self.put('a.json',data or self.fixture);out=self.base/'collection';collect(self.input,out,self.manifest);return out
    def test_node_export_validates_in_python(self):
        self.assertEqual(validate_bundle(self.fixture,self.manifest),[])
    def test_duplicate_export_preserves_original_bytes(self):
        a=self.put('a.json',self.fixture);d=copy.deepcopy(self.fixture);d['exported_at']='2026-10-18T00:00:00Z';b=self.put('duplicate.json',d)
        out=self.base/'collection';summary=collect(self.input,out,self.manifest)
        self.assertEqual(summary['valid_unique_submissions'],1);self.assertEqual(summary['duplicate_submissions'],1)
        self.assertEqual(len(list((out/'submissions').glob('*.json'))),2)
        self.assertIn(a.read_bytes(),[p.read_bytes() for p in (out/'submissions').glob('*.json')]);self.assertIn(b.read_bytes(),[p.read_bytes() for p in (out/'submissions').glob('*.json')])
    def test_two_reviewers_disagreement_and_original_labels(self):
        self.put('a.json',self.fixture);b=copy.deepcopy(self.fixture);b['reviewer_id']='ISOLATED_TEST_B';b['session_id']='MOCK_SESSION_B';b['videos'][0]['events'][0].update(event_id='MOCK_EVENT_B',type='PLACEMENT',start_s=1.1,end_s=2.2,before_state='HELD_BY_PERSON',after_state='ON_SURFACE');b['videos'][0]['states'][0]['state_id']='MOCK_STATE_B';b['videos'][0]['states'][0]['physical_state']='HELD_BY_PERSON';self.put('b.json',b)
        out=self.base/'collection';summary=collect(self.input,out,self.manifest)
        self.assertEqual(summary['valid_unique_submissions'],2);self.assertEqual(summary['event_records'],2);self.assertGreater(summary['correspondences_with_differences'],0)
        records=load_json(out/'collection.json')['by_video']['test1']['events'];self.assertEqual({r['record']['type'] for r in records},{'PICKUP','PLACEMENT'})
        self.assertIn('TYPE_DIFFERENCE',(out/'event_correspondence.csv').read_text(encoding='utf-8-sig'))
        self.assertIn('STATE_DIFFERENCE',(out/'state_comparison.csv').read_text(encoding='utf-8-sig'))
    def test_wrong_source_rejected(self):
        d=copy.deepcopy(self.fixture);d['videos'][0]['source_sha256']='0'*64;self.put('bad.json',d)
        summary=collect(self.input,self.base/'collection',self.manifest);self.assertEqual(summary['rejected_submissions'],1);self.assertEqual(summary['valid_unique_submissions'],0)
    def test_session_revisions_are_not_silently_selected(self):
        self.put('a.json',self.fixture);b=copy.deepcopy(self.fixture);b['videos'][0]['events'][0]['notes']='DIFFERENT TEST REVISION';b['updated_at']='2026-10-18T01:00:00Z';self.put('b.json',b)
        summary=collect(self.input,self.base/'collection',self.manifest);self.assertEqual(summary['session_revision_conflicts'],1);self.assertEqual(summary['event_records'],2)
    def test_unresolved_produces_no_authoritative_gt(self):
        out=self.collection();target=self.base/'unresolved.json';summary=finalize(out,out/'adjudication.json',target,self.manifest)
        self.assertEqual(summary['authoritative_events'],0);self.assertEqual(summary['eligible_coverage_videos'],0);self.assertEqual(load_json(target)['truth'],[])
    def test_explicit_event_without_exhaustive_coverage_is_descriptive_only(self):
        out=self.collection();adj=load_json(out/'adjudication.json');row=adj['events'][0];row.update(decision='ACCEPT',final_event_id='MOCK_FINAL_EVENT',reviewed_object_id='test1:MOCK_OBJECT',evidence_supported=True,target_identity_confirmed=True,adjudicator_id='ISOLATED_TEST_OWNER');p=self.base/'decisions.json';p.write_text(json.dumps(adj),encoding='utf8');target=self.base/'limited.json'
        summary=finalize(out,p,target,self.manifest);self.assertEqual(summary['authoritative_events'],0);self.assertEqual(summary['non_exhaustive_supported_events'],1)
    def test_explicit_full_adjudication_exports_existing_evaluator_shape(self):
        out=self.collection(self.full(copy.deepcopy(self.fixture)));adj=load_json(out/'adjudication.json');adj['events'][0].update(decision='ACCEPT',final_event_id='MOCK_FINAL_EVENT',reviewed_object_id='test1:MOCK_OBJECT',evidence_supported=True,target_identity_confirmed=True,adjudicator_id='ISOLATED_TEST_OWNER')
        c=adj['coverage'][0];c.update(decision='ACCEPT_EXHAUSTIVE',adjudicator_id='ISOLATED_TEST_OWNER');c['attestations']={k:True for k in ATTESTATIONS}
        p=self.base/'decisions.json';p.write_text(json.dumps(adj),encoding='utf8');target=self.base/'final.json';summary=finalize(out,p,target,self.manifest)
        self.assertEqual(summary['authoritative_events'],1);self.assertEqual(summary['eligible_coverage_videos'],1)
        sys.path.insert(0,str(ROOT/'src'));from memory_graph.experiments.three_vlm_evaluation import eligible_coverage
        self.assertTrue(eligible_coverage(load_json(target)['coverage'][0]));self.assertEqual(load_json(target)['truth'][0]['review_status'],'HUMAN_REVIEWED')
    def test_coverage_cannot_bypass_unresolved_event(self):
        out=self.collection(self.full(copy.deepcopy(self.fixture)));adj=load_json(out/'adjudication.json');adj['coverage'][0].update(decision='ACCEPT_EXHAUSTIVE',adjudicator_id='ISOLATED_TEST_OWNER');adj['coverage'][0]['attestations']={k:True for k in ATTESTATIONS};p=self.base/'decisions.json';p.write_text(json.dumps(adj),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'Unresolved'):finalize(out,p,self.base/'bad_final.json',self.manifest)
    def test_collection_label_tampering_rejected(self):
        out=self.collection();p=out/'collection.json';c=load_json(p);c['by_video']['test1']['events'][0]['record']['notes']='TAMPERED';p.write_text(json.dumps(c),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'differ from original'):finalize(out,out/'adjudication.json',self.base/'bad_final.json',self.manifest)
    def test_overwrite_existing_collection_refused(self):
        out=self.collection()
        with self.assertRaises(ValueError):collect(self.input,out,self.manifest)
    def test_adjudicated_state_requires_and_preserves_final_state_id(self):
        out=self.collection();adj=load_json(out/'adjudication.json');adj['states'][0].update(decision='ACCEPT',final_state_id='MOCK_FINAL_STATE',reviewed_object_id='test1:MOCK_OBJECT',evidence_supported=True,adjudicator_id='ISOLATED_TEST_OWNER');p=self.base/'decisions.json';p.write_text(json.dumps(adj),encoding='utf8');target=self.base/'state_final.json'
        summary=finalize(out,p,target,self.manifest);self.assertEqual(summary['explicitly_adjudicated_states'],1);self.assertEqual(load_json(target)['states'][0]['state_id'],'MOCK_FINAL_STATE')
    def test_explicit_same_final_event_merges_sources_without_voting(self):
        a=self.full(copy.deepcopy(self.fixture));self.put('a.json',a);b=copy.deepcopy(a);b['reviewer_id']='ISOLATED_TEST_B';b['session_id']='MOCK_SESSION_B';self.put('b.json',b);out=self.base/'collection';collect(self.input,out,self.manifest);adj=load_json(out/'adjudication.json')
        for row in adj['events']:row.update(decision='ACCEPT',final_event_id='MOCK_SAME_FINAL_EVENT',reviewed_object_id='test1:MOCK_OBJECT',evidence_supported=True,target_identity_confirmed=True,adjudicator_id='ISOLATED_TEST_OWNER')
        adj['coverage'][0].update(decision='ACCEPT_EXHAUSTIVE',adjudicator_id='ISOLATED_TEST_OWNER',attestations={k:True for k in ATTESTATIONS});p=self.base/'decisions.json';p.write_text(json.dumps(adj),encoding='utf8');target=self.base/'final.json';summary=finalize(out,p,target,self.manifest)
        self.assertEqual(summary['authoritative_events'],1);self.assertEqual(len(load_json(target)['truth'][0]['source_refs']),2);self.assertEqual(len(load_json(target)['source_submissions']),2)
    def test_zero_event_requires_explicit_eligible_coverage(self):
        a=self.full(copy.deepcopy(self.fixture));a['videos'][0]['events']=[];out=self.collection(a);adj=load_json(out/'adjudication.json');adj['coverage'][0].update(decision='ACCEPT_EXHAUSTIVE',adjudicator_id='ISOLATED_TEST_OWNER',attestations={k:True for k in ATTESTATIONS});p=self.base/'decisions.json';p.write_text(json.dumps(adj),encoding='utf8');target=self.base/'negative.json';summary=finalize(out,p,target,self.manifest)
        self.assertEqual(summary['authoritative_events'],0);self.assertEqual(summary['eligible_coverage_videos'],1)
    def test_gap_prevents_owner_from_bypassing_source_exhaustiveness(self):
        a=self.full(copy.deepcopy(self.fixture));v=a['videos'][0];v['uncertain_intervals']=[{'uncertainty_id':'MOCK_GAP','start_s':3,'end_s':4,'reason':'TEST GAP','could_conceal_event':True,'identity_uncertain':False}];v['event_list_exhaustiveness']=exhaustiveness(v);out=self.collection(a);adj=load_json(out/'adjudication.json');adj['events'][0].update(decision='REJECT',adjudicator_id='ISOLATED_TEST_OWNER',notes='TEST ONLY');adj['coverage'][0].update(decision='ACCEPT_EXHAUSTIVE',adjudicator_id='ISOLATED_TEST_OWNER',attestations={k:True for k in ATTESTATIONS});p=self.base/'decisions.json';p.write_text(json.dumps(adj),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'No human submission'):finalize(out,p,self.base/'bad_final.json',self.manifest)
    def test_actual_owner_cli_collect_and_finalize_unresolved(self):
        self.put('a.json',self.fixture);out=self.base/'cli_collection'
        collected=subprocess.run([sys.executable,'-B','scripts/import_findmind_gt.py','--input-dir',str(self.input),'--output-dir',str(out)],cwd=ROOT,capture_output=True,text=True,encoding='utf8')
        self.assertEqual(collected.returncode,0,collected.stderr);self.assertEqual(json.loads(collected.stdout)['valid_unique_submissions'],1)
        target=self.base/'cli_final.json';finished=subprocess.run([sys.executable,'-B','scripts/import_findmind_gt.py','--finalize',str(out),'--adjudication',str(out/'adjudication.json'),'--output',str(target)],cwd=ROOT,capture_output=True,text=True,encoding='utf8')
        self.assertEqual(finished.returncode,0,finished.stderr);self.assertEqual(load_json(target)['truth'],[])

if __name__=='__main__':unittest.main()
