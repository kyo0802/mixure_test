"""Isolated native-video condition; all baseline/upstream artifacts are read-only."""
import copy
import gc
import json
import os
import time
from fractions import Fraction
from pathlib import Path
from .common import ROOT, OUT, sha256, canonical_hash

EXP=OUT/'video_event_experiment'
POLICY={'representation':'NATIVE_ANNOTATED_EVENT_VIDEO','video_processor_target_fps':15.0,
        'minimum_effective_fps':10.0,'canvas':[800,600],'codec':'libx264','pixel_format':'yuv420p',
        'crf':18,'preset':'medium','encoder_threads':1,'audio':False,'source_fps_preserved':True,
        'target_annotation':'EXACT_EXISTING_AUTHORIZED_FRAME_ONLY','candidate_policy':'FROZEN_EVENT_CONTEXTS_EXACT_FRAME_ONLY',
        'window_changes':0,'identity_writes':0,'trusted_physical_writes':0,'answer_retries':0}

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(rel,value):
    p=EXP/rel;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def setup():
    import sys
    sys.path.insert(0,str(EXP/'.deps'))
    runtime=EXP/'.runtime';runtime.mkdir(parents=True,exist_ok=True)
    for name in ['HF_HOME','TORCH_HOME','TMP','TEMP','TMPDIR']:
        os.environ[name]=str(runtime)
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'

def verify_baseline():
    from .pipeline import verify_manifest
    check=verify_manifest(OUT,OUT/'final/final_integrity_manifest.json')
    if not check['valid']:raise RuntimeError(check)
    return check

def events():
    req=read(OUT/'qwen/requests.json')
    all_events={e['pack_id']:e for e in read(OUT/'event_windows/event_manifest.json')}
    result=[copy.deepcopy(all_events[r['pack_id']]) for r in req]
    if len(result)!=9 or any(e['category']!='PHYSICAL_INTERACTION_EVENT' or e['completeness']!='COMPLETE_EVENT_WINDOW' for e in result):
        raise ValueError('Exact nine complete dispatches required')
    return result

def source_frame_indices(e):return range(e['start_frame'],e['end_frame']+1)

def render_row(e,frame,timeline,fps):
    raw=timeline.get(frame)
    row=copy.deepcopy(raw) if raw else {'frame':frame,'time':frame/fps,'identity_authorized':False,
        'target_bbox':None,'mask_reference':None,'anchors':[],'target_authorization_provenance':[]}
    # No source frame outside the window; no forward/backward authority fill.
    if row['time']<e['start_time']-1e-8 or row['time']>e['end_time']+1e-8:
        raise ValueError('Source frame outside frozen event')
    if not row.get('identity_authorized'):
        row.update(identity_authorized=False,target_bbox=None,mask_reference=None,target_authorization_provenance=[])
    frozen={c['key']:{o['frame']:o['bbox'] for o in c['observations']} for c in e['contexts']}
    row['anchors']=[a for a in row.get('anchors',[]) if a['anchor_key'] in frozen and frame in frozen[a['anchor_key']]]
    for a in row['anchors']:
        if a['bbox']!=frozen[a['anchor_key']][frame]:raise ValueError('Frozen candidate bbox drift')
    row['phase']='BEFORE' if row['time']<e['transition_time'] else 'DURING' if row['time']<=e['transition_time']+.6 else 'AFTER'
    return row

def video_prompt(e):
    from .contract import prompt
    original=prompt(e)
    phases=', '.join(f['phase'] for f in e['frames'])
    return original.replace('over the chronological visual sequence.','over the supplied event video.').replace(
        f'Image phases in order: {phases}. Same-image reference panels repeat that image.',
        'Video phases are trigger-relative. Same-frame reference panels repeat that video frame.')

def message(path,prompt):
    return [{'role':'user','content':[{'type':'video','path':str(path)},{'type':'text','text':prompt}]}]

