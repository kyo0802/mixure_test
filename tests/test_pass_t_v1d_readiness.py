"""Bounded CPU tests. Every event below is deterministic software mock data,
not a VLM prediction, visual fixture, human annotation or physical-event GT.
"""
import sys
sys.dont_write_bytecode=True
import os,json,copy,unittest,datetime,hashlib,importlib.util
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015'
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor')]
DENIED=[]
def guard(event,args):
    if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','PIL','cv2','tensorflow','huggingface_hub'}:
        DENIED.append(event+':'+str(args[0]));raise RuntimeError('CPU_TEST_MODEL_PIXEL_IMPORT_DENIED')
    if event.startswith('socket.'):
        DENIED.append(event);raise RuntimeError('CPU_TEST_NETWORK_DENIED')
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        p=Path(os.fsdecode(args[0])).resolve();low=str(p).lower().replace('\\','/')
        if p.suffix.lower() in {'.png','.jpg','.jpeg','.mp4','.avi','.mov','.safetensors','.bin','.pt','.pth','.npy','.npz'} or '/.models/' in low or low.endswith('/external_dev_gt.json') or '/val_set/' in low:
            DENIED.append(str(p));raise RuntimeError('CPU_TEST_MEDIA_WEIGHT_GT_DENIED')
        mode,flags=args[1:3]
        writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
        if writing and not p.is_relative_to(OUT):raise RuntimeError('CPU_TEST_WRITE_OUTSIDE_REPORT')
sys.addaudithook(guard)

from memory_graph.pass_t.phase2b import v1d_protocol as p
from memory_graph.pass_t.phase2b import v1d_execution as x
from memory_graph.pass_t.phase2b import v1d_outputs as o
from memory_graph.pass_t.phase2b.evaluation import (closed_interval_gap,match_known_events,evaluate_item,CLOSED_INTERVAL_MATCHER)
from memory_graph.pass_t.phase2b.common import canonical_bytes,digest,Phase2BBlocked

def mock_approval(draft):
    return {'confirmation':'APPROVE_PHASE2B_V1D_FREEZE '+digest(canonical_bytes(draft))+' NO_EXECUTION',
       'reviewer_id':'MOCK_HUMAN_NOT_ACTUAL_APPROVAL','execution_authorized':False,
       'decisions':[{'id':d['id'],'decision_sha256':p.decision_digest(d),'status':'APPROVED'} for d in draft['human_decisions']]}
def mock_auth(bundle):
    h=bundle['freeze_receipt']['protocol_sha256']
    return {'schema_version':p.VERSION+'_EXECUTION_AUTHORIZATION','confirmation':'EXECUTE_PHASE2B_V1D '+h+' 18_CALLS',
       'protocol_sha256':h,'max_calls':18,'reviewer_id':'MOCK_NOT_REAL_EXECUTION_AUTHORIZATION','nonce':'a'*32,
       'expires_at_utc':'2099-01-01T00:00:00+00:00','call_ids':list(range(1,19))}
def mock_native_envelope(draft,cid):
    call,w=p.call_context(draft,cid)
    return {'payload':{'schema_version':'PASS_T_PHASE2B_MODEL_PAYLOAD_V1','request_id':'REQ_'+'a'*20,
       'representation':'NATIVE_VIDEO_ARRAY','media':[], 'instructions':(ROOT/draft['prompt_path']).read_text(encoding='utf8'),
       'target':{'opaque_id':'TARGET_A','description':'the designated object in supplied bounded media'},
       'ontology':{'event_types':['PICKUP','PLACEMENT'],'window_outcomes':['CONFIRMED_EVENTS','NO_CONFIRMED_EVENT','INSUFFICIENT_EVIDENCE','TARGET_NOT_OBSERVABLE']},
       'output_contract':'PASS_T_PHASE2B_PREDICTION_V1'},'media':[],
       'generation':{'max_output_tokens':1024,'sampling':False,'seed':42},
       'native_video_array':{'aliases':[f['supplied_alias'] for f in w['selected']],'native_pts_s':[f['native_source_pts_s'] for f in w['selected']]}}
