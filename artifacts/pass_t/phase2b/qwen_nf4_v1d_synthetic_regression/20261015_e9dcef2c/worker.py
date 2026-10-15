"""Exactly eight fixed serial synthetic conditions, one NF4 model instance."""
import support as s
import inputs as inp
import os,time,hashlib,traceback,importlib.util

def verify_lock():
    lock=s.read(s.OUT/'EXECUTION_LOCK_RECEIPT.json');path=s.OUT/'V1D_PREREGISTERED_EXECUTION_MANIFEST.json'
    assert s.sha(path)==lock['manifest_sha256']
    manifest=s.read(path)
    assert s.sha(s.OUT/'V1D_PREREGISTERED_CRITERIA.md')==manifest['criteria_sha256']
    for name,h in {**manifest['source_sha256'],**manifest['CPU_receipt_sha256']}.items():
        if s.sha(s.ROOT/name)!=h:raise RuntimeError('LOCKED_SOURCE_HASH_MISMATCH:'+name)
    for name,h in manifest['media_sha256'].items():
        if s.sha(s.OUT/name)!=h:raise RuntimeError('LOCKED_FIXTURE_HASH_MISMATCH:'+name)
    assert s.sha(inp.prompt_path())==manifest['prompt_sha256']
    return manifest

def validate(raw,aliases):
    from memory_graph.pass_t.phase2b.predictions import parse_raw,validate_prediction,schema
    import jsonschema
    try:value=parse_raw(raw)
    except Exception as error:
        return {'JSON_SYNTAX_PASS':False,'SCHEMA_PASS':False,'SEMANTIC_PASS':None,'CITATION_PASS':None,'STRICT_FULL_PASS':False,
          'strict':{'valid':False,'parser_error':repr(error)},'categories':['JSON_SYNTAX'],'event_count':None,'event_bearing':False,
          'timing_uncertainty_strings':[],'global_uncertainty':None,'window_citations':None,'targeted_violations':'NOT_EVALUABLE_DUE_TO_PARSE_FAILURE'}
    sch=schema();strict=validate_prediction(value,aliases)
    errors=list(jsonschema.Draft202012Validator(sch).iter_errors(value))
    spec=importlib.util.spec_from_file_location('existing_shadow',s.REF/'diagnostics/collect_all_prediction_violations.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    predicates=mod.collect(value,aliases,sch)
    def stage(rows):
        if any(r['status']=='VIOLATED' for r in rows):return False
        if any(r['status']=='NOT_EVALUABLE' for r in rows):return None
        return True if any(r['status']=='SATISFIED' for r in rows) else None
    events=value.get('events');events=events if isinstance(events,list) else []
    timing=[event.get('timing_uncertainty') for event in events if isinstance(event,dict)]
    timing_bad=sum(not isinstance(x,str) or len(x)<1 for x in timing)+sum(not isinstance(x,dict) for x in events)
    global_value=value.get('uncertainty');window=value.get('window_cited_frame_aliases')
    global_bad=not isinstance(global_value,str) or len(global_value)<1
    window_bad=not jsonschema.Draft202012Validator(sch['properties']['window_cited_frame_aliases']).is_valid(window)
    member_ok=isinstance(window,list) and all(isinstance(x,str) and x in aliases for x in window)
    schema_findings=[{'path':'/'+ '/'.join(map(str,error.absolute_path)),'validator':error.validator,'message':error.message} for error in errors]
    return {'JSON_SYNTAX_PASS':True,'SCHEMA_PASS':not errors,'STRICT_FULL_PASS':strict['valid'],'strict':strict,
      'SEMANTIC_PASS':stage([r for r in predicates if not r['rule_id'].startswith('SCHEMA') and r['rule_id'] not in {'EMPTY_TIMING_UNCERTAINTY','EMPTY_WINDOW_CITATIONS','CITATION_MEMBERSHIP'}]),
      'CITATION_PASS':stage([r for r in predicates if r['rule_id']=='CITATION_MEMBERSHIP']),
      'schema_errors':schema_findings,'shadow_diagnostic_only':predicates,'categories':sorted({r['rule_id'] for r in predicates if r['status']=='VIOLATED'}),
      'event_count':len(events),'event_bearing':bool(events),'timing_uncertainty_strings':timing,
      'distinct_timing_uncertainty_strings':list(dict.fromkeys(x for x in timing if isinstance(x,str))),
      'global_uncertainty':global_value,'global_uncertainty_present':'uncertainty' in value,
      'window_citations':window,'window_citations_nonempty':isinstance(window,list) and bool(window),'window_citation_membership':member_ok,
      'targeted_violations':{'event_timing_entries':timing_bad,'global_uncertainty':int(global_bad),'window_citations':int(window_bad or not member_ok)},
      'known_state_applicable':any(r['rule_id']=='KNOWN_STATE_SUPPORT' and r['status'] in {'VIOLATED','SATISFIED'} for r in predicates),
      'window_outcome':value.get('window_outcome'),
      'visual_warning_screening':{'precision':'UNREVIEWED','target_continuity':'UNREVIEWED','citation_evidential_meaning':'UNREVIEWED'},
      'stage_scope':'semantic and membership shadow diagnostics do not override authoritative structural early-return'}

def attempt(runtime,entry,index):
    manifest=verify_lock();fid=entry['scenario_id'];f=inp.fixture(fid);rep=f['representation'];video=rep=='NATIVE_VIDEO_ARRAY'
    mode='NATIVE_ARRAY_EXPERIMENTAL' if video else 'NATIVE_VIDEO_ARRAY_DISABLED'
    runtime.deployment=inp.deployment(mode)
    envelope=inp.envelope(fid)
    aid=f'R{index:02d}_{entry["condition_id"]}'
    marker={'attempt_id':aid,'scenario_id':fid,'condition_id':entry['condition_id'],'representation':rep,'video_input_mode':mode,
      'started_at_unix':time.time(),'generation_retry':0,'prompt_sha256':manifest['prompt_sha256'],
      'execution_manifest_sha256':s.sha(s.OUT/'V1D_PREREGISTERED_EXECUTION_MANIFEST.json')}
    s.save(f'runs/{aid}/started.json',marker)
    print('GENERATION_STARTED',aid,fid,rep,flush=True)
    began=time.perf_counter()
    try:result=runtime.generate(envelope)
    except Exception:
        s.save(f'runs/{aid}/failure.json',{**marker,'error':traceback.format_exc(),'raw_available':False,
          'actual_generation_entry':'UNDETERMINED_FROM_EXCEPTION, not counted as completed','hardware':s.hardware()})
        raise
    raw=result.pop('raw_output').encode('utf8')
    raw_path=s.OUT/f'runs/{aid}/raw_output.txt'
    with raw_path.open('xb') as handle:handle.write(raw);handle.flush();os.fsync(handle.fileno())
    s.save(f'runs/{aid}/runtime_receipt.json',result)
    inp.assert_no_metadata_leak(envelope['payload'],result['rendered_prompt'])
    if result['generation_controls']!=manifest['generation_effective_expected'] or result['seed_applied']!=42:
        raise RuntimeError('EFFECTIVE_GENERATION_CONFIGURATION_MISMATCH')
    cpu=s.read(s.OUT/f'cpu/{fid}.json')
    assert result['rendered_prompt_sha256']==cpu['receipt']['rendered_prompt_sha256']
    assert result['processed_frame_aliases']==[f'F{i:04d}' for i in range(1,9)] and result['processor_frame_count']==8
    if video:
        assert result['video_input_mode']==mode and result['native_video_modality'] and result['temporal_patch_count']==4
        for key,row in result['tensor_records'].items():assert row['canonical_sha256']==cpu['tensors'][key]['canonical_sha256']
        assert result['task_prompt_sha256']==manifest['prompt_sha256']
    checks=validate(raw,result['processed_frame_aliases'])
    record={**marker,'completed_generation':True,'raw_response_sha256':s.sha(raw_path),'raw_response_bytes':len(raw),
      'runtime_receipt_sha256':s.sha(s.OUT/f'runs/{aid}/runtime_receipt.json'),'validation':checks,
      'end_to_end_seconds':time.perf_counter()-began,'hardware_after':s.hardware(),'real_DEV_image_reads':0}
    s.save(f'runs/{aid}/completed.json',record)
    print('GENERATION_COMPLETED',aid,'strict=',checks['STRICT_FULL_PASS'],'events=',checks['event_count'],'seconds=',round(result['runtime_seconds'],2),flush=True)

def main():
    manifest=verify_lock();os.environ.pop('CUDA_VISIBLE_DEVICES',None)
    os.environ['PASS_T_LOCAL_RUNTIME_APPROVAL']='true';os.environ.pop('PASS_T_PHASE2B_REAL_RUN_PERMISSION',None)
    import torch,psutil
    from memory_graph.pass_t.phase2b.local_vlm.nf4 import QwenNF4Runtime
    from memory_graph.pass_t.phase2b.local_vlm.catalog import SPECS
    if torch.cuda.mem_get_info()[0]<10*2**30 or psutil.virtual_memory().available<8*2**30:raise RuntimeError('LOAD_RESOURCE_HEADROOM_BLOCKED')
    s.save('MODEL_LOAD_STARTED.json',{'started_at_unix':time.time(),'hardware':s.hardware()})
    runtime=QwenNF4Runtime(SPECS['qwen_nf4'],inp.deployment(),s.MODEL,{})
    s.save('MODEL_LOADED.json',{'health':runtime.health(),'hardware':s.hardware(),'load_peak_reserved_bytes':torch.cuda.max_memory_reserved(),'model_instances':1})
    for i,entry in enumerate(manifest['order'],1):attempt(runtime,entry,i)
    s.save('GPU_EXECUTION_COMPLETE.json',{'completed_calls':8,'planned_calls':8,'warmups':0,'retries':0,'extra_calls':0,
      'pixel_paths_read':sorted(s.PIXEL_READS),'denied':s.DENIED,'real_DEV_image_reads':0,'source_mutations_during_execution':False,
      'protocol_frozen':False,'Graph_writes':0,'V1E_created':False})
    del runtime;torch.cuda.empty_cache()
    s.save('MODEL_UNLOADED.json',{'hardware':s.hardware(),'owned_model_deleted':True})

if __name__=='__main__':
    try:main()
    except Exception:
        error=traceback.format_exc();s.save('GPU_FATAL_ERROR.json',{'error':error,'denied':s.DENIED,'pixel_paths_read':sorted(s.PIXEL_READS),
          'hardware':s.hardware(),'no_repair_or_retry_performed':True})
        print(error,flush=True);raise
