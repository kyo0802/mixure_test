import pytest
from memory_graph.v297_physical_identity.person import PersonEpochBuilder,PersonPolicy,CameraCompensator
from memory_graph.v297_physical_identity.physical import PhysicalIdentityState,PhysicalPolicy,motion_coupling

def row(t,x=100,y=100,eid='ce:a',oid=None):
    return {'time':t,'frame':round(t*30),'bbox':[x,y,x+30,y+60],'candidate_epoch_id':eid,'candidate_id':eid,
        'observation_id':oid or f'{eid}@{t}','confidence':.9,'label':'cell phone','v3':[1.,0.],
        'candidate_epoch_start':0,'epoch_unresolved':False,'scene_break':False,'epoch_split_reason':None,
        'raw_source_verified':True,'annotation_overlays':False,'crop_sha256':f'h{eid}{t}',
        'raw_image_sha256':f'f{t}','raw_image_path':'original#frame','raw_crop_path':'clean',
        'source':'yolo_track','video_id':'synthetic','evidence_producer':'synthetic-test'}
def person(t,x=80,y=70,eid='pe:1'):
    return {'person_epoch_id':eid,'time':t,'frame':round(t*30),'bbox':[x,y,x+100,y+150],'local_track_id':'local:p'}
def cam(dx=0,valid=True,segment=1):
    return {'reliable':valid,'translation':[dx,0.],'cumulative_translation':[dx,0.],'camera_segment':segment,'normalized_units':'image_diagonal'}
def begin(s,t,rows=(),people=(),camera=None):
    s.begin_frame({'time':t,'frame':round(t*30),'image_size':[1000,1000],'scene_ok':True},list(people),camera or cam(),list(rows))
def auth(s,r):s.authorized(r,{'authorization_id':f'auth:{r["time"]}','alias_id':'alias:1','epoch_id':1})

def test_person_raw_id_after_gap_is_new_epoch():
    b=PersonEpochBuilder('s',PersonPolicy())
    a=b.process(0,[{'anchor_key':'local:1','bbox':[0,0,100,200]}],[1000,1000])[0]
    c=b.process(3,[{'anchor_key':'local:1','bbox':[0,0,100,200]}],[1000,1000])[0]
    assert a['person_epoch_id']!=c['person_epoch_id']

def test_one_frame_proximity_does_not_support_identity():
    s=PhysicalIdentityState('phone_01',PhysicalPolicy());r=row(0);begin(s,0,[r],[person(0)]);auth(s,r)
    r2=row(.2,eid='ce:b');begin(s,.2,[r2],[person(.2)])
    assert s.assess(r2)['interaction']!='INTERACTION_CONTINUITY_SUPPORT'

def test_multiframe_compensated_joint_motion_couples():
    h=[{'time':i*.2,'target_comp':[i*.02,0],'person_comp':[i*.02+.1,0],'relative':[.1,0],'camera_reliable':True} for i in range(4)]
    assert motion_coupling(h,PhysicalPolicy())=='MOTION_COUPLED'

def test_camera_pan_alone_is_not_coupled():
    h=[{'time':i*.2,'target_comp':[0,0],'person_comp':[.1,0],'relative':[.1,0],'camera_reliable':True} for i in range(4)]
    assert motion_coupling(h,PhysicalPolicy())!='MOTION_COUPLED'

def test_unreliable_compensation_is_unknown():
    h=[{'time':i*.2,'target_comp':[i*.02,0],'person_comp':[i*.02,0],'relative':[0,0],'camera_reliable':False} for i in range(4)]
    assert motion_coupling(h,PhysicalPolicy())=='MOTION_UNKNOWN'

def test_persistent_overlap_then_missing_target_creates_hypothesis():
    s=PhysicalIdentityState('phone_01',PhysicalPolicy())
    for i in range(3):
        t=i*.2;r=row(t);begin(s,t,[r],[person(t)]);auth(s,r)
    begin(s,.6,[],[person(.6)])
    assert s.snapshot()['occlusion_hypothesis']['state']=='TARGET_OCCLUDED_WITH_PERSON_HYPOTHESIS'

