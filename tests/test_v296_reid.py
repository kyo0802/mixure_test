"""Real authority API invariants and synthetic evidence contract edge cases."""
from dataclasses import replace
import numpy as np
import pytest
from memory_graph.identity.contracts import Observation,Policy
from memory_graph.identity.guard import IdentityGuard
from memory_graph.v296_reid.epochs import CandidateEpochBuilder,EpochPolicy
from memory_graph.v296_reid.integrity import pair_integrity,candidate_integrity
from memory_graph.v296_reid.appearance import photometric_veto
from memory_graph.v296_reid.evidence import ConfirmationPolicy,TemporalAccumulator
from memory_graph.v296_reid.guard import V296IdentityGuard

def row(t,local='new',epoch='new_epoch',**kwargs):
    return {'video_id':'synthetic','frame':round(t*30),'time':t,'observation_id':f'{local}@{t}','candidate_id':local,
        'candidate_epoch_id':epoch,'candidate_epoch_start':4.,'local_track_id':local,'local_track_ids':[local],
        'bbox':[0,0,100,150],'label':'cell phone','confidence':.9,'source':'yolo_track','sam_overlap':0.,'drift':False,
        'scene_break':False,'epoch_unresolved':False,'v3':[1.,.04],'v2':[1.,.04],
        'crop_sha256':f'crop-{local}-{t}','raw_image_sha256':f'frame-{t}','raw_image_path':'original.mp4#frame',
        'raw_crop_path':'clean.png','annotation_overlays':False,'raw_source_verified':True,'evidence_producer':'original-frame-canonical',**kwargs}
def bank(t=0.,epoch='initial',**kwargs):
    r=row(t,local='initial',epoch=epoch)
    return {**r,'entry_id':f'bank:{t}','embedding':[1.,0.],'active':True,'authorization_id':'auth:initial',
        'parent_lineage':['alias:initial'],'alias_id':'alias:initial','epoch_id':1,**kwargs}
def config():return ConfirmationPolicy(g_support=.8,g_lower=.75,a_support=.85,a_lower=.82,v2_support=.8,a_frames=5,a_duration=.8,calibrated=True)
def evaluate(geometry='CORE_STRONG_MATCH',veto='UNKNOWN',neg=False,rows=None):
    rows=rows or [row(x) for x in [4.,4.2,4.4]];cores=[bank(),bank(.2)]
    a=TemporalAccumulator(config())
    return a.evaluate(rows,cores,[],[rows[-1]],True,lambda r:r['v2'],
       lambda *args:{'state':geometry,'core_pairs':[],'negative_positive':neg,'integrity_valid':geometry!='INVALID_EVIDENCE'},
       lambda *args:{'state':veto})

def test_epoch_same_id_gap_splits():
    b=CandidateEpochBuilder('unit');first=b.process([row(0.)])[0];second=b.process([row(4.)])[0]
    assert first['candidate_epoch_id']!=second['candidate_epoch_id']
def test_short_fragment_stitch_has_no_identity_authority():
    b=CandidateEpochBuilder('unit');first=b.process([row(0.,local='a')])[0];second=b.process([row(.2,local='b')])[0]
    assert first['candidate_epoch_id']==second['candidate_epoch_id']
    assert not hasattr(b,'write') and not hasattr(b,'_issue')
def test_no_stitch_simultaneous_distinct_objects():
    b=CandidateEpochBuilder('unit');r=b.process([row(0.,local='a'),row(0.,local='b',bbox=[200,0,300,150])])
    assert r[0]['candidate_epoch_id']!=r[1]['candidate_epoch_id']
def test_single_noisy_frame_pending_not_split():
    b=CandidateEpochBuilder('unit');a=b.process([row(0.)])[0]
    noise=b.process([row(.2,v3=[0.,1.])])[0];good=b.process([row(.4)])[0]
    assert noise['epoch_unresolved'] and good['candidate_epoch_id']==a['candidate_epoch_id'] and not good['epoch_unresolved']
