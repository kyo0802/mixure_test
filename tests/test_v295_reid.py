"""Identity evidence must never become a second mutation authority."""
from dataclasses import replace
import numpy as np
import pytest
from memory_graph.identity.contracts import Observation
from memory_graph.identity.guard import IdentityGuard
from memory_graph.v295_reid.evidence import RecoveryPolicy,TrackletIdentityEvidenceAccumulator
from memory_graph.v295_reid.geometry import geometry_statistics,strong_geometry


def obs(t,candidate='new',v=(1.,.04),**kwargs):
    return Observation(f'{candidate}@{t}',candidate,round(t*30),t,(0,0,100,150),'cell phone',.9,'synthetic:raw',vector=v,**kwargs)

def bank(v=(1.,0.),kind='core',active=True):
    return {'entry_id':f'{kind}:{v}','embedding':v,'active':active,'authorization_id':'guard:1','parent_lineage':['alias:1']}

def evaluate(rows,negative=(),geom=None,current=None,core=None):
    p=RecoveryPolicy(core_support=.8,lower_support=.75,automatic_confirmation_enabled=True,calibration_id='SYNTHETIC_TEST_ONLY')
    a=TrackletIdentityEvidenceAccumulator(p)
    return a.evaluate('new',rows,core or [bank(),bank((.99,.1))],list(negative),current or [rows[-1]],True,
                      lambda *args:geom or {'core_positive':True,'negative_positive':False,'status':'CORE_VERIFIED'})


def test_near_target_ranks_over_distractor():
    from memory_graph.identity.contracts import cosine
    assert cosine((1.,.02),(1.,0.))>cosine((0.,1.),(1.,0.))


def test_accumulator_single_lucky_score_is_not_confirmation():
    r=evaluate([obs(4.,v=(0.,1.)),obs(4.2,v=(0.,1.)),obs(4.4,v=(1.,0.))])
    assert not r['gates']['multi_frame_core_support'] and r['stage']!='CONFIRMED_MATCH'


def test_negative_stronger_blocks():
    r=evaluate([obs(x,v=(.8,.6)) for x in [4.,4.2,4.4]],negative=[bank((.8,.6),'negative')])
    assert r['stage']=='REJECTED' and not r['gates']['no_stronger_negative']


def test_core_geometry_supports_multi_frame_confirmation():
    assert evaluate([obs(x) for x in [4.,4.2,4.4]])['stage']=='CONFIRMED_MATCH'


def test_negative_geometry_blocks_even_high_core_similarity():
    r=evaluate([obs(x) for x in [4.,4.2,4.4]],geom={'core_positive':True,'negative_positive':True})
    assert r['stage']=='REJECTED'


def test_geometry_failure_is_unknown_not_rejection():
    r=evaluate([obs(x) for x in [4.,4.2,4.4]],geom={'core_positive':False,'negative_positive':False,'status':'UNKNOWN'})
    assert r['stage']=='PROVISIONAL'


def test_revoked_core_cannot_supply_evidence():
    r=evaluate([obs(x) for x in [4.,4.2,4.4]],core=[bank(active=False),bank((.99,.1),active=False)])
    assert r['core_similarity_matrix']==[[],[],[]] and r['stage']!='CONFIRMED_MATCH'


def test_duplicate_view_hashes_do_not_supply_three_supports():
    rows=[obs(x) for x in [4.,4.2,4.4]];a=TrackletIdentityEvidenceAccumulator(RecoveryPolicy(),{o.observation_id:{'view_hash':'same'} for o in rows})
    assert len(a.independent(rows))==1


def test_gap_reused_local_id_does_not_reuse_persistence():
    rows=[obs(x) for x in [4.,4.2,8.]]
    assert len(TrackletIdentityEvidenceAccumulator(RecoveryPolicy()).independent(rows))==1


@pytest.mark.parametrize('source',['sam','yolo_raw','yolo_track'])
def test_first_perfect_crop_and_iou_do_not_authorize(source):
    r=evaluate([obs(4.,source=source,sam_overlap=1.)])
    assert r['stage']!='CONFIRMED_MATCH'


def test_geometry_requires_inliers_ratio_and_spatial_coverage():
    p=np.array([[10,10],[90,10],[90,90],[10,90],[20,30],[80,30],[30,70],[70,70]],np.float32)
    stats=geometry_statistics(p,p+2,(100,100),(100,100))
    assert strong_geometry(stats,{'min_inliers':8,'min_inlier_ratio':.5,'min_coverage':.1})
    stats['coverage1']=.001
    assert not strong_geometry(stats,{'min_inliers':8,'min_inlier_ratio':.5,'min_coverage':.1})


def test_geometry_failure_never_reports_different_object():
    s=geometry_statistics([],[],(100,100),(100,100))
    assert not strong_geometry(s,{'min_inliers':8,'min_inlier_ratio':.5,'min_coverage':.1})


def test_evidence_and_geometry_have_no_identity_mutation_api():
    for cls in [TrackletIdentityEvidenceAccumulator]:
        assert not any(hasattr(cls,x) for x in ['write','bind_alias','_issue','_authorize'])


def test_canonical_crop_shared_aspect_and_mask_fallback():
    from memory_graph.v295_reid.dataset import crop_observation
    im=np.zeros((100,200,3),np.uint8)
    crop,mask,md=crop_observation(im,(20,20,80,60),np.zeros((100,200),bool))
    assert md['aspect_preserved'] and not md['mask']['used'] and mask is None
    assert crop.shape[:2]==(44,66)


