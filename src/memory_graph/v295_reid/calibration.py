"""Freeze numeric policies before any opened-val regression; development evidence only."""
from dataclasses import asdict
from collections import defaultdict
import math
import statistics
import time
import numpy as np
from .io import OUT,read,save,sha
from .benchmark import select
from .geometry import LightGlueVerifier,strong_geometry
from .evidence import RecoveryPolicy


def calibrate():
    dest=OUT/'calibration/confirmation_policy.json'
    if dest.exists():return read(dest)
    selected=select();name=selected['backbone'];metrics=read(OUT/f'benchmark/{name}_metrics.json')
    positives=read(OUT/'benchmark/positive_observations.json');negatives=read(OUT/'benchmark/negative_observations.json')
    byvid=defaultdict(dict)
    for r in positives+negatives:byvid[r['video_id']][r['observation_id']]=r
    records=read(OUT/f'benchmark/{name}_single_frame_evidence.json')
    verifier=LightGlueVerifier();pairs=[]
    try:
        for vid,refs in metrics['reference_protocol'].items():
            items=[r for r in records if r['video_id']==vid];features=np.load(OUT/f'benchmark/embeddings/{name}/{vid}.npz')
            chosen=[]
            for label in ['TARGET','DISTRACTOR']:
                group=[r for r in items if r['label']==label]
                if not group:continue
                # Temporal bins plus diverse local candidate groups, not highest-scoring easy samples.
                indices=sorted(set([0,len(group)//2,len(group)-1]));chosen.extend(group[i] for i in indices)
                seen={r['candidate_id'] for r in chosen}
                for r in group:
                    if len([c for c in chosen if c['label']==label])>=8:break
                    if r['candidate_id'] not in seen:chosen.append(r);seen.add(r['candidate_id'])
            for query in chosen:
                row=byvid[vid][query['observation_id']]
                ranked=sorted(refs['core_ids'],key=lambda oid:-float(features[row['observation_id']]@features[oid]))[:2]
                for oid in ranked:
                    result=verifier.compare(row,byvid[vid][oid]);pairs.append({'video_id':vid,'label':query['label'],**result})
        operating=[]
        for ni in [8,12,16]:
            for ratio in [.5,.6,.7]:
                for coverage in [.1,.15,.2]:
                    policy={'min_inliers':ni,'min_inlier_ratio':ratio,'min_coverage':coverage}
                    pos=[r for r in pairs if r['label']=='TARGET'];neg=[r for r in pairs if r['label']=='DISTRACTOR']
                    operating.append({**policy,'positive_pairs':sum(strong_geometry(r,policy) for r in pos),
                                      'false_positive_pairs':sum(strong_geometry(r,policy) for r in neg),
                                      'positive_total':len(pos),'negative_total':len(neg)})
        safe=[r for r in operating if r['false_positive_pairs']==0]
        best=max(safe,key=lambda r:(r['positive_pairs'],r['min_inliers'],r['min_inlier_ratio'],r['min_coverage'])) if safe else None
        geometry=best or {'min_inliers':16,'min_inlier_ratio':.7,'min_coverage':.2,'positive_pairs':0}
        tau=math.ceil((metrics['negative']['max']+.04)*50)/50
        # Headroom is explicitly above the development distractor maximum, not tuned on val.
        policy=RecoveryPolicy(backbone=name,core_support=tau,lower_support=tau-.02,admission_support=tau-.08,
            geometric_min_inliers=geometry['min_inliers'],geometric_min_ratio=geometry['min_inlier_ratio'],
            geometric_min_coverage=geometry['min_coverage'],
            automatic_confirmation_enabled=bool(best and best['positive_pairs']>=3),calibration_id='V295_DEVELOPMENT_ONLY_FROZEN')
        result={'policy':asdict(policy),'frozen_unix':time.time(),'selected_backbone_sha256':sha(OUT/'benchmark/selected_backbone.json'),
                'dataset_sha256':sha(OUT/'benchmark/identity_dataset_manifest.json'),
                'appearance_justification':f'core_support = ceil20milli(development distractor maximum {metrics["negative"]["max"]:.6f} + .04); lower quantile support -.02; admission -.08.',
                'geometry_justification':'Measured development same-target versus distractor-to-Core pairs; maximize positive verifications subject to zero observed false geometric acceptance, then prefer stricter gates.',
                'geometry_operating_points':operating,'selected_geometry':geometry,
                'minimum_frame_justification':'At least3 nonduplicate quality frames across0.4s at unchanged5fps; no single maximum identity decision.',
                'margin_justification':'.08 Core-vs-Negative and physical competitor margin provides additional abstention buffer; geometric agreement remains mandatory.',
                'scope':'Development labels only; small instance diversity; thresholds are not a held-out guarantee.'}
        save(OUT/'lightglue/development_pair_evidence.json',pairs)
        save(OUT/'lightglue/verifier_metrics.json',{'pairs':len(pairs),'selected_geometry':geometry,
             'positive_pairs':sum(r['label']=='TARGET' for r in pairs),'negative_pairs':sum(r['label']=='DISTRACTOR' for r in pairs),
             'uncached_latency_median_seconds':statistics.median(verifier.latencies) if verifier.latencies else None,
             'operating_points':operating,'source':'Official SuperPoint + LightGlue; object-region keypoints; normalized256 RANSAC threshold3pixels; no raw-match-count decision'})
        for label,folder in [('TARGET','positive_examples'),('DISTRACTOR','negative_examples')]:
            examples=sorted([r for r in pairs if r['label']==label],key=lambda r:-r['geometric_inliers'])[:3]
            for i,r in enumerate(examples):save(OUT/f'lightglue/{folder}/example_{i+1}.json',r)
        save(dest,result)
        text='# Development-only confirmation calibration\n\n'+result['appearance_justification']+'\n\n'+result['geometry_justification']+'\n\n'+__import__('json').dumps(asdict(policy),indent=2)+'\n\nNo val_1–11 pixels or GT used for calibration. LightGlue failure is UNKNOWN; only strong negative verification rejects. All long-gap confirmations require positive Core verification. Small-instance calibration does not prove zero future false merges.\n'
        (OUT/'calibration/threshold_report.md').write_text(text,encoding='utf8')
        print('SELECTED',name,'POLICY',asdict(policy),'GEOMETRY',geometry,flush=True)
    finally:verifier.close()
    return result