def mock_no_event(aliases):
    return {'schema_version':'PASS_T_PHASE2B_PREDICTION_V1','target_id':'TARGET_A','window_outcome':'NO_CONFIRMED_EVENT',
        'window_cited_frame_aliases':[aliases[0]],'events':[],
        'last_directly_supported_state':{'state':'STATE_UNKNOWN','supporting_frame_alias':None},
        'end_visibility':'UNKNOWN','subsequent_state':'UNKNOWN','rationale':'Software mock only.',
        'uncertainty':'No physical judgment from software mock.',
        'safety_assertions':{'global_identity_claimed':False,'state_persisted_across_unobserved_interval':False,'container_or_handover_auto_classified':False}}
def mock_event(alias='F0001',event_id='PRED_EVT_001'):
    return {'event_id':event_id,'event_type':'PICKUP','timing':{'status':'EXACT_SUPPLIED_FRAME','frame_alias':alias},
        'cited_frame_aliases':[alias],'before_state':{'state':'STATE_UNKNOWN','supporting_frame_alias':None},
        'after_state':{'state':'STATE_UNKNOWN','supporting_frame_alias':None},'target_association_uncertainty':'NONE',
        'timing_uncertainty':'Mock time compatibility only.','rationale':'Deterministic software test, not evidence.'}
def mock_gt(a,b,event_id='MOCK_GT_1'):
    return {'event_id':event_id,'event_type':'PICKUP','event_time':{'start_timestamp_s':a,'end_timestamp_s':b}}