def test_sustained_change_splits():
    b=CandidateEpochBuilder('unit');a=b.process([row(0.)])[0];b.process([row(.2,v3=[0.,1.])]);c=b.process([row(.4,v3=[0.,1.])])[0]
    assert c['candidate_epoch_id']!=a['candidate_epoch_id']
def test_same_observation_cannot_verify_self():
    a=row(4.);b=bank();b.update(a)
    assert 'SELF_EVIDENCE' in pair_integrity(a,a,b,a['observation_id'])['rejection_reasons']
def test_same_crop_hash_cannot_verify():
    a=row(4.);b=bank();a['crop_sha256']=b['crop_sha256']
    assert not pair_integrity(a,b,b,a['observation_id'])['admissible']
def test_core_descendant_same_epoch_cannot_verify():
    a=row(4.);b=bank(epoch='new_epoch')
    assert 'SAME_LINEAGE_REFERENCE' in pair_integrity(a,b,b,a['observation_id'])['rejection_reasons']
def test_circular_lineage_cannot_verify():
    a=row(4.);b=bank(parent_lineage=['candidate_alias'])
    assert not pair_integrity(a,b,b,a['observation_id'],alias='candidate_alias')['admissible']
def test_reference_after_epoch_start_cannot_verify():
    a=row(4.4);b=bank(4.2)
    assert 'CROSS_CANDIDATE_EPOCH_EVIDENCE' in pair_integrity(a,b,b,a['observation_id'])['rejection_reasons']
def test_old_reference_committed_after_candidate_start_forbidden():
    a=row(4.4);b=bank(0.,created_time=4.2)
    assert not pair_integrity(a,b,b,a['observation_id'])['admissible']
def test_stronger_negative_appearance_blocks_confirmation():
    rows=[row(x,v3=[.8,.6]) for x in [4.,4.2,4.4]];neg=bank(-1.,embedding=[.8,.6])
    result=TemporalAccumulator(config()).evaluate(rows,[bank(),bank(.2)],[neg],[rows[-1]],True,lambda r:r['v2'],
        lambda *args:{'state':'CORE_STRONG_MATCH','negative_positive':False,'integrity_valid':True},lambda *args:{'state':'UNKNOWN'})
    assert result['stage']=='REJECTED'
def test_route_g_verifier_uses_current_only_without_gpu(monkeypatch):
    from memory_graph.v296_reid.geometry import CurrentLightGlue
    verifier=CurrentLightGlue.__new__(CurrentLightGlue);verifier.results=[];verifier.invalid_pairs=[]
    seen=[]
    def compare(a,b):
        seen.append(a['observation_id']);return {'status':'STRONG_MATCH'}
    monkeypatch.setattr(verifier,'compare',compare)
    a=row(4.4);b=bank();result=verifier.verify(a,[b],[],[1.],[])
    assert result['state']=='CORE_STRONG_MATCH' and seen==[a['observation_id']]
def test_invalid_current_pair_cannot_reach_matcher(monkeypatch):
    from memory_graph.v296_reid.geometry import CurrentLightGlue
    verifier=CurrentLightGlue.__new__(CurrentLightGlue);verifier.results=[];verifier.invalid_pairs=[]
    monkeypatch.setattr(verifier,'compare',lambda *args:pytest.fail('invalid evidence reached matcher'))
    a=row(4.4,annotation_overlays=True);b=bank()
    assert verifier.verify(a,[b],[],[1.],[])['state']=='INVALID_EVIDENCE'
def test_mask_acquisition_is_not_itself_physical_change():
    b=CandidateEpochBuilder('unit');a=b.process([row(0.,foreground_mask_path=None)])[0]
    mid=b.process([row(.2,v3=[.6,.8],foreground_mask_path='mask.png',sam_overlap=.95)])[0]
    later=b.process([row(.4,v3=[.6,.8],foreground_mask_path='mask.png',sam_overlap=.95)])[0]
    assert a['candidate_epoch_id']==mid['candidate_epoch_id']==later['candidate_epoch_id'] and not mid['epoch_unresolved']