def test_same_person_reappearance_after_occlusion_supports():
    s=PhysicalIdentityState('phone_01',PhysicalPolicy())
    for i in range(3):
        t=i*.2;r=row(t);begin(s,t,[r],[person(t)]);auth(s,r)
    begin(s,.6,[],[person(.6)])
    for t in [.8,1.,1.2]:
        r=row(t,eid='ce:b');begin(s,t,[r],[person(t)])
    assert s.assess(r)['interaction']=='INTERACTION_CONTINUITY_SUPPORT'

def test_far_short_gap_candidate_is_inconsistent():
    s=PhysicalIdentityState('phone_01',PhysicalPolicy());r=row(0);begin(s,0,[r]);auth(s,r)
    far=row(.2,x=800);begin(s,.2,[far]);assert s.assess(far)['reachability']=='PHYSICALLY_INCONSISTENT'

def test_preexisting_coexistent_candidate_stays_distinct():
    s=PhysicalIdentityState('phone_01',PhysicalPolicy())
    for i in range(3):
        t=i*.2;a=row(t);b=row(t,x=500,eid='ce:b');begin(s,t,[a,b]);auth(s,a)
    assert s.known_distinct
    later=row(5,x=500,eid='ce:b');begin(s,5,[later]);a=s.assess(later)
    assert a['known_distinct'] and a['preexistence_contradiction']

def test_raw_id_is_not_distinct_lineage_after_arbitrary_gap():
    s=PhysicalIdentityState('phone_01',PhysicalPolicy())
    for i in range(3):
        t=i*.2;a=row(t);b=row(t,x=500,eid='ce:b');begin(s,t,[a,b]);auth(s,a)
    c=row(5,eid='ce:c');c['v3']=[0.,1.];begin(s,5,[c]);assert not s.assess(c)['known_distinct']

def test_person_epoch_break_drops_occlusion_support():
    s=PhysicalIdentityState('phone_01',PhysicalPolicy())
    for i in range(3):
        t=i*.2;r=row(t);begin(s,t,[r],[person(t)]);auth(s,r)
    begin(s,.6,[],[person(.6)])
    r=row(.8,eid='ce:b');begin(s,.8,[r],[person(.8,eid='pe:2')]);assert s.assess(r)['interaction']!='INTERACTION_CONTINUITY_SUPPORT'

def test_partial_duplicate_is_not_known_distinct_entity():
    s=PhysicalIdentityState('phone_01',PhysicalPolicy())
    for i in range(3):
        t=i*.2;a=row(t);b=row(t,x=110,eid='ce:b');b['bbox']=[110,100,115,105];begin(s,t,[a,b]);auth(s,a)
    assert not s.known_distinct

def test_long_gap_without_context_is_unknown():
    s=PhysicalIdentityState('phone_01',PhysicalPolicy());r=row(0);begin(s,0,[r]);auth(s,r)
    c=row(10,eid='ce:new');begin(s,10,[c]);a=s.assess(c)
    assert a['reachability']=='PHYSICAL_UNKNOWN' and a['interaction']=='INTERACTION_CONTINUITY_UNKNOWN'

def test_state_rejects_unscoped_trusted_update():
    s=PhysicalIdentityState('phone_01',PhysicalPolicy());r=row(0);begin(s,0,[r])
    with pytest.raises(PermissionError):s.authorized(r,{})

from memory_graph.identity.contracts import Observation,Policy
from memory_graph.identity.guard import IdentityGuard
from memory_graph.v296_reid.guard import V296IdentityGuard
from memory_graph.v296_reid.evidence import ConfirmationPolicy
from memory_graph.v296_reid.integrity import pair_integrity
from memory_graph.v297_physical_identity.guard import V297IdentityGuard
from memory_graph.v297_physical_identity.policy import decide

def visual(stage='CONFIRMED_MATCH',geometry='CORE_STRONG_MATCH'):
    return {'stage':stage,'route':'G' if geometry=='CORE_STRONG_MATCH' else 'A',
        'integrity':{'admissible':True},'LightGlue':{'state':geometry},'DINOv3':{'median':1.}}