class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.draft=p.draft_protocol(ROOT)
        cls.bundle=p.frozen_bundle(cls.draft,mock_approval(cls.draft),ROOT) # memory only; no freeze writer called
        cls.auth=mock_auth(cls.bundle)
    def test_draft_is_unapproved_and_all_21_pending(self):
        self.assertEqual(p.validate_draft(self.draft,ROOT)['decisions_pending'],21)
        self.assertTrue(all(d['human_approval_status']=='PROPOSED_AWAITING_HUMAN_APPROVAL' for d in self.draft['human_decisions']))
    def test_three_representations_exact_six_by_three(self):
        self.assertEqual({r['representation'] for r in self.draft['run_order']},set(p.REPRESENTATIONS))
        self.assertEqual(len(self.draft['run_order']),18)
    def test_no_execution_without_frozen_manifest_before_loader(self):
        with patch.object(x,'_runtime_factory') as factory,patch.object(x,'load_envelope') as loader:
            with self.assertRaises(Phase2BBlocked):x.execute_authorized({},self.auth,ROOT)
            factory.assert_not_called();loader.assert_not_called()
    def test_no_execution_without_separate_authorization(self):
        with patch.object(x,'_runtime_factory') as factory,patch.object(x,'load_envelope') as loader:
            with self.assertRaises(Phase2BBlocked):x.execute_authorized(self.bundle,None,ROOT)
            factory.assert_not_called();loader.assert_not_called()
    def test_no_external_permission_flags_no_resources_media_or_model(self):
        with patch.dict(os.environ,{'PASS_T_LOCAL_RUNTIME_APPROVAL':'','PASS_T_PHASE2B_REAL_RUN_PERMISSION':''}),\
             patch.object(x,'_resources') as resources,patch.object(x,'_runtime_factory') as factory:
            with self.assertRaises(Phase2BBlocked):x.execute_authorized(self.bundle,self.auth,ROOT)
            resources.assert_not_called();factory.assert_not_called()
    def test_authorization_expired(self):
        auth=copy.deepcopy(self.auth);auth['expires_at_utc']='2000-01-01T00:00:00+00:00'
        with self.assertRaises(Phase2BBlocked):p.authorize_execution(self.bundle,auth,root=ROOT)
    def test_authorization_does_not_reuse_other_protocol(self):
        auth=copy.deepcopy(self.auth);auth['protocol_sha256']='0'*64
        with self.assertRaises(Phase2BBlocked):p.authorize_execution(self.bundle,auth,root=ROOT)
    def test_authorization_call_budget_and_inventory(self):
        for key,val in [('max_calls',19),('call_ids',[1]),('nonce','bad')]:
            auth=copy.deepcopy(self.auth);auth[key]=val
            with self.subTest(key=key),self.assertRaises(Phase2BBlocked):p.authorize_execution(self.bundle,auth,root=ROOT)
    def test_call_outside_budget(self):
        with self.assertRaises(Phase2BBlocked):p.authorize_execution(self.bundle,self.auth,19,ROOT)
    def test_freeze_requires_all_21_decisions(self):
        approval=mock_approval(self.draft);approval['decisions'].pop()
        with self.assertRaises(Phase2BBlocked):p.frozen_bundle(self.draft,approval,ROOT)
    def test_freeze_rejects_implicit_approval(self):
        with self.assertRaises(Phase2BBlocked):p.frozen_bundle(self.draft,{'approved':True},ROOT)
    def test_draft_settings_tampering_and_legacy_rejected(self):
        for key,val in [('reference','STATIC_PRIMARY'),('model','other'),('max_pixels',999999),('representations',['REENCODED_AUTHORIZED_VIDEO']),('task_prompt_sha256','0'*64),('new_identity_ambiguity_clause',True)]:
            draft=copy.deepcopy(self.draft);draft['settings'][key]=val
            with self.subTest(key=key),self.assertRaises(Phase2BBlocked):p.validate_draft(draft,ROOT)
    def test_component_nf4_and_bridge_hash_tampering(self):
        for name in [p.BASE+'local_vlm/nf4.py',p.BASE+'local_vlm/video_array_bridge.py',p.BASE+'contracts/prediction_v1.json']:
            b=copy.deepcopy(self.bundle);b['protocol']['draft']['components_sha256'][name]='0'*64
            with self.subTest(name=name),self.assertRaises(Phase2BBlocked):p.verify_frozen(b,ROOT)
    def test_frozen_receipt_hash_tampering(self):
        b=copy.deepcopy(self.bundle);b['freeze_receipt']['protocol_sha256']='0'*64
        with self.assertRaises(Phase2BBlocked):p.verify_frozen(b,ROOT)
    def test_uniform8_not_target_or_gt_selected(self):
        self.assertEqual(p.uniform8(list(range(108))),[0,15,31,46,61,76,92,107])
        for w in self.draft['windows']:
            self.assertEqual(w['media_integrity'],'PENDING_AUTHORIZED_EXECUTION')
        draft=copy.deepcopy(self.draft);draft['windows'][0]['positions'][1]+=1
        with self.assertRaises(Phase2BBlocked):p.validate_draft(draft,ROOT)
    def test_native_bridge_cpu_eligibility(self):
        cid=next(r['proposed_call_index'] for r in self.draft['run_order'] if r['representation']=='NATIVE_VIDEO_ARRAY')
        dep=x.runtime_deployment(self.bundle,self.auth,cid,ROOT);_,w=p.call_context(self.draft,cid)
        envelope=mock_native_envelope(self.draft,cid)
        result=p.bridge_eligibility(envelope,dep,ROOT)
        self.assertEqual((result['source_frames'],result['temporal_units']),(8,4))
    def test_bridge_alias_pts_prompt_system_and_leak_tampering(self):
        cid=next(r['proposed_call_index'] for r in self.draft['run_order'] if r['representation']=='NATIVE_VIDEO_ARRAY')
        for mutation in ['aliases','pts','prompt','system','leak','generation']:
            dep=x.runtime_deployment(self.bundle,self.auth,cid,ROOT);env=mock_native_envelope(self.draft,cid)
            if mutation=='aliases':env['native_video_array']['aliases'][0]='F9999'
            if mutation=='pts':env['native_video_array']['native_pts_s'][0]+=1
            if mutation=='prompt':env['payload']['instructions']='different'
            if mutation=='system':dep['response_format_system']='different'
            if mutation=='leak':env['payload']['physical_gt']='forbidden'
            if mutation=='generation':env['generation']['max_output_tokens']=1
            with self.subTest(mutation=mutation),self.assertRaises(Phase2BBlocked):p.bridge_eligibility(env,dep,ROOT)
    def test_bridge_rejects_before_torch_import(self):
        from memory_graph.pass_t.phase2b.local_vlm.video_array_bridge import prepare_video_array
        with self.assertRaises(Phase2BBlocked):prepare_video_array(None,{}, {'real_pilot_mode':p.REAL_MODE,'synthetic_only':False})
        self.assertNotIn('torch',sys.modules)
    def test_mock_bridge_cannot_enter_real_preprocessor(self):
        from memory_graph.pass_t.phase2b.local_vlm.video_array_bridge import prepare_video_array
        cid=next(r['proposed_call_index'] for r in self.draft['run_order'] if r['representation']=='NATIVE_VIDEO_ARRAY')
        dep=x.runtime_deployment(self.bundle,self.auth,cid,ROOT);env=mock_native_envelope(self.draft,cid)
        with self.assertRaisesRegex(Phase2BBlocked,'MOCK_RECORDS'):
            prepare_video_array(None,env,dep)
        self.assertNotIn('torch',sys.modules)
    def test_real_mode_does_not_impersonate_synthetic(self):
        cid=next(r['proposed_call_index'] for r in self.draft['run_order'] if r['representation']=='NATIVE_VIDEO_ARRAY')
        dep=x.runtime_deployment(self.bundle,self.auth,cid,ROOT);dep['synthetic_only']=True
        with self.assertRaises(Phase2BBlocked):p.bridge_eligibility({},dep,ROOT)
    def test_real_native_does_not_use_unauthorized_representation(self):
        cid=next(r['proposed_call_index'] for r in self.draft['run_order'] if r['representation']=='MULTI_IMAGE')
        dep=x.runtime_deployment(self.bundle,self.auth,cid,ROOT)
        with self.assertRaises(Phase2BBlocked):p.bridge_eligibility({},dep,ROOT)
    def test_real_media_loader_guard_precedes_file_reads(self):
        with self.assertRaises(Phase2BBlocked):x.load_envelope({},self.auth,1,ROOT)
        self.assertNotIn('PIL',sys.modules)
    def test_legacy_bridge_synthetic_guard_preserved_as_source(self):
        text=(ROOT/p.BASE/'local_vlm/video_array_bridge.py').read_text(encoding='utf8')
        self.assertIn("real_receipt is None and expected_prompt_sha256!=V1C_SHA256",text)
        self.assertIn("deployment.get('synthetic_only') is not True",text)
    def test_dry_run_cannot_invoke_model_or_media(self):
        with patch.object(x,'_runtime_factory') as factory,patch.object(x,'load_envelope') as loader:
            dry=p.dry_run(ROOT)
            self.assertEqual(dry['calls_executed'],0);self.assertFalse(dry['protocol_frozen'])
            factory.assert_not_called();loader.assert_not_called()
    def test_cli_default_is_cpu_dry_run(self):
        import io,contextlib
        spec=importlib.util.spec_from_file_location('mock_v1d_cli',ROOT/'scripts/run_pass_t_v1d_pilot.py')
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        output=io.StringIO()
        with patch.object(sys,'argv',['run_pass_t_v1d_pilot.py']),contextlib.redirect_stdout(output):cli.main()
        result=json.loads(output.getvalue());self.assertEqual(result['mode'],'CPU_METADATA_DRY_RUN');self.assertEqual(result['calls_executed'],0)
    def test_cli_output_is_direct_unapproved_draft(self):
        import io,contextlib,tempfile
        spec=importlib.util.spec_from_file_location('mock_v1d_cli_out',ROOT/'scripts/run_pass_t_v1d_pilot.py')
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        folder=Path(tempfile.mkdtemp(prefix='MOCK_DRAFT_',dir=OUT/'mock_records'));output=folder/'draft.json'
        with patch.object(sys,'argv',['run_pass_t_v1d_pilot.py','dry-run','--output',str(output)]),contextlib.redirect_stdout(io.StringIO()):cli.main()
        value=json.loads(output.read_text(encoding='utf8'));self.assertEqual(value['status'],'DRAFT');p.validate_draft(value,ROOT)
    def test_mock_human_records_cannot_load_real_runtime(self):
        with self.assertRaises(Phase2BBlocked):p.require_production_human_records(self.bundle,self.auth)
        dep=x.runtime_deployment(self.bundle,self.auth,1,ROOT)
        with self.assertRaises(Phase2BBlocked):x._runtime_factory(dep,self.draft,ROOT)
        self.assertNotIn('torch',sys.modules)

