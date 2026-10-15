"""One authorized local model instance, one synthetic video smoke then fixed12 B."""
import support as s
import engineering as e
import os,time,traceback,hashlib,json,importlib.util

def verify_lock():
    lock=s.read(s.OUT/'PREREGISTRATION_LOCK_RECEIPT.json')
    assert s.sha(s.OUT/'run_manifest.json')==lock['manifest_sha256']
    manifest=s.read(s.OUT/'run_manifest.json')
    assert s.sha(s.ROOT/manifest['criteria_path'])==manifest['criteria_sha256']
    for name,h in {**manifest['source_hashes'],**manifest['input_hashes']}.items():
        if s.sha(s.ROOT/name)!=h:raise RuntimeError('EXECUTION_LOCK_HASH_MISMATCH:'+name)
    return manifest

def validation(raw,aliases):
    from memory_graph.pass_t.phase2b.predictions import parse_raw,validate_prediction,schema
    import jsonschema
    try:value=parse_raw(raw)
    except Exception as error:
        return {'JSON_SYNTAX_PASS':False,'SCHEMA_PASS':False,'SEMANTIC_PASS':None,'CITATION_PASS':None,
          'STRICT_FULL_PASS':False,'strict_result':{'valid':False,'parser_error':repr(error)},
          'violation_categories':['JSON_SYNTAX'],'event_count':None,'event_bearing':False,'known_state_applicable':False}
    strict=validate_prediction(value,aliases)
    spec=importlib.util.spec_from_file_location('existing_shadow',s.REF/'diagnostics/collect_all_prediction_violations.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    predicates=module.collect(value,aliases,schema())
    structural=list(jsonschema.Draft202012Validator(schema()).iter_errors(value))
    def stage(rows):
        if any(r['status']=='VIOLATED' for r in rows):return False
        if any(r['status']=='NOT_EVALUABLE' for r in rows):return None
        return True if any(r['status']=='SATISFIED' for r in rows) else None
    citations=[r for r in predicates if r['rule_id']=='CITATION_MEMBERSHIP']
    semantic=[r for r in predicates if not r['rule_id'].startswith('SCHEMA') and r['rule_id'] not in {'EMPTY_TIMING_UNCERTAINTY','EMPTY_WINDOW_CITATIONS','CITATION_MEMBERSHIP'}]
    events=value.get('events') if isinstance(value,dict) else None
    return {'JSON_SYNTAX_PASS':True,'SCHEMA_PASS':not structural,'SEMANTIC_PASS':stage(semantic),'CITATION_PASS':stage(citations),
      'STRICT_FULL_PASS':strict['valid'],'strict_result':strict,'predicates_diagnostic_only':predicates,
      'violation_categories':sorted({r['rule_id'] for r in predicates if r['status']=='VIOLATED'}),
      'event_count':len(events) if isinstance(events,list) else None,'event_bearing':bool(isinstance(events,list) and events),
      'known_state_applicable':any(r['rule_id']=='KNOWN_STATE_SUPPORT' and r['status'] in {'SATISFIED','VIOLATED'} for r in predicates),
      'known_state_supported':stage([r for r in predicates if r['rule_id']=='KNOWN_STATE_SUPPORT']),
      'window_outcome':value.get('window_outcome') if isinstance(value,dict) else None,
      'stage_limit':'Strict unchanged, may early-return on schema. Independent shadow stages are diagnostic, not scoring.'}

def attempt(runtime,identifier,fixture,representation,kind):
    manifest=verify_lock()
    mode='NATIVE_ARRAY_EXPERIMENTAL' if kind=='VIDEO_SMOKE' else 'NATIVE_VIDEO_ARRAY_DISABLED'
    runtime.deployment=e.deployment(mode)
    envelope=e.make_envelope(fixture,representation)
    condition_hash=hashlib.sha256(s.canon({'fixture':fixture,'representation':representation,'mode':mode,'generation':envelope['generation']})).hexdigest()
    marker={'attempt_id':identifier,'fixture':fixture,'representation':representation,'kind':kind,'video_input_mode':mode,
      'condition_hash':condition_hash,'manifest_sha256':s.sha(s.OUT/'run_manifest.json'),'started_at_unix':time.time(),'generation_retry':0}
    s.save(f'runs/{identifier}/started.json',marker)
    print('GENERATION_STARTED',identifier,fixture,representation,flush=True)
    started=time.perf_counter()
    try:result=runtime.generate(envelope)
    except Exception:
        s.save(f'runs/{identifier}/failure.json',{**marker,'error':traceback.format_exc(),'hardware':s.hardware(),
          'elapsed_s':time.perf_counter()-started,'raw_output_available':False,'no_retry_performed':True})
        raise
    raw=result.pop('raw_output').encode('utf8')
    # Raw output is durable before any schema/semantic/citation evaluation.
    raw_path=s.OUT/f'runs/{identifier}/raw_output.txt'
    raw_path.parent.mkdir(parents=True,exist_ok=True)
    with raw_path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    s.save(f'runs/{identifier}/runtime_receipt.json',result)
    if result['generation_controls']!={'max_new_tokens':1024,'do_sample':False,'max_time':300} or result['seed_applied']!=42:
        raise RuntimeError('MATERIAL_GENERATION_CONFIGURATION_MISMATCH')
    aliases=result['processed_frame_aliases']
    if aliases!=[f'F{i:04d}' for i in range(1,9)] or result['processor_frame_count']!=8:
        raise RuntimeError('MATERIAL_SOURCE_ALIAS_OR_FRAME_COUNT_MISMATCH')
    cpu_path=s.OUT/'cpu'/('video_'+fixture+'.json' if kind=='VIDEO_SMOKE' else fixture+'_'+representation+'.json')
    cpu=s.read(cpu_path)
    if kind=='VIDEO_SMOKE':
        if not result.get('native_video_modality') or result['video_input_mode']!=mode or result['temporal_patch_count']!=4:
            raise RuntimeError('NATIVE_VIDEO_ROUTE_NOT_PROVEN')
        for k,record in cpu['video_receipt']['tensor_records'].items():
            if result['tensor_records'][k]['canonical_sha256']!=record['canonical_sha256']:
                raise RuntimeError('GPU_SMOKE_PREPROCESS_TENSOR_MISMATCH:'+k)
    elif result['rendered_prompt_sha256']!=cpu['receipt']['rendered_prompt_sha256']:
        raise RuntimeError('VARIANT_B_SERIALIZED_PROMPT_MISMATCH')
    checks=validation(raw,aliases)
    receipt={**marker,'raw_output_sha256':s.sha(raw_path),'raw_output_bytes':len(raw),'generation_completed':True,
      'nonempty_raw_output':bool(raw.strip()),'validation':checks,'runtime_receipt_path':f'runs/{identifier}/runtime_receipt.json',
      'runtime_receipt_sha256':s.sha(s.OUT/f'runs/{identifier}/runtime_receipt.json'),'elapsed_s':time.perf_counter()-started,
      'hardware_after':s.hardware(),'real_DEV_pixel_reads':0,'inference_on_real_Phase2a':False}
    s.save(f'runs/{identifier}/completed.json',receipt)
    print('GENERATION_COMPLETE',identifier,'strict=',checks['STRICT_FULL_PASS'],'events=',checks['event_count'],
          'seconds=',round(result['runtime_seconds'],2),flush=True)
    return receipt

def main():
    manifest=verify_lock();s.authorities()
    os.environ.pop('CUDA_VISIBLE_DEVICES',None)
    os.environ['PASS_T_LOCAL_RUNTIME_APPROVAL']='true'
    os.environ.pop('PASS_T_PHASE2B_REAL_RUN_PERMISSION',None)
    import torch,psutil
    from memory_graph.pass_t.phase2b.local_vlm.nf4 import QwenNF4Runtime
    from memory_graph.pass_t.phase2b.local_vlm.catalog import SPECS
    before=s.hardware()
    if torch.cuda.mem_get_info()[0]<10*2**30 or psutil.virtual_memory().available<8*2**30:
        raise RuntimeError('LOAD_RESOURCE_HEADROOM_BLOCKED')
    s.save('MODEL_LOAD_STARTED.json',{'started_at_unix':time.time(),'hardware_before':before,'manifest_sha256':s.sha(s.OUT/'run_manifest.json')})
    runtime=QwenNF4Runtime(SPECS['qwen_nf4'],e.deployment(),s.MODEL,{})
    s.save('MODEL_LOADED.json',{'health':runtime.health(),'hardware_after':s.hardware(),
      'load_reserved_peak_bytes':torch.cuda.max_memory_reserved(),'single_instance':True})
    smoke=attempt(runtime,'VIDEO_SMOKE_001',manifest['smoke']['fixture'],'NATIVE_VIDEO_ARRAY','VIDEO_SMOKE')
    if not smoke['nonempty_raw_output']:
        raise RuntimeError('VIDEO_SMOKE_EMPTY_OUTPUT_NO_OUTPUT_BASED_RETRY')
    s.save('VIDEO_SMOKE_RESULT.json',{'engineering_pass':True,'attempts':1,'strict_valid':smoke['validation']['STRICT_FULL_PASS'],
      'nonempty_raw_output':True,'actual_model_forward_and_generation_completed':True,'frame_alias_grounding_not_proven':True,
      'actual_model_temporal_ids':'NOT_INSTRUMENTED','representation_status':'FRAME_MATCHED_ONLY'})
    # Answer-independent switch to OFF. No new warmup, model reload or settings changes.
    for i,row in enumerate(manifest['original_B_order'],1):
        rep={'MULTI_IMAGE_8':'MULTI_IMAGE','STORYBOARD_8':'STORYBOARD'}[row['representation']]
        attempt(runtime,f'B_{i:02d}',row['fixture_id'],rep,'VARIANT_B')
    s.save('GPU_EXECUTION_COMPLETE.json',{'smoke_generations':1,'variant_B_generations':12,
      'all_scheduled_completed':True,'pixel_paths_read':sorted(s.PIXEL_READS),'denied_accesses':s.DENIED,
      'real_DEV_imagery_read':False,'protocol_frozen':False,'Memory_Graph_write':False,'runtime_mutations_during_B':False})
    del runtime
    torch.cuda.empty_cache()
    s.save('MODEL_UNLOADED.json',{'hardware':s.hardware(),'owned_runtime_deleted':True})

if __name__=='__main__':
    try:main()
    except Exception:
        error=traceback.format_exc()
        s.save('GPU_FATAL_ERROR.json',{'error':error,'denied':s.DENIED,'pixel_paths_read':sorted(s.PIXEL_READS),'hardware':s.hardware()})
        print(error,flush=True)
        raise
