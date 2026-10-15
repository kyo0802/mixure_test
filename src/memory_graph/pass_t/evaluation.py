"""Window-level evaluator skeleton. No inference, training or graph writes."""
import math
from itertools import combinations
from .contracts import ACTIONS


def rate(n, d):
    if not d:return {'numerator':n,'denominator':d,'rate':None,'percent':None,'wilson_95_ci':None}
    z=1.959963984540054;p=n/d;den=1+z*z/d
    center=(p+z*z/(2*d))/den
    radius=z*math.sqrt(p*(1-p)/d+z*z/(4*d*d))/den
    return {'numerator':n,'denominator':d,'rate':p,'percent':100*p,
            'wilson_95_ci':[max(0,center-radius),min(1,center+radius)]}


def extent(e):
    return (e['onset_interval_s'][0],e['offset_interval_s'][1]) if e['onset_interval_s'] and e['offset_interval_s'] else None


def match_events(gt, pred, tolerance=.5):
    """Earliest GT onset first; match action + contained uncertainty interval."""
    matches=[];used=set()
    for gi,g in sorted(enumerate(gt),key=lambda z:(extent(z[1]) or (math.inf,math.inf),z[0])):
        ge=extent(g);candidates=[]
        for pi,p in enumerate(pred):
            pe=extent(p)
            if pi in used or p['action']!=g['action']:continue
            if ge and pe and ge[0]-tolerance<=pe[0]<=pe[1]<=ge[1]+tolerance:
                candidates.append((abs(pe[0]-ge[0])+abs(pe[1]-ge[1]),pi))
        if candidates:
            pi=min(candidates)[1];used.add(pi);matches.append((gi,pi))
    return matches


