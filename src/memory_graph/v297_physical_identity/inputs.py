"""Read-only reuse of verified original evidence; isolate every new model artifact."""
from contextlib import contextmanager
import numpy as np
from PIL import Image
from .io import ROOT,OUT,PREV,OLD,read,save,sha

@contextmanager
def visual_namespace():
    from memory_graph.v296_reid import io,appearance,geometry
    old=[(m,m.OUT) for m in [io,appearance,geometry]]
    try:
        for m,_ in old:m.OUT=OUT
        yield
    finally:
        for m,p in old:m.OUT=p

def prepare(video_id):
    source_root=PREV/f'inputs/{video_id}';source=read(source_root/'source.json')
    if not source:raise FileNotFoundError(f'Missing verified original inputs: {video_id}')
    video=ROOT/(f'{video_id}.mp4' if video_id.startswith('test') else f'val_set/{video_id}.mp4')
    if sha(video)!=source['video_sha256']:raise ValueError('Video changed since verified crop extraction')
    raw=ROOT/(f'outputs_v292/{video_id}' if video_id.startswith('test') else f'outputs/validation/runs/{video_id}/{video_id}')
    for p,h in source['raw_sources'].items():
        if sha(raw/p)!=h:raise ValueError('Raw perception source changed')
    rows=read(source_root/'observations.json');frames=read(source_root/'frames.json')
    for r in rows:
        if sha(r['raw_crop_path'])!=r['raw_crop_sha256'] or sha(r['crop_path'])!=r['crop_sha256']:raise ValueError('Original clean crop changed')
        rgb=np.asarray(Image.open(r['raw_crop_path']).convert('RGB')).copy()
        if r.get('foreground_mask_path'):
            fg=np.asarray(Image.open(r['foreground_mask_path']).convert('L'))>0;rgb[~fg]=128;r['foreground_mask_sha256']=sha(r['foreground_mask_path'])
        if not np.array_equal(rgb,np.asarray(Image.open(r['crop_path']).convert('RGB'))):raise ValueError('Foreground/canonical crop drift')
        r['source_video_sha256']=source['video_sha256']
    save(OUT/f'inputs/{video_id}/observations.json',rows);save(OUT/f'inputs/{video_id}/frames.json',frames)
    save(OUT/f'inputs/{video_id}/source.json',{**source,'V296_verified_inputs_sha256':sha(source_root/'observations.json'),'mode':'READ_ONLY_VALIDATED_ORIGINAL_EVIDENCE_REPLAY'})
    return rows,frames

def feature_provider(video_id,rows):
    from memory_graph.v296_reid.appearance import FeatureProvider
    provider=FeatureProvider(video_id,rows)
    for name in ['dinov2']:
        p=PREV/f'appearance/embeddings/{name}/{video_id}.npz';resources=read(PREV/f'appearance/resources/{video_id}.json',{})
        model=resources.get('fresh_models',{}).get(name)
        if p.exists() and model and model['revision']==read(OLD/f'setup/{name}_model.json')['revision'] and model['embedding_protocol']=='patch_mean_foreground_if_reliable_else_all_object_crop_patches':
            with np.load(p) as archive:provider.caches[name].update({k:archive[k] for k in archive.files})
    return provider

def lightglue(policy):
    from memory_graph.v296_reid.geometry import CurrentLightGlue
    class ReadOnlyCachedLightGlue(CurrentLightGlue):
        def compare(self,a,b):
            import hashlib
            key=hashlib.sha256((a['crop_sha256']+b['crop_sha256']+'official_superpoint512').encode()).hexdigest()
            p=OUT/f'lightglue/pairs/{key}.json'
            if not p.exists():
                previous=read(PREV/f'lightglue/pairs/{key}.json')
                if previous:save(p,previous)
            return super().compare(a,b)
    return ReadOnlyCachedLightGlue(policy)
