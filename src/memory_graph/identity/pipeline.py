"""Current IO: pure perception evidence -> guard -> frozen downstream interfaces.

No historical registry, trusted timeline, candidate aliases or bank trust is read.
Replay reuses raw observations, not previous identity conclusions.
"""
from pathlib import Path
from collections import defaultdict
from dataclasses import asdict
import json, time, hashlib
from .contracts import Observation, Policy, iou, digest
from .guard import IdentityGuard

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/identity_rebuild'
def read(path,default=None):
    return json.loads(Path(path).read_text(encoding='utf8')) if Path(path).is_file() else default
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def safe_output(path):
    path=Path(path).resolve()
    if not path.is_relative_to(OUT.resolve()):raise ValueError('Identity outputs must be under outputs/identity_rebuild')
    return path
def write(path,value):
    path=safe_output(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')

class Embedder:
    """Unchanged frozen feature extractor; all newly cached crops stay in this run."""
    def __init__(self,cache):
        import torch
        torch.set_num_threads(4)
        from memory_graph.v24.appearance import MobileNetEmbedder
        self.model=MobileNetEmbedder();self.model.cache_dir=safe_output(cache)
        self.model.cache_dir.mkdir(parents=True,exist_ok=True)
    def vector(self,image,box):
        from memory_graph.v24.appearance import crop_rgb
        vector,_=self.model.embed_crop(crop_rgb(image,box))
        return tuple(float(x) for x in vector)

def _sam_index(log):
    result=defaultdict(list)
    for segment in log.get('segments',[]):
        for obs in segment.get('observations',[]):result[obs['frame_index']].append(obs)
    return result

def replay(source,video,output,policy=None,embedder=None,sam_provider=None):
    import cv2
    source=Path(source).resolve();video=Path(video).resolve();output=safe_output(output)
    if (output/'identity.json').exists():raise FileExistsError('Completed identity run is immutable; select a fresh output')
    start=time.perf_counter();p=policy or Policy();g=IdentityGuard(p)
    paths={'metadata':source/'video_metadata.json','tracks':source/'perception/tracks.json',
           'detections':source/'perception/yolo_detections.json','sam':source/'sam/sam_continuity_log.json'}
    meta=read(paths['metadata']);tracks=read(paths['tracks']);detections=read(paths['detections'])
    if meta is None or tracks is None or detections is None:raise ValueError('Missing raw perception inputs')
    rawby=defaultdict(list);trackby=defaultdict(list);anchors=defaultdict(list)
    for index,d in enumerate(detections):
        if d['class_name']=='cell phone':rawby[d['frame_index']].append((index,d))
    for t in tracks:
        for r in t['observations']:
            if t['detector_class']=='cell phone':trackby[r['frame_index']].append((t['track_id'],r))
            else:anchors[r['frame_index']].append({'anchor_key':'local:'+str(t['track_id']),
                'entity_id':'local:'+str(t['track_id']),'raw_label':t['detector_class'],'bbox':r['bbox'],
                'authorized':True,'provenance':'raw local detector observation; no target identity authority'})
    sam_log=read(paths['sam'],{});sam=_sam_index(sam_log);generated_sam=False
    # Episode boundaries are conservative scene continuity breaks. They provide no identity.
    episode_path=source/'perception/episodes.json'
    if not episode_path.exists():episode_path=source/'upstream_v21/event_analysis/episodes.json'
    episodes=read(episode_path,[]);break_frames={e['start_frame'] for e in episodes[1:]}
    if embedder is None:embedder=Embedder(output/'appearance_cache')
    cap=cv2.VideoCapture(str(video));input_rows=[];embedding_errors=[];latencies=[]
    try:
        for info in meta['sampled_frames']:
            f=info['frame_index'];ts=info['timestamp'];frame_start=time.perf_counter()
            rows=[];image=None
            if trackby[f] or rawby[f]:
                cap.set(cv2.CAP_PROP_POS_FRAMES,f);ok,image=cap.read()
                if not ok:raise OSError(f'Failed decoding frame {f}')
            # Retain local tracker evidence; raw detections not represented by a track remain candidates.
            evidence=[(f'track:{tid}',r,'yolo_track') for tid,r in trackby[f]]
            for index,d in rawby[f]:
                if not any(iou(d['bbox'],r['bbox'])>=.5 for _,r in trackby[f]):
                    evidence.append((f'raw:{index}',d,'yolo_raw'))
            for cid,r,kind in evidence:
                match=max(sam[f],key=lambda s:iou(s['bbox'],r['bbox']),default=None)
                overlap=iou(match['bbox'],r['bbox']) if match else 0.
                drift=bool(match and overlap>=p.support_iou and match.get('diagnostics',{}).get('possible_mask_drift'))
                try:vector=embedder.vector(image,r['bbox'])
                except ValueError as exc:
                    vector=();embedding_errors.append({'frame':f,'candidate':cid,'error':str(exc)})
                rows.append(Observation(f'{cid}@{f}',cid,f,ts,tuple(r['bbox']),'cell phone',r['confidence'],
                    f'{paths["tracks"] if kind=="yolo_track" else paths["detections"]}#{cid}:{f}',
                    vector=vector,sam_overlap=overlap,drift=drift,scene_break=f in break_frames,source=kind))
            g.process(ts,rows)
            if sam_provider and not generated_sam and g.restart_tickets():
                ticket=g.restart_tickets()[0]
                bound=g.final_ledger()[-1]['observation']
                log=g.restart_target_sam(ticket,bound['observation_id'],sam_provider)
                write(output/'sam/unverified_propagation.json',log);sam_log=log;sam=_sam_index(log);generated_sam=True
            input_rows.append({'frame':f,'time':ts,'image_size':[meta['width'],meta['height']],
                'anchors':anchors[f],'candidate_present':bool(rows or sam[f]),'scene_ok':True})
            latencies.append(time.perf_counter()-frame_start)
    finally:cap.release()
    snap=g.snapshot();authorized={r['observation']['frame']:r for r in g.final_ledger()}
    mask_lookup={}
    for segment in sam_log.get('segments',[]):
        for row in segment.get('observations',[]):
            mask_lookup[(row['frame_index'],row['object_id'])]=segment.get('masks_rle',{}).get(f'{row["frame_index"]}:{row["object_id"]}')
    final=[]
    for row in input_rows:
        auth=authorized.get(row['frame']);obs=auth['observation'] if auth else None
        mask_ref=None
        if obs:
            match=max(sam[row['frame']],key=lambda s:iou(s['bbox'],obs['bbox']),default=None)
            if match and iou(match['bbox'],obs['bbox'])>=p.support_iou and not match.get('diagnostics',{}).get('possible_mask_drift'):
                rle=mask_lookup.get((row['frame'],match['object_id']))
                if rle:
                    from memory_graph.v22.sam_tracking import decode_mask
                    from PIL import Image
                    mask_path=output/f'masks/f{row["frame"]:06d}.png';mask_path.parent.mkdir(parents=True,exist_ok=True)
                    Image.fromarray(decode_mask(rle).astype('uint8')*255).save(mask_path)
                    mask_ref=mask_path.relative_to(ROOT).as_posix()
        final.append({**row,'identity_authorized':auth is not None,'target_bbox':obs['bbox'] if obs else None,
            'chain_id':f'epoch:{auth["epoch_id"]}' if auth else None,'mask_reference':mask_ref,
            'upstream_identity_state':'AUTHORIZED' if auth else 'UNRESOLVED',
            'source':'final_revocation_filtered_ledger',
            'target_authorization_provenance':[auth['authorization_id'],auth['alias_id']] if auth else []})
    metrics={'initial_binding':bool(snap['aliases']),'epochs':len(snap['epochs']),
        'epoch_breaks':sum(e['end_time'] is not None for e in snap['epochs']),
        'authorized_observations':len(authorized),'sampled_frames':len(final),
        'unresolved_frames':sum(not r['identity_authorized'] for r in final),
        'unresolved_candidate_frames':sum(r['candidate_present'] and not r['identity_authorized'] for r in final),
        'confirmed_recoveries':sum(e['start_reason']=='MULTI_EVIDENCE_REIDENTIFICATION' for e in snap['epochs']),
        'revoked_aliases':sum(a['status']=='REVOKED' for a in snap['aliases']),
        'decision_counts':{s:sum(d['decision']==s for d in snap['decisions']) for s in ['PROVISIONAL','AMBIGUOUS','CONFIRMED_MATCH','REJECTED','REVOKED']},
        'core_entries':sum(b['active'] for b in snap['banks']['core']),
        'quarantined_entries':sum(b['active'] for b in snap['banks']['quarantine']),
        'negative_entries':sum(b['active'] for b in snap['banks']['negative']),
        'rejected_bank_updates':snap['rejected_bank_updates'],
        'unauthorized_matched':sum(not any(a['authorization_id']==r['authorization_id'] and 'AUTHORIZE_OBSERVATION' in a['capabilities'] for a in snap['authorizations']) for r in g.final_ledger()),
        'embedding_errors':embedding_errors,'wall_seconds':time.perf_counter()-start,
        'identity_and_embedding_frame_seconds_mean':sum(latencies)/len(latencies),
        'policy_sha256':digest(asdict(p)),'mode':'RAW_PERCEPTION' if sam_provider else 'RAW_EVIDENCE_REPLAY',
        'fresh_yolo':bool(sam_provider),'fresh_sam':generated_sam,'fresh_appearance':True,
        'source_hashes':{k:sha(v) for k,v in paths.items() if v.is_file()},'video_sha256':sha(video)}
    write(output/'identity.json',snap);write(output/'authorized_rows.json',final);write(output/'metrics.json',metrics)
    return metrics

def raw(video,output):
    """Pure perception + capability-gated SAM. Never invokes legacy identity fusion."""
    import sys
    output=safe_output(output);video=Path(video).resolve()
    if output.exists():raise FileExistsError('Fresh raw run requires a new output directory')
    perception=output/'raw/perception';perception.mkdir(parents=True)
    from memory_graph.config_v2 import load_v2_config
    from memory_graph.perception.track_manager import collect_tracks
    config=load_v2_config(ROOT/'configs/v2.yaml')
    config.perception.detector.model=str(ROOT/'.models/yolo11s.pt')
    collect_tracks(video,perception,config)
    meta=read(perception/'video_metadata.json')
    write(output/'raw/video_metadata.json',meta)
    write(perception/'tracks.json',read(perception/'track_timelines.json'))
    write(perception/'yolo_detections.json',read(perception/'detections.json'))
    def sam_provider(context):
        import torch
        from memory_graph.v22 import sam_tracking as frozen
        for path in (frozen.SAM_DEPS,frozen.SAM_SOURCE):
            if str(path) not in sys.path:sys.path.insert(0,str(path))
        from sam2.build_sam import build_sam2_video_predictor
        model=build_sam2_video_predictor(frozen.CONFIG,str(frozen.CHECKPOINT),device='cuda',apply_postprocessing=False)
        obs=context['observation'];seed={'frame_index':obs['frame'],'timestamp':obs['time'],
            'bbox':obs['bbox'],'confidence':obs['confidence'],'class_name':'cell phone'}
        inputs={'video_metadata.json':meta,'detections.json':read(perception/'detections.json')}
        old_choose,old_extract=frozen.choose_seeds,frozen.extract_frames
        frozen.choose_seeds=lambda *_:[('unverified_target_seed',seed)]
        frozen.extract_frames=lambda _,frames,folder:old_extract(video,frames,folder)
        sam_output=output/'sam';sam_output.mkdir(exist_ok=True)
        try:
            with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
                result=frozen.run_segment(video.stem,'guard_seed',obs['frame'],meta['sampled_frames'][-1]['frame_index'],inputs,model,sam_output)
        finally:frozen.choose_seeds,frozen.extract_frames=old_choose,old_extract
        return {'segments':[result],'seed_authorization':context,'identity_status':'UNVERIFIED; guard rechecks each frame'}
    return replay(output/'raw',video,output, sam_provider=sam_provider)

def prepare(output,video):
    """Minimal ledger adapter; frozen builder, selection, renderer and prompt are reused verbatim."""
    import cv2
    from memory_graph.events.window_builder import WindowConfig,target_timeline,select_events,select_context,dense_frames
    from memory_graph.reasoning.pipeline import render_frame,contact_sheet
    from memory_graph.reasoning.contract import prompt
    output=safe_output(output);dest=output/'prepared';cfg=WindowConfig()
    if (dest/'qwen/requests.json').exists():raise FileExistsError('Prepared evidence already frozen')
    rows=target_timeline(read(output/'authorized_rows.json'),cfg);pool,selected,queues=select_events(rows,cfg)
    cap=cv2.VideoCapture(str(video));events=[];requests=[]
    try:
        for i,e in enumerate(selected):
            contexts=select_context(rows,e,cfg)
            event={**e,'pack_id':f'identity_W{i+1:02d}','video_id':Path(video).stem,'target_id':'phone_01',
                'representation':'DENSE_ORDERED_EVENT_FRAMES','contexts':contexts,'markers':[c['marker'] for c in contexts],
                'actor_markers':[c['marker'] for c in contexts if c['role']=='INTERACTION_ACTOR_CANDIDATE'],
                'location_markers':[c['marker'] for c in contexts if c['role']=='LOCATION_ANCHOR_CANDIDATE'],
                'physical_reasoning_eligible':e['category']=='PHYSICAL_INTERACTION_EVENT' and e['completeness']=='COMPLETE_EVENT_WINDOW','frames':[]}
            paths=[]
            if e['category']=='PHYSICAL_INTERACTION_EVENT':
                for row in dense_frames(rows,e,cfg):
                    row={**row,'phase':'BEFORE' if row['time']<e['transition_time'] else 'DURING' if row['time']<=e['transition_time']+.6 else 'AFTER'}
                    cap.set(cv2.CAP_PROP_POS_FRAMES,row['frame']);ok,img=cap.read()
                    if not ok:raise OSError('Cannot render evidence')
                    path=dest/f'frames/{event["pack_id"]}/f{row["frame"]:06d}.png';render_frame(img,row,event,contexts,path);paths.append(path)
                    event['frames'].append({'frame':row['frame'],'image_path':str(path),'sha256':sha(path),'phase':row['phase'],
                        'time':row['time'],'target_marked':row['identity_authorized'],'target_bbox':row['target_bbox'],
                        'identity_authorization_provenance':row['target_authorization_provenance']})
                contact_sheet(paths,dest/f'{event["pack_id"]}.png',event)
            events.append(event)
            if event['physical_reasoning_eligible']:
                requests.append({'pack_id':event['pack_id'],'images':[str(x) for x in paths],
                    'image_sha256':[sha(x) for x in paths],'prompt':prompt(event),'max_new_tokens':1400})
    finally:cap.release()
    write(dest/'events.json',events);write(dest/'qwen/requests.json',requests)
    result={'event_count':len(events),'qwen_eligible':len(requests),'queues':queues,'config':cfg.to_dict(),
        'authorized_source':'final_revocation_filtered_ledger','frozen_downstream_changed':False}
    write(dest/'interface_smoke.json',result);return result

def reason(output):
    """Run the unchanged dense-image backend/validator on current authorized evidence."""
    from memory_graph.reasoning import model
    from memory_graph.reasoning.contract import parse_json,prompt
    from memory_graph.reasoning.validator import DirectReasoningValidator
    output=safe_output(output);dest=output/'prepared';requests=read(dest/'qwen/requests.json')
    if (dest/'qwen/responses.json').exists():raise FileExistsError('Inference already completed')
    if not requests:write(dest/'qwen/responses.json',[]);return {'calls':0,'reason':'NO_ELIGIBLE_EVENT'}
    events={e['pack_id']:e for e in read(dest/'events.json')};old=model.OUT;model.OUT=dest
    try:
        backend=model.Backend();results=[]
        for r in requests:
            if prompt(events[r['pack_id']])!=r['prompt'] or any(sha(p)!=h for p,h in zip(r['images'],r['image_sha256'])):raise ValueError('Evidence drift')
            raw_text=backend(r['images'],r['prompt'],r['max_new_tokens']);answer=parse_json(raw_text)
            result=DirectReasoningValidator().validate(events[r['pack_id']],answer)
            if not backend.last_trace.get('ended_with_EOS'):
                result['valid']=False;result['errors'].append('INCOMPLETE_GENERATION');result['status']='INVALID_MODEL_REASONING_OUTPUT'
            results.append({'pack_id':r['pack_id'],'raw_output':raw_text,'answer':answer,'validation':result,'trace':backend.last_trace})
        write(dest/'qwen/responses.json',results)
        return {'calls':len(results),'identity_writes':0,'physical_policy_changed':False}
    finally:model.OUT=old
