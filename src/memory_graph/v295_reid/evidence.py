"""Causal multi-frame evidence matrices and transparent hard gates, no authority."""
from dataclasses import dataclass,asdict
import numpy as np
from memory_graph.identity.contracts import cosine,iou


@dataclass(frozen=True)
class RecoveryPolicy:
    backbone: str='dinov2'
    core_support: float=.7
    lower_support: float=.68
    admission_support: float=.6
    negative_margin: float=.08
    competitor_margin: float=.08
    minimum_frames: int=3
    minimum_duration: float=.4
    independent_interval: float=.2
    minimum_quality: float=.5
    near_duplicate_cosine: float=.998
    maximum_observation_gap: float=.6
    maximum_core_views: int=8
    core_diversity_cosine: float=.985
    minimum_bank_quality: float=.6
    stabilization_frames: int=3
    stabilization_span: float=.4
    geometric_min_inliers: int=8
    geometric_min_ratio: float=.5
    geometric_min_coverage: float=.1
    automatic_confirmation_enabled: bool=False
    calibration_id: str='UNFROZEN'

    def geometry_policy(self):
        return {'min_inliers':self.geometric_min_inliers,'min_inlier_ratio':self.geometric_min_ratio,'min_coverage':self.geometric_min_coverage}


class TrackletIdentityEvidenceAccumulator:
    def __init__(self,policy,metadata=None):
        self.policy=policy;self.metadata=metadata or {};self.results=[]

    def independent(self,observations):
        p=self.policy;rows=[]
        # A local ID reused after a detection gap does not carry old support forward.
        causal=[]
        for o in sorted(observations,key=lambda o:o.time):
            if causal and (o.time-causal[-1].time>p.maximum_observation_gap+1e-5 or o.scene_break):causal=[]
            causal.append(o)
        for o in causal:
            if not o.phone or o.source=='sam' or o.drift or not o.vector or o.confidence<p.minimum_quality:continue
            if rows and o.time-rows[-1].time<p.independent_interval-1e-5:continue
            m=self.metadata.get(o.observation_id,{})
            duplicate=False
            for prev in rows:
                pm=self.metadata.get(prev.observation_id,{})
                if m.get('view_hash') and m.get('view_hash')==pm.get('view_hash'):duplicate=True;break
                if m.get('pixel_descriptor') is not None and pm.get('pixel_descriptor') is not None:
                    distance=float(np.abs(np.asarray(m['pixel_descriptor'],dtype=float)-np.asarray(pm['pixel_descriptor'],dtype=float)).mean())
                    if distance<4. and cosine(o.vector,prev.vector)>=p.near_duplicate_cosine:duplicate=True;break
                # Near-identical view hashes can be audited with explicit pixel-distance metadata.
                if cosine(o.vector,prev.vector)>=p.near_duplicate_cosine and m.get('near_duplicate_with')==prev.observation_id:
                    duplicate=True;break
            if not duplicate:rows.append(o)
        return rows[-12:]

    def evaluate(self,candidate_id,observations,core,negative,current,epoch_broken,verifier=None):
        p=self.policy;rows=self.independent(observations)
        core=[b for b in core if b.get('active') and b.get('authorization_id') and b.get('parent_lineage')]
        negative=[b for b in negative if b.get('active')]
        cm=[[cosine(o.vector,b['embedding']) for b in core] for o in rows]
        nm=[[cosine(o.vector,b['embedding']) for b in negative] for o in rows]
        cm=[[s if s is not None else -1. for s in row] for row in cm];nm=[[s if s is not None else -1. for s in row] for row in nm]
        support=[float(np.mean(sorted(s,reverse=True)[:2])) if s else -1. for s in cm]
        neg=[max(s,default=-1.) for s in nm]
        duration=rows[-1].time-rows[0].time if rows else 0.
        med=float(np.median(support)) if support else -1.;lower=float(np.quantile(support,.25)) if support else -1.
        negative_margin=min((s-n for s,n in zip(support,neg)),default=-2.)
        distinct=sum(any(s[j]>=p.core_support for s in cm) for j in range(len(core)))
        last=observations[-1];competing=[x for x in current if x.phone and x.candidate_id!=candidate_id and iou(x.bbox,last.bbox)<.1]
        competitor_scores=[max((cosine(x.vector,b['embedding']) or -1. for b in core),default=-1.) for x in competing]
        competitor_best=max(competitor_scores,default=-1.)
        coexist=any(x.get('authorized_target',False) for x in [self.metadata.get(y.observation_id,{}) for y in competing])
        gates={'semantic_compatible':last.phone and last.source!='sam',
               'current_observation_supported':bool(rows and rows[-1].observation_id==last.observation_id and not last.drift and not last.scene_break),
               'quality_observations':len(rows)>=p.minimum_frames,
               'temporal_persistence':duration>=p.minimum_duration-1e-5,
               'multi_frame_core_support':med>=p.core_support and lower>=p.lower_support and sum(s>=p.lower_support for s in support)>=p.minimum_frames,
               'multiple_trusted_core_views':len(core)>=2 and distinct>=2,
               'no_stronger_negative':not negative or negative_margin>=p.negative_margin,
               'no_strong_competitor':not competing or med-competitor_best>=p.competitor_margin,
               'no_coexistence_contradiction':not coexist,'epoch_requires_reauthorization':epoch_broken,
               'independent_core_verification':False,'no_negative_geometric_verification':True,
               'development_calibrated':p.automatic_confirmation_enabled and p.calibration_id!='UNFROZEN'}
        geometric={'status':'NOT_REQUESTED','core_positive':False,'negative_positive':False}
        serious=len(rows)>=p.minimum_frames and med>=p.admission_support and duration>=p.minimum_duration-1e-5
        if serious and verifier:
            geometric=verifier(rows,core,negative,cm,nm)
            gates['independent_core_verification']=bool(geometric.get('core_positive'))
            gates['no_negative_geometric_verification']=not geometric.get('negative_positive',False)
        if not gates['semantic_compatible'] or not gates['no_coexistence_contradiction'] or not gates['no_negative_geometric_verification'] or not gates['no_stronger_negative']:
            stage='REJECTED'
        elif all(gates.values()):stage='CONFIRMED_MATCH'
        elif len(rows)<2:stage='NEW_CANDIDATE'
        elif not gates['no_strong_competitor']:stage='AMBIGUOUS'
        elif serious:stage='PROVISIONAL'
        else:stage='EVIDENCE_ACCUMULATING'
        result={'candidate_id':candidate_id,'observation_ids':[o.observation_id for o in rows],
            'timestamps':[o.time for o in rows],'duration':duration,'quality':[o.confidence for o in rows],
            'backbone':p.backbone,'core_entry_ids':[b['entry_id'] for b in core],'negative_entry_ids':[b['entry_id'] for b in negative],
            'core_similarity_matrix':cm,'negative_similarity_matrix':nm,'core_median':med,'core_lower_quantile':lower,
            'supporting_observations':sum(s>=p.lower_support for s in support),'distinct_core_prototypes_supported':distinct,
            'negative_support_consistency':neg,'core_vs_negative_min_margin':negative_margin,
            'competitor_state':{'ids':[x.candidate_id for x in competing],'best_core_similarity':competitor_best},
            'coexistence_contradiction':coexist,'LightGlue':geometric,'gates':gates,'stage':stage,
            'frame':last.frame,'time':last.time,'calibration_id':p.calibration_id}
        self.results.append(result);return result
