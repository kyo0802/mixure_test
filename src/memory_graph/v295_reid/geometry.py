"""Official SuperPoint/LightGlue + object-region RANSAC: evidence only."""
import gc
import os
import sys
import time
import cv2
import numpy as np
from PIL import Image
from .io import ROOT,OUT,save,read,sha


def geometry_statistics(points0,points1,size0,size1):
    count=len(points0)
    out={'raw_matches':count,'geometric_inliers':0,'inlier_ratio':0.,'coverage0':0.,'coverage1':0.,'transform_valid':False,'homography':None}
    if count<4:return out
    a=np.asarray(points0,np.float32)/np.asarray(size0,np.float32)*256
    b=np.asarray(points1,np.float32)/np.asarray(size1,np.float32)*256
    cv2.setRNGSeed(295)
    h,mask=cv2.findHomography(a,b,cv2.RANSAC,3.,maxIters=3000,confidence=.999)
    if h is None or mask is None or not np.isfinite(h).all():return out
    keep=mask.ravel().astype(bool);n=int(keep.sum())
    cov=lambda p:float(cv2.contourArea(cv2.convexHull(p)))/(256*256) if len(p)>=3 else 0.
    corners=np.asarray([[[0,0],[256,0],[256,256],[0,256]]],np.float32)
    projected=cv2.perspectiveTransform(corners,h)[0]
    area=abs(cv2.contourArea(projected))/(256*256)
    valid=bool(cv2.isContourConvex(projected) and .03<area<30 and np.isfinite(projected).all())
    out.update(geometric_inliers=n,inlier_ratio=n/count,coverage0=cov(a[keep]),coverage1=cov(b[keep]),
               transform_valid=valid,homography=h.tolist(),ransac_inlier_mask=keep.tolist())
    return out


def strong_geometry(stats,policy):
    return bool(stats.get('transform_valid') and stats['geometric_inliers']>=policy['min_inliers'] and
                stats['inlier_ratio']>=policy['min_inlier_ratio'] and
                min(stats['coverage0'],stats['coverage1'])>=policy['min_coverage'])


class LightGlueVerifier:
    def __init__(self,policy=None):
        import torch
        for p in [ROOT/'.runtime/v295_vendor',ROOT/'tools/LightGlue']:
            if str(p) not in sys.path:sys.path.insert(0,str(p))
        os.environ['TORCH_HOME']=str(ROOT/'.models/v295/torch')
        from lightglue import SuperPoint,LightGlue
        self.torch=torch;self.extractor=SuperPoint(max_num_keypoints=1024).eval().cuda()
        self.matcher=LightGlue(features='superpoint').eval().cuda()
        self.policy=policy or {'min_inliers':8,'min_inlier_ratio':.5,'min_coverage':.1}
        self.features={};self.latencies=[]

    def feature(self,row):
        key=row['crop_sha256']
        if key in self.features:return self.features[key]
        t=self.torch;im=np.asarray(Image.open(row['crop_path']).convert('RGB'))
        tensor=t.from_numpy(im.copy()).permute(2,0,1).float().div(255).cuda()
        with t.inference_mode():f=self.extractor.extract(tensor,resize=512)
        points=f['keypoints'][0].cpu().numpy();h,w=im.shape[:2]
        xy=np.rint(points).astype(int);xy[:,0]=np.clip(xy[:,0],0,w-1);xy[:,1]=np.clip(xy[:,1],0,h-1)
        if row.get('foreground_mask_path'):
            mask=np.asarray(Image.open(row['foreground_mask_path']))>0;keep=mask[xy[:,1],xy[:,0]]
        else:
            # Exclude canonical crop margin even when a reliable segmentation is unavailable.
            a,b,c,d=row['canonical_metadata']['crop_bounds'];box=row['bbox']
            keep=(points[:,0]>=box[0]-a)&(points[:,0]<box[2]-a)&(points[:,1]>=box[1]-b)&(points[:,1]<box[3]-b)
        k=t.as_tensor(keep,device='cuda')
        for field in ['keypoints','keypoint_scores','descriptors']:
            if field in f:f[field]=f[field][:,k]
        f={k:v.detach().cpu() for k,v in f.items()};self.features[key]=f
        return f

    def compare(self,a,b):
        pairkey=__import__('hashlib').sha256((a['crop_sha256']+b['crop_sha256']+'official_superpoint512').encode()).hexdigest()
        path=OUT/f'lightglue/pairs/{pairkey}.json';cached=read(path)
        if cached:
            return {**cached,'status':'STRONG_MATCH' if strong_geometry(cached,self.policy) else 'UNKNOWN','cache_hit':True}
        t=self.torch;t.cuda.synchronize();started=time.perf_counter();f0=self.feature(a);f1=self.feature(b)
        points0=f0['keypoints'][0].numpy();points1=f1['keypoints'][0].numpy();matches=np.empty((0,2),dtype=int)
        if len(points0)>=4 and len(points1)>=4:
            with t.inference_mode():result=self.matcher({'image0':{k:v.cuda() for k,v in f0.items()},'image1':{k:v.cuda() for k,v in f1.items()}})
            matches=result['matches'][0].cpu().numpy()
        s=geometry_statistics(points0[matches[:,0]],points1[matches[:,1]],f0['image_size'][0].numpy(),f1['image_size'][0].numpy())
        t.cuda.synchronize();elapsed=time.perf_counter()-started;self.latencies.append(elapsed)
        s.update(candidate_observation_id=a['observation_id'],reference_observation_id=b['observation_id'],
                 candidate_crop_sha256=a['crop_sha256'],reference_crop_sha256=b['crop_sha256'],
                 keypoints0=points0.tolist(),keypoints1=points1.tolist(),matches=matches.tolist(),
                 keypoint_count0=len(points0),keypoint_count1=len(points1),seconds=elapsed,
                 foreground_filter='Reliable mask if present, otherwise bbox excludes margin',
                 status='STRONG_MATCH' if strong_geometry(s,self.policy) else 'UNKNOWN',cache_hit=False)
        save(path,s);return s

    def verify(self,candidate_rows,core_rows,negative_rows):
        pairs={'core':[],'negative':[]}
        for kind,refs in [('core',core_rows),('negative',negative_rows)]:
            for candidate in candidate_rows:
                for reference in refs:pairs[kind].append(self.compare(candidate,reference))
        return {'core_positive':any(x['status']=='STRONG_MATCH' for x in pairs['core']),
                'negative_positive':any(x['status']=='STRONG_MATCH' for x in pairs['negative']),
                'core_pairs':pairs['core'],'negative_pairs':pairs['negative'],
                'status':'NEGATIVE_VERIFIED' if any(x['status']=='STRONG_MATCH' for x in pairs['negative']) else
                         'CORE_VERIFIED' if any(x['status']=='STRONG_MATCH' for x in pairs['core']) else 'UNKNOWN'}

    def close(self):
        del self.matcher;del self.extractor;self.features.clear();gc.collect();self.torch.cuda.empty_cache()
