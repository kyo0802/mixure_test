from types import SimpleNamespace as S
from memory_graph.v21.contracts import IdentityConfig, PersistentEntity
from memory_graph.v21.resolver import resolve
import pytest


def track(tid,start,end,x=.2,label='chair'):
    def obs(t):
        return S(timestamp=t,frame_index=round(t*5),normalized_center=(x,.3),velocity=(0,0),
                 area_fraction=.1,nearest_tracks=[],bbox=(10,10,30,30),confidence=.9)
    return S(track_id=tid,first_seen=start,last_seen=end,detector_class=label,observations=[obs(start),obs(end)])


def run(tracks):
    q={t.track_id:{'usable_for_identity':True,'flags':['GOOD']} for t in tracks}
    f={t.track_id:[[1,0],[1,0]] for t in tracks}
    meta=S(sampled_frames=[S(timestamp=i/5,frame_index=i) for i in range(31)])
    return resolve(tracks,q,f,meta,IdentityConfig())


def test_short_gap_multi_cue_match_and_absence():
    entities,decisions,_=run([track(1,0,1),track(2,1.2,2)])
    assert len(entities)==1 and decisions[-1]['decision']=='MATCH'
    assert entities[0].visibility=='LOST' and entities[0].current_bbox is None
    assert entities[0].last_confirmed_seen==2


def test_co_visible_identical_chairs_cannot_merge():
    entities,_,_=run([track(1,0,2),track(2,0,2)])
    assert len(entities)==2


def test_same_class_far_or_late_is_insufficient():
    assert len(run([track(1,0,1),track(2,1.2,2,x=.8)])[0])==2
    assert len(run([track(1,0,1),track(2,4,5)])[0])==2


def test_ambiguous_alternatives_stay_separate():
    entities,decisions,_=run([track(1,0,1),track(2,0,1),track(3,1.2,2)])
    assert len(entities)==3 and decisions[-1]['decision']=='AMBIGUOUS'


def test_unobserved_current_box_rejected():
    with pytest.raises(ValueError):
        PersistentEntity(entity_id='entity_1',local_track_ids=[1],first_seen=0,last_confirmed_seen=1,
                         last_confirmed_bbox=(1,1,2,2),current_bbox=(1,1,2,2),visibility='UNOBSERVED',uncertainty=1)


def test_inference_does_not_import_evaluator_or_narrative():
    from pathlib import Path
    for path in Path('src/memory_graph/v21').glob('*.py'):
        text=path.read_text(encoding='utf-8')
        assert 'evaluation_v21' not in text
        assert 'smartphone_01' not in text and 'trash_bin_01' not in text
