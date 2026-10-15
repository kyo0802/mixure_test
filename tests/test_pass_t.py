"""Focused offline Phase1 contract tests; never run a model or the Builder."""
import sys
from pathlib import Path
from copy import deepcopy
import json
import hashlib
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'artifacts/pass_i/runtime/vendor'))
from memory_graph.pass_t.contracts import (validate_prediction, baseline, schema_errors,
    PREDICTION_SCHEMA, GT_SCHEMA, directly_observable, TRANSITIONS)
from memory_graph.pass_t.fixtures import context, cases, event, prediction, gt_from_prediction
from memory_graph.pass_t.sampling import (sample, make_manifest, validate_manifest, manifest_identity,
    bundle_from_manifest,validate_bundle,shared_frames,leakage_errors,verify_encoded_timing)
from memory_graph.pass_t.evaluation import evaluate,rate,match_events


@pytest.mark.parametrize('case',cases(),ids=lambda x:x['case_id'])
def test_synthetic_contracts(case):
    assert not validate_prediction(case['prediction'],case['bundle'],0,4)
    assert not validate_prediction(case['gt'],case['bundle'],0,4,human=True)


def test_schemas_separate_and_human_fields_rejected():
    m,b=context();p=prediction();g=gt_from_prediction(p,m['sampling_manifest_id'])
    assert schema_errors(g,PREDICTION_SCHEMA)
    assert schema_errors(p,GT_SCHEMA)
    for field in ['provenance','sampled_observability','adjudication','observable_in_full_window','unobservable_reason','global_alias','graph_write']:
        q=deepcopy(p);q[field]={};assert validate_prediction(q,b,0,4)


@pytest.mark.parametrize('assessment,actions,unresolved',[
 ('CONFIRMED_NONE',[event('PICK_UP')],[]),('CONFIRMED_NONE',[],['PLACE']),
 ('INDETERMINATE',[],[]),('EVENTS_OBSERVED',[],[]),('EVENTS_OBSERVED',[event('PICK_UP')],['PLACE']),
 ('PARTIALLY_OBSERVED',[event('PICK_UP')],[]),('PARTIALLY_OBSERVED',[],['PLACE'])])
def test_assessment_consistency(assessment,actions,unresolved):
    _,b=context();p=prediction(actions);p['event_assessment']=assessment;p['unresolved_transitions']=unresolved
    assert validate_prediction(p,b,0,4)


@pytest.mark.parametrize('field,value',[
 ('holder_local_id','P1'),('holder_status','NOT_HELD'),('confirmed_at_s',1.),('evidence_frame_ids',['F003'])])
def test_never_confirmed(field,value):
    _,b=context();p=prediction();p['last_confirmed_state'][field]=value
    assert validate_prediction(p,b,0,4)


def test_holder_and_visibility_are_separate():
    x=next(x for x in cases() if x['case_id']=='held_before_occlusion')
    p=x['prediction'];b=x['bundle'];assert not validate_prediction(p,b,0,4)
    for field,value in [('holder_local_id',None),('holder_status','NOT_HELD'),('holder_status','UNKNOWN')]:
        q=deepcopy(p);q['last_confirmed_state'][field]=value;assert validate_prediction(q,b,0,4)
    assert p['last_confirmed_state']['confirmation_status']=='CONFIRMED'
    assert p['current_visibility_at_window_end']=='OCCLUDED'


def test_unknown_holder_is_not_not_held():
    x=next(x for x in cases() if x['case_id']=='unknown_holder')
    assert not validate_prediction(x['prediction'],x['bundle'],0,4)
    assert x['prediction']['last_confirmed_state']['holder_status']=='UNKNOWN'


@pytest.mark.parametrize('mutator',[
 lambda p:p['events'][0].update(evidence_frame_ids=['F099']),
 lambda p:p['events'][0].update(actor_local_id='P99'),
 lambda p:p['events'][0].update(target_local_id='phone_01'),
 lambda p:p['events'][0].update(support_class='UNSUPPORTED'),
 lambda p:p['events'][0].update(onset_interval_s=[-1,0]),
 lambda p:p['events'][0].update(offset_interval_s=[5,6]),
 lambda p:p['events'][0].update(onset_interval_s=[2,1]),
 lambda p:p['events'][0].update(receiver_local_id='P2'),
 lambda p:p['events'][0].update(action='TRACK_LOST'),
 lambda p:p['events'][0].update(action='UNKNOWN')])
