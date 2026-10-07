"""Same frozen timeline conversion and dense image preparation, with fresh sources."""
import time
from bisect import bisect_right
from collections import Counter
from .common import ROOT,read,write,sha as sha256,source_hashes
from memory_graph.reasoning.common import canonical_hash
from memory_graph.reasoning.pipeline import render_frame,contact_sheet,freeze_files
from memory_graph.reasoning.contract import prompt
def authorized_rows(video,runroot):
    folder=runroot/video;meta=read(folder/'video_metadata.json');fps=meta['fps'];size=[meta['width'],meta['height']]
    identity=read(folder/'identity/identity_timeline.json')['phone_timeline'];iby={r['frame_index']:r for r in identity}
    confirmed=sorted(a['frame'] for a in read(folder/'identity/identity_authorizations.json') if a['decision']=='CONFIRMED_MATCH')
    def chain(f):return f'{video}:guard-confirmed:{confirmed[bisect_right(confirmed,f)-1]}' if bisect_right(confirmed,f) else f'{video}:target-binding'
    observations=read(folder/'memory/observations.json');oby={}
    for obs in observations:
        if obs['status'] in {'TRUSTED','CONFIRMED_MATCH'}:oby.setdefault(obs['frame'],[]).append(obs)
    refs={}
    for ref in read(folder/'segmentation/mask_references.json'):
        if ref['trusted'] and ref['object_id']=='phone_01':refs[ref['frame']]=ref
    rows={}
    for info in meta['sampled_frames']:
        f=info['frame_index'];state=iby.get(f,{});valid=state.get('state') in {'VISIBLE','MATCHED','IDENTITY_CONFIRMED'}
        obs=oby.get(f,[]);targets=[o for o in obs if o['entity_id']=='phone_01'];ref=refs.get(f)
        target=targets[0]['bbox'] if valid and targets else None
        mask=None
        if valid and ref:
            target=ref['bbox'];mask=str((folder/ref['artifact_path']).relative_to(ROOT))
        anchors=[{'anchor_key':video+'::'+o['entity_id'],'entity_id':o['entity_id'],'raw_label':o['raw_detector_label'],'bbox':o['bbox'],
            'provenance':o['provenance'],'authorized':True} for o in obs if o['entity_id']!='phone_01']
        rows[f]={'frame':f,'time':f/fps,'image_size':size,'target_bbox':target,'identity_authorized':bool(target),
            'upstream_identity_state':state.get('state'),'chain_id':chain(f) if target else None,'mask_reference':mask,
            'anchors':anchors,'candidate_present':False,'scene_ok':True,'source':str(folder/'memory/observations.json'),
            'target_authorization_provenance':[o['observation_id'] for o in targets] if target else []}
    dense_sources=[]
    for item in read(runroot/'recovered'/video/'prepared_events.json'):
        event_id=item['event']['event_id'];dense_sources.append(event_id)
        for raw in item['rows']:
            f=raw['frame'];authorized=raw['target_authorization']['geometry_usable']
            if f in rows and rows[f]['identity_authorized']:continue
            anchors=[]
            for a in raw.get('anchors',[]):
                if not a.get('authorized'):continue
                tail=a['anchor_key'].split('::')[-1]
                key=video+'::'+tail if tail.startswith('entity_') else video+'::'+event_id+'::'+tail
                anchors.append({**a,'anchor_key':key})
            rows[f]={'frame':f,'time':f/fps,'image_size':size,'target_bbox':raw.get('target_bbox') if authorized else None,
                'identity_authorized':authorized,'upstream_identity_state':raw.get('phone_01_state'),
                'chain_id':chain(f) if authorized else None,'mask_reference':raw.get('mask_reference') if authorized else None,
                'anchors':anchors,'candidate_present':bool(raw.get('phone_candidates') or raw.get('sam_present')),
                'scene_ok':raw.get('scene_ok',True),'source':str(runroot/'recovered'/video/'prepared_events.json')+f'#{event_id}:{f}',
                'target_authorization_provenance':raw['target_authorization']}
    return sorted(rows.values(),key=lambda r:r['frame']),{'video_id':video,'fps':fps,'image_size':size,
        'source_manifests':[str(folder/'run_manifest.json'),str(runroot/'recovered'/video/'prepared_events.json')],
        'source_sha256':[sha256(folder/'memory/observations.json'),sha256(runroot/'recovered'/video/'prepared_events.json')],
        'dense_events_used':dense_sources,'fresh_YOLO_SAM_calls':True,'identity_logic_changed':False}

