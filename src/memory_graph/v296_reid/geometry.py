"""Current-only, independent, clean local correspondence support; not physical proof."""
import hashlib,time
import numpy as np
from PIL import Image,ImageDraw
from memory_graph.v295_reid.geometry import LightGlueVerifier,geometry_statistics,strong_geometry
from .io import OUT,OLD,read,save
from .integrity import pair_integrity

class CurrentLightGlue(LightGlueVerifier):
    def __init__(self,policy):
        super().__init__({k:policy[k] for k in ['min_inliers','min_inlier_ratio','min_coverage']})
        self.integrity_policy=policy;self.results=[];self.invalid_pairs=[]
    def compare(self,a,b):
        key=hashlib.sha256((a['crop_sha256']+b['crop_sha256']+'official_superpoint512').encode()).hexdigest()
        path=OUT/f'lightglue/pairs/{key}.json';cached=read(path) or read(OLD/f'lightglue/pairs/{key}.json')
        if cached:result={**cached,'cache_hit':True}
        else:
            t=self.torch;t.cuda.synchronize();start=time.perf_counter();f0=self.feature(a);f1=self.feature(b)
            pts0=f0['keypoints'][0].numpy();pts1=f1['keypoints'][0].numpy();matches=np.empty((0,2),int)
            if len(pts0)>=4 and len(pts1)>=4:
                with t.inference_mode():r=self.matcher({'image0':{k:v.cuda() for k,v in f0.items()},'image1':{k:v.cuda() for k,v in f1.items()}})
                matches=r['matches'][0].cpu().numpy()
            result=geometry_statistics(pts0[matches[:,0]],pts1[matches[:,1]],f0['image_size'][0].numpy(),f1['image_size'][0].numpy())
            t.cuda.synchronize();elapsed=time.perf_counter()-start;self.latencies.append(elapsed)
            result.update(keypoints0=pts0.tolist(),keypoints1=pts1.tolist(),matches=matches.tolist(),seconds=elapsed,cache_hit=False,
                candidate_crop_sha256=a['crop_sha256'],reference_crop_sha256=b['crop_sha256'],candidate_observation_id=a['observation_id'],reference_observation_id=b['observation_id'])
        match=np.asarray(result['matches'],int).reshape(-1,2);keep=np.asarray(result.get('ransac_inlier_mask',[]),bool)
        spatial=[]
        if len(keep)==len(match) and keep.any():
            for side,row in [(0,a),(1,b)]:
                pts=np.asarray(result[f'keypoints{side}'])[match[keep,side]];w,h=row['canonical_metadata']['crop_dimensions']
                normalized=pts/np.asarray([w,h]);border=((normalized<.08)|(normalized>.92)).any(1)
                cells=np.clip((normalized*3).astype(int),0,2);occupied=len(set(map(tuple,cells)))
                spatial.append({'inlier_coordinates':pts.tolist(),'occupied_3x3_cells':occupied,'border_fraction':float(border.mean())})
        quality=bool(len(spatial)==2 and all(x['border_fraction']<=self.integrity_policy['max_border_fraction'] and x['occupied_3x3_cells']>=self.integrity_policy['minimum_occupied_cells'] for x in spatial))
        result.update(correspondence_distribution=spatial,object_spatial_integrity=quality)
        result['status']='STRONG_MATCH' if strong_geometry(result,self.policy) and quality else 'UNKNOWN'
        result['pair_reference']=str(path.relative_to(OUT));save(path,result)
        if result['status']=='STRONG_MATCH':self.visualize(a,b,result,key)
        return result
    def visualize(self,a,b,result,key):
        dest=OUT/f'lightglue/audit_visualizations/{key}.png'
        if dest.exists():return
        im0=Image.open(a['raw_crop_path']).convert('RGB');im1=Image.open(b['raw_crop_path']).convert('RGB');sizes=[im0.size,im1.size]
        im0.thumbnail((400,400));im1.thumbnail((400,400));sheet=Image.new('RGB',(im0.width+im1.width,max(im0.height,im1.height)),(35,35,35));sheet.paste(im0,(0,0));sheet.paste(im1,(im0.width,0));draw=ImageDraw.Draw(sheet)
        matches=result['matches'];keep=result.get('ransac_inlier_mask',[])
        for index,(i,j) in enumerate(matches):
            if index>=len(keep) or not keep[index]:continue
            x,y=result['keypoints0'][i];u,v=result['keypoints1'][j]
            p=(x/sizes[0][0]*im0.width,y/sizes[0][1]*im0.height);q=(im0.width+u/sizes[1][0]*im1.width,v/sizes[1][1]*im1.height)
            draw.line([p,q],fill=(30,220,90),width=1)
        dest.parent.mkdir(parents=True,exist_ok=True);sheet.save(dest)
    def verify(self,current,core,negative,core_scores,negative_scores):
        groups={'core':[],'negative':[]};invalid=[];start=time.perf_counter()
        for kind,bank,scores in [('core',core,core_scores),('negative',negative,negative_scores)]:
            ranked=sorted(range(len(bank)),key=lambda j:-(scores[j] if j<len(scores) else -1))[:3 if kind=='core' else 2]
            for j in ranked:
                b=bank[j];check=pair_integrity(current,b,b,current['observation_id'])
                if not check['admissible']:
                    invalid.append(check);self.invalid_pairs.append(check);continue
                result=self.compare(current,b)
                compact={k:v for k,v in result.items() if k not in ['keypoints0','keypoints1','matches','homography','ransac_inlier_mask']}
                groups[kind].append({**compact,'reference_entry_id':b['entry_id'],'integrity':check})
        cp=any(x['status']=='STRONG_MATCH' for x in groups['core']);np_=any(x['status']=='STRONG_MATCH' for x in groups['negative'])
        result={'state':'NEGATIVE_STRONG_MATCH' if np_ else 'CORE_STRONG_MATCH' if cp else 'UNKNOWN' if groups['core'] else 'INVALID_EVIDENCE',
            'core_pairs':groups['core'],'negative_pairs':groups['negative'],'negative_positive':np_,
            'integrity_valid':bool(groups['core']),'invalid_pairs_rejected':invalid,'current_observation_id':current['observation_id'],
            'wall_seconds':time.perf_counter()-start,'role':'LOCAL_CORRESPONDENCE_SUPPORT_NOT_PHYSICAL_IDENTITY_PROOF'}
        self.results.append(result);return result