def inspect_clip(path):
    import av
    with av.open(str(path)) as c:
        streams=list(c.streams);s=c.streams.video[0];frames=list(c.decode(video=0))
        timestamps=[float(f.pts*f.time_base) for f in frames]
        fps=float(s.average_rate);dt=1/fps
        cfr=all(abs((b-a)-dt)<=max(float(s.time_base)*2,1e-6) for a,b in zip(timestamps,timestamps[1:]))
        return {'codec':s.codec_context.name,'fps':fps,'frame_count':len(frames),'duration':len(frames)/fps,
            'resolution':[s.width,s.height],'audio_streams':sum(x.type=='audio' for x in streams),
            'constant_frame_rate':cfr,'decoded_timestamps':timestamps,'stream_time_base':str(s.time_base),
            'sha256':sha256(path)}

def prepare():
    setup();verify_baseline()
    if (EXP/'videos/video_manifest.json').exists():raise RuntimeError('Video preparation already completed')
    import av,cv2,numpy as np
    from .pipeline import render_frame
    chosen=events();dev={d['video_id']:d for d in read(OUT/'event_windows/development_inputs.json')}
    frozen=read(OUT/'final/final_integrity_manifest.json')
    write('config/experiment_config.json',{**POLICY,'dependency_av':av.__version__,'compatibility_corrections':0})
    baseline_paths=['qwen/requests.json','qwen/responses.json','qwen/validator_results.json','qwen/model_config.json',
        'qwen/runtime.json','event_windows/event_manifest.json','event_windows/config.json',
        'evaluation/post_freeze_review.json','evaluation/reasoning_metrics.json','evaluation/search_memory.json',
        'evaluation/coverage_details.json','VALIDATION_HANDOFF.md','final/final_integrity_manifest.json']
    write('config/baseline_reference.json',{'pack_ids':[e['pack_id'] for e in chosen],
        'baseline_files':{p:sha256(OUT/p) for p in baseline_paths},'prior_handoff_sha256':sha256(OUT/'VALIDATION_HANDOFF.md'),
        'baseline_sources':frozen['sources'],'held_out_accessed':False})
    manifests=[];requests=[]
    scratch=EXP/'.runtime/render.png'
    for e in chosen:
        d=dev[e['video_id']];source=Path(d['path'])
        if sha256(source)!=d['sha256']:raise RuntimeError('Manifested development media changed')
        timeline=read(OUT/f"event_windows/target_timelines/{e['video_id']}.json")
        rows={r['frame']:r for r in timeline['rows']};fps=d['fps']
        clip=EXP/f"videos/annotated/{e['pack_id']}.mp4";clip.parent.mkdir(parents=True,exist_ok=True)
        cap=cv2.VideoCapture(str(source));cap.set(cv2.CAP_PROP_POS_FRAMES,e['start_frame'])
        frame_records=[]
        with av.open(str(clip),'w',format='mp4') as container:
            rate=Fraction(str(fps)).limit_denominator(100000)
            stream=container.add_stream('libx264',rate=rate)
            stream.width=800;stream.height=600;stream.pix_fmt='yuv420p'
            stream.options={'crf':'18','preset':'medium','threads':'1'};stream.codec_context.thread_count=1
            for index,f in enumerate(source_frame_indices(e)):
                ok,image=cap.read()
                if not ok:raise RuntimeError('Development source decode failed')
                row=render_row(e,f,rows,fps)
                canvas=render_frame(image,row,e,e['contexts'],scratch)
                frame=av.VideoFrame.from_ndarray(np.asarray(canvas),format='rgb24');frame.pts=index;frame.time_base=1/rate
                for packet in stream.encode(frame):container.mux(packet)
                frame_records.append({'source_frame':f,'source_time':f/fps,'phase':row['phase'],
                    'T_marked':bool(row['identity_authorized']),'mask_reference':row.get('mask_reference'),
                    'authorization_provenance':row.get('target_authorization_provenance',[]),
                    'candidate_keys':[a['anchor_key'] for a in row['anchors']]})
            for packet in stream.encode():container.mux(packet)
        cap.release()
        meta=inspect_clip(clip)
        if not meta['constant_frame_rate'] or meta['audio_streams'] or meta['resolution']!=[800,600]:raise RuntimeError('Encoding invariant failed')
        if abs(meta['fps']-fps)>1e-5 or meta['frame_count']!=len(source_frame_indices(e)):raise RuntimeError('FPS/frame count drift')
        if abs(meta['duration']-e['duration_seconds'])>1/fps+.002:raise RuntimeError('Duration exceeds codec tolerance')
        record={'pack_id':e['pack_id'],'source_path':str(source),'source_sha256':d['sha256'],
            'source_fps':fps,'source_resolution':timeline['provenance']['image_size'],
            'start_time':e['start_time'],'end_time':e['end_time'],'trigger_time':e['transition_time'],
            'start_frame':e['start_frame'],'end_frame':e['end_frame'],'window_duration':e['duration_seconds'],
            'path':str(clip),'encoding':meta,'annotation_frames':frame_records,
            'target_marked_frames':sum(r['T_marked'] for r in frame_records),
            'contexts':e['contexts'],'actor_markers':e['actor_markers'],'location_markers':e['location_markers']}
        manifests.append(record);requests.append({'pack_id':e['pack_id'],'messages':message(clip,video_prompt(e)),
            'video_sha256':meta['sha256'],'prompt':video_prompt(e),'prompt_sha256':canonical_hash(video_prompt(e)),
            'requested_fps':min(15.0,fps),'max_new_tokens':1400})
        print('Encoded',e['pack_id'],meta['frame_count'],'frames',round(fps,5),'fps; authorized T',record['target_marked_frames'],flush=True)
    if scratch.exists():scratch.unlink()
    write('videos/video_manifest.json',manifests);write('qwen/requests.json',requests)
    return {'clips':len(manifests),'encoded_frames':sum(m['encoding']['frame_count'] for m in manifests)}

