"""Read only manifested development observations; never enumerate raw-media directories."""
from bisect import bisect_right
from memory_graph.reasoning.common import ROOT,read,sha256

def inputs():
    config=read(ROOT/'outputs_v292/canonical_config.json')
    videos=config['video_ids'];result=[]
    for video in videos:
        manifest=read(ROOT/f'outputs_v292/{video}/run_manifest.json')
        path=ROOT/f'{video}.mp4'
        if sha256(path)!=manifest['video_sha256']:raise ValueError('Manifested development media changed: '+video)
        result.append({'video_id':video,'path':str(path),'sha256':manifest['video_sha256'],
            'membership_source':f'outputs_v292/{video}/run_manifest.json','fps':read(ROOT/f'outputs_v292/{video}/video_metadata.json')['fps']})
    return result

def authorized_rows(video):
    folder=ROOT/'outputs_v292'/video;meta=read(folder/'video_metadata.json');fps=meta['fps'];size=[meta['width'],meta['height']]
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
    for item in read(ROOT/f'outputs_v293/{video}/prepared_events.json'):
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
                'scene_ok':raw.get('scene_ok',True),'source':f'outputs_v293/{video}/prepared_events.json#{event_id}:{f}',
                'target_authorization_provenance':raw['target_authorization']}
    return sorted(rows.values(),key=lambda r:r['frame']),{'video_id':video,'fps':fps,'image_size':size,
        'source_manifests':[f'outputs_v292/{video}/run_manifest.json',f'outputs_v293/{video}/prepared_events.json'],
        'source_sha256':[sha256(folder/'memory/observations.json'),sha256(ROOT/f'outputs_v293/{video}/prepared_events.json')],
        'dense_events_used':dense_sources,'fresh_YOLO_SAM_calls':0,'identity_logic_changed':False}
