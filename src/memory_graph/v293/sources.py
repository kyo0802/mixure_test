"""Frozen upstream reads, bounded dense repair and observation-only row adaptation."""
from copy import deepcopy
from pathlib import Path
import gc
import re
import cv2
import numpy as np
from .audit import BASE, OUT, ROOT, VIDEOS, read, write
from .evidence import authorize_observation, bounded_window
from memory_graph.v292.validator import sha256

MAX_EXPANSION_SECONDS=1.5
PROTECTED_FILES=['src/memory_graph/v26/authorization.py','src/memory_graph/v26/pipeline.py',
    'src/memory_graph/v29/physical_gate.py','src/memory_graph/v28/local_subgraph.py',
    'src/memory_graph/v28/search_planner.py','src/memory_graph/v28/memory.py',
    'src/memory_graph/v29/dense_reinspection.py','configs/v292_canonical.yaml']

def verify_baseline_contract(full_hashes=True):
    config=read(BASE/'canonical_config.json')
    if full_hashes:
        from memory_graph.v292.finalize import verify_frozen_predictions
        verified=verify_frozen_predictions(BASE)
        if not verified['valid']: raise RuntimeError(verified['errors'])
    for path,expected in config['source_code_sha256'].items():
        if sha256(ROOT/path)!=expected: raise RuntimeError(f'Frozen source changed: {path}')
    for model in config['model_identifiers'].values():
        if sha256(ROOT/model['path'])!=model['sha256']: raise RuntimeError('Model hash changed')
    for v in VIDEOS:
        if sha256(ROOT/f'{v}.mp4')!=read(BASE/v/'run_manifest.json')['video_sha256']:
            raise RuntimeError(f'Raw development video changed: {v}')
    frozen=read(BASE/'artifact_manifest.json')['videos']
    identity_hashes={v:{p:sha256(BASE/v/p) for p in frozen[v] if p.startswith(('identity/','memory/','search/'))
                       or p in ('identity_timeline.json','entity_registry.json','sam_reinit_log.json')} for v in VIDEOS}
    unchanged=all(digest==frozen[v][p] for v,files in identity_hashes.items() for p,digest in files.items())
    t8=read(BASE/'test8/identity/identity_timeline.json')['phone_timeline']
    t9=read(BASE/'test9/identity/identity_timeline.json')['phone_timeline']
    auths=read(BASE/'test8/identity/identity_authorizations.json')
    unauthorized=0
    for v in VIDEOS:
        auth={a['authorization_id']:a for a in read(BASE/v/'identity/identity_authorizations.json')}
        for row in read(BASE/v/'identity/identity_timeline.json')['phone_timeline']:
            if row['state']=='MATCHED' and (row.get('authorization_id') not in auth or
                auth[row['authorization_id']]['source_guard_decision']!='V2.6_IDENTITY_GUARD'): unauthorized+=1
    mapping=read(BASE/'test2/identity/entity_registry.json')['track_to_entity']
    return {'baseline_hash_validation_requested':full_hashes,'identity_threshold':config['identity']['appearance_threshold'],
        'margin':config['identity']['uniqueness_margin'],'protected_sources':{p:sha256(ROOT/p) for p in PROTECTED_FILES},
        'identity_and_memory_hashes':identity_hashes,'identity_and_memory_unchanged':unchanged,
        'test7_identity_unchanged':all(d==frozen['test7'][p] for p,d in identity_hashes['test7'].items()),
        'test8_closed_loop':bool(auths and any(r['frame_index']>auths[0]['frame'] and r['state']=='VISIBLE' for r in t8)),
        'test8_confirmation_frames':[r['frame_index'] for r in t8 if r['state']=='MATCHED'],
        'test9_unresolved':not any(r['state']=='MATCHED' for r in t9),
        'unauthorized_matched':unauthorized,'test2_fusion_preserved':mapping.get('22')==mapping.get('43')=='phone_01',
        'baseline_config_sha256':config['canonical_config_sha256']}

def trusted_seeds(video,fps):
    refs=read(BASE/video/'segmentation/mask_references.json',[])
    result=[];last={};segments={}
    for ref in sorted(refs,key=lambda x:x['frame']):
        if not ref.get('trusted') or ref.get('object_id')!='phone_01' or ref.get('source_kind') not in {'target_full','reinitialized'}: continue
        path=BASE/video/ref['artifact_path']
        if not path.is_file() or sha256(path)!=ref['artifact_sha256']: raise RuntimeError('Trusted source mask missing or changed')
        stream=(ref['source_kind'],ref.get('authorization_id'))
        if stream not in last or ref['frame']-last[stream]>round(.4*fps): segments[stream]=segments.get(stream,0)+1
        last[stream]=ref['frame']
        result.append({**deepcopy(ref),'mask_bbox':ref['bbox'],'mask_reference':str(path),
            'chain_id':f'{video}:{stream[0]}:{stream[1]}:segment{segments[stream]}'})
    return result

