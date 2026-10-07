"""Paired post-freeze comparison on unchanged reference labels and trust mapping."""
from collections import Counter
from .video_experiment import ROOT,OUT,EXP,read,write,events,verify_baseline
from .common import sha256
from .evaluation import FIELDS,score,summarize,simulation
from .pipeline import verify_manifest

TAXONOMY=['VIDEO_TEMPORAL_DENSITY_NOT_ACHIEVED','NATIVE_VIDEO_RUNTIME_INFEASIBLE','VIDEO_PROCESSOR_FAILURE',
    'VIDEO_ENCODING_FAILURE','STATIC_COLLAPSE','QWEN_EVENT_REASONING_ERROR','QWEN_ACTOR_ERROR','QWEN_RELEASE_ERROR',
    'QWEN_VISIBILITY_ERROR','QWEN_RELATION_ERROR','UPSTREAM_ACTOR_CONTEXT_MISSING','UPSTREAM_LOCATION_CONTEXT_MISSING',
    'UPSTREAM_IDENTITY_LIMITATION','WINDOW_NOT_ACTUALLY_ACTION_COMPLETE','REVIEW_REFERENCE_DISAGREEMENT']

def paired(ids,a,b,va,vb,reference,video_review):
    aa={r['pack_id']:r for r in a};bb={r['pack_id']:r for r in b}
    aval={r['pack_id']:r for r in va};bval={r['pack_id']:r for r in vb}
    rows=[]
    for p in ids:
        truth=reference[p]['admissible_values']
        rows.append({'pack_id':p,'reference':truth,'image_answer':aa[p]['answer'],'video_answer':bb[p]['answer'],
            'image_correctness':score(aa[p]['answer'],truth),'video_correctness':score(bb[p]['answer'],truth)})
    return {'n':len(ids),'pack_ids':ids,
        'image':summarize([aa[p] for p in ids],[reference[p] for p in ids],[aval[p] for p in ids]),
        'video':summarize([bb[p] for p in ids],[video_review[p] for p in ids],[bval[p] for p in ids]),'rows':rows}

def unique_episode(groups,paired_rows):
    lookup={r['pack_id']:r for r in paired_rows};out=[]
    for group in groups:
        out.append({'pack_ids':group,
            'image_all_correct':{f:all(lookup[p]['image_correctness'][f]=='CORRECT' for p in group) for f in FIELDS},
            'video_all_correct':{f:all(lookup[p]['video_correctness'][f]=='CORRECT' for p in group) for f in FIELDS},
            'image_any_correct':{f:any(lookup[p]['image_correctness'][f]=='CORRECT' for p in group) for f in FIELDS},
            'video_any_correct':{f:any(lookup[p]['video_correctness'][f]=='CORRECT' for p in group) for f in FIELDS}})
    return {'n':len(out),'aggregation':'Conservative all-window agreement is primary; any-window counts descriptive',
        'image_all_correct':{f:sum(r['image_all_correct'][f] for r in out) for f in FIELDS},
        'video_all_correct':{f:sum(r['video_all_correct'][f] for r in out) for f in FIELDS},'rows':out}