def test_ancestor_bank_ids_forbid_other_epoch_descendant():
    a=row(4.,bank_ancestor_ids=['ancestor']);b=bank(parent_lineage=['ancestor'])
    assert not pair_integrity(a,b,b,a['observation_id'])['admissible']
def test_explicit_tracker_reset_splits_without_gap():
    b=CandidateEpochBuilder('unit');a=b.process([row(0.)])[0];c=b.process([row(.2,tracker_reset=True)])[0]
    assert a['candidate_epoch_id']!=c['candidate_epoch_id']
def test_mixed_video_temporal_evidence_forbidden():
    rows=[row(4.,video_id='different')]+[row(x) for x in [4.2,4.4]]
    assert not candidate_integrity(rows,rows[-1])['admissible']
def test_revocation_excludes_backfilled_descendants():
    g,m=bound_guard()
    for t in [4.,4.2,4.4]:current=advance(g,m,t)
    token=g._issue(current,'REVOKED',['REVOKE_ALIAS'],g._active_alias,reason='SYNTHETIC_CONTRADICTION')
    g.write('revoke_alias',token,current)
    assert not any(r['candidate_id']=='new_epoch' for r in g.final_ledger())
    assert not any(b['active'] and b['candidate_id']=='new_epoch' for b in g.snapshot()['banks']['quarantine'])
def test_old_frame_cannot_provide_current_geometry():
    a=row(4.);b=bank();r=pair_integrity(a,b,b,row(4.4)['observation_id'])
    assert 'OLD_FRAME_ONLY_CONFIRMATION' in r['rejection_reasons']
def test_annotated_crop_forbidden():
    a=row(4.,annotation_overlays=True);b=bank()
    assert 'ANNOTATED_IMAGE_USED_FOR_REID' in pair_integrity(a,b,b,a['observation_id'])['rejection_reasons']
def test_negative_absence_not_positive_identity():
    r=evaluate(geometry='UNKNOWN');assert r['negative_state']=='NO_INFORMATION' and r['stage']!='CONFIRMED_MATCH'
def test_negative_geometry_blocks_both_routes():
    assert evaluate(neg=True)['stage']=='REJECTED'
def test_photometric_strong_veto_blocks():
    assert evaluate(veto='STRONG_CONTRADICTION')['stage']=='REJECTED'
def test_photometric_no_contradiction_not_identity():
    assert evaluate(geometry='UNKNOWN',veto='NO_CONTRADICTION')['stage']!='CONFIRMED_MATCH'
def test_dino_agreement_without_persistence_not_identity():
    assert evaluate(geometry='UNKNOWN',rows=[row(4.)])['stage']!='CONFIRMED_MATCH'
def test_route_a_unknown_geometry_can_confirm_strict_tracklet():
    r=evaluate(geometry='UNKNOWN',rows=[row(x) for x in [4.,4.2,4.4,4.6,4.8]])
    assert r['route']=='A' and r['stage']=='CONFIRMED_MATCH'
def test_invalid_geometry_cannot_confirm():
    assert evaluate(geometry='INVALID_EVIDENCE',rows=[row(x) for x in [4.,4.2,4.4,4.6,4.8]])['stage']!='CONFIRMED_MATCH'
def test_route_g_current_independent_geometry_confirms():
    r=evaluate();assert r['route']=='G' and r['stage']=='CONFIRMED_MATCH' and r['current_observation']==row(4.4)['observation_id']
def test_current_low_appearance_cannot_reuse_old_high():
    rows=[row(x) for x in [4.,4.2,4.4]]+[row(4.6,v3=[0.,1.])]
    assert evaluate(rows=rows)['stage']!='CONFIRMED_MATCH'