class MatcherTests(unittest.TestCase):
    def test_closed_interval_cases(self):
        for gt,pred,wanted in [((0,2),(1,1),0),((0,2),(0,0),0),((0,2),(2,2),0),((0,2),(-1,-1),1),
            ((0,2),(3,3),1),((0,2),(1,3),0),((0,2),(2,4),0),((0,2),(3,4),1),((1,1),(1,1),0),((1,1),(2,2),1)]:
            with self.subTest(gt=gt,pred=pred):self.assertEqual(closed_interval_gap(gt,pred),wanted)
    def test_missing_nonfinite_and_reversed_intervals(self):
        for gt,pred in [(None,(0,0)),((0,1),None),((2,1),(0,0)),((0,1),(float('nan'),1)),((0,1),(2,1))]:
            with self.subTest(gt=gt,pred=pred):self.assertIsNone(closed_interval_gap(gt,pred))
    def match(self,at,tolerance,gt=None,pred=None):
        return match_known_events(gt or [mock_gt(0,0)],pred or [mock_event()], [{'opaque_alias':'F0001','source_timestamp_s':at}],tolerance,False,matcher_policy=CLOSED_INTERVAL_MATCHER)
    def test_exact_boundaries_at_all_three_tolerances(self):
        for tolerance in (0,0.2,0.5):
            with self.subTest(tolerance=tolerance):
                self.assertEqual(len(self.match(tolerance,tolerance)['matches']),1)
                self.assertEqual(len(self.match(tolerance+0.000001,tolerance)['matches']),0)
    def test_decimal_boundary_without_epsilon(self):
        gt=[mock_gt(0.1,0.1)]
        self.assertEqual(len(self.match(0.3,0.2,gt=gt)['matches']),1)
        self.assertEqual(len(self.match(0.3000000001,0.2,gt=gt)['matches']),0)
    def test_legacy_reproduction_and_new_policy_explicit(self):
        gt=[mock_gt(0,2)];pred=[mock_event()];mapping=[{'opaque_alias':'F0001','source_timestamp_s':1}]
        self.assertEqual(len(match_known_events(gt,pred,mapping,0,False)['matches']),0)
        self.assertEqual(len(match_known_events(gt,pred,mapping,0,False,matcher_policy=CLOSED_INTERVAL_MATCHER)['matches']),1)
    def test_one_to_one_duplicate_prediction_and_duplicate_gt(self):
        preds=[mock_event(),mock_event(event_id='PRED_EVT_002')]
        self.assertEqual(len(self.match(0,0,pred=preds)['matches']),1)
        self.assertEqual(len(self.match(0,0,gt=[mock_gt(0,0),mock_gt(0,0,'MOCK_GT_2')])['matches']),1)
    def test_unknown_missing_time_or_uncertain_association_no_match(self):
        for mutation in [{'timing':{'status':'TIMING_UNKNOWN'}},{'timing':{}},{'target_association_uncertainty':'POSSIBLE'},{'cited_frame_aliases':[]}]:
            pred=mock_event();pred.update(mutation)
            with self.subTest(mutation=mutation):self.assertEqual(len(self.match(0,0,pred=[pred])['matches']),0)
    def test_unknown_matcher_policy_rejected(self):
        with self.assertRaises(Phase2BBlocked):match_known_events([],[],[],0,False,matcher_policy='UNAPPROVED')
    def test_point_containment_not_physical_duration(self):
        # No event-duration fields or invented midpoint are created by the matcher.
        result=self.match(1,0,gt=[mock_gt(0,2)])
        self.assertEqual(result['matches'][0]['temporal_match_score'],0)
        self.assertNotIn('duration',json.dumps(result))

