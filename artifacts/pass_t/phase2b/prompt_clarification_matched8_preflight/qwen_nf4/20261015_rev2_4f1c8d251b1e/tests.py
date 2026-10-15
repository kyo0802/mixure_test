import core
import copy,json,re,unittest,ast
from collections import Counter
import fixture_generator as gen
from diagnostics.collect_all_prediction_violations import collect
from memory_graph.pass_t.phase2b.predictions import parse_raw,schema,validate_prediction
from step2 import time_audit,outcome

class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=[json.loads(s) for s in (core.OUT/'COLLECT_ALL_ATTEMPT_VIOLATIONS.jsonl').read_text().splitlines()]
        cls.lock=core.read(core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json')
        cls.fixtures=core.read(core.OUT/'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json')['scenarios']
        cls.results=core.read(core.OUT/'matched8_results.json')
        cls.prompt=(core.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt').read_text()
        cls.good=parse_raw((core.ROOT/next(x['raw_path'] for x in cls.rows if x['reproduced_strict']['valid'])).read_bytes())
    def test_33_inventory(self):self.assertEqual(len(self.rows),33)
    def test_unique(self):self.assertEqual(len({x['attempt_id'] for x in self.rows}),33)
    def test_warmup(self):self.assertEqual(sum(x['kind']=='WARMUP' for x in self.rows),11)
    def test_measured(self):self.assertEqual(sum(x['kind']=='MEASURED' for x in self.rows),22)
    def test_raw_hashes(self):
        for x in self.rows:self.assertEqual(core.sha(core.ROOT/x['raw_path']),x['raw_sha256'])
    def test_original_result(self):self.assertTrue(all(x['original_strict']==x['reproduced_strict'] for x in self.rows))
    def test_15_pass(self):self.assertEqual(sum(x['reproduced_strict']['valid'] for x in self.rows),15)
    def test_g2(self):self.assertTrue(all((not x['violations'])==x['reproduced_strict']['valid'] for x in self.rows))
    def test_g3(self):self.assertTrue(all(x['strict_first_error']==x['shadow_first_error'] for x in self.rows))
    def test_g4(self):
        f=core.read(core.OUT/'diagnostics/frequencies.json');self.assertEqual(f['masked_attempts'],11)
        self.assertEqual(f['masked_individual_violations'],20)
    def test_g5(self):self.assertTrue(core.authorities())
    def test_no_shadow_override(self):
        self.assertEqual(sum(bool(x['violations']) for x in self.rows),18)
    def test_rule_states(self):
        allowed={'VIOLATED','SATISFIED','NOT_APPLICABLE','NOT_EVALUABLE'}
        self.assertTrue(all(p['status'] in allowed for x in self.rows for p in x['shadow_predicates']))
    def test_no_events_na(self):
        p=collect(self.good,['F0001'],schema());self.assertTrue(any(x['rule_id']=='EVENT_STATE_SUPPORT' and x['status']=='NOT_APPLICABLE' for x in p))
    def test_bad_events_dependency(self):
        g=copy.deepcopy(self.good);g['events']=[None]
        p=collect(g,['F0001'],schema());self.assertTrue(any(x['rule_id']=='EVENT_STATE_SUPPORT' and x['status']=='NOT_EVALUABLE' for x in p))
        self.assertFalse(any(x['rule_id']=='KNOWN_STATE_SUPPORT' and x['status']=='VIOLATED' for x in p))
    def test_missing_inventory_ne(self):
        p=collect(self.good,None,schema());self.assertTrue(any(x['rule_id']=='CITATION_MEMBERSHIP' and x['status']=='NOT_EVALUABLE' for x in p))
    def test_wrongtype_target_ne(self):
        g=copy.deepcopy(self.good);g['events']=[{'target_association_uncertainty':[],'timing':{'status':[]}}]
        p=collect(g,['F0001'],schema());self.assertTrue(any(x['rule_id']=='TARGET_ASSOCIATION_ENUM' and x['status']=='NOT_EVALUABLE' for x in p))
    def test_known_state_breakdown(self):
        paths=[v['json_path'] for r in self.rows for v in r['violations'] if v['rule_id']=='KNOWN_STATE_SUPPORT']
        self.assertEqual(len(paths),20);self.assertTrue(any(p=='/last_directly_supported_state' for p in paths))
    def test_fixture_count(self):self.assertEqual(len(self.fixtures),7)
    def test_fixture_strata(self):self.assertEqual(Counter(x['intended_stratum'] for x in self.fixtures),Counter({'SYNTHETIC_0_EVENT':2,'SYNTHETIC_1_EVENT':2,'SYNTHETIC_2_EVENT':2,'WARMUP':1}))
    def test_fixture_distinct(self):self.assertEqual(len({x['fixture_id'] for x in self.fixtures}),7)
    def test_fixture_eight(self):self.assertTrue(all(len(x['frames'])==8 for x in self.fixtures))
    def test_fixture_regeneration(self):
        for f in self.fixtures:
            for i,x in enumerate(f['frames']):self.assertEqual(core.byte_sha(gen.render(f['seed'],f['script'],i).tobytes()),x['canonical_rgb_pixel_sha256'])
    def test_lock_hashes(self):
        for n,h in self.lock['model_visible_frames_sha256'].items():self.assertEqual(core.sha(core.OUT/n),h)
    def test_lock_manifest(self):self.assertEqual(core.sha(core.OUT/'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json'),self.lock['fixture_manifest_sha256'])
    def test_lock_before_prompt_chain(self):
        receipt=core.read(core.OUT/'prompt_candidate/receipt.json');self.assertEqual(receipt['fixture_lock_receipt_sha256'],core.sha(core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json'))
        self.assertTrue(self.lock['prompt_file_absent_at_lock'])
    def test_no_old_images(self):
        b=core.ROOT/'artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/fixtures'
        old={h for p in b.glob('*/fixture.json') for h in core.read(p)['source_frame_pixel_digests']}
        self.assertFalse(old & {x['canonical_rgb_pixel_sha256'] for f in self.fixtures for x in f['frames']})
    def test_no_real_fixture_source(self):
        tree=ast.parse((core.OUT/'fixture_generator.py').read_text())
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='open' for n in ast.walk(tree)))
    def test_opaque_names(self):
        self.assertTrue(all(re.fullmatch(r'X_[0-9a-f]{16}',f['fixture_id']) for f in self.fixtures))
        self.assertTrue(all(re.fullmatch(r'F\d{4}\.png',core.Path(x['path']).name) for f in self.fixtures for x in f['frames']))
    def test_prompt_hash(self):self.assertEqual(core.byte_sha(self.prompt.encode()),core.read(core.OUT/'prompt_candidate/receipt.json')['prompt_sha256'])
    def test_pending_clause_absent(self):
        self.assertNotIn('Under TARGET_REFERENCE_NONE',self.prompt);self.assertNotIn('unique physical instance',self.prompt)
    def test_no_fixture_literals(self):
        for f in self.fixtures:
            for lit in [f['fixture_id'],str(f['seed']),f['intended_stratum']]:self.assertNotIn(lit,self.prompt)
    def test_no_new_fields(self):
        for field in ['timing_uncertainty','window_cited_frame_aliases','supporting_frame_alias','subsequent_state']:
            self.assertIn(field,self.prompt)
        self.assertIn('Do not add fields',self.prompt)
    def test_nonempty_uncertainty_contract(self):self.assertEqual(schema()['properties']['events']['items']['properties']['timing_uncertainty']['minLength'],1)
    def test_citation_contract(self):self.assertEqual(schema()['properties']['window_cited_frame_aliases']['minItems'],1)
    def test_target_clause_acceptance(self):self.assertTrue(core.read(core.OUT/'conditional_clauses/identity_acceptance_cpu_fixture.json')['validation']['valid'])
    def test_no_gt_prompt(self):
        for word in ['PT2A_','test5','test7','S000','SYNTHETIC_','reviewer_']:self.assertNotIn(word,self.prompt)
    def test_six_dev(self):self.assertEqual(sum(x['kind']=='DEV' for x in self.results),6)
    def test_six_synthetic(self):self.assertEqual(sum(x['kind']=='SYNTHETIC_EVAL' for x in self.results),6)
    def test_one_warmup(self):self.assertEqual(sum(x['kind']=='WARMUP' for x in self.results),1)
    def test_no_test3(self):self.assertFalse(any(x.get('source')=='test3' for x in self.results))
    def test_uniform_agreement(self):self.assertTrue(all(x['prior_uniform_agreement'] is True for x in self.results if x['kind']=='DEV'))
    def test_same_sources(self):self.assertTrue(all(x['checks']['FRAME_SOURCE_MATCH'] and x['checks']['FRAME_ORDER_MATCH'] for x in self.results))
    def test_processor_selection(self):self.assertTrue(all(x['checks']['PROCESSOR_SELECTED_FRAME_MATCH'] for x in self.results))
    def test_temporal_patch(self):self.assertTrue(all(x['budgets']['VIDEO']['temporal_patches']==4 and x['budgets']['VIDEO']['temporal_padding']==0 for x in self.results))
    def test_native_mapping(self):self.assertTrue(all(x['checks']['NATIVE_TIME_MAPPING_VERIFIED'] and len(x['lineage'])==8 for x in self.results))
    def test_native_video_not_multi(self):self.assertTrue(all('video_grid_thw' in x['budgets']['VIDEO'] for x in self.results))
    def test_alias_inventory(self):self.assertTrue(all(len(x['budgets']['VIDEO']['supplied_aliases'])==8 for x in self.results))
    def test_time_distortion(self):
        t=time_audit([i*.5 for i in range(8)],2,2);self.assertEqual(t['max_abs_nominal_deviation_s'],0);self.assertEqual(t['max_abs_model_patch_deviation_s'],.5)
    def test_perturbed_pts_frame_only(self):
        times=[0,.4,.9,1.6,2.,2.7,3.3,3.5];t=time_audit(times,2,2)
        self.assertEqual(outcome(True,True,True,True,True,t['max_abs_model_patch_deviation_s']),'FRAME_MATCHED_ONLY')
    def test_perturbed_selection_notmatched(self):self.assertEqual(outcome(True,True,False,True,True,.05),'NOT_MATCHED')
    def test_unverified_notmatched(self):self.assertEqual(outcome(True,True,None,True,True,None),'NOT_MATCHED')
    def test_fullmatch_path(self):self.assertEqual(outcome(True,True,True,True,True,.05),'FULLY_MATCHED')
    def test_frameonly_path(self):self.assertEqual(outcome(True,True,True,True,True,.5),'FRAME_MATCHED_ONLY')
    def test_no_runtime_consumption_claim(self):self.assertTrue(all(x['budgets']['VIDEO']['runtime_consumption']=='RUNTIME_CONSUMPTION_NOT_VERIFIED' for x in self.results))
    def test_environment(self):self.assertEqual([core.os.environ[k] for k in ['CUDA_VISIBLE_DEVICES','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE']],['-1','1','1'])
    def test_network_guard(self):self.assertIs(core.socket.create_connection,core.denied)
    def test_weight_guard(self):self.assertRaises(PermissionError,core.open_guard,'open',('fake.safetensors','r',0))
    def test_core_denied(self):self.assertRaises(RuntimeError,core.denied)
    def test_no_model_calls_source(self):
        bad=[]
        for p in core.OUT.rglob('*.py'):
            for n in ast.walk(ast.parse(p.read_text())):
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='generate':bad.append(str(p))
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='from_pretrained' and not (isinstance(n.func.value,ast.Name) and n.func.value.id=='AutoProcessor'):bad.append(str(p))
        self.assertFalse(bad)

if __name__=='__main__':
    with (core.OUT/'cpu_tests.log').open('x',encoding='utf-8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    record={'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors),
      'failures':[(str(case),trace) for case,trace in result.failures],
      'errors':[(str(case),trace) for case,trace in result.errors],
      'skipped':[(str(case),reason) for case,reason in result.skipped],'new_model_calls':0}
    core.save('cpu_tests.json',record);print(record)
    if not result.wasSuccessful():raise SystemExit(1)
