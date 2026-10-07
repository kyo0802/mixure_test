"""Validated original crops, primary features, lazy correlated crosscheck, veto only."""
from collections import defaultdict
from pathlib import Path
import hashlib,time
import cv2
import numpy as np
from PIL import Image
from .io import ROOT,OUT,OLD,read,save,sha

PROTOCOL='patch_mean_foreground_if_reliable_else_all_object_crop_patches'

def photometric_descriptor(row):
    # Bbox alone does not certify pure foreground: abstain when SAM is unreliable.
    if not row.get('foreground_mask_path'):return {'usable':False,'reason':'no reliable foreground mask'}
    rgb=np.asarray(Image.open(row.get('raw_crop_path',row['crop_path'])).convert('RGB'))
    fg=np.asarray(Image.open(row['foreground_mask_path']).convert('L'))>0
    if fg.shape!=rgb.shape[:2]:return {'usable':False,'reason':'foreground geometry mismatch'}
    lab=cv2.cvtColor(rgb.astype(np.float32)/255.,cv2.COLOR_RGB2LAB);ab=lab[:,:,1:]
    chroma=np.linalg.norm(ab,axis=2);selected=fg&(chroma>=8.)
    if selected.sum()<32 or selected.sum()/max(1,fg.sum())<.08:return {'usable':False,'reason':'achromatic or insufficient chromatic foreground'}
    pixels=ab[selected];q=np.quantile(pixels,[.2,.5,.8],axis=0)
    return {'usable':True,'ab':q[1].tolist(),'ab_quantiles':q.tolist(),'chromatic_fraction':float(selected.sum()/fg.sum()),
        'foreground_pixels':int(fg.sum()),'producer':'masked-original-Lab-chroma-median; no positive identity'}

def photometric_veto(candidate,references,threshold):
    refs=[x for x in references if x.get('usable')]
    if not candidate.get('usable') or not refs:return {'state':'UNKNOWN','positive_identity_evidence':False,'reason':'insufficient comparable foreground chroma'}
    distances=[float(np.linalg.norm(np.asarray(candidate['ab'])-np.asarray(x['ab']))) for x in refs]
    distance=min(distances)
    return {'state':'STRONG_CONTRADICTION' if distance>threshold else 'NO_CONTRADICTION',
        'positive_identity_evidence':False,'minimum_ab_distance':distance,'all_ab_distances':distances,'threshold':threshold}

def validate_original(video_id):
    dest=OUT/f'inputs/{video_id}/observations.json'
    if dest.exists():
        rows=read(dest);source=read(OUT/f'inputs/{video_id}/source.json')
        video=ROOT/(f'{video_id}.mp4' if video_id.startswith('test') else f'val_set/{video_id}.mp4')
        if sha(video)!=source['video_sha256']:raise ValueError('Original video changed since V296 extraction')
        rawsource=ROOT/(f'outputs_v292/{video_id}' if video_id.startswith('test') else f'outputs/validation/runs/{video_id}/{video_id}')
        for rel,h in source['raw_sources'].items():
            if sha(rawsource/rel)!=h:raise ValueError('Cached raw perception source drift')
        for r in rows:
            if sha(r['crop_path'])!=r['crop_sha256'] or sha(r['raw_crop_path'])!=r['raw_crop_sha256']:raise ValueError('Clean crop drift')
            expected=np.asarray(Image.open(r['raw_crop_path']).convert('RGB')).copy()
            if r.get('foreground_mask_path'):
                fg=np.asarray(Image.open(r['foreground_mask_path']).convert('L'))>0;expected[~fg]=128
            if not np.array_equal(expected,np.asarray(Image.open(r['crop_path']).convert('RGB'))):raise ValueError('Cached foreground/canonical crop drift')
            r['source_video_sha256']=source['video_sha256']
        return rows
    rows=read(OLD/f'crops/{video_id}/observations.json');source=read(OLD/f'crops/{video_id}/source.json')
    video=ROOT/(f'{video_id}.mp4' if video_id.startswith('test') else f'val_set/{video_id}.mp4')
    rawsource=ROOT/(f'outputs_v292/{video_id}' if video_id.startswith('test') else f'outputs/validation/runs/{video_id}/{video_id}')
    if not rows or sha(video)!=source['video_sha256']:raise ValueError('Missing or stale V295 input; no silent reuse')
    for rel,h in source['raw_sources'].items():
        if sha(rawsource/rel)!=h:raise ValueError('Raw perception source drift')
    return verify_rows(video_id,rows,video,read(OLD/f'crops/{video_id}/frames.json'),source)

