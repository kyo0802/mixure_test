"""Experiment adapters; historical runtimes are reused without edits."""
from pathlib import Path
import os,json,hashlib,time,gc
from .observation_interface import AdapterValue,RawResponse
from .videollama3_adapter import VideoLLaMA3Adapter
def label(i,f):return f'Image {i+1} corresponds exactly to alias {f.alias}, native source PTS {f.native_pts_s:.9f} seconds.'
def task(request):return request.task_instruction+'\nRequired JSON schema:\n'+json.dumps(request.output_schema,sort_keys=True)
class VideoLLaMAFullAdapter(VideoLLaMA3Adapter):
    def render(self,request):
        content=[]
        for i,f in enumerate(request.frames):content.extend([{'type':'text','text':label(i,f)},{'type':'image','image':{'image_path':str(f.path)}}])
        content.append({'type':'text','text':task(request)})
        conv=[{'role':'system','content':request.system_instruction},{'role':'user','content':content}]
        text=self.processor.apply_chat_template(conv,tokenize=False,add_system_prompt=True,add_generation_prompt=True)
        return AdapterValue(conv,{'rendered_text':text,'rendered_sha256':hashlib.sha256(text.encode()).hexdigest(),'model_transport':'OFFICIAL_VIDEOLLAMA_MULTIMAGE','consumed_aliases':[f.alias for f in request.frames]})
class QwenFullAdapter(VideoLLaMA3Adapter):
    def load(self,settings):
        for k in ('HF_HOME','HF_MODULES_CACHE','TORCH_HOME','TMP','TEMP','TRITON_CACHE_DIR'):
            p=self.root/'.runtime/three_vlm_qwen'/k;p.mkdir(parents=True,exist_ok=True);os.environ[k]=str(p)
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PASS_T_LOCAL_RUNTIME_APPROVAL='true',TOKENIZERS_PARALLELISM='false')
        self.check_resources(load=True)
        from memory_graph.pass_t.phase2b.local_vlm.nf4 import QwenNF4Runtime
        from memory_graph.pass_t.phase2b.local_vlm.catalog import SPECS
        import torch
        self.torch=torch;owner=self
        class Runtime(QwenNF4Runtime):
            def preprocess(self,envelope):return envelope['prepared'].data,envelope['prepared'].metadata
        deploy={'approved':True,'processor_max_pixels':settings['processor_max_pixels'],'generation_timeout_seconds':300,'asset_audit_path':str(self.root/'artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c/model_assets.json')}
        self.runtime=Runtime(SPECS['qwen_nf4'],deploy,self.root/settings['model_path'],None);self.processor=self.runtime.processor;self.model=self.runtime.model
        return self.runtime.health()
    def render(self,request):
        from PIL import Image
        images=[];content=[]
        for i,f in enumerate(request.frames):
            with Image.open(f.path) as im:images.append(im.convert('RGB'))
            content.extend([{'type':'text','text':label(i,f)},{'type':'image','image':images[-1]}])
        content.append({'type':'text','text':task(request)})
        text=self.processor.apply_chat_template([{'role':'system','content':request.system_instruction},{'role':'user','content':content}],tokenize=False,add_generation_prompt=True)
        return AdapterValue((text,images,[f.alias for f in request.frames]),{'rendered_text':text,'rendered_sha256':hashlib.sha256(text.encode()).hexdigest(),'model_transport':'OFFICIAL_QWEN_MULTIMAGE'})
    def preprocess(self,frames,rendered,settings):
        text,images,aliases=rendered.data
        inputs=self.processor(text=[text],images=images,padding=True,return_tensors='pt')
        from memory_graph.pass_t.phase2b.local_vlm.qwen_contract import grid_accounting
        from memory_graph.pass_t.phase2b.local_vlm.video_array_bridge import tensor_record
        grid=grid_accounting(inputs);assert len(inputs['image_grid_thw'])==len(frames)
        return AdapterValue(inputs,{'consumed_aliases':aliases,'grid':grid,'tensors':{k:tensor_record(v) for k,v in inputs.items()},'source_dimensions':[list(im.size) for im in images],'effective_temporal_representation':'INDEPENDENT_CHRONOLOGICAL_IMAGES'})
    def generate(self,prepared,rendered,generation):
        response=self.runtime.generate({'prepared':prepared,'generation':{'sampling':False,'seed':generation['seed'],'max_output_tokens':generation['max_new_tokens']}})
        raw=response.pop('raw_output');response.update(elapsed_s=response['runtime_seconds'],eos_reached=response['eos_observed'],token_cap_reached=response['output_cap_reached'],timeout_reached=response['generation_deadline_reached'],resources=self.resources())
        return RawResponse(raw,response)
    def close(self):
        self.runtime=None;super().close()
