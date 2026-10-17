"""Common CPU-only experiment contract. No model, GT, or Graph imports."""
import json,re,math
STATES=['ON_SURFACE','HELD_BY_PERSON','OTHER','UNKNOWN']
PROMPT={'system':'You analyze chronological visual observations using only visible evidence. Return one JSON object, without markdown or extra text.', 'task':'''Analyze the supplied chronological source frames. Identify relevant movable objects using generic descriptions. For each object, report directly observable physical states and its relation to a supporting surface or person. ON_SURFACE means visibly supported by a surface; HELD_BY_PERSON means visibly held by a person. Use OTHER for a visible state outside these categories and UNKNOWN when visibility or support is insufficient. Do not infer continued holding, existence, nonexistence, or manipulation from disappearance or occlusion. Do not equate camera motion with object motion. Similar appearance alone does not establish the same physical instance.
First record observations, then propose only visibly supported PICKUP (surface to held) or PLACEMENT (held to surface) transitions. Events are optional. Cite only the supplied aliases; do not invent intermediate aliases or exact event times. Each state entry refers to exactly one supplied frame. Use each alias at most once per object and keep states chronological. Event object descriptions must exactly match an observation; before/after references must cite its corresponding observed states. Omit unsupported transitions and use UNCERTAIN if evidence cannot establish a conclusion. NO_CONFIRMED_EVENT means no transition was established from these samples, not an exhaustive negative claim. Keep the response compact. Always include status, observations, and events (an empty list if none).'''}
SCHEMA={'type':'object','additionalProperties':False,'required':['status','observations','events'],'properties':{
 'status':{'enum':['EVENTS','NO_CONFIRMED_EVENT','UNCERTAIN']},
 'observations':{'type':'array','items':{'type':'object','additionalProperties':False,'required':['object','states'],'properties':{'object':{'type':'string','minLength':1},'states':{'type':'array','minItems':1,'maxItems':8,'items':{'type':'object','additionalProperties':False,'required':['frame','state'],'properties':{'frame':{'type':'string'},'state':{'enum':STATES}}}}}}},
 'events':{'type':'array','items':{'type':'object','additionalProperties':False,'required':['type','object','before_frames','after_frames'],'properties':{'type':{'enum':['PICKUP','PLACEMENT']},'object':{'type':'string','minLength':1},'before_frames':{'type':'array','minItems':1,'uniqueItems':True,'items':{'type':'string'}},'after_frames':{'type':'array','minItems':1,'uniqueItems':True,'items':{'type':'string'}}}}}}}
def strict_load(text):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('DUPLICATE_KEY:'+k)
            d[k]=v
        return d
    return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda s:(_ for _ in ()).throw(ValueError('NONFINITE:'+s)))
def check(text,aliases):
    from jsonschema import Draft202012Validator
    r={'json_valid':False,'schema_valid':None,'citation_valid':None,'semantic_valid':None,'full_valid':False,'parsed':None,'errors':[]}
    try:d=strict_load(text);r.update(json_valid=True,parsed=d)
    except (ValueError,TypeError) as e:r['errors'].append('JSON:'+str(e));return r
    errors=[str(list(e.path))+':'+e.message for e in Draft202012Validator(SCHEMA).iter_errors(d)]
    r['schema_valid']=not errors;r['errors']+=['SCHEMA:'+x for x in errors]
    if errors:return r
    order={a:i for i,a in enumerate(aliases)};cite=[];sem=[];objects={}
    for o in d['observations']:
        if o['object'] in objects:sem.append('DUPLICATE_OBJECT_DESCRIPTION')
        objects[o['object']]={s['frame']:s['state'] for s in o['states']}
        fs=[s['frame'] for s in o['states']]
        if len(set(fs))!=len(fs):sem.append('DUPLICATE_OBJECT_FRAME_STATE')
        cite += ['UNSUPPLIED:'+a for a in fs if a not in order]
        if all(a in order for a in fs) and list(map(order.get,fs))!=sorted(map(order.get,fs)):sem.append('NONCHRONOLOGICAL_STATES')
    if (d['status']=='EVENTS')!=bool(d['events']):sem.append('STATUS_EVENTS_INCONSISTENT')
    for e in d['events']:
        bf,af=e['before_frames'],e['after_frames'];cite+=['UNSUPPLIED:'+a for a in bf+af if a not in order]
        if all(a in order for a in bf+af) and max(map(order.get,bf))>=min(map(order.get,af)):sem.append('EVENT_TEMPORAL_ORDER')
        states=objects.get(e['object']);expected=('ON_SURFACE','HELD_BY_PERSON') if e['type']=='PICKUP' else ('HELD_BY_PERSON','ON_SURFACE')
        if states is None:sem.append('EVENT_OBJECT_NOT_OBSERVED')
        elif any(states.get(a)!=expected[0] for a in bf) or any(states.get(a)!=expected[1] for a in af):sem.append('EVENT_STATE_CITATIONS_INCONSISTENT')
    r.update(citation_valid=not cite,semantic_valid=not sem,full_valid=not cite and not sem);r['errors']+=cite+sem;return r
def validate_raw(raw,aliases):
    strict=check(raw,aliases);match=re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*',raw,re.S);body=None
    if match and '```' not in match.group(1):body={'policy':'EXACT_SINGLE_OUTER_FENCE_ONLY','validation':check(match.group(1),aliases),'authoritative':False}
    return {'raw':strict,'normalized_body':body,'physical_evidence_validity':'UNREVIEWED_NOT_INFERRED_FROM_CONTRACT','invalid_is_not_no_event':True}
def interval_distance(a,b):return max(b[0]-a[1],a[0]-b[1],0.)
def choose_uniform8(indices,pts):
    """Constrained nearest native-PTS quantiles, earlier tie; no repeated frames."""
    import bisect
    if len(indices)<=8:return list(indices)
    chosen=[];lo=indices[0];hi=indices[-1]
    for k in range(8):
        target=pts[lo]+(pts[hi]-pts[lo])*k/7
        lower=chosen[-1]+1 if chosen else lo;upper=hi-(7-k)
        pos=min(max(bisect.bisect_left(pts,target,lower,upper+1),lower),upper)
        opts={pos,max(lower,pos-1)};chosen.append(min(opts,key=lambda i:(abs(pts[i]-target),i)))
    return chosen
def merge_intervals(intervals):
    result=[]
    for a,b in sorted(intervals):
        if result and a<=result[-1][1]+1e-9:result[-1][1]=max(b,result[-1][1])
        else:result.append([a,b])
    return result