def physical_evidence(**changes):
    return {'known_distinct':False,'preexistence_contradiction':False,'reachability':'PHYSICALLY_CONSISTENT',
        'interaction':'INTERACTION_CONTINUITY_UNKNOWN','physical_continuity':{'gap':.6},
        'unique_physical_support':True,'candidate_continuity_valid':True,'competing_plausible_epochs':[],**changes}

def guarded(geometry='CORE_STRONG_MATCH',near=False):
    state=PhysicalIdentityState('phone_01');metadata={}
    config=ConfirmationPolicy(g_support=.8,g_lower=.75,a_support=.85,a_lower=.82,v2_support=.8,a_frames=5,a_duration=.8,calibrated=True)
    def verifier(current,core,negative,*args):
        pairs=[{'integrity':pair_integrity(current,b,b,current['observation_id']),
            'status':'STRONG_MATCH' if geometry=='CORE_STRONG_MATCH' else 'UNKNOWN'} for b in core[:2]]
        return {'state':geometry,'negative_positive':False,'integrity_valid':geometry!='INVALID_EVIDENCE','core_pairs':pairs}
    guard=V297IdentityGuard(Policy(),config,metadata,lambda r:r['v2'],verifier,lambda *args:{'state':'UNKNOWN'},state)
    for t in [0.,.2,.4,.6,.8]:step(guard,metadata,t,[('initial','initial',100,[1.,0.])],near=near)
    return guard,metadata

def step(g,m,t,spec=(),near=False,person_epoch='pe:1',source='yolo_track',sam=0.):
    rows=[]
    for local,epoch,x,embedding in spec:
        r=row(t,x=x,eid=epoch,oid=f'{local}@{t}');r.update(v3=embedding,v2=embedding,local_track_id=local,
            local_track_ids=[local],candidate_epoch_start=0. if epoch=='initial' else 1.,source=source,sam_overlap=sam,drift=False,
            provenance='synthetic-current-original',candidate_id=local)
        rows.append(r)
    begin(g.physical,t,rows,[person(t,eid=person_epoch)] if near else [])
    obs=[]
    for r in rows:
        m[r['observation_id']]=r;obs.append(Observation(r['observation_id'],r['candidate_epoch_id'],r['frame'],t,
            tuple(r['bbox']),'cell phone',.9,r['provenance'],vector=tuple(r['v3']),source=source,sam_overlap=sam))
    g.process(t,obs);g.physical.prune_aliases({a['alias_id'] for a in g._aliases if a['status']=='CONFIRMED'})
    current=[a for a in g.final_ledger() if a['observation']['time']==t]
    if current:g.physical.authorized(m[current[-1]['observation']['observation_id']],current[-1])
    return obs

def test_single_phone_recovery_without_person_actual_guard():
    g,m=guarded()
    for t in [1.,1.2,1.4]:step(g,m,t,[('new','new',100,[1.,0.])])
    s=g.snapshot();assert len(s['aliases'])==2
    assert s['confirmation_audit'][0]['confirmation_context']=='CONTINUITY_RECOVERY'
    assert all(r['authorization_id'] for r in s['final_ledger'])

def test_actual_guard_interaction_recovery_without_geometry():
    g,m=guarded('UNKNOWN',near=True)
    for t in [1.,1.2,1.4,1.6,1.8,2.,2.2,2.4,2.6,2.8,3.,3.2,3.4,3.6]:step(g,m,t,near=True)
    for t in [3.8,4.,4.2,4.4,4.6]:step(g,m,t,[('new','new',100,[1.,0.])],near=True)
    s=g.snapshot();assert len(s['aliases'])==2
    assert s['confirmation_audit'][0]['confirmation_context']=='INTERACTION_CONDITIONED_RECOVERY'
    assert len(s['banks']['core'])==3
    assert len(s['backfill_events'][0]['backfilled_observation_ids'])==4

