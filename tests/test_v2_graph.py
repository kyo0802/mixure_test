from memory_graph.config_v2 import V2Config
from memory_graph.vlm.parser import parse_result
from memory_graph.scene_graph.builder import build_scene
from memory_graph.memory.temporal_memory import fuse_relations
from memory_graph.memory.transition_builder import build_transitions
from v2_helpers import timelines,event,frames


def test_geometry_agreement_and_conflict():
    tracks,meta=timelines([[(10,20)]*6,[(25,20)]*6])
    raw={'event_id':'evt_001','entities':[], 'relations':[{'subject_track_id':1,'object_track_id':2,
         'predicate':'NEAR','confidence':.9,'temporal_phase':'persistent'}]}
    result=parse_result(raw,[1,2],'evt_001')
    scene=build_scene(event(),frames(),tracks,meta,V2Config(),result,'success')
    assert any(r.evidence.vlm and r.evidence.geometry=='supports' for r in scene.relations)
    far,meta=timelines([[(0,0)]*6,[(85,85)]*6])
    scene=build_scene(event(),frames(),far,meta,V2Config(),result,'success')
    assert not any(r.evidence.vlm for r in scene.relations)
    assert scene.rejected_relations


def test_unknown_backend_does_not_fabricate_semantics_or_interactions():
    tracks,meta=timelines([[(10,20)]*6,[(25,20)]*6])
    scene=build_scene(event(),frames(),tracks,meta,V2Config())
    assert all(e.semantic_class=='unknown' for e in scene.entities)
    assert all(not r.evidence.vlm for r in scene.relations)
    assert not any(r.predicate in {'ON','HOLDING','PICKING_UP'} for r in scene.relations)


def test_repeated_relations_merge_but_long_gap_does_not():
    tracks,meta=timelines([[(10,20)]*6,[(25,20)]*6])
    a=build_scene(event(),frames(),tracks,meta,V2Config())
    b=a.model_copy(deep=True);b.event_id='evt_002'
    for r in b.relations:
        r.start_time+=2;r.end_time+=2;r.observed_times=[t+2 for t in r.observed_times];r.event_ids=['evt_002']
    merged=fuse_relations([a,b],{1,2},1.2)
    assert len(merged)==len(a.relations)
    assert all(r.event_ids==['evt_001','evt_002'] and r.end_time==3.6 for r in merged)
    for r in b.relations:
        r.start_time+=10;r.end_time+=10
    assert len(fuse_relations([a,b],{1,2},1.2))==2*len(a.relations)


def test_temporal_claim_requires_multiple_observed_frames():
    tracks, meta = timelines([[(10,20)]*6, [(25,20)]*6])
    raw = {'event_id':'evt_001', 'entities':[], 'relations':[{
        'subject_track_id':1, 'object_track_id':2, 'predicate':'NEAR',
        'confidence':.9, 'temporal_phase':'persistent'}]}
    result = parse_result(raw, [1,2], 'evt_001')
    scene = build_scene(event(), frames(times=(0,0,0)), tracks, meta, V2Config(), result, 'success')
    assert not any(r.evidence.vlm for r in scene.relations)
    assert 'distinct' in scene.rejected_relations[0]['reason']


def test_direction_inside_geometry_deadband_is_not_promoted():
    tracks, meta = timelines([[(10,20)]*6, [(10.5,20)]*6])
    raw = {'event_id':'evt_001','entities':[], 'relations':[{
        'subject_track_id':1,'object_track_id':2,'predicate':'LEFT_OF',
        'confidence':.95,'temporal_phase':'during'}]}
    scene = build_scene(event(), frames(), tracks, meta, V2Config(), parse_result(raw,[1,2],'evt_001'),'success')
    assert not any(r.evidence.vlm for r in scene.relations)
    assert 'insufficient geometric support' in scene.rejected_relations[0]['reason']


def test_temporal_fusion_preserves_distinct_phase_claims():
    tracks, meta = timelines([[(10,20)]*6, [(25,20)]*6])
    scene = build_scene(event(), frames(), tracks, meta, V2Config())
    before = scene.model_copy(deep=True)
    after = scene.model_copy(deep=True)
    for relation in before.relations:
        relation.temporal_phase = 'before'
    for relation in after.relations:
        relation.temporal_phase = 'after'
    merged = fuse_relations([before, after], {1,2}, 1.2)
    assert len(merged) == 2*len(scene.relations)
    assert {r.temporal_phase for r in merged} == {'before','after'}


def test_person_object_interaction_requires_semantic_actor_and_nearby_evidence():
    tracks, meta = timelines([[(10,20)]*6, [(25,20)]*6], ['person','cup'])
    raw = {'event_id':'evt_001', 'entities':[
        {'track_id':1, 'semantic_class':'person', 'confidence':.9},
        {'track_id':2, 'semantic_class':'basketball', 'confidence':.9}],
        'relations':[{'subject_track_id':1, 'object_track_id':2, 'predicate':'HOLDING',
                      'confidence':.9, 'temporal_phase':'during'}]}
    result = parse_result(raw, [1,2], 'evt_001')
    scene = build_scene(event(), frames(), tracks, meta, V2Config(), result, 'success')
    holding = next(r for r in scene.relations if r.predicate == 'HOLDING')
    assert holding.evidence.vlm and holding.evidence.geometry == 'not_testable'
    assert holding.evidence.details['physical_or_action_verification'] is False
    raw['entities'][0]['semantic_class'] = 'hand'
    scene = build_scene(event(), frames(), tracks, meta, V2Config(), parse_result(raw,[1,2],'evt_001'), 'success')
    assert any(r.predicate == 'HOLDING' and r.evidence.details['actor_scope'] == 'hand' for r in scene.relations)
    raw['entities'][0]['semantic_class'] = 'unknown'
    scene = build_scene(event(), frames(), tracks, meta, V2Config(), parse_result(raw,[1,2],'evt_001'), 'success')
    assert not any(r.predicate == 'HOLDING' for r in scene.relations)


def test_observed_transitions_require_vlm_evidence_and_nonoverlapping_support():
    tracks,meta = timelines([[(10,20)]*6,[(25,20)]*6])
    scene = build_scene(event(),frames(),tracks,meta,V2Config())
    before = next(r for r in scene.relations if r.predicate == 'NEAR').model_copy(deep=True)
    after = before.model_copy(deep=True)
    after.start_time,after.end_time,after.observed_times = 2,3,[2,3]
    after.object_track_id = 3
    assert build_transitions([before,after],3) == []
    before.evidence.vlm = after.evidence.vlm = True
    transitions = build_transitions([before,after],3)
    assert len(transitions) == 1 and transitions[0]['causal_claim'] is False
    after.start_time = 1
    assert build_transitions([before,after],3) == []