def processor_inputs(backend,req,clip):
    # Official native path receives an MP4 video modality, not a manual image list.
    # transformers 4.57.6 cannot tensorize returned VideoMetadata in Qwen's
    # outer BatchFeature. Observe the unchanged official sampler instead.
    original=backend.processor.video_processor.sample_frames
    observed={}
    def observe(*args,**kwargs):
        metadata=kwargs.get('metadata',args[0] if args else None)
        indices=original(*args,**kwargs)
        observed.update(metadata=metadata,indices=indices)
        return indices
    backend.processor.video_processor.sample_frames=observe
    try:
        inputs=backend.processor.apply_chat_template(req['messages'],tokenize=True,add_generation_prompt=True,
            return_dict=True,return_tensors='pt',fps=req['requested_fps'],do_sample_frames=True)
    finally:backend.processor.video_processor.sample_frames=original
    metadata=observed['metadata']
    ids=observed['indices']
    ids=ids.tolist() if hasattr(ids,'tolist') else list(ids) if ids is not None else None
    count=len(ids) if ids is not None else int(inputs['video_grid_thw'][0,0])*backend.processor.video_processor.temporal_patch_size
    duration=clip['encoding']['duration'];effective=count/duration
    grids=inputs['video_grid_thw'].tolist()
    marked={r['source_frame'] for r in clip['annotation_frames'] if r['T_marked']}
    metrics={'pack_id':req['pack_id'],'source_fps':clip['source_fps'],'clip_duration':duration,
        'window_duration':clip['window_duration'],'encoded_frame_count':clip['encoding']['frame_count'],
        'requested_processor_fps':req['requested_fps'],'actual_selected_frame_count':count,
        'effective_processor_fps':effective,'selected_clip_frame_indices':ids,
        'selected_clip_timestamps':[i/metadata.fps for i in ids] if ids is not None else 'selected_timestamps_not_exposed',
        'selected_source_frame_indices':[clip['start_frame']+i for i in ids] if ids is not None else None,
        'selected_T_authorized_frames':sum(clip['start_frame']+i in marked for i in ids) if ids is not None else None,
        'video_grid_thw':grids,'visual_tokens':sum(t*h*w//backend.processor.video_processor.merge_size**2 for t,h,w in grids),
        'input_tokens':int(inputs['input_ids'].shape[1]),
        'second_per_grid_ts':inputs['second_per_grid_ts'].tolist() if hasattr(inputs.get('second_per_grid_ts'),'tolist') else inputs.get('second_per_grid_ts'),
        'pixel_values_videos_shape':list(inputs['pixel_values_videos'].shape),
        'native_video_modality':True,'image_list_inputs':False,'density_valid':effective>=10.0}
    if 'pixel_values' in inputs:raise RuntimeError('Unexpected image modality')
    return inputs,metrics

def generate(backend,inputs):
    import torch
    from transformers import StoppingCriteria,StoppingCriteriaList
    from torch.nn.attention import sdpa_kernel,SDPBackend
    from .model import Monitor
    moved={k:v.to(backend.device) if hasattr(v,'to') else v for k,v in inputs.items()}
    moved['pixel_values_videos']=moved['pixel_values_videos'].to(backend.model.dtype)
    start=time.monotonic();trace={};raw='';error=None
    deadline=start+120
    class Deadline(StoppingCriteria):
        def __call__(self,input_ids,scores,**kwargs):return time.monotonic()>=deadline
    torch.cuda.reset_peak_memory_stats()
    with Monitor() as mon:
        try:
            with torch.inference_mode(),sdpa_kernel([SDPBackend.CUDNN_ATTENTION,SDPBackend.MATH],set_priority=True):
                output=backend.model.generate(**moved,max_new_tokens=1400,do_sample=False,stopping_criteria=StoppingCriteriaList([Deadline()]))
            new=output[:,moved['input_ids'].shape[1]:];eos=backend.model.generation_config.eos_token_id
            eos=eos if isinstance(eos,list) else [eos]
            trace.update(generated_tokens=int(new.shape[1]),ended_with_EOS=bool(new.shape[1] and int(new[0,-1]) in eos))
            raw=backend.processor.batch_decode(new,skip_special_tokens=True)[0]
            del output,new
        except Exception as exc:error=type(exc).__name__+': '+str(exc)
    trace.update(runtime_seconds=time.monotonic()-start,error=error,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),**mon.result())
    del moved;gc.collect();torch.cuda.empty_cache()
    return raw,trace

