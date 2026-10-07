"""Deterministic target-transition windows. Geometry triggers evidence, never relations."""
from dataclasses import dataclass, asdict
from copy import deepcopy
from math import hypot
from statistics import median

@dataclass(frozen=True)
class WindowConfig:
    stable_pre_seconds: float = .7
    stable_post_seconds: float = 1.0
    min_seconds: float = 2.0
    preferred_seconds: float = 3.5
    max_seconds: float = 6.0
    max_observation_gap_seconds: float = .4
    motion_speed_image_diagonals_per_second: float = .04
    velocity_interval_seconds: float = .2
    smoothing_seconds: float = .4
    state_dwell_seconds: float = .3
    dense_frame_fps: float = 5.0
    physical_budget_per_video: int = 4
    lifecycle_budget_per_video: int = 6
    max_actor_candidates: int = 2
    max_location_candidates: int = 3

    def to_dict(self): return asdict(self)

ACTOR_LABELS = {'person', 'hand', 'arm', 'carrier'}

def center(box): return ((box[0]+box[2])/2, (box[1]+box[3])/2)

def context_key(a): return a.get('anchor_key') or a['entity_id']

def role(a):
    return 'INTERACTION_ACTOR_CANDIDATE' if a.get('raw_label',a.get('label','')).lower() in ACTOR_LABELS else 'LOCATION_ANCHOR_CANDIDATE'

def target_timeline(rows, config=WindowConfig()):
    rows = deepcopy(sorted(rows, key=lambda r:r['time']))
    speeds=[]; previous=None; history=[]
    for i,r in enumerate(rows):
        authorized=bool(r.get('identity_authorized') and r.get('target_bbox'))
        r['identity_authorized']=authorized
        if not authorized:
            r['visibility']='UNTRUSTED' if r.get('candidate_present') else 'UNOBSERVED'
            r['motion_state']='UNKNOWN';r['motion_speed']=None;r['actor_associations']=[]
            previous=None;history=[];speeds=[];continue
        box=r['target_bbox'];w,h=r['image_size'];diag=hypot(w,h)
        r['visibility']='PARTIAL' if min(box[:2])<=1 or box[2]>=w-1 or box[3]>=h-1 else 'VISIBLE'
        r['actor_associations']=[context_key(a) for a in r['anchors'] if role(a)=='INTERACTION_ACTOR_CANDIDATE' and
            a['bbox'][0]<=center(box)[0]<=a['bbox'][2] and a['bbox'][1]<=center(box)[1]<=a['bbox'][3]]
        history=[p for p in history if r['time']-p['time']<=config.max_observation_gap_seconds and p['chain_id']==r['chain_id']]
        prior=min(history,key=lambda p:abs(r['time']-p['time']-config.velocity_interval_seconds),default=None)
        speed=None;camera=None
        if prior:
            dt=r['time']-prior['time'];dx=center(box)[0]-center(prior['target_bbox'])[0];dy=center(box)[1]-center(prior['target_bbox'])[1]
            old={context_key(a):a for a in prior['anchors'] if role(a)=='LOCATION_ANCHOR_CANDIDATE'}
            offsets=[(center(a['bbox'])[0]-center(old[context_key(a)]['bbox'])[0],center(a['bbox'])[1]-center(old[context_key(a)]['bbox'])[1])
                     for a in r['anchors'] if role(a)=='LOCATION_ANCHOR_CANDIDATE' and context_key(a) in old]
            if len(offsets)>=2:
                camera=(median(v[0] for v in offsets),median(v[1] for v in offsets));dx-=camera[0];dy-=camera[1]
            speed=hypot(dx,dy)/diag/dt
        if speed is not None:speeds.append((r['time'],speed))
        speeds=[s for s in speeds if r['time']-s[0]<=config.smoothing_seconds]
        value=median(s[1] for s in speeds) if speeds else None
        r['motion_speed']=value;r['camera_translation_estimate']=camera
        r['motion_state']='UNKNOWN' if value is None else 'MOVING' if value>config.motion_speed_image_diagonals_per_second else 'STATIONARY'
        r['carried_like']=bool(r['actor_associations'] and r['motion_state']=='MOVING')
        history.append(r);previous=r
    # A fixed dwell suppresses short detector jitter; no semantic action is assigned.
    current=None;pending=None;pending_start=None
    for r in rows:
        if r['motion_state']=='UNKNOWN':current=None;pending=None;continue
        observed=r['motion_state']
        if current is None:current=observed
        if observed!=current:
            if pending!=observed:pending=observed;pending_start=r['time']
            if r['time']-pending_start>=config.state_dwell_seconds:current=observed;pending=None
        else:pending=None
        r['motion_state']=current
        r['carried_like']=bool(r.get('actor_associations') and current=='MOVING')
    return rows

