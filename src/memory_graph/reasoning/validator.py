"""Minimal output consistency, independent of perception and physical-memory truth."""
from .contract import KEYS, EVENT_TYPES, RELATIONS

class DirectReasoningValidator:
    def validate(self,event,answer):
        errors=[];schema=True
        result={'pack_id':event['pack_id'],'schema_valid':True,'valid':False,
                'status':'INVALID_MODEL_REASONING_OUTPUT','errors':errors}
        if not isinstance(answer,dict) or set(answer)!=KEYS:
            result['schema_valid']=False;errors.append('INVALID_JSON_OR_KEYS');return result
        allowed={'event_type':set(EVENT_TYPES),'interaction_anchor':set(event['markers'])|{'NONE','UNCERTAIN'},
            'released':{'YES','NO','UNCERTAIN'},'target_visible_after':{'YES','PARTIAL','NO','UNCERTAIN'},
            'final_relation':set(RELATIONS),'final_relation_anchor':set(event['markers'])|{'NONE','UNCERTAIN'},
            'confidence':{'HIGH','MEDIUM','LOW'}}
        for key in KEYS:
            if not isinstance(answer[key],str) or answer[key] not in allowed[key]:
                schema=False;errors.append('UNKNOWN_ANCHOR' if key in {'interaction_anchor','final_relation_anchor'} else 'INVALID_ENUM:'+key)
        result['schema_valid']=schema
        if not schema:return result
        relation=answer['final_relation'];anchor=answer['final_relation_anchor'];kind=answer['event_type']
        if relation=='NONE' and anchor!='NONE':errors.append('IMPOSSIBLE_RELATION_ANCHOR')
        if relation=='UNCERTAIN' and anchor not in {'NONE','UNCERTAIN'}:errors.append('IMPOSSIBLE_RELATION_ANCHOR')
        if relation not in {'NONE','UNCERTAIN'} and anchor not in event['markers']:errors.append('IMPOSSIBLE_RELATION_ANCHOR')
        if kind=='PLACED_OR_PUT_DOWN' and answer['released']=='NO':errors.append('INTERNAL_CONTRADICTION:PLACEMENT_NOT_RELEASED')
        if kind=='STATIC' and answer['released']=='YES':errors.append('INTERNAL_CONTRADICTION:STATIC_RELEASE')
        if relation=='HELD_BY':
            if kind not in {'CARRIED_OR_HELD','PICKED_UP'} or answer['released']=='YES':
                errors.append('INTERNAL_CONTRADICTION:HOLDING_STATE')
            if answer['interaction_anchor'] not in {anchor,'UNCERTAIN'}:
                errors.append('INTERNAL_CONTRADICTION:HOLDING_ACTOR')
        result['valid']=not errors
        if result['valid']:result['status']='VALID_MODEL_REASONING_OUTPUT'
        return result
