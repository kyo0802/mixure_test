"""Nine development-video evidence replay, with bounded selective dense recovery."""
from collections import Counter
from pathlib import Path
import time
from .audit import ROOT, BASE, OUT, VIDEOS, read, write, run_audit
from .sources import EvidenceSources, verify_baseline_contract
from .evidence import select_pack
from .reasoning import LocalVLM, dispatch, render_pack, evaluate_gate, prompt, validate_answer


def input_fingerprint(question,images):
    import hashlib
    digest=hashlib.sha256(question.encode('utf-8'))
    for path in images:
        p=Path(path)
        if not p.is_file():return None
        digest.update(hashlib.sha256(p.read_bytes()).digest())
    return digest.hexdigest()

def prepare_all():
    if (OUT/'artifact_manifest.json').exists():raise RuntimeError('V293 predictions are frozen')
    baseline=verify_baseline_contract()
    write(OUT/'baseline_contract.json',baseline)
    if not (OUT/'evidence_failure_audit.json').exists():run_audit()
    source=EvidenceSources();summary=[]
    try:
        for video in VIDEOS:
            started=time.monotonic();folder=OUT/video;packs=[];pool=[];logs=[];prepared=[]
            for event in read(BASE/video/'events/selected_events.json'):
                print(f'V293 prepare {video} {event["event_id"]}',flush=True)
                spec,rows,anchors,masks,log,size,fps=source.prepare(video,event)
                options=[select_pack(video,spec,a,rows,fps) for a in anchors]
                options.sort(key=lambda p:(p['eligibility_status']!='ELIGIBLE',-p.get('transition_selection_score',0),
                                          -p['usable_pair_frame_count'],p['anchor_id']))
                chosen=options[:2]
                for p in options:p['query_budget_selected']=p in chosen
                pool.extend(options);packs.extend(chosen);logs.append(log)
                prepared.append({'event':spec,'rows':rows,'masks':masks,'size':size,'fps':fps,'packs':chosen})
            write(folder/'candidate_pair_pool.json',pool)
            write(folder/'pair_evidence_requests.json',[{'event_id':p['event_id'],'target_id':p['target_id'],'anchor_id':p['anchor_id']} for p in packs])
            write(folder/'pair_evidence_packs.json',packs)
            write(folder/'eligibility_decisions.json',[{k:p[k] for k in ('event_id','anchor_id','eligibility_status','failure_reason','secondary_reasons')} for p in packs])
            write(folder/'selected_temporal_frames.json',[{'event_id':p['event_id'],'anchor_id':p['anchor_id'],'selected_frames':p['selected_frames']} for p in packs])
            write(folder/'selective_dense_recomputation_log.json',logs)
            write(folder/'prepared_events.json',prepared)
            item={'video_id':video,'pair_requests_total':len(packs),'pair_evidence_eligible':sum(p['eligibility_status']=='ELIGIBLE' for p in packs),
                'recomputed_intervals':sum(l['recomputed'] for l in logs),'prepare_seconds':time.monotonic()-started,
                'rejections':dict(Counter(p['failure_reason'] for p in packs if p['failure_reason']))}
            summary.append(item);write(folder/'prepare_summary.json',item);print(item,flush=True)
    finally:source.close()
    write(OUT/'prepare_summary.json',summary)
    return summary