def test_invalid_event(mutator):
    _,b=context();p=prediction([event('PICK_UP')]);mutator(p);assert validate_prediction(p,b,0,4)


def test_handoff_requires_two_distinct_observed_people():
    _,b=context();p=prediction([event('HANDOFF',actor='P1',receiver='P2')])
    assert not validate_prediction(p,b,0,4)
    for receiver in [None,'P1','P99']:
        q=deepcopy(p);q['events'][0]['receiver_local_id']=receiver;assert validate_prediction(q,b,0,4)
    b['person_ids']=[];assert validate_prediction(p,b,0,4)


def test_no_person_tracks_actor_unknown_and_actor_metric_na():
    m,b=context();b['person_ids']=[];p=prediction([event('PICK_UP',actor=None)])
    assert not validate_prediction(p,b,0,4)
    g=gt_from_prediction(p,m['sampling_manifest_id']);result=evaluate([{'bundle':b,'gt':g,'prediction':p}])
    assert result['actor_accuracy']['rate'] is None


def test_place_anchor_and_proximity_rules():
    _,b=context();p=prediction([event('PLACE')]);assert not validate_prediction(p,b,0,4)
    for pred in ['NEAR','HELD_BY','UNKNOWN']:
        q=deepcopy(p);q['events'][0]['relation']['predicate']=pred;assert validate_prediction(q,b,0,4)
    q=deepcopy(p);q['events'][0]['relation']['anchor_local_id']='A99';assert validate_prediction(q,b,0,4)
    q=deepcopy(p);q['events'][0]['relation']['anchor_local_id']=None;q['events'][0]['relation']['anchor_label']='observed table'
    assert not validate_prediction(q,b,0,4)


def test_temporal_gaps_and_uncertainty():
    _,b=context();p=prediction([event('PICK_UP',.5,1),event('PLACE',3,3.5)])
    assert not validate_prediction(p,b,0,4)
    q=deepcopy(p);q['events'].reverse();assert validate_prediction(q,b,0,4)
    q=prediction([event('PICK_UP',.5,2),event('PLACE',1,2.5)]);assert validate_prediction(q,b,0,4)
    q=prediction([event('PICK_UP')]);q['events'][0].update(onset_interval_s=None,offset_interval_s=None,boundary_status='UNLOCALIZABLE',boundary_reason='boundary not visible')
    assert not validate_prediction(q,b,0,4)
    q['events'][0]['boundary_status']='BRACKETED';assert validate_prediction(q,b,0,4)
    q['events'][0].update(offset_interval_s=[1,1.2],boundary_status='ONE_SIDED')
    assert not validate_prediction(q,b,0,4)


def test_sampling_missed_and_per_manifest_observability():
    x=next(x for x in cases() if x['case_id']=='sampling_missed');g=x['gt'];b=x['bundle'];sm=b['sampling_manifest_id']
    assert not directly_observable(g['events'][0],sm)
    for mutation in ['full_false','direct','missing']:
        q=deepcopy(g)
        if mutation=='full_false':q['events'][0]['observable_in_full_window']=False
        elif mutation=='direct':q['events'][0]['sampled_observability'][sm]['support_class']='DIRECT'
        else:q['events'][0]['sampled_observability']={'SM_'+'f'*12:{'support_class':'UNSUPPORTED','unobservable_reason':'SAMPLING_MISSED'}}
        assert validate_prediction(q,b,0,4,human=True)


def test_confirmed_none_requires_gt_coverage():
    m,b=context();g=gt_from_prediction(prediction(),m['sampling_manifest_id'],False)
    assert validate_prediction(g,b,0,4,human=True)


def source(times):
    return [{'source_frame_index':i,'timestamp_s':t,'sha256':'0'*64,'timestamp_provenance':'DERIVED_FPS'} for i,t in enumerate(times)]


