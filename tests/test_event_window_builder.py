from copy import deepcopy
from memory_graph.events.window_builder import WindowConfig,adaptive_window,select_events,dense_frames,target_timeline

def timeline(fps=10):
    return [{'frame':i,'time':i/fps,'identity_authorized':True,'target_bbox':[i,10,i+10,20],
        'image_size':[1000,600],'motion_state':'STATIONARY' if i<20 or i>=40 else 'MOVING',
        'visibility':'VISIBLE','chain_id':'authorized-chain','anchors':[],'scene_ok':True,'carried_like':False} for i in range(int(fps*7))]

def test_adaptive_complete_contains_pre_transition_post():
    rows=timeline();e=adaptive_window(rows,{'index':40,'trigger':'MOVING_TO_STATIONARY','category':'PHYSICAL_INTERACTION_EVENT'})
    assert e['completeness']=='COMPLETE_EVENT_WINDOW'
    assert e['start_time']<4<e['end_time'] and e['duration_seconds']>=2
    assert e['HAS_PRE_STATE'] and e['HAS_TRANSITION'] and e['HAS_POST_STATE']

def test_no_pre_state_is_not_sent_as_physical_evidence():
    rows=timeline()[36:];e=adaptive_window(rows,{'index':4,'trigger':'MOVING_TO_STATIONARY','category':'PHYSICAL_INTERACTION_EVENT'})
    assert e['completeness']=='INCOMPLETE_EVENT_WINDOW' and 'NO_STABLE_PRE_STATE' in e['failure_categories']

def test_no_stable_post_cannot_be_complete():
    rows=timeline()[:44];e=adaptive_window(rows,{'index':40,'trigger':'MOVING_TO_STATIONARY','category':'PHYSICAL_INTERACTION_EVENT'})
    assert not e['HAS_POST_STATE']

def test_identity_chain_change_is_rejected():
    rows=timeline()
    for r in rows[40:]:r['chain_id']='new-chain'
    e=adaptive_window(rows,{'index':40,'trigger':'MOVING_TO_STATIONARY','category':'PHYSICAL_INTERACTION_EVENT'})
    assert e['completeness']=='INCOMPLETE_EVENT_WINDOW' and 'UPSTREAM_IDENTITY_LIMITATION' in e['failure_categories']

def test_observation_coverage_gap_is_not_filled():
    rows=timeline();rows=rows[:30]+rows[38:]
    e=adaptive_window(rows,{'index':32,'trigger':'MOVING_TO_STATIONARY','category':'PHYSICAL_INTERACTION_EVENT'})
    assert e['completeness']=='INCOMPLETE_EVENT_WINDOW'

def test_lifecycle_does_not_consume_physical_budget():
    rows=timeline()
    for i in range(50,69,2):rows[i].update(identity_authorized=False,visibility='UNOBSERVED',motion_state='UNKNOWN',chain_id=None)
    _,selected,queues=select_events(rows,WindowConfig(physical_budget_per_video=1,lifecycle_budget_per_video=1))
    assert queues['PHYSICAL_INTERACTION_EVENT']['selected']==1
    assert queues['IDENTITY_LIFECYCLE_EVENT']['selected']==1
    assert sum(e['category']=='PHYSICAL_INTERACTION_EVENT' for e in selected)==1

def test_dense_sequence_preserves_bounds_and_transition():
    rows=timeline();e=adaptive_window(rows,{'index':40,'trigger':'MOVING_TO_STATIONARY','category':'PHYSICAL_INTERACTION_EVENT'})
    frames=dense_frames(rows,e)
    assert len(frames)>5 and frames[0]['frame']==e['start_frame'] and frames[-1]['frame']==e['end_frame']
    assert e['transition_frame'] in [f['frame'] for f in frames]

def test_seconds_are_independent_of_frame_indices():
    rows=timeline();other=deepcopy(rows)
    for r in other:r['frame']*=3
    t={'index':40,'trigger':'MOVING_TO_STATIONARY','category':'PHYSICAL_INTERACTION_EVENT'}
    a=adaptive_window(rows,t);b=adaptive_window(other,t)
    assert (a['start_time'],a['end_time'])==(b['start_time'],b['end_time'])

def test_motion_processing_cannot_mutate_identity_inputs():
    rows=timeline();original=deepcopy(rows);result=target_timeline(rows)
    assert rows==original and [r['identity_authorized'] for r in result]==[r['identity_authorized'] for r in rows]
    assert all('identity_write_authorized' not in r for r in rows)

def test_untrusted_candidate_never_becomes_target():
    rows=timeline();rows[20].update(identity_authorized=False,candidate_present=True)
    result=target_timeline(rows)
    assert result[20]['visibility']=='UNTRUSTED' and not result[20]['identity_authorized']
