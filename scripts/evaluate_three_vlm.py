"""Common post-inference diagnostics and evidence-limited evaluation.

No model import, no raw-output repair, no automatic human/physical GT labels.
Derived files are in this experiment only. Historical references are read-only.
"""
from pathlib import Path
import sys,json,hashlib,collections,statistics,math,csv
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/pass_t/phase3/three_vlm_full_v1'
sys.dont_write_bytecode=True;sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor')]
from memory_graph.experiments.three_vlm_contract import validate_raw,merge_intervals
from memory_graph.experiments.three_vlm_evaluation import event_metrics
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(name,d):
    with (OUT/name).open('x',encoding='utf8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def p95(xs):return sorted(xs)[max(0,math.ceil(len(xs)*.95)-1)] if xs else None
def main():
    dataset=read(OUT/'dataset.json');unique=[w for w in dataset['windows'] if w['status']=='ELIGIBLE' and not w['duplicate_of']];results={};proposals=[];observations=[];integrity=[];input_checks=0
    prompt=read(OUT/'prompt.json');frozen_schema=read(OUT/'schema.json')
    for model in ('qwen','videollama','nemotron'):
        base=OUT/'runs'/model;rows=[];wall=[];tokens=[];inputs=[];peaks=[];globalpeaks=[];objects=collections.Counter();states=collections.Counter()
        load_failures=[{'path':str(p.relative_to(ROOT)),**read(p)} for p in base.glob('load_failure_*.json')]
        load_receipts=[read(p) for p in base.glob('model_load_*.json')]
        for w in unique:
            dest=base/w['window_id'];r={'window_id':w['window_id'],'video_id':w['video_id'],'visual_input_sha256':w['visual_input_sha256'],'status':'NOT_EXECUTED','physical_evidence_status':'UNREVIEWED'}
            if (dest/'failure.json').exists():r.update(status='FAILED',failure=read(dest/'failure.json'))
            if not (dest/'raw.txt').exists():rows.append(r);continue
            raw=(dest/'raw.txt').read_text(encoding='utf8');diag=validate_raw(raw,[f['alias'] for f in w['frames']]);r.update(status='RAW_SAVED',raw_path=str((dest/'raw.txt').relative_to(ROOT)),raw_sha256=sha(dest/'raw.txt'),validation=diag)
            receipt=read(dest/'receipt.json') if (dest/'receipt.json').exists() else None
            if receipt:
                assert r['raw_sha256']==receipt['raw_sha256'];r['status']='COMPLETED';r['receipt']=receipt
                inp=read(dest/'input.json');checks={'frames_match_frozen_dataset':inp['frames']==w['frames'],'dataset_freeze_matches':inp['dataset_freeze_sha256']==sha(OUT/'dataset_freeze.json')}
                if model=='nemotron':
                    rendered=inp['rendered_text'];checks.update(submitted_frames_match=inp['submitted_frames']==len(w['frames']),official_processor_frames_match=inp['hf_preview_consumed_frames']==len(w['frames']),video_pruning_disabled=inp['video_pruning_rate']==0)
                else:
                    rr=read(dest/'rendered.json');rendered=rr['rendered_text'];checks.update(rendered_hash_matches=rr['rendered_sha256']==hashlib.sha256(rendered.encode('utf8')).hexdigest(),prompt_hash_matches=inp['prompt_sha256']==sha(OUT/'prompt.json'),schema_hash_matches=inp['schema_sha256']==sha(OUT/'schema.json'),source_video_hash_matches=inp['source_video_sha256']==w['source_video_sha256'],consumed_aliases_match=inp['preprocessing']['consumed_aliases']==[f['alias'] for f in w['frames']])
                checks.update(common_system_present=prompt['system'] in rendered,common_task_present=prompt['task'] in rendered,common_schema_present=json.dumps(frozen_schema,sort_keys=True) in rendered)
                r['input_integrity_checks']=checks;input_checks+=1
                integrity.extend({'model':model,'window_id':w['window_id'],'failed_check':k} for k,v in checks.items() if not v)
            if (dest/'validation.json').exists():assert read(dest/'validation.json')==diag,('PARSER_RESULT_DRIFT',model,w['window_id'])
            generation=read(dest/'generation.json') if (dest/'generation.json').exists() else {};r['generation']=generation
            if receipt and 'elapsed_s' in receipt:wall.append(receipt['elapsed_s'])
            if 'generated_tokens' in generation:tokens.append(generation['generated_tokens'])
            if 'input_token_count' in generation:inputs.append(generation['input_token_count'])
            resource=generation.get('resources',{});
            if 'gpu_peak_allocated_gib' in resource:peaks.append(resource['gpu_peak_allocated_gib'])
            if resource.get('gpu_global_peak_used_mib') is not None:globalpeaks.append(resource['gpu_global_peak_used_mib'])
            content=diag['raw']['parsed'] if diag['raw']['json_valid'] else diag['normalized_body']['validation']['parsed'] if diag['normalized_body'] else None
            r['descriptive_content']=content;r['descriptive_origin']='RAW_JSON' if diag['raw']['json_valid'] else 'EXACT_OUTER_FENCE' if diag['normalized_body'] else 'NONE'
            if isinstance(content,dict):
                for o in content.get('observations',[]) if isinstance(content.get('observations',[]),list) else []:
                    if not isinstance(o,dict):continue
                    obj=o.get('object');
                    if isinstance(obj,str):objects[obj]+=1
                    for state in o.get('states',[]) if isinstance(o.get('states',[]),list) else []:
                        if not isinstance(state,dict):continue
                        if isinstance(state.get('state'),str):states[state['state']]+=1
                        observations.append({'model':model,'window_id':w['window_id'],'video_id':w['video_id'],'object_description':obj,'state_claim':state,'strict_accepted':diag['raw']['full_valid'],'physical_support':'UNREVIEWED'})
                frame_map={f['alias']:f for f in w['frames']}
                for i,e in enumerate(content.get('events',[]) if isinstance(content.get('events',[]),list) else []):
                    if not isinstance(e,dict):continue
                    bf=e.get('before_frames',[]);af=e.get('after_frames',[]);known=isinstance(bf,list) and isinstance(af,list) and bool(bf) and bool(af) and all(isinstance(a,str) and a in frame_map for a in bf+af)
                    bracket=[max(frame_map[a]['native_pts_s'] for a in bf),min(frame_map[a]['native_pts_s'] for a in af)] if known else None
                    proposals.append({'model':model,'window_id':w['window_id'],'event_index':i,'video_id':w['video_id'],'video_sha256':w['source_video_sha256'],'type':e.get('type'),'object_description':e.get('object'),'before_frames':bf,'after_frames':af,'evidence_bracket_native_pts':bracket,'bracket_is_not_physical_event_duration':True,'strict_accepted':diag['raw']['full_valid'],'origin':r['descriptive_origin'],'reviewed_object_id':None,'reviewed_event_group':None,'physical_review_status':'UNREVIEWED','timing_match_status':'NOT_SCORED_WITHOUT_REVIEWED_IDENTITY_AND_GT_SCOPE'})
            rows.append(r)
        complete=[r for r in rows if r['status']=='COMPLETED'];parsed=[r for r in complete if r['validation']['raw']['json_valid']];schema=[r for r in complete if r['validation']['raw']['schema_valid']];accepted=[r for r in complete if r['validation']['raw']['full_valid']]
        # Citation membership is an independent diagnostic even when schema fails.
        citation_assessable=[];citation_good=[];no_citations=[]
        for r in complete:
            d=r.get('descriptive_content')
            if not isinstance(d,dict):continue
            allowed={f['alias'] for w in unique if w['window_id']==r['window_id'] for f in w['frames']};refs=[]
            def scan(x):
                if isinstance(x,dict):
                    for k,v in x.items():
                        if k=='frame' and isinstance(v,str):refs.append(v)
                        elif k in ('before_frames','after_frames') and isinstance(v,list):refs.extend(v)
                        else:scan(v)
                elif isinstance(x,list):
                    for y in x:scan(y)
            scan(d)
            if not refs:no_citations.append(r['window_id']);continue
            citation_assessable.append(r['window_id'])
            if all(isinstance(a,str) and a in allowed for a in refs):citation_good.append(r['window_id'])
        pervideo={}
        for v in dataset['videos']:
            rs=[r for r in rows if r['video_id']==v['video_id']];completed_ids={r['window_id'] for r in rs if r['status']=='COMPLETED'};intervals=merge_intervals([w['presentation_interval_half_open'] for w in unique if w['window_id'] in completed_ids])
            pervideo[v['video_id']]={'unique_inputs':len(rs),'completed':sum(r['status']=='COMPLETED' for r in rs),'failed':sum(r['status']=='FAILED' for r in rs),'not_executed':sum(r['status']=='NOT_EXECUTED' for r in rs),'raw_strict_valid':sum(r.get('validation',{}).get('raw',{}).get('full_valid',False) for r in rs),'completed_window_time_intervals':intervals,'completed_window_allocation_coverage_fraction':sum(b-a for a,b in intervals)/v['duration_seconds'],'coverage_is_not_continuous_visual_assessability':True}
        mp=[p for p in proposals if p['model']==model]
        results[model]={'unique_inputs':len(unique),'completed':len(complete),'failed':sum(r['status']=='FAILED' for r in rows),'not_executed':sum(r['status']=='NOT_EXECUTED' for r in rows),'raw_saved_without_receipt':sum(r['status']=='RAW_SAVED' for r in rows),'raw_json_parse_count':len(parsed),'raw_schema_valid_count':len(schema),'raw_strict_valid_count':len(accepted),'rates_denominator':'COMPLETED_ACTUAL_GENERATIONS; NOT_ALL_WINDOWS','raw_json_parse_rate':len(parsed)/len(complete) if complete else None,'raw_strict_valid_rate':len(accepted)/len(complete) if complete else None,'normalized_body_full_valid_count':sum(bool(r['validation']['normalized_body'] and r['validation']['normalized_body']['validation']['full_valid']) for r in complete),'citation_membership_assessable_count':len(citation_assessable),'citation_membership_valid_count':len(citation_good),'citation_support_physical_validity':'UNREVIEWED; MEMBERSHIP_IS_NOT_SUPPORT','token_cap_count':sum(bool(r['generation'].get('token_cap_reached')) for r in complete),'eos_count':sum(bool(r['generation'].get('eos_reached')) for r in complete),'timeout_count':sum(bool(r['generation'].get('timeout_reached')) for r in complete),'end_to_end_window_seconds_sum':sum(wall),'median_window_latency_s':statistics.median(wall) if wall else None,'p95_window_latency_s_nearest_rank':p95(wall),'model_load_receipts':load_receipts,'peak_torch_allocated_gib':max(peaks) if peaks else None,'peak_global_gpu_used_mib_includes_other_processes':max(globalpeaks) if globalpeaks else None,'input_token_stats':{'count':len(inputs),'median':statistics.median(inputs) if inputs else None,'min':min(inputs) if inputs else None,'max':max(inputs) if inputs else None},'output_token_stats':{'count':len(tokens),'median':statistics.median(tokens) if tokens else None,'min':min(tokens) if tokens else None,'max':max(tokens) if tokens else None},'tokens_not_cross_model_computation_units':True,'object_description_frequencies':dict(objects),'state_claim_frequencies':dict(states),'event_proposal_count':len(mp),'strict_event_proposal_count':sum(p['strict_accepted'] for p in mp),'event_claim_types':dict(collections.Counter(str(p['type']) for p in mp)),'physical_event_correctness':None,'unsupported_state_claim_frequency':None,'reason_unsupported_unmeasured':'NO_NEW_HUMAN_PER_STATE_SUPPORT_REVIEW','per_video':pervideo,'load_failures':load_failures,'rows':rows}
        results[model]['descriptive_status_counts']=dict(collections.Counter(r['descriptive_content'].get('status') for r in complete if isinstance(r.get('descriptive_content'),dict)))
        results[model]['unknown_state_claim_fraction']=states.get('UNKNOWN',0)/sum(states.values()) if states else None
        results[model]['no_citations_count']=len(no_citations)
        results[model]['raw_validation_error_counts']=dict(collections.Counter(e for r in complete for e in set(r['validation']['raw']['errors'])))
        results[model]['normalized_validation_error_counts']=dict(collections.Counter(e for r in complete if r['validation']['normalized_body'] for e in set(r['validation']['normalized_body']['validation']['errors'])))
    common=set.intersection(*[{r['window_id'] for r in results[m]['rows'] if r['status']=='COMPLETED'} for m in results]);qv=set(r['window_id'] for r in results['qwen']['rows'] if r['status']=='COMPLETED')&set(r['window_id'] for r in results['videollama']['rows'] if r['status']=='COMPLETED')
    gt=ROOT/'artifacts/pass_t/phase2a/v2/external_returns/datasets/ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c/external_dev_gt.json';side=ROOT/'artifacts/pass_t/phase2a/v2/exhaustive_reviews/adjudicated_7e28b9edf80a8e4da88caa66/adjudicated_dev_view.json';human=ROOT/'artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/HUMAN_ADJUDICATED_CALLS.json'
    references=[]
    for r in read(gt)['records']:
        item=read(ROOT/'artifacts/pass_t/phase2a/v2/items'/r['annotation_item_id']/'item.json')
        authorized=item['authorized_half_open_frames']
        source_windows=[w for w in dataset['windows'] if w['window_id'] in item['original_pack_ids']]
        references.append({'item_id':r['annotation_item_id'],'original_pack_ids':item['original_pack_ids'],'approved_gt_source_frames_half_open':authorized,'new_selected_indices_outside_gt_authorized_scope':{w['window_id']:[f['source_frame_index'] for f in w.get('frames',[]) if not authorized[0]<=f['source_frame_index']<authorized[1]] for w in source_windows},'response_sha256':r['response_sha256'],'window_outcome':r['response']['window_outcome'],'event_types':[e['event_type'] for e in r['response']['events']],'original_evaluation':r['evaluation'],'formal_eligible':r['formal_eligible'],'quarantined':item['original_pack_ids']==['test3__W07'],'target_scope':'LOCAL_ANNOTATED_TARGET_ONLY; NOT_ALL_GENERIC_OBJECTS','exhaustiveness_sidecar_required':bool(set(item['original_pack_ids'])&{'test5__W05','test7__W05'})})
    # Human files remain blank/unreviewed in this task; no implicit import or score.
    manual_rows=list(csv.DictReader((OUT/'human_review/coverage.csv').open(encoding='utf-8-sig')))
    assert all(r['review_status']=='UNREVIEWED' for r in manual_rows),'HUMAN_SUBMISSION_PRESENT: VALIDATE_NEW_SUBMISSION_SEPARATELY'
    metrics={m:{str(t):event_metrics([],[],[],t) for t in (0,.2,.5)} for m in results}
    evaluation={'existing_gt_sources':{str(p.relative_to(ROOT)):sha(p) for p in (gt,side,human)},'existing_gt_references':references,'exhaustive_sidecar':read(side),'old_human_adjudication':read(human),'new_human_labels_created':0,'formal_event_metrics':metrics,'object_recognition_recall':None,'state_accuracy':None,'state_confusion_matrix':None,'wrong_target_event_rate':None,'physical_support_frequency':None,'reason':'Historical formal eligibility zero; target-specific sparse labels do not exhaustively annotate all generic objects; no new human state/identity/proposal adjudication.','non_exhaustive_unlisted_events':'UNEVALUATED','known_pickup_descriptive_windows':['test5__W05','test7__W05'],'no_eligible_placement_positives':True}
    changes=[p for p,h in read(OUT/'preservation_before.json').items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
    freeze=read(OUT/'dataset_freeze.json');frozen_changes=[p for p,h in {**freeze['components'],**freeze['frames']}.items() if sha(ROOT/p)!=h]
    source_video_changes=[v['video_id'] for v in dataset['videos'] if sha(Path(v['path']))!=v['sha256']]
    original_components=read(OUT/'execution_components.json')['components'];execution_changes=[p for p,h in original_components.items() if sha(ROOT/p)!=h]
    revisions=read(OUT/'execution_integration_revisions.json')['changes'] if (OUT/'execution_integration_revisions.json').exists() else []
    accounted={r['file'] for r in revisions if original_components.get(r['file'])==r['before_sha256'] and sha(ROOT/r['file'])==r['after_sha256'] and (OUT/r['error_evidence']).exists()}
    unexpected_execution_changes=[p for p in execution_changes if p not in accounted]
    pixel_groups={}
    for w in unique:pixel_groups.setdefault(tuple(f['sha256'] for f in w['frames']),[]).append(w['window_id'])
    additional_identical_visual_sequences=[v for v in pixel_groups.values() if len(v)>1]
    assert not changes and not frozen_changes and not unexpected_execution_changes and not additional_identical_visual_sequences and not source_video_changes and not integrity, {'historical':changes,'frozen':frozen_changes,'execution':unexpected_execution_changes,'duplicates':additional_identical_visual_sequences,'videos':source_video_changes,'inputs':integrity}
    save('model_results.json',results);save('event_proposals.json',{'proposals':proposals,'automatic_physical_event_deduplication':False,'reason':'Physical identity and real-event equivalence require human review; exact-input duplicate windows already removed.','authoritative_event_scores':None});save('state_claims.json',observations);save('gt_evaluation.json',evaluation)
    save('matched_inputs.json',{'all_three_completed':sorted(common),'qwen_videollama_completed':sorted(qv),'shared_source_evidence':True,'identical_internal_temporal_encoding':False,'comparison_type':'DEPLOYMENT_CONFIGURATION_COMPARISON','effective_evidence_must_be_checked_per_input_receipt':True})
    save('verification.json',{'historical_protected_files':len(read(OUT/'preservation_before.json')),'changed_historical_files':changes,'changed_frozen_dataset_or_frames':frozen_changes,'changed_source_videos':source_video_changes,'completed_input_receipts_checked':input_checks,'input_integrity_failures':integrity,'documented_execution_integration_changes':execution_changes,'unexpected_execution_component_changes':unexpected_execution_changes,'additional_identical_visual_sequences_among_unique_inputs':additional_identical_visual_sequences,'all_nine_source_timelines_covered':all(v['timeline_coverage_complete'] for v in dataset['videos']),'human_labels_invented':0,'graph_writes':0,'three_model_completed_count':len(common),'qwen_videollama_completed_count':len(qv)})
    print(json.dumps({m:{k:r[k] for k in ('completed','failed','not_executed','raw_json_parse_count','raw_strict_valid_count','event_proposal_count')} for m,r in results.items()}))
if __name__=='__main__':main()