def _debug_unavailable(video,pack,rows,folder):
    candidates=[r for r in rows if any(a['anchor_key']==pack['anchor_id'] for a in r['anchors'])]
    if not candidates:return []
    selected=[]
    for idx in sorted({0,len(candidates)//2,len(candidates)-1}):
        row=candidates[idx];a=next(a for a in row['anchors'] if a['anchor_key']==pack['anchor_id'])
        selected.append({'frame':row['frame'],'phase':'UNAVAILABLE','target_bbox':row.get('target_bbox'),
            'anchor_bbox':a['bbox'],'target_visible_state':pack['failure_reason']})
    return render_pack(video,{**pack,'selected_frames':selected},folder,True)


def reselect_prepared():
    """Apply an evidence-contract correction without repeating any dense inference."""
    if (OUT/'artifact_manifest.json').exists():raise RuntimeError('V293 predictions are frozen')
    summaries=[]
    for video in VIDEOS:
        folder=OUT/video;prepared=read(folder/'prepared_events.json');packs=[];pool=[]
        for item in prepared:
            anchors=read(folder/'events'/item['event']['event_id']/'anchors.json')
            options=[select_pack(video,item['event'],a,item['rows'],item['fps']) for a in anchors]
            options.sort(key=lambda p:(p['eligibility_status']!='ELIGIBLE',-p.get('transition_selection_score',0),
                                      -p['usable_pair_frame_count'],p['anchor_id']))
            item['packs']=options[:2]
            for p in options:p['query_budget_selected']=p in item['packs']
            packs.extend(item['packs']);pool.extend(options)
        write(folder/'prepared_events.json',prepared)
        write(folder/'candidate_pair_pool.json',pool)
        write(folder/'pair_evidence_packs.json',packs)
        write(folder/'pair_evidence_requests.json',[{'event_id':p['event_id'],'target_id':p['target_id'],'anchor_id':p['anchor_id']} for p in packs])
        write(folder/'eligibility_decisions.json',[{k:p[k] for k in ('event_id','anchor_id','eligibility_status','failure_reason','secondary_reasons')} for p in packs])
        write(folder/'selected_temporal_frames.json',[{'event_id':p['event_id'],'anchor_id':p['anchor_id'],'selected_frames':p['selected_frames']} for p in packs])
        summary=read(folder/'prepare_summary.json')
        summary.update(pair_evidence_eligible=sum(p['eligibility_status']=='ELIGIBLE' for p in packs),
                       rejections=dict(Counter(p['failure_reason'] for p in packs if p['failure_reason'])),
                       evidence_reselected_without_dense_rerun=True)
        write(folder/'prepare_summary.json',summary);summaries.append(summary)
    write(OUT/'prepare_summary.json',summaries)
    return summaries

def replay_vlm():
    if (OUT/'artifact_manifest.json').exists():raise RuntimeError('V293 predictions are frozen')
    model=LocalVLM();debug_counts=Counter();summaries=[]
    for video in VIDEOS:
        started=time.monotonic();folder=OUT/video;results=[];physical=[];inputs=[];metrics=Counter();reasons=Counter()
        previous={}
        for old in read(folder/'vlm_results.json',[]):
            if old.get('called') and old.get('observable_facts'):
                previous[(old['event_id'],old['anchor_id'])]=(old,input_fingerprint(old['prompt'],old['images']))
        for prepared in read(folder/'prepared_events.json'):
            e=prepared['event'];rows=prepared['rows']
            for p in prepared['packs']:
                metrics['pair_requests_total']+=1
                for key,val in p['funnel'].items():metrics[key]+=int(val)
                eligible=p['eligibility_status']=='ELIGIBLE';metrics['pair_evidence_eligible']+=int(eligible)
                identifier=p['anchor_id'].replace('::','__').replace(':','_')
                image_dir=folder/'vlm_inputs'/identifier
                if eligible:
                    images=render_pack(video,p,image_dir,debug_counts['eligible']<3)
                    debug_counts['eligible']+=1
                else:
                    images=[];reasons[p['failure_reason']]+=1
                    if debug_counts['unavailable']<3:
                        _debug_unavailable(video,p,rows,folder/'debug_unavailable'/identifier);debug_counts['unavailable']+=1
                print(f'V293 {video} {p["anchor_id"]} {p["eligibility_status"]}',flush=True)
                old,fingerprint=previous.get((p['event_id'],p['anchor_id']),(None,None))
                current_fingerprint=input_fingerprint(prompt(p),images) if eligible else None
                if eligible and old and fingerprint and fingerprint==current_fingerprint:
                    result={**old,**validate_answer(p,old['observable_facts']),
                            'reused_exact_input_response':True,'response_input_sha256':fingerprint}
                else:
                    result=dispatch(p,images,model)
                    result.update(reused_exact_input_response=False,response_input_sha256=current_fingerprint)
                    metrics['vlm_new_inference_calls']+=int(result['called'])
                result.update(event_id=p['event_id'],anchor_id=p['anchor_id'],target_id=p['target_id'])
                metrics['vlm_called']+=int(result['called']);metrics['vlm_schema_valid']+=int(result['schema_valid'])
                metrics['vlm_grounding_valid']+=int(result['grounding_valid'])
                if result['called'] and not result['grounding_valid']:
                    if debug_counts['invalid']<2:render_pack(video,p,image_dir,True);debug_counts['invalid']+=1
                decisions=evaluate_gate(video,e,p,result,rows,prepared['masks'],tuple(prepared['size']))
                metrics['physical_gate_called']+=len(decisions)
                for d in decisions:metrics['physical_'+d['decision'].lower()]+=1
                inputs.append({'event_id':p['event_id'],'anchor_id':p['anchor_id'],'images':[str(i.relative_to(ROOT)) for i in images],
                    'prompt':result.get('prompt'),'model':'Qwen2.5-VL-3B-Instruct','generation_max_tokens':768})
                results.append(result);physical.extend(decisions)
                write(folder/'vlm_results.json',results);write(folder/'physical_decisions.json',physical)
        for key in ('vlm_called','vlm_new_inference_calls','vlm_schema_valid','vlm_grounding_valid','physical_gate_called','physical_promoted','physical_candidate','physical_uncertain','physical_rejected'):
            metrics.setdefault(key,0)
        write(folder/'vlm_inputs.json',inputs)
        write(folder/'grounding_validation.json',[{k:r.get(k) for k in ('event_id','anchor_id','status','reason','called','schema_valid','grounding_valid','evidence_frames')} for r in results])
        prepare=read(folder/'prepare_summary.json')
        first=('evidence_eligibility' if not metrics['pair_evidence_eligible'] else 'vlm_schema' if not metrics['vlm_schema_valid']
               else 'vlm_grounding' if not metrics['vlm_grounding_valid'] else 'physical_geometry' if not metrics['physical_gate_called'] else None)
        row={**prepare,'funnel':dict(metrics),'rejection_counts':dict(reasons),'first_failing_stage':first,
            'response_inference_seconds':sum(r.get('runtime_seconds',0) for r in results),
            'exact_input_response_reused':sum(r.get('reused_exact_input_response',False) for r in results),
            'vlm_and_gate_seconds':time.monotonic()-started,'relation_breakdown':{rel:dict(Counter(d['decision'] for d in physical if d['candidate_relation']==rel)) for rel in sorted({d['candidate_relation'] for d in physical})},
            'vlm_status_counts':dict(Counter(r['status'] for r in results))}
        write(folder/'summary.json',row);summaries.append(row);print(row,flush=True)
    aggregate=Counter()
    for row in summaries:aggregate.update(row['funnel'])
    rejection=Counter()
    for row in summaries:rejection.update(row['rejection_counts'])
    write(OUT/'evidence_funnel.json',{'aggregate':dict(aggregate),'per_video':{r['video_id']:r for r in summaries},'rejection_counts':dict(rejection),
        'metric_note':'Physical gate count counts relation hypotheses, not unique pairs; phase usable counters are independent, not conditional conversion rates.'})
    write(OUT/'benchmark_summary.json',{'videos':summaries,'development_videos_only':VIDEOS,
        'upstream_full_rerun':False,'selectively_recomputed_intervals':sum(r['recomputed_intervals'] for r in summaries),
        'prepare_seconds':sum(r['prepare_seconds'] for r in summaries),
        'canonical_response_inference_seconds':sum(r['response_inference_seconds'] for r in summaries),
        'response_reuse_policy':'Only identical prompt and image SHA256 responses from this V293 development run; grounding and gate re-evaluated with final contract.',
        'runtime_note':'Canonical response times exclude discarded development attempts; response reuse is not a new inference call.'})
    return summaries
