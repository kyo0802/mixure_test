"""Native Video array CPU preflight; no model, runtime server or generation."""
import core
import json,math,inspect
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from memory_graph.pass_t.phase2b.builders import uniform_positions
from memory_graph.pass_t.phase2b.predictions import schema

PREVIOUS=core.ROOT/'artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003'
AUDIT=core.ROOT/'artifacts/pass_t/phase2b/output_failure_audit/qwen_nf4/20261015'

def time_audit(times,fps,patch_size,observed_seconds_per_grid=None):
    native=[float(t)-float(times[0]) for t in times]
    nominal=[i/fps for i in range(len(times))]
    # Actual temporal positional metadata is per temporal patch, not per frame.
    seconds=patch_size/fps if observed_seconds_per_grid is None else observed_seconds_per_grid
    patch=[(i//patch_size)*seconds for i in range(len(times))]
    return {'native_window_relative_s':native,'encoded_container_frame_time_s':[None]*len(times),
      'processor_selected_nominal_frame_time_s':nominal,'model_visible_temporal_patch_time_s':patch,
      'nominal_reconstruction_deviation_s':[b-a for a,b in zip(native,nominal)],
      'time_distortion_s':[b-a for a,b in zip(native,patch)],
      'max_abs_nominal_deviation_s':max(abs(b-a) for a,b in zip(native,nominal)),
      'max_abs_model_patch_deviation_s':max(abs(b-a) for a,b in zip(native,patch)),
      'proposed_tolerance_s':0.1,'tolerance_approved':False,'native_sidecar_model_visible':False,
      'time_encoding_class':'UNIFORM_RECONSTRUCTED','container_encoding':'NONE_NATIVE_VIDEO_FRAME_ARRAY'}

def outcome(frame_ok,order_ok,processor_ok,mapping_ok,alias_ok,max_deviation):
    checks=[frame_ok,order_ok,processor_ok,mapping_ok,alias_ok]
    if not all(x is True for x in checks):return 'NOT_MATCHED'
    return 'FULLY_MATCHED' if max_deviation is not None and max_deviation<=0.1 else 'FRAME_MATCHED_ONLY'

def groups():
    inventory=core.read(AUDIT/'prospective_uniform8_inventory.json');result=[]
    for prior in inventory:
        raw=core.read(PREVIOUS/'private'/prior['opaque_id']/'source.json');allframes=raw['frames'];positions=uniform_positions(len(allframes),8)
        assert positions==prior['positions']
        selected=[allframes[i] for i in positions]
        assert [f['frame_id'] for f in selected]==prior['source_frame_ids']
        assert [f['source_timestamp_s'] for f in selected]==prior['native_pts_s']
        result.append({'id':prior['opaque_id'],'kind':'DEV','private_item_id':prior['item_id'],'source':prior['source'],
          'authorized_count':len(allframes),'authorized_first':allframes[0]['frame_id'],'authorized_last':allframes[-1]['frame_id'],
          'positions':positions,'prior_uniform_agreement':True,'frames':[{'path':f['image_path'],'file_sha256':f['sha256'],
             'native_id':f['frame_id'],'native_pts_s':f['source_timestamp_s'],'alias':a} for f,a in zip(selected,prior['aliases'])]})
    manifest=core.read(core.OUT/'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json')
    for fixture in manifest['scenarios']:
        result.append({'id':fixture['fixture_id'],'kind':'WARMUP' if fixture['intended_stratum']=='WARMUP' else 'SYNTHETIC_EVAL',
          'authorized_count':8,'authorized_first':0,'authorized_last':7,'positions':uniform_positions(8,8),
          'prior_uniform_agreement':'N/A_NEW_LOCKED_FIXTURE',
          'frames':[{'path':core.rel(core.OUT/f['path']),'file_sha256':f['file_sha256'],
               'native_id':f['source_frame_index'],'native_pts_s':f['synthetic_timestamp_s'],'alias':f['opaque_alias']} for f in fixture['frames']]})
    return result

def conversation(processor,rep,aliases,prompt,system):
    contents=[]
    if rep=='MULTI_IMAGE':
        for alias in aliases:contents.extend([{'type':'text','text':'Supplied aliases: '+alias},{'type':'image'}])
    else:contents.extend([{'type':'text','text':'Supplied aliases: '+', '.join(aliases)},{'type':'video' if rep=='VIDEO' else 'image'}])
    contents.append({'type':'text','text':prompt+'\nRequired JSON schema:\n'+json.dumps(schema())})
    messages=[{'role':'system','content':[{'type':'text','text':system}]},{'role':'user','content':contents}]
    return processor.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)

def process_one(g,processor,torch):
    folder=core.OUT/'model_visible'/'matched8_native_array'/g['id'];folder.mkdir(parents=True,exist_ok=False)
    images=[];lineage=[]
    for i,row in enumerate(g['frames']):
        path=core.ROOT/row['path'];assert core.sha(path)==row['file_sha256']
        with Image.open(path) as im:rgb=im.convert('RGB')
        images.append(rgb);canonical=core.byte_sha(rgb.tobytes())
        p=folder/f'IMG_{i+1:03d}.png';rgb.save(p,format='PNG',optimize=False)
        with Image.open(p) as im:assert core.byte_sha(im.convert('RGB').tobytes())==canonical
        lineage.append({**row,'width':rgb.width,'height':rgb.height,'canonical_rgb_sha256':canonical,
            'new_multi_path':str(p.relative_to(core.OUT)),'new_file_sha256':core.sha(p)})
    aliases=[f['alias'] for f in lineage];times=[f['native_pts_s'] for f in lineage]
    w,h=images[0].size;assert all(im.size==(w,h) for im in images)
    cell=480;scaled=round(h*cell/w);label=32;columns=3
    storyboard=Image.new('RGB',(columns*cell,3*(scaled+label)),'white');draw=ImageDraw.Draw(storyboard);tiles=[]
    for i,(im,alias) in enumerate(zip(images,aliases)):
        x=(i%3)*cell;y=(i//3)*(scaled+label);tile=im.resize((cell,scaled),Image.Resampling.LANCZOS)
        storyboard.paste(tile,(x,y+label));draw.text((x+8,y+8),alias,fill='black',font=ImageFont.load_default())
        crop=storyboard.crop((x,y+label,x+cell,y+label+scaled));assert crop.tobytes()==tile.tobytes()
        tiles.append({'slot':i,'alias':alias,'source_rgb_sha256':lineage[i]['canonical_rgb_sha256'],
           'tile_rectangle':[x,y+label,x+cell,y+label+scaled],'tile_rgb_sha256':core.byte_sha(tile.tobytes()),
           'transform':{'resize':'PIL_LANCZOS','source_wh':[w,h],'tile_wh':[cell,scaled],'label_height':32}})
    storypath=folder/'STORYBOARD.png';storyboard.save(storypath,format='PNG',optimize=False)
    prompt=(core.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt').read_text()
    system=(core.OUT/'prompt_candidate/v2_system_unchanged.txt').read_text()
    budget={};observer={};rendered={}
    for rep,ims in [('MULTI_IMAGE',images),('STORYBOARD',[storyboard])]:
        text=conversation(processor,rep,aliases,prompt,system);rendered[rep]=text
        inputs=processor(text=[text],images=ims,return_tensors='pt',padding=True,device='cpu')
        grid=inputs['image_grid_thw'].tolist();merge=processor.image_processor.merge_size
        budget[rep]={'image_grid_thw':grid,'effective_spatial_hw':[[int(x[1])*14,int(x[2])*14] for x in grid],
            'visual_tokens':sum(int(np.prod(x))//merge**2 for x in grid),'expanded_input_tokens':int(inputs['input_ids'].numel()),
            'pixel_tensor_shape':list(inputs['pixel_values'].shape),'pixel_tensor_sha256':core.byte_sha(inputs['pixel_values'].numpy().tobytes()),
            'source_frame_count':8,'processor_image_count':len(ims),'time_encoding_class':'ORDER_ONLY',
            'native_times_model_visible':False,'time_distortion_s':[None]*8,'runtime_consumption':'RUNTIME_CONSUMPTION_NOT_VERIFIED'}
        del inputs
    # Genuine video ndarray public API: not an image-list conversation.
    array=np.stack([np.asarray(im) for im in images]);array_sha=core.byte_sha(array.tobytes())
    fps=7/(times[-1]-times[0]);patch_size=processor.video_processor.temporal_patch_size
    from transformers.video_utils import VideoMetadata
    metadata=VideoMetadata(total_num_frames=8,fps=fps,duration=8/fps)
    original=processor.video_processor._preprocess
    def observe(*args,**kwargs):
        videos=kwargs.get('videos',args[0] if args else None)
        t=videos[0];observer['accepted_tensor_shape']=list(t.shape)
        observer['accepted_frame_rgb_sha256']=[core.byte_sha(f.permute(1,2,0).contiguous().numpy().tobytes()) for f in t]
        return original(*args,**kwargs)
    processor.video_processor._preprocess=observe
    try:
        text=conversation(processor,'VIDEO',aliases,prompt,system);rendered['VIDEO']=text
        inputs=processor(text=[text],videos=[array],video_metadata=[metadata],fps=fps,do_sample_frames=False,
            return_tensors='pt',return_metadata=False,device='cpu')
    finally:processor.video_processor._preprocess=original
    grid=inputs['video_grid_thw'].tolist();merge=processor.video_processor.merge_size
    accepted=observer['accepted_frame_rgb_sha256'];expected=[f['canonical_rgb_sha256'] for f in lineage]
    frame_match=accepted==expected
    seconds=inputs['second_per_grid_ts']
    # BatchFeature converts this processor metadata to float32; retain actual
    # output precision rather than demanding impossible float64 equality.
    assert len(seconds)==1 and np.isclose(float(seconds[0]),patch_size/fps,rtol=1e-6,atol=0)
    time=time_audit(times,fps,patch_size,float(seconds[0]))
    time['seconds_per_grid_tensor_dtype']=str(seconds.dtype)
    selected=list(range(len(accepted)))
    budget['VIDEO']={'video_grid_thw':grid,'effective_spatial_hw':[[int(x[1])*14,int(x[2])*14] for x in grid],
       'visual_tokens':sum(int(np.prod(x))//merge**2 for x in grid),'expanded_input_tokens':int(inputs['input_ids'].numel()),
       'pixel_tensor_shape':list(inputs['pixel_values_videos'].shape),'pixel_tensor_sha256':core.byte_sha(inputs['pixel_values_videos'].numpy().tobytes()),
       'second_per_grid_ts':[float(x) for x in seconds],'source_frame_count':8,'accepted_frames':len(accepted),
       'selected_indices':selected,'sampling_disabled_explicitly':True,'temporal_patch_size':patch_size,'temporal_patches':grid[0][0],
       'temporal_padding':int(grid[0][0])*patch_size-len(accepted),'supplied_aliases':aliases,
       'aliases_by_temporal_unit':[aliases[i:i+patch_size] for i in range(0,8,patch_size)],
       'alias_granularity':'8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified',
       'runtime_consumption':'RUNTIME_CONSUMPTION_NOT_VERIFIED','native_array_sha256':array_sha,
       'direct_api_path':'Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)',
       'V3_runtime_route':'NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made'}
    del inputs,array
    checks={'FRAME_SOURCE_MATCH':True,'FRAME_ORDER_MATCH':True,'PROCESSOR_SELECTED_FRAME_MATCH':frame_match,
       'NATIVE_TIME_MAPPING_VERIFIED':len(set(aliases))==8 and len(times)==8,
       'CITATION_ALIAS_MATCH':True,'REPRESENTATION_BUDGET_DOCUMENTED':True}
    status=outcome(True,True,frame_match,checks['NATIVE_TIME_MAPPING_VERIFIED'],True,time['max_abs_model_patch_deviation_s'])
    payload={'candidate_status':'CPU_PREFLIGHT_NOT_APPROVED','opaque_window_id':g['id'],'target':'TARGET_A',
       'representations':{'MULTI_IMAGE':{'files':[f'IMG_{i+1:03d}.png' for i in range(8)],'aliases':aliases},
          'STORYBOARD':{'file':'STORYBOARD.png','aliases':aliases},
          'VIDEO':{'native_frame_array_source_files':[f'IMG_{i+1:03d}.png' for i in range(8)],'aliases':aliases,
                   'processor_fps':fps,'do_sample_frames':False}},
       'task_prompt_sha256':core.sha(core.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt'),
       'identity_clause_activated':False,'not_current_runtime_envelope':True}
    visible_text=json.dumps(payload)+''.join(rendered.values())
    leaks=[v for v in [g.get('private_item_id'),g.get('source'),*[str(f['native_id']) for f in lineage if g['kind']=='DEV']] if v and v in visible_text]
    assert not leaks
    core.save(f'model_visible/matched8_native_array/{g["id"]}/candidate_payload.json',payload)
    for rep,text in rendered.items():core.save(f'model_visible/matched8_native_array/{g["id"]}/rendered_{rep}.txt',text)
    result={**g,'lineage':lineage,'storyboard_tiles':tiles,'storyboard_sha256':core.sha(storypath),
       'frame_array_observer':observer,'time':time,'budgets':budget,'checks':checks,'outcome':status,
       'reasons':['CFR_TIME_DISTORTION'] if status=='FRAME_MATCHED_ONLY' else [] if status=='FULLY_MATCHED' else ['PROCESSOR_DROPPED_FRAMES'],
       'alias_policy_human_decision':'Membership accepts all supplied aliases but per-frame distinguishability within temporal pair not established',
       'leakage':{'metadata_scan':'PASS','pixel_semantic_leakage':'PIXEL_SEMANTIC_LEAKAGE_UNDETERMINED','identity_reference_present':False},
       'model_visible_time_notes':'Video has inferred uniform fps temporal positions; images/storyboard order-only. Native PTS is private. No timestamp header.',
       'raw_arrays_not_persisted':True,'cuda_initialized':torch.cuda.is_initialized()}
    assert not torch.cuda.is_initialized()
    core.save(f'private_mappings/{g["id"]}.json',result)
    return result

def run():
    core.authorities();inputgroups=groups();results=[];processor=None;error=None
    try:processor,torch=core.load_processor()
    except (OSError,ImportError) as e:error=str(e)
    for g in inputgroups:
        try:
            if processor is None:raise RuntimeError('PROCESSOR_BEHAVIOR_UNVERIFIABLE:'+str(error))
            result=process_one(g,processor,torch)
        except Exception as e:
            result={**g,'outcome':'NOT_MATCHED','reasons':['PROCESSOR_BEHAVIOR_UNVERIFIABLE'],
                'error':str(e),'claim':'Not matched for primary-protocol purposes because unverified, not demonstrated frame mismatch',
                'runtime_consumption':'RUNTIME_CONSUMPTION_NOT_VERIFIED'}
            core.save(f'processor_diagnostics/current/{g["id"]}_unverified.json',result)
        results.append(result);print(g['id'],result['outcome'],result.get('error',''),flush=True)
    sources=[core.ROOT/'.venv/Lib/site-packages/transformers/models/qwen2_vl/video_processing_qwen2_vl.py',
      core.ROOT/'.venv/Lib/site-packages/transformers/models/qwen2_5_vl/processing_qwen2_5_vl.py',
      core.ROOT/'.venv/Lib/site-packages/transformers/models/qwen2_5_vl/modeling_qwen2_5_vl.py',
      core.ROOT/'.venv/Lib/site-packages/transformers/video_processing_utils.py']
    core.save('processor_source_inventory.json',{core.rel(p):core.sha(p) for p in sources})
    core.save('matched8_results.json',results)
    text='''# Matched Video 8 CPU 預檢

只載本機processor/tokenizer，沒有model。原uniform_positions round ties-to-even、首末包含算法保留；DEV六窗逐項重現此前八個位置。test3未建立input。Synthetic六評估+一warmup均來自先鎖影格。

Public API直接接受RGB ndarray為video；有video_grid_thw，不是Multi-image。_preprocess輸入觀察器逐frame核對canonicalRGB digest與順序；8frame→4 temporal patches、2frame/pair，未pad/drop/dup。內部CPU張量僅記shape/digest，未持久化。原runtime仍AVI/fps4路徑，nativearray尚未接入；不能用本CPU成功宣稱runtime consumption成功。

時間：無container，所以encoded frame time每項null（NOT_APPLICABLE）。processor fps=7/native span；沒有源PTS逐點輸入。second_per_grid_ts=temporal_patch_size/fps；installed modeling get_rope_index用這個值與tokens_per_second构造時間position。未呼叫model/forward，僅來源碼驗證與processor輸出。時序是uniform重建，非native PTS exact。Multi/Storyboard ORDER_ONLY；原PTS仍private sidecar，無新time header。報告同時列每frame nominal重建與實際temporal-unit重建 deviation，不能只用較小nominal數字忽略pair時間量化。Video per-frame aliases有8個，時間位置只有4個；membership validator能接受8，但模型是否分辨每一張尚未證明，需human alias policy。

0.1s容許只是proposal，不是批准。FRAME_MATCHED_ONLY表示source/order/CPUconsumption可核對但時間粒度／distortion或政策不足；不能默認18-call arm已獲准。整體budget有固有差異，沒有time-information/token/pixel parity聲稱。

| Case | Kind | Outcome | Reason / max patch deviation |
|---|---|---|---|
'''
    for x in results:text+=f"| {x.get('source',x['id'])} | {x['kind']} | {x['outcome']} | {x.get('reasons')} / {x.get('time',{}).get('max_abs_model_patch_deviation_s','UNVERIFIED')} |\n"
    text+='\n## 逐窗與逐fixture完整資料\n'
    for x in results:
        text+=f"\n### {x['id']} ({x['kind']})\n\n"
        if 'lineage' not in x:text+=str(x.get('error'))+'\n';continue
        text+=f"Authorized count={x['authorized_count']}; first/last={x['authorized_first']}/{x['authorized_last']}; positions={x['positions']}; previousagreement={x['prior_uniform_agreement']}.\n\n"
        text+='| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |\n|---|---|---|---|---|---|\n'
        for i,f in enumerate(x['lineage']):text+=f"| {f['alias']} | {f['native_id']} | {f['native_pts_s']} | {f['canonical_rgb_sha256']} | {x['time']['nominal_reconstruction_deviation_s'][i]} | {x['time']['time_distortion_s'][i]} |\n"
        gaps=[b-a for a,b in zip([f['native_pts_s'] for f in x['lineage']],[f['native_pts_s'] for f in x['lineage']][1:])]
        text+=f"\nNative gaps={gaps}; checks={x['checks']}. Budget={json.dumps(x['budgets'],ensure_ascii=False)}.\n\n"
        text+=f"完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/{x['id']}.json)。\n"
    text+='\nMetadata leakage掃描無private item/sourceID/GTroles/answers/reviewer/oldprediction/targetref；像素本身可能暴露物理事件，PIXEL_SEMANTIC_LEAKAGE_UNDETERMINED。正常scene evidence不是新增metadata answer；不聲稱影像可完全概念盲化。\n'
    core.save('QWEN_NF4_MATCHED_VIDEO8_CPU_PREFLIGHT_REPORT.md',text)
    core.receipt(2,[AUDIT/'prospective_uniform8_inventory.json',core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json',*sources],
       [core.OUT/'matched8_results.json',core.OUT/'QWEN_NF4_MATCHED_VIDEO8_CPU_PREFLIGHT_REPORT.md',core.OUT/'processor_source_inventory.json'],
       'COMPLETE',not_matched=sum(x['outcome']=='NOT_MATCHED' for x in results),runtime_consumption='RUNTIME_CONSUMPTION_NOT_VERIFIED')
if __name__=='__main__':run()
