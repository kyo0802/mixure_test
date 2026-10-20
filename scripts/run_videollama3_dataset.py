"""User-authorized direct VideoLLaMA3 experiment. No Graph writes or Qwen changes.

prepare freezes exact existing frame selections, run resumes unfinished windows.
No GT/human annotations are read by preparation or inference.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time, traceback
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'.runtime/videollama3/vendor'),str(ROOT/'outputs/current_development/video_event_experiment/.deps'),str(ROOT/'artifacts/pass_i/runtime/vendor')]
OUT=ROOT/'artifacts/pass_t/phase3/videollama3_full_v1'
EVENT=ROOT/'outputs/current_development/event_windows'
OLD=ROOT/'artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f/frozen_bundle.json'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def save(p,d):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
def rel(p):return Path(p).resolve().relative_to(ROOT).as_posix()
def resolve(p):return Path(p) if Path(p).is_absolute() else ROOT/p
def append(d):
    with (OUT/'ledger.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps({'utc':utc(),**d},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())

def prepare():
    assert not (OUT/'input_freeze.json').exists(),'ALREADY_PREPARED'
    freeze=read(EVENT/'builder_freeze.json')
    assert sha(EVENT/'event_manifest.json')==freeze['files']['event_windows/event_manifest.json']
    rows=read(EVENT/'event_manifest.json');videos=read(EVENT/'development_inputs.json')
    protected={rel(EVENT/'event_manifest.json'):sha(EVENT/'event_manifest.json'),rel(OLD):sha(OLD)}
    for folder in ['artifacts/pass_t/phase3/observation_ablation_v1','artifacts/pass_t/phase3/vlm_physical_state_pilot_v1','artifacts/pass_t/phase2a/v2','artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and 'runtime_cache' not in p.parts and p.suffix not in ('.png','.jpg','.mp4'):protected[rel(p)]=sha(p)
    video_map={}
    for v in videos:
        p=resolve(v['path']);actual=sha(p) if p.exists() else None
        video_map[v['video_id']]={**v,'actual_sha256':actual,'integrity_ok':actual==v['sha256']}
    frozen8={i:w for w in read(OLD)['protocol']['draft']['windows'] for i in w['original_pack_ids']}
    windows=[];needed={}
    for w in rows:
        base={k:w.get(k) for k in ('pack_id','video_id','category','start_frame','end_frame','physical_reasoning_eligible','completeness')}
        base['source_video_sha256']=video_map[w['video_id']]['sha256']
        if not w.get('frames'):
            windows.append({**base,'availability':'UNAVAILABLE_NO_FROZEN_FRAME_CONFIGURATION','frames':[]});continue
        if not video_map[w['video_id']]['integrity_ok']:
            windows.append({**base,'availability':'UNAVAILABLE_SOURCE_VIDEO_HASH_MISMATCH','frames':[]});continue
        if w['pack_id'] in frozen8:
            chosen=frozen8[w['pack_id']]['selected']
            frames=[]
            for f in chosen:
                p=resolve(f['source_path']);assert sha(p)==f['recorded_source_png_sha256']
                frames.append({'alias':f['supplied_alias'],'path':rel(p),'source_frame_index':f['source_frame_index'],'native_pts_s':f['native_source_pts_s'],'sha256':sha(p),'source':'EXISTING_FROZEN_UNIFORM8'})
            sampling='EXISTING_FROZEN_UNIFORM8'
        else:
            frames=[];sampling='EXACT_EXISTING_DENSE_FRAME_CONFIGURATION_NO_RESAMPLING'
            for f in w['frames']:
                p=resolve(f['image_path']);assert sha(p)==f['sha256']
                protected[rel(p)]=f['sha256']
                idx=f['frame'];clean=OUT/'clean_frames'/w['video_id']/f'S{idx:06d}.png'
                frames.append({'alias':f'F{idx-w["start_frame"]+1:04d}','path':rel(clean),'source_frame_index':idx,'annotated_original_path':rel(p),'annotated_original_sha256':f['sha256'],'source':'EXACT_INDEX_UNANNOTATED_SOURCE_DECODE'})
                needed.setdefault(w['video_id'],set()).add(idx)
        windows.append({**base,'availability':'ELIGIBLE','sampling':sampling,'frames':frames})
    # Exact source indices only. This creates clean copies, never changes source media.
    import av
    decoded={}
    for vid,indices in needed.items():
        decoded[vid]={};pending=set(indices)
        with av.open(str(resolve(video_map[vid]['path']))) as c:
            stream=c.streams.video[0]
            for idx,frame in enumerate(c.decode(stream)):
                if idx in pending:
                    if frame.pts is None:raise ValueError('MISSING_NATIVE_PTS')
                    p=OUT/'clean_frames'/vid/f'S{idx:06d}.png';p.parent.mkdir(parents=True,exist_ok=True)
                    if not p.exists():frame.to_image().save(p)
                    decoded[vid][idx]={'native_pts_s':float(frame.pts*frame.time_base),'native_pts':frame.pts,'native_time_base':str(frame.time_base),'sha256':sha(p)}
                    pending.remove(idx)
                if not pending:break
        assert not pending,('MISSING_EXACT_SOURCE_FRAMES',vid,sorted(pending))
    seen={}
    for w in windows:
        if w['availability']!='ELIGIBLE':continue
        for f in w['frames']:
            if f['source']=='EXACT_INDEX_UNANNOTATED_SOURCE_DECODE':f.update(decoded[w['video_id']][f['source_frame_index']])
            protected[f['path']]=f['sha256']
        key=hashlib.sha256(json.dumps([w['source_video_sha256'],[(f['source_frame_index'],f['sha256'],f['alias']) for f in w['frames']]],sort_keys=True).encode()).hexdigest()
        w['input_identity_sha256']=key;w['duplicate_of']=seen.get(key)
        if key not in seen:seen[key]=w['pack_id']
        w['overlapping_windows']=[x['pack_id'] for x in windows if x['availability']=='ELIGIBLE' and x['video_id']==w['video_id'] and x['pack_id']!=w['pack_id'] and max(x['start_frame'],w['start_frame'])<=min(x['end_frame'],w['end_frame'])]
    for name in ('prompt.json','schema.json'):
        (OUT/name).write_bytes((ROOT/'artifacts/pass_t/phase3/observation_ablation_v1/condition_c_state_first'/name).read_bytes())
    cfg={'model':'DAMO-NLP-SG/VideoLLaMA3-7B','revision':read(ROOT/'.models/VideoLLaMA3-7B/download_provenance.json')['revision'],'model_path':'.models/VideoLLaMA3-7B','adapter':'memory_graph.experiments.videollama3_adapter.VideoLLaMA3Adapter','quantization':'LANGUAGE_NF4_DOUBLE_QUANT_BF16_COMPUTE_VISION_PROJECTOR_BF16','attention':'sdpa','preprocessing':{'max_visual_tokens_total':4096,'min_visual_tokens':16,'image_merge_size':1},'generation':{'do_sample':False,'seed':42,'max_new_tokens':1024,'timeout_seconds':300},'reference':'NONE','target_identity_authorization':False,'memory_graph_writes':False,'quality_retries':0}
    save(OUT/'dataset_inventory.json',{'created_utc':utc(),'windows':windows,'videos':video_map,'empty_configurations_are_not_resampled':True,'independence':'DUPLICATE_AND_OVERLAP_GROUPS_NOT_INDEPENDENT; SESSION_INDEPENDENCE_UNPROVEN'})
    save(OUT/'configuration.json',cfg);save(OUT/'preservation_before.json',protected)
    model_files={rel(p):sha(p) for p in (ROOT/cfg['model_path']).iterdir() if p.is_file() and p.suffix in ('.json','.py','.safetensors')}
    components={rel(p):sha(p) for p in [OUT/'prompt.json',OUT/'schema.json',OUT/'configuration.json',OUT/'dataset_inventory.json',Path(__file__),ROOT/'src/memory_graph/experiments/videollama3_adapter.py',ROOT/'scripts/run_phase3_observation_ablation.py']}
    save(OUT/'input_freeze.json',{'created_utc':utc(),'scope':'REPRODUCIBILITY_INPUT_SNAPSHOT_NOT_NEW_HUMAN_APPROVAL','components':components,'model_files':model_files,'eligible_windows':sum(w['availability']=='ELIGIBLE' for w in windows),'unique_generation_inputs':len(seen),'gt_model_visible':False})
    print('PREPARED',len(rows),'records',len(seen),'unique inputs',flush=True)

def run():
    from memory_graph.experiments.observation_interface import SourceFrame,ObservationRequest,verify_sources
    from memory_graph.experiments.videollama3_adapter import VideoLLaMA3Adapter
    from run_phase3_observation_ablation import validation
    freeze=read(OUT/'input_freeze.json')
    for p,h in {**freeze['components'],**freeze['model_files']}.items():assert sha(ROOT/p)==h,('FROZEN_COMPONENT_MISMATCH',p)
    cfg=read(OUT/'configuration.json');prompt=read(OUT/'prompt.json');schema=read(OUT/'schema.json')
    adapter=VideoLLaMA3Adapter(ROOT)
    model_meta=adapter.load(cfg)
    if not (OUT/'model_runtime.json').exists():save(OUT/'model_runtime.json',model_meta)
    append({'stage':'MODEL_LOADED','resources':adapter.resources()})
    try:
        for w in read(OUT/'dataset_inventory.json')['windows']:
            if w['availability']!='ELIGIBLE':continue
            dest=OUT/'calls'/w['pack_id'];dest.mkdir(parents=True,exist_ok=True)
            if (dest/'receipt.json').exists() or (dest/'failure.json').exists():continue
            if w['duplicate_of']:
                original=OUT/'calls'/w['duplicate_of']
                if (original/'receipt.json').exists():
                    save(dest/'receipt.json',{'classification':'EXACT_INPUT_DUPLICATE_REUSE','duplicate_of':w['duplicate_of'],'original_receipt_sha256':sha(original/'receipt.json'),'model_generations':0,'independent_sample':False});continue
                save(dest/'failure.json',{'classification':'DUPLICATE_SOURCE_UNAVAILABLE','duplicate_of':w['duplicate_of']});continue
            # A STARTED marker without raw is never silently regenerated after interruption.
            if (dest/'started.json').exists() and not (dest/'raw.txt').exists():
                save(dest/'failure.json',{'classification':'INTERRUPTED_UNKNOWN_GENERATION_STATE','model_output_fabricated':False});continue
            frames=tuple(SourceFrame(f['alias'],ROOT/f['path'],f['source_frame_index'],f['native_pts_s'],f['sha256']) for f in w['frames'])
            request=ObservationRequest(frames,w['source_video_sha256'],prompt['system'],prompt['task'],schema,cfg['generation'],cfg,cfg['preprocessing'])
            verify_sources(request)
            if (dest/'raw.txt').exists():
                diagnostics=validation((dest/'raw.txt').read_text(encoding='utf8'),schema,[f.alias for f in frames],'C')
                if not (dest/'validation.json').exists():save(dest/'validation.json',diagnostics)
                save(dest/'receipt.json',{'classification':'RAW_RECOVERED_WITHOUT_REGENERATION','raw_sha256':sha(dest/'raw.txt'),'input_freeze_sha256':sha(OUT/'input_freeze.json'),'model_generations':1});continue
            stage='RESOURCE_GATE';started=time.perf_counter()
            try:
                adapter.check_resources(load=False)
                stage='RENDER';rendered=adapter.render(request)
                save(dest/'rendered_text.json',rendered.metadata)
                stage='PREPROCESS';prepared=adapter.preprocess(frames,rendered,cfg['preprocessing'])
                assert prepared.metadata['consumed_aliases']==[f.alias for f in frames]
                save(dest/'input_receipt.json',{'frames':w['frames'],'source_video_sha256':w['source_video_sha256'],'input_freeze_sha256':sha(OUT/'input_freeze.json'),'preprocessing':prepared.metadata,'model_metadata_sha256':sha(OUT/'model_runtime.json')})
                stage='GENERATE';save(dest/'started.json',{'utc':utc(),'input_identity_sha256':w['input_identity_sha256'],'maximum_generations':1});append({'window':w['pack_id'],'stage':'GENERATE_STARTED'})
                response=adapter.generate(prepared,rendered,cfg['generation'])
                with (dest/'raw.txt').open('xb') as f:f.write(response.text.encode('utf8'));f.flush();os.fsync(f.fileno())
                save(dest/'generation.json',response.metadata)
                stage='VALIDATE';save(dest/'validation.json',validation(response.text,schema,[f.alias for f in frames],'C'))
                receipt={'classification':'COMPLETED','elapsed_s':time.perf_counter()-started,'raw_sha256':sha(dest/'raw.txt'),'input_freeze_sha256':sha(OUT/'input_freeze.json'),'resources':adapter.resources(),'model_generations':1,'physical_correctness':'NOT_ESTABLISHED_BY_PARSER'}
                save(dest/'receipt.json',receipt);append({'window':w['pack_id'],**receipt});print('COMPLETED',w['pack_id'],round(receipt['elapsed_s'],1),flush=True)
                del prepared,rendered;adapter.cleanup()
            except Exception as e:
                failure={'stage':stage,'error_type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc(),'raw_saved':(dest/'raw.txt').exists(),'quality_retry':False}
                save(dest/'failure.json',failure);append({'window':w['pack_id'],'stage':'FAILED','error':str(e)});print('FAILED',w['pack_id'],stage,str(e),flush=True)
                adapter.cleanup()
                # An API compatibility error is global: fix integration, preserve attempts, resume.
                if not isinstance(e,(TimeoutError,RuntimeError)) or 'out of memory' not in str(e).lower():raise
                adapter.check_resources(load=False)
    finally:adapter.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);args=parser.parse_args()
    if args.action=='prepare':prepare()
    else:run()