def stable_key(r):
    if not r['identity_authorized']:return (r['visibility'],'UNKNOWN',None)
    return ('OBSERVED',r['motion_state'],r['chain_id'])

def runs(rows,cfg):
    result=[]
    for i,r in enumerate(rows):
        key=stable_key(r)
        if not result or result[-1]['key']!=key or r['time']-rows[i-1]['time']>cfg.max_observation_gap_seconds:
            result.append({'key':key,'start':i,'end':i})
        else:result[-1]['end']=i
    return result

def transitions(rows,cfg):
    result=[]
    for i in range(1,len(rows)):
        a,b=rows[i-1],rows[i]
        if b['time']-a['time']>cfg.max_observation_gap_seconds:
            result.append({'index':i,'trigger':'OBSERVATION_COVERAGE_GAP','category':'IDENTITY_LIFECYCLE_EVENT'});continue
        if a['identity_authorized']!=b['identity_authorized']:
            trigger='OBSERVATION_GAP_START' if a['identity_authorized'] else 'OBSERVATION_RECOVERY'
            result.append({'index':i,'trigger':trigger,'category':'IDENTITY_LIFECYCLE_EVENT'})
            if a['identity_authorized'] and a['motion_state']=='MOVING' and b['visibility']=='UNOBSERVED':
                result.append({'index':i,'trigger':'MOVEMENT_TO_UNOBSERVED','category':'PHYSICAL_INTERACTION_EVENT'})
        if a['identity_authorized'] and b['identity_authorized']:
            if a['chain_id']!=b['chain_id']:
                result.append({'index':i,'trigger':'AUTHORIZED_CHAIN_CHANGE','category':'IDENTITY_LIFECYCLE_EVENT'});continue
            if a['visibility']!=b['visibility']:
                result.append({'index':i,'trigger':'VISIBILITY_CHANGE','category':'IDENTITY_LIFECYCLE_EVENT'})
            if (a['motion_state'],b['motion_state'])==('STATIONARY','MOVING'):
                result.append({'index':i,'trigger':'STATIONARY_TO_MOVING','category':'PHYSICAL_INTERACTION_EVENT'})
            elif (a['motion_state'],b['motion_state'])==('MOVING','STATIONARY'):
                result.append({'index':i,'trigger':'CARRIED_LIKE_TO_STABLE' if a.get('carried_like') else 'MOVING_TO_STATIONARY','category':'PHYSICAL_INTERACTION_EVENT'})
    return result

def adaptive_window(rows,trigger,cfg=WindowConfig()):
    i=trigger['index'];t=rows[i]['time'];segments=runs(rows,cfg)
    pre_candidates=[s for s in segments if s['end']<i and t-rows[s['start']]['time']<=cfg.max_seconds and
        rows[s['end']]['time']-rows[s['start']]['time']>=cfg.stable_pre_seconds and
        s['key'][0]=='OBSERVED' and s['key'][1]!='UNKNOWN']
    pre=pre_candidates[-1] if pre_candidates else None
    post_candidates=[s for s in segments if s['start']>=i and rows[s['start']]['time']-t<=cfg.max_seconds and
        rows[s['end']]['time']-rows[s['start']]['time']>=cfg.stable_post_seconds and
        s['key'][0] in {'OBSERVED','UNOBSERVED'} and (s['key'][0]=='UNOBSERVED' or s['key'][1]!='UNKNOWN')]
    # The segment containing the transition's new state starts on this exact transition index.
    post=post_candidates[0] if post_candidates else None
    lo=max(0,i-1);hi=i
    if pre:
        lo=pre['end']
        while lo>pre['start'] and rows[pre['end']]['time']-rows[lo]['time']<cfg.stable_pre_seconds:lo-=1
    if post:
        hi=post['start']
        while hi<post['end'] and rows[hi]['time']-rows[post['start']]['time']<cfg.stable_post_seconds:hi+=1
    # Extend within stable PRE/POST states, never borrowing evidence outside max span.
    if pre and post:
        while rows[hi]['time']-rows[lo]['time']<cfg.preferred_seconds:
            if hi<post['end']:hi+=1
            elif lo>pre['start']:lo-=1
            else:break
            if rows[hi]['time']-rows[lo]['time']>cfg.max_seconds:break
    duration=rows[hi]['time']-rows[lo]['time'];local=rows[lo:hi+1]
    auth_chains={r['chain_id'] for r in local if r['identity_authorized']}
    gap=any(b['time']-a['time']>cfg.max_observation_gap_seconds for a,b in zip(local,local[1:]))
    scene_break=any(not r.get('scene_ok',True) for r in local)
    same_chain=len(auth_chains)==1
    reasons=[]
    if not pre:reasons.append('NO_STABLE_PRE_STATE')
    if not post:reasons.append('NO_STABLE_POST_STATE')
    if gap:reasons.append('TRANSITION_NOT_CAPTURED')
    if not same_chain or scene_break:reasons.append('UPSTREAM_IDENTITY_LIMITATION')
    if duration<cfg.min_seconds:reasons.append('WINDOW_END_TOO_EARLY')
    if duration>cfg.max_seconds:reasons.append('WINDOW_TOO_LONG')
    if not any(r['identity_authorized'] for r in local):reasons.append('TARGET_NOT_VISIBLE_ENOUGH')
    complete=bool(pre and post and not reasons)
    return {'category':trigger['category'],'trigger':trigger['trigger'],'transition_frame':rows[i]['frame'],
        'transition_time':t,'start_frame':rows[lo]['frame'],'end_frame':rows[hi]['frame'],
        'start_time':rows[lo]['time'],'end_time':rows[hi]['time'],'duration_seconds':duration,
        'HAS_PRE_STATE':bool(pre),'HAS_TRANSITION':not gap and lo<i<=hi,'HAS_POST_STATE':bool(post),
        'pre_state':list(pre['key']) if pre else None,'post_state':list(post['key']) if post else None,
        'completeness':'COMPLETE_EVENT_WINDOW' if complete else 'INCOMPLETE_EVENT_WINDOW',
        'failure_categories':reasons,'identity_authorized_fraction':sum(r['identity_authorized'] for r in local)/len(local),
        'identity_write_authorized':False,'row_indices':[lo,hi], 'semantic_action_assigned':False}