class OutputTests(unittest.TestCase):
    def test_absent_is_not_no_event(self):
        result=o.classify_output(None,['F0001'])
        self.assertEqual(result['classification'],'ABSENT_PREDICTION');self.assertIsNone(result['authoritative_prediction'])
    def test_invalid_json_not_repaired(self):
        for raw in [b'',b'```json\n{}\n```',b'{"x":1,"x":2}',b'{"x":NaN}',b'[]',b'\xff']:
            with self.subTest(raw=raw):
                r=o.classify_output(raw,['F0001']);self.assertEqual(r['classification'],'INVALID_JSON');self.assertIsNone(r['authoritative_prediction'])
    def test_valid_no_event_distinguished(self):
        result=o.classify_output(json.dumps(mock_no_event(['F0001'])).encode(),['F0001'])
        self.assertEqual(result['classification'],'VALID_NO_CONFIRMED_EVENT')
        self.assertTrue(all(v=='PASS' for v in result['stages'].values()))
    def test_schema_invalid_stages_not_assessed(self):
        value=mock_no_event(['F0001']);value['uncertainty']=''
        r=o.classify_output(json.dumps(value).encode(),['F0001'])
        self.assertEqual(r['classification'],'STRICT_INVALID');self.assertEqual(r['stages']['SCHEMA'],'FAIL')
        self.assertEqual(r['stages']['SEMANTIC'],'NOT_ASSESSED_DUE_TO_SCHEMA_FAILURE')
        self.assertIsNone(r['authoritative_prediction'])
    def test_citation_failure_separate(self):
        value=mock_no_event(['F9999']);r=o.classify_output(json.dumps(value).encode(),['F0001'])
        self.assertEqual((r['stages']['SCHEMA'],r['stages']['SEMANTIC'],r['stages']['CITATION']),('PASS','PASS','FAIL'))
    def test_semantic_failure_separate(self):
        value=mock_no_event(['F0001']);value['window_outcome']='CONFIRMED_EVENTS'
        r=o.classify_output(json.dumps(value).encode(),['F0001'])
        self.assertEqual((r['stages']['SCHEMA'],r['stages']['SEMANTIC'],r['stages']['CITATION']),('PASS','FAIL','PASS'))
    def test_invalid_cannot_enter_authoritative_matching(self):
        with patch('memory_graph.pass_t.phase2b.v1d_outputs.evaluate_item') as evaluator:
            for raw in [None,b'bad',b'{}']:
                result=o.gated_evaluation(raw,['F0001'],{}, {}, {})
                self.assertIsNone(result['sensitivity_results']);self.assertFalse(result['no_event_inferred'])
            evaluator.assert_not_called()
    def test_uncertain_window_not_negative_or_match(self):
        value=mock_no_event(['F0001']);value['window_outcome']='INSUFFICIENT_EVIDENCE'
        result=o.gated_evaluation(json.dumps(value).encode(),['F0001'],{'annotation_item_id':'SOFTWARE_MOCK'},
            {'pilot_scoring_permission':'DESCRIPTIVE_UNCERTAINTY_ONLY'}, {'private_mapping':[]})
        for row in result['sensitivity_results'].values():
            self.assertTrue(row['descriptive_only']);self.assertNotIn('case_level_false_event_alert',row)
    def test_nonexhaustive_extra_prediction_unevaluated_three_sensitivities(self):
        value=mock_no_event(['F0001']);value['window_outcome']='CONFIRMED_EVENTS';value['events']=[mock_event()]
        result=o.gated_evaluation(json.dumps(value).encode(),['F0001'],
            {'annotation_item_id':'SOFTWARE_MOCK','response':{'events':[]}},
            {'pilot_scoring_permission':'KNOWN_EVENT_MATCHING_ONLY','supported_positive_event_ids':[]},
            {'private_mapping':[{'opaque_alias':'F0001','source_timestamp_s':0}]})
        self.assertEqual(set(result['sensitivity_results']),{'0','0.2','0.5'})
        self.assertTrue(all(r['extra_predictions_interpretation']=='UNEVALUATED' for r in result['sensitivity_results'].values()))
    def test_raw_bytes_exclusive_and_unchanged(self):
        path=OUT/'mock_records'/'raw_preservation.txt';path.parent.mkdir(parents=True,exist_ok=True)
        raw=b'not repaired \n ``` {}'
        if path.exists():self.assertEqual(path.read_bytes(),raw)
        else:o.preserve_raw(path,raw)
        self.assertEqual(path.read_bytes(),raw)
        with self.assertRaises(FileExistsError):o.preserve_raw(path,b'replacement')

class MockReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.draft=p.draft_protocol(ROOT)
        cls.bundle=p.frozen_bundle(cls.draft,mock_approval(cls.draft),ROOT)
        cls.auth=mock_auth(cls.bundle)
    def test_mock_receipt_bound_to_protocol_sources_and_invalid_excluded(self):
        cid=self.draft['run_order'][0]['proposed_call_index'];call,w=p.call_context(self.draft,cid)
        aliases=[f['supplied_alias'] for f in w['selected']]
        prompt=(ROOT/self.draft['prompt_path']).read_text(encoding='utf8')
        system=(ROOT/self.draft['system_path']).read_text(encoding='utf8')
        rendered=system+'\nMODEL_INPUT_MOCK_NO_PIXELS\n'+prompt
        receipt={'model':p.MODEL,'revision':p.REVISION,'generation_controls':{'do_sample':False,'max_new_tokens':1024,'max_time':300},'seed_applied':42,
            'rendered_prompt':rendered,'rendered_prompt_sha256':digest(rendered.encode()),'captured_system_text':system,'processed_frame_aliases':aliases,
            'processor_frame_count':8,'reference_image_count':0,'configured_pixel_cap':200704,
            'native_video_modality':True,'temporal_patch_count':4,'representation_status':'FRAME_MATCHED_ONLY','tensor_records':{'mock':'NO_TENSOR_OR_VISUAL_INPUT'}}
        envelope={'payload':{'instructions':prompt},'generation':{'sampling':False,'seed':42,'max_output_tokens':1024}}
        destination=OUT/'mock_records'/('invalid_receipt_'+self.bundle['freeze_receipt']['protocol_sha256'][:12])
        if destination.exists():
            saved=json.loads((destination/'call_receipt.json').read_text(encoding='utf8'))
        else:
            saved=x.record_call_result(destination,b'{}',receipt,envelope,{'media_integrity':'MOCK_METADATA_ONLY'},self.bundle,self.auth,cid,execution_kind='MOCK_METADATA_ONLY',root=ROOT)
        self.assertEqual(saved['execution_kind'],'MOCK_METADATA_ONLY');self.assertIsNone(saved['classification']['authoritative_prediction'])
        self.assertEqual(saved['protocol_sha256'],self.bundle['freeze_receipt']['protocol_sha256'])
        self.assertEqual(saved['components_sha256'],self.draft['components_sha256'])
        self.assertEqual((destination/'raw_output.txt').read_bytes(),b'{}')
    def test_mock_18_call_worker_no_model_pixels_or_gt(self):
        import tempfile
        destination=Path(tempfile.mkdtemp(prefix='MOCK_18_METADATA_',dir=OUT/'mock_records'))
        require_mock_path=destination.resolve().is_relative_to(OUT.resolve());self.assertTrue(require_mock_path)
        state={'calls':0}
        draft=self.draft;bundle=self.bundle;auth=self.auth
        def loader(_b,_a,cid,_r):
            _,w=p.call_context(draft,cid)
            return {'payload':{'instructions':(ROOT/draft['prompt_path']).read_text(encoding='utf8')},
                    'generation':{'max_output_tokens':1024,'sampling':False,'seed':42},'mock_call_id':cid}, {'media_integrity':'MOCK_METADATA_ONLY','frame_alias_mapping':w['selected']}
        class SoftwareMockRuntime:
            def __init__(self):self.deployment={}
            def generate(self,env):
                state['calls']+=1;cid=env['mock_call_id'];_,w=p.call_context(draft,cid)
                aliases=[f['supplied_alias'] for f in w['selected']];system=(ROOT/draft['system_path']).read_text(encoding='utf8')
                rendered=system+'\n'+env['payload']['instructions']
                raw='{}' if state['calls']==1 else 'invalid software mock' if state['calls']==2 else json.dumps(mock_no_event(aliases))
                return {'raw_output':raw,'model':p.MODEL,'revision':p.REVISION,
                    'generation_controls':{'do_sample':False,'max_new_tokens':1024,'max_time':300},'seed_applied':42,
                    'rendered_prompt':rendered,'rendered_prompt_sha256':digest(rendered.encode()),'captured_system_text':system,
                    'processed_frame_aliases':aliases,'processor_frame_count':8,'reference_image_count':0,'configured_pixel_cap':200704,
                    'native_video_modality':True,'temporal_patch_count':4,'representation_status':'FRAME_MATCHED_ONLY'}
        good={'gpu_free_gib':10,'gpu_used_gib':6,'ram_available_gib':8,'owned_rss_gib':1}
        with patch.dict(os.environ,{'PASS_T_LOCAL_RUNTIME_APPROVAL':'1','PASS_T_PHASE2B_REAL_RUN_PERMISSION':'1'}),\
             patch.object(x,'_resources',return_value=good),patch.object(x,'load_envelope',side_effect=loader),\
             patch.object(x,'_runtime_factory',return_value=SoftwareMockRuntime()) as factory:
            x._worker(bundle,auth,destination,ROOT,execution_kind='MOCK_METADATA_ONLY')
        self.assertEqual(state['calls'],18);factory.assert_called_once()
        self.assertEqual(json.loads((destination/'progress.json').read_text())['stage'],'COMPLETE')
        summary=x.staged_run_summary(destination,draft['run_order'])
        self.assertEqual(summary['call_classifications'],{'STRICT_INVALID':1,'INVALID_JSON':1,'VALID_NO_CONFIRMED_EVENT':16})
        self.assertEqual(summary['stage_counts_over_recorded_outputs']['FULL_STRICT'],{'FAIL':2,'PASS':16})
        self.assertTrue(all(json.loads(f.read_text())['execution_kind']=='MOCK_METADATA_ONLY' for f in destination.glob('call_*/call_receipt.json')))
        self.assertNotIn('torch',sys.modules);self.assertNotIn('PIL',sys.modules)
    def test_authorization_lease_replay_rejected(self):
        import tempfile
        parent=Path(tempfile.mkdtemp(prefix='MOCK_LEASE_',dir=OUT/'mock_records'))
        folder=parent/'lease';x.claim_authorization_use(folder,self.auth)
        with self.assertRaises(FileExistsError):x.claim_authorization_use(folder,self.auth)
    def test_bad_runtime_receipt_preserves_raw_and_blocks_matching(self):
        import tempfile
        parent=Path(tempfile.mkdtemp(prefix='MOCK_BAD_RECEIPT_',dir=OUT/'mock_records'));folder=parent/'call'
        cid=self.draft['run_order'][0]['proposed_call_index']
        with self.assertRaisesRegex(ValueError,'RAW_PRESERVED'):
            x.record_call_result(folder,b'{}',{'model':'WRONG'}, {'payload':{},'generation':{}},{'media_integrity':'MOCK_METADATA_ONLY'},self.bundle,self.auth,cid,execution_kind='MOCK_METADATA_ONLY',root=ROOT)
        self.assertEqual((folder/'raw_output.txt').read_bytes(),b'{}')
        saved=json.loads((folder/'call_receipt.json').read_text());self.assertIsNone(saved['classification']['authoritative_prediction'])
    def test_missing_vs_incomplete_vs_not_started(self):
        import tempfile
        path=Path(tempfile.mkdtemp(prefix='MOCK_STOP_',dir=OUT/'mock_records'))
        (path/'call_01.started').write_text('software mock')
        (path/'call_02').mkdir();(path/'call_02/raw_output.txt').write_bytes(b'{}')
        rows=x.call_completion_summary(path,[{'proposed_call_index':i} for i in (1,2,3)])
        self.assertEqual([r['status'] for r in rows],['ABSENT_PREDICTION_AFTER_START','INCOMPLETE_RECEIPT_RAW_PRESERVED','NOT_EXECUTED_AFTER_STOP'])
    def test_historical_v1d_result_is_not_reclassified(self):
        directory=ROOT/'artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c'
        summary=json.loads((directory/'V1D_REGRESSION_SUMMARY.json').read_text())
        self.assertEqual(summary['strict_full_pass'],1);self.assertEqual(summary['actual_event_bearing'],6)
        calls=[json.loads(f.read_text()) for f in directory.glob('runs/*/completed.json')]
        bearing=[r for r in calls if r['validation']['event_count']]
        self.assertEqual(len(bearing),6);self.assertTrue(all(not r['validation']['STRICT_FULL_PASS'] for r in bearing))
    def test_safety_boundaries_cpu_mock(self):
        good={'gpu_free_gib':10,'gpu_used_gib':6,'ram_available_gib':8,'owned_rss_gib':1}
        self.assertIsNone(x.safety_reason(good,'BEFORE_LOAD'))
        for field,value in [('gpu_free_gib',9.99),('ram_available_gib',7.99)]:
            with self.subTest(field=field):self.assertEqual(x.safety_reason({**good,field:value},'BEFORE_LOAD'),'LOAD_RESOURCE_GATE')
        self.assertEqual(x.safety_reason({**good,'gpu_free_gib':1.99},'BEFORE_GENERATION'),'GENERATION_RESOURCE_GATE')
        for field,value in [('gpu_used_gib',14.51),('owned_rss_gib',20.01),('ram_available_gib',1.99)]:
            with self.subTest(field=field):self.assertEqual(x.safety_reason({**good,field:value},'RUNNING'),'RESOURCE_STOP')

def main():
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    summary={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
        'cpu_only':True,'model_modules_loaded':[m for m in sys.modules if m.split('.')[0] in {'torch','transformers','PIL','cv2'}],
        'guard_denials':DENIED,'mock_data_are_physical_GT':False,'actual_model_calls':0,'protocol_freeze_writer_called':False}
    (OUT/'CPU_TEST_RESULTS.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
