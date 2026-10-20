"""Official pinned VideoLLaMA3 implementation behind ObservationAdapter.

Dependencies are imported only on load. No automatic download or Graph access.
"""
from __future__ import annotations
import gc,hashlib,json,os,subprocess,time
from pathlib import Path
from .observation_interface import AdapterValue,RawResponse

class VideoLLaMA3Adapter:
    def __init__(self,root:Path):self.root=root;self.model=None;self.processor=None
    def check_resources(self,*,load=False):
        import psutil
        row=subprocess.check_output(['nvidia-smi','--query-gpu=memory.free,memory.used','--format=csv,noheader,nounits'],text=True).strip().split(',')
        free,used=map(int,row);ram=psutil.virtual_memory().available/2**30
        if free<(10000 if load else 2048) or ram<(8 if load else 2) or (not load and used>14848):raise RuntimeError(f'HARDWARE_GATE free_vram_mib={free} used_vram_mib={used} free_ram_gib={ram:.2f}')
    def load(self,settings):
        for key,sub in {'HF_HOME':'huggingface','HF_MODULES_CACHE':'modules','TRANSFORMERS_CACHE':'transformers','TORCH_HOME':'torch','TMP':'tmp','TEMP':'tmp'}.items():
            p=self.root/'.runtime/videollama3'/sub;p.mkdir(parents=True,exist_ok=True);os.environ[key]=str(p)
        os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
        self.check_resources(load=True)
        import torch,transformers,bitsandbytes
        from transformers import AutoModelForCausalLM,AutoProcessor,BitsAndBytesConfig
        self.torch=torch;started=time.perf_counter()
        path=self.root/settings['model_path']
        self.processor=AutoProcessor.from_pretrained(path,trust_remote_code=True,local_files_only=True)
        self.processor.image_processor.max_tokens=settings['preprocessing']['max_visual_tokens_total']
        self.processor.image_processor.min_tokens=settings['preprocessing']['min_visual_tokens']
        quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16,llm_int8_skip_modules=['model.vision_encoder','model.mm_projector','lm_head'])
        self.model=AutoModelForCausalLM.from_pretrained(path,trust_remote_code=True,local_files_only=True,torch_dtype=torch.bfloat16,device_map={'':'cuda:0'},quantization_config=quant,attn_implementation='sdpa',low_cpu_mem_usage=True).eval()
        modules=[n for n,m in self.model.named_modules() if isinstance(m,bitsandbytes.nn.Linear4bit)]
        assert modules and not any('vision_encoder' in n or 'mm_projector' in n for n in modules),'SELECTIVE_QUANTIZATION_NOT_RESPECTED'
        vision_dtypes=sorted({str(p.dtype) for n,p in self.model.named_parameters() if 'vision_encoder' in n})
        assert vision_dtypes==['torch.bfloat16'],vision_dtypes
        return {'model':settings['model'],'revision':settings['revision'],'transformers':transformers.__version__,'torch':torch.__version__,'bitsandbytes':bitsandbytes.__version__,'attention':'OFFICIAL_SDPA','linear4bit_module_count':len(modules),'quantized_vision_or_projector':False,'vision_parameter_dtypes':vision_dtypes,'load_seconds':time.perf_counter()-started,'device_map':self.model.hf_device_map,'resources':self.resources()}
    def render(self,request):
        content=[]
        for f in request.frames:
            content.extend([{'type':'text','text':f.alias},{'type':'image','image':{'image_path':str(f.path)}}])
        content.append({'type':'text','text':request.task_instruction+'\nOutput JSON schema:\n'+json.dumps(request.output_schema,ensure_ascii=False)})
        conversation=[{'role':'system','content':request.system_instruction},{'role':'user','content':content}]
        text=self.processor.apply_chat_template(conversation,tokenize=False,add_system_prompt=True,add_generation_prompt=True)
        # Official template renders image placeholders, never local path names.
        assert str(self.root) not in text,'LOCAL_PATH_LEAK'
        return AdapterValue(conversation,{'rendered_text':text,'rendered_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'supplied_aliases':[f.alias for f in request.frames],'task_and_schema_shared_with_qwen_c':True})
    def preprocess(self,frames,rendered,settings):
        inputs=self.processor(conversation=rendered.data,add_system_prompt=True,add_generation_prompt=True,return_tensors='pt')
        grids=inputs['grid_sizes'].tolist();merges=inputs['merge_sizes'].tolist()
        assert len(grids)==len(frames),'PROCESSOR_FRAME_COUNT_MISMATCH'
        metadata={'consumed_aliases':[f.alias for f in frames],'grid_sizes':grids,'merge_sizes':merges,'modals':inputs['modals'],'global_visual_token_budget':settings['max_visual_tokens_total'],'actual_visual_tokens':sum(t*(h//m)*(w//m) for (t,h,w),m in zip(grids,merges)),'tensors':{k:{'shape':list(v.shape),'dtype':str(v.dtype),'sha256_cpu_bytes':hashlib.sha256(v.contiguous().view(self.torch.uint8).numpy().tobytes()).hexdigest()} for k,v in inputs.items() if hasattr(v,'shape')},'temporal_representation':'CHRONOLOGICAL_INDEPENDENT_IMAGES_NO_NATIVE_VIDEO_RESAMPLING'}
        inputs={k:v.to(device='cuda:0',dtype=self.torch.bfloat16 if v.is_floating_point() else v.dtype) if hasattr(v,'to') else v for k,v in inputs.items()}
        return AdapterValue(inputs,metadata)
    def generate(self,prepared,rendered,generation):
        torch=self.torch;torch.manual_seed(generation['seed']);torch.cuda.manual_seed_all(generation['seed']);torch.cuda.reset_peak_memory_stats()
        from transformers import StoppingCriteria,StoppingCriteriaList
        started=time.perf_counter();deadline=started+generation['timeout_seconds']
        class Deadline(StoppingCriteria):
            def __call__(self,input_ids,scores,**kwargs):return time.perf_counter()>deadline
        with torch.inference_mode():
            ids=self.model.generate(**prepared.data,do_sample=False,max_new_tokens=generation['max_new_tokens'],use_cache=True,stopping_criteria=StoppingCriteriaList([Deadline()]))
        torch.cuda.synchronize();elapsed=time.perf_counter()-started
        text=self.processor.batch_decode(ids,skip_special_tokens=True)[0]
        eos=self.model.generation_config.eos_token_id;eos=[eos] if isinstance(eos,int) else (eos or [])
        return RawResponse(text,{'elapsed_s':elapsed,'generated_tokens':int(ids.shape[-1]),'output_token_ids':ids[0].tolist(),'eos_reached':int(ids[0,-1]) in eos,'timeout_reached':elapsed>generation['timeout_seconds'],'token_cap_reached':int(ids.shape[-1])>=generation['max_new_tokens'],'decode_policy':'OFFICIAL_DECODE_ALL_GENERATED_IDS_INPUTS_EMBEDS_PATH','resources':self.resources(),'quality_retries':0})
    def resources(self):
        import psutil
        t=getattr(self,'torch',None)
        return {'process_rss_gib':psutil.Process().memory_info().rss/2**30,'free_ram_gib':psutil.virtual_memory().available/2**30,**({'gpu_allocated_gib':t.cuda.memory_allocated()/2**30,'gpu_reserved_gib':t.cuda.memory_reserved()/2**30,'gpu_peak_allocated_gib':t.cuda.max_memory_allocated()/2**30} if t is not None else {})}
    def cleanup(self):
        gc.collect()
        if getattr(self,'torch',None) is not None:self.torch.cuda.empty_cache()
    def close(self):
        self.model=None;self.processor=None;self.cleanup()
