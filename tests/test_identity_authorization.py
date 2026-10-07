"""Deterministic contract/adversarial tests, independent of validation videos."""
from dataclasses import replace
import pytest
from memory_graph.identity.contracts import Observation, Policy
from memory_graph.identity.guard import IdentityGuard

def obs(t, candidate='track:1', vector=(1.,0.), box=(0.,0.,20.,30.), **kw):
    return Observation(f'{candidate}@{t}',candidate,round(t*30),t,box,'cell phone',.9,
                       'fixture:raw',vector=vector,**kw)
def bound(policy=None):
    g=IdentityGuard(policy or Policy())
    for t in (0.,.2,.4):g.process(t,[obs(t)])
    assert g.snapshot()['aliases'][0]['status']=='CONFIRMED'
    return g

@pytest.mark.parametrize('candidate',['track:1','track:99','raw:7'])
def test_post_gap_overlap_never_authorizes(candidate):
    g=bound();g.process(4.,[obs(4.,candidate,sam_overlap=1.)])
    assert not any(x['observation']['time']==4 for x in g.final_ledger())
    assert len(g.snapshot()['aliases'])==1
    assert g.snapshot()['epochs'][0]['end_reason']=='OBSERVATION_GAP'

def test_short_continuity_observation_only():
    g=bound();g.process(.6,[obs(.6)])
    assert g.final_ledger()[-1]['observation']['time']==.6
    auth=g.snapshot()['authorizations'][-1]
    assert auth['capabilities']==['AUTHORIZE_OBSERVATION']

def test_high_similarity_is_provisional_without_calibration():
    g=bound();g.process(4.,[obs(4.,'new')])
    assert g.snapshot()['decisions'][-1]['decision']=='PROVISIONAL'
    assert len(g.snapshot()['banks']['core'])==3
    assert len(g.snapshot()['aliases'])==1

@pytest.mark.parametrize('method',['bind_alias','commit_bank','authorize_observation','restart_sam'])
def test_direct_writes_require_nonforgeable_capability(method):
    g=bound()
    with pytest.raises(PermissionError):
        g.write(method, {'authorization_id':'invented'},obs(.6),'core')

def test_serialized_or_reused_token_not_authority():
    g=bound(); record=g.snapshot()['authorizations'][0]
    with pytest.raises(PermissionError):g.write('bind_alias',record,obs(.4),'core')
    ticket=g.restart_tickets()[0]
    g.restart_target_sam(ticket,obs(.4).observation_id,lambda _: 'executed')
    with pytest.raises(PermissionError):g.restart_target_sam(ticket,obs(.4).observation_id,lambda _:None)

def test_wrong_scope_and_changed_observation_rejected():
    g=bound();ticket=g.restart_tickets()[0]
    with pytest.raises(PermissionError):g.restart_target_sam(ticket,'wrong',lambda _:None)
    with pytest.raises(PermissionError):g.write('authorize_observation',ticket,obs(99.),'core')

def test_stale_sam_ticket_rejected_after_epoch_break():
    g=bound();ticket=g.restart_tickets()[0];g.process(5.,[])
    with pytest.raises(PermissionError):g.restart_target_sam(ticket,obs(.4).observation_id,lambda _:None)

def test_multiple_competitors_ambiguous():
    g=bound();g.process(4.,[obs(4.,'a'),obs(4.,'b',box=(100.,0.,120.,30.))])
    assert all(x['decision']=='AMBIGUOUS' for x in g.snapshot()['decisions'][-2:])

def test_semantic_mismatch_rejected():
    g=bound();g.process(4.,[replace(obs(4.,'other'),label='chair')])
    assert g.snapshot()['decisions'][-1]['decision']=='REJECTED'

def test_drift_breaks_even_with_overlap():
    g=bound();g.process(.6,[obs(.6,sam_overlap=1.,drift=True)])
    assert not any(x['observation']['time']==.6 for x in g.final_ledger())

def test_no_persistent_alias_for_short_track_fragment():
    g=bound();g.process(.6,[obs(.6,'fragment',sam_overlap=.9)])
    assert g.final_ledger()[-1]['observation']['candidate_id']=='fragment'
    assert all(x['candidate_id']!='fragment' for x in g.snapshot()['aliases'])

def strong_recovered():
    # Synthetic full-gate fixture. This policy is NOT deployed or calibrated.
    g=bound(Policy(automatic_confirmation_enabled=True,calibration_id='SYNTHETIC_ONLY'))
    for t in (4.,4.2,4.4):
        g.process(t,[obs(t,'new'),obs(t,'distinct',vector=(0.,1.),box=(100.,0.,120.,30.))])
    return g

def test_synthetic_multi_evidence_can_confirm():
    g=strong_recovered();aliases=g.snapshot()['aliases']
    assert any(x['candidate_id']=='new' and x['status']=='CONFIRMED' for x in aliases)
    assert g.snapshot()['banks']['quarantine']
    assert len(g.snapshot()['banks']['core'])==3

def test_one_high_score_cannot_confirm_even_under_synthetic_policy():
    g=bound(Policy(automatic_confirmation_enabled=True,calibration_id='SYNTHETIC_ONLY'))
    g.process(4.,[obs(4.,'new'),obs(4.,'distinct',vector=(0.,1.),box=(100.,0.,120.,30.))])
    assert not any(x['candidate_id']=='new' for x in g.snapshot()['aliases'])

def test_revocation_cascades_to_earlier_ledger_bank_and_sam():
    g=strong_recovered()
    g.process(4.6,[obs(4.6,'new'),obs(4.6,'track:1',box=(100.,0.,120.,30.))])
    snap=g.snapshot()
    assert any(x['candidate_id']=='new' and x['status']=='REVOKED' for x in snap['aliases'])
    assert all(x['observation']['candidate_id']!='new' for x in g.final_ledger())
    assert all(not x['active'] for x in snap['banks']['quarantine'])
    assert any(x['candidate_id']=='new' for x in snap['ledger'])

def test_negative_distractor_does_not_pollute_core():
    g=bound();g.process(.6,[obs(.6),obs(.6,'other',vector=(0.,1.),box=(100.,0.,120.,30.))])
    g.process(4.,[obs(4.,'other',vector=(0.,1.))])
    assert g.snapshot()['banks']['negative']
    assert g.snapshot()['decisions'][-1]['decision']=='REJECTED'
    assert len(g.snapshot()['banks']['core'])==3

def test_every_authorized_observation_has_lineage():
    g=bound();g.process(.6,[obs(.6)])
    for row in g.final_ledger():
        assert row['authorization_id'] and row['alias_id'] and row['epoch_id']
        assert row['evidence_hash'] and row['observation']['provenance']

def test_snapshot_cannot_mutate_authority():
    g=bound();s=g.snapshot();s['aliases'][0]['candidate_id']='evil'
    assert g.snapshot()['aliases'][0]['candidate_id']=='track:1'

def test_out_of_order_or_duplicate_evidence_rejected():
    g=bound()
    with pytest.raises(ValueError):g.process(.1,[obs(.1)])
    with pytest.raises(ValueError):g.process(.6,[obs(.4)])

def test_initial_binding_keeps_unresolved_seen_competitor_in_quality_ranking():
    g=IdentityGuard()
    for t in (0.,.2,.4):
        g.process(t,[obs(t,'a'),obs(t,'b',box=(100.,0.,120.,30.))])
    assert not g.snapshot()['aliases']
    # Absence of an unresolved mature competitor does not prove uniqueness.
    g.process(.6,[obs(.6,'a')])
    assert not g.snapshot()['aliases']