def _scene_rows(video,rows):
    cap=cv2.VideoCapture(str(ROOT/f'{video}.mp4')); previous=None;previous_hist=None; segment=0; result={}
    try:
        for row in rows:
            cap.set(cv2.CAP_PROP_POS_FRAMES,row['frame']);ok,image=cap.read()
            if not ok: result[row['frame']]={'scene_ok':False,'view_ok':False,'scene_segment':segment};continue
            gray=cv2.cvtColor(cv2.resize(image,(64,36)),cv2.COLOR_BGR2GRAY)
            hist=cv2.calcHist([gray],[0],None,[32],[0,256]);cv2.normalize(hist,hist)
            diff=float(np.abs(gray.astype(float)-previous).mean()/255) if previous is not None else 0.
            corr=float(cv2.compareHist(hist,previous_hist,cv2.HISTCMP_CORREL)) if previous_hist is not None else 1.
            cut=diff>.35 and corr<.2
            if cut:segment+=1
            result[row['frame']]={'scene_ok':not cut,'view_ok':bool(gray.std()>1),'scene_segment':segment,
                'scene_diagnostics':{'normalized_luma_difference':diff,'histogram_correlation':corr,
                    'policy':'cut if luma difference >0.35 AND histogram correlation <0.2; fixed diagnostic, not identity threshold'},
                'image_size':[image.shape[1],image.shape[0]]}
            previous=gray.astype(float);previous_hist=hist
    finally:cap.release()
    return result

