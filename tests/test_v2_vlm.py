import json
import pytest
from memory_graph.vlm.parser import parse_result
from memory_graph.vlm.cache import analyze_cached
from memory_graph.scene_graph.fusion import aggregate_entities
from memory_graph.config_v2 import V2Config
from v2_helpers import timelines,event


def response(label='basketball',confidence=.9):
    return {'event_id':'evt_001','entities':[{'track_id':1,'semantic_class':label,'confidence':confidence,'attributes':{'color':'orange'}}],
            'relations':[]}


def test_invalid_ids_and_predicates_rejected():
    with pytest.raises(ValueError,match='unsupplied'):
        parse_result(response(),[2],'evt_001')
    raw=response();raw['relations']=[{'subject_track_id':1,'object_track_id':2,'predicate':'OWNS','confidence':.9,'temporal_phase':'during'}]
    with pytest.raises(ValueError):
        parse_result(raw,[1,2],'evt_001')
    with pytest.raises(ValueError):
        parse_result(response(),[1],'evt_002')


def test_prose_is_not_accepted_and_ownership_attribute_rejected():
    with pytest.raises(ValueError):
        parse_result('The object is a basketball.',[1],'evt_001')
    raw=response();raw['entities'][0]['attributes']={'owner':'person'}
    with pytest.raises(ValueError):
        parse_result(raw,[1],'evt_001')


def test_semantic_correction_preserves_identity():
    tracks,_=timelines([[(10,20)]*6])
    entities,rejected,_=aggregate_entities(tracks,[event(ids=(1,))],[parse_result(response(),[1],'evt_001')],V2Config())
    assert not rejected and entities[0].track_id==1
    assert entities[0].semantic_class=='basketball' and entities[0].detector_class=='cup'
    assert entities[0].entity_id=='basketball_01'


def test_weak_or_conflicting_semantics_remain_unknown():
    tracks,_=timelines([[(10,20)]*6])
    weak=parse_result(response(confidence=.2),[1],'evt_001')
    entities,_,_=aggregate_entities(tracks,[event(ids=(1,))],[weak],V2Config())
    assert entities[0].semantic_class=='unknown' and not entities[0].attributes
    a=parse_result(response(),[1],'evt_001')
    b=parse_result(response('cup'),[1],'evt_001')
    entities,_,_=aggregate_entities(tracks,[event(ids=(1,))],[a,b],V2Config())
    assert entities[0].semantic_class=='unknown'


def test_separate_chairs_are_never_merged_by_class():
    tracks,_=timelines([[(10,20)]*6,[(50,20)]*6],['chair','chair'])
    raw=response('chair');raw['entities'].append({'track_id':2,'semantic_class':'chair','confidence':.9,'attributes':{}})
    entities,_,_=aggregate_entities(tracks,[event()],[parse_result(raw,[1,2],'evt_001')],V2Config())
    assert [(e.track_id,e.entity_id) for e in entities]==[(1,'chair_01'),(2,'chair_02')]


def test_cache_invalidation_uses_images_prompt_metadata_and_model(tmp_path):
    class Mock:
        calls=0
        identity={'backend':'mock','revision':'1'}
        def analyze_event(self,images,tracks,event):
            self.calls+=1
            return response()
    image=tmp_path/'frame.jpg';image.write_bytes(b'one')
    backend=Mock();tracks=[{'track_id':1}];metadata={'event_id':'evt_001'}
    for _ in range(2):
        analyze_cached(backend,[image],tracks,metadata,tmp_path/'cache',tmp_path/'raw.json')
    assert backend.calls==1
    image.write_bytes(b'two')
    analyze_cached(backend,[image],tracks,metadata,tmp_path/'cache',tmp_path/'raw.json')
    assert backend.calls==2
    backend.identity={'backend':'mock','revision':'2'}
    analyze_cached(backend,[image],tracks,metadata,tmp_path/'cache',tmp_path/'raw.json')
    assert backend.calls==3
