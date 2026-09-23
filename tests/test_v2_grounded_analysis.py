import json
import pytest
from PIL import Image
from memory_graph.vlm.grounded_analysis import analyze_grounded, track_crops
from memory_graph.vlm.cache import analyze_cached


def inputs(tmp_path):
    images = []
    for phase in ['before','during','after']:
        path = tmp_path/f'{phase}.jpg'
        Image.new('RGB',(200,100),'red').save(path)
        images.append(path)
    tracks = [{'track_id':tid,'observations':[
        {'phase':phase,'visible':True,'timestamp':i,'bbox':[0,0,100,100]}
        for i,phase in enumerate(['before','during','after'])]} for tid in [1,2]]
    return images,tracks,{'event_id':'evt_001','original_image_size':{'width':400,'height':200}}


def test_crops_are_scaled_and_visibly_labeled_with_fixed_id(tmp_path):
    images,tracks,event = inputs(tmp_path)
    crops,refs = track_crops(images,tracks[0],event)
    assert len(crops) == 3
    assert all(r['bbox_in_keyframe'] == [0,0,51,51] and r['track_id'] == 1 for r in refs)
    assert all((tmp_path/r['image']).is_file() for r in refs)
    assert crops[0].height == 79


def test_invalid_component_is_explicit_and_cannot_change_identity(tmp_path):
    images,tracks,event = inputs(tmp_path)
    responses = iter([
        {'track_id':1,'semantic_class':'chair','confidence':.9},
        {'track_id':999,'semantic_class':'chair','confidence':.9},
        {'event_id':'evt_001','entities':[], 'relations':[
            {'subject_track_id':1,'object_track_id':2,'predicate':'OWNS','confidence':.9,'temporal_phase':'during'}]}])
    def generate(images,prompt,budget):
        assert len(images) == 3
        return json.dumps(next(responses))
    result,trace,errors = analyze_grounded(generate,images,tracks,event)
    assert [entity['track_id'] for entity in result['entities']] == [1]
    assert result['relations'] == []
    assert len(trace) == 3 and len(errors) == 2
    assert errors[0]['track_id'] == 2
    assert 'changed' in errors[0]['error'] and errors[1]['stage'] == 'relations'


def test_all_failed_components_cannot_be_reported_as_valid_empty_scene(tmp_path):
    images,tracks,event = inputs(tmp_path)
    class Backend:
        identity = {'backend':'synthetic-test-only'}
        last_trace = [{'stage':'relations','error':'invalid output','response':'bad'}]
        last_component_errors = [{'stage':'relations','error':'invalid output'}]
        def analyze_event(self,*args):
            return {'event_id':'evt_001','entities':[],'relations':[]}
    raw = tmp_path/'raw.json'
    with pytest.raises(ValueError,match='All VLM components failed'):
        analyze_cached(Backend(),images,tracks,event,tmp_path/'cache',raw)
    assert json.loads(raw.read_text())['generation_trace'][0]['response'] == 'bad'
