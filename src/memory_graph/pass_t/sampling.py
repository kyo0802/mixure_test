"""Pure timestamp sampling contracts. This module never decodes source frames."""
from bisect import bisect_left
from copy import deepcopy
import hashlib
import json
import math
import re
from pathlib import Path
from .contracts import MANIFEST_SCHEMA, BUNDLE_SCHEMA, schema_errors


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sample(source, start, end, fps=3):
    if not all(math.isfinite(x) for x in [start,end,fps]) or start>=end or fps<=0:
        raise ValueError('Invalid window or density')
    inside=[x for x in source if start<=x['timestamp_s']<end]
    if not inside: raise ValueError('No authorized source timestamps')
    times=[x['timestamp_s'] for x in inside]
    indices=[x['source_frame_index'] for x in inside]
    if any(a>=b for a,b in zip(times,times[1:])) or any(a>=b for a,b in zip(indices,indices[1:])):
        raise ValueError('Source chronology/indices must be strictly increasing')
    n=math.ceil((end-start)*fps-1e-9)
    grids=list(range(n)) if n<=16 else [(2*j*(n-1)+15)//30 for j in range(16)]
    selected=[]; used=set(); collisions=[]
    for k in grids:
        t=start+k/fps; pos=bisect_left(times,t)
        candidates=[i for i in [pos-1,pos] if 0<=i<len(inside)]
        # Floating point roundoff must not reverse a mathematical tie.
        best=candidates[0]
        for i in candidates[1:]:
            if abs(times[i]-t)<abs(times[best]-t)-1e-12: best=i
        item=inside[best]
        if item['source_frame_index'] in used: collisions.append(k);continue
        selected.append(deepcopy(item));used.add(item['source_frame_index'])
    return selected, {'grid_count':n,'selected_grid_indices':grids,
        'collision_grid_indices':collisions,'realized_density_fps':len(selected)/(end-start)}


def manifest_identity(manifest):
    fields={k:manifest[k] for k in ['event_window_id','window_start_s','window_end_s','target_fps']}
    fields['source_video_id_or_hash']=manifest.get('source_video_hash') or manifest['source_video_id']
    fields['ordered_source_frame_indices']=[f['source_frame_index'] for f in manifest['frames']]
    fields['timestamp_provenance']=[f['timestamp_provenance'] for f in manifest['frames']]
    return 'SM_'+digest(fields)[:12]


def make_manifest(unit, selected, sampling):
    m={**deepcopy(unit),'schema_version':'v1','sampling':sampling,'frames':[]}
    for i,f in enumerate(selected):
        name=f'F{i:03d}'
        m['frames'].append({'frame_id':name,'source_frame_index':f['source_frame_index'],
            'source_timestamp_s':f['timestamp_s'],
            'window_relative_timestamp_s':f['timestamp_s']-unit['window_start_s'],
            'image_path':f'frames/{name}.png','sha256':f['sha256'],
            'timestamp_provenance':f['timestamp_provenance'],'overlay_policy_id':'OVERLAY_NEUTRAL_V1',
            'sampling_manifest_version':'v1'})
    m['sampling_manifest_id']=manifest_identity(m)
    return m


def validate_manifest(m, root=None):
    errors=schema_errors(m,MANIFEST_SCHEMA)
    if errors:return errors
    start=m['window_start_s'];end=m['window_end_s'];frames=m['frames']
    if start>=end:errors.append('invalid window')
    if len(frames)>16:errors.append('frame cap exceeded')
    if m['sampling_manifest_id']!=manifest_identity(m):errors.append('content identity mismatch')
    n=math.ceil((end-start)*m['target_fps']-1e-9)
    grid=list(range(n)) if n<=16 else [(2*j*(n-1)+15)//30 for j in range(16)]
    if m['sampling']['grid_count']!=n or m['sampling']['selected_grid_indices']!=grid:
        errors.append('sampling grid metadata mismatch')
    if abs(m['sampling']['realized_density_fps']-len(frames)/(end-start))>1e-9:
        errors.append('realized density mismatch')
    for i,f in enumerate(frames):
        if f['frame_id']!=f'F{i:03d}':errors.append('noncanonical frame ID')
        if not start<=f['source_timestamp_s']<end:errors.append('unauthorized frame')
        if abs(f['window_relative_timestamp_s']-(f['source_timestamp_s']-start))>.001:
            errors.append('relative timestamp mismatch')
        if f['image_path']!=f"frames/{f['frame_id']}.png":errors.append('asset name mismatch')
        if i and (frames[i-1]['source_timestamp_s']>=f['source_timestamp_s'] or frames[i-1]['source_frame_index']>=f['source_frame_index']):errors.append('duplicate/unordered frame')
        if root is not None:
            p=Path(root)/f['image_path']
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:
                errors.append('missing/corrupt asset '+f['frame_id'])
    return errors


FORBIDDEN=re.compile(r'pick[ _-]?up|move[ _-]?while[ _-]?held|place|release|handoff|truth|trigger|reid|score|identityguard|alias|label|(?:^|[\W_])gt(?:$|[\W_])|phone_\d+|ce:|entity_\d+|candidate_\d+|test\d+|val_\d+',re.I)


def leakage_errors(bundle, asset_metadata=None):
    errors=[]
    def walk(value,path=''):
        if isinstance(value,dict):
            for k,v in value.items():
                if FORBIDDEN.search(k):errors.append('forbidden key '+path+'.'+k)
                walk(v,path+'.'+k)
        elif isinstance(value,list):
            for i,v in enumerate(value):walk(v,path+f'[{i}]')
        elif isinstance(value,str) and FORBIDDEN.search(value):errors.append('forbidden value '+path)
    walk(bundle)
    if asset_metadata:
        # All image text/EXIF or container descriptive metadata is forbidden,
        # even if it does not happen to match the token list.
        errors.append('nonempty model-visible asset metadata')
        walk(asset_metadata,'metadata')
    return errors


def bundle_from_manifest(m, representation, prompt_sha, persons=(), anchors=()):
    if representation not in {'A','B','C'}:raise ValueError('Unsupported representation; no substitution')
    b={'representation_type':representation,'schema_version':'v1',
       'sampling_manifest_id':m['sampling_manifest_id'],
       'frames':[{'frame_id':f['frame_id'],'image_path':f['image_path'],
                  'timestamp_s':f['source_timestamp_s'],'sha256':f['sha256']} for f in m['frames']],
       'target_id':'T1','person_ids':list(persons),'allowed_anchor_ids':list(anchors),
       'overlay_policy_id':'OVERLAY_NEUTRAL_V1','prompt_id':'pass_t_event_annotator_v1',
       'prompt_sha256':prompt_sha,'media_path':{'A':'media/input.mkv','B':None,'C':'media/grid.png'}[representation],
       'tile_mapping':[]}
    if representation=='C':
        b['tile_mapping']=[{'frame_id':f['frame_id'],'row':i//4,'column':i%4,
                           'timestamp_s':f['source_timestamp_s']} for i,f in enumerate(m['frames'])]
    b['bundle_id']='B_'+digest(b)[:12]
    return b


def validate_bundle(b):
    errors=schema_errors(b,BUNDLE_SCHEMA)
    if errors:return errors
    content={k:v for k,v in b.items() if k!='bundle_id'}
    if b['bundle_id']!='B_'+digest(content)[:12]:errors.append('bundle hash mismatch')
    if len(b['frames'])>16:errors.append('bundle frame cap exceeded')
    if [x['frame_id'] for x in b['frames']]!=[f'F{i:03d}' for i in range(len(b['frames']))]:errors.append('duplicate/noncanonical frame IDs')
    if any(a['timestamp_s']>=z['timestamp_s'] for a,z in zip(b['frames'],b['frames'][1:])):errors.append('bundle chronology invalid')
    if b['representation_type']=='B' and (b['media_path'] is not None or b['tile_mapping']):errors.append('B mode mismatch')
    if b['representation_type']=='A' and (b['media_path'] not in {'media/input.mkv','media/input.mp4'} or b['tile_mapping']):errors.append('A mode mismatch')
    if b['representation_type']=='C':
        expected=[{'frame_id':f['frame_id'],'row':i//4,'column':i%4,'timestamp_s':f['timestamp_s']} for i,f in enumerate(b['frames'])]
        if b['media_path']!='media/grid.png' or b['tile_mapping']!=expected:errors.append('storyboard mapping mismatch')
    return errors+leakage_errors(b)


def shared_frames(bundles):
    if not bundles:raise ValueError('no representations')
    origin=(bundles[0]['sampling_manifest_id'],bundles[0]['frames'])
    return all((b['sampling_manifest_id'],b['frames'])==origin for b in bundles)


def verify_encoded_timing(intended_pts, decoded_pts, ordered_frame_signatures=None):
    """Contract checker only; requires an adapter to supply actual decoded PTS."""
    if len(intended_pts)!=len(decoded_pts):
        return {'status':'BLOCKED','reason':'decoded frame count mismatch','max_deviation_s':None}
    if not decoded_pts or any(a>=b for a,b in zip(decoded_pts,decoded_pts[1:])):
        return {'status':'BLOCKED','reason':'decoded chronology invalid','max_deviation_s':None}
    deviation=max(abs(a-b) for a,b in zip(intended_pts,decoded_pts))
    if ordered_frame_signatures is not None and ordered_frame_signatures[0]!=ordered_frame_signatures[1]:
        return {'status':'BLOCKED','reason':'decoded frame order/content mismatch','max_deviation_s':deviation}
    return {'status':'READY' if deviation<=.001 else 'A_NON_EQUIVALENT',
            'reason':None if deviation<=.001 else 'encoded timing exceeds 1ms',
            'max_deviation_s':deviation}