def prepare(video,runroot):
    OUT=runroot/"prepared"
    from memory_graph.events.window_builder import WindowConfig,target_timeline,select_events,select_context,dense_frames
    import cv2
    if (OUT/'event_windows/builder_freeze.json').exists():raise RuntimeError('Builder already frozen; no tuning/reselection')
    cfg=WindowConfig();write(OUT/'event_windows/config.json',{'initial_global_config':cfg.to_dict(),'general_corrections':0,'representation':'DENSE_ORDERED_EVENT_FRAMES'})
    meta=read(runroot/video/'video_metadata.json');dev=[{'video_id':video,'path':str(ROOT/'val_set'/f'{video}.mp4'),'fps':meta['fps']}];events=[];diagnostics=[];candidates=[];started=time.monotonic()
    write(OUT/'event_windows/development_inputs.json',dev)
    for item in dev:
        video=item['video_id'];raw,provenance=authorized_rows(video,runroot);rows=target_timeline(raw,cfg)
        pool,selected,queues=select_events(rows,cfg)
        write(OUT/f'event_windows/target_timelines/{video}.json',{'provenance':provenance,'rows':rows})
        candidates += [{'video_id':video,**e} for e in pool]
        cap=cv2.VideoCapture(item['path'])
        try:
            for index,e in enumerate(selected):
                event={**e,'pack_id':f'{video}__W{index+1:02d}','video_id':video,'target_id':'phone_01',
                    'representation':'DENSE_ORDERED_EVENT_FRAMES','physical_reasoning_eligible':e['category']=='PHYSICAL_INTERACTION_EVENT' and e['completeness']=='COMPLETE_EVENT_WINDOW'}
                ctx=select_context(rows,e,cfg);event['contexts']=ctx;event['markers']=[c['marker'] for c in ctx]
                event['actor_markers']=[c['marker'] for c in ctx if c['role']=='INTERACTION_ACTOR_CANDIDATE']
                event['location_markers']=[c['marker'] for c in ctx if c['role']=='LOCATION_ANCHOR_CANDIDATE']
                event['actor_available']=bool(event['actor_markers']);event['location_available']=bool(event['location_markers'])
                event['frames']=[];paths=[]
                # Lifecycle is independently budgeted and never dispatched as placement.
                if event['category']=='PHYSICAL_INTERACTION_EVENT':
                    for row in dense_frames(rows,e,cfg):
                        row={**row,'phase':'BEFORE' if row['time']<event['transition_time'] else 'DURING' if row['time']<=event['transition_time']+.6 else 'AFTER'}
                        if not event['start_frame']<=row['frame']<=event['end_frame']:raise ValueError('Out-of-window frame')
                        cap.set(cv2.CAP_PROP_POS_FRAMES,row['frame']);okay,image=cap.read()
                        if not okay:raise OSError('Validation frame decode failed')
                        path=OUT/f"event_windows/frames/{event['pack_id']}/f{row['frame']:06d}.png"
                        render_frame(image,row,event,ctx,path);paths.append(path)
                        event['frames'].append({'frame':row['frame'],'time':row['time'],'phase':row['phase'],'image_path':str(path),'sha256':sha256(path),
                            'target_marked':row['identity_authorized'],'target_bbox':row['target_bbox'], 'mask_reference':row.get('mask_reference'),
                            'identity_authorization_provenance':row['target_authorization_provenance']})
                    sheet=OUT/f"event_windows/event_review_sheets/{event['pack_id']}.png";contact_sheet(paths,sheet,event);event['review_sheet']=str(sheet)
                events.append(event)
        finally:cap.release()
        diagnostics.append({'video_id':video,'timeline_rows':len(rows),'authorized_target_rows':sum(r['identity_authorized'] for r in rows),'queues':queues})
        print('Prepared',video,queues,flush=True)
    write(OUT/'event_windows/candidate_manifest.json',candidates);write(OUT/'event_windows/event_manifest.json',events)
    physical=[e for e in events if e['category']=='PHYSICAL_INTERACTION_EVENT']
    counts=Counter(e['completeness'] for e in physical)
    metrics={'validation_videos':len(dev),'selected_physical_events':len(physical),'complete':counts['COMPLETE_EVENT_WINDOW'],
        'incomplete':counts['INCOMPLETE_EVENT_WINDOW'],'complete_rate':counts['COMPLETE_EVENT_WINDOW']/len(physical) if physical else 0,
        'qwen_eligible':sum(e['physical_reasoning_eligible'] for e in events),'lifecycle_selected':len(events)-len(physical),
        'per_video':diagnostics,'actor_available':sum(e['actor_available'] for e in physical),'location_available':sum(e['location_available'] for e in physical),
        'semantic_placement_release_coverage':'Requires post-freeze visual engineering review; no GT used for selection',
        'identity_writes':0,'fresh_upstream_YOLO_SAM':True,'prepare_seconds':time.monotonic()-started}
    write(OUT/'event_windows/window_metrics.json',metrics)
    requests=[]
    for e in events:
        if not e['physical_reasoning_eligible']:continue
        requests.append({'pack_id':e['pack_id'],'images':[f['image_path'] for f in e['frames']],
            'image_sha256':[f['sha256'] for f in e['frames']], 'prompt':prompt(e),'prompt_sha256':canonical_hash(prompt(e)), 'max_new_tokens':1400})
    write(OUT/'qwen/requests.json',requests)
    files=list((OUT/'event_windows').rglob('*'))+[OUT/'qwen/requests.json']
    write(OUT/'event_windows/builder_freeze.json',{'stage':'A_BUILDER_AND_REQUESTS_FROZEN_BEFORE_REVIEW','review_started':False,
        'files':freeze_files(OUT,files),'sources':source_hashes(),'freeze_unix':time.time(),'config_corrections':0})
    return metrics
