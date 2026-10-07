"""Causal geometry/interaction evidence. No aliases, tokens, bank or ledger writes."""
from dataclasses import dataclass,asdict
from collections import defaultdict
import math
import numpy as np
from memory_graph.identity.contracts import iou,cosine
from memory_graph.v296_reid.integrity import clean,provenance
from .person import center,area

@dataclass(frozen=True)
class PhysicalPolicy:
    continuity_horizon:float=1.2
    base_reach:float=.025
    maximum_reach:float=.12
    velocity_buffer:float=.025
    proximity_distance:float=.045
    proximity_frames:int=3
    proximity_span:float=.4
    coupling_frames:int=3
    coupling_span:float=.4
    minimum_motion_speed:float=.01
    direction_cosine:float=.8
    relative_stability:float=.055
    interaction_horizon:float=4.
    reappearance_frames:int=3
    reappearance_span:float=.4
    coexistence_frames:int=2
    coexistence_span:float=.2
    distinct_separation:float=.008
    known_negative_similarity:float=.94
    maximum_bbox_scale:float=4.

def compact(row):return {k:v for k,v in row.items() if k not in ['v3','v2','pixel_descriptor','physical_identity_evidence']}
def edge_distance(a,b):
    return math.hypot(max(0,a[0]-b[2],b[0]-a[2]),max(0,a[1]-b[3],b[1]-a[3]))
def separated(a,b,diag,policy):
    ca=center(a);cb=center(b)
    inside=lambda p,r:r[0]<=p[0]<=r[2] and r[1]<=p[1]<=r[3]
    return bool(iou(a,b)<.1 and not inside(ca,b) and not inside(cb,a) and edge_distance(a,b)/diag>policy.distinct_separation)
def motion_coupling(history,policy):
    rows=history[-8:]
    if len(rows)<policy.coupling_frames or rows[-1]['time']-rows[0]['time']<policy.coupling_span-1e-5 or not all(r['camera_reliable'] for r in rows) or len({r.get('camera_segment',0) for r in rows})>1:return 'MOTION_UNKNOWN'
    t=[];p=[]
    for a,b in zip(rows,rows[1:]):
        dt=b['time']-a['time']
        if dt<=0:return 'MOTION_UNKNOWN'
        t.append((np.asarray(b['target_comp'])-a['target_comp'])/dt);p.append((np.asarray(b['person_comp'])-a['person_comp'])/dt)
    active=[(a,b) for a,b in zip(t,p) if np.linalg.norm(a)>=policy.minimum_motion_speed and np.linalg.norm(b)>=policy.minimum_motion_speed]
    if len(active)<2:return 'MOTION_UNKNOWN'
    aligned=all(float(np.dot(a,b)/np.linalg.norm(a)/np.linalg.norm(b))>=policy.direction_cosine for a,b in active)
    relatives=np.asarray([r['relative'] for r in rows]);stable=max(np.linalg.norm(x-relatives[0]) for x in relatives)<=policy.relative_stability
    return 'MOTION_COUPLED' if aligned and stable else 'MOTION_NOT_COUPLED'

