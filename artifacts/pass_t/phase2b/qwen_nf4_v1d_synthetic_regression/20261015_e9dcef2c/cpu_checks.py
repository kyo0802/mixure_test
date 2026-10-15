"""Minimal CPU validation on the eight new scenarios only; no VLM instance."""
import support as s
import inputs as inp
import traceback,difflib,hashlib,re,json

def demonstrate_pin_blocker():
    s.cpu_guards()
    from memory_graph.pass_t.phase2b.local_vlm.video_array_bridge import prepare_video_array
    f=next(f for f in s.read(s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json')['scenarios'] if f['representation']=='NATIVE_VIDEO_ARRAY')
    try:prepare_video_array(None,inp.envelope(f['scenario_id']),inp.deployment('NATIVE_ARRAY_EXPERIMENTAL'))
    except ValueError as error:
        assert str(error)=='V1C_HASH_CHANGED'
        s.save('BRIDGE_PIN_BLOCKER.json',{'demonstrated_error':str(error),'traceback':traceback.format_exc(),
          'source_sha256':s.sha(s.ROOT/'src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py'),
          'model_calls':0,'scope':'old bridge pins V1C, so authorized V1D cannot run video without one explicit config extension'})
        print('BRIDGE_PIN_BLOCKER_CONFIRMED',flush=True)
    else:raise RuntimeError('EXPECTED_OLD_PIN_BLOCKER_NOT_DEMONSTRATED')

def run():
    torch=s.cpu_guards()
    from transformers import AutoProcessor
    from memory_graph.pass_t.phase2b.local_vlm.nf4 import QwenNF4Runtime
    from memory_graph.pass_t.phase2b.local_vlm.video_array_bridge import tensor_record
    manifest=s.read(s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json');lock=s.read(s.OUT/'FIXTURE_LOCK_RECEIPT.json')
    assert s.sha(s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json')==lock['fixture_manifest_sha256']
    for name,h in manifest['media_assets_sha256'].items():assert s.sha(s.OUT/name)==h,name
    assert s.sha(s.OUT/'renderer.py')==manifest['renderer_sha256']
    candidate=inp.prompt_path().read_text(encoding='utf8');review=s.read(s.OUT/'PROMPT_AUTHORING_RECEIPT.json')
    assert s.sha(inp.prompt_path())==review['V1D_sha256']
    assert review['fixture_lock_unix']<review['authored_at_unix']
    assert not re.search(r'F\d{4}|S_[0-9a-f]{16}|\btest\d+\b',candidate)
    assert not re.search(r'\{\s*"',candidate)
    p=AutoProcessor.from_pretrained(s.MODEL,local_files_only=True,trust_remote_code=False,max_pixels=200704)
    obj=object.__new__(QwenNF4Runtime);obj.processor=p
    results=[];checks=[]
    def check(label,value):
        checks.append({'check':label,'passed':bool(value)})
        if not value:raise RuntimeError('CPU_CHECK_FAILED:'+label)
    for f in manifest['scenarios']:
        fid=f['scenario_id'];video=f['representation']=='NATIVE_VIDEO_ARRAY'
        obj.deployment=inp.deployment('NATIVE_ARRAY_EXPERIMENTAL' if video else 'NATIVE_VIDEO_ARRAY_DISABLED')
        env=inp.envelope(fid);batch,receipt=obj.preprocess(env)
        inp.assert_no_metadata_leak(env['payload'],receipt['rendered_prompt'])
        check(fid+'_8_consumed_aliases',receipt['processed_frame_aliases']==[f'F{i:04d}' for i in range(1,9)])
        check(fid+'_CPU_only',all(v.device.type=='cpu' for v in batch.values()))
        check(fid+'_nonempty_input_ids',batch['input_ids'].numel()>0)
        check(fid+'_pixel_budget',all(v<=200704 for vs in receipt['per_grid_spatial_pixels'].values() for v in vs))
        if video:
            check(fid+'_native_video',set(batch)=={'input_ids','attention_mask','pixel_values_videos','video_grid_thw','second_per_grid_ts'})
            check(fid+'_8to4',receipt['processor_frame_count']==8 and receipt['temporal_patch_count']==4 and receipt['temporal_padding']==0)
            check(fid+'_one_video_marker',receipt['rendered_prompt'].count('<|video_pad|>')==1 and '<|image_pad|>' not in receipt['rendered_prompt'])
            check(fid+'_new_prompt_pinned',receipt['task_prompt_sha256']==s.sha(inp.prompt_path()))
        else:
            check(fid+'_image_route',not 'video_grid_thw' in batch and 'pixel_values' in batch)
            check(fid+'_correct_image_count',receipt['rendered_prompt'].count('<|image_pad|>')==(8 if f['representation']=='MULTI_IMAGE' else 1))
        check(fid+'_no_reference',receipt['reference_image_count']==0)
        s.save(f'cpu/{fid}.json',{'scenario_id':fid,'representation':f['representation'],'receipt':receipt,
          'input_token_count':int(batch['input_ids'].shape[-1]),'tensors':{k:tensor_record(v) for k,v in batch.items()}})
        results.append({'scenario_id':fid,'representation':f['representation'],'input_tokens':int(batch['input_ids'].shape[-1])})
        print('CPU_INPUT_VERIFIED',fid,f['representation'],flush=True)
    # Versioned explicit pin rejects mismatches and unapproved non-synthetic use.
    f=next(f for f in manifest['scenarios'] if f['representation']=='NATIVE_VIDEO_ARRAY')
    for case in ['wrong_pin','not_synthetic','disabled']:
        obj.deployment=inp.deployment('NATIVE_ARRAY_EXPERIMENTAL')
        if case=='wrong_pin':obj.deployment['experimental_task_prompt_sha256']='0'*64
        if case=='not_synthetic':obj.deployment['synthetic_only']=False
        if case=='disabled':obj.deployment.pop('video_input_mode')
        try:obj.preprocess(inp.envelope(f['scenario_id']))
        except (ValueError,RuntimeError):check('reject_'+case,True)
        else:check('reject_'+case,False)
    original_env=inp.envelope(f['scenario_id'])
    original_env['payload']['instructions']=(s.REF/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt').read_text(encoding='utf8')
    obj.deployment=inp.deployment('NATIVE_ARRAY_EXPERIMENTAL')
    obj.deployment.pop('experimental_task_prompt_sha256');obj.deployment.pop('experimental_task_prompt_candidate')
    _,default_receipt=obj.preprocess(original_env)
    check('default_V1C_pin_preserved_on_new_CPU_media',default_receipt['task_prompt_sha256']==review['V1C_sha256'])
    old_bridge=(s.OUT/'bridge_before.txt').read_text(encoding='utf8');current=(s.ROOT/'src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py').read_text(encoding='utf8')
    s.save('BRIDGE_V1D_PIN_REPAIR.patch',''.join(difflib.unified_diff(old_bridge.splitlines(True),current.splitlines(True),fromfile='V1C_pinned_bridge.py',tofile='explicit_synthetic_prompt_pin_bridge.py')))
    s.save('CPU_CHECKS.json',{'checks':checks,'passed':sum(r['passed'] for r in checks),'count':len(checks),'inputs':results,
      'CUDA_initialized':torch.cuda.is_initialized(),'V1C_task_tokens':len(p.tokenizer((s.REF/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt').read_text(encoding='utf8'),add_special_tokens=False)['input_ids']),
      'V1D_task_tokens':len(p.tokenizer(candidate,add_special_tokens=False)['input_ids']),
      'token_count_scope':'exact standalone task tokenizer count, excluding schema/system/media',
      'new_fixture_leak_scan':'PASS metadata identifiers/alias literals/JSON example patterns absent; no historical model text copied',
      'pixel_paths_read':sorted(s.PIXEL_READS),'denied':s.DENIED,'V1C_unchanged':s.sha(s.REF/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt')==review['V1C_sha256']})
    print('CPU_COMPLETE',len(checks),'checks',flush=True)

if __name__=='__main__':
    import sys
    if sys.argv[1]=='probe':demonstrate_pin_blocker()
    elif sys.argv[1]=='test':run()
    else:raise RuntimeError('UNKNOWN_CPU_MODE')
