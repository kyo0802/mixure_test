"""Observation-only authorization and deterministic bounded pair evidence."""
from copy import deepcopy
from math import hypot

def authorize_observation(*, frame, sam, prior, fps, chain_active, conflicting,
                          scene_ok, mask_available):
    checks = {'trusted_origin':bool(prior and prior.get('trusted')),
        'causal_short_continuity':bool(prior and 0 <= frame-prior['frame'] <= round(.4*fps)),
        'continuity_unbroken':bool(chain_active), 'no_identity_conflict':not conflicting,
        'no_drift':bool(sam and not sam.get('diagnostics',{}).get('possible_mask_drift',False)),
        'mask_quality':bool(sam and sam.get('area',0)>0 and mask_available), 'scene_continuity':bool(scene_ok)}
    okay=all(checks.values())
    return {'status':'OBSERVATION_AUTHORIZED' if okay else 'UNAVAILABLE', 'geometry_usable':okay,
            'identity_write_authorized':False,'checks':checks,
            'failed_checks':[k for k,v in checks.items() if not v],
            'source_trusted_frame':prior['frame'] if prior else None}

def bounded_window(event,fps,last_frame,max_expand_seconds=1.5):
    budget=round(fps*max_expand_seconds)
    return max(0,event['start_frame']-budget),min(last_frame,event['end_frame']+budget)

def _iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return inter/max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)

def _distance(a,b):
    return hypot((a[0]+a[2]-b[0]-b[2])/2,(a[1]+a[3]-b[1]-b[3])/2)/max(1,hypot(b[2]-b[0],b[3]-b[1]))

def transition_score(first,last,anchor_key):
    a=next(x for x in first['anchors'] if x['anchor_key']==anchor_key)
    b=next(x for x in last['anchors'] if x['anchor_key']==anchor_key)
    ta,tb=first['target_bbox'],last['target_bbox']
    return (abs(_distance(ta,a['bbox'])-_distance(tb,b['bbox']))+
            abs(_iou(ta,a['bbox'])-_iou(tb,b['bbox']))+
            abs(float(first.get('mask_area') or 0)-float(last.get('mask_area') or 0))/max(1,float(first.get('mask_area') or 1)))

