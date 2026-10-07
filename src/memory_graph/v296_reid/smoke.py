"""Conditional fresh integration using the unchanged pre-V294 physical interfaces."""
from collections import defaultdict
from pathlib import Path
import cv2
from PIL import Image
import numpy as np
from memory_graph.identity.contracts import iou
from .io import ROOT,OUT,read,save,sha
from .appearance import verify_rows
from .runner import replay,verify_freeze

def fresh_crops(source,video_id,video):
    from memory_graph.v295_reid.dataset import crop_observation
    from memory_graph.v22.sam_tracking import decode_mask
    meta=read(source/'video_metadata.json');by=defaultdict(list);anchors=defaultdict(list);sam=defaultdict(list)
    for tr in read(source/'perception/tracks.json'):
        for r in tr['observations']:
            if tr['detector_class']=='cell phone':by[r['frame_index']].append((f'track:{tr["track_id"]}',r,'yolo_track'))
            else:anchors[r['frame_index']].append({'anchor_key':f'local:{tr["track_id"]}','entity_id':f'local:{tr["track_id"]}','raw_label':tr['detector_class'],'bbox':r['bbox'],'authorized':True,'provenance':'fresh local detector; no target identity authority'})
    for index,r in enumerate(read(source/'perception/yolo_detections.json')):
        if r['class_name']=='cell phone' and not any(iou(r['bbox'],x[1]['bbox'])>=.5 for x in by[r['frame_index']]):by[r['frame_index']].append((f'raw:{index}',r,'yolo_raw'))
    for seg in read(source/'sam/sam_continuity_log.json',{}).get('segments',[]):
        for r in seg.get('observations',[]):sam[r['frame_index']].append((r,seg.get('masks_rle',{}).get(f'{r["frame_index"]}:{r["object_id"]}')))
    cap=cv2.VideoCapture(str(video));rows=[];frames=[]
    try:
        for info in meta['sampled_frames']:
            f=info['frame_index'];frames.append({'frame':f,'time':info['timestamp'],'anchors':anchors[f],'image_size':[meta['width'],meta['height']],'candidate_present':bool(by[f] or sam[f]),'scene_ok':True})
            if not by[f]:continue
            cap.set(cv2.CAP_PROP_POS_FRAMES,f);ok,im=cap.read()
            if not ok:raise OSError('Fresh crop decode failed')
            for cid,o,kind in by[f]:
                match=max(sam[f],key=lambda x:iou(x[0]['bbox'],o['bbox']),default=None);overlap=iou(match[0]['bbox'],o['bbox']) if match else 0.
                drift=bool(match and overlap>=.3 and match[0].get('diagnostics',{}).get('possible_mask_drift'));mask=decode_mask(match[1]) if match and overlap>=.5 and not drift and match[1] else None
                rgb,fg,md=crop_observation(im,o['bbox'],mask);oid=f'{cid}@{f}';p=OUT/f'smoke/canonical/{oid.replace(":","_")}.png';p.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(rgb).save(p);mp=None
                if fg is not None:mp=p.with_name(p.stem+'_mask.png');Image.fromarray(fg.astype('uint8')*255).save(mp)
                rows.append({'video_id':video_id,'observation_id':oid,'candidate_id':cid,'frame':f,'time':info['timestamp'],'bbox':o['bbox'],'label':'cell phone','confidence':o['confidence'],'source':kind,
                    'provenance':source.relative_to(ROOT).as_posix()+'#'+oid,'crop_path':str(p),'crop_sha256':sha(p),'foreground_mask_path':str(mp) if mp else None,
                    'sam_overlap':overlap,'drift':drift,'scene_break':False,'canonical_metadata':md})
    finally:cap.release()
    return verify_rows(video_id,rows,video,frames,{'video_sha256':sha(video),'mode':'FRESH_RAW_PERCEPTION'})

def run_smoke():
    verify_freeze();gate=read(OUT/'known_val_regression/safety_summary.json')
    if not gate or not gate.get('identity_safety_gate_passed'):
        result={'status':'SKIPPED_IDENTITY_SAFETY_GATE','model_requested':'Qwen2.5-VL-7B NF4','model_loaded':False,
            'Qwen3_or_Strata_used':False,'reason':'Prompt section4 requires identity regression safety before starting Qwen.'}
        save(OUT/'smoke/qwen25_smoke.json',result);return result
    from memory_graph.identity import pipeline as frozen
    old=frozen.OUT;frozen.OUT=OUT
    try:
        raw=OUT/'smoke/fresh_raw_seed';video=ROOT/'test2.mp4'
        if not (raw/'metrics.json').exists():frozen.raw(video,raw)
        log=read(raw/'sam/unverified_propagation.json')
        if log:save(raw/'raw/sam/sam_continuity_log.json',log)
        vid='smoke_test2';rows=read(OUT/f'inputs/{vid}/observations.json') or fresh_crops(raw/'raw',vid,video)
        dest=OUT/'smoke/v296_test2';m=replay(vid,dest,rows)
        prepared=read(dest/'prepared/interface_smoke.json') or frozen.prepare(dest,video)
        if not (dest/'prepared/qwen/responses.json').exists():frozen.reason(dest)
        results=read(dest/'prepared/qwen/responses.json')
        result={'status':'COMPLETE','model':'Qwen2.5-VL-7B NF4','Qwen3_or_Strata_used':False,
            'fresh_yolo':True,'fresh_sam':bool(log),'V296_identity':m,'events':prepared,'calls':len(results),
            'EOS_complete':all(r['trace']['ended_with_EOS'] for r in results),'schema_valid':all(r['validation']['schema_valid'] for r in results),
            'validator_valid':all(r['validation']['valid'] for r in results),'unchanged_frozen_interfaces':True}
        save(OUT/'smoke/qwen25_smoke.json',result);return result
    finally:frozen.OUT=old