def test_actual_guard_same_appearance_long_gap_without_context_unresolved():
    g,m=guarded()
    for t in [4.,4.2,4.4,4.6,4.8]:step(g,m,t,[('new','new',100,[1.,0.])])
    assert len(g.snapshot()['aliases'])==1
    assert g.physical_decisions[-1]['decision']=='AMBIGUOUS'

def test_actual_guard_strong_visual_far_short_gap_rejected():
    g,m=guarded()
    for t in [1.,1.2,1.4]:step(g,m,t,[('new','new',800,[1.,0.])])
    assert len(g.snapshot()['aliases'])==1
    assert g.physical_decisions[-1]['decision']=='REJECTED'

def test_actual_guard_person_break_cannot_recover():
    g,m=guarded('UNKNOWN',near=True);step(g,m,1.,near=True)
    for t in [3.8,4.,4.2,4.4,4.6]:step(g,m,t,[('new','new',100,[1.,0.])],near=True,person_epoch='pe:2')
    assert len(g.snapshot()['aliases'])==1

def test_strong_interaction_poor_appearance_not_confirmed():
    p=physical_evidence(interaction='INTERACTION_CONTINUITY_SUPPORT',reachability='PHYSICAL_UNKNOWN',physical_continuity={'gap':3.})
    assert decide(visual(stage='REJECTED'),p,PhysicalPolicy())['stage']=='REJECTED'

def test_identical_known_distinct_visual_blocks_policy():
    for key in ['known_distinct','preexistence_contradiction']:
        assert decide(visual(),physical_evidence(**{key:True}),PhysicalPolicy())['stage']=='REJECTED'

def test_competing_candidates_without_unique_physical_support_ambiguous():
    p=physical_evidence(unique_physical_support=False,competing_plausible_epochs=['other'])
    assert decide(visual(),p,PhysicalPolicy())['stage']=='AMBIGUOUS'

def test_invalid_geometry_cannot_support_interaction():
    p=physical_evidence(reachability='PHYSICAL_UNKNOWN',interaction='INTERACTION_CONTINUITY_SUPPORT',physical_continuity={'gap':3.})
    assert decide(visual(geometry='INVALID_EVIDENCE'),p,PhysicalPolicy())['stage']!='CONFIRMED_MATCH'

def test_epoch_break_clears_short_physical_support():
    s=PhysicalIdentityState('phone_01');r=row(0);begin(s,0,[r]);auth(s,r)
    c=row(.2,eid='new');c['epoch_split_reason']='SUSTAINED_LOCAL_APPEARANCE_CHANGE';begin(s,.2,[c])
    assert s.assess(c)['reachability']=='PHYSICAL_UNKNOWN'

def test_known_distinct_multiview_link_across_new_epoch_veto_only():
    s=PhysicalIdentityState('phone_01')
    for t in [0.,.2,.4]:
        a=row(t);b=row(t,x=500,eid='other');begin(s,t,[a,b]);auth(s,a)
    c=row(5,x=500,eid='reappeared');c['candidate_epoch_start']=5.;begin(s,5,[c]);p=s.assess(c)
    assert p['known_distinct'] and not p['preexistence_contradiction']
    assert decide(visual(),p,PhysicalPolicy())['stage']=='REJECTED'

def test_backfill_filters_distinct_and_physical_contradiction(monkeypatch):
    g,m=guarded();step(g,m,1.,[('new','new',100,[1.,0.])]);step(g,m,1.2,[('new','new',100,[1.,0.])])
    ids=['new@1.0','new@1.2'];m[ids[0]]['physical_identity_evidence']['known_distinct']=True
    observed={}
    def capture(self,current,result):observed.update(result);return {'backfilled_observation_ids':[]}
    monkeypatch.setattr(V296IdentityGuard,'_backfill',capture)
    g._backfill(g._observations[ids[-1]],{'observation_ids':ids,'DINOv3':{'per_frame':[1.,1.]},'DINOv2_matrix':[[1.],[1.]]})
    assert observed['observation_ids']==[ids[-1]]

