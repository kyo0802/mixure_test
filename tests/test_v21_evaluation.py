from memory_graph.evaluation_v21.evaluator import score_samples
from memory_graph.v21.graphs import convert_relations
from memory_graph.evaluation_v21.evaluator import distinct_tests,NOT_MEASURABLE
from memory_graph.v21.contracts import ContextResult
import pytest


def sample(visibility='VISIBLE'):
    return {'frame_index':1,'gt_object_id':'test_object','bbox':[0,0,10,10],
            'visibility':visibility,'manually_reviewed':True}


def test_missing_detection_is_not_association_failure():
    *_,errors=score_samples([sample()],[],[],{}, {})
    assert [e['type'] for e in errors]==['DETECTION_FAILURE']


def test_occluded_frame_excluded_from_recall():
    _,metrics,*_=score_samples([sample('OCCLUDED')],[],[],{}, {})
    assert not metrics


def test_no_later_observation_is_not_reassociation_requirement():
    det={'frame_index':1,'bbox':[0,0,10,10],'class_name':'object'}
    track={'track_id':1,'observations':[det]}
    *_,errors=score_samples([sample()],[det],[track],{1:'entity_1'}, {})
    assert not errors


def test_geometry_near_never_promotes_to_physical_memory():
    relation={'subject_track_id':1,'object_track_id':2,'predicate':'NEAR','confidence':.99,
              'start_time':0,'end_time':1,'observed_times':[0,1],'event_ids':['e1'],
              'evidence':{'vlm':True,'geometry':'supports'}}
    obs,candidates,memory=convert_relations([{'relations':[relation]}],{1:'e1',2:'e2'},[],2)
    assert obs[0]['predicate']=='IMAGE_NEAR' and obs[0]['physical_confidence'] is None
    assert not candidates and not memory


def test_distinct_phone_false_merge_is_penalized():
    tests,errors=distinct_tests({'phone':{'e1'},'desk1':{'e1'},'desk2':{'e2'}},
                              [('phone','desk1'),('desk1','desk2'),('phone','unmapped')])
    assert len(errors)==1 and errors[0]['type']=='FALSE_MERGE'
    assert tests[1]['result']=='PASS' and tests[2]['result']==NOT_MEASURABLE


def test_context_none_and_uncertain_are_valid_but_false_support_is_not():
    assert ContextResult(event_id='e',decision='NONE',explanation='No evidence').claims==[]
    assert ContextResult(event_id='e',decision='UNCERTAIN',explanation='Occlusion').claims==[]
    with pytest.raises(ValueError):ContextResult(event_id='e',decision='SUPPORTED',explanation='Nothing')


def test_physical_promotion_requires_repeated_supported_evidence():
    relation={'subject_track_id':1,'object_track_id':2,'predicate':'HOLDING','confidence':.9,
              'start_time':0,'end_time':1,'observed_times':[0,1],'event_ids':['e1'],
              'evidence':{'vlm':True,'geometry':'not_testable','details':{'phase_checks':[{'verdict':'not_testable'}]}}}
    context={'frames':[{'phase':p,'timestamp':t,'visible_entity_ids':['actor','object']}
                       for p,t in [('before',0),('during',1)]]}
    def result(event):
        return ContextResult(event_id=event,decision='SUPPORTED',explanation='Synthetic test only',claims=[
            {'subject_entity_id':'actor','object_entity_id':'object','predicate':'HOLDING','confidence':.9,
             'supporting_phases':['before','during'],'explanation':'Synthetic test evidence'}])
    _,_,single=convert_relations([{'relations':[relation]}],{1:'actor',2:'object'},[(result('e1'),context)],6)
    assert not single
    _,_,multiple=convert_relations([{'relations':[relation]}],{1:'actor',2:'object'},
                                  [(result('e1'),context),(result('e2'),context)],6)
    assert not multiple, 'Renaming the same observed frames is not independent evidence'
    later={'frames':[{'phase':p,'timestamp':t,'visible_entity_ids':['actor','object']}
                     for p,t in [('before',2),('during',3)]]}
    _,_,multiple=convert_relations([{'relations':[relation]}],{1:'actor',2:'object'},
                                  [(result('e1'),context),(result('e2'),later)],8)
    assert len(multiple)==2 and all(r['memory_status']=='STALE' for r in multiple)
