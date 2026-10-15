"""Sequential CPU preparation and immutable preregistration; no GPU calls."""
import support as s
import sys,traceback
import json,hashlib,base64,io,math,difflib,importlib.util

def make_envelope(fixture,representation):
    from PIL import Image
    import numpy as np
    f=s.read(s.OUT/'inputs'/fixture/'fixture.json')
    prompt=(s.REF/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt').read_text(encoding='utf8')
    payload={'schema_version':'PASS_T_PHASE2B_MODEL_PAYLOAD_V1','request_id':'REQ_'+hashlib.sha256((fixture+representation).encode()).hexdigest()[:20],
      'target':{'opaque_id':'TARGET_A','description':'the designated object in supplied bounded media'},
      'ontology':{'event_types':['PICKUP','PLACEMENT'],'window_outcomes':['CONFIRMED_EVENTS','NO_CONFIRMED_EVENT','INSUFFICIENT_EVIDENCE','TARGET_NOT_OBSERVABLE']},
      'representation':representation,'media':[],'instructions':prompt,'output_contract':'PASS_T_PHASE2B_PREDICTION_V1'}
    envelope={'payload':payload,'generation':{'max_output_tokens':1024,'sampling':False,'seed':42},'media':[]}
    aliases=[r['opaque_alias'] for r in f['frames']]
    if representation=='NATIVE_VIDEO_ARRAY':
        images=[]
        for r in f['frames']:
            with Image.open(s.OUT/'inputs'/fixture/r['filename']) as im:images.append(np.asarray(im.convert('RGB')).copy())
        envelope['native_video_array']={'frames':np.stack(images),'aliases':aliases,
          'native_pts_s':[r['synthetic_timestamp_s'] for r in f['frames']],
          'source_rgb_sha256':[r['rgb_sha256'] for r in f['frames']]}
    else:
        paths=[s.OUT/'inputs'/fixture/r['filename'] for r in f['frames']] if representation=='MULTI_IMAGE' else [s.OUT/'inputs'/fixture/'STORYBOARD.png']
        for i,p in enumerate(paths):
            row={'media_id':f'MEDIA_{i+1:03d}','media_type':'image/png','content_sha256':s.sha(p),
              'supplied_frame_aliases':[aliases[i]] if representation=='MULTI_IMAGE' else aliases}
            payload['media'].append(row)
            envelope['media'].append({'media_id':row['media_id'],'base64':base64.b64encode(p.read_bytes()).decode()})
    return envelope

def deployment(mode='NATIVE_VIDEO_ARRAY_DISABLED'):
    return {'approved':True,'synthetic_only':True,'processor_max_pixels':200704,'generation_timeout_seconds':300,
      'response_format_system':(s.REF/'prompt_candidate/v2_system_unchanged.txt').read_text(encoding='utf8'),
      'asset_audit_path':str(s.OUT/'model_assets.json'),'scratch_path':str(s.OUT/'scratch'),
      'video_input_mode':mode,'identity_clause_enabled':False}

def cpu():
    manifest=s.authorities()
    torch=s.cpu_guards()
    import numpy as np
    from PIL import Image,ImageDraw,ImageFont
    from transformers import AutoProcessor
    from transformers.video_utils import VideoMetadata
    from memory_graph.pass_t.phase2b.local_vlm.nf4 import QwenNF4Runtime
    from memory_graph.pass_t.phase2b.local_vlm.video_array_bridge import tensor_record,static_timeline
    from memory_graph.pass_t.phase2b.predictions import schema
    p=AutoProcessor.from_pretrained(s.MODEL,local_files_only=True,trust_remote_code=False,max_pixels=200704)
    for c in [p.image_processor,p.video_processor]:c.size={'shortest_edge':3136,'longest_edge':200704};c.min_pixels=3136;c.max_pixels=200704
    obj=object.__new__(QwenNF4Runtime);obj.processor=p;obj.deployment=deployment('NATIVE_ARRAY_EXPERIMENTAL')
    results=[];tests=[]
    def check(name,condition):
        tests.append({'test':name,'pass':bool(condition)})
        if not condition:raise RuntimeError('CPU_CHECK_FAILED:'+name)
    for fixture in manifest['scenarios']:
        fid=fixture['fixture_id'];folder=s.OUT/'inputs'/fid;folder.mkdir(parents=True,exist_ok=False)
        frames=[];images=[]
        for i,row in enumerate(fixture['frames']):
            raw=(s.REF/row['path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==row['file_sha256']
            path=folder/f'F{i+1:04d}.png'
            with path.open('xb') as f:f.write(raw)
            with Image.open(path) as im:images.append(im.convert('RGB'))
            frames.append({**row,'filename':path.name,'rgb_sha256':hashlib.sha256(images[-1].tobytes()).hexdigest()})
        width,height=images[0].size;cell=480;scaled=round(height*cell/width);label=32
        board=Image.new('RGB',(1440,3*(scaled+label)),'white');draw=ImageDraw.Draw(board)
        for i,(im,row) in enumerate(zip(images,frames)):
            x=(i%3)*cell;y=(i//3)*(scaled+label)
            board.paste(im.resize((cell,scaled),Image.Resampling.LANCZOS),(x,y+label))
            draw.text((x+8,y+8),row['opaque_alias'],fill='black',font=ImageFont.load_default())
        board.save(folder/'STORYBOARD.png',format='PNG',optimize=False)
        s.save(f'inputs/{fid}/fixture.json',{'fixture_id':fid,'intended_stratum':fixture['intended_stratum'],'frames':frames,
          'new_fixture':False,'source_manifest_sha256':s.sha(s.REF/'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json')})
        old=s.read(s.REF/'private_mappings'/f'{fid}.json')
        check(fid+'_storyboard_exact_source_hash',s.sha(folder/'STORYBOARD.png')==old['storyboard_sha256'])
        e=make_envelope(fid,'NATIVE_VIDEO_ARRAY');batch,r=obj.preprocess(e)
        aliases=e['native_video_array']['aliases'];array=e['native_video_array']['frames'];pts=e['native_video_array']['native_pts_s']
        system=deployment()['response_format_system'];prompt=e['payload']['instructions']
        messages=[{'role':'system','content':[{'type':'text','text':system}]},{'role':'user','content':[
          {'type':'text','text':'Supplied aliases: '+', '.join(aliases)},{'type':'video'},
          {'type':'text','text':prompt+'\nRequired JSON schema:\n'+json.dumps(schema())}]}]
        rendered=p.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
        reference=p(text=[rendered],videos=[array],video_metadata=[VideoMetadata(total_num_frames=8,fps=r['processor_fps'],duration=8/r['processor_fps'])],
          fps=r['processor_fps'],do_sample_frames=False,return_tensors='pt',return_metadata=False,device='cpu')
        comparisons={}
        for key in batch:
            comparisons[key]={'reference':tensor_record(reference[key]),'actual':tensor_record(batch[key]),
              'elementwise_equal':bool(torch.equal(reference[key],batch[key])),
              'max_abs_difference':float((reference[key].to(torch.float64)-batch[key].to(torch.float64)).abs().max())}
        check(fid+'_all_five_tensor_values_equal',all(v['elementwise_equal'] and v['max_abs_difference']==0 for v in comparisons.values()) and len(comparisons)==5)
        check(fid+'_old_pixel_tensor_hash_equal',tensor_record(batch['pixel_values_videos'])['raw_le_c_sha256']==old['budgets']['VIDEO']['pixel_tensor_sha256'])
        check(fid+'_rendered_exact_original',rendered==(s.REF/'model_visible/matched8_native_array'/fid/'rendered_VIDEO.txt').read_text(encoding='utf8'))
        check(fid+'_eight_frame_rgb_order',r['source_rgb_sha256']==old['frame_array_observer']['accepted_frame_rgb_sha256'])
        check(fid+'_four_units',batch['video_grid_thw'][0,0].item()==4 and r['temporal_padding']==0)
        check(fid+'_old_time_metadata',batch['second_per_grid_ts'].tolist()==old['budgets']['VIDEO']['second_per_grid_ts'])
        check(fid+'_hash_deterministic',tensor_record(batch['input_ids'])==tensor_record(batch['input_ids'].clone()))
        # Negative tests use only the locked warmup and never generate.
        if fixture['intended_stratum']=='WARMUP':
            for mode,err in [('NATIVE_VIDEO_ARRAY_DISABLED','disabled'),('AUTO','unknown')]:
                obj.deployment=deployment(mode)
                rejected=False
                try:obj.preprocess(e)
                except (ValueError,RuntimeError):rejected=True
                check('reject_'+err,rejected)
            obj.deployment=deployment('NATIVE_ARRAY_EXPERIMENTAL')
            for change in ['hash','alias','frame_count','pts']:
                bad=make_envelope(fid,'NATIVE_VIDEO_ARRAY')
                if change=='hash':bad['native_video_array']['source_rgb_sha256'][0]='0'*64
                if change=='alias':bad['native_video_array']['aliases'][1]='F0001'
                if change=='frame_count':bad['native_video_array']['frames']=bad['native_video_array']['frames'][:7]
                if change=='pts':bad['native_video_array']['native_pts_s'][1]=bad['native_video_array']['native_pts_s'][0]
                rejected=False
                try:obj.preprocess(bad)
                except (ValueError,RuntimeError):rejected=True
                check('reject_'+change,rejected)
        result={'fixture':fid,'kind':fixture['intended_stratum'],'video_receipt':r,'tensor_parity':comparisons,
          'historical_tensor_hash_format':'raw numpy C bytes, not new TENSOR_LE_C_V1 header hash; raw pixel digest matches',
          'historical_input_ids':'reconstructed direct CPU reference; historical tensor dump not available',
          'CPU_only':True,'cuda_initialized':torch.cuda.is_initialized()}
        results.append(result)
        s.save(f'cpu/video_{fid}.json',result)
        obj.deployment=deployment('NATIVE_VIDEO_ARRAY_DISABLED')
        if fixture['intended_stratum']!='WARMUP':
            for rep in ['MULTI_IMAGE','STORYBOARD']:
                inputs,receipt=obj.preprocess(make_envelope(fid,rep))
                oldbudget=old['budgets'][rep]
                check(fid+'_'+rep+'_old_pixel_parity',tensor_record(inputs['pixel_values'])['raw_le_c_sha256']==oldbudget['pixel_tensor_sha256'])
                check(fid+'_'+rep+'_rendered_parity',receipt['rendered_prompt']==(s.REF/'model_visible/matched8_native_array'/fid/f'rendered_{rep}.txt').read_text(encoding='utf8'))
                s.save(f'cpu/{fid}_{rep}.json',{'input_tokens':int(inputs['input_ids'].numel()),'receipt':receipt,
                   'tensors':{k:tensor_record(v) for k,v in inputs.items()},'mode':'NATIVE_VIDEO_ARRAY_DISABLED'})
        obj.deployment=deployment('NATIVE_ARRAY_EXPERIMENTAL')
        print('CPU_PASS',fid,'8->4','source_model_ids',[r['static_timeline'][i]['static_relative_model_temporal_id'] for i in range(0,8,2)],flush=True)
    check('source_faithful_integer_before_multiply', [r['static_relative_model_temporal_id'] for r in static_timeline([f'F{i:04d}' for i in range(1,9)],list(range(8)),1.,.99)]==[0]*8)
    check('canonical_hash_layout_independent',tensor_record(torch.arange(12).reshape(3,4).T)['canonical_sha256']==tensor_record(torch.arange(12).reshape(3,4).T.contiguous())['canonical_sha256'])
    check('CPU_no_CUDA',not torch.cuda.is_initialized())
    s.save('CPU_CHECKS.json',{'tests':tests,'count':len(tests),'passed':sum(t['pass'] for t in tests),
      'synthetic_sequences':7,'real_DEV_pixel_reads':0,'guard_denials':s.DENIED,'pixel_paths_read':sorted(s.PIXEL_READS),
      'generation_calls':0,'CUDA_initialized':torch.cuda.is_initialized()})
    print('CPU_COMPLETE',len(tests),'checks',flush=True)

def final_cpu_gate():
    # Recheck negative assertions after source review; no preprocessing replay,
    # no additional fixture construction and no model instance.
    s.authorities();torch=s.cpu_guards()
    from memory_graph.pass_t.phase2b.local_vlm.nf4 import QwenNF4Runtime
    obj=object.__new__(QwenNF4Runtime)
    fixture=s.read(s.REF/'regression_preregistration.json')['warmup_fixture']
    tests=[]
    for key in ['disabled','unknown','hash','alias','frame_count','pts']:
        obj.deployment=deployment('NATIVE_ARRAY_EXPERIMENTAL');env=make_envelope(fixture,'NATIVE_VIDEO_ARRAY')
        if key=='disabled':obj.deployment=deployment()
        if key=='unknown':obj.deployment=deployment('AUTO')
        if key=='hash':env['native_video_array']['source_rgb_sha256'][0]='0'*64
        if key=='alias':env['native_video_array']['aliases'][1]='F0001'
        if key=='frame_count':env['native_video_array']['frames']=env['native_video_array']['frames'][:7]
        if key=='pts':env['native_video_array']['native_pts_s'][1]=env['native_video_array']['native_pts_s'][0]
        # The bridge validates all these cases before using processor.
        obj.processor=None
        try:obj.preprocess(env)
        except (ValueError,RuntimeError):tests.append({'case':key,'rejected_before_processor':True})
        else:raise RuntimeError('FINAL_NEGATIVE_GUARD_FAILED:'+key)
    s.save('FINAL_CPU_GATE.json',{'checks':tests,'passed':len(tests),'cpu_only':True,'cuda_initialized':torch.cuda.is_initialized(),
      'source_hashes':{str(p.relative_to(s.ROOT)):s.sha(p) for p in [s.OUT/'engineering.py',s.ROOT/'src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py']},
      'scope':'Six reviewed negative assertions repeated; not six additional unique tests.'})
    print('FINAL_CPU_GATE_PASS',len(tests),flush=True)

def lock():
    s.authorities()
    cpu=s.read(s.OUT/'CPU_CHECKS.json');assert cpu['count']==cpu['passed'] and not cpu['CUDA_initialized']
    assert s.read(s.OUT/'FINAL_CPU_GATE.json')['passed']==6
    old=s.read(s.REF/'regression_preregistration.json')
    assert len(old['variant_b_order'])==12 and old['generation']=={'do_sample':False,'max_new_tokens':1024,'seed':42}
    assets=s.read(s.OUT/'model_assets.json')
    assert assets['model']=='Qwen/Qwen2.5-VL-7B-Instruct' and assets['revision']=='cc594898137f460bfe9f0759e9844b3ce807cfb5'
    for name,h in assets['files_sha256'].items():
        if s.sha(s.MODEL/name)!=h:raise RuntimeError('LOCAL_MODEL_ASSET_CHANGED:'+name)
    before=s.read(s.OUT/'BEFORE.json');allowed='src/memory_graph/pass_t/phase2b/local_vlm/nf4.py'
    for name,h in before['files'].items():
        if name!=allowed and s.sha(s.ROOT/name)!=h:raise RuntimeError('PROTECTED_SOURCE_CHANGED:'+name)
    old_source=(s.OUT/'historical_source/nf4_original_bytes.dat').read_bytes().decode('utf8')
    new_source=(s.ROOT/allowed).read_text(encoding='utf8')
    s.save('runtime_changes.diff',''.join(difflib.unified_diff(old_source.splitlines(True),new_source.splitlines(True),fromfile='historical/nf4.py',tofile='src/memory_graph/pass_t/phase2b/local_vlm/nf4.py')))
    sources={p.relative_to(s.ROOT).as_posix():s.sha(p) for p in (s.ROOT/'src/memory_graph/pass_t/phase2b').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for p in s.OUT.glob('*.py'):sources[p.relative_to(s.ROOT).as_posix()]=s.sha(p)
    for name in ['processor_source_inventory.json','SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json','SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json',
      'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt','prompt_candidate/v2_system_unchanged.txt','regression_preregistration.json']:
        p=s.REF/name;sources[p.relative_to(s.ROOT).as_posix()]=s.sha(p)
    inventory={p.relative_to(s.ROOT).as_posix():s.sha(p) for p in (s.OUT/'inputs').rglob('*') if p.is_file()}
    manifest={'task':'QWEN_NF4_ENGINEERING_CLOSEOUT_SYNTHETIC_ONLY','model_assets':assets,
      'prompt_status':'APPROVED_FOR_SYNTHETIC_REGRESSION_CANDIDATE_ONLY','identity_clause_enabled':False,
      'source_hashes':sources,'input_hashes':inventory,'original_B_order':old['variant_b_order'],
      'original_preregistration_sha256':s.sha(s.REF/'regression_preregistration.json'),
      'coverage':{'per_representation_event_bearing_min':2,'per_representation_known_state_applicable_min':1,'pooled_event_bearing_min':4,
        'authority':'Original Markdown explicitly defines Variant B 4/12; old JSON pooled6 applies to 18-call A, not B.'},
      'generation':old['generation'],'timeouts_s':{'load':120,'generation':300,'request':330,'whole_process':4500},
      'resource_limits':{'global_gpu_used_gib':14.5,'owned_process_tree_rss_gib':20,'load_free_gpu_gib':10,'load_free_ram_gib':8,
        'generation_free_gpu_gib':2,'system_ram_available_hard_floor_gib':2,'monitor_interval_s':1},
      'smoke':{'fixture':old['warmup_fixture'],'initial_calls':1,'technical_repair_extra_max':1,
        'mode':'NATIVE_ARRAY_EXPERIMENTAL','acceptance':'load + native video tensors + completed generation + no OOM + preserved nonempty raw; strict validity separate'},
      'variant_B':{'planned_calls':12,'generation_retry':0,'warmup_calls':0,'optional_repeat_calls':0,'mode':'NATIVE_VIDEO_ARRAY_DISABLED'},
      'classification':{'REGRESSION_PASS':'all12 strict pass AND coverage', 'STRUCTURAL_PASS_COVERAGE_INSUFFICIENT':'all12 strict pass but coverage absent',
        'REGRESSION_FAIL':'any completed strict output fails','REGRESSION_INCOMPLETE':'scheduled matrix prevented by safety/runtime/integrity'},
      'warnings':{'strict_pass_below':10,'same_violation_min_distinct_attempts':3,'low_event_or_known_state_coverage':True,
        'all_zero_event_or_abstention':True,'missing_EOS_citation_or_temporal_evidence':True},
      'processor':{'transformers':'4.57.6','max_pixels':200704,'min_pixels':3136,'temporal_patch_size':2,'merge_size':2,'patch_size':14,
        'storyboard':{'columns':3,'cell_width':480,'scaled_height':270,'label_height':32,'canvas':[1440,906]},
        'video':{'fps':'7/(synthetic_pts[7]-synthetic_pts[0])','do_sample_frames':False,'return_metadata':False,'status':'FRAME_MATCHED_ONLY'}},
      'no_real_DEV_images':True,'protocol_frozen':False,'Phase2a_pilot':False,'Variant_A':False}
    manifest['CPU_preprocessing_receipt_hashes']={p.relative_to(s.ROOT).as_posix():s.sha(p) for p in (s.OUT/'cpu').glob('*.json')}
    manifest['processor_configuration_sha256']=hashlib.sha256(s.canon(manifest['processor'])).hexdigest()
    text='''# Preregistered Qwen NF4 engineering closeout criteria

This execution lock is NOT a human research Protocol Freeze. Scope: one separate locked synthetic warmup Video Array smoke (at most one additional only after a logged technical repair), then exactly 12 original-order Variant B calls. No additional warmups/repeats. No real DEV imagery/inference.

## Fixed authority and execution

Six locked evaluation fixtures (two intended zero/one/two events) and the independent original warmup; lock receipt SHA 149f8696e51fa91cf43147d761315672dc43594aebe41b58cea8ed78956346ee. V1C SHA 3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722, synthetic candidate only; identity clause NOT_APPROVED_NOT_ENABLED. Local original revision cc594898137f460bfe9f0759e9844b3ce807cfb5, NF4 double 4-bit BF16 SDPA, one model instance serial execution. Immutable manifest below contains exact asset/source/config/order hashes.

Image max_pixels200704/min3136; 8 full source images. Storyboard 3 columns of480x270 plus32alias strip,1440x906 globally resized to same per-input cap; budgets are not equal information. Video8 native arrays, temporal patch2 ->4units, FRAME_MATCHED_ONLY. Flag OFF for Variant B. No reference. do_sample=false, seed42, max_new_tokens1024, repeat1, generation retry0; inactive temperature not forced.

Load120s, generation300s, request330s, whole4500s. Global GPU used14.5GiB, owned treeRSS20GiB; loadfreeGPU10GiB/RAM8GiB, generationfreeGPU2GiB, system availableRAM hard floor2GiB. Supervisor samples1s nominal, includes complete owned process tree; sampling is not continuous/global mathematical peak.

## Hard stops (immutable before first generation)

Stop immediately for: (1) protected artifact/source hash mismatch; (2) unapproved prompt/schema/Validator modification; (3) attempt to access real Phase2a DEV video/frame; (4) inability to identify exact locked fixture; (5) CUDA OOM or unrecoverable runtime crash that cannot safely recover under smoke allowance; (6) unsafe resource utilization; (7) material actual-versus-preregistered input/generation/validation mismatch; (8) missing/invalid research-critical raw receipts preventing trustworthy continuation. Strict JSON failure alone never authorizes prompt alteration or rerun. No evolving pass-count early-stop rule.

## Classification and branch coverage

All12 mandatory strict outputs must pass authoritative parser/schema/semantic/citation. Each representation requires >=2/6 model-emitted event-bearing attempts and >=1/6 known-state support applicable; pooled >=4/12 event-bearing per the existing explicit Variant B Markdown criterion. This is independent of A's pooled6/18 JSON entry. Do not manufacture events. REGRESSION_PASS=allstrict+coverage; STRUCTURAL_PASS_COVERAGE_INSUFFICIENT=allstrict but inadequatecoverage; REGRESSION_FAIL=one or more completed strict failures; REGRESSION_INCOMPLETE=safety/runtime/integrity prevents completion. No physical accuracy implication.

## Post-run engineering warnings

After scheduled attempts report: full strict passes below10/12; any one violation category in >=3 distinct attempts; event-bearing coverage below threshold; known-state coverage below threshold; all responses no-event/abstention; missing/ambiguous EOS,citation,temporal evidence. These are engineering thresholds, not statistical accuracy thresholds, and never authorize prompt changes.

## Repair and preservation

Before first generation fix objectively demonstrated engineering blockers, preserve diffs/tests and recompute hashes before final lock. After generation starts no automatic changes to V1C,fixtures,schema,Validator,generation settings; no output-validity/content based rerun. Only one separately logged smoke technical recovery, same warmup, safehardware, new engineeringconfig version, no task/contract/evaluationchanges. First failed attempt retained. Once B begins any material runtimechange stops for humanreview. Preserve each fullraw/start/completion/validation/resource receipt even when strict fails; no JSON/citation filling/repair. No Protocol Freeze,DEV inference,Graph write,commit/push.
'''
    doc=s.ROOT/'docs/preregistered_criteria.md'
    if doc.exists():doc=s.ROOT/'docs/preregistered_criteria_qwen_closeout_20261015_94dcf4d4.md'
    if doc.exists():raise RuntimeError('PREREGISTRATION_PATH_COLLISION')
    doc.parent.mkdir(parents=True,exist_ok=True)
    with doc.open('x',encoding='utf8',newline='\n') as f:f.write(text)
    s.save('preregistered_criteria.md',text)
    manifest['criteria_path']=doc.relative_to(s.ROOT).as_posix();manifest['criteria_sha256']=s.sha(doc)
    s.save('run_manifest.json',manifest)
    s.save('PREREGISTRATION_LOCK_RECEIPT.json',{'manifest_sha256':s.sha(s.OUT/'run_manifest.json'),
      'criteria_sha256':s.sha(doc),'criteria_path':manifest['criteria_path'],'locked_at_unix':__import__('time').time(),
      'GPU_generations_before_lock':0,'model_loads_before_lock':0,'kind':'EXECUTION_CRITERIA_LOCK_NOT_RESEARCH_PROTOCOL_FREEZE'})
    for p in [doc,s.OUT/'run_manifest.json',s.OUT/'preregistered_criteria.md',s.OUT/'PREREGISTRATION_LOCK_RECEIPT.json']:p.chmod(0o444)
    print('PREREGISTRATION_LOCKED',s.sha(s.OUT/'run_manifest.json'),flush=True)

if __name__=='__main__':
    try:
        if sys.argv[1]=='snapshot':s.snapshot()
        elif sys.argv[1]=='cpu':cpu()
        elif sys.argv[1]=='final-cpu':final_cpu_gate()
        elif sys.argv[1]=='lock':lock()
        else:raise RuntimeError('ENGINEERING_COMMAND_NOT_IMPLEMENTED')
    except Exception:
        error=traceback.format_exc()
        i=1
        while (s.OUT/f'errors/cpu_{i:03d}.json').exists():i+=1
        s.save(f'errors/cpu_{i:03d}.json',{'error':error,'command':sys.argv[1:],'denied':s.DENIED})
        print(error,file=sys.stderr);sys.exit(1)