def test_cross_epoch_temporal_rows_forbidden():
    rows=[row(4.,epoch='old')]+[row(x) for x in [4.2,4.4]]
    assert not candidate_integrity(rows,rows[-1])['admissible']
def test_photometric_output_is_veto_only():
    assert photometric_veto({'usable':False},[],100.)['state']=='UNKNOWN'
    a={'usable':True,'ab':[0.,0.]};b={'usable':True,'ab':[1.,1.]}
    assert photometric_veto(a,[b],100.)['state']=='NO_CONTRADICTION'

def bound_guard(geometry='CORE_STRONG_MATCH'):
    metadata={}
    g=V296IdentityGuard(Policy(),config(),metadata,lambda r:r['v2'],
        lambda *args:{'state':geometry,'negative_positive':False,'integrity_valid':geometry!='INVALID_EVIDENCE','core_pairs':[]},
        lambda *args:{'state':'UNKNOWN'})
    for t in [0.,.2,.4]:
        r=row(t,local='initial',epoch='initial');r['candidate_epoch_start']=0.;metadata[r['observation_id']]=r
        o=Observation(r['observation_id'],'initial',r['frame'],t,tuple(r['bbox']),'cell phone',.9,'raw:syn',vector=(1.,.04))
        g.process(t,[o])
    return g,metadata
def advance(g,metadata,t,epoch='new_epoch',**kwargs):
    r=row(t,epoch=epoch,**kwargs);metadata[r['observation_id']]=r
    o=Observation(r['observation_id'],epoch,r['frame'],t,tuple(r['bbox']),'cell phone',.9,'raw:syn',vector=tuple(r['v3']),source=r['source'],sam_overlap=r['sam_overlap'])
    g.process(t,[o]);return o
def test_backfill_same_epoch_guard_capability_only():
    g,m=bound_guard()
    for t in [4.,4.2,4.4]:advance(g,m,t)
    s=g.snapshot();new=[r for r in s['final_ledger'] if r['candidate_id']=='new_epoch']
    assert [r['observation']['time'] for r in new]==[4.4,4.,4.2]
    assert len(s['banks']['core'])==3 and s['backfill_events'][0]['backfilled_start']==4.
    assert all(any(a['authorization_id']==r['authorization_id'] for a in s['authorizations']) for r in new)
def test_backfill_never_crosses_epoch_boundary():
    g,m=bound_guard();advance(g,m,4.,epoch='different');advance(g,m,4.2);advance(g,m,4.4);advance(g,m,4.6)
    assert not any(r['candidate_id']=='different' for r in g.final_ledger())
def test_provisional_cannot_core_or_alias():
    g,m=bound_guard('UNKNOWN')
    for t in [4.,4.2,4.4]:advance(g,m,t)
    assert len(g.snapshot()['aliases'])==1 and len(g.snapshot()['banks']['core'])==3
def test_confirmation_never_floods_core():
    g,m=bound_guard()
    for t in [4.,4.2,4.4]:advance(g,m,t)
    assert len(g.snapshot()['banks']['core'])==3
@pytest.mark.parametrize('source',['sam','yolo_raw','yolo_track'])
def test_sam_yolo_id_iou_alone_cannot_authorize_gap(source):
    g,m=bound_guard();advance(g,m,4.,source=source,sam_overlap=1.)
    assert len(g.snapshot()['aliases'])==1
def test_authority_methods_inherited_verbatim_and_forgery_rejected():
    for name in ['_issue','_check','write','_revoke','final_ledger','_bank','restart_target_sam']:
        assert getattr(V296IdentityGuard,name) is getattr(IdentityGuard,name)
    g,m=bound_guard()
    with pytest.raises(PermissionError):g.write('bind_alias',{'route':'A'},Observation('x','x',120,4.,(0,0,1,1),'cell phone',.9,'raw'))