def verify_rows(video_id,rows,video,frames,source):
    by=defaultdict(list)
    for r in rows:by[r['frame']].append(r)
    cap=cv2.VideoCapture(str(video));output=[]
    try:
        for frame,group in by.items():
            cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,img=cap.read()
            if not ok:raise OSError('Original frame decoding failed')
            rawsha=hashlib.sha256(img.tobytes()).hexdigest()
            for r in group:
                if sha(r['crop_path'])!=r['crop_sha256']:raise ValueError('Canonical crop hash mismatch')
                a,b,c,d=r['canonical_metadata']['crop_bounds'];rgb=cv2.cvtColor(img[b:d,a:c],cv2.COLOR_BGR2RGB)
                expected=rgb.copy()
                if r.get('foreground_mask_path'):
                    fg=np.asarray(Image.open(r['foreground_mask_path']).convert('L'))>0;expected[~fg]=128
                stored=np.asarray(Image.open(r['crop_path']).convert('RGB'))
                if not np.array_equal(expected,stored):raise ValueError('Annotated/stale/non-original canonical image rejected')
                p=OUT/f'inputs/{video_id}/raw_crops/{r["observation_id"].replace(":","_")}.png';p.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(rgb).save(p)
                rr={**r,'raw_crop_path':str(p),'raw_crop_sha256':sha(p),'raw_image_path':str(video)+f'#frame={frame}',
                    'raw_image_sha256':rawsha,'source_video_sha256':source['video_sha256'],'annotation_overlays':False,'raw_source_verified':True,
                    'evidence_producer':'decoded-original-verified-canonical','pixel_descriptor':cv2.resize(rgb,(32,32),interpolation=cv2.INTER_AREA).tolist()}
                rr['photometric']=photometric_descriptor(rr);output.append(rr)
    finally:cap.release()
    save(OUT/f'inputs/{video_id}/observations.json',output);save(OUT/f'inputs/{video_id}/frames.json',frames);save(OUT/f'inputs/{video_id}/source.json',source)
    return output

class FeatureProvider:
    def __init__(self,video_id,rows):
        self.video_id=video_id;self.rows={r['observation_id']:r for r in rows};self.caches={};self.models={};self.requests=defaultdict(set);self.seconds=defaultdict(float)
        for name in ['dinov3','dinov2']:
            path=OLD/f'benchmark/embeddings/{name}/{video_id}.npz'
            if path.exists():
                meta=read(path.with_suffix('.json'));official=read(OLD/f'setup/{name}_model.json')
                if meta['crop_manifest_sha256']!=sha(OLD/f'crops/{video_id}/observations.json') or meta['model']['revision']!=official['revision'] or meta['model'].get('embedding_protocol')!=PROTOCOL:raise ValueError('Invalid official feature cache')
                with np.load(path) as archive:self.caches[name]={k:archive[k] for k in archive.files}
            else:self.caches[name]={}
    def vector(self,name,row):
        oid=row['observation_id'];self.requests[name].add(oid)
        if oid not in self.caches[name]:
            # Secondary model is never loaded unless confirmation risk requests it.
            if name not in self.models:
                from memory_graph.v295_reid.backbones import Backbone
                self.models[name]=Backbone(name)
            start=time.perf_counter();self.caches[name][oid]=self.models[name].vector(row);self.seconds[name]+=time.perf_counter()-start
        return tuple(float(x) for x in self.caches[name][oid])
    def close(self):
        meta={name:model.metadata() for name,model in self.models.items()}
        for model in self.models.values():model.close()
        for name in self.models:
            path=OUT/f'appearance/embeddings/{name}/{self.video_id}.npz';path.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(path,**self.caches[name])
        result={'requested_observations':{n:len(ids) for n,ids in self.requests.items()},'inference_seconds':dict(self.seconds),'fresh_models':meta,
            'v2_role':'Correlated robustness crosscheck; never an independent identity witness'}
        save(OUT/f'appearance/resources/{self.video_id}.json',result);self.models.clear();return result
