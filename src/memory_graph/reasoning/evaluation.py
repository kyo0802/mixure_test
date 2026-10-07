"""Post-freeze engineering review evaluation; no imports into window/inference logic."""
from collections import Counter
from .common import ROOT,OUT,read,write,sha256
from .pipeline import verify,verify_manifest

FIELDS=('event_type','interaction_anchor','released','target_visible_after','final_relation','final_relation_anchor')
FAILURES=('WINDOW_START_TOO_LATE','WINDOW_END_TOO_EARLY','WINDOW_TOO_LONG','NO_STABLE_PRE_STATE','NO_STABLE_POST_STATE',
    'TRANSITION_NOT_CAPTURED','ACTOR_CONTEXT_MISSING','LOCATION_CONTEXT_MISSING','TARGET_NOT_VISIBLE_ENOUGH',
    'EVENT_SELECTION_WRONG','QWEN_EVENT_REASONING_ERROR','QWEN_ACTOR_ERROR','QWEN_RELATION_ERROR','UPSTREAM_IDENTITY_LIMITATION')

def score(answer,truth):
    return {f:'INDETERMINATE' if truth.get(f) is None else 'CORRECT' if isinstance(answer,dict) and answer.get(f) in truth[f] else 'INCORRECT' for f in FIELDS}

def summarize(responses,reviews,validations):
    lookup={r['pack_id']:r for r in reviews};rows=[]
    for p in responses:
        r=lookup[p['pack_id']];rows.append({'pack_id':p['pack_id'],'field_correctness':score(p['answer'],r['admissible_values']),
            'reasoning_eligible':r['reasoning_eligible'],'unsafe_overclaim':r['unsafe_overclaim']})
    def fields(subset):
        result={}
        for f in FIELDS:
            c=Counter(r['field_correctness'][f] for r in subset);den=c['CORRECT']+c['INCORRECT']
            result[f]={'correct':c['CORRECT'],'incorrect':c['INCORRECT'],'indeterminate':c['INDETERMINATE'],'denominator':den,'rate':c['CORRECT']/den if den else None}
        return result
    return {'calls':len(responses),'schema_valid':sum(v['schema_valid'] for v in validations),'validator_valid':sum(v['valid'] for v in validations),
        'reasoning_eligible':sum(r['reasoning_eligible'] for r in rows),'reasoning_eligible_rate':sum(r['reasoning_eligible'] for r in rows)/len(rows) if rows else None,
        'ALL':fields(rows),'REASONING_ELIGIBLE':fields([r for r in rows if r['reasoning_eligible']]),
        'event_types':dict(Counter((p['answer'] or {}).get('event_type','MISSING') for p in responses)),
        'relations':dict(Counter((p['answer'] or {}).get('final_relation','MISSING') for p in responses)),
        'unsafe_overclaims':sum(r['unsafe_overclaim'] for r in rows),'rows':rows}

def simulation(answer,validation,review):
    """Exact conservative V2945 post-review mapping; never operational trust writes."""
    relation=(answer or {}).get('final_relation');real=relation not in {None,'NONE','UNCERTAIN'}
    state='UNCERTAIN'
    if not validation['valid'] or review['unsafe_overclaim'] or review['relation_review']=='INCORRECT':state='REJECTED'
    elif real and review['relation_review']=='SUPPORTED' and review['material_assertions_safe']:state='PROMOTED'
    elif real and review['relation_review']=='WEAKLY_SUPPORTED' and review['material_assertions_safe'] and review['search_useful']:state='CANDIDATE'
    safe=real and state in {'PROMOTED','CANDIDATE'} and review['search_useful'] and review['material_assertions_safe']
    return {'pack_id':validation['pack_id'],'simulated_state':state,'SAFE_SEARCHABLE_MEMORY':safe,'actual_trusted_writes':0,'identity_writes':0}

