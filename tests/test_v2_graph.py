from memory_graph.config_v2 import V2Config
from memory_graph.vlm.parser import parse_result
from memory_graph.scene_graph.builder import build_scene
from memory_graph.memory.temporal_memory import fuse_relations
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