def select_events(rows,cfg=WindowConfig()):
    candidates=[adaptive_window(rows,t,cfg) for t in transitions(rows,cfg)]
    queues={};selected=[]
    for category,budget in [('PHYSICAL_INTERACTION_EVENT',cfg.physical_budget_per_video),('IDENTITY_LIFECYCLE_EVENT',cfg.lifecycle_budget_per_video)]:
        queue=[e for e in candidates if e['category']==category]
        queue.sort(key=lambda e:(e['completeness']!='COMPLETE_EVENT_WINDOW',not e['trigger'].endswith(('STABLE','STATIONARY')), -e['identity_authorized_fraction'],e['transition_time']))
        chosen=[]
        for e in queue:
            # Do not spend the physical budget twice on the same bounded transition.
            if category=='PHYSICAL_INTERACTION_EVENT' and any(abs(e['transition_time']-c['transition_time'])<cfg.stable_post_seconds and
                max(e['start_time'],c['start_time'])<=min(e['end_time'],c['end_time']) for c in chosen):continue
            if len(chosen)<budget:chosen.append(e)
        queues[category]={'candidates':len(queue),'budget':budget,'selected':len(chosen)};selected.extend(chosen)
    selected.sort(key=lambda e:(e['transition_time'],e['category']))
    return candidates,selected,queues

def dense_frames(rows,event,cfg=WindowConfig()):
    lo,hi=event['row_indices'];available=rows[lo:hi+1]
    wanted=[event['start_time']+k/cfg.dense_frame_fps for k in range(int(event['duration_seconds']*cfg.dense_frame_fps)+1)]
    ids={min(range(lo,hi+1),key=lambda i:abs(rows[i]['time']-t)) for t in wanted}
    ids|={lo,hi,min(range(lo,hi+1),key=lambda i:abs(rows[i]['time']-event['transition_time']))}
    return [rows[i] for i in sorted(ids)]

def select_context(rows,event,cfg=WindowConfig()):
    lo,hi=event['row_indices'];groups={}
    for r in rows[lo:hi+1]:
        for a in r['anchors']:
            key=context_key(a);entry=groups.setdefault(key,{'key':key,'raw_label':a.get('raw_label',a.get('label')),'role':role(a),'observations':[], 'proximity':[]})
            entry['observations'].append({'frame':r['frame'],'bbox':a['bbox']})
            if r['identity_authorized']:
                x,y=center(r['target_bbox']);ax,ay=center(a['bbox'])
                entry['proximity'].append(hypot(x-ax,y-ay)/hypot(*r['image_size']))
    context=[]
    for kind,budget in [('INTERACTION_ACTOR_CANDIDATE',cfg.max_actor_candidates),('LOCATION_ANCHOR_CANDIDATE',cfg.max_location_candidates)]:
        pool=[e for e in groups.values() if e['role']==kind and len(e['observations'])>=2]
        pool.sort(key=lambda e:(median(e['proximity']) if e['proximity'] else float('inf'),-len(e['observations']),e['key']))
        for e in pool[:budget]:
            e=deepcopy(e);e.pop('proximity');e['marker']=chr(65+len(context));context.append(e)
    return context
