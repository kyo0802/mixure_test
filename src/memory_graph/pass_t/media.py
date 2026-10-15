"""Offline real media adapter; target data enters only via the mapping manifest.

Only authorized frames are converted to model-input pixels. Sequential codec
preroll is counted privately; it never becomes an image or model-visible asset.
"""
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from .sampling import (sample, make_manifest, validate_manifest, bundle_from_manifest,
                       validate_bundle, shared_frames, leakage_errors, verify_encoded_timing, digest)
from .resolver import stage0_gate, PILOT_RESTRICTION


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def dump(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes((json.dumps(value, indent=2, ensure_ascii=False)+'\n').encode('utf-8'))


def require_media():
    try:
        import av
        av.codec.Codec('ffv1', 'w')
        av.codec.Codec('ffv1', 'r')
        return av
    except (ImportError, ValueError) as exc:
        raise RuntimeError('BLOCKED_ENVIRONMENT: PyAV FFV1 encoder/decoder required: '+str(exc)) from exc


def authorized(index, pts, mapping):
    lo, hi = mapping['authorized_half_open_frames']
    return lo <= index < hi and mapping['window_start_s'] <= pts < mapping['window_end_s']


def decode_authorized(source, mapping):
    av = require_media()
    rows, images = [], {}
    delta = []
    preroll = 0
    lo, hi = mapping['authorized_half_open_frames']
    with av.open(str(source), 'r') as container:
        stream = container.streams.video[0]
        codec = stream.codec_context.name
        dimensions = [stream.width, stream.height]
        for index, frame in enumerate(container.decode(stream)):
            if index >= hi:
                break
            if frame.pts is None or frame.time_base is None:
                raise ValueError('Native source PTS unavailable; no undocumented timestamp fallback')
            pts = float(frame.pts * frame.time_base)
            if index < lo:
                preroll += 1
                continue
            derived = index / mapping['source_fps']
            delta.append({'source_frame_index':index,'derived_fps_s':derived,'native_pts_s':pts,
                          'difference_s':pts-derived,'authorized_by_both_bounds':authorized(index,pts,mapping)})
            if not authorized(index, pts, mapping):
                continue
            pixels = frame.to_ndarray(format='rgb24')
            images[index] = pixels
            rows.append({'source_frame_index':index,'timestamp_s':pts,'sha256':'0'*64,
                         'timestamp_provenance':'NATIVE_PTS'})
    if not rows:
        raise ValueError('No authorized decoded frames')
    if any(a['timestamp_s'] >= b['timestamp_s'] for a,b in zip(rows,rows[1:])):
        raise ValueError('Source PTS not strictly monotonic')
    return rows, images, {'method':'SEQUENTIAL_DECODE_FROM_FRAME_ZERO; NO_SEEK',
                          'source_codec':codec,'source_dimensions':dimensions,
                          'codec_preroll_frames_not_model_input':preroll,
                          'authorized_pixel_frames':len(rows),'pts_vs_derived':delta,
                          'timestamp_used':'NATIVE_PTS','pts_probe':'PyAV/libavformat; ffprobe CLI absent',
                          'max_abs_pts_vs_derived_s':max(abs(x['difference_s']) for x in delta)}


def exact_overlay(pixels, index, observations):
    exact = [o for o in observations if o['frame_index']==index and o.get('bbox')]
    boxes = {tuple(x['bbox']) for x in exact}
    if len(boxes)>1:
        raise ValueError('Conflicting exact source boxes')
    image = Image.fromarray(pixels.copy())
    if not boxes:
        return image, False
    box = next(iter(boxes))
    if len(box)!=4 or not all(math.isfinite(x) for x in box):
        raise ValueError('Invalid exact box')
    x1,y1,x2,y2 = box
    if not 0<=x1<x2<=image.width or not 0<=y1<y2<=image.height:
        raise ValueError('Exact box exceeds clean source dimensions')
    ImageDraw.Draw(image).rectangle(box, outline=(0,180,180), width=2)
    return image, True


def coverage(selected, marked):
    return {'marked_count':sum(marked),'sampled_count':len(selected),
            'ratio':sum(marked)/len(selected) if selected else 0,
            'unmarked_source_frame_indices':[s['source_frame_index'] for s,m in zip(selected,marked) if not m],
            'grounding_status':'TARGET_VISUALLY_GROUNDED_ON_EXACT_OBSERVATIONS' if any(marked) else 'TARGET_NOT_VISUALLY_GROUNDED'}


def rgb_signature(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def encode_video(path, frames, pts, window_duration_s=None):
    av = require_media()
    path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    signatures = [rgb_signature(np.asarray(image)) for image in frames]
    encoded_pts = [round(t*1000) for t in pts]
    end_tick = round(window_duration_s*1000) if window_duration_s is not None else encoded_pts[-1]+333
    durations = {t: (encoded_pts[i+1] if i+1<len(encoded_pts) else end_tick)-t
                 for i,t in enumerate(encoded_pts)}
    if any(d<=0 for d in durations.values()):
        raise ValueError('Invalid native video duration')
    if any(a>=b for a,b in zip(encoded_pts,encoded_pts[1:])):
        raise ValueError('A_NON_EQUIVALENT: timebase quantization collision')
    with av.open(str(path),'w',format='matroska') as container:
        container.metadata.clear()
        stream = container.add_stream('ffv1',rate=3)
        stream.width,stream.height = frames[0].size
        stream.pix_fmt = 'bgr0'
        stream.time_base = Fraction(1,1000)
        stream.codec_context.time_base = Fraction(1,1000)
        stream.metadata.clear()
        for image, ticks in zip(frames,encoded_pts):
            frame = av.VideoFrame.from_ndarray(np.asarray(image),format='rgb24')
            frame.pts = ticks;frame.time_base=Fraction(1,1000)
            for packet in stream.encode(frame):
                packet.duration = durations[packet.pts]
                container.mux(packet)
        for packet in stream.encode():
            packet.duration = durations[packet.pts]
            container.mux(packet)
    decoded_pts, decoded_signatures = [], []
    with av.open(str(path),'r') as c:
        s = c.streams.video[0]
        metadata = {'container':dict(c.metadata),'stream':dict(s.metadata)}
        codec = s.codec_context.name
        for f in c.decode(s):
            decoded_pts.append(float(f.pts*f.time_base))
            decoded_signatures.append(rgb_signature(f.to_ndarray(format='rgb24')))
    timing = verify_encoded_timing(pts,decoded_pts,(signatures,decoded_signatures))
    return {'adapter_status':'READY' if timing['status']=='READY' else timing['status'],
            'backend_video_capability':'NOT_TESTED','encoded_frame_count':len(encoded_pts),
            'decoded_frame_count':len(decoded_pts),'intended_window_relative_pts_s':pts,
            'encoder_pts_ticks':encoded_pts,'encoder_time_base':'1/1000','decoded_pts_s':decoded_pts,
            'frame_duration_ticks':[durations[t] for t in encoded_pts],
            'authorized_window_duration_s':window_duration_s,
            'timing':timing,'codec':codec,'container':'matroska','pixel_format':'bgr0',
            'pixel_transform':'RGB24 -> BGR0 -> RGB24; FFV1 lossless',
            'ordered_pixel_signatures':signatures,'decoded_pixel_signatures':decoded_signatures,
            'sha256':sha(path),'metadata':metadata}


def storyboard(path, frames, manifest):
    width,height = frames[0].size
    scale = min(1,320/width)
    tw,th = round(width*scale),round(height*scale)
    header = 24
    grid = Image.new('RGB',(4*tw,math.ceil(len(frames)/4)*(th+header)),(32,32,32))
    mapping=[]
    for i,(image,f) in enumerate(zip(frames,manifest['frames'])):
        row,col = i//4,i%4
        x,y = col*tw,row*(th+header)
        tile = image.resize((tw,th),Image.Resampling.LANCZOS)
        grid.paste(tile,(x,y+header))
        # Exact frame-ID and time only, never source identifiers or event labels.
        ImageDraw.Draw(grid).text((x+4,y+4),f"{f['frame_id']}  {f['source_timestamp_s']:.6f}s",fill=(255,255,255))
        mapping.append({'frame_id':f['frame_id'],'row':row,'column':col,'timestamp_s':f['source_timestamp_s'],
                        'pixel_rectangle':[x,y+header,x+tw,y+header+th]})
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    grid.save(path,format='PNG')
    return {'tile_mapping':mapping,'tile_dimensions':[tw,th], 'header_height':header,
            'source_dimensions':[width,height], 'effective_resolution_per_frame':[tw,th],
            'transform':'LANCZOS aspect-preserving resize; separate neutral header; row-major 4 columns',
            'sampling_manifest_id':manifest['sampling_manifest_id'],'sha256':sha(path)}


def scan_real(folder, bundles, a_record):
    """Scan actual generated files and reopened metadata, not synthetic fixtures."""
    errors = []
    folder = Path(folder)
    # Model-visible scope is bundles + frames/media, never audit or source manifest.
    paths = [p for d in ['frames','media'] for p in (folder/d).glob('*')]
    for b in bundles:
        errors.extend(validate_bundle(b))
        errors.extend(leakage_errors(b))
    for p in paths:
        errors.extend(leakage_errors({'asset_path':p.relative_to(folder).as_posix()}))
        if p.suffix=='.png':
            with Image.open(p) as im:
                im.load()
                errors.extend(leakage_errors({},dict(im.info) or dict(im.getexif())))
    # libavformat creates only structural tags ENCODER/DURATION. They are
    # allowlisted by key AND value, recorded, and scanned for private tokens.
    meta = a_record['metadata']
    for section,tags in meta.items():
        for key,value in tags.items():
            if key.upper()=='ENCODER' and value.startswith(('Lavf','Lavc')):
                errors.extend(leakage_errors({'technical':value}))
            elif key.upper()=='DURATION' and all(c in '0123456789:.' for c in value):
                pass
            else:
                errors.append('Unexpected nonessential container metadata: '+section+'.'+key)
    return {'status':'REAL_LEAKAGE_PASS' if not errors else 'BLOCKED_LEAKAGE','errors':errors,
            'actual_assets_scanned':len(paths), 'overlay_text':'target rectangles only; storyboard F IDs and times',
            'image_metadata':'reopened PNG info/EXIF empty',
            'technical_container_metadata':meta,'private_mapping_in_bundle':False}


def make_media(source, mapping, folder, prompt_sha):
    if 'diagnostic_only' in mapping:
        raise ValueError('Private diagnostic records are forbidden media inputs')
    if mapping['resolution_status']!='RESOLVED_UNIQUE' or mapping['binding_causality_status']=='NON_CAUSAL':
        raise ValueError('Unresolved/noncausal target-specific input blocked')
    if not mapping['clean_source_hash_verified'] or sha(source)!=mapping['source_video_hash']:
        raise ValueError('Clean source hash mismatch')
    folder = Path(folder)
    if folder.exists():
        raise FileExistsError('Refusing media overwrite; choose a fresh pilot directory')
    rows,pixels,source_decode = decode_authorized(source,mapping)
    selected, sampling = sample(rows,mapping['window_start_s'],mapping['window_end_s'],3)
    (folder/'frames').mkdir(parents=True)
    images,marked = [],[]
    for i,record in enumerate(selected):
        im,m = exact_overlay(pixels[record['source_frame_index']],record['source_frame_index'],mapping['exact_observations'])
        path=folder/'frames'/f'F{i:03d}.png'
        im.save(path,format='PNG')
        record['sha256']=sha(path);images.append(im);marked.append(m)
    unit={'event_window_id':mapping['pack_id'],'session_id':mapping['video_id'],
          'source_video_id':mapping['video_id'],'source_video_hash':mapping['source_video_hash'],
          'target_local_id':mapping['resolved_local_track_id'],'window_start_s':mapping['window_start_s'],
          'window_end_s':mapping['window_end_s'],'target_fps':3}
    manifest=make_manifest(unit,selected,sampling)
    bundles=[bundle_from_manifest(manifest,x,prompt_sha) for x in 'ABC']
    a=encode_video(folder/'media/input.mkv',images,[f['window_relative_timestamp_s'] for f in manifest['frames']],
                   mapping['window_end_s']-mapping['window_start_s'])
    c=storyboard(folder/'media/grid.png',images,manifest)
    leak=scan_real(folder,bundles,a)
    errors=validate_manifest(manifest,folder)+[err for b in bundles for err in validate_bundle(b)]
    if not shared_frames(bundles):errors.append('A/B/C manifest mismatch')
    if a['adapter_status']!='READY':errors.append('A timing/order verification failed')
    if leak['errors']:errors.extend(leak['errors'])
    if not all(authorized(f['source_frame_index'],f['source_timestamp_s'],mapping) for f in manifest['frames']):
        errors.append('Unauthorized selected frame')
    cov=coverage(selected,marked)
    grounded=cov['marked_count']>0
    ready=not errors and grounded
    for b in bundles:
        dump(folder/f"bundle_{b['representation_type']}.json",b)
    # Source identifiers/cutoff/causality/restrictions are outside model bundles.
    dump(folder/'private/frame_manifest.json',manifest)
    record={**PILOT_RESTRICTION,'pack_id':mapping['pack_id'],
            'binding_causality_status':mapping['binding_causality_status'],
            'integrity_status':'PASS' if not errors else 'BLOCKED','target_grounded':grounded,
            'real_smoke_status':'PASS' if ready else 'BLOCKED', 'errors':errors,
            'overlay_coverage':cov,'source_decode':source_decode,'A':a,
            'B':{'adapter_status':'READY' if not errors else 'BLOCKED','frames':len(images),'resolution':list(images[0].size)},
            'C':{'adapter_status':'READY' if not errors else 'BLOCKED',**c},'leakage':leak,
            'sampling_manifest_id':manifest['sampling_manifest_id'],
            'source_frame_indices':[f['source_frame_index'] for f in manifest['frames']],
            'canonical_timestamps_s':[f['source_timestamp_s'] for f in manifest['frames']],
            'model_visible_allowlist':['bundle_A.json','bundle_B.json','bundle_C.json','frames/','media/'],
            'private_do_not_send':['private/'],'model_inference_calls':0,'graph_writes':0}
    dump(folder/'private/pilot_integrity.json',record)
    return record


def run_pilot(pilot_partial=False):
    root=Path(__file__).resolve().parents[3];out=root/'artifacts/pass_t'
    # This is the only file opened for target information.
    mappings=json.loads((out/'manifests/window_target_mapping.json').read_text(encoding='utf-8'))['packs']
    gate=stage0_gate(mappings,pilot_partial)
    prompt=out/'contracts/pass_t_event_annotator_v1.txt'
    prompt_sha=sha(prompt)
    if prompt_sha!='45fcdd24b6fcc161ed7af007a5fdfd1d355349bc04dd7680255037bd68a4c76c':
        raise ValueError('Frozen Pass T prompt hash mismatch')
    results=[]
    for m in mappings:
        if m['pack_id'] not in gate['eligible_packs']:
            results.append({**PILOT_RESTRICTION,'pack_id':m['pack_id'],
                            'binding_causality_status':m['binding_causality_status'],
                            'real_smoke_status':'BLOCKED','A':{'adapter_status':'BLOCKED'},
                            'B':{'adapter_status':'BLOCKED'},'C':{'adapter_status':'BLOCKED'},
                            'reason_codes':m['reason_codes'],'leakage':{'status':'REAL_LEAKAGE_NOT_RUN_NO_ELIGIBLE_WINDOW'}})
            continue
        folder=out/'inputs/pilot_partial'/('U_'+digest(m['pack_id'])[:12]+'_r2')
        try:
            result=make_media(root/m['source_video_path'],m,folder,prompt_sha)
            result['artifact_directory']=folder.relative_to(root).as_posix()
        except Exception as exc:
            state='BLOCKED_ENVIRONMENT' if 'BLOCKED_ENVIRONMENT' in str(exc) else 'BLOCKED'
            result={**PILOT_RESTRICTION,'pack_id':m['pack_id'],'binding_causality_status':m['binding_causality_status'],
                    'real_smoke_status':state,'A':{'adapter_status':state},'B':{'adapter_status':state},
                    'C':{'adapter_status':state},'error':str(exc)}
        results.append(result)
    report={**PILOT_RESTRICTION,'gate':gate,'packs':results,'milestone':'M3','optional_scene_only':'NOT_RUN',
            'model_inference_calls':0,'graph_writes':0,'builder_changes':0}
    dump(out/'smoke/phase1b_real_media.json',report)
    dump(out/'manifests/phase1b_milestone_M3.json',{'status':'COMPLETE','attempted':len(gate['eligible_packs']),
                                                 'passed':sum(x['real_smoke_status']=='PASS' for x in results)})
    return {'attempted':len(gate['eligible_packs']),'passed':sum(x['real_smoke_status']=='PASS' for x in results),
            'failed':[{'pack_id':x['pack_id'],'error':x.get('error',x.get('errors'))} for x in results
                      if x['pack_id'] in gate['eligible_packs'] and x['real_smoke_status']!='PASS']}
