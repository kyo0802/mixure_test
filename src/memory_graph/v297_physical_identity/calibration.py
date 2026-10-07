"""Development-only normalized calibration; scenario criteria are already sealed."""
from dataclasses import asdict
import math
import numpy as np
from .io import OUT,PREV,OLD,read,save,sha
from .physical import PhysicalPolicy,edge_distance
from .person import PersonPolicy,CameraCompensator,center
from .inputs import prepare

def calibrate():
    if (OUT/'FROZEN_V297_POLICY_MANIFEST.json').exists():raise PermissionError('Policy frozen')
    seal=read(OUT/'development_gt/SCENARIOS_FROZEN_BEFORE_POLICY.json')
    if not seal or any(sha(OUT/'development_gt'/p)!=h for p,h in seal['files'].items()):raise ValueError('Scenario definitions drifted')
    cadence=[];moves=[];near=[];coverage={}
    for i in range(1,10):
        vid=f'test{i}';rows,frames=prepare(vid);gt=read(OUT/f'development_gt/{vid}_identity_scenario.json');positive=set(gt['reviewed_target_observation_ids'])
        by={}
        for r in rows:
            if r['observation_id'] in positive and (r['frame'] not in by or r['confidence']>by[r['frame']]['confidence']):by[r['frame']]=r
        camera=CameraCompensator();old=None;count=0
        for a,b in zip(frames,frames[1:]):cadence.append(b['time']-a['time'])
        for f in frames:
            c=camera.update(f);count+=c['reliable'];r=by.get(f['frame'])
            if not r:continue
            persons=[p for p in f['anchors'] if p['raw_label']=='person']
            if persons:
                d=min(edge_distance(r['bbox'],p['bbox'])/math.hypot(*f['image_size']) for p in persons)
                if d<=.12:near.append(d)
            if old and c['reliable'] and old[1]['reliable'] and c['camera_segment']==old[1]['camera_segment'] and 0<r['time']-old[0]['time']<=.401:
                raw=(center(r['bbox'])-center(old[0]['bbox']))/math.hypot(*f['image_size']);comp=raw-(np.asarray(c['cumulative_translation'])-old[1]['cumulative_translation']);moves.append(float(np.linalg.norm(comp)))
            old=(r,c)
        coverage[vid]={'camera_reliable_frames':count,'sampled_frames':len(frames),'person_frames':sum(any(a['raw_label']=='person' for a in f['anchors']) for f in frames)}
    step=float(np.median(cadence));base=max(.025,min(.06,float(np.quantile(moves,.95)) if moves else .025));prox=max(.045,min(.06,(float(np.quantile(near,.9))+.01) if near else .045))
    p=PhysicalPolicy(continuity_horizon=round(step*6,3),base_reach=base,proximity_distance=prox)
    previous=read(PREV/'calibration/parameters.json');cfg={**previous,'physical':asdict(p),'person':asdict(PersonPolicy()),'camera':{'min_anchors':3,'residual_limit':.015,'maximum_scale':1.6},
        'scope':'V297 DEVELOPMENT ONLY, deterministic physical/interaction gates; no val calibration','calibration_justification':{'sample_cadence_median':step,'short_horizon':'6sample intervals, bounded by camera chain and measured motion','base_reach':'95th percentile trusted development adjacent compensated displacement, conservative floor.025 cap.06','proximity':'90th percentile near target/person edge distance plus.01, floor.045 cap.06','motion':'At least3frames/.4s, two nonzero compensated motions, cosine>=.8 plus relative geometry<=.055','long_gap':'No physical reachability extrapolation beyond bounded horizon; interaction needs live same PersonEpoch and reliable camera chain','Negative':'Persistent simultaneous separation only, not partial duplicate bounding boxes'},'development_distributions':{'compensated_steps':moves,'near_person_distances':near},'evidence_coverage':coverage}
    save(OUT/'calibration/parameters.json',cfg);save(OUT/'calibration/physical_policy.json',{'physical':cfg['physical'],'camera':cfg['camera'],'calibration_justification':cfg['calibration_justification'],'development_distributions':cfg['development_distributions'],'evidence_coverage':coverage})
    save(OUT/'calibration/interaction_policy.json',{'person':cfg['person'],'proximity':prox,'motion_coupling':{'frames':p.coupling_frames,'span':p.coupling_span,'minimum_compensated_speed':p.minimum_motion_speed,'direction_cosine':p.direction_cosine,'relative_stability':p.relative_stability},'occlusion_horizon':p.interaction_horizon,'reappearance_frames':p.reappearance_frames,'reappearance_span':p.reappearance_span,'no_carrying_or_action_truth':True})
    save(OUT/'person_epochs/policy.json',cfg['person']);save(OUT/'physical_identity/state_policy.json',{'physical':cfg['physical'],'only_Guard_authorized_current_updates':True,'no_future_information':True,'no_identity_authority':True})
    save(OUT/'interaction/state_machine.json',{'states':['NO_INTERACTION_CONTEXT','TARGET_NEAR_PERSON','TARGET_MOTION_COUPLED_WITH_PERSON','TARGET_OCCLUDED_WITH_PERSON','TARGET_UNOBSERVED_AFTER_INTERACTION','CANDIDATE_REAPPEARED_NEAR_SAME_PERSON','CANDIDATE_CONTEXT_SUPPORTED','CANDIDATE_CONTEXT_CONTRADICTED','CONTEXT_UNKNOWN'],
        'transitions':['persistent authorized target proximity -> near person','multiple nonzero camera-compensated motions + stable relative geometry -> coupled','persistent overlap/coupling then target absent while same PersonEpoch remains -> occlusion hypothesis','same live PersonEpoch+timing+relative region+multiple current candidate frames -> context supported','person/scene break or timeout -> UNKNOWN','known distinct or physical contradiction -> context contradicted'],'no_weighted_score':True,'no_semantic_action_inference':True})
    print('Calibrated development only; horizon',p.continuity_horizon,'reach',base,'proximity',prox,flush=True)
