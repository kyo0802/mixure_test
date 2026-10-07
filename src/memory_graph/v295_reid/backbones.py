"""Inference-only official backbones on identical canonical observations."""
import gc
import importlib.metadata
import time
import numpy as np
from PIL import Image
from .io import ROOT, OUT, read, save, sha

MODELS={'mobilenet':'torchvision/mobilenet_v3_small-047dcff4',
        'dinov2':'facebook/dinov2-base','dinov3':'facebook/dinov3-vitb16-pretrain-lvd1689m'}


class Backbone:
    def __init__(self,name):
        import torch
        torch.set_num_threads(4)
        if not torch.cuda.is_available():raise RuntimeError('V295 benchmark requires CUDA')
        self.torch=torch;self.name=name;self.device='cuda';self.methods=set()
        torch.cuda.reset_peak_memory_stats()
        if name=='mobilenet':
            from memory_graph.v24.appearance import MobileNetEmbedder
            self.extractor=MobileNetEmbedder();self.extractor.cache_dir=OUT/'benchmark/mobile_native_cache';self.extractor.cache_dir.mkdir(parents=True,exist_ok=True)
            self.model=self.extractor.model;self.processor=None;self.revision=self.extractor.weight_sha256
            self.dimension=576;self.dtype='float32';self.preprocessing='Existing Resize256/CenterCrop224/ImageNet normalization, unchanged weights/features+avgpool'
        else:
            from transformers import AutoModel,AutoImageProcessor
            meta=read(OUT/f'setup/{name}_model.json')
            if not meta or meta.get('blocked'):raise PermissionError(f'{name}: official checkpoint unavailable')
            self.revision=meta['revision'];kwargs={'revision':self.revision,'cache_dir':str(ROOT/'.models/v295/hf'),'local_files_only':True}
            self.processor=AutoImageProcessor.from_pretrained(MODELS[name],use_fast=name=='dinov3',**kwargs)
            self.model=AutoModel.from_pretrained(MODELS[name],**kwargs).eval().to('cuda',dtype=torch.float32)
            self.dimension=self.model.config.hidden_size;self.dtype='float32';self.preprocessing=self.processor.to_dict()
        self.latencies=[]

    def vector(self,row):
        t=self.torch;image=Image.open(row['crop_path']).convert('RGB');t.cuda.synchronize();started=time.perf_counter()
        if self.name=='mobilenet':
            # Native transform and extractor, but bypass historical/cache timing effects.
            tensor=self.extractor.transform(image).unsqueeze(0).to('cuda')
            with t.inference_mode():v=self.model.avgpool(self.model.features(tensor)).flatten(1)[0]
            method='native_global'
        else:
            inputs=self.processor(images=image,return_tensors='pt').to('cuda')
            with t.inference_mode():out=self.model(**inputs)
            regs=getattr(self.model.config,'num_register_tokens',0)
            patches=out.last_hidden_state[0,1+regs:]
            v=patches.mean(0);method='canonical_object_crop_patch_mean'
            if row.get('foreground_mask_path'):
                mask=Image.open(row['foreground_mask_path']).convert('L').convert('RGB')
                m=self.processor(images=mask,return_tensors='pt',do_rescale=False,do_normalize=False)['pixel_values'].to('cuda')
                ps=self.model.config.patch_size;pooled=t.nn.functional.avg_pool2d(m.float().mean(1,keepdim=True)/255,ps,ps).flatten()>=.5
                if len(pooled)==len(patches) and pooled.sum()>=2:
                    v=patches[pooled].mean(0);method='foreground_patch_mean'
        v=t.nn.functional.normalize(v.float(),dim=0).cpu().numpy();t.cuda.synchronize()
        self.latencies.append(time.perf_counter()-started);self.methods.add(method)
        if not np.isfinite(v).all():raise ValueError('Nonfinite backbone feature')
        return v

    def metadata(self):
        import statistics
        return {'model_id':MODELS[self.name],'revision':self.revision,'dimension':self.dimension,'dtype':self.dtype,
                'embedding_protocol':'native_mobile_global' if self.name=='mobilenet' else 'patch_mean_foreground_if_reliable_else_all_object_crop_patches',
                'preprocessing':self.preprocessing,'representations':sorted(self.methods),'device':'CUDA',
                'observations':len(self.latencies),'latency_median_seconds':statistics.median(self.latencies) if self.latencies else None,
                'latency_mean_seconds':sum(self.latencies)/len(self.latencies) if self.latencies else None,
                'gpu_peak_allocated_bytes':self.torch.cuda.max_memory_allocated(),
                'packages':{x:importlib.metadata.version(x) for x in ['torch','torchvision','transformers','huggingface-hub']}}

    def close(self):
        del self.model
        if hasattr(self,'extractor'):del self.extractor
        gc.collect();self.torch.cuda.empty_cache()


def embed_video(model,video_id):
    rows=read(OUT/f'crops/{video_id}/observations.json');dest=OUT/f'benchmark/embeddings/{model.name}/{video_id}.npz'
    if dest.exists():
        meta=read(dest.with_suffix('.json'))
        protocol='native_mobile_global' if model.name=='mobilenet' else 'patch_mean_foreground_if_reliable_else_all_object_crop_patches'
        if (not meta or meta['crop_manifest_sha256']!=sha(OUT/f'crops/{video_id}/observations.json') or
            meta['model']['revision']!=model.revision or meta['model'].get('embedding_protocol')!=protocol):
            raise ValueError('Cached embedding protocol/source/model changed; use a fresh namespace')
        loaded=np.load(dest);return {k:loaded[k] for k in loaded.files}
    features={}
    for r in rows:features[r['observation_id']]=model.vector(r)
    dest.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(dest,**features)
    save(dest.with_suffix('.json'),{'model':model.metadata(),'crop_manifest_sha256':sha(OUT/f'crops/{video_id}/observations.json')})
    return features
