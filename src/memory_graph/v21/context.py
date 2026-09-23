"""Generic missed-object event context. Historical crops are never current detections."""
import hashlib
import json
from pathlib import Path
import cv2
from PIL import Image
from ..memory.memory_store import save_json
from .artifacts import read
from .quality import crop_frame
from .contracts import ContextResult


def build_context(event_path, tracks, mapping, source, config):
    frames=read(event_path/'keyframes.json')
    by_frame={}
    for track in tracks:
        for obs in track.observations:
            by_frame.setdefault(obs.frame_index,{})[track.track_id]=obs
    supplied=frames[0]['supplied_track_ids']
    visible={mapping[tid] for f in frames for tid in f['visible_track_ids'] if tid in mapping and tid in supplied}
    before,during,after=frames
    candidates=[]
    for t in tracks:
        if t.track_id not in mapping: continue
        prior=[o for o in t.observations if o.timestamp<=during['timestamp']]
        if not prior: continue
        last=prior[-1]
        missing=any(t.track_id not in by_frame.get(f['frame_index'],{}) for f in [during,after])
        if missing and 0<=during['timestamp']-last.timestamp<=config.missed_context_seconds:
            required=t.track_id in supplied and t.track_id in by_frame.get(before['frame_index'],{})
            candidates.append((required,last,t))
    candidates.sort(key=lambda item:(item[0],item[1].timestamp,item[1].confidence),reverse=True)
    missing=[]; images=[]; cap=cv2.VideoCapture(str(source)); seen=set(); supplemental=0
    for required,last,t in candidates:
        entity=mapping[t.track_id]
        if entity in seen: continue
        # A before-visible supplied identity must survive a later detector miss.
        # The extra historical-context budget must never evict this required evidence.
        if not required and supplemental>=config.max_missing_context: continue
        if not required: supplemental+=1
        seen.add(entity)
        cap.set(cv2.CAP_PROP_POS_FRAMES,last.frame_index); ok,image=cap.read()
        if not ok: raise RuntimeError('Missing context source frame')
        crop=crop_frame(image,last.bbox)
        # Historical references identify appearance, not fine scene geometry.
        # Bound their tokens so preserving all required identities fits a 16 GiB GPU.
        if max(crop.shape[:2])>384:
            scale=384/max(crop.shape[:2])
            crop=cv2.resize(crop,(max(1,round(crop.shape[1]*scale)),max(1,round(crop.shape[0]*scale))))
        path=event_path/f'last_confirmed_{entity}.jpg'
        cv2.imwrite(str(path),crop)
        images.append(path)
        missing.append({'entity_id':entity,'local_track_id':t.track_id,'last_confirmed_seen':last.timestamp,
            'last_confirmed_frame':last.frame_index,'last_confirmed_bbox':last.bbox,'historical_crop':path.name,
            'historical_crop_max_edge':384,
            'required_before_visible_context':required,
            'phase_visibility':{f['phase']:'VISIBLE' if t.track_id in by_frame.get(f['frame_index'],{}) else 'UNOBSERVED' for f in frames},
            'current_bbox_when_unobserved':None})
    cap.release()
    phase_context=[]
    for f in frames:
        phase_context.append({'phase':f['phase'],'timestamp':f['timestamp'],
            'visible_entity_ids':sorted({mapping[tid] for tid in f['visible_track_ids'] if tid in mapping and tid in supplied}),
            'drawn_track_to_entity':{str(tid):mapping[tid] for tid in f['visible_track_ids'] if tid in mapping and tid in supplied}})
    allowed=sorted(visible|{m['entity_id'] for m in missing})
    return {'event_id':event_path.name,'frames':phase_context,'historical_references':missing,'allowed_entity_ids':allowed},images


def analyze_context(backend,event_path,context,historical_images,cache):
    prompt=('Analyze the three chronological scene images before/during/after. Drawn numeric IDs map to persistent hypotheses in metadata. '
        'Remaining images are LAST CONFIRMED historical crops, NOT current locations. A detector miss is not disappearance, '
        'occlusion, motion, or evidence of placement. Never invent a bbox or identity merge. '
        'Report only visually supported human-object or physical relations among allowed entity IDs. '
        'Use NONE when none are visible, UNCERTAIN when evidence is incomplete, SUPPORTED only with clear visual evidence. '
        'Historical crops identify appearance only. Do not infer a hidden destination. '
        'Return a single JSON object matching this schema, without markdown.\n'+json.dumps(ContextResult.model_json_schema())+
        '\nMetadata:\n'+json.dumps(context))
    paths=[event_path/f'{p}.jpg' for p in ['before','during','after']]+historical_images
    digest=hashlib.sha256(json.dumps({'prompt':prompt,'backend':backend.identity},sort_keys=True).encode())
    for p in paths: digest.update(p.read_bytes())
    cache=Path(cache); cache.mkdir(exist_ok=True)
    file=cache/f'{digest.hexdigest()}.json'
    hit=file.exists()
    if hit: record=read(file)
    else:
        raw=backend._generate([Image.open(p).convert('RGB') for p in paths],prompt,1800)
        record={'prompt':prompt,'response':raw,'backend':backend.identity,
                'images':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
        save_json(file,record)
    record={**record,'cache_hit':hit}
    result=None
    try:
        raw=record['response'].strip()
        if raw.startswith('```json') and raw.endswith('```'): raw=raw[7:-3].strip()
        result=ContextResult.model_validate_json(raw)
        if result.event_id!=context['event_id']: raise ValueError('Wrong event ID')
        for claim in result.claims:
            if claim.subject_entity_id==claim.object_entity_id or not {claim.subject_entity_id,claim.object_entity_id}<=set(context['allowed_entity_ids']):
                raise ValueError('Invented or self-related entity ID')
        record['validated']=result.model_dump()
    except (ValueError,TypeError) as error:
        record['error']=str(error); result=None
    save_json(event_path/'persistent_context_input.json',context)
    save_json(event_path/'persistent_context_vlm.json',record)
    return result,hit
