"""Non-gating, dependency-aware reimplementation of current contract predicates.

Production Validator exposes no separate semantic predicates. Original strict
result is imported unchanged by the caller; this module never overrides it.
"""
import jsonschema

def collect(value,aliases,schema):
    rows=[]
    def add(rule,path,status,evidence,error=None):
        rows.append({'rule_id':rule,'json_path':path,'status':status,'evidence':evidence,'strict_error':error})
    errors=sorted(jsonschema.Draft202012Validator(schema).iter_errors(value),key=lambda e:list(e.absolute_path))
    for e in errors:
        path='/'+ '/'.join(map(str,e.absolute_path));rule='SCHEMA_'+e.validator.upper()
        if path.endswith('timing_uncertainty') and e.validator=='minLength':rule='EMPTY_TIMING_UNCERTAINTY'
        if path=='/window_cited_frame_aliases' and e.validator=='minItems':rule='EMPTY_WINDOW_CITATIONS'
        add(rule,path,'VIOLATED',{'constraint':e.validator,'expected':e.validator_value,'actual':e.instance},path+':'+e.message)
    if not errors:add('SCHEMA','/','SATISFIED','All schema constraints hold')
    if not isinstance(value,dict):
        for rule in ['CITATION_MEMBERSHIP','STATE_SUPPORT','OUTCOME_EVENT_CONSISTENCY','TIMING','TARGET_ASSOCIATION']:
            add(rule,'/','NOT_EVALUABLE','Top level is not object')
        return rows
    alias_ok=isinstance(aliases,list) and all(isinstance(a,str) for a in aliases)
    supplied=set(aliases) if alias_ok else None
    order={a:i for i,a in enumerate(aliases)} if alias_ok else None
    def citation(a,path,error):
        if not alias_ok or not isinstance(a,str):add('CITATION_MEMBERSHIP',path,'NOT_EVALUABLE','Missing alias inventory or wrong alias type');return
        add('CITATION_MEMBERSHIP',path,'SATISFIED' if a in supplied else 'VIOLATED',a,None if a in supplied else error)
    window=value.get('window_cited_frame_aliases')
    if isinstance(window,list) and all(isinstance(a,str) for a in window):
        for i,a in enumerate(window):citation(a,f'/window_cited_frame_aliases/{i}','OUT_OF_PAYLOAD_WINDOW_CITATION:'+a)
        if not window:add('CITATION_MEMBERSHIP','/window_cited_frame_aliases','NOT_APPLICABLE','No aliases to test; empty-list schema failure is separate')
    else:add('CITATION_MEMBERSHIP','/window_cited_frame_aliases','NOT_EVALUABLE','Missing/wrong-type list')
    events=value.get('events');event_ok=isinstance(events,list) and all(isinstance(e,dict) for e in events)
    if event_ok and all(isinstance(e.get('event_id'),str) for e in events):
        ids=[e['event_id'] for e in events];ok=len(ids)==len(set(ids))
        add('EVENT_ID_UNIQUE','/events','SATISFIED' if ok else 'VIOLATED',ids,None if ok else 'DUPLICATE_EVENT_ID')
    elif not event_ok:add('EVENT_ID_UNIQUE','/events','NOT_EVALUABLE','Missing/wrong event array')
    def state(v,path,unknown_error,known_error,cite_error):
        if not isinstance(v,dict) or v.get('state') not in schema['$defs']['state']['properties']['state']['enum'] or 'supporting_frame_alias' not in v or (v['supporting_frame_alias'] is not None and not isinstance(v['supporting_frame_alias'],str)):
            add('STATE_SUPPORT',path,'NOT_EVALUABLE','State object/enum/support type unavailable');return
        a=v['supporting_frame_alias'];known=v['state']!='STATE_UNKNOWN';ok=(a is not None) if known else (a is None)
        add('KNOWN_STATE_SUPPORT' if known else 'UNKNOWN_STATE_SUPPORT',path,'SATISFIED' if ok else 'VIOLATED',v,
            None if ok else known_error if known else unknown_error)
        if a is not None:citation(a,path+'/supporting_frame_alias',cite_error+(':'+a if cite_error.startswith('OUT_OF_PAYLOAD_STATE:') else ''))
        else:add('CITATION_MEMBERSHIP',path+'/supporting_frame_alias','NOT_APPLICABLE','Null support has no cited alias')
    if event_ok:
        if not events:
            for rule in ['EVENT_CITATIONS','EVENT_STATE_SUPPORT','EVENT_TIMING','TARGET_ASSOCIATION','TIMING_UNCERTAINTY']:
                add(rule,'/events','NOT_APPLICABLE','No event objects')
        for i,e in enumerate(events):
            prefix=f'/events/{i}';eid=e.get('event_id')
            eid_ok=isinstance(eid,str)
            citations=e.get('cited_frame_aliases')
            if isinstance(citations,list) and all(isinstance(a,str) for a in citations) and eid_ok:
                for j,a in enumerate(citations):citation(a,prefix+f'/cited_frame_aliases/{j}',f'OUT_OF_PAYLOAD_CITATION:{eid}:{a}')
            else:add('EVENT_CITATIONS',prefix+'/cited_frame_aliases','NOT_EVALUABLE','Missing/wrong list or ID')
            t=e.get('timing')
            if isinstance(t,dict) and isinstance(t.get('status'),str) and t.get('status') in {'EXACT_SUPPLIED_FRAME','BOUNDED_SUPPLIED_FRAMES','TIMING_UNKNOWN'} and eid_ok:
                keys={'EXACT_SUPPLIED_FRAME':['frame_alias'],'BOUNDED_SUPPLIED_FRAMES':['start_frame_alias','end_frame_alias'],'TIMING_UNKNOWN':[]}[t['status']]
                if all(isinstance(t.get(k),str) for k in keys):
                    if t['status']=='BOUNDED_SUPPLIED_FRAMES':
                        a,b=t['start_frame_alias'],t['end_frame_alias']
                        if alias_ok and a in order and b in order:
                            ok=order[a]<=order[b];add('TIME_INTERVAL_ORDER',prefix+'/timing','SATISFIED' if ok else 'VIOLATED',t,None if ok else f'REVERSED_TIME_INTERVAL:{eid}')
                        else:add('TIME_INTERVAL_ORDER',prefix+'/timing','NOT_EVALUABLE','Both aliases need ordered inventory')
                    for k in keys:citation(t[k],prefix+'/timing/'+k,f'OUT_OF_PAYLOAD_TIMING:{eid}:{t[k]}')
                    if not keys:add('EVENT_TIMING',prefix+'/timing','NOT_APPLICABLE','TIMING_UNKNOWN contains no time aliases')
                else:add('EVENT_TIMING',prefix+'/timing','NOT_EVALUABLE','Timing aliases missing/wrong type')
            else:add('EVENT_TIMING',prefix+'/timing','NOT_EVALUABLE','Missing/wrong timing/ID')
            for key in ['before_state','after_state']:
                if eid_ok:state(e.get(key),prefix+'/'+key,f'UNKNOWN_STATE_HAS_SUPPORT:{eid}:{key}',f'KNOWN_STATE_MISSING_SUPPORT:{eid}:{key}',f'OUT_OF_PAYLOAD_STATE:{eid}')
                else:add('STATE_SUPPORT',prefix+'/'+key,'NOT_EVALUABLE','Missing event ID')
            u=e.get('timing_uncertainty')
            if isinstance(u,str) and u:add('TIMING_UNCERTAINTY',prefix+'/timing_uncertainty','SATISFIED','Nonempty string; correctness not proven')
            elif u=='':pass  # Atomic schema violation already recorded, do not count twice.
            else:add('TIMING_UNCERTAINTY',prefix+'/timing_uncertainty','NOT_EVALUABLE','Missing/null/wrong type; schema result separate')
            a=e.get('target_association_uncertainty')
            if isinstance(a,str) and a in {'NONE','POSSIBLE','HIGH'}:add('TARGET_ASSOCIATION_ENUM',prefix+'/target_association_uncertainty','SATISFIED',a)
            else:add('TARGET_ASSOCIATION_ENUM',prefix+'/target_association_uncertainty','NOT_EVALUABLE','Wrong type/enum; schema result separate')
            add('TARGET_ASSOCIATION_PHYSICAL_POLICY',prefix+'/target_association_uncertainty','NOT_APPLICABLE','No current validator rule bans HIGH with CONFIRMED_EVENTS; pending human semantic review')
    else:
        for rule in ['EVENT_CITATIONS','EVENT_STATE_SUPPORT','EVENT_TIMING','TARGET_ASSOCIATION']:
            add(rule,'/events','NOT_EVALUABLE','Missing/wrong-type event array or object')
    state(value.get('last_directly_supported_state'),'/last_directly_supported_state','UNKNOWN_LAST_STATE_HAS_SUPPORT','KNOWN_LAST_STATE_MISSING_SUPPORT','OUT_OF_PAYLOAD_LAST_STATE')
    outcome=value.get('window_outcome')
    if event_ok and outcome in schema['properties']['window_outcome']['enum']:
        ok=(outcome=='CONFIRMED_EVENTS')==bool(events)
        error='CONFIRMED_EVENTS_REQUIRES_EVENT' if outcome=='CONFIRMED_EVENTS' else 'NON_CONFIRMED_OUTCOME_REQUIRES_EMPTY_EVENTS'
        add('OUTCOME_EVENT_CONSISTENCY','/events','SATISFIED' if ok else 'VIOLATED',{'outcome':outcome,'events':len(events)},None if ok else error)
    else:add('OUTCOME_EVENT_CONSISTENCY','/events','NOT_EVALUABLE','Missing/wrong outcome/event array')
    return rows
