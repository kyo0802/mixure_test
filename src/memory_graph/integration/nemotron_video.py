"""Parameterized existing vLLM Nemotron NVFP4 video-array deployment.

The historical benchmark launcher is untouched. This worker consumes only the
current session's source images and canonical observation contract.
"""
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import time
import traceback
from .adapters import read,sha
from .fresh_video import save
from .nemotron_assets import verify_existing
from .runtime_timing import Trace

MODEL_CONFIG=dict(repository='nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-NVFP4-QAD',
    revision='16853d6c682223e967d5622c99d0082cb994b771',vllm_version='0.31.0',
    model_path='.models/Nemotron-Nano-12B-v2-VL-NVFP4-QAD',quantization='modelopt_fp4',
    max_model_len=8192,gpu_memory_utilization=.85,max_num_seqs=1,video_pruning_rate=0)


def run(root,session):
    from memory_graph.experiments.three_vlm_contract import validate_raw
    manifest=read(session/'source_manifest.json');contract=read(session/'vlm/contract.json');video=manifest['video']
    windows=manifest['windows'];base=session/'vlm';start=time.monotonic()
    trace=Trace(base/'timing.jsonl',MODEL_CONFIG['revision'])
    trace.event('worker_run_entry',lifecycle='COLD_PROCESS_PER_VIDEO',resident_across_jobs=False)
    discovery=time.monotonic()
    model=root/MODEL_CONFIG['model_path']
    if not model.is_dir():raise FileNotFoundError('EXISTING_NEMOTRON_NVFP4_REQUIRED')
    free=int(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip().splitlines()[0])
    if free<10240:raise RuntimeError('NEMOTRON_REQUIRES_10_GIB_FREE_VRAM')
    trace.event('asset_discovery_and_resource_gate',seconds=time.monotonic()-discovery,free_vram_mib=free)
    settings=dict(model=str(model),trust_remote_code=True,quantization='modelopt_fp4',dtype='bfloat16',
        max_model_len=8192,gpu_memory_utilization=.85,max_num_seqs=1,max_num_batched_tokens=8192,
        enforce_eager=True,enable_prefix_caching=False,video_pruning_rate=0,
        limit_mm_per_prompt={'image':0,'video':1},skip_mm_profiling=True,seed=42)
    with trace.span('model_asset_verification'):
        verification=verify_existing(root)
    save(base/'asset_verification.json',verification)
    trace.event('asset_verification_result',validation_kind=verification['validation_kind'],
        fresh_files=len(verification['fresh_files']),cached_files=len(verification['cached_files']))
    save(base/'runtime.json',dict(model=MODEL_CONFIG,settings=settings,generation=dict(temperature=0,seed=42,max_tokens=1536,timeout_s=300),
        contract_sha256=sha(base/'contract.json'),manifest_sha256=sha(session/'source_manifest.json'),
        model_asset_hashes=verification['asset_hashes'],asset_verification_kind=verification['validation_kind'],
        asset_manifest_sha256=verification['manifest_sha256']))
    imports=time.monotonic()
    import numpy as np
    import torch
    import vllm
    from vllm import LLM,SamplingParams
    from transformers import AutoTokenizer
    from PIL import Image
    trace.event('runtime_imports',seconds=time.monotonic()-imports)
    if vllm.__version__!=MODEL_CONFIG['vllm_version']:raise RuntimeError('VLLM_VERSION_CHANGED')
    with trace.span('engine_init_including_cuda_weights_kv',lifecycle='COLD_ENGINE'):
        engine=LLM(**settings)
    with trace.span('tokenizer_and_processor_configuration'):
        tokenizer=AutoTokenizer.from_pretrained(model,local_files_only=True,trust_remote_code=True)
        processor=engine.llm_engine.input_processor.renderer.get_mm_processor().info.get_hf_processor()
    trace.event('engine_ready',allocated_vram_bytes=torch.cuda.memory_allocated(),
        peak_allocated_vram_bytes=torch.cuda.max_memory_allocated(),
        limitation='Engine subprocess memory is reported by vLLM logs, not this parent torch counter')
    save(base/'load.json',dict(seconds=time.monotonic()-start,torch=torch.__version__,vllm=vllm.__version__,
        device=torch.cuda.get_device_name(),configuration=settings))
    completed=0
    for w in windows:
        dest=base/w['window_id'];dest.mkdir(exist_ok=False)
        try:
            tick=time.monotonic();images=[]
            for f in w['frames']:
                path=root/f['path'].replace('\\','/')
                if sha(path)!=f['sha256']:raise ValueError('FRAME_HASH_MISMATCH')
                with Image.open(path) as im:images.append(np.asarray(im.convert('RGB')))
            array=np.stack(images)
            mapping='\n'.join(f'Video frame {i+1} corresponds exactly to alias {f["alias"]}, authoritative native source PTS {f["native_pts_s"]:.9f} seconds.' for i,f in enumerate(w['frames']))
            body=mapping+'\nVideo frame positions are ordinal selected frames; use the supplied native source PTS mapping.\n'+contract['prompt']['task']+'\nRequired JSON schema:\n'+__import__('json').dumps(contract['schema'],sort_keys=True)
            messages=[dict(role='system',content=contract['prompt']['system']+'\n/no_think'),
                dict(role='user',content=[dict(type='video',video=''),dict(type='text',text=body)])]
            rendered=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
            metadata=dict(fps=video['fps'],total_num_frames=video['frame_count'],duration=video['presentation_duration_s'],
                frames_indices=[f['source_frame_index'] for f in w['frames']],video_backend='PRESELECTED_SOURCE_PNGS',do_sample_frames=False)
            preview=processor(text=[rendered],videos=[(array,metadata)],return_tensors='pt')
            actual=int(preview['pixel_values_flat_video'].shape[0])
            if actual!=len(images):raise ValueError('PROCESSOR_FRAME_COUNT_CHANGED')
            save(dest/'input.json',dict(frames=w['frames'],array_shape=list(array.shape),array_sha256=hashlib.sha256(array.tobytes()).hexdigest(),
                hf_video_tensor_shape=list(preview['pixel_values_flat_video'].shape),submitted_frames=len(images),hf_preview_consumed_frames=actual,
                rendered_text=rendered,rendered_sha256=hashlib.sha256(rendered.encode()).hexdigest(),video_metadata=metadata,
                processor_class=type(processor).__name__,native_pts_authoritative=True,
                temporal_limitation='vLLM internal timestamps are FPS-derived approximations; explicit native source PTS in text are authoritative',
                engine_attention_trace_available=False,source_sha256=video['source_sha256']))
            del preview
            trace.event('request_preparation',seconds=time.monotonic()-tick,window=w['window_id'],
                lifecycle='FIRST_REQUEST' if completed==0 else 'WARM_SEQUENTIAL_WINDOW')
            save(dest/'started.json',dict(maximum_generations=1,wall_time=time.time(),quality_retries=0))
            def deadline(signum,frame):raise TimeoutError('NEMOTRON_GENERATION_300_SECONDS')
            previous=signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,300)
            try:
                with trace.span('generation',window=w['window_id'],
                        lifecycle='FIRST_REQUEST' if completed==0 else 'WARM_SEQUENTIAL_WINDOW'):
                    result=engine.generate([dict(prompt=rendered,multi_modal_data={'video':[(array,metadata)]})],
                        SamplingParams(temperature=0,seed=42,max_tokens=1536),use_tqdm=False)[0]
            finally:
                signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
            serialization=time.monotonic();response=result.outputs[0]
            with (dest/'raw.txt').open('xb') as f:f.write(response.text.encode('utf8'));f.flush();os.fsync(f.fileno())
            save(dest/'validation.json',validate_raw(response.text,[f['alias'] for f in w['frames']]))
            save(dest/'generation.json',dict(generated_tokens=len(response.token_ids),input_tokens=len(result.prompt_token_ids),
                finish_reason=response.finish_reason,elapsed_s=time.monotonic()-tick,raw_sha256=sha(dest/'raw.txt'),
                native_pts_s=[f['native_pts_s'] for f in w['frames']],quality_retries=0))
            trace.event('output_serialization_and_validation',seconds=time.monotonic()-serialization,window=w['window_id'])
            completed+=1;print('NEMOTRON_COMPLETE '+w['window_id'],flush=True)
        except Exception as exc:
            save(dest/'failure.json',dict(error=str(exc),traceback=traceback.format_exc(),raw_saved=(dest/'raw.txt').exists(),invalid_is_not_no_event=True))
            save(base/'receipt.json',dict(completed=completed,requested=len(windows),stopped=True,elapsed_s=time.monotonic()-start,
                not_executed=[x['window_id'] for x in windows if not (base/x['window_id']/'started.json').exists()]))
            raise
    trace.event('all_windows_complete_before_process_shutdown',completed=completed)
    save(base/'receipt.json',dict(completed=completed,requested=len(windows),elapsed_s=time.monotonic()-start,
        representation='OFFICIAL_VIDEO_ARRAY',historical_outputs_reused=False))