def select_pack(video_id,event,anchor,rows,fps):
    key=anchor['anchor_key']
    ordered=sorted(rows,key=lambda r:r['frame'])
    def anchor_at(r):
        return next((a for a in r.get('anchors',[]) if a['anchor_key']==key and a.get('authorized')),None)
    def target(r):
        return bool(r.get('target_bbox') and r.get('target_authorization',{}).get('status')=='OBSERVATION_AUTHORIZED')
    pairs=[r for r in ordered if target(r) and anchor_at(r) and r.get('view_ok')]
    anchors=[r for r in ordered if anchor_at(r)]
    metrics={'before_target_usable':any(target(r) for r in ordered), 'before_anchor_usable':bool(anchors),
        'during_target_usable':len(pairs)>=2,'during_anchor_usable':len(anchors)>=2,
        'transition_evidence_usable':False,'after_anchor_usable':False}
    result={'video_id':video_id,'event_id':event['event_id'],'target_id':'phone_01','anchor_id':key,
        'anchor':deepcopy(anchor),'before_frames':[],'during_frames':[],'after_frames':[], 'selected_frames':[],
        'eligibility_status':'EVIDENCE_UNAVAILABLE','failure_reason':None,'secondary_reasons':[],
        'funnel':metrics,'physical_absence_claimed':False,'identity_write_authorized':False,
        'usable_pair_frame_count':len(pairs),'profile':'LOCAL_TEMPORAL_PAIR_WITH_OPTIONAL_AFTER_NONOBSERVATION',
        'provenance':[event['event_id'],key], 'selection_reasons':[]}
    possibilities=[]
    for j,during in enumerate(pairs):
        for before in pairs[:j]:
            if before.get('chain_id')!=during.get('chain_id') or before.get('scene_segment')!=during.get('scene_segment'):
                continue
            score=transition_score(before,during,key)
            if score <= 1e-6: continue
            metrics['transition_evidence_usable']=True
            after=[]
            for row in ordered:
                if row['frame']<=during['frame'] or not anchor_at(row): continue
                if row.get('scene_segment')!=during.get('scene_segment') or not row.get('scene_ok') or not row.get('view_ok'): continue
                visible=target(row) and row.get('chain_id')==during.get('chain_id')
                not_observed=(not row.get('sam_present') and not row.get('phone_candidates')
                              and row.get('target_visible_state')=='NOT_OBSERVED')
                if visible or not_observed:
                    # One AFTER sequence describes one assessable state. A lone miss
                    # after a visible frame must not become non-observation evidence.
                    if after and target(after[0])!=visible: break
                    after.append(row)
                if len(after)==2: break
            if not after: continue
            size=during.get('image_size')
            box=during['target_bbox']
            target_clipped=bool(size and (box[0]<=0 or box[1]<=0 or box[2]>=size[0] or box[3]>=size[1]))
            if not target(after[0]) and target_clipped:
                # A target leaving the camera field cannot establish an observable
                # post-interaction target region, even when the anchor stays visible.
                continue
            # Non-observation needs repeated anchor-visible views; one detector miss is insufficient.
            if not target(after[0]) and (len(after)<2 or after[1]['frame']-after[0]['frame']>round(.4*fps)
                    or after[0]['frame']-during['frame']>round(.4*fps)): continue
            metrics['after_anchor_usable']=True
            possibilities.append((score,-abs(during['frame']-event['peak_frame']),-before['frame'],before,during,after))
    if not possibilities:
        if not any(target(r) for r in ordered): reason='NO_TARGET_BEFORE'
        elif not anchors: reason='ANCHOR_EVIDENCE_MISSING'
        elif not pairs: reason='PAIR_NEVER_COVISIBLE'
        elif len(pairs)<2: reason='NO_TARGET_DURING'
        elif not metrics['transition_evidence_usable']: reason='NO_TRANSITION_EVIDENCE'
        elif any(not r.get('scene_ok') for r in ordered): reason='SCENE_BREAK'
        else: reason='NO_ANCHOR_AFTER'
        result['failure_reason']=reason
        if any(r.get('sam_present') and not target(r) for r in ordered): result['secondary_reasons'].append('MASK_UNTRUSTWORTHY')
        if not any(r.get('mask_reference') for r in ordered): result['secondary_reasons'].append('MASK_UNAVAILABLE')
        return result
    score,_,_,before,during,after=max(possibilities,key=lambda p:p[:3])
    result['transition_selection_score']=score
    mids=[r for r in pairs if before['frame']<r['frame']<=during['frame'] and r.get('chain_id')==before.get('chain_id')]
    # At most three transition frames, chosen at the start, midpoint and end of the actual change.
    mids=[mids[k] for k in sorted(set([0,len(mids)//2,len(mids)-1]))]
    phases=[('BEFORE',[before]),('DURING',mids),('AFTER',after)]
    for phase,phase_rows in phases:
        result[f'{phase.lower()}_frames']=[r['frame'] for r in phase_rows]
        for r in phase_rows:
            a=anchor_at(r); observed=target(r)
            result['selected_frames'].append({'phase':phase,'frame':r['frame'],'time':r['time'],
                'target_id':'phone_01','anchor_id':key,'target_bbox':r.get('target_bbox') if observed else None,
                'anchor_bbox':a['bbox'],'target_observation_authorization':deepcopy(r['target_authorization']),
                'anchor_observation_authorization':{'status':'OBSERVATION_AUTHORIZED','source':a.get('source'),
                    'confidence':a.get('confidence'),'raw_label':a.get('raw_label'), 'persistent_identity_claimed':False},
                'target_visible_state':'OBSERVED' if observed else 'TARGET_NOT_OBSERVED_WITH_ANCHOR_VISIBLE',
                'anchor_visible_state':'OBSERVED','mask_reference':r.get('mask_reference') if observed else None,
                'bbox_reference':a.get('bbox_reference',f"{event['event_id']}#frame:{r['frame']}:{key}"),
                'continuity_chain_id':r.get('chain_id') or during.get('chain_id'),
                'scene_continuity':{'segment':r['scene_segment'],'no_cut_detected':r['scene_ok'],'region_observable':r['view_ok']}})
    result.update(eligibility_status='ELIGIBLE',failure_reason=None,
        selection_reasons=['Maximum measured pair geometry/visibility change among causal authorized observations',
            'Earliest subsequent anchor-visible assessable views; no physical absence inferred',
            'Non-observation requires two same-state views within short continuity and no preceding target edge clipping'],
        continuity_chain_id=before.get('chain_id'))
    return result