def hash_sources():
    paths=['src/memory_graph/reasoning/video_experiment.py','src/memory_graph/reasoning/video_evaluation.py',
        'scripts/run_video_event_experiment.py','tests/test_video_event_experiment.py']
    return {p:sha256(ROOT/p) for p in paths if (ROOT/p).exists()}

def freeze_inputs():
    baseline=read(EXP/'config/baseline_reference.json')
    windows={e['pack_id']:{k:e[k] for k in ['start_time','end_time','transition_time','start_frame','end_frame','contexts','actor_markers','location_markers']} for e in events()}
    write('freeze/source_hashes.json',{**baseline['baseline_sources'],**hash_sources()})
    write('freeze/window_hashes.json',{p:canonical_hash(w) for p,w in windows.items()})
    paths=[p for directory in ['config','videos','processor','freeze'] for p in (EXP/directory).rglob('*') if p.is_file()]
    paths.append(EXP/'qwen/requests.json')
    write('freeze/video_experiment_freeze_manifest.json',{'stage':'PRE_CANONICAL_FROZEN','freeze_unix':time.time(),
        'files':{p.relative_to(EXP).as_posix():sha256(p) for p in paths},'sources':hash_sources(),
        'baseline_protected':baseline,'window_changes':0,'prior_handoff_sha256':baseline['prior_handoff_sha256']})