def test_actual_guard_backfill_never_crosses_epoch():
    g,m=guarded();step(g,m,1.,[('old','other',100,[1.,0.])])
    for t in [1.2,1.4,1.6]:step(g,m,t,[('new','new',100,[1.,0.])])
    assert len(g.snapshot()['aliases'])==2
    assert not any(r['candidate_id']=='other' for r in g.final_ledger())

@pytest.mark.parametrize('source',['sam','yolo_raw','yolo_track'])
def test_actual_guard_detector_or_sam_long_gap_no_authority(source):
    g,m=guarded()
    for t in [4.,4.2,4.4,4.6,4.8]:step(g,m,t,[('initial','new',100,[1.,0.])],source=source,sam=1.)
    assert len(g.snapshot()['aliases'])==1

def test_only_guard_authority_methods_inherited_and_forgery_blocked():
    for name in ['_issue','_check','write','_revoke','final_ledger','restart_target_sam']:
        assert getattr(V297IdentityGuard,name) is getattr(IdentityGuard,name)
    g,m=guarded();obs=Observation('bad','bad',30,1.,(0,0,1,1),'cell phone',.9,'raw')
    with pytest.raises(PermissionError):g.write('bind_alias',{'physical':'SUPPORT'},obs)
    assert not hasattr(g.physical,'write') and not hasattr(g.physical,'_issue')

def test_revocation_prunes_physical_lineage():
    s=PhysicalIdentityState('phone_01')
    for t in [0.,.2,.4]:
        a=row(t);b=row(t,x=500,eid='other');begin(s,t,[a,b]);auth(s,a)
    s.prune_aliases(set());assert not s.last and not s.known_distinct and not s.occlusion

def test_camera_chain_restart_does_not_create_joint_motion():
    h=[{'time':i*.2,'target_comp':[i*.02,0],'person_comp':[i*.02,0],'relative':[0,0],
        'camera_reliable':True,'camera_segment':i+1} for i in range(3)]
    assert motion_coupling(h,PhysicalPolicy())=='MOTION_UNKNOWN'

def test_actual_guard_distinct_same_visual_candidate_cannot_merge():
    g,m=guarded()
    for t in [1.,1.2,1.4]:step(g,m,t,[('initial','initial',100,[1.,0.]),('other','other',500,[1.,0.])])
    assert g.physical.known_distinct
    for t in [4.,4.2,4.4]:step(g,m,t,[('other','other',100,[1.,0.])])
    assert len(g.snapshot()['aliases'])==1
    assert g.physical_decisions[-1]['decision']=='REJECTED'
    assert g.physical_decisions[-1]['physical_identity']['preexistence_contradiction']

def test_interaction_support_not_inherited_through_explicit_candidate_break():
    s=PhysicalIdentityState('phone_01')
    for t in [0.,.2,.4]:
        r=row(t);begin(s,t,[r],[person(t)]);auth(s,r)
    begin(s,.6,[],[person(.6)])
    for t in [.8,1.,1.2]:
        r=row(t,eid='new');r['epoch_split_reason']='EXPLICIT_TRACKER_RESET';begin(s,t,[r],[person(t)])
    assert s.assess(r)['interaction']=='INTERACTION_CONTINUITY_UNKNOWN'

def test_invalid_visual_contract_cannot_confirm_short_continuity():
    for flag in ['bad_geometry','bad_integrity']:
        v=visual()
        if flag=='bad_geometry':v['LightGlue']['state']='INVALID_EVIDENCE'
        else:v['integrity']['admissible']=False
        assert decide(v,physical_evidence(),PhysicalPolicy())['stage']!='CONFIRMED_MATCH'

def test_failed_identity_gate_skips_qwen_without_importing_reasoner(monkeypatch):
    from memory_graph.v297_physical_identity import smoke
    result={};monkeypatch.setattr(smoke,'verify_freeze',lambda:None)
    monkeypatch.setattr(smoke,'read',lambda *args:{'identity_safety_gate_passed':False,'blockers':['test8 unresolved']})
    monkeypatch.setattr(smoke,'save',lambda p,value:result.update(value))
    assert smoke.run_smoke()['status']=='SKIPPED_IDENTITY_SAFETY_GATE'
    assert result['model_loaded'] is False
