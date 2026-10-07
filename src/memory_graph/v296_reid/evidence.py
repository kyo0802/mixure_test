"""Explicit epoch-level dual-route gates, with no target mutation API."""
from dataclasses import dataclass
import numpy as np
from memory_graph.identity.contracts import cosine,iou
from .integrity import candidate_integrity,pair_integrity

@dataclass(frozen=True)
class ConfirmationPolicy:
    admission:float=.60
    g_support:float=.68
    g_lower:float=.66
    g_current:float=.68
    g_frames:int=3
    g_duration:float=.4
    a_support:float=.80
    a_lower:float=.76
    a_current:float=.80
    a_frames:int=5
    a_duration:float=.8
    v2_support:float=.62
    negative_margin:float=.08
    competitor_margin:float=.10
    independent_interval:float=.2
    confidence:float=.5
    duplicate_cosine:float=.998
    maximum_core:int=8
    core_diversity:float=.985
    stabilization_frames:int=3
    stabilization_seconds:float=.4
    photometric_threshold:float=40.
    calibrated:bool=False

def matrix(rows,bank,key='v3'):
    return [[cosine(tuple(r[key]),tuple(b['embedding'])) or -1. for b in bank] for r in rows]
def summary(m):
    support=[float(np.mean(sorted(s,reverse=True)[:2])) if s else -1. for s in m]
    return {'per_frame':support,'median':float(np.median(support)) if support else -1.,'lower':float(np.quantile(support,.25)) if support else -1.,'current':support[-1] if support else -1.}