class PhysicalIdentityState:
    def __init__(self,target_entity_id,policy=None):
        self.target_entity_id=target_entity_id;self.policy=policy or PhysicalPolicy();self.last=None;self.target_history=[];self.candidate_history=defaultdict(list)
        self.person_history=[];self.person_epoch=None;self.occlusion=None;self.known_distinct=[];self.coexistent=defaultdict(list)
        self.frame=None;self.people=[];self.rows=[];self.camera=None;self.interaction_state='NO_INTERACTION_CONTEXT';self.events=[];self.assessments=[];self.authorized_ids=set()
    def begin_frame(self,frame,people,camera,rows):
        if self.frame and frame['time']<=self.frame['time']:raise ValueError('Physical evidence must be causal')
        self.frame=frame;self.people=people;self.camera=camera;self.rows=rows
        for r in rows:
            r['current_people']=people;self.candidate_history[r['candidate_epoch_id']].append(r)
        if not frame.get('scene_ok',True):self.occlusion=None;self.person_epoch=None;self.person_history=[];self.interaction_state='CONTEXT_UNKNOWN'
        if self.occlusion:
            alive=any(p['person_epoch_id']==self.occlusion['person_epoch'] for p in people)
            if not alive or frame['time']-self.occlusion['disappearance_time']>self.policy.interaction_horizon:
                self.events.append({'state':'CONTEXT_UNKNOWN','frame':frame['frame'],'reason':'PersonEpoch absent/broken or occlusion horizon expired'});self.occlusion=None;self.interaction_state='CONTEXT_UNKNOWN'
        if self.last and not any(r['candidate_epoch_id']==self.last['candidate_epoch_id'] and not r.get('epoch_unresolved') for r in rows):
            age=frame['time']-self.last['time'];near=self.person_history[-self.policy.proximity_frames:]
            persistent=len(near)>=self.policy.proximity_frames and near[-1]['time']-near[0]['time']>=self.policy.proximity_span-1e-5
            same=next((p for p in people if p['person_epoch_id']==self.person_epoch),None)
            if not self.occlusion and persistent and same and age<=self.policy.continuity_horizon+.001 and all(r['proximity'] in ['PERSON_NEAR_TARGET','PERSON_TARGET_OVERLAP'] for r in near) and (near[-1]['proximity']=='PERSON_TARGET_OVERLAP' or motion_coupling(near,self.policy)=='MOTION_COUPLED'):
                self.occlusion={'state':'TARGET_OCCLUDED_WITH_PERSON_HYPOTHESIS','person_epoch':self.person_epoch,'disappearance_frame':frame['frame'],'disappearance_time':frame['time'],
                    'last_relative_position':near[-1]['relative'],'motion_state':motion_coupling(near,self.policy),'confidence_class':'PERSISTENT_GEOMETRIC_HYPOTHESIS_NOT_CARRYING_TRUTH',
                    'evidence_observations':[x['observation_id'] for x in near],'target_authorizations':[x['authorization_id'] for x in near],
                    'scene_camera_segment':self.last['camera_segment']}
                self.interaction_state='TARGET_OCCLUDED_WITH_PERSON';self.events.append({**self.occlusion,'frame':frame['frame']})
        for r in rows:
            r['physical_identity_evidence']=self.assess(r)
            state=r['physical_identity_evidence']['interaction']
            context=r['physical_identity_evidence']['reappearance_context']
            if context.get('same_person_epoch') and context.get('persistent_reappearance_frames',0) and state=='INTERACTION_CONTINUITY_UNKNOWN':
                self.events.append({'state':'CANDIDATE_REAPPEARED_NEAR_SAME_PERSON','frame':r['frame'],'time':r['time'],'candidate_epoch':r['candidate_epoch_id'],'identity_authorized':False})
            if state in ['INTERACTION_CONTINUITY_SUPPORT','INTERACTION_CONTINUITY_CONTRADICTION']:
                self.events.append({'state':'CANDIDATE_CONTEXT_SUPPORTED' if state=='INTERACTION_CONTINUITY_SUPPORT' else 'CANDIDATE_CONTEXT_CONTRADICTED','frame':r['frame'],'time':r['time'],'candidate_epoch':r['candidate_epoch_id']})
        if self.occlusion and self.last and frame['time']-self.last['time']>self.policy.continuity_horizon:
            self.interaction_state='TARGET_UNOBSERVED_AFTER_INTERACTION'
    def _coordinates(self,r):
        raw=center(r['bbox'])/math.hypot(*self.frame['image_size']);offset=np.asarray(self.camera.get('cumulative_translation') or [0.,0.])
        return raw,raw-offset
    def _proximity(self,row,person):
        if not person:return 'UNKNOWN'
        diag=math.hypot(*self.frame['image_size']);d=edge_distance(row['bbox'],person['bbox'])/diag
        if iou(row['bbox'],person['bbox'])>0:return 'PERSON_TARGET_OVERLAP'
        return 'PERSON_NEAR_TARGET' if d<=self.policy.proximity_distance else 'PERSON_NOT_NEAR'
    def _reachability(self,row):
        if not self.last:return {'state':'PHYSICAL_UNKNOWN','reason':'No trusted target history','gap':None,'candidate_continuity_valid':False}
        gap=row['time']-self.last['time'];raw,comp=self._coordinates(row);raw_delta=raw-np.asarray(self.last['raw_position'])
        base={'gap':gap,'raw_displacement':float(np.linalg.norm(raw_delta)),'camera_compensated_displacement':None,'candidate_continuity_valid':False,'last_authorized_observation':self.last['observation_id']}
        if row.get('scene_break') or row.get('epoch_unresolved') or row.get('epoch_split_reason') in ['SCENE_BREAK','EXPLICIT_TRACKER_RESET','SUSTAINED_LOCAL_APPEARANCE_CHANGE','SAME_CLASS_COEXISTENCE_CONFLICT']:
            return {**base,'state':'PHYSICAL_UNKNOWN','reason':'Candidate break/pending discontinuity resets stale physical support'}
        if gap<0:return {**base,'state':'PHYSICAL_UNKNOWN','reason':'Noncausal candidate'}
        if gap>self.policy.continuity_horizon+.001:return {**base,'state':'PHYSICAL_UNKNOWN','reason':'Beyond bounded motion horizon; no invented reachability'}
        if not self.camera['reliable'] or not self.last['camera_reliable'] or self.camera['camera_segment']!=self.last['camera_segment']:
            return {**base,'state':'PHYSICAL_UNKNOWN','reason':'Camera compensation unavailable or chain broken'}
        distance=float(np.linalg.norm(comp-np.asarray(self.last['comp_position'])));speed=max((x['speed'] for x in self.target_history[-5:] if x['speed'] is not None),default=0.)
        envelope=min(self.policy.maximum_reach,self.policy.base_reach+(speed+self.policy.velocity_buffer)*gap)
        scale=max(area(row['bbox']),area(self.last['bbox']))/min(area(row['bbox']),area(self.last['bbox']))
        consistent=distance<=envelope and scale<=self.policy.maximum_bbox_scale
        return {**base,'state':'PHYSICALLY_CONSISTENT' if consistent else 'PHYSICALLY_INCONSISTENT','camera_compensated_displacement':distance,
            'motion_envelope':envelope,'last_measured_speed':speed,'bbox_scale_ratio':scale,'candidate_continuity_valid':consistent,
            'reason':'Bounded compensated displacement+elapsed time+measured velocity+scale+scene; not distance alone'}
    def distinct_link(self,row):
        for record in self.known_distinct:
            if row['candidate_epoch_id']==record['candidate_epoch_id']:
                return {'matched':True,'physical_entity_id':record['physical_entity_id'],'basis':'EXACT_SAFE_CANDIDATE_EPOCH_LINEAGE','coexistence_evidence':record['evidence']}
            refs=record['references'];scores=[cosine(tuple(row.get('v3',[])),tuple(r.get('v3',[]))) for r in refs if clean(r) and r['time']<row['candidate_epoch_start'] and r['crop_sha256']!=row['crop_sha256']]
            scores=[x for x in scores if x is not None]
            if len(scores)>=2 and min(sorted(scores,reverse=True)[:2])>=self.policy.known_negative_similarity:
                return {'matched':True,'physical_entity_id':record['physical_entity_id'],'basis':'MULTIVIEW_TRUSTED_DISTINCT_VISUAL_LINK_VETO_ONLY','similarities':scores,'coexistence_evidence':record['evidence']}
        return {'matched':False,'basis':'NO_INFORMATION'}
    def _interaction(self,row):
        h=self.occlusion
        if row.get('scene_break') or row.get('epoch_unresolved') or row.get('epoch_split_reason') in ['SCENE_BREAK','EXPLICIT_TRACKER_RESET','SUSTAINED_LOCAL_APPEARANCE_CHANGE','SAME_CLASS_COEXISTENCE_CONFLICT']:
            return {'state':'INTERACTION_CONTINUITY_UNKNOWN','reason':'Candidate discontinuity resets stale interaction support','person_epoch':None}
        if not h:return {'state':'INTERACTION_CONTINUITY_UNKNOWN','reason':'No live person-linked occlusion hypothesis','person_epoch':None}
        person=next((p for p in self.people if p['person_epoch_id']==h['person_epoch']),None)
        if not person:return {'state':'INTERACTION_CONTINUITY_UNKNOWN','reason':'Same PersonEpoch unavailable','person_epoch':h['person_epoch']}
        hist=self.candidate_history[row['candidate_epoch_id']];near=[];diag=math.hypot(*self.frame['image_size'])
        for r in hist[-8:]:
            p=next((x for x in r.get('current_people',[]) if x['person_epoch_id']==h['person_epoch']),person if r['time']==row['time'] else None)
            if p and self._proximity(r,p) in ['PERSON_NEAR_TARGET','PERSON_TARGET_OVERLAP']:
                rel=(center(r['bbox'])-center(p['bbox']))/diag;near.append({'row':r,'relative':rel.tolist()})
        lastrel=(center(row['bbox'])-center(person['bbox']))/diag;delta=float(np.linalg.norm(lastrel-np.asarray(h['last_relative_position'])))
        time_ok=row['time']-h['disappearance_time']<=self.policy.interaction_horizon+.001;region_ok=delta<=self.policy.relative_stability
        persistent=len(near)>=self.policy.reappearance_frames and near[-1]['row']['time']-near[0]['row']['time']>=self.policy.reappearance_span-1e-5
        camera_ok=self.camera['reliable'] and self.camera['camera_segment']==h['scene_camera_segment']
        state='INTERACTION_CONTINUITY_SUPPORT' if persistent and region_ok and time_ok and camera_ok else 'INTERACTION_CONTINUITY_CONTRADICTION' if camera_ok and (not region_ok or not time_ok) else 'INTERACTION_CONTINUITY_UNKNOWN'
        return {'state':state,'person_epoch':h['person_epoch'],'same_person_epoch':True,'persistent_reappearance_frames':len(near),'relative_position_delta':delta,
            'current_proximity':self._proximity(row,person),'timing_plausible':time_ok,'camera_chain_reliable':camera_ok,'occlusion_hypothesis':h,
            'candidate_evidence_observations':[x['row']['observation_id'] for x in near],'reason':'Persistent same short PersonEpoch, relative geometry, timing and reliable camera chain; geometric support only'}
    def assess(self,row):
        distinct=self.distinct_link(row);reach=self._reachability(row);interaction=self._interaction(row)
        preexist=bool(distinct['matched'] and distinct['basis']=='EXACT_SAFE_CANDIDATE_EPOCH_LINEAGE')
        others=[r for r in self.rows if r['candidate_epoch_id']!=row['candidate_epoch_id'] and r['confidence']>=.5 and separated(row['bbox'],r['bbox'],math.hypot(*self.frame['image_size']),self.policy)]
        plausible=[r['candidate_epoch_id'] for r in others if not self.distinct_link(r)['matched'] and self._reachability(r)['state']!='PHYSICALLY_INCONSISTENT']
        if interaction['state']=='INTERACTION_CONTINUITY_SUPPORT':
            plausible=[r['candidate_epoch_id'] for r in others if not self.distinct_link(r)['matched'] and self._interaction(r)['state']=='INTERACTION_CONTINUITY_SUPPORT']
        single=not self.known_distinct and not self.coexistent and not others and reach['state']=='PHYSICALLY_CONSISTENT'
        return {'candidate_epoch':row['candidate_epoch_id'],'frame':row['frame'],'time':row['time'],'reachability':reach['state'],'physical_continuity':reach,
            'interaction':interaction['state'],'reappearance_context':interaction,'PersonEpoch':interaction.get('person_epoch') or self.person_epoch,
            'person_proximity_history':self.person_history[-8:],'motion_coupling':motion_coupling(self.person_history,self.policy),
            'occlusion_hypothesis':self.occlusion,'known_distinct':distinct['matched'],'known_distinct_entity_result':distinct,
            'preexistence_contradiction':preexist,'candidate_preexistence_result':'PREEXISTING_KNOWN_DISTINCT' if preexist else 'NO_TRUSTED_PREEXISTENCE_CONTRADICTION',
            'candidate_continuity_valid':reach['candidate_continuity_valid'],'competing_plausible_epochs':plausible,'unique_physical_support':not plausible,
            'single_phone_state':'NO_COMPETING_SAME_CLASS_ENTITY_OBSERVED' if single else 'COMPETITION_OR_CONTEXT_UNKNOWN',
            'camera_compensation':self.camera,'anchor_context':[a['anchor_key'] for a in self.frame.get('anchors',[]) if a['raw_label']!='person'],
            'evidence_provider_grants_identity':False}
    def authorized(self,row,ledger):
        if not all(ledger.get(k) for k in ['authorization_id','alias_id','epoch_id']):raise PermissionError('Target state only accepts Guard-authorized ledger provenance')
        if row['time']!=self.frame['time']:raise ValueError('Backfill is not a new current physical state')
        raw,comp=self._coordinates(row);previous=self.last;dt=row['time']-previous['time'] if previous else 0
        valid=bool(previous and self.camera['reliable'] and previous['camera_reliable'] and previous['camera_segment']==self.camera['camera_segment'] and 0<dt<=self.policy.continuity_horizon+.001)
        velocity=(comp-np.asarray(previous['comp_position']))/dt if valid else None;raw_velocity=(raw-np.asarray(previous['raw_position']))/dt if previous and dt>0 else None
        current={**compact(row),'authorization_id':ledger['authorization_id'],'alias_id':ledger['alias_id'],'identity_epoch_id':ledger['epoch_id'],
            'raw_position':raw.tolist(),'comp_position':comp.tolist(),'raw_velocity':raw_velocity.tolist() if raw_velocity is not None else None,
            'compensated_velocity':velocity.tolist() if velocity is not None else None,'speed':float(np.linalg.norm(velocity)) if velocity is not None else None,
            'camera_segment':self.camera['camera_segment'],'camera_reliable':self.camera['reliable']}
        self.last=current;self.target_history.append(current);self.authorized_ids.add(ledger['authorization_id']);diag=math.hypot(*self.frame['image_size'])
        nearest=min(self.people,key=lambda p:edge_distance(row['bbox'],p['bbox']),default=None);near=self._proximity(row,nearest)
        if nearest and near in ['PERSON_NEAR_TARGET','PERSON_TARGET_OVERLAP']:
            pe=nearest['person_epoch_id']
            if pe!=self.person_epoch:self.person_history=[];self.occlusion=None
            self.person_epoch=pe;pc=center(nearest['bbox'])/diag-np.asarray(self.camera.get('cumulative_translation') or [0,0])
            relative=(center(row['bbox'])-center(nearest['bbox']))/diag
            self.person_history.append({'time':row['time'],'frame':row['frame'],'observation_id':row['observation_id'],'authorization_id':ledger['authorization_id'],
                'person_epoch':pe,'proximity':near,'target_comp':comp.tolist(),'person_comp':pc.tolist(),'relative':relative.tolist(),'camera_reliable':self.camera['reliable'],'camera_segment':self.camera['camera_segment']})
            self.person_history=self.person_history[-12:];self.interaction_state='TARGET_MOTION_COUPLED_WITH_PERSON' if motion_coupling(self.person_history,self.policy)=='MOTION_COUPLED' else 'TARGET_NEAR_PERSON'
        else:self.person_history=[];self.person_epoch=None;self.interaction_state='NO_INTERACTION_CONTEXT'
        self.events.append({'state':self.interaction_state,'frame':row['frame'],'time':row['time'],'person_epoch':self.person_epoch,'proximity':near,'authorization_id':ledger['authorization_id']})
        for other in self.rows:
            if other['candidate_epoch_id']==row['candidate_epoch_id'] or other['confidence']<.5 or not clean(other) or not separated(row['bbox'],other['bbox'],diag,self.policy):continue
            key=other['candidate_epoch_id'];self.coexistent[key].append({'time':row['time'],'frame':row['frame'],'target_observation':row['observation_id'],
                'target_authorization':ledger['authorization_id'],'target_alias':ledger['alias_id'],'candidate_observation':other['observation_id'],'target_bbox':row['bbox'],'candidate_bbox':other['bbox']})
            evidence=self.coexistent[key];refs=self.candidate_history[key]
            if len(evidence)>=self.policy.coexistence_frames and evidence[-1]['time']-evidence[0]['time']>=self.policy.coexistence_span-1e-5 and not any(k['candidate_epoch_id']==key for k in self.known_distinct):
                record={'physical_entity_id':f'distinct:{len(self.known_distinct)+1}','candidate_epoch_id':key,'evidence':list(evidence),'references':refs[-8:],
                    'interval':[evidence[0]['time'],evidence[-1]['time']],'producer':'persistent simultaneous separation from Guard-authorized target'}
                self.known_distinct.append(record);self.events.append({'state':'KNOWN_DISTINCT_PHYSICAL_ENTITY','frame':row['frame'],'physical_entity_id':record['physical_entity_id'],'candidate_epoch':key})
    def snapshot(self):
        return {'target_entity_id':self.target_entity_id,'policy':asdict(self.policy),'last_authorized_observation':self.last,
            'uncertainty':'UNKNOWN' if not self.last else 'TRUSTED_LOCAL_HISTORY_WITH_BOUNDED_GEOMETRY','interaction_state':self.interaction_state,
            'last_near_person_epoch':self.person_epoch,'person_proximity_history':self.person_history,'occlusion_hypothesis':self.occlusion,
            'known_distinct_entities':[{**k,'references':[compact(r) for r in k['references']]} for k in self.known_distinct],'events':self.events,'target_history':self.target_history}
    def prune_aliases(self,active_aliases):
        self.known_distinct=[k for k in self.known_distinct if any(x['target_alias'] in active_aliases for x in k['evidence'])]
        if self.last and self.last['alias_id'] not in active_aliases:
            self.target_history=[r for r in self.target_history if r['alias_id'] in active_aliases];self.last=self.target_history[-1] if self.target_history else None
            self.person_history=[];self.person_epoch=None;self.occlusion=None;self.interaction_state='CONTEXT_UNKNOWN'
