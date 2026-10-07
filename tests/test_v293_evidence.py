from copy import deepcopy
import pytest
from memory_graph.v293.evidence import authorize_observation, bounded_window, select_pack
from memory_graph.v293.reasoning import dispatch, validate_answer, FACT_KEYS

def rows(absent=False):
    result=[]
    for f,x in [(0,0),(2,2),(4,8),(6,9),(8,9)]:
        visible=not(absent and f>=6)
        result.append({'frame':f,'time':f/10,'target_bbox':[x,0,x+4,4] if visible else None,
            'target_authorization':{'status':'OBSERVATION_AUTHORIZED' if visible else 'UNAVAILABLE','geometry_usable':visible},
            'target_visible_state':'OBSERVED' if visible else 'NOT_OBSERVED',
            'chain_id':'trusted-chain' if visible else None,'scene_segment':0,'scene_ok':True,'view_ok':True,
            'phone_candidates':[],'sam_present':visible,'mask_area':16 if visible else None,
            'mask_reference':'mask.png' if visible else None,
            'anchors':[{'anchor_key':'v::e::a','bbox':[10,0,20,10],'authorized':True,'raw_label':'box','confidence':.8}]})
    return result

def pack(rs=None):
    return select_pack('test1',{'event_id':'e','peak_frame':4,'start_frame':0,'end_frame':8},
                       {'anchor_key':'v::e::a','raw_label':'box'},rs or rows(),10)

def answer(p):
    return {**{k:'UNCERTAIN' for k in FACT_KEYS},'subject_reference':p['target_id'],
        'anchor_reference':p['anchor_id'],'event_reference':p['event_id'],
        'evidence_frames':{'BEFORE':p['before_frames'],'DURING':p['during_frames'],'AFTER':p['after_frames']},
        'uncertainty':'uncertain','evidence_summary':'Only the highlighted pair is described.',
        'target_visual_description':'green phone','anchor_visual_description':'magenta box'}

def authorization(**changes):
    args={'frame':12,'sam':{'area':20,'diagnostics':{'possible_mask_drift':False}},
          'prior':{'frame':10,'trusted':True,'chain_id':'chain'},'fps':30,
          'chain_active':True,'conflicting':False,'scene_ok':True,'mask_available':True}
    args.update(changes)
    return authorize_observation(**args)

def test_observation_authorization_never_confirms_identity():
    a=authorization(); assert a['status']=='OBSERVATION_AUTHORIZED'
    assert a['identity_write_authorized'] is False and 'MATCHED' not in str(a)

def test_observation_authorization_supports_geometry():
    assert authorization()['geometry_usable'] is True

@pytest.mark.parametrize('change',[{'chain_active':False},{'conflicting':True},{'scene_ok':False},
    {'mask_available':False},{'sam':{'area':20,'diagnostics':{'possible_mask_drift':True}}},
    {'prior':{'frame':13,'trusted':True}},{'frame':40}])
def test_unsafe_observation_rejected(change):
    assert authorization(**change)['geometry_usable'] is False

def test_after_nonobservation_usable_not_physical_absence():
    p=pack(rows(True)); assert p['eligibility_status']=='ELIGIBLE'
    assert any(r['target_visible_state']=='TARGET_NOT_OBSERVED_WITH_ANCHOR_VISIBLE' for r in p['selected_frames'])
    assert p['physical_absence_claimed'] is False

def test_before_requires_both_members():
    rs=rows()
    for r in rs: r['anchors']=[]
    assert pack(rs)['eligibility_status']=='EVIDENCE_UNAVAILABLE'

def test_pair_never_mixes_anchors():
    rs=rows()
    for r in rs: r['anchors'].append({'anchor_key':'other','bbox':[0,0,1,1],'authorized':True})
    assert all(r['anchor_id']=='v::e::a' for r in pack(rs)['selected_frames'])

def test_adaptive_selection_prefers_actual_change():
    p=pack(); assert 4 in p['during_frames']
    assert p['before_frames'][0]<min(p['during_frames'])<p['after_frames'][0]

def test_scene_break_invalidates_absence():
    rs=rows(True)
    for r in rs[3:]: r['scene_segment']=1; r['scene_ok']=False
    p=pack(rs)
    assert all(r['frame']<6 for r in p['selected_frames'])
    assert not any(r['target_visible_state']=='TARGET_NOT_OBSERVED_WITH_ANCHOR_VISIBLE' for r in p['selected_frames'])

def test_untrusted_mask_is_not_absence():
    rs=rows(True)
    for r in rs[3:]: r['sam_present']=True
    assert not any(r['target_visible_state']=='TARGET_NOT_OBSERVED_WITH_ANCHOR_VISIBLE' for r in pack(rs)['selected_frames'])

def test_bounded_expansion_uses_global_budget():
    e={'start_frame':100,'end_frame':190}
    assert bounded_window(e,30,1000,1.5)==(55,235)

