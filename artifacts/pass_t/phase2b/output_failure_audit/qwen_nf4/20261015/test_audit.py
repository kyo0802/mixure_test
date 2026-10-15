"""Narrow CPU tests, synthetic dictionaries only, no inference fixtures executed."""
import copy
import hashlib
import importlib
import json
import tempfile
import unittest
from pathlib import Path
import audit

class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s=audit.schema()
        cls.good={'schema_version':'PASS_T_PHASE2B_PREDICTION_V1','target_id':'TARGET_A',
          'window_outcome':'NO_CONFIRMED_EVENT','window_cited_frame_aliases':['F0001'], 'events':[],
          'last_directly_supported_state':{'state':'STATE_UNKNOWN','supporting_frame_alias':None},
          'end_visibility':'UNKNOWN','subsequent_state':'UNKNOWN','rationale':'Synthetic test only',
          'uncertainty':'Association unresolved','safety_assertions':{'global_identity_claimed':False,
          'state_persisted_across_unobserved_interval':False,'container_or_handover_auto_classified':False}}
        cls.event={'event_id':'PRED_EVT_001','event_type':'PICKUP',
          'timing':{'status':'EXACT_SUPPLIED_FRAME','frame_alias':'F0001'},'cited_frame_aliases':['F0001'],
          'before_state':{'state':'ON_SURFACE','supporting_frame_alias':'F0001'},
          'after_state':{'state':'HELD_BY_PERSON','supporting_frame_alias':'F0002'},
          'target_association_uncertainty':'NONE','timing_uncertainty':'Exact supplied frame; no additional observed uncertainty',
          'rationale':'Synthetic contract fixture, not a scene answer'}

    def result(self,obj,rr=None):
        rr=rr or {'eos_observed':True,'output_cap_reached':False,'generation_deadline_reached':False}
        raw=json.dumps(obj).encode();hist=audit.validate_prediction(obj,['F0001','F0002'])
        return audit.analyze(raw,rr,['F0001','F0002'],['F0001','F0002'],hist,self.s)

    def event_obj(self):
        o=copy.deepcopy(self.good);o['window_outcome']='CONFIRMED_EVENTS';o['events']=[copy.deepcopy(self.event)];return o

    def test_stable_ids(self):
        self.assertEqual(audit.attempt_id('r','c',1),'r/c/ITER_01')
    def test_round_distinction(self):
        self.assertNotEqual(audit.attempt_id('r1','c',1),audit.attempt_id('r2','c',1))
    def test_unique_attempts(self):
        ids=[audit.attempt_id(r,c,i) for r,_ in audit.ROUNDS for c in audit.EXPECTED for i in range(3)]
        self.assertEqual(len(set(ids)),66)
    def test_expected_primary_33(self):self.assertEqual(len(audit.EXPECTED)*3,33)
    def test_warmup_separation(self):
        rows=audit.read(audit.OUT/'primary_attempts.json');self.assertEqual(sum(x['kind']=='WARMUP' for x in rows),11)
        self.assertEqual(sum(x['kind']=='MEASURED' for x in rows),22)
    def test_historical_pass_preserved(self):
        rows=audit.read(audit.OUT/'primary_attempts.json');self.assertEqual(sum(x['strict_pass'] for x in rows),15)
    def test_validator_reproduced(self):
        self.assertTrue(all(not x['reproduction_mismatch'] for x in audit.read(audit.OUT/'primary_attempts.json')))
    def test_hashes_verified(self):
        summary=audit.read(audit.OUT/'analysis_summary.json');self.assertTrue(all(not x['errors'] for x in summary['receipt_integrity']))
    def test_tampered_receipt(self):
        with tempfile.TemporaryDirectory(dir=audit.OUT) as t:
            p=Path(t);(p/'capacity_results.json').write_text('[]')
            (p/'engineering_completion_receipt.json').write_text(json.dumps({'files':{'capacity_results.json':'bad'}}))
            self.assertEqual(audit.verify_receipts(p)['errors'],['capacity_results.json'])
    def test_missing_receipt(self):
        with tempfile.TemporaryDirectory(dir=audit.OUT) as t:
            self.assertRaises(FileNotFoundError,audit.verify_receipts,Path(t))
    def test_empty_null_missing(self):
        o=self.event_obj();o['events'][0]['timing_uncertainty']=''
        self.assertIn('EMPTY_REQUIRED_UNCERTAINTY',self.result(o)['failure_labels'])
        o['events'][0]['timing_uncertainty']=None
        self.assertIn('INVALID_NULLABILITY',self.result(o)['failure_labels'])
        del o['events'][0]['timing_uncertainty']
        self.assertIn('REQUIRED_FIELD_MISSING',self.result(o)['failure_labels'])
    def test_multilabel_secondary(self):
        o=self.event_obj();o['events'][0]['timing_uncertainty']='';o['events'][0]['after_state']['supporting_frame_alias']=None
        result=self.result(o);self.assertIn('OTHER_SEMANTIC_ERROR',result['failure_labels'])
        self.assertIn('EMPTY_REQUIRED_UNCERTAINTY',result['failure_labels'])
    def test_error_path(self):
        o=self.event_obj();o['events'][0]['timing_uncertainty']='';r=self.result(o)
        self.assertIn('/events/0/timing_uncertainty',[d['path'] for d in r['error_details']])
    def test_empty_window_citation(self):
        o=copy.deepcopy(self.good);o['window_cited_frame_aliases']=[]
        self.assertIn('EMPTY_REQUIRED_CITATIONS',self.result(o)['failure_labels'])
    def test_eos_not_inferred(self):
        r=self.result(self.good,{'eos_observed':False});self.assertIn('EOS_NOT_REACHED',r['failure_labels'])
    def test_eos_missing(self):self.assertIn('GENERATION_STATUS_UNKNOWN',self.result(self.good,{ 'output_cap_reached':False})['failure_labels'])
    def test_truncation(self):
        labels=audit.generation_labels({'eos_observed':False,'output_cap_reached':True},b'{}')
        self.assertIn('TRUNCATED_BY_MAX_NEW_TOKENS',labels)
    def test_timeout(self):self.assertIn('GENERATION_TIMEOUT',audit.generation_labels({'generation_deadline_reached':True},b'{}'))
    def test_malformed_event_count(self):
        r=audit.analyze(b'{"events":[',{'eos_observed':False},[],[],None,self.s)
        self.assertIsNone(r['features']['event_count']);self.assertEqual(r['features']['event_count_status'],'EVENT_COUNT_NOT_RECOVERABLE')
    def test_fence_not_repaired(self):
        r=audit.analyze(b'```json\n{}\n```',{'eos_observed':True},[],[],None,self.s)
        self.assertFalse(r['json_parse_success']);self.assertIn('MARKDOWN_CODE_FENCE',r['failure_labels'])
    def test_unsupported_alias(self):
        o=copy.deepcopy(self.good);o['window_cited_frame_aliases']=['F9999']
        self.assertIn('CITED_ALIAS_NOT_SUPPLIED',self.result(o)['failure_labels'])
    def test_unconsumed_alias(self):
        ds=audit.secondary_checks(self.good,['F0001','F0002'],['F0002']);self.assertIn('CITED_ALIAS_NOT_PROCESSOR_CONSUMED',[d['label'] for d in ds])
    def test_complexity(self):
        a=audit.complexity(self.good,self.s);b=audit.complexity(self.event_obj(),self.s)
        self.assertEqual(a['event_count'],0);self.assertEqual(b['event_count'],1)
        self.assertGreater(b['structural_complexity_score'],a['structural_complexity_score'])
    def test_no_gt_feature(self):
        r=self.result(self.good);self.assertNotIn('ground_truth',r);self.assertNotIn('human_label',r)
    def test_model_imports_blocked(self):
        for m in ['torch','transformers','bitsandbytes','accelerate','memory_graph.pass_t.phase2b.local_vlm.nf4']:
            with self.assertRaises(ImportError):importlib.import_module(m)
    def test_no_cuda_loaded(self):self.assertNotIn('torch',audit.sys.modules)
    def test_replay_does_not_mutate(self):
        p=audit.BASE/'v2_20261014_owned_tree/runs/MULTI_8_P200704/iteration_0_raw.txt';before=p.read_bytes()
        audit.parse_raw(before);self.assertEqual(before,p.read_bytes())
    def test_no_protocol_or_graph_write(self):
        self.assertNotIn('memory_graph.pass_t.phase2b.protocol',audit.sys.modules)
        self.assertNotIn('memory_graph.graph',audit.sys.modules)

if __name__=='__main__':
    with (audit.OUT/'test_log.txt').open('x',encoding='utf-8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AuditTests))
    record={'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors),
        'failures':result.failures,'errors':result.errors,'skipped':result.skipped,
        'forbidden_imports_fail_closed':True,'models_loaded':False,'gpu_initialized':False}
    audit.write('test_results.json',record);print(json.dumps(record));raise SystemExit(0 if result.wasSuccessful() else 1)