def evaluate(items):
    """Items contain separated GT, prediction, bundle and optional runtime.

    Human anchor-label equivalence requires explicit adjudication; text matching
    never asserts physical-anchor equivalence.
    """
    counts={a:{'tp':0,'fp':0,'fn':0,'support':0} for a in ACTIONS}
    pickup=[0,0];placement=[0,0];unsupported=[]; factual=[];order=[0,0];actor=[0,0]
    coverage=[0,len(items)];selective=[0,0];abstention=[0,0];location=[0,0];locunsupported=[0,0]
    relation_correct=[0,0];relation_coverage=[0,len(items)];localization=[];sampling_missed=0
    anchor_pending=0;logs=[]; sessions=set()
    for item in items:
        g=item['gt'];p=item['prediction'];sm=item['bundle']['sampling_manifest_id'];sessions.add(g['session_id'])
        full=g['events'];direct=[e for e in full if e['sampled_observability'][sm]['support_class']=='DIRECT']
        predictions=p['events'];matches=match_events(direct,predictions);fullmatches=match_events(full,predictions)
        true_prediction={pi:gi for gi,pi in fullmatches}; matched_gt={gi for gi,pi in matches}; matched_pred={pi for gi,pi in matches}
        for a,score in [('PICK_UP',pickup),('PLACE',placement)]:
            negative=(g['event_assessment']!='INDETERMINATE' and
                      not any(e['action']==a for e in full) and a not in g['unresolved_transitions'])
            if negative:score[1]+=1;score[0]+=int(any(e['action']==a for e in predictions))
        for e in full:
            o=e['sampled_observability'][sm]
            if o['unobservable_reason']=='SAMPLING_MISSED':sampling_missed+=1
        for gi,e in enumerate(direct):
            counts[e['action']]['support']+=1
            counts[e['action']]['tp' if gi in matched_gt else 'fn']+=1
        for pi,e in enumerate(predictions):
            if pi not in matched_pred:counts[e['action']]['fp']+=1
            if pi not in true_prediction:
                factual.append({'window':g['event_window_id'],'action':e['action']})
                unsupported.append({'window':g['event_window_id'],'action':e['action'],'reason':'NO_MATCHING_GT_ACTION'})
            else:
                o=full[true_prediction[pi]]['sampled_observability'][sm]
                if o['support_class']!='DIRECT':
                    unsupported.append({'window':g['event_window_id'],'action':e['action'],
                                        'reason':o['unobservable_reason'] or 'INDIRECT_ONLY'})
            if pi not in matched_pred:logs.append({'type':'UNSUPPORTED_ACTION','action':e['action'],'window':g['event_window_id']})
        for gi,pi in matches:
            ge=extent(direct[gi]);pe=extent(predictions[pi]);localization.append((abs(ge[0]-pe[0])+abs(ge[1]-pe[1]))/2)
            if item['bundle']['person_ids'] and direct[gi]['actor_local_id'] not in {None,'UNKNOWN'}:
                actor[1]+=1;actor[0]+=int(direct[gi]['actor_local_id']==predictions[pi]['actor_local_id'])
        for a,b in combinations(matches,2):
            order[1]+=1;order[0]+=int((a[0]<b[0])==(a[1]<b[1]))
        answered=p['event_assessment'] not in {'INDETERMINATE'}
        coverage[0]+=int(answered)
        if answered:
            selective[1]+=1
            selective[0]+=int(p['event_assessment']==g['event_assessment'] and len(matches)==len(direct)==len(predictions))
        if g['event_assessment']=='INDETERMINATE':
            abstention[1]+=1;abstention[0]+=int(p['event_assessment']=='INDETERMINATE' and not predictions)
        s=p['last_confirmed_state'];gs=g['last_confirmed_state'];rel=s['relation'];grel=gs['relation']
        definite=s['confirmation_status']=='CONFIRMED' and rel['predicate']!='UNKNOWN'
        if definite:
            locunsupported[1]+=1;relation_coverage[0]+=1
            support=gs['sampled_observability'][sm]['support_class']=='DIRECT'
            locunsupported[0]+=int(not support)
            if rel['anchor_local_id'] is None and rel['anchor_label'] is not None:
                equivalence=item.get('anchor_label_adjudicated_equal')
                if equivalence is None:anchor_pending+=1;continue
            else:equivalence=rel['anchor_local_id']==grel['anchor_local_id']
            correct=gs['confirmation_status']=='CONFIRMED' and rel['predicate']==grel['predicate'] and rel['reference_frame']==grel['reference_frame'] and equivalence
            location[1]+=1;location[0]+=int(not correct);relation_correct[1]+=1;relation_correct[0]+=int(correct and support)
    per={}
    for a,c in counts.items():
        precision=c['tp']/(c['tp']+c['fp']) if c['tp']+c['fp'] else None
        recall=c['tp']/(c['tp']+c['fn']) if c['tp']+c['fn'] else None
        f1=2*c['tp']/(2*c['tp']+c['fp']+c['fn']) if 2*c['tp']+c['fp']+c['fn'] else None
        per[a]={**c,'precision':precision,'recall':recall,'f1':f1}
    f1s=[v['f1'] for v in per.values() if v['support'] and v['f1'] is not None]
    return {'windows':len(items),'sessions':len(sessions),'false_pickup':rate(*pickup),
            'false_placement':rate(*placement),'incorrect_definite_final_location':rate(*location),
            'unsupported_definite_final_location':rate(*locunsupported),
            'pending_anchor_adjudication':anchor_pending,'unsupported_action_assertions':unsupported,
            'physical_action_errors':factual,'unsupported_reason_counts':{reason:sum(x['reason']==reason for x in unsupported)
                for reason in ['SAMPLING_MISSED','OCCLUDED','OUT_OF_VIEW','TOO_SMALL','INDIRECT_ONLY','NO_MATCHING_GT_ACTION','OTHER']},
            'event_per_class':per,'event_macro_f1':sum(f1s)/len(f1s) if f1s else None,
            'temporal_order':rate(*order),'temporal_localization_error_s':sum(localization)/len(localization) if localization else None,
            'actor_accuracy':rate(*actor),'relation_precision':rate(*relation_correct),
            'relation_coverage':rate(*relation_coverage),'answer_coverage':rate(*coverage),
            'selective_accuracy':rate(*selective),'correct_abstention':rate(*abstention),
            'sampling_missed_excluded_from_direct_recall':sampling_missed,
            'authority_log':logs,'graph_write_attempts':0,
            'engineering':{'request_completion':None,'schema_valid_rate':None,'latency_s':None,
                'peak_vram_bytes':None,'visual_tokens':None,'runtime_errors':None,
                'note':'Synthetic evaluator fixtures only; no model runtime measured'}}