def test_ineligible_pack_does_not_call_vlm():
    p=pack(); p['eligibility_status']='EVIDENCE_UNAVAILABLE'
    def fail(*args): raise AssertionError('VLM should not be called')
    assert dispatch(p,[],fail)['status']=='VLM_NOT_CALLED'

def test_eligible_synthetic_pack_calls_vlm():
    import json
    p=pack(); calls=[]
    def call(images,prompt): calls.append(prompt); return json.dumps(answer(p))
    r=dispatch(p,[],call); assert len(calls)==1 and r['grounding_valid']

def test_valid_json_wrong_pair_rejected():
    p=pack(); a=answer(p); a['anchor_reference']='other'
    assert validate_answer(p,a)['status']=='VLM_GROUNDING_INVALID'

def test_wrong_frame_rejected():
    p=pack(); a=answer(p); a['evidence_frames']['BEFORE']=[999]
    assert not validate_answer(p,a)['grounding_valid']

def test_inconsistent_subject_visibility_rejected():
    p=pack(rows(True)); a=answer(p); a['target_visible_after']='YES'
    assert not validate_answer(p,a)['grounding_valid']

def test_schema_invalid_distinct_from_grounding():
    assert validate_answer(pack(),{})['status']=='VLM_SCHEMA_INVALID'

def test_pack_does_not_mutate_input_identity():
    rs=rows(); before=deepcopy(rs);pack(rs);assert rs==before

def test_recompute_contract_and_regression_checks():
    from memory_graph.v293.sources import verify_baseline_contract
    result=verify_baseline_contract(full_hashes=False)
    assert result['identity_threshold']==.60 and result['margin']==.10
    assert result['test7_identity_unchanged'] and result['test8_closed_loop']


def test_grounded_geometry_reaches_unchanged_physical_gate():
    import numpy as np
    from memory_graph.v22.sam_tracking import encode_mask
    from memory_graph.v293.reasoning import evaluate_gate
    rs=rows();masks={}
    for r in rs:
        box=r['target_bbox'];r['sam_phone']={'bbox':box,'area':16}
        binary=np.zeros((30,30),dtype=bool);binary[box[1]:box[3],box[0]:box[2]]=True
        masks[str(r['frame'])]=encode_mask(binary)
    p=pack(rs);a=answer(p);grounding=validate_answer(p,a)
    decisions=evaluate_gate('test1',{'event_id':'e','start_frame':0,'end_frame':8},p,
                            {**grounding,'observable_facts':a},rs,masks,(30,30))
    assert decisions and all(d['decision'] in {'PROMOTED','CANDIDATE','UNCERTAIN','REJECTED'} for d in decisions)
    assert all(d['identity_write_authorized'] is False for d in decisions)


def test_invalid_grounding_never_reaches_physical_gate():
    from memory_graph.v293.reasoning import evaluate_gate
    assert evaluate_gate('test1',{},pack(),{'grounding_valid':False},[],{},(30,30))==[]


def test_copied_prompt_description_is_not_grounding():
    p=pack();a=answer(p);a['target_visual_description']='describe the GREEN highlighted phone'
    assert validate_answer(p,a)['status']=='VLM_GROUNDING_INVALID'


def test_single_miss_after_visible_frame_not_admitted_as_absence():
    rs=rows();rs[-1]=rows(True)[-1]
    p=pack(rs)
    assert not any(r['target_visible_state']=='TARGET_NOT_OBSERVED_WITH_ANCHOR_VISIBLE' for r in p['selected_frames'])


def test_late_nonobservation_cannot_bridge_unobserved_gap():
    rs=rows(True)
    for r in rs[3:]:r['frame']+=100
    p=pack(rs)
    assert not any(r['target_visible_state']=='TARGET_NOT_OBSERVED_WITH_ANCHOR_VISIBLE' for r in p['selected_frames'])


def test_target_exiting_frame_not_used_as_after_nonobservation():
    rs=rows(True)
    for r in rs:r['image_size']=[12,30]
    p=pack(rs)
    assert not any(r['target_visible_state']=='TARGET_NOT_OBSERVED_WITH_ANCHOR_VISIBLE' for r in p['selected_frames'])


def test_response_reuse_requires_exact_prompt_and_image_bytes(tmp_path):
    from memory_graph.v293.runner import input_fingerprint
    p=tmp_path/'frame.jpg';p.write_bytes(b'first image')
    original=input_fingerprint('prompt',[p])
    assert original==input_fingerprint('prompt',[p])
    assert original!=input_fingerprint('different prompt',[p])
    p.write_bytes(b'changed image')
    assert original!=input_fingerprint('prompt',[p])


def test_valid_ids_with_description_of_another_anchor_rejected():
    p=pack();p['anchor']['raw_label']='person';a=answer(p)
    a['anchor_visual_description']='Basketball lying on a wooden surface'
    assert validate_answer(p,a)['status']=='VLM_GROUNDING_INVALID'


def test_anchor_description_hand_is_compatible_with_person():
    p=pack();p['anchor']['raw_label']='person';a=answer(p)
    a['anchor_visual_description']='A hand and arm holding the phone'
    assert validate_answer(p,a)['grounding_valid']
