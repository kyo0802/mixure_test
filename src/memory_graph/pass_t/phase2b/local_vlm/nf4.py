"""Authorized existing Qwen NF4 loader; reuses generic local runtime generation."""
from __future__ import annotations
import json
import importlib.metadata
import time
import base64
import tempfile
from pathlib import Path
from ..common import Phase2BBlocked, file_sha256, environment_bool
from .runtime import QwenAWQRuntime

BASELINE_ID = "QWEN25_VL_7B_INSTRUCT_NF4_BF16_SDPA"

def verify_assets(snapshot: Path, *, hash_files=True):
    required = ["config.json", "model.safetensors.index.json", "preprocessor_config.json", "tokenizer.json",
                "tokenizer_config.json", "chat_template.json", "download_provenance.json"]
    for name in required:
        if not (snapshot / name).is_file():
            raise Phase2BBlocked("MISSING_PROCESSOR_TOKENIZER_OR_CONFIG:" + name)
    provenance=json.loads((snapshot/"download_provenance.json").read_text(encoding="utf8"))
    if provenance.get("repository")!="Qwen/Qwen2.5-VL-7B-Instruct" or provenance.get("revision")!="cc594898137f460bfe9f0759e9844b3ce807cfb5":
        raise Phase2BBlocked("NF4_REVISION_PROVENANCE_MISMATCH")
    config=json.loads((snapshot/"config.json").read_text(encoding="utf8"))
    if config.get("model_type")!="qwen2_5_vl" or config.get("quantization_config"):
        raise Phase2BBlocked("ORIGINAL_INSTRUCT_CHECKPOINT_REQUIRED_NOT_AWQ")
    index=json.loads((snapshot/"model.safetensors.index.json").read_text(encoding="utf8"))
    shards=sorted(set(index["weight_map"].values()))
    from safetensors import safe_open
    tensor_count=0
    for name in shards:
        if Path(name).name!=name or not (snapshot/name).is_file():
            raise Phase2BBlocked("MISSING_OR_UNSAFE_WEIGHT_SHARD:"+name)
        with safe_open(snapshot/name,framework="pt",device="cpu") as handle:
            keys=set(handle.keys()); tensor_count+=len(keys)
            expected={key for key,value in index["weight_map"].items() if value==name}
            if keys!=expected:
                raise Phase2BBlocked("SAFETENSORS_INDEX_KEY_MISMATCH")
    hashes={p.name:file_sha256(p) for p in snapshot.iterdir() if p.is_file()} if hash_files else {}
    return {"baseline_id":BASELINE_ID,"path":str(snapshot),"model":provenance["repository"],
            "revision":provenance["revision"],"revision_evidence":"LOCAL_DOWNLOAD_PROVENANCE_AND_HISTORICAL_CONFIG; NOT_INDEPENDENT_UPSTREAM_CHECKSUM_ATTESTATION",
            "authoritative_weight_checksum_available":False,"files_sha256":hashes,"shards":shards,
            "weight_bytes":sum((snapshot/name).stat().st_size for name in shards),"tensor_count":tensor_count}