def test_exact_grid_tie_collision_and_half_open():
    a,info=sample(source([i/30 for i in range(121)]),0,4,3)
    assert info['grid_count']==12;assert [x['source_frame_index'] for x in a]==list(range(0,120,10))
    assert sample(source([.25,.75]),.5,1,1)[0][0]['timestamp_s']==.75 # earlier .25 outside window
    assert sample(source([.25,.75]),0,1,2)[0][0]['timestamp_s']==.25
    picked,info=sample(source([0,.5]),0,1,3);assert len(picked)==2;assert info['collision_grid_indices']==[2]
    assert all(x['timestamp_s']<1 for x in picked)


def test_earlier_tie_and_sixteen_cap():
    picked,_=sample(source([0,.25,.75]),0,1,2);assert [x['timestamp_s'] for x in picked]==[0,.25]
    picked,info=sample(source([i/30 for i in range(181)]),0,6,3)
    assert len(picked)==16;assert info['selected_grid_indices']==[(2*j*17+15)//30 for j in range(16)]
    assert sample(source([0,.1]),0,.2)[1]['grid_count']==1


@pytest.mark.parametrize('rows,start,end,fps',[
 ([],0,1,3),(source([2,3]),0,1,3),(source([0,0]),0,1,3),(source([.3,.2]),0,1,3),
 (source([0]),1,0,3),(source([0]),0,1,0)])
def test_sampling_invalid_sources(rows,start,end,fps):
    with pytest.raises(ValueError):sample(rows,start,end,fps)


def test_manifest_ids_and_abc_invariants():
    m,b=context();assert not validate_manifest(m);assert m['sampling_manifest_id']==manifest_identity(m)
    bundles=[bundle_from_manifest(m,x,'0'*64) for x in ['A','B','C']]
    assert all(not validate_bundle(x) for x in bundles);assert shared_frames(bundles)
    bundles[2]['frames'][0]['timestamp_s']+=.1;assert not shared_frames(bundles)
    n=deepcopy(m);n['target_fps']=2;assert manifest_identity(n)!=m['sampling_manifest_id']
    with pytest.raises(ValueError):bundle_from_manifest(m,'image_fallback','0'*64)


@pytest.mark.parametrize('mutation',[
 lambda m:m['frames'][0].update(frame_id='F001'),
 lambda m:m['frames'][1].update(source_frame_index=0),
 lambda m:m['frames'][0].update(source_timestamp_s=4),
 lambda m:m['frames'][0].update(window_relative_timestamp_s=.1),
 lambda m:m.update(sampling_manifest_id='SM_'+'f'*12),
 lambda m:m['sampling'].update(grid_count=13)])
def test_manifest_corruption(mutation):
    m,_=context();mutation(m);assert validate_manifest(m)


def test_asset_checksums(tmp_path):
    m,_=context();(tmp_path/'frames').mkdir()
    for f in m['frames']:
        p=tmp_path/f['image_path'];p.write_bytes(b'synthetic');f['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    assert not validate_manifest(m,tmp_path)
    (tmp_path/m['frames'][0]['image_path']).write_bytes(b'corrupt');assert validate_manifest(m,tmp_path)


@pytest.mark.parametrize('token',['PICK_UP','pickup','place','release','handoff','gt','truth','trigger','reid','score','identityguard','alias','label','phone_01','ce:test4:0005'])
def test_leakage_keys_values_and_metadata(token):
    _,b=context();assert leakage_errors({**b,'private':token})
    assert leakage_errors({**b,token:'x'})
    assert leakage_errors(b,{'description':token})


def test_neutral_metadata_and_paths():
    _,b=context();assert not leakage_errors(b)
    q=deepcopy(b);q['frames'][0]['image_path']='frames/place/F000.png';assert validate_bundle(q)
    assert leakage_errors(b,{'EXIF':'innocent text'})


def test_native_temporal_verification_contract():
    assert verify_encoded_timing([0,.3,.7],[0,.3,.7])['status']=='READY'
    assert verify_encoded_timing([0,.3,.7],[0,.33,.66])['status']=='A_NON_EQUIVALENT'
    assert verify_encoded_timing([0,.3],[0])['status']=='BLOCKED'
    assert verify_encoded_timing([0,.3],[.3,0])['status']=='BLOCKED'
    assert verify_encoded_timing([0,.3],[0,.3],(['a','b'],['b','a']))['status']=='BLOCKED'


def test_evaluator_deterministic_baselines():
    rows=cases();abstain=[{**x,'prediction':baseline(x['bundle'],4)} for x in rows]
    none=[{**x,'prediction':baseline(x['bundle'],4,False)} for x in rows]
    a=evaluate(abstain);n=evaluate(none)
    assert a['false_pickup']['numerator']==a['false_placement']['numerator']==0
    assert a['false_pickup']['denominator']==a['false_placement']['denominator']==6
    assert a['answer_coverage']['rate']==0;assert a['event_macro_f1']==0
    assert n['answer_coverage']['rate']==1
    assert n['event_per_class']['PICK_UP']['fn']==1
    assert n['event_per_class']['PLACE']['fn']==2
    assert a['sampling_missed_excluded_from_direct_recall']==1
    assert a['graph_write_attempts']==n['graph_write_attempts']==0
    assert a['sessions']==1
    assert rate(0,0)['wilson_95_ci'] is None
    assert .048<rate(0,75)['wilson_95_ci'][1]<.05


def test_eligible_negatives_and_unsupported_true_event():
    x=next(x for x in cases() if x['case_id']=='sampling_missed')
    x['prediction']=prediction([event('PICK_UP')]);result=evaluate([x])
    assert result['false_pickup']['denominator']==0
    assert result['unsupported_reason_counts']['SAMPLING_MISSED']==1
    assert not result['physical_action_errors']
    assert result['event_per_class']['PICK_UP']['fp']==1


def test_order_matching_and_actor_precision():
    x=cases()[0];r=evaluate([x]);assert r['event_macro_f1']==1
    assert r['temporal_order']['rate']==1;assert r['actor_accuracy']['rate']==1
    assert match_events(x['gt']['events'],x['prediction']['events'])==[(0,0),(1,1)]


def test_safety_factual_vs_unsupported_location():
    x=next(x for x in cases() if x['case_id']=='place_release');sm=x['bundle']['sampling_manifest_id']
    x['gt']['last_confirmed_state']['sampled_observability'][sm]={'support_class':'UNSUPPORTED','unobservable_reason':'OCCLUDED'}
    r=evaluate([x]);assert r['incorrect_definite_final_location']['numerator']==0
    assert r['unsupported_definite_final_location']['numerator']==1
    x['prediction']['last_confirmed_state']['relation']['anchor_local_id']=None
    x['prediction']['last_confirmed_state']['relation']['anchor_label']='table'
    r=evaluate([x]);assert r['pending_anchor_adjudication']==1
    assert r['incorrect_definite_final_location']['denominator']==0


def test_preserved_prompt_and_stage0_gate():
    prompt=ROOT/'artifacts/pass_i/prompts/pass_i_prelabel_prompt.txt'
    assert hashlib.sha256(prompt.read_bytes()).hexdigest()=='b6057e19de893514fabba7842dbd3a91957fc17e7255c2e9bfb2a3b16dd7b53d'
    from memory_graph.pass_t.phase1 import inspect_sources
    result=inspect_sources();assert result['event_packs_found']==9
    assert result['blocked_with_reason']==7;assert result['stage0_gate_pass'] is False
    assert result['source_pixels_decoded']==result['model_inference_calls']==0


def test_delivered_prompt_hash_and_schemas():
    from jsonschema import Draft202012Validator
    folder=ROOT/'artifacts/pass_t/contracts'
    record=json.loads((folder/'prompt_manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((folder/'pass_t_event_annotator_v1.txt').read_bytes()).hexdigest()==record['core_sha256']
    for mode,h in record['segment_sha256'].items():
        assert hashlib.sha256((folder/f'pass_t_event_annotator_v1_{mode}.txt').read_bytes()).hexdigest()==h
    for schema in folder.glob('PASS_T_*SCHEMA_V1.json'):
        Draft202012Validator.check_schema(json.loads(schema.read_text(encoding='utf-8')))
