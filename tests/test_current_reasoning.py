import pytest
from memory_graph.reasoning.contract import parse_json,prompt
from memory_graph.reasoning.validator import DirectReasoningValidator
from memory_graph.reasoning.pipeline import verify_reference

def test_exact_clean_baseline_is_preserved():
    assert verify_reference()['valid']

@pytest.mark.parametrize('raw',['{"event_type":"STATIC","event_type":"PICKED_UP"}','{"x":NaN}','[]','answer: {}'])
def test_strict_json_rejects_ambiguous_or_non_json_output(raw):
    with pytest.raises(ValueError):parse_json(raw)

def test_seven_field_prompt_only_adapts_context_roles():
    text=prompt({'markers':['A','B'],'actor_markers':['A'],'location_markers':['B'],'frames':[{'phase':'BEFORE'},{'phase':'DURING'},{'phase':'AFTER'}]})
    assert 'Interaction actor candidates: A. Location anchor candidates: B.' in text
    assert 'support_frames' not in text and 'IoU' not in text and 'interaction_anchor' in text

def test_consistency_validator_rejects_placement_without_release():
    answer={'event_type':'PLACED_OR_PUT_DOWN','interaction_anchor':'NONE','released':'NO','target_visible_after':'YES','final_relation':'NONE','final_relation_anchor':'NONE','confidence':'HIGH'}
    assert not DirectReasoningValidator().validate({'pack_id':'x','markers':[]},answer)['valid']