class QwenNF4Runtime(QwenAWQRuntime):
    def __init__(self,spec,deployment,snapshot,metadata_manifest):
        if not environment_bool("PASS_T_LOCAL_RUNTIME_APPROVAL") or deployment.get("approved") is not True:
            raise Phase2BBlocked("MODEL_LOAD_REQUIRES_RUNTIME_APPROVAL")
        verify_assets(snapshot,hash_files=False)
        from ..common import read_json
        audit=read_json(Path(deployment["asset_audit_path"]))
        for name,expected in audit["files_sha256"].items():
            if file_sha256(snapshot/name)!=expected:
                raise Phase2BBlocked("NF4_ASSET_HASH_CHANGED:"+name)
        import torch,psutil
        from transformers import AutoProcessor,AutoModelForImageTextToText,BitsAndBytesConfig
        if not torch.cuda.is_available() or torch.cuda.mem_get_info()[0] < 10*2**30 or psutil.virtual_memory().available < 8*2**30:
            raise Phase2BBlocked("NF4_LOAD_HEADROOM_REQUIRES_10GIB_GPU_8GIB_RAM")
        torch.set_num_threads(4)
        self.spec=spec;self.deployment=deployment;self.tested_representations=[]
        torch.cuda.reset_peak_memory_stats();started=time.perf_counter()
        self.processor=AutoProcessor.from_pretrained(snapshot,local_files_only=True,trust_remote_code=False,
                                                     max_pixels=deployment["processor_max_pixels"])
        self.model=AutoModelForImageTextToText.from_pretrained(snapshot,local_files_only=True,trust_remote_code=False,
            torch_dtype=torch.bfloat16,attn_implementation="sdpa",low_cpu_mem_usage=True,device_map={"":"cuda"},
            quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16)).eval()
        torch.cuda.synchronize()
        self.load_seconds=time.perf_counter()-started;self.load_peak_bytes=torch.cuda.max_memory_allocated()
        quant=self.model.config.quantization_config.to_dict()
        if not self.model.is_loaded_in_4bit or quant.get("bnb_4bit_quant_type")!="nf4" or quant.get("bnb_4bit_use_double_quant") is not True or "bfloat16" not in str(quant.get("bnb_4bit_compute_dtype")):
            raise Phase2BBlocked("EFFECTIVE_NF4_SETTINGS_MISMATCH")
        if self.model.config._attn_implementation!="sdpa":raise Phase2BBlocked("EFFECTIVE_ATTENTION_CHANGED")
        self.effective={"baseline_id":BASELINE_ID,"quantization_config":quant,"device_map":self.model.hf_device_map,
            "attention":"sdpa","sdpa_kernel_policy":"CUDNN_ATTENTION preferred, MATH fallback",
            "bitsandbytes_version":importlib.metadata.version("bitsandbytes"),"torch_version":torch.__version__,
            "cuda_runtime":torch.version.cuda,"processor":self.processor.image_processor.to_dict(),
            "transformers_version":importlib.metadata.version("transformers"),"cpu_offload":False}

    def health(self):
        return {**super().health(),"effective_runtime":self.effective,"real_model":True}

    def generate(self,envelope):
        import torch
        from torch.nn.attention import sdpa_kernel,SDPBackend
        if torch.cuda.mem_get_info()[0]<2*2**30:raise Phase2BBlocked("NF4_INFERENCE_HEADROOM_REQUIRES_2GIB_FREE")
        with sdpa_kernel([SDPBackend.CUDNN_ATTENTION,SDPBackend.MATH],set_priority=True):
            result=self.generate_common(envelope)
        result.update(baseline_id=BASELINE_ID,real_model=True,peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                      gpu_free_total_bytes=list(torch.cuda.mem_get_info()))
        return result

    def generate_video(self,envelope):
        """Compatibility method; native video uses the common NF4 contract."""
        return self.generate_common(envelope)

    def preprocess(self,envelope):
        """CPU/native processor path, also usable without constructing a model."""
        # Explicit local in-process extension. Historical AVI/image behavior is
        # the default; current HTTP transport does not accept native arrays.
        mode=self.deployment.get('video_input_mode','NATIVE_VIDEO_ARRAY_DISABLED')
        if mode not in {'NATIVE_VIDEO_ARRAY_DISABLED','NATIVE_ARRAY_EXPERIMENTAL'}:
            raise Phase2BBlocked('UNSUPPORTED_VIDEO_INPUT_MODE_NO_FALLBACK')
        if mode=='NATIVE_ARRAY_EXPERIMENTAL':
            from .video_array_bridge import prepare_video_array
            return prepare_video_array(self.processor,envelope,self.deployment)
        if 'native_video_array' in envelope:
            raise Phase2BBlocked('NATIVE_VIDEO_ARRAY_DISABLED_NO_SILENT_FALLBACK')
        import io
        from PIL import Image
        from .qwen_contract import messages,processor_size,grid_accounting
        from transformers.video_utils import VideoMetadata
        import av
        payload=envelope['payload'];blobs={r['media_id']:base64.b64decode(r['base64'],validate=True) for r in envelope['media']}
        schema=json.loads((Path(__file__).parents[1]/'contracts/prediction_v1.json').read_text(encoding='utf8'))
        size=processor_size(self.deployment['processor_max_pixels'])
        # Installed fast-image defaults can override per-call size with min/max;
        # video consumes size directly. Pin both attribute families explicitly.
        for processor in [self.processor.image_processor,self.processor.video_processor]:
            processor.size=dict(size);processor.min_pixels=3136;processor.max_pixels=self.deployment['processor_max_pixels']
        video_rows=[r for r in payload['media'] if r['media_type']=='video/x-msvideo']
        if len(video_rows)>1:raise Phase2BBlocked('EXACTLY_ONE_NATIVE_VIDEO_SUPPORTED')
        video=bool(video_rows);assets=[];images=[];observed={};selected_aliases=None;encoded_pts=[]
        staging=Path(self.deployment['scratch_path']);staging.mkdir(parents=True,exist_ok=True)
        started=time.perf_counter()
        with tempfile.TemporaryDirectory(dir=staging) as temporary:
            for row in payload['media']:
                if row['media_type']=='video/x-msvideo':
                    clip=Path(temporary)/'NEUTRAL_CLIP.avi';clip.write_bytes(blobs[row['media_id']])
                    with av.open(str(clip)) as c:
                        stream=c.streams.video[0];fps=float(stream.average_rate)
                        encoded_pts=[float(f.pts*f.time_base) for f in c.decode(video=0)]
                    aliases=row['supplied_frame_aliases']
                    if len(encoded_pts)!=len(aliases):raise Phase2BBlocked('ENCODED_VIDEO_ALIAS_COUNT_MISMATCH')
                    metadata=VideoMetadata(total_num_frames=len(encoded_pts),fps=fps,duration=len(encoded_pts)/fps)
                    selected=self.processor.video_processor.sample_frames(metadata=metadata,fps=self.deployment.get('processor_video_fps',4.0)).tolist()
                    selected_aliases=[aliases[j] for j in selected];assets.append(clip)
                    observed.update(encoded_frame_count=len(encoded_pts),decoded_frame_count=len(encoded_pts),
                                    processor_selected_indices=selected,selected_encoded_timestamps_s=[encoded_pts[j] for j in selected],
                                    encoded_fps=fps,native_video_modality=True)
                else:
                    image=Image.open(io.BytesIO(blobs[row['media_id']])).convert('RGB');images.append(image);assets.append(image)
            conversation,contract,prompt_hash=messages(payload,assets,schema,self.deployment.get('response_format_system'),selected_aliases)
            rendered=self.processor.apply_chat_template(conversation,tokenize=False,add_generation_prompt=True)
            if video:
                original=self.processor.video_processor.sample_frames
                def observe(*args,**kwargs):
                    result=original(*args,**kwargs);observed['actually_selected_indices']=result.tolist();return result
                self.processor.video_processor.sample_frames=observe
                try:
                    inputs=self.processor.apply_chat_template(conversation,tokenize=True,add_generation_prompt=True,return_dict=True,
                        return_tensors='pt',fps=self.deployment.get('processor_video_fps',4.0),do_sample_frames=True,device='cpu',
                        )
                finally:self.processor.video_processor.sample_frames=original
                if observed.get('actually_selected_indices')!=observed['processor_selected_indices']:
                    raise Phase2BBlocked('VIDEO_SAMPLE_METADATA_PROCESSOR_MISMATCH')
                processed=selected_aliases
            else:
                inputs=self.processor(text=[rendered],images=images,padding=True,return_tensors='pt',device='cpu')
                processed=list(dict.fromkeys(a for r in payload['media'] for a in r['supplied_frame_aliases']))
            accounting=grid_accounting(inputs)
            for values in accounting['per_grid_spatial_pixels'].values():
                if any(v>self.deployment['processor_max_pixels'] for v in values):
                    raise Phase2BBlocked('PROCESSOR_EFFECTIVE_PIXEL_BUDGET_UNRESOLVED')
        return inputs,{'processor_seconds':time.perf_counter()-started,'prompt_contract':contract,'prompt_contract_sha256':prompt_hash,
            'rendered_prompt':rendered,'rendered_prompt_sha256':__import__('hashlib').sha256(rendered.encode()).hexdigest(),
            'processed_frame_aliases':processed,'processor_frame_count':len(processed),'input_image_dimensions':[list(im.size) for im in images],
            'reference_image_count':sum(r['media_id'].startswith('REFERENCE_') for r in payload['media']),
            'configured_pixel_cap':self.deployment['processor_max_pixels'],**accounting,**observed}

    def generate_common(self,envelope):
        import torch
        from .qwen_contract import generation_controls
        from .catalog import runtime_error
        total_started=time.perf_counter();inputs,receipt=self.preprocess(envelope)
        kwargs,seed=generation_controls(envelope['generation'],self.deployment['generation_timeout_seconds'])
        if seed is not None:torch.manual_seed(seed)
        count=int(inputs['input_ids'].shape[-1]);context=self.model.config.max_position_embeddings
        if count+kwargs['max_new_tokens']>context:raise Phase2BBlocked('INPUT_PLUS_OUTPUT_EXCEEDS_MODEL_CONTEXT')
        inputs={k:v.to('cuda') if hasattr(v,'to') else v for k,v in inputs.items()}
        for k in ('pixel_values','pixel_values_videos'):
            if k in inputs:inputs[k]=inputs[k].to(self.model.dtype)
        prefill={};forward_start={}
        def pre(module,args):
            if 'seconds' not in prefill:torch.cuda.synchronize();forward_start['time']=time.perf_counter()
        def post(module,args,output):
            if 'seconds' not in prefill:torch.cuda.synchronize();prefill['seconds']=time.perf_counter()-forward_start['time']
        a=self.model.register_forward_pre_hook(pre);b=self.model.register_forward_hook(post)
        torch.cuda.reset_peak_memory_stats();started=time.perf_counter()
        try:
            with torch.inference_mode():generated=self.model.generate(**inputs,**kwargs)
            torch.cuda.synchronize()
        except Exception as error:raise Phase2BBlocked(runtime_error(error)+':'+str(error)) from error
        finally:a.remove();b.remove()
        seconds=time.perf_counter()-started;new=generated[:,count:]
        ids=new[0].tolist();eos=self.model.generation_config.eos_token_id
        eos_set={eos} if isinstance(eos,int) else set(eos or [])
        eos_seen=bool(ids and ids[-1] in eos_set)
        raw=self.processor.batch_decode(new,skip_special_tokens=True,clean_up_tokenization_spaces=False)[0]
        # Strict parser is called by transport/probe after raw bytes are durably stored.
        return {'model':self.spec.model,'revision':self.spec.revision,'quantization':self.spec.quantization,
            'raw_output':raw,'input_token_count':count,'context_limit':context,'context_headroom_after_output_cap':context-count-kwargs['max_new_tokens'],
            'generated_tokens':len(ids),'last_generated_token_id':ids[-1] if ids else None,'eos_token_ids':sorted(eos_set),'eos_observed':eos_seen,
            'output_cap_reached':len(ids)>=kwargs['max_new_tokens'],'generation_deadline_reached':not eos_seen and seconds>=kwargs['max_time'],
            'generation_controls':kwargs,'seed_applied':seed,'seed_guarantees_determinism':False,'runtime_seconds':seconds,
            'prefill_first_model_forward_seconds':prefill.get('seconds'),'prefill_scope':'vision+first complete model forward; independent hooks/synchronize',
            'decode_and_generation_overhead_seconds':seconds-prefill.get('seconds',0),'request_total_seconds':time.perf_counter()-total_started,
            'peak_inference_vram_bytes':torch.cuda.max_memory_allocated(),'cpu_offload_used':False,**receipt}