def run():
    setup();verify_baseline()
    if (EXP/'qwen/execution_started.json').exists():raise RuntimeError('Canonical already started; no retries')
    from .model import Backend,Monitor
    from .contract import parse_json
    from .validator import DirectReasoningValidator
    from .pipeline import verify_manifest
    import torch
    requests=read(EXP/'qwen/requests.json');clips=read(EXP/'videos/video_manifest.json')
    start=time.monotonic()
    with Monitor() as mon:backend=Backend()
    loading={'seconds':time.monotonic()-start,**mon.result()}
    write('config/qwen_config.json',{**backend.identity(),'video_processor_class':type(backend.processor.video_processor).__name__,
        'video_processor_config':backend.processor.video_processor.to_dict(),'load':loading})
    # Preflight selection uses duration only; no review labels/accuracy enter runtime selection.
    pre=max(range(9),key=lambda i:clips[i]['encoding']['duration'])
    print('Native processor audit for all nine; preflight:',requests[pre]['pack_id'],flush=True)
    cached_metrics=[]
    for req,clip in zip(requests,clips):
        inputs,m=processor_inputs(backend,req,clip);cached_metrics.append(m);del inputs;gc.collect()
        print('Processor',m['pack_id'],m['actual_selected_frame_count'],'frames',round(m['effective_processor_fps'],3),'fps',m['visual_tokens'],'visual tokens',flush=True)
    write('processor/processor_metrics.json',cached_metrics)
    if not all(m['density_valid'] for m in cached_metrics):
        write('processor/temporal_density.json',{'valid':False,'status':'VIDEO_TEMPORAL_DENSITY_NOT_ACHIEVED','events':cached_metrics});return {'status':'VIDEO_TEMPORAL_DENSITY_NOT_ACHIEVED'}
    write('processor/temporal_density.json',{'valid':True,'requested_fps':15.0,'minimum_effective_fps':10.0,'events':cached_metrics})
    inputs,pm=processor_inputs(backend,requests[pre],clips[pre]);raw,trace=generate(backend,inputs);del inputs
    write('qwen/preflight.json',{'pack_id':requests[pre]['pack_id'],'raw_response':raw,'compute_trace':trace,
        'processor':pm,'semantic_reviewed':False,'purpose':'Technical native video compatibility only'})
    print('Preflight technical status',trace.get('ended_with_EOS'),trace['error'],round(trace['runtime_seconds'],2),flush=True)
    if trace['error'] and ('OutOfMemory' in trace['error'] or 'out of memory' in trace['error']):
        for req,clip in zip(requests,clips):req['requested_fps']=min(10.0,clip['source_fps'])
        write('qwen/requests.json',requests)
        conf=read(EXP/'config/experiment_config.json');conf.update(video_processor_target_fps=10.0,
            compatibility_corrections=1,fallback='GLOBAL_RUNTIME_COMPATIBILITY_FALLBACK_15_TO_10FPS')
        write('config/experiment_config.json',conf)
        cached_metrics=[]
        for req,clip in zip(requests,clips):
            inputs,m=processor_inputs(backend,req,clip);cached_metrics.append(m);del inputs;gc.collect()
        write('processor/processor_metrics.json',cached_metrics)
        write('processor/temporal_density.json',{'valid':all(m['density_valid'] for m in cached_metrics),'requested_fps':10.0,'minimum_effective_fps':10.0,'events':cached_metrics})
        if not all(m['density_valid'] for m in cached_metrics):return {'status':'VIDEO_TEMPORAL_DENSITY_NOT_ACHIEVED'}
        inputs,pm=processor_inputs(backend,requests[pre],clips[pre]);raw,trace=generate(backend,inputs);del inputs
        write('qwen/preflight_10fps.json',{'pack_id':requests[pre]['pack_id'],'raw_response':raw,'compute_trace':trace,'processor':pm,'semantic_reviewed':False})
    if trace['error'] or not trace.get('ended_with_EOS'):
        write('qwen/runtime.json',{'canonical_calls':0,'status':'NATIVE_VIDEO_RUNTIME_INFEASIBLE','preflight_trace':trace})
        return {'status':'NATIVE_VIDEO_RUNTIME_INFEASIBLE'}
    freeze_inputs()
    if not verify_manifest(EXP,EXP/'freeze/video_experiment_freeze_manifest.json')['valid']:raise RuntimeError('Pre-run freeze failed')
    write('qwen/execution_started.json',{'started_unix':time.time(),'planned_calls':9,'retries':0})
    e_by={e['pack_id']:e for e in events()};responses=[];parsed=[];vals=[]
    for req,clip in zip(requests,clips):
        print('Canonical native video',req['pack_id'],flush=True)
        start=time.monotonic();answer=None;raw='';trace={};error=None
        try:
            inputs,m=processor_inputs(backend,req,clip)
            if not m['density_valid']:raise RuntimeError('VIDEO_TEMPORAL_DENSITY_NOT_ACHIEVED')
            raw,trace=generate(backend,inputs);del inputs
            error=trace['error'];answer=parse_json(raw)
        except Exception as exc:error=type(exc).__name__+': '+str(exc)
        val=DirectReasoningValidator().validate(e_by[req['pack_id']],answer)
        if not trace.get('ended_with_EOS'):
            val['valid']=False;val['errors'].append('INCOMPLETE_GENERATION');val['status']='INVALID_MODEL_REASONING_OUTPUT'
        trace.update(wall_seconds=time.monotonic()-start)
        responses.append({'pack_id':req['pack_id'],'raw_output':raw,'answer':answer,'error':error,'compute_trace':trace,'processor':m,'actual_inference':True,'retries':0})
        parsed.append({'pack_id':req['pack_id'],'answer':answer});vals.append(val)
        for name,data in [('responses',responses),('parsed_outputs',parsed),('validator_results',vals)]:write(f'qwen/{name}.json',data)
        print('Completed',req['pack_id'],round(trace['wall_seconds'],2),'EOS',trace.get('ended_with_EOS'),'error',error,flush=True)
    runtime={'canonical_calls':len(responses),'load':loading,'inference_seconds':sum(r['compute_trace']['runtime_seconds'] for r in responses),
        'wall_inference_seconds':sum(r['compute_trace']['wall_seconds'] for r in responses),
        'EOS_count':sum(r['compute_trace'].get('ended_with_EOS',False) for r in responses),
        'runtime_errors':sum(r['error'] is not None for r in responses),'OOM_count':sum('out of memory' in str(r['error']).lower() for r in responses),
        'timeouts':sum(not r['compute_trace'].get('ended_with_EOS',False) and not r['error'] for r in responses),
        'peak_global_gpu_bytes':max([loading['global_gpu_used_peak_bytes']]+[r['compute_trace'].get('global_gpu_used_peak_bytes',0) for r in responses]),
        'schema_valid':sum(v['schema_valid'] for v in vals),'validator_valid':sum(v['valid'] for v in vals),'retries':0}
    write('qwen/runtime.json',runtime)
    paths=[p for d in ['config','videos','processor','qwen','freeze'] for p in (EXP/d).rglob('*') if p.is_file()]
    write('final/artifact_manifest.json',{'stage':'PREDICTIONS_FROZEN_BEFORE_REVIEW','freeze_unix':time.time(),
        'files':{p.relative_to(EXP).as_posix():sha256(p) for p in paths},'sources':hash_sources(),'review_started':False})
    del backend;gc.collect();torch.cuda.empty_cache()
    return runtime
