"""Canonical raw crops. Development labels are used only by the benchmark."""
from collections import defaultdict
import math
import re
import cv2
import numpy as np
from PIL import Image
from memory_graph.identity.contracts import iou
from .io import OUT, ROOT, read, save, sha, sources


def crop_observation(image, bbox, mask=None):
    h,w=image.shape[:2];x1,y1,x2,y2=bbox
    px=.05*(x2-x1);py=.05*(y2-y1)
    bounds=(max(0,int(x1-px)),max(0,int(y1-py)),min(w,math.ceil(x2+px)),min(h,math.ceil(y2+py)))
    a,b,c,d=bounds
    if c<=a or d<=b:raise ValueError('Invalid canonical crop')
    rgb=cv2.cvtColor(image[b:d,a:c],cv2.COLOR_BGR2RGB); foreground=None
    diagnostics={'used':False,'fallback':'no reliable same-frame SAM mask'}
    if mask is not None and mask.shape==(h,w):
        ys,xs=np.nonzero(mask)
        if len(xs)>=32:
            mb=(int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1)
            region=mask[b:d,a:c].astype(bool);fraction=float(region.mean())
            diagnostics.update(mask_bbox_iou=iou(mb,bbox),foreground_fraction=fraction)
            # Pure mask quality, never identity evidence or a label.
            if iou(mb,bbox)>=.5 and .15<=fraction<=.98 and region.sum()/len(xs)>=.85:
                foreground=region;rgb=rgb.copy();rgb[~region]=128
                diagnostics.update(used=True,fallback=None)
    return rgb,foreground,{'crop_bounds':list(bounds),'source_dimensions':[w,h],'crop_dimensions':[c-a,d-b],
                          'margin_fraction':.05,'aspect_preserved':True,'mask':diagnostics}


def extract(video_id,*,source_override=None,video_override=None,safe_override=None):
    manifest=OUT/f'crops/{video_id}/observations.json'
    if manifest.exists():return read(manifest)
    source,video,safe=sources(video_id) if source_override is None else (source_override,video_override,safe_override)
    meta=read(source/'video_metadata.json')
    metrics=read(safe/'metrics.json')
    if sha(video)!=metrics['video_sha256']:raise ValueError('Source video changed since safe identity replay')
    tracks=read(source/'perception/tracks.json');raw=read(source/'perception/yolo_detections.json')
    by=defaultdict(list);anchors=defaultdict(list)
    for tr in tracks:
        for o in tr['observations']:
            if tr['detector_class']=='cell phone':by[o['frame_index']].append((f"track:{tr['track_id']}",o,'yolo_track'))
            else:anchors[o['frame_index']].append({'anchor_key':f"local:{tr['track_id']}",'entity_id':f"local:{tr['track_id']}",
                'raw_label':tr['detector_class'],'bbox':o['bbox'],'authorized':True,'provenance':'raw local detector; no persistent identity'})
    for index,o in enumerate(raw):
        if o['class_name']=='cell phone' and not any(iou(o['bbox'],x[1]['bbox'])>=.5 for x in by[o['frame_index']]):
            by[o['frame_index']].append((f'raw:{index}',o,'yolo_raw'))
    sam=defaultdict(list)
    for seg in read(source/'sam/sam_continuity_log.json',{}).get('segments',[]):
        for o in seg.get('observations',[]):
            sam[o['frame_index']].append((o,seg.get('masks_rle',{}).get(f"{o['frame_index']}:{o['object_id']}")))
    episodes=read(source/'perception/episodes.json',read(source/'upstream_v21/event_analysis/episodes.json',[]))
    breaks={e['start_frame'] for e in episodes[1:]};result=[];frame_rows=[];cap=cv2.VideoCapture(str(video))
    try:
        for info in meta['sampled_frames']:
            f=info['frame_index'];ts=info['timestamp'];frame_rows.append({'frame':f,'time':ts,'anchors':anchors[f],
                'image_size':[meta['width'],meta['height']],'candidate_present':bool(by[f] or sam[f]),'scene_ok':True})
            if not by[f]:continue
            cap.set(cv2.CAP_PROP_POS_FRAMES,f);ok,img=cap.read()
            if not ok:raise OSError(f'Cannot decode {video_id}:{f}')
            for cid,o,kind in by[f]:
                match=max(sam[f],key=lambda x:iou(x[0]['bbox'],o['bbox']),default=None)
                overlap=iou(match[0]['bbox'],o['bbox']) if match else 0.
                drift=bool(match and overlap>=.3 and match[0].get('diagnostics',{}).get('possible_mask_drift'))
                mask=None
                if match and overlap>=.5 and not drift and match[1]:
                    from memory_graph.v22.sam_tracking import decode_mask
                    mask=decode_mask(match[1])
                rgb,fg,md=crop_observation(img,o['bbox'],mask)
                oid=f'{cid}@{f}';path=OUT/f'crops/{video_id}/{cid.replace(":","_")}_f{f:06d}.png';path.parent.mkdir(parents=True,exist_ok=True)
                Image.fromarray(rgb).save(path);mp=None
                if fg is not None:
                    mp=path.with_name(path.stem+'_mask.png');Image.fromarray(fg.astype('uint8')*255).save(mp)
                # Hash a small view for exact/near duplicate audits; no labels from appearance.
                small=cv2.resize(rgb,(32,32),interpolation=cv2.INTER_AREA)
                result.append({'video_id':video_id,'observation_id':oid,'candidate_id':cid,'frame':f,'time':ts,
                    'bbox':o['bbox'],'label':'cell phone','confidence':o['confidence'],'source':kind,
                    'provenance':f'{source.relative_to(ROOT).as_posix()}/perception#{oid}',
                    'crop_path':str(path),'crop_sha256':sha(path),'foreground_mask_path':str(mp) if mp else None,
                    'sam_overlap':overlap,'drift':drift,'scene_break':f in breaks,'canonical_metadata':md,
                    'view_hash':__import__('hashlib').sha256(small.tobytes()).hexdigest()})
    finally:cap.release()
    save(manifest,result);save(OUT/f'crops/{video_id}/frames.json',frame_rows)
    save(OUT/f'crops/{video_id}/source.json',{'video_sha256':metrics['video_sha256'],'raw_sources':{
        x:sha(source/x) for x in ['video_metadata.json','perception/tracks.json','perception/yolo_detections.json']}})
    return result