def evaluate():
    checks={'new':verify(),'same_runtime_old':verify_manifest(OUT,OUT/'final/baseline_prediction_manifest.json')}
    if not all(c['valid'] for c in checks.values()):raise RuntimeError(checks)
    review=read(OUT/'evaluation/post_freeze_review.json');responses=read(OUT/'qwen/responses.json');vals=read(OUT/'qwen/validator_results.json')
    if not review or review['predictions_changed']:raise ValueError('Frozen review required')
    by={r['pack_id']:r for r in review['events']};events=read(OUT/'event_windows/event_manifest.json')
    physical=[e for e in events if e['category']=='PHYSICAL_INTERACTION_EVENT']
    if set(by)!={e['pack_id'] for e in physical}:raise ValueError('Every selected physical window must be reviewed')
    metrics=summarize(responses,list(by.values()),vals)
    old_review=read(ROOT/'outputs/reference_qwen/evaluation/post_freeze_review.json')['events']
    eligible={r['pack_id']:r['stratum']=='REASONING_ELIGIBLE' for r in read(ROOT/'outputs/reference_qwen/evaluation/eligibility_stratification.json')['events']}
    for r in old_review:r['reasoning_eligible']=eligible[r['pack_id']]
    same=OUT/'evaluation/runtime_matched_baseline';old_res=read(same/'responses.json');old_vals=read(same/'validator_results.json')
    old_metrics=summarize(old_res,old_review,old_vals)
    original=read(ROOT/'outputs/reference_qwen/reasoning/reasoning_metrics.json')
    sims=[simulation(p['answer'],v,by[p['pack_id']]) for p,v in zip(responses,vals)]
    # New-baseline safe/unsafe flags are reviewed separately after its predictions freeze.
    old_new_review=read(OUT/'evaluation/baseline_same_runtime_review.json')['events']
    for r in old_new_review:r['reasoning_eligible']=eligible[r['pack_id']]
    old_metrics=summarize(old_res,old_new_review,old_vals)
    old_sims=[simulation(p['answer'],v,next(r for r in old_new_review if r['pack_id']==p['pack_id'])) for p,v in zip(old_res,old_vals)]
    complete=[e for e in physical if e['completeness']=='COMPLETE_EVENT_WINDOW']
    window={'selected_physical':len(physical),'deterministic_complete':len(complete),'deterministic_incomplete':len(physical)-len(complete),
        'automatic_complete_rate':len(complete)/len(physical),'review_complete_pre_transition_post':sum(by[e['pack_id']]['visually_complete_transition'] for e in physical),
        'placement_release_reviewable':sum(by[e['pack_id']]['placement_release_reviewable'] for e in physical),
        'placement_release_sent_to_qwen':sum(by[e['pack_id']]['placement_release_reviewable'] for e in complete),
        'reasoning_eligible_among_dispatched':metrics['reasoning_eligible'],'reasoning_eligible_rate_among_dispatched':metrics['reasoning_eligible_rate'],
        'reasoning_eligible_selected_physical':sum(r['reasoning_eligible'] for r in by.values()),
        'review_scope':'Execution-agent visual engineering review; not independent human GT or model-wide accuracy',
        'rows':[{'pack_id':e['pack_id'],'trigger':e['trigger'],'completeness':e['completeness'],
                 'visual_complete':by[e['pack_id']]['visually_complete_transition'],'placement_release_reviewable':by[e['pack_id']]['placement_release_reviewable'],
                 'reasoning_eligible':by[e['pack_id']]['reasoning_eligible'],'finding':by[e['pack_id']]['finding']} for e in physical]}
    memory={'simulation_only':True,'unchanged_V2945_mapping':True,'new_safe_searchable_memory':sum(s['SAFE_SEARCHABLE_MEMORY'] for s in sims),
        'old_same_runtime_safe_searchable_memory':sum(s['SAFE_SEARCHABLE_MEMORY'] for s in old_sims),'original_baseline_safe_searchable_memory':0,
        'events':sims,'P_C_U_R':dict(Counter(s['simulated_state'] for s in sims)),'actual_identity_writes':0,'actual_physical_writes':0,
        'actual_Memory_Graph_Search_Planner_updates':0,'offline_review_not_identity_authority':True}
    failures=Counter(c for r in review['events'] for c in r['failure_categories'])
    bottleneck=review['single_bottleneck']
    analysis={'taxonomy':list(FAILURES),'counts':{c:failures[c] for c in FAILURES},'single_bottleneck':bottleneck,
        'rows':[{'pack_id':r['pack_id'],'categories':r['failure_categories'],'finding':r['finding']} for r in review['events']],
        'duplicate_window_pairs':review.get('duplicate_window_pairs',[]),'parameters_retuned_after_review':False}
    comparison={'original_V2945':original,'same_runtime_old_windows':old_metrics,'new_adaptive_windows':metrics,
        'same_checkpoint_quantization_preprocessing_generation_kernel':True,'original_baseline_unchanged':True,
        'prompt_delta':'Only actor/location role declaration; same seven fields, no examples/citations/geometry',
        'old_visual_complete_transition':review['old_visual_complete_transition'],'new_visual_complete_transition':window['review_complete_pre_transition_post'],
        'old_placement_release_reviewable':review['old_placement_release_reviewable'],'new_placement_release_reviewable':window['placement_release_reviewable'],
        'matched_scene_videos':['test1','test2','test8'],'expanded_new_development_videos':9,
        'new_matched_scene_subset':summarize([p for p in responses if p['pack_id'].split('__')[0] in {'test1','test2','test8'}],list(by.values()),
            [v for v in vals if v['pack_id'].split('__')[0] in {'test1','test2','test8'}]),
        'comparison_not_paired_accuracy':'Changed boundaries/context and expanded development scene coverage; correlated packs and class distributions differ',
        'decision':review['decision'],'readiness':review['readiness']}
    for name,value in [('window_quality',window),('reasoning_metrics',metrics),('search_memory',memory),('failure_analysis',analysis),('baseline_comparison',comparison)]:write(OUT/f'evaluation/{name}.json',value)
    write(OUT/'evaluation/review_freeze.json',{'review_completed_unix':review['review_completed_unix'],'predictions_changed':False,
        'files':{p.relative_to(OUT).as_posix():sha256(p) for p in (OUT/'evaluation').glob('*.json') if p.name!='review_freeze.json'},
        'sources':{'src/memory_graph/reasoning/evaluation.py':sha256(ROOT/'src/memory_graph/reasoning/evaluation.py')}})
    return {'window_quality':window,'new_metrics':metrics,'memory':memory,'decision':review['decision'],'readiness':review['readiness']}
