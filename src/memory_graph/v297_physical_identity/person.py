"""Short geometric person hypotheses and conservative partial camera translation."""
from dataclasses import dataclass,asdict
import math
import numpy as np
from memory_graph.identity.contracts import iou

def center(box):return np.asarray([(box[0]+box[2])/2,(box[1]+box[3])/2],float)
def area(box):return max(1.,(box[2]-box[0])*(box[3]-box[1]))

@dataclass(frozen=True)
class PersonPolicy:
    maximum_gap:float=1.0
    stitch_gap:float=.4
    stitch_iou:float=.3
    maximum_jump:float=.18
    scale_ratio:float=4.

class PersonEpochBuilder:
    def __init__(self,video,policy=None):
        self.video=video;self.policy=policy or PersonPolicy();self.locals={};self.last={};self.epochs={};self.events=[]
    def process(self,timestamp,people,image_size,scene_break=False):
        diag=math.hypot(*image_size);out=[];used=set();present={p.get('anchor_key',p.get('local_track_id')) for p in people}
        for p in people:
            local=p.get('anchor_key',p.get('local_track_id'));eid=self.locals.get(local);prev=self.last.get(eid);reason=None
            if prev:
                gap=timestamp-prev['time'];jump=np.linalg.norm(center(p['bbox'])-center(prev['bbox']))/diag;scale=max(area(p['bbox']),area(prev['bbox']))/min(area(p['bbox']),area(prev['bbox']))
                if gap>self.policy.maximum_gap+.001:reason='PERSON_GAP_OR_RECYCLE'
                elif scene_break or p.get('tracker_reset'):reason='PERSON_SCENE_OR_RESET'
                elif jump>self.policy.maximum_jump or scale>self.policy.scale_ratio:reason='PERSON_GEOMETRIC_DISCONTINUITY'
                elif eid in used:reason='PERSON_SIMULTANEOUS_CONFLICT'
                if reason:self.epochs[eid]['end_reason']=reason;eid=None
            if eid is None and not reason and not scene_break:
                possible=[k for k,v in self.last.items() if k not in used and not self.epochs[k]['end_reason'] and self.epochs[k]['local_track_ids'][-1] not in present and 0<timestamp-v['time']<=self.policy.stitch_gap+.001 and iou(v['bbox'],p['bbox'])>=self.policy.stitch_iou and np.linalg.norm(center(p['bbox'])-center(v['bbox']))/diag<=self.policy.maximum_jump]
                if len(possible)==1:eid=possible[0];self.events.append({'state':'SHORT_PERSON_FRAGMENT_STITCH','person_epoch':eid,'time':timestamp,'local_track':local})
            if eid is None:
                eid=f'pe:{self.video}:{len(self.epochs)+1:04d}';self.epochs[eid]={'person_epoch_id':eid,'start_time':timestamp,'local_track_ids':[],'observation_ids':[],'end_reason':None}
                self.events.append({'state':'NEW_PERSON_EPOCH','person_epoch':eid,'time':timestamp,'reason':reason or 'NEW_LOCAL_PERSON'})
            e=self.epochs[eid]
            if local not in e['local_track_ids']:e['local_track_ids'].append(local)
            row={'person_epoch_id':eid,'local_track_id':local,'time':timestamp,'frame':p.get('frame',round(timestamp*30)),'bbox':list(p['bbox']),'producer':'raw-detector short geometric PersonEpoch; not permanent person identity'}
            e['observation_ids'].append(f'{local}@{timestamp}');self.locals[local]=eid;self.last[eid]=row;out.append(row);used.add(eid)
        return out
    def snapshot(self):return {'policy':asdict(self.policy),'epochs':list(self.epochs.values()),'events':self.events}

class CameraCompensator:
    """Median translation with scale/residual checks, no global camera pose claim."""
    STATIC_LABELS={'chair','table','refrigerator','microwave','tv','clock','oven'}
    def __init__(self,min_anchors=3,residual_limit=.015,maximum_scale=1.6):
        self.min_anchors=min_anchors;self.residual_limit=residual_limit;self.maximum_scale=maximum_scale;self.previous=None;self.cumulative=np.zeros(2);self.segment=0;self.last_reliable=False;self.results=[]
    def update(self,frame):
        diag=math.hypot(*frame['image_size']);offsets=[];keys=[];prev=self.previous;valid_time=bool(prev and 0<frame['time']-prev['time']<=.401 and frame.get('scene_ok',True))
        if valid_time:
            old={a['anchor_key']:a for a in prev['anchors'] if a['raw_label'] in self.STATIC_LABELS}
            for a in frame['anchors']:
                b=old.get(a['anchor_key'])
                if b and b['raw_label']==a['raw_label'] and max(area(a['bbox']),area(b['bbox']))/min(area(a['bbox']),area(b['bbox']))<=self.maximum_scale:
                    offsets.append((center(a['bbox'])-center(b['bbox']))/diag);keys.append(a['anchor_key'])
        translation=np.median(offsets,axis=0) if offsets else np.zeros(2);residual=np.linalg.norm(np.asarray(offsets)-translation,axis=1) if offsets else np.asarray([])
        reliable=bool(len(offsets)>=self.min_anchors and np.quantile(residual,.75)<=self.residual_limit)
        if reliable:
            if not self.last_reliable:self.segment+=1;self.cumulative=np.zeros(2)
            self.cumulative+=translation
        else:self.cumulative=np.zeros(2)
        result={'frame':frame['frame'],'time':frame['time'],'reliable':reliable,'translation':translation.tolist() if reliable else None,
            'raw_anchor_offsets':[x.tolist() for x in offsets],'anchor_keys':keys,'residual_p75':float(np.quantile(residual,.75)) if len(residual) else None,
            'cumulative_translation':self.cumulative.tolist() if reliable else None,'camera_segment':self.segment,
            'normalized_units':'image_diagonal','limitation':'partial median translation only; unsupported rotation/scale/scene change yields UNKNOWN'}
        self.previous=frame;self.last_reliable=reliable;self.results.append(result);return result
