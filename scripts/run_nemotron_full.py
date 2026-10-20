"""Official Linux vLLM NVFP4 video-array execution. Never substitutes four images."""
from pathlib import Path
import os,sys,json,hashlib,time,traceback,signal,site,threading,subprocess
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/pass_t/phase3/three_vlm_full_v1';sys.dont_write_bytecode=True
for key in ('HF_HOME','HF_MODULES_CACHE','TORCH_HOME','TRITON_CACHE_DIR','VLLM_CACHE_ROOT','XDG_CACHE_HOME','TMPDIR'):
    p=ROOT/'.runtime/nemotron/cache'/key;p.mkdir(parents=True,exist_ok=True);os.environ[key]=str(p)
# DrvFS does not support AF_UNIX sockets, and long repository paths exceed 107
# bytes. Only ephemeral local IPC uses native Linux /tmp; data/caches stay here.
ipc=Path('/tmp/findmind_nemotron');ipc.mkdir(mode=0o700,exist_ok=True)
os.environ['TMPDIR']=str(ipc);os.environ['VLLM_RPC_BASE_PATH']=str(ipc)
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',VLLM_WORKER_MULTIPROC_METHOD='spawn',TOKENIZERS_PARALLELISM='false',TORCH_COMPILE_DISABLE='1')
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'.runtime/nemotron/sitepackages_linux')]
site.addsitedir(str(ROOT/'.runtime/nemotron/sitepackages_linux'))
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
def main():
    from memory_graph.experiments.three_vlm_contract import validate_raw
    cfg=read(OUT/'configuration.json');config=cfg['models']['nemotron'];prompt=read(OUT/'prompt.json');schema=read(OUT/'schema.json');freeze=read(OUT/'dataset_freeze.json')
    for p,h in freeze['components'].items():assert sha(ROOT/p)==h,('FROZEN_COMPONENT_CHANGED',p)
    windows=[w for w in read(OUT/'dataset.json')['windows'] if w['status']=='ELIGIBLE' and not w['duplicate_of']]
    base=OUT/'runs/nemotron';base.mkdir(parents=True,exist_ok=True);attempt=len(list(base.glob('load_attempt_*.json')))+1
    resources={'scope':'GLOBAL_GPU_USED_INCLUDES_DISPLAY_AND_OTHER_PROCESSES','gpu_global_peak_used_mib':None,'samples':0}
    def sample_gpu():
        while True:
            try:
                used=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],text=True).strip().splitlines()[0]);resources['gpu_global_peak_used_mib']=max(resources['gpu_global_peak_used_mib'] or 0,used);resources['samples']+=1
            except Exception:pass
            time.sleep(1)
    threading.Thread(target=sample_gpu,daemon=True).start()
    settings={'model':str(ROOT/config['model_path']),'trust_remote_code':True,'quantization':'modelopt_fp4','dtype':'bfloat16','max_model_len':config['max_model_len'],'gpu_memory_utilization':config['gpu_memory_utilization'],'max_num_seqs':1,'max_num_batched_tokens':8192,'enforce_eager':True,'enable_prefix_caching':False,'video_pruning_rate':0,'limit_mm_per_prompt':{'image':0,'video':1},'skip_mm_profiling':True,'seed':42}
    save(base/f'load_attempt_{attempt:02d}.json',{'settings':settings,'revision':config['revision'],'vllm_version_expected':config['vllm_version'],'runtime_source_sha256':sha(Path(__file__)),'dataset_freeze_sha256':sha(OUT/'dataset_freeze.json')})
    try:
        import numpy as np,torch,vllm
        from vllm import LLM,SamplingParams
        from transformers import AutoTokenizer
        from PIL import Image
        assert vllm.__version__==config['vllm_version']
        start=time.perf_counter();engine=LLM(**settings)
        tokenizer=AutoTokenizer.from_pretrained(ROOT/config['model_path'],local_files_only=True,trust_remote_code=True)
        processor=engine.llm_engine.input_processor.renderer.get_mm_processor().info.get_hf_processor()
        save(base/f'model_load_{attempt:02d}.json',{'seconds':time.perf_counter()-start,'torch':torch.__version__,'vllm':vllm.__version__,'capability':torch.cuda.get_device_capability(),'device':torch.cuda.get_device_name(),'resources':{'peak_allocated_gib':torch.cuda.max_memory_allocated()/2**30},'engine':settings})
    except Exception as e:
        save(base/f'load_failure_{attempt:02d}.json',{'classification':'ENGINEERING_BLOCKED_NO_MODEL_OUTPUT','error_type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc(),'resources':dict(resources),'not_executed_window_ids':[w['window_id'] for w in windows]});raise
    for w in windows:
        dest=base/w['window_id'];dest.mkdir(exist_ok=True)
        if (dest/'receipt.json').exists() or (dest/'failure.json').exists():continue
        if (dest/'started.json').exists() and not (dest/'raw.txt').exists():save(dest/'failure.json',{'error':'INTERRUPTED_UNKNOWN_GENERATION_STATE_NO_RETRY'});continue
        if (dest/'raw.txt').exists():
            if not (dest/'validation.json').exists():save(dest/'validation.json',validate_raw((dest/'raw.txt').read_text(encoding='utf8'),[f['alias'] for f in w['frames']]))
            save(dest/'receipt.json',{'completed':True,'recovered_raw':True,'raw_sha256':sha(dest/'raw.txt')});continue
        try:
            tick=time.perf_counter();images=[]
            for f in w['frames']:
                assert sha(ROOT/f['path'])==f['sha256']
                with Image.open(ROOT/f['path']) as im:images.append(np.asarray(im.convert('RGB')))
            array=np.stack(images)
            mapping='\n'.join(f'Video frame {i+1} corresponds exactly to alias {f["alias"]}, authoritative native source PTS {f["native_pts_s"]:.9f} seconds.' for i,f in enumerate(w['frames']))
            body=mapping+'\nVideo frame positions are ordinal selected frames; use the supplied native source PTS mapping.\n'+prompt['task']+'\nRequired JSON schema:\n'+json.dumps(schema,sort_keys=True)
            messages=[{'role':'system','content':prompt['system']+'\n/no_think'},{'role':'user','content':[{'type':'video','video':''},{'type':'text','text':body}]}]
            rendered=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
            source_timeline=read(OUT/'timelines'/f'{w["video_id"]}.json')
            video_metadata={'fps':source_timeline['source']['fps'],'total_num_frames':len(source_timeline['frames']),'duration':source_timeline['presentation_interval_half_open'][1]-source_timeline['presentation_interval_half_open'][0],'frames_indices':[f['source_frame_index'] for f in w['frames']],'video_backend':'PRESELECTED_SOURCE_PNGS','do_sample_frames':False}
            # Preview the identical official vLLM video processor used by this engine.
            preview=processor(text=[rendered],videos=[(array,video_metadata)],return_tensors='pt')
            actual=int(preview['pixel_values_flat_video'].shape[0]);assert actual==len(images),('HF_VIDEO_FRAME_COUNT_CHANGED',actual,len(images))
            input_record={'frames':w['frames'],'array_shape':list(array.shape),'array_sha256':hashlib.sha256(array.tobytes()).hexdigest(),'hf_video_tensor_shape':list(preview['pixel_values_flat_video'].shape),'submitted_frames':len(images),'hf_preview_consumed_frames':actual,'processor_class':type(processor).__name__,'rendered_text':rendered,'dataset_freeze_sha256':sha(OUT/'dataset_freeze.json'),'temporal_positions':'NATIVE_SOURCE_PTS_EXPLICIT_IN_TEXT; ENGINE_TIMESTAMPS_ROUNDED_FROM_RECORDED_SOURCE_FPS','video_pruning_rate':0,'engine_worker_attention_trace_available':False}
            save(dest/'input.json',input_record);del preview
            save(dest/'started.json',{'maximum_generations':1,'wall_time':time.time()})
            sampling=SamplingParams(temperature=0,seed=cfg['generation']['seed'],max_tokens=cfg['generation']['max_new_tokens'])
            save(dest/'video_transport.json',{'metadata':video_metadata,'vllm_internal_timestamp_rule':'floor(1000/source_fps) milliseconds * original source index; approximate, NOT authoritative native PTS','authoritative_native_pts_s':[f['native_pts_s'] for f in w['frames']],'representation_is_deployment_comparison_not_identical_internal_temporal_encoding':True})
            def deadline(signum,frame):raise TimeoutError('FROZEN_300_SECOND_GENERATION_TIMEOUT')
            previous_handler=signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,cfg['generation']['timeout_seconds'])
            try:result=engine.generate([{'prompt':rendered,'multi_modal_data':{'video':[(array,video_metadata)]}}],sampling,use_tqdm=False)[0]
            finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous_handler)
            response=result.outputs[0]
            with (dest/'raw.txt').open('xb') as f:f.write(response.text.encode('utf8'));f.flush();os.fsync(f.fileno())
            save(dest/'generation.json',{'generated_tokens':len(response.token_ids),'input_token_count':len(result.prompt_token_ids),'finish_reason':response.finish_reason,'eos_reached':response.finish_reason=='stop','token_cap_reached':response.finish_reason=='length','timeout_reached':False,'elapsed_s':time.perf_counter()-tick,'resources':dict(resources),'worker_gpu_memory_in_this_process':False})
            save(dest/'validation.json',validate_raw(response.text,[f['alias'] for f in w['frames']]))
            save(dest/'receipt.json',{'completed':True,'elapsed_s':time.perf_counter()-tick,'raw_sha256':sha(dest/'raw.txt'),'dataset_freeze_sha256':sha(OUT/'dataset_freeze.json'),'quality_retries':0});print('COMPLETED nemotron',w['window_id'],flush=True)
        except Exception as e:
            save(dest/'failure.json',{'error':str(e),'traceback':traceback.format_exc(),'raw_saved':(dest/'raw.txt').exists(),'quality_retry':False});print('FAILED nemotron',w['window_id'],str(e),flush=True)
            if isinstance(e,(TypeError,AttributeError,ImportError,TimeoutError)):raise
if __name__=='__main__':main()