def test_existing_guard_remains_only_authority():
    g=IdentityGuard()
    with pytest.raises(PermissionError):g.write('bind_alias',{'LightGlue':'STRONG_MATCH'},obs(0.))


def bound_guard(geometry=None):
    from memory_graph.v295_reid.guard import V295IdentityGuard
    p=RecoveryPolicy(core_support=.8,lower_support=.75,automatic_confirmation_enabled=True,calibration_id='SYNTHETIC_TEST_ONLY')
    g=V295IdentityGuard(recovery_policy=p,verifier=lambda *args:geometry or {'core_positive':True,'negative_positive':False})
    for t in [0.,.2,.4]:g.process(t,[obs(t,candidate='initial')])
    return g


def test_provisional_never_promotes_core():
    g=bound_guard({'core_positive':False,'negative_positive':False,'status':'UNKNOWN'})
    for t in [4.,4.2,4.4]:g.process(t,[obs(t)])
    s=g.snapshot()
    assert len(s['aliases'])==1 and len(s['banks']['core'])==3
    assert s['banks']['quarantine'] and s['decisions'][-1]['decision']=='PROVISIONAL'


def test_true_long_gap_recovery_is_guard_authorized_and_quarantined():
    g=bound_guard()
    for t in [4.,4.2]:g.process(t,[obs(t)])
    assert len(g.snapshot()['aliases'])==1
    g.process(4.4,[obs(4.4)])
    s=g.snapshot();assert len(s['aliases'])==2 and len(s['banks']['core'])==3
    assert any(b['candidate_id']=='new' for b in s['banks']['quarantine'])
    assert s['final_ledger'][-1]['observation']['time']==4.4
    g.process(4.6,[obs(4.6,v=(.94,.3))])
    assert len(g.snapshot()['banks']['core'])==3


def test_stabilized_diverse_view_has_guard_lineage():
    g=bound_guard()
    for t in [4.,4.2,4.4,4.6]:g.process(t,[obs(t)])
    g.process(4.8,[obs(4.8,v=(.86,.5))])
    core=g.snapshot()['banks']['core'];assert len(core)==4
    assert core[-1]['alias_id'] in core[-1]['parent_lineage'] and core[-1]['authorization_id'].startswith('auth:')


def test_revoked_alias_excludes_descendant_core_and_ledger():
    g=bound_guard()
    for t in [4.,4.2,4.4,4.6]:g.process(t,[obs(t)])
    g.process(4.8,[obs(4.8,v=(.86,.5))])
    other=Observation('initial@5','initial',150,5.,(200,0,300,150),'cell phone',.9,'synthetic:raw',vector=(1.,.04))
    g.process(5.,[obs(5.),other]);s=g.snapshot()
    assert s['aliases'][-1]['status']=='REVOKED'
    assert not any(b['active'] for b in s['banks']['core'] if b['candidate_id']=='new')
    assert not any(r['candidate_id']=='new' for r in s['final_ledger'])


def test_negative_geometry_distractor_never_gains_alias():
    g=bound_guard({'core_positive':True,'negative_positive':True})
    for t in [4.,4.2,4.4]:g.process(t,[obs(t)])
    assert len(g.snapshot()['aliases'])==1 and g.snapshot()['decisions'][-1]['decision']=='REJECTED'


@pytest.mark.parametrize('source',['sam','yolo_raw','yolo_track'])
def test_local_id_high_iou_and_sam_overlap_cannot_reauthorize_gap(source):
    g=bound_guard();g.process(4.,[obs(4.,candidate='initial',source=source,sam_overlap=1.)])
    assert len(g.snapshot()['aliases'])==1 and len(g.final_ledger())==1


def test_current_continuity_still_works():
    g=bound_guard();g.process(.6,[obs(.6,candidate='initial')])
    assert g.final_ledger()[-1]['observation']['time']==.6
    assert g.snapshot()['authorizations'][-1]['decision']=='CONTINUITY_AUTHORIZED'


def test_evidence_cannot_forge_guard_write_or_restart():
    g=bound_guard()
    for payload in [{'DINO':'perfect'},{'LightGlue':'STRONG_MATCH'}]:
        with pytest.raises(PermissionError):g.write('bind_alias',payload,obs(4.))
        with pytest.raises(PermissionError):g.write('commit_bank',payload,obs(4.),'core')


def test_v295_inherits_all_authority_methods_verbatim():
    from memory_graph.v295_reid.guard import V295IdentityGuard
    for method in ['_issue','_check','write','_revoke','_new_epoch','final_ledger','process','_bank','restart_target_sam']:
        assert getattr(V295IdentityGuard,method) is getattr(IdentityGuard,method)


def test_near_duplicate_pixels_do_not_count_as_independent():
    rows=[obs(x) for x in [4.,4.2,4.4]]
    metadata={o.observation_id:{'pixel_descriptor':np.full((32,32,3),i)} for i,o in enumerate(rows)}
    a=TrackletIdentityEvidenceAccumulator(RecoveryPolicy(),metadata)
    assert len(a.independent(rows))==1


def test_current_drift_cannot_use_earlier_good_frames_to_confirm():
    rows=[obs(x) for x in [4.,4.2,4.4]]+[obs(4.6,drift=True)]
    r=evaluate(rows);assert not r['gates']['current_observation_supported'] and r['stage']!='CONFIRMED_MATCH'


def test_scene_break_cannot_reauthorize_from_old_tracklet():
    rows=[obs(x) for x in [4.,4.2,4.4]]+[obs(4.6,scene_break=True)]
    assert evaluate(rows)['stage']!='CONFIRMED_MATCH'
