"""Causal physical-candidate hypotheses; no target identity or authority."""
from dataclasses import dataclass,asdict
import math
from memory_graph.identity.contracts import iou,cosine

@dataclass(frozen=True)
class EpochPolicy:
    max_gap:float=.6
    stitch_gap:float=.4
    stitch_iou:float=.35
    stitch_similarity:float=.86
    jump_image_diagonals:float=.25
    scale_ratio:float=4.
    aspect_ratio:float=2.5
    local_change_similarity:float=.65
    change_persistence:int=2
    sam_loss_persistence:int=2
    photometric_change_distance:float=40.
    stitch_motion_limit:float=.10
    stitch_sam_similarity:float=.76

def transition(a,b):
    aa=a['bbox'];bb=b['bbox'];w,h=b.get('canonical_metadata',{}).get('source_dimensions',[1920,1080])
    area=lambda box:max(1.,(box[2]-box[0])*(box[3]-box[1]))
    aspect=lambda box:(box[2]-box[0])/max(1.,box[3]-box[1])
    jump=math.hypot((aa[0]+aa[2]-bb[0]-bb[2])/2,(aa[1]+aa[3]-bb[1]-bb[3])/2)/math.hypot(w,h)
    return {'gap':b['time']-a['time'],'iou':iou(aa,bb),'similarity':cosine(tuple(a['v3']),tuple(b['v3'])),
        'jump':jump,'scale_ratio':max(area(aa),area(bb))/min(area(aa),area(bb)),
        'aspect_ratio':max(aspect(aa),aspect(bb))/min(aspect(aa),aspect(bb))}

class CandidateEpochBuilder:
    def __init__(self,video,policy=None):
        self.video=video;self.policy=policy or EpochPolicy();self.epochs={};self.locals={};self.last={};self.events=[];self.pending={}
    def _new(self,row,reason):
        eid=f'ce:{self.video}:{len(self.epochs)+1:04d}'
        self.epochs[eid]={'candidate_epoch_id':eid,'start_time':row['time'],'start_frame':row['frame'],
            'local_track_ids':[],'observation_ids':[],'end_reason':None,'end_time':None,'creation_reason':reason}
        self.events.append({'kind':'SPLIT' if reason!='NEW_LOCAL_CANDIDATE' else 'NEW','epoch':eid,'frame':row['frame'],'reason':reason})
        return eid
    def process(self,rows,allow_stitch=True):
        p=self.policy;out=[];present={r['candidate_id'] for r in rows};used=set()
        for row in rows:
            local=row['candidate_id'];eid=self.locals.get(local);previous=self.last.get(eid);unresolved=False;reason=None
            if previous:
                tr=transition(previous,row)
                if tr['gap']>p.max_gap+.001:reason='OBSERVATION_GAP_OR_TRACKER_RECYCLE'
                elif row.get('scene_break'):reason='SCENE_BREAK'
                elif row.get('tracker_reset'):reason='EXPLICIT_TRACKER_RESET'
                elif tr['jump']>p.jump_image_diagonals:reason='IMPLAUSIBLE_SPATIAL_JUMP'
                elif tr['scale_ratio']>p.scale_ratio or tr['aspect_ratio']>p.aspect_ratio:reason='BBOX_DISCONTINUITY'
                elif eid in used:reason='SAME_CLASS_COEXISTENCE_CONFLICT'
                else:
                    pd=previous.get('photometric',{});rd=row.get('photometric',{})
                    photochange=bool(pd.get('usable') and rd.get('usable') and math.dist(pd['ab'],rd['ab'])>p.photometric_change_distance)
                    mask_transition=bool(previous.get('foreground_mask_path'))!=bool(row.get('foreground_mask_path'))
                    # Native pooling switches at reliable mask acquisition; a representation
                    # transition alone is not a physical change point at a short smooth step.
                    representation_change=mask_transition and tr['gap']<=p.stitch_gap+.001 and tr['iou']>=.1 and row.get('sam_overlap',0)>=.3
                    low=(tr['similarity'] is None or tr['similarity']<p.local_change_similarity) and not representation_change or photochange
                    samloss=previous.get('sam_overlap',0)>=.3 and row.get('sam_overlap',0)<.1
                    pending=self.pending.get(eid,{'appearance':0,'sam':0})
                    pending={'appearance':pending['appearance']+1 if low else 0,'sam':pending['sam']+1 if samloss else 0}
                    self.pending[eid]=pending
                    if pending['appearance']>=p.change_persistence:reason='SUSTAINED_LOCAL_APPEARANCE_CHANGE'
                    elif pending['sam']>=p.sam_loss_persistence:reason='SAM_CONTINUITY_LOSS'
                    elif low or samloss:unresolved=True
                if reason:
                    self.epochs[eid].update(end_reason=reason,end_time=row['time']);eid=None
            if eid is None and allow_stitch and not reason:
                possible=[]
                for other,prev in self.last.items():
                    e=self.epochs[other]
                    if other in used or e['end_time'] is not None or set(e['local_track_ids']).intersection(present):continue
                    tr=transition(prev,row)
                    pd=prev.get('photometric',{});rd=row.get('photometric',{})
                    color_consistent=not (pd.get('usable') and rd.get('usable') and math.dist(pd['ab'],rd['ab'])>p.photometric_change_distance)
                    appearance_motion=tr['similarity'] is not None and tr['similarity']>=p.stitch_similarity and (tr['iou']>=p.stitch_iou or tr['jump']<=p.stitch_motion_limit)
                    masked_continuity=prev.get('sam_overlap',0)>=.9 and row.get('sam_overlap',0)>=.9 and tr['iou']>=.1 and tr['similarity'] is not None and tr['similarity']>=p.stitch_sam_similarity
                    if 0<tr['gap']<=p.stitch_gap+.001 and (appearance_motion or masked_continuity) and tr['scale_ratio']<=p.scale_ratio and color_consistent and not row.get('scene_break') and not prev.get('epoch_unresolved'):
                        possible.append(other)
                if len(possible)==1:
                    eid=possible[0];self.events.append({'kind':'STITCH','epoch':eid,'frame':row['frame'],'local_track':local,'reason':'unique short-gap spatial+appearance continuity; no identity grant'})
            if eid is None:eid=self._new(row,reason or 'NEW_LOCAL_CANDIDATE')
            e=self.epochs[eid];self.locals[local]=eid;used.add(eid)
            if local not in e['local_track_ids']:e['local_track_ids'].append(local)
            e['observation_ids'].append(row['observation_id'])
            r={**row,'local_track_id':local,'candidate_id':eid,'candidate_epoch_id':eid,'candidate_epoch_start':e['start_time'],
                'epoch_unresolved':unresolved,'epoch_split_reason':reason,'local_track_ids':list(e['local_track_ids'])}
            # One suspicious frame cannot replace the stable continuity reference.
            if not unresolved:self.last[eid]=r
            else:self.events.append({'kind':'PENDING_DISCONTINUITY','epoch':eid,'frame':row['frame']})
            out.append(r)
        return out
    def snapshot(self):return {'epochs':list(self.epochs.values()),'events':self.events,'policy':asdict(self.policy)}
