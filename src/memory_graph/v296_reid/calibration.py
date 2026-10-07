"""Development-only global calibration. Never reads val ground truth or results."""
from dataclasses import asdict
from collections import defaultdict
import math,time
import numpy as np
from .io import ROOT,OUT,OLD,read,save,sha
from .epochs import EpochPolicy,transition
from .evidence import ConfirmationPolicy
from .appearance import validate_original,FeatureProvider,photometric_veto

def calibrate():
    if (OUT/'calibration/parameters.json').exists():raise FileExistsError('Calibration exists; do not overwrite')
    positive=read(OLD/'benchmark/positive_observations.json');negative=read(OLD/'benchmark/negative_observations.json')
    labels={(x['video_id'],x['observation_id']):'TARGET' for x in positive};labels.update({(x['video_id'],x['observation_id']):'DISTRACTOR' for x in negative})
    transitions=[];photodists=[];negdist=[];frames=[];byvideo={}
    for i in range(1,10):
        vid=f'test{i}';rows=validate_original(vid);provider=FeatureProvider(vid,rows)
        try:
            for r in rows:r['v3']=list(provider.vector('dinov3',r))
        finally:provider.close()
        by={r['observation_id']:r for r in rows};byvideo[vid]=by
        initial=read(ROOT/f'outputs/identity_rebuild/development/runs_final/{vid}/identity.json')
        refs=[by[b['observation_id']] for b in initial['banks']['core'] if b['active']]
        grouped=defaultdict(list)
        for r in rows:
            if labels.get((vid,r['observation_id']))=='TARGET':grouped[r['candidate_id']].append(r)
        for group in grouped.values():
            group.sort(key=lambda x:x['time'])
            for a,b in zip(group,group[1:]):
                tr=transition(a,b)
                if 0<tr['gap']<=.4+1e-5:transitions.append(tr)
        # Paired photometric references use all individually trusted, causally earlier target foregrounds.
        trusted=[r for r in rows if labels.get((vid,r['observation_id']))=='TARGET' and r['photometric'].get('usable')]
        for r in rows:
            label=labels.get((vid,r['observation_id']))
            references=[x['photometric'] for x in trusted if x['time']<r['time']-.4 and x['observation_id']!=r['observation_id']]
            v=photometric_veto(r['photometric'],references,1e9)
            if label and v['state']!='UNKNOWN':
                record={'video':vid,'observation':r['observation_id'],'label':label,'distance':v['minimum_ab_distance']}
                (photodists if label=='TARGET' else negdist).append(record)
    threshold=math.ceil((max([x['distance'] for x in photodists],default=35.)+5.)/5)*5.
    old=read(OLD/'benchmark/backbone_metrics.json');max3=old['dinov3']['negative']['max'];max2=old['dinov2']['negative']['max']
    round02=lambda x:math.ceil(x/.02-1e-10)*.02
    g=round02(max3+.04);a=round02(max3+.16);v2=round02(max2+.14)
    confirmation=ConfirmationPolicy(g_support=g,g_lower=g-.02,g_current=g,a_support=a,a_lower=a-.04,a_current=a,
        v2_support=v2,photometric_threshold=threshold,calibrated=True)
    # Global target continuity quantiles with broad safety margins; no val/case-specific rules.
    quant=lambda key,q:float(np.quantile([t[key] for t in transitions],q))
    epoch=EpochPolicy(jump_image_diagonals=max(.25,quant('jump',.995)*1.5),scale_ratio=max(4.,quant('scale_ratio',.995)*1.5),
        aspect_ratio=max(2.5,quant('aspect_ratio',.995)*1.5),local_change_similarity=min(.65,quant('similarity',.02)-.05),photometric_change_distance=threshold)
    geometry={**read(OLD/'calibration/confirmation_policy.json')['selected_geometry'],'max_border_fraction':.5,'minimum_occupied_cells':4}
    # Prior development geometric quality calibration retained; add provenance/spatial tests, not higher inlier thresholds.
    parameters={'confirmation':asdict(confirmation),'epoch':asdict(epoch),'geometry':geometry,
        'scope':'DEVELOPMENT ONLY; no val GT or metrics read','calibrated_unix':time.time(),
        'v3_support_justification':f'Observed labeled distractor maximum{max3:.6f};G margin+.04,A margin+.16',
        'v2_support_justification':f'Observed labeled distractor maximum{max2:.6f};correlated crosscheck margin+.14',
        'photometric_justification':'Cutoff above every measured trusted development target nearest earlier-target foreground distance, plus5 Lab units. Missing reliable foreground is UNKNOWN.',
        'temporal_justification':'G3independentframes/.4s;A5frames/.8s. A current/median/lower stronger thanG. Short stitch unique IoU≥.35,similarity≥.86 across≤.4s;gaps>.6split. Appearance change persists2frames.',
        'development_source_hashes':{name:sha(OLD/'benchmark'/name) for name in ['positive_observations.json','negative_observations.json','label_provenance.json']}}
    save(OUT/'calibration/parameters.json',parameters);save(OUT/'candidate_epochs/policy.json',asdict(epoch));save(OUT/'calibration/candidate_epoch_policy.json',asdict(epoch))
    save(OUT/'calibration/route_g_policy.json',{'thresholds':asdict(confirmation),'route':'G','independent_current_geometry_required':True})
    save(OUT/'calibration/route_a_policy.json',{'thresholds':asdict(confirmation),'route':'A','geometry':'UNKNOWN only, never INVALID_EVIDENCE','v2_role':'correlated crosscheck'})
    save(OUT/'appearance/photometric_veto.json',{'threshold':threshold,'positive_pairs':photodists,'negative_pairs':negdist,
        'trusted_target_veto_count':sum(x['distance']>threshold for x in photodists),'distractor_veto_count':sum(x['distance']>threshold for x in negdist),
        'outputs':['UNKNOWN','NO_CONTRADICTION','STRONG_CONTRADICTION'],'positive_identity_allowed':False})
    save(OUT/'candidate_epochs/epoch_calibration.json',{'trusted_transitions':transitions,'selected':asdict(epoch)})
    save(OUT/'lightglue/policy.json',geometry)
    save(OUT/'evidence_integrity/policy.json',{'current_candidate_required':True,'reference_predates_candidate_epoch':True,
        'self_same_hash_same_epoch_lineage_forbidden':True,'original_decode_validation_required':True,'invalid_evidence_never_positive':True,
        'backfill':'sameepoch only; clean current-verified temporal support, no pending discontinuity, per-row v3/v2/support/veto checks'})
    print('Development calibrated',parameters,flush=True)
