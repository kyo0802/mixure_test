"""Consolidated successful V2945 NF4 loader and unchanged generation method."""
import time,threading
from .common import ROOT,OUT,MODEL_ID,REVISION,MODEL_PATH,sha256,canonical_hash
class Monitor:
    def __init__(self):self.samples=[];self.stop_event=threading.Event()
    def sample(self):
        import torch,psutil
        free,total=torch.cuda.mem_get_info()
        self.samples.append({'monotonic':time.monotonic(),'global_gpu_used_bytes':total-free,
            'process_RSS_bytes':psutil.Process().memory_info().rss,'available_RAM_bytes':psutil.virtual_memory().available})
    def loop(self):
        while not self.stop_event.wait(.5):self.sample()
    def __enter__(self):self.sample();self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start();return self
    def __exit__(self,*args):self.stop_event.set();self.thread.join();self.sample()
    def result(self):
        return {'global_gpu_used_peak_bytes':max(s['global_gpu_used_bytes'] for s in self.samples),
            'process_RSS_peak_bytes':max(s['process_RSS_bytes'] for s in self.samples),
            'min_available_RAM_bytes':min(s['available_RAM_bytes'] for s in self.samples),'sample_interval_seconds':.5}

class Backend:
    def __init__(self):
        import torch
        from types import SimpleNamespace
        from transformers import AutoProcessor,AutoModelForImageTextToText,BitsAndBytesConfig
        self.config=SimpleNamespace(device='cuda',cpu_threads=4,cache_dir=str(OUT/'qwen/.vlm_cache'),revision=REVISION,
            local_files_only=True,model=str(ROOT/'.models/Qwen2.5-VL-7B-Instruct'),load_in_4bit=True,
            max_new_tokens=1400,image_longest_edge=800,max_inference_seconds=120,ground_entities_individually=False)
        self.device='cuda';self.mode='NF4_4BIT';self.resolved_revision=REVISION;torch.set_num_threads(4)
        kw={'cache_dir':self.config.cache_dir,'revision':REVISION,'local_files_only':True,'trust_remote_code':False}
        self.processor=AutoProcessor.from_pretrained(self.config.model,**kw)
        self.model=AutoModelForImageTextToText.from_pretrained(self.config.model,**kw,torch_dtype=torch.bfloat16,
            attn_implementation='sdpa',low_cpu_mem_usage=True,device_map={'':'cuda'},
            quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
                bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16)).eval()
        self.last_trace={}
    def identity(self):
        import torch,transformers
        from memory_graph.vlm.local_backend import LocalBackend
        return {'model_id':MODEL_ID,'local_path':str(MODEL_PATH),'revision':REVISION,'mode':self.mode,
            'dtype':str(self.model.dtype),'quantization':'NF4 double, BF16 compute' if self.mode=='NF4_4BIT' else 'none',
            'device_map':getattr(self.model,'hf_device_map',{}),'attention_implementation':self.model.config._attn_implementation,
            'transformers_version':transformers.__version__,'torch_version':torch.__version__,'CUDA_version':torch.version.cuda,
            'processor_class':type(self.processor.image_processor).__name__,'processor_config':self.processor.image_processor.to_dict(),
            'chat_template_sha256':canonical_hash(self.processor.chat_template),'generation_config':self.model.generation_config.to_dict(),
            'generation_overrides':{'do_sample':False,'max_new_tokens':1400,'timeout_seconds':120},
            'image_thumbnail_max':800,'generation_backend':'unchanged LocalBackend._generate',
            'SDPA_kernel_policy':'CUDNN_ATTENTION preferred; MATH fallback, no model/quantization change',
            'runtime_compatibility_correction':1,
            'generation_backend_sha256':sha256(ROOT/'src/memory_graph/vlm/local_backend.py')}

    def __call__(self,images,prompt,budget):
        import torch
        from PIL import Image
        from memory_graph.vlm.local_backend import LocalBackend
        loaded=[]
        for p in images:
            with Image.open(p) as im:loaded.append(im.convert('RGB'))
        original=self.model.generate;trace={}
        def capture(*args,**kwargs):
            trace.update(input_token_count=kwargs['input_ids'].shape[1],image_grid_thw=kwargs['image_grid_thw'].tolist(),
                pixel_tensor_shape=list(kwargs['pixel_values'].shape),do_sample=kwargs['do_sample'],max_new_tokens=kwargs['max_new_tokens'])
            result=original(*args,**kwargs);new=result[:,kwargs['input_ids'].shape[1]:]
            trace['generated_token_count']=new.shape[1];last=int(new[0,-1]) if new.shape[1] else None
            eos=self.model.generation_config.eos_token_id;eos=eos if isinstance(eos,list) else [eos]
            trace['ended_with_EOS']=last in eos
            return result
        self.model.generate=capture;torch.cuda.reset_peak_memory_stats();start=time.monotonic()
        failure=None
        try:
            from torch.nn.attention import sdpa_kernel,SDPBackend
            # Windows wheel lacks Flash Attention. Prefer available cuDNN SDPA
            # to avoid the quadratic FP32 math attention matrix on dense inputs.
            with Monitor() as mon, sdpa_kernel([SDPBackend.CUDNN_ATTENTION,SDPBackend.MATH],set_priority=True):
                raw=LocalBackend._generate(self,loaded,prompt,budget)
        except Exception as error:
            failure=type(error).__name__+': '+str(error)
            raise
        finally:
            self.model.generate=original
            trace.update(runtime_seconds=time.monotonic()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                peak_reserved_bytes=torch.cuda.max_memory_reserved(),error=failure,**mon.result())
            trace['deadline_or_token_cap_reached']=not trace.get('ended_with_EOS',False)
            self.last_trace=trace
        return raw