class TemporalAccumulator:
    def __init__(self,policy):self.policy=policy
    def independent(self,rows):
        p=self.policy;out=[]
        for r in rows:
            if r.get('epoch_unresolved') or r.get('drift') or r['source']=='sam' or r['confidence']<p.confidence:continue
            if out and r['time']-out[-1]['time']<p.independent_interval-1e-5:continue
            duplicate=False
            for prev in out:
                if r['crop_sha256']==prev['crop_sha256']:duplicate=True;break
                if r.get('pixel_descriptor') is not None and prev.get('pixel_descriptor') is not None:
                    delta=float(np.abs(np.asarray(r['pixel_descriptor'],float)-np.asarray(prev['pixel_descriptor'],float)).mean())
                    if delta<4. and cosine(tuple(r['v3']),tuple(prev['v3']))>=p.duplicate_cosine:duplicate=True;break
            if not duplicate:out.append(r)
        return out[-16:]
    def evaluate(self,history,core,negative,current,epoch_broken,v2,geometry,photometric):
        p=self.policy;last=history[-1];rows=self.independent(history);integ=candidate_integrity(rows,last)
        valid=[];excluded=[]
        for b in core:
            check=pair_integrity(last,b,b,last['observation_id'])
            (valid if check['admissible'] else excluded).append(b if check['admissible'] else {'entry_id':b['entry_id'],'integrity':check})
        neg=[b for b in negative if b.get('active')];cm=matrix(rows,valid);nm=matrix(rows,neg);s=summary(cm)
        current_vector=last['v3'];current_support=summary(matrix([last],valid))['current']
        negbest=[max(x,default=-1.) for x in nm];margin=min((a-b for a,b in zip(s['per_frame'],negbest)),default=-2.)
        competing=[r for r in current if r['candidate_epoch_id']!=last['candidate_epoch_id'] and iou(r['bbox'],last['bbox'])<.1]
        comp=[max(matrix([r],valid)[0],default=-1.) for r in competing]
        coexist=any(r.get('authorized_target',False) for r in competing)
        dur=rows[-1]['time']-rows[0]['time'] if rows else 0.
        distinct=sum(any(x[j]>=p.g_support for x in cm) for j in range(len(valid)))
        photo=photometric(last,valid)
        g={'state':'NOT_REQUESTED','negative_positive':False,'integrity_valid':True,'core_pairs':[]}
        v2s={'state':'NOT_REQUESTED','correlated_not_independent':True};v2matrix=[]
        serious=bool(integ['admissible'] and len(rows)>=p.g_frames and dur>=p.g_duration-1e-5 and s['median']>=p.admission and valid)
        if serious:
            g=geometry(last,valid,neg,cm[-1],nm[-1] if nm else [])
            v2rows=[{**r,'v2':v2(r)} for r in rows];v2cores=[{**b,'embedding':list(v2(b))} for b in valid]
            v2matrix=matrix(v2rows,v2cores,'v2');ss=summary(v2matrix)
            agree=ss['median']>=p.v2_support and ss['lower']>=p.v2_support and ss['current']>=p.v2_support
            v2s={**ss,'state':'STRONG_AGREEMENT' if agree else 'DISAGREEMENT' if ss['current']<p.v2_support-.1 else 'PARTIAL_AGREEMENT','correlated_not_independent':True}
        common={'valid_candidate_epoch':integ['admissible'],'semantic':last['label']=='cell phone' and last['source']!='sam',
            'quality':last['confidence']>=p.confidence and not last.get('drift'),'epoch_requires_reauthorization':epoch_broken,
            'multiple_independent_core_views':len(valid)>=2 and distinct>=2,'no_negative_contradiction':not neg or margin>=p.negative_margin,
            'no_negative_geometry':not g.get('negative_positive'),'no_low_level_contradiction':photo['state']!='STRONG_CONTRADICTION',
            'no_coexistence':not coexist,'no_serious_competitor':not comp or current_support-max(comp)>=p.competitor_margin,
            'crosscheck_agreement':v2s['state']=='STRONG_AGREEMENT','geometry_evidence_integrity':g.get('integrity_valid',True),
            'development_calibrated':p.calibrated}
        routeg={**common,'multiple_frames':len(rows)>=p.g_frames,'duration':dur>=p.g_duration-1e-5,
            'consistent_appearance':s['median']>=p.g_support and s['lower']>=p.g_lower,'current_appearance':current_support>=p.g_current,
            'current_independent_geometry':g['state']=='CORE_STRONG_MATCH'}
        routea={**common,'more_independent_frames':len(rows)>=p.a_frames,'longer_duration':dur>=p.a_duration-1e-5,
            'stronger_consistency':s['median']>=p.a_support and s['lower']>=p.a_lower,'stronger_current':current_support>=p.a_current,
            'geometry_unknown_only':g['state']=='UNKNOWN'}
        route='G' if all(routeg.values()) else 'A' if all(routea.values()) else None
        contradiction=not common['no_negative_contradiction'] or not common['no_negative_geometry'] or not common['no_low_level_contradiction'] or coexist
        stage='CONFIRMED_MATCH' if route else 'REJECTED' if contradiction or not common['semantic'] else 'AMBIGUOUS' if not common['no_serious_competitor'] or v2s['state']=='DISAGREEMENT' else 'PROVISIONAL' if serious else 'EVIDENCE_ACCUMULATING' if len(rows)>=2 else 'NEW_CANDIDATE'
        return {'candidate_epoch_id':last['candidate_epoch_id'],'candidate_id':last['candidate_epoch_id'],
            'local_track_ids':last.get('local_track_ids',[last.get('local_track_id')]),'current_observation':last['observation_id'],
            'observation_ids':[r['observation_id'] for r in rows],'frame':last['frame'],'time':last['time'],'duration':dur,
            'DINOv3':{**s,'current':current_support,'matrix':cm,'distinct_core_views':distinct},'DINOv2':v2s,'DINOv2_matrix':v2matrix,
            'negative_matrix':nm,'negative_margin':margin,'negative_state':'NO_INFORMATION' if not neg else 'EXPLICIT_NEGATIVE_BANK',
            'Core_sources':[{k:v for k,v in b.items() if k not in ['embedding','v3','v2','pixel_descriptor']} for b in valid],
            'Negative_sources':[{k:v for k,v in b.items() if k not in ['embedding','v3','v2','pixel_descriptor']} for b in neg],
            'excluded_core':excluded,'integrity':integ,'photometric':photo,'LightGlue':g,'competitor_ids':[r['candidate_epoch_id'] for r in competing],
            'route_g_gates':routeg,'route_a_gates':routea,'route':route,'stage':stage}