class EvidenceSources:
    def __init__(self): self.runner=None

    def close(self):
        self.runner=None;gc.collect()
        import torch
        if torch.cuda.is_available():torch.cuda.empty_cache()

    def prepare(self,video,event):
        from memory_graph.v29 import dense_reinspection as module
        from memory_graph.v291.anchors import recover_anchors
        from memory_graph.v22.sam_tracking import decode_mask
        original=read(BASE/video/'events/dense'/event['event_id']/'dense_observations.json')
        original_masks=read(BASE/video/'events/dense'/event['event_id']/'target_masks.json',{})
        metadata=read(BASE/video/'upstream_v21/event_analysis/video_metadata.json')
        fps=float(metadata['fps']);size=(int(metadata['width']),int(metadata['height']))
        last=max(x['frame_index'] for x in metadata['sampled_frames'])
        seeds=trusted_seeds(video,fps)
        low,high=bounded_window(event,fps,last,MAX_EXPANSION_SECONDS)
        eligible_seeds=[s for s in seeds if low<=s['frame']<=event['end_frame']]
        folder=OUT/video/'events'/event['event_id']
        requested=deepcopy(event);log={'event_id':event['event_id'],'recomputed':False,
            'baseline_config_sha256':read(BASE/'canonical_config.json')['canonical_config_sha256'],
            'raw_sha256':read(BASE/video/'run_manifest.json')['video_sha256'],
            'model_identifiers':read(BASE/'canonical_config.json')['model_identifiers'],
            'dense_source_sha256':sha256(ROOT/'src/memory_graph/v29/dense_reinspection.py'),
            'canonical_dense_settings':{'confidence':.15,'image_size':960,'max_fps':15,'sam_postprocessing':False},
            'max_expansion_seconds_each_side':MAX_EXPANSION_SECONDS,'original_interval':[event['start_frame'],event['end_frame']]}
        if eligible_seeds and (not original_masks or not original.get('seed')):
            earlier=[s for s in eligible_seeds if s['frame']<=event['start_frame']]
            if earlier: requested['start_frame']=max(earlier,key=lambda s:s['frame'])['frame']
            # Only extend AFTER when a frozen request actually lacks later queried-anchor coverage.
            reqs=[q for q in read(BASE/video/'vlm/pair_requests.json') if q['event_id']==event['event_id']]
            after_missing=any(not any(r['frame']>event['peak_frame']+3 and any(a['anchor_key']==q['anchor_key'] for a in r['anchors']) for r in original['rows']) for q in reqs)
            if after_missing:requested['end_frame']=high
            selected=[s for s in seeds if requested['start_frame']<=s['frame']<=requested['end_frame']]
            seed=selected[0]
            # The inference seed must be on its exact source frame, never the nearest earlier sample.
            old_numbers=module.frame_numbers
            def numbers(e,desired,native):
                return sorted(set(old_numbers(e,desired,native)+[seed['frame'],e['end_frame']]))
            if self.runner is None:self.runner=module.DenseRunner()
            module.frame_numbers=numbers
            try:self.runner.run(video,requested,selected,fps,folder/'raw_dense')
            finally:module.frame_numbers=old_numbers
            dense=read(folder/'raw_dense/dense_observations.json');masks=read(folder/'raw_dense/target_masks.json',{})
            log.update(recomputed=True,reason='Missing/corrupted dense RLE or omitted authorized restart seed; bounded window has frozen trusted seed',
                actual_interval=[dense['sampling']['start_frame'],dense['sampling']['end_frame']],seed_frame=seed['frame'],seed_chain_id=seed['chain_id'])
            recovery=recover_anchors(requested,dense,frame_size=size)
            anchors=[];mapped={}
            for a in recovery['anchors']:
                key=f"{video}::{event['event_id']}::{a['anchor_id']}"
                anchor={**a,'anchor_key':key,'semantic_uncertainty':'Detector class retained; not verified physical identity'}
                anchors.append(anchor)
                for box in a['boxes']:
                    row=next(r for r in dense['rows'] if r['frame']==box['frame'])
                    det=next((d for d in row['anchors'] if d['bbox']==box['bbox']),{})
                    mapped.setdefault(box['frame'],[]).append({'anchor_key':key,'entity_id':key,'bbox':box['bbox'],
                        'raw_label':a['raw_label'],'label':a['raw_label'],'confidence':det.get('confidence'),
                        'source':a['source'],'authorized':a['trusted_for_physical_reasoning'],
                        'bbox_reference':str(folder.relative_to(ROOT))+f"/raw_dense/dense_observations.json#frame:{box['frame']}",
                        'semantic_uncertainty':anchor['semantic_uncertainty']})
            for r in dense['rows']:r['anchors']=mapped.get(r['frame'],[])
        else:
            dense=deepcopy(original);masks=deepcopy(original_masks);seed=None
            anchors=read(BASE/video/'events/dense'/event['event_id']/'anchor_recovery.json')['anchors']
            lookup={a['anchor_key']:a for a in anchors}
            for r in dense['rows']:
                for a in r['anchors']:
                    source=lookup.get(a['anchor_key'],{})
                    a.update(authorized=bool(source.get('trusted_for_physical_reasoning')),
                        raw_label=source.get('raw_label',a['label']),confidence=None,
                        source=source.get('source'),semantic_uncertainty='Frozen V292 omitted detection confidence; not reconstructed')
            log.update(reason='Reused frozen dense geometry; no valid seed within global expansion budget' if not eligible_seeds else 'Frozen dense evidence reusable',
                actual_interval=[dense['sampling']['start_frame'],dense['sampling']['end_frame']])
        scenes=_scene_rows(video,dense['rows']); adapted=[];active=True;started=False
        timeline=read(BASE/video/'identity/identity_timeline.json')['phone_timeline']
        by_frame={r['frame_index']:r for r in timeline}
        seed_scene=scenes.get(seed['frame'],{}).get('scene_segment') if seed else None
        for raw in dense['rows']:
            row=deepcopy(raw);f=row['frame'];sam=row.get('sam_phone');scene=scenes[f]
            prior=max((s for s in seeds if s['frame']<=f and seed and s['chain_id']==seed['chain_id']),key=lambda s:s['frame'],default=None)
            conflict=by_frame.get(f,{}).get('state') in {'AMBIGUOUS','PROVISIONAL','REJECTED'}
            if started and (sam is None or sam.get('diagnostics',{}).get('possible_mask_drift') or conflict):active=False
            if sam:started=True
            auth=authorize_observation(frame=f,sam=sam,prior=prior,fps=fps,chain_active=active,
                conflicting=conflict,scene_ok=scene['scene_ok'] and scene['scene_segment']==seed_scene,
                mask_available=str(f) in masks)
            okay=auth['geometry_usable'];mask_path=None
            if okay:
                target=folder/'masks'/f'f{f:06d}.png';target.parent.mkdir(parents=True,exist_ok=True)
                if not cv2.imwrite(str(target),decode_mask(masks[str(f)]).astype('uint8')*255):raise OSError(target)
                mask_path=str(target.relative_to(ROOT))
            row.update(**scene,target_authorization=auth,target_bbox=sam['bbox'] if okay else None,
                target_visible_state='OBSERVED' if okay else 'UNTRUSTED_OBSERVATION' if sam or row.get('yolo_phone_detections') else 'NOT_OBSERVED',
                mask_area=sam['area'] if okay else None,mask_reference=mask_path, sam_present=bool(sam),
                phone_candidates=row.get('yolo_phone_detections',[]),chain_id=seed['chain_id'] if okay else None)
            # Existing field is retained as input provenance; no identity state is edited or projected.
            row['baseline_dense_identity_authorized']=row.pop('identity_authorized',False)
            for a in row['anchors']:
                x1,y1,x2,y2=a['bbox'];w,h=size
                a['authorized']=bool(a.get('authorized') and 0<=x1<x2<=w and 0<=y1<y2<=h)
            adapted.append(row)
        write(folder/'observation_rows.json',adapted);write(folder/'anchors.json',anchors)
        write(folder/'selective_recomputation.json',log)
        return requested,adapted,anchors,masks,log,size,fps