def evaluate():
    verify_baseline();check=verify_manifest(EXP,EXP/'final/artifact_manifest.json')
    if not check['valid']:raise RuntimeError(check)
    frozen=read(OUT/'evaluation/post_freeze_review.json');ref={r['pack_id']:r for r in frozen['events']}
    current=read(EXP/'evaluation/post_freeze_video_review.json')
    if current['predictions_changed']:raise ValueError('Prediction edits forbidden')
    vr={r['pack_id']:r for r in current['events']}
    ids=[e['pack_id'] for e in events()]
    if set(vr)!=set(ids):raise ValueError('Exact nine video reviews required')
    for p in ids:
        if vr[p]['admissible_values']!=ref[p]['admissible_values']:raise ValueError('Frozen reference changed')
        if vr[p]['reasoning_eligible']!=ref[p]['reasoning_eligible']:raise ValueError('Frozen stratum changed')
    a=read(OUT/'qwen/responses.json');b=read(EXP/'qwen/responses.json')
    va=read(OUT/'qwen/validator_results.json');vb=read(EXP/'qwen/validator_results.json')
    subsets={'all9':ids,'eligible':[p for p in ids if ref[p]['reasoning_eligible']],
        'complete_action6':[p for p in ids if ref[p]['visually_complete_transition']],
        'release3':[p for p in ids if ref[p]['confirmed_visible_release']]}
    if [len(subsets[k]) for k in subsets]!=[9,8,6,3]:raise ValueError('Reference denominator drift')
    results={k:paired(ps,a,b,va,vb,ref,vr) for k,ps in subsets.items()}
    for k,d in results.items():write(f'evaluation/paired_{k}.json',d)
    groups=[['test1__W03','test1__W05']]+[[p] for p in ids if p not in {'test1__W03','test1__W05'}]
    release_groups=[['test1__W03','test1__W05'],['test8__W06']]
    unique={'ALL':unique_episode(groups,results['all9']['rows']),
        'ACTION':unique_episode([g for g in groups if all(p in subsets['complete_action6'] for p in g)],results['all9']['rows']),
        'RELEASE':unique_episode(release_groups,results['release3']['rows'])}
    write('evaluation/unique_episode_analysis.json',unique)
    fields={'event_type_analysis':'event_type','actor_analysis':'interaction_anchor','release_analysis':'released',
        'visibility_analysis':'target_visible_after','relation_analysis':'final_relation'}
    all9=results['all9'];dist=all9['video']['event_types']
    static='STATIC_COLLAPSE_PERSISTS' if dist.get('STATIC',0)==9 else 'STATIC_COLLAPSE_RESOLVED' if dist.get('STATIC',0)==0 else 'STATIC_COLLAPSE_REDUCED'
    for name,f in fields.items():
        data={'field':f,'image':all9['image']['ALL'][f],'video':all9['video']['ALL'][f],
            'rows':[{'pack_id':r['pack_id'],'image':(r['image_answer'] or {}).get(f),'video':(r['video_answer'] or {}).get(f),
                'reference':r['reference'][f],'image_correctness':r['image_correctness'][f],'video_correctness':r['video_correctness'][f]} for r in all9['rows']]}
        if f=='event_type':data.update(image_distribution=all9['image']['event_types'],video_distribution=dist,STATIC_collapse=static,
            complete_action=results['complete_action6'])
        if f=='released':data.update(confirmed_packs=results['release3'],unique_release=unique['RELEASE'])
        if f=='final_relation':data.update(anchor_image=all9['image']['ALL']['final_relation_anchor'],
            anchor_video=all9['video']['ALL']['final_relation_anchor'],
            appropriate_abstention_image=sum((r['answer'] or {}).get('final_relation') in {'NONE','UNCERTAIN'} and
                score(r['answer'],ref[r['pack_id']]['admissible_values'])['final_relation']=='CORRECT' for r in a),
            appropriate_abstention_video=sum((r['answer'] or {}).get('final_relation') in {'NONE','UNCERTAIN'} and
                score(r['answer'],ref[r['pack_id']]['admissible_values'])['final_relation']=='CORRECT' for r in b))
        write(f'evaluation/{name}.json',data)
    def mem(rs,vals,reviews):
        sims=[simulation(r['answer'],v,reviews[r['pack_id']]) for r,v in zip(rs,vals)]
        return {'P_C_U_R':{s:sum(r['simulated_state']==s for r in sims) for s in ['PROMOTED','CANDIDATE','UNCERTAIN','REJECTED']},
            'safe_searchable_memory':sum(r['SAFE_SEARCHABLE_MEMORY'] for r in sims),
            'wrong_location_memory':sum(r['SAFE_SEARCHABLE_MEMORY'] and reviews[r['pack_id']]['relation_review']=='INCORRECT' for r in sims),
            'unsafe_physical_claims':sum(reviews[r['pack_id']]['unsafe_overclaim'] for r in sims),'events':sims}
    memory={'image':mem(a,va,ref),'video':mem(b,vb,vr),'unchanged_offline_simulation':True,
        'actual_identity_writes':0,'actual_trusted_physical_writes':0,'actual_Memory_Graph_Search_Planner_updates':0}
    write('evaluation/search_memory.json',memory)
    ar=read(OUT/'qwen/runtime.json');br=read(EXP/'qwen/runtime.json');pm=read(EXP/'processor/processor_metrics.json')
    compute={'image_runtime':ar,'video_runtime':br,'video_processor':pm,
        'image_input_tokens':sum(r['compute_trace']['input_token_count'] for r in a),
        'image_visual_tokens':sum(sum(t*h*w//4 for t,h,w in r['compute_trace']['image_grid_thw']) for r in a),
        'video_input_tokens':sum(m['input_tokens'] for m in pm),'video_visual_tokens':sum(m['visual_tokens'] for m in pm),
        'image_frames':sum(len(r['images']) for r in read(OUT/'qwen/requests.json')),
        'video_selected_frames':sum(m['actual_selected_frame_count'] for m in pm),
        'throughput_claim':'Different visual token counts and temporal patch packing; runtime comparison is descriptive only'}
    write('evaluation/compute_comparison.json',compute)
    counts=Counter(c for r in current['events'] for c in r['failure_categories'])
    failure={'taxonomy':TAXONOMY,'counts':{t:counts[t] for t in TAXONOMY},'rows':current['events'],
        'reference_disagreements':current.get('reference_disagreements',[]),'reference_rewritten':False,
        'STATIC_collapse':static,'identity_changes':0,'window_changes':0}
    write('evaluation/failure_analysis.json',failure)
    action=results['complete_action6']['video']['ALL']['event_type']['correct']
    release=results['release3']['video']['ALL']['released']['correct']
    unique_release=unique['RELEASE']['video_all_correct']['released']
    unsafe=memory['video']['unsafe_physical_claims'];image_unsafe=memory['image']['unsafe_physical_claims']
    meaningful=(unique['ACTION']['video_all_correct']['event_type']>=2 or unique_release>=1)
    safe=(unsafe<=image_unsafe and memory['video']['safe_searchable_memory']>=memory['image']['safe_searchable_memory']
          and all9['video']['ALL']['interaction_anchor']['correct']>=all9['image']['ALL']['interaction_anchor']['correct'])
    infrastructure=br['runtime_errors']==0 and br['EOS_count']==9
    if not infrastructure:decision='VIDEO_NATIVE_EXPERIMENT_INVALID'
    elif action>=3 and unique_release==2 and safe:decision='VIDEO_NATIVE_CLEAR_IMPROVEMENT'
    elif action>0 or release>0:decision='VIDEO_NATIVE_PARTIAL_IMPROVEMENT' if unsafe<=image_unsafe else 'VIDEO_NATIVE_REGRESSION'
    elif unsafe>image_unsafe or sum(v['correct'] for v in all9['video']['ALL'].values())<sum(v['correct'] for v in all9['image']['ALL'].values()):decision='VIDEO_NATIVE_REGRESSION'
    else:decision='VIDEO_NATIVE_NO_IMPROVEMENT'
    representation='FREEZE_NATIVE_VIDEO_FOR_VALIDATION' if infrastructure and meaningful and safe else 'KEEP_DENSE_IMAGES_FOR_VALIDATION'
    result={'decision':decision,'representation':representation,'next_step':'RUN_FROZEN_HELD_OUT_VALIDATION',
        'complete_action_event_correct':action,'confirmed_release_correct':release,'unique_release_correct':unique_release,
        'STATIC_collapse':static,'unsafe_video':unsafe,'safe_searchable_video':memory['video']['safe_searchable_memory'],
        'selection_rule':'At least two unique action episodes or one fully-agreeing unique release episode improved; no unsafe/actor/safe-memory regression. Diversity alone never qualifies.',
        'primary_reference':'Unchanged execution-agent frozen engineering review, not independent human GT'}
    write('evaluation/decision.json',result)
    return result