def benchmark_dataset():
    dest=OUT/'benchmark/identity_dataset_manifest.json'
    if dest.exists():return read(dest)
    positives=[];negatives=[];provenance=[];all_rows=[];references={};conflicts=[]
    for n in range(1,10):
        vid=f'test{n}';rows=extract(vid);all_rows+=rows;byid={x['observation_id']:x for x in rows}
        _,_,safe=sources(vid);snap=read(safe/'identity.json');trusted={x['observation']['observation_id']:x for x in snap['final_ledger']}
        coreids=[b['observation_id'] for b in snap['banks']['core'] if b['active']]
        references[vid]=coreids
        labels={};reasons={}
        for oid,ledger in trusted.items():
            if oid in byid:labels[oid]='TARGET';reasons[oid]={'type':'FINAL_CONTINUITY_AUTHORIZED_EPOCH','source':str(safe/'identity.json'),
                    'authorization_id':ledger['authorization_id'],'alias_id':ledger['alias_id'],'epoch_id':ledger['epoch_id']}
        for oid in coreids:
            if oid in byid:labels[oid]='TARGET';reasons.setdefault(oid,{'type':'CAUSAL_INITIAL_BINDING_CORE','source':str(safe/'identity.json')})
        for x in rows:
            targets=[byid[oid] for oid in trusted if oid in byid and byid[oid]['frame']==x['frame']]
            if any(t['candidate_id']!=x['candidate_id'] and iou(t['bbox'],x['bbox'])<.1 for t in targets):
                labels[x['observation_id']]='DISTRACTOR';reasons[x['observation_id']]={'type':'SAME_FRAME_SPATIALLY_SEPARATE_FROM_AUTHORIZED_TARGET',
                    'trusted_observation_ids':[t['observation_id'] for t in targets],'source':str(safe/'identity.json')}
        review=ROOT/f'outputs_v26/{vid}/review.md';stream=read(sources(vid)[0]/'identity/candidate_stream.json',{}).get('observations',[])
        detections=read(sources(vid)[0]/'perception/yolo_detections.json')
        if review.exists():
            for line in review.read_text(encoding='utf8').splitlines():
                cells=[c.strip() for c in line.split('|')]
                if len(cells)<7 or not cells[1].startswith('candidate_') or cells[6] not in {'TARGET','DISTRACTOR'}:continue
                cid,f,label=cells[1],int(cells[2]),cells[6]
                rawrows=[s for s in stream if s.get('candidate_id')==cid and s['frame_index']==f]
                mapped=[]
                for s in rawrows:
                    d=detections[s['raw_detection_index']]
                    mapped += [r for r in rows if r['frame']==f and iou(r['bbox'],d['bbox'])>=.85]
                for x in mapped:
                    oid=x['observation_id']
                    if oid in labels and labels[oid]!=label:conflicts.append({'video':vid,'observation':oid,'existing':labels[oid],'review':label});continue
                    labels[oid]=label;reasons[oid]={'type':'PREEXISTING_REVIEWED_DEVELOPMENT_POINT','source':str(review),
                        'source_sha256':sha(review),'legacy_candidate_id':cid,'reviewed_frame':f,'mapping':'same-frame raw detection IoU>=.85; no temporal label extrapolation'}
        # Reviewed target points can also prove simultaneous spatially distinct negatives.
        target_rows=[byid[oid] for oid,label in labels.items() if label=='TARGET']
        for x in rows:
            witnesses=[t for t in target_rows if t['frame']==x['frame'] and t['candidate_id']!=x['candidate_id'] and iou(t['bbox'],x['bbox'])<.1]
            if witnesses and x['observation_id'] not in labels:
                labels[x['observation_id']]='DISTRACTOR';reasons[x['observation_id']]={'type':'COEXISTS_WITH_PROVEN_DEVELOPMENT_TARGET_POINT',
                    'trusted_observation_ids':[t['observation_id'] for t in witnesses],
                    'witness_provenance':[reasons[t['observation_id']] for t in witnesses]}
        for oid,label in labels.items():
            x={**byid[oid],'identity_label':label,'label_provenance':reasons[oid]}
            (positives if label=='TARGET' else negatives).append(x);provenance.append({'video_id':vid,'observation_id':oid,'label':label,**reasons[oid]})
    tracklets=[]
    grouped=defaultdict(list)
    for x in positives+negatives:grouped[(x['video_id'],x['candidate_id'],x['identity_label'])].append(x)
    for (vid,cid,label),group in grouped.items():
        chunks=[]
        for x in sorted(group,key=lambda x:x['time']):
            if not chunks or x['time']-chunks[-1][-1]['time']>.6:chunks.append([])
            chunks[-1].append(x)
        for i,chunk in enumerate(chunks):
            tracklets.append({'tracklet_id':f'{vid}/{cid}/{label}/{i}','video_id':vid,'candidate_id':cid,'label':label,
                             'observation_ids':[x['observation_id'] for x in chunk],'duration':chunk[-1]['time']-chunk[0]['time'],
                             'label_scope':'Only individually proven rows; no propagation of reviewed-point labels'})
    manifest={'scope':'DEVELOPMENT_ONLY; no val pixels/GT in calibration','positives':len(positives),'negatives':len(negatives),
        'raw_observations':len(all_rows),'core_reference_ids':references,'label_conflicts':conflicts,
        'unlabeled':len(all_rows)-len(positives)-len(negatives),'canonical_protocol':'Original frame,5% margin, aspect retained, reliable same-frame mask or recorded bbox fallback',
        'dataset_hash':__import__('hashlib').sha256(__import__('json').dumps(provenance,sort_keys=True).encode()).hexdigest()}
    save(OUT/'benchmark/positive_observations.json',positives);save(OUT/'benchmark/negative_observations.json',negatives)
    save(OUT/'benchmark/label_provenance.json',provenance);save(OUT/'benchmark/tracklets.json',tracklets);save(dest,manifest)
    return manifest
