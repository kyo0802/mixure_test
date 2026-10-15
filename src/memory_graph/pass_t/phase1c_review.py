"""Prepare exactly seven bounded human-only packages from causal source fields."""
import json
from fractions import Fraction
from pathlib import Path
import numpy as np
from PIL import Image
from .phase1c_common import ROOT, OUT, read, write, sha, COUNTERS
from .phase1c_policy import verify_freeze
from .media import require_media, authorized, rgb_signature

REVIEW=OUT/'human_seed_review'
EXPECTED=('test2__W01','test3__W07','test5__W01','test5__W05','test7__W05','test8__W06','test8__W07')
RESTRICTIONS={'human_review_only':True,'not_model_input':True,'evaluation_eligible':False,
              'purpose':'HUMAN_REVIEW_ONLY','status':'NOT_FOR_EVALUATION'}


def projected_inventory(mapping):
    """No diagnosis report, ranking, GT, guard decisions or post-window data."""
    video=mapping['video_id'];base=ROOT/'outputs_v292'/video
    binding=read(base/'identity/target_binding.json')['bound_target']
    seed=binding['source_track_id']
    tracks=read(base/'perception/tracks.json')
    seed_rows=[{'frame_index':o['frame_index'],'timestamp':o['timestamp'],'bbox':o['bbox']}
               for t in tracks if t['track_id']==seed for o in t['observations']
               if o['timestamp']<mapping['window_start_s']]
    detections=read(base/'perception/yolo_detections.json')
    rows=[]
    for row in read(base/'candidate_stream.json')['observations']:
        if not mapping['window_start_s']<=row['timestamp']<mapping['window_end_s'] or row.get('semantic_class')!='cell phone':
            continue
        index=row['raw_detection_index']
        det=detections[index]
        if det['frame_index']!=row['frame_index']:
            raise ValueError('Raw observation frame mismatch')
        local=row.get('source_track_id')
        id_=str(local) if local is not None else row.get('candidate_id')
        # A detection without recorded track/candidate identity is visible but
        # never becomes an invented selectable persistent candidate.
        rows.append({'candidate_id':id_,'local_track_id':str(local) if local is not None else None,
                     'recorded_candidate_reference':row.get('candidate_id'),
                     'observation_id':f'raw:{index}@{row["frame_index"]}',
                     'source_frame_index':row['frame_index'],'source_timestamp_s':row['timestamp'],
                     'bbox':det['bbox'],'provenance_reference':f'outputs_v292/{video}/candidate_stream.json',
                     'origin':'RECORDED_IN_WINDOW_SOURCE_OBSERVATION; upstream causality unverified'})
    return seed,binding,seed_rows,rows


def reference_selection(seed_rows,bound_frame):
    if not seed_rows:return []
    rows=sorted(seed_rows,key=lambda x:x['frame_index'])
    indices={rows[0]['frame_index'],rows[-1]['frame_index']}
    if any(o['frame_index']==bound_frame for o in rows):indices.add(bound_frame)
    return [o for o in rows if o['frame_index'] in indices]


def candidate_inventory(observations):
    result=[]
    for id_ in sorted({o['candidate_id'] for o in observations if o['candidate_id'] is not None}):
        obs=[o for o in observations if o['candidate_id']==id_]
        result.append({'candidate_id':id_,'local_track_id':obs[0]['local_track_id'],
                       'observation_ids':[o['observation_id'] for o in obs],
                       'evidence_frame_ids':sorted({f'S{o["source_frame_index"]:06d}' for o in obs}),
                       'recorded_provenance_edges':[],
                       'selection_scope':'EXISTING_LOCAL_CANDIDATE_ONLY; no global identity authority'})
    return result


def encode_trimmed_clip(path,frames,window_start,window_end,folder):
    av=require_media();signatures=[]
    ticks=[round((f['source_timestamp_s']-window_start)*1000) for f in frames]
    end=round((window_end-window_start)*1000)
    durations={t:(ticks[i+1] if i+1<len(ticks) else end)-t for i,t in enumerate(ticks)}
    if any(v<=0 for v in durations.values()):raise ValueError('Review clip timebase collision')
    with av.open(str(path),'w',format='matroska') as container:
        stream=container.add_stream('ffv1',rate=30)
        first=Image.open(folder/frames[0]['image_path']);stream.width,stream.height=first.size;first.close()
        stream.pix_fmt='bgr0';stream.time_base=Fraction(1,1000);stream.codec_context.time_base=Fraction(1,1000)
        for f,t in zip(frames,ticks):
            with Image.open(folder/f['image_path']) as image:
                pixels=np.asarray(image.convert('RGB'));signatures.append(rgb_signature(pixels))
                frame=av.VideoFrame.from_ndarray(pixels,format='rgb24');frame.pts=t;frame.time_base=Fraction(1,1000)
                for packet in stream.encode(frame):
                    packet.duration=durations[packet.pts];container.mux(packet)
        for packet in stream.encode():
            packet.duration=durations[packet.pts];container.mux(packet)
    actual=[];decoded=[]
    with av.open(str(path),'r') as container:
        for f in container.decode(video=0):
            actual.append(float(f.pts*f.time_base));decoded.append(rgb_signature(f.to_ndarray(format='rgb24')))
    if decoded!=signatures or len(actual)!=len(frames):raise ValueError('Review clip frame correspondence failed')
    error=max(abs(a-(f['source_timestamp_s']-window_start)) for a,f in zip(actual,frames))
    if error>.001:raise ValueError('Review clip PTS error exceeds 1ms')
    return {'path':'review_clip.mkv','codec':'ffv1','decoded_frame_count':len(actual),
            'max_pts_deviation_s':error,'sha256':sha(path),'full_rate':True,**RESTRICTIONS}


def make_item(mapping,original_seed,refs,observations,receipt):
    folder=REVIEW/'items'/mapping['pack_id']
    if folder.exists():raise FileExistsError('Refusing review item overwrite')
    folder.mkdir(parents=True);(folder/'frames').mkdir();(folder/'references').mkdir()
    source=ROOT/mapping['source_video_path']
    if sha(source)!=mapping['source_video_hash']:raise ValueError('Read-only source integrity mismatch')
    av=require_media();frames=[];references=[];reference_by_index={o['frame_index']:o for o in refs}
    with av.open(str(source),'r') as c:
        for index,frame in enumerate(c.decode(video=0)):
            if index>=mapping['authorized_half_open_frames'][1]:break
            if frame.pts is None:raise ValueError('Missing native source PTS')
            pts=float(frame.pts*frame.time_base)
            if index in reference_by_index:
                row=reference_by_index[index]
                if not pts<mapping['window_start_s']:raise ValueError('Reference is not strictly pre-window')
                pixels=Image.fromarray(frame.to_ndarray(format='rgb24'));box=row['bbox']
                x1,y1,x2,y2=box
                if not 0<=x1<x2<=pixels.width or not 0<=y1<y2<=pixels.height:
                    raise ValueError('Invalid exact seed crop box')
                crop=pixels.crop((int(x1),int(y1),int(np.ceil(x2)),int(np.ceil(y2))))
                path=f'references/R{index:06d}.png';crop.save(folder/path,format='PNG')
                references.append({'reference_id':f'R{index:06d}','source_frame_index':index,'source_timestamp_s':pts,
                                   'image_path':path,'sha256':sha(folder/path),'role':'REFERENCE_PRE_WINDOW',
                                   'original_seed_track':original_seed,'bbox':box,
                                   'provenance_reference':f'outputs_v292/{mapping["video_id"]}/perception/tracks.json',
                                   'may_be_used_as_in_window_evidence':False})
            if not authorized(index,pts,mapping):continue
            path=f'frames/S{index:06d}.png';image=Image.fromarray(frame.to_ndarray(format='rgb24'))
            image.save(folder/path,format='PNG')
            frames.append({'frame_id':f'S{index:06d}','source_frame_index':index,'source_timestamp_s':pts,
                           'image_path':path,'sha256':sha(folder/path),'timestamp_provenance':'NATIVE_PTS'})
    if not frames:raise ValueError('No authorized full-rate frames')
    indices={f['source_frame_index'] for f in frames}
    observations=[o for o in observations if o['source_frame_index'] in indices]
    candidates=candidate_inventory(observations)
    clip=encode_trimmed_clip(folder/'review_clip.mkv',frames,mapping['window_start_s'],mapping['window_end_s'],folder)
    item={**RESTRICTIONS,'pack_id':mapping['pack_id'],'source_video_identifier':mapping['video_id'],
          'original_resolution':mapping['resolution_status'],'original_seed_track':original_seed,
          'binding_causality':'CAUSALITY_UNVERIFIED',
          'window_start_s':mapping['window_start_s'],'window_end_s':mapping['window_end_s'],
          'authorized_half_open_frames':mapping['authorized_half_open_frames'],
          'overlap_group_id':mapping['overlap_group_id'], 'frames':frames,'references':references,
          'candidates':candidates,'observations':observations,'clip':clip,
          'question':'Which local candidate, if any, is directly supported by authorized evidence and provenance as the target defined by the original seed track?',
          'intended_target_reference_status':'PRE_WINDOW_SEED_REFERENCE_AVAILABLE' if references else 'NO_AUTHORIZED_SEED_REFERENCE; UNRESOLVED is permitted',
          'policy_md_sha256':receipt['policy_md_sha256'],'policy_json_sha256':receipt['policy_json_sha256'],
          'source_provenance_references':[f'outputs_v292/{mapping["video_id"]}/identity/target_binding.json',
              f'outputs_v292/{mapping["video_id"]}/candidate_stream.json',f'outputs_v292/{mapping["video_id"]}/perception/tracks.json',
              f'outputs_v292/{mapping["video_id"]}/perception/yolo_detections.json']}
    write(folder/'item.json',item,exclusive=True)
    return item


def prepare():
    receipt=verify_freeze()
    requests=read(OUT/'manifests/human_seed_request.json')['requests']
    if set(r['pack_id'] for r in requests)!=set(EXPECTED) or len(requests)!=7:
        raise ValueError('Review request scope is not exactly the expected seven')
    mappings={m['pack_id']:m for m in read(OUT/'manifests/window_target_mapping.json')['packs']}
    listed={r['pack_id']:{c['local_track_id'] for c in r['available_local_candidates'] if c['local_track_id']}
            for r in requests}
    manifest={'schema_version':'HUMAN_SEED_REVIEW_V1',**RESTRICTIONS,'items':[],
              'policy_receipt':'../contracts/PASS_T_HUMAN_SEED_ELIGIBILITY_POLICY_V1.freeze_receipt.json',
              'recording_session_independence':'UNKNOWN','candidate_inventory_discrepancies':[]}
    for id_ in EXPECTED:
        mapping=mappings[id_];seed,binding,seed_rows,observations=projected_inventory(mapping)
        reference_rows=reference_selection(seed_rows,binding['frame_index']) if receipt['allow_pre_window_seed_reference'] else []
        item=make_item(mapping,seed,reference_rows,observations,receipt)
        item['original_seed_observations_pre_window']=len(seed_rows)
        item['original_seed_observations_in_window']=sum(o.get('local_track_id')==str(seed) for o in item['observations'])
        # These fields are factual seed counts, never candidate ranking counts.
        write(REVIEW/'items'/id_/'item.json',item)
        observed={c['local_track_id'] for c in item['candidates'] if c['local_track_id']}
        if observed!=listed[id_]:
            manifest['candidate_inventory_discrepancies'].append({'pack_id':id_,'manifest_tracks':sorted(listed[id_]),
                'authorized_native_pts_tracks':sorted(observed),'reason':'Native PTS and conservative frame bounds filter authorization; source manifests are unchanged.'})
        item_path=REVIEW/'items'/id_/'item.json'
        manifest['items'].append({'pack_id':id_,'item_path':f'items/{id_}/item.json','item_sha256':sha(item_path),
                                  'overlap_group_id':mapping['overlap_group_id'],'original_resolution':mapping['resolution_status']})
    (REVIEW/'responses').mkdir(exist_ok=True);(REVIEW/'reports').mkdir(exist_ok=True)
    write(REVIEW/'review_manifest.json',manifest,exclusive=True)
    instructions='''# Seven-window human seed review

HUMAN_REVIEW_ONLY · NOT_MODEL_INPUT · NOT_FOR_EVALUATION. Policy was frozen first. Exactly seven items; no event annotation or global identity assignment.

## Open on Windows PowerShell

```powershell
Set-Location 'C:\\Users\\smile\\Desktop\\test2\\mixure_test_SAM'
.\\.venv\\Scripts\\python.exe -B scripts/run_pass_t_human_seed_review.py
```

This opens a native Tk window; no web server, internet, browser or 127.0.0.1 is required. The top panel identifies the pack, original seed and authorized bounds. Play/step through the full-rate trimmed images. The source video cannot be scrubbed outside the window. Exact observation boxes show existing local IDs only; unlinked raw observations are visible but not invented selectable tracks. Candidate IDs are ascending without scores or ranks.

REFERENCE_PRE_WINDOW crops are separate seed references, never evidence frames. Check every reference actually used. Any reliance requires HUMAN_VISUAL_LOCALIZATION_ONLY. If no authorized seed reference or defensible unique localization exists, UNRESOLVED is correct. Do not choose based on an event answer or generic global identity similarity.

## Save

1. Type your actual reviewer ID. Select one of the four decisions; no decision is preselected.
2. For SELECT_LOCAL_CANDIDATE choose an existing ID. Add exact displayed evidence frames; selected cases must cite a frame with that candidate's actual observation. Relevant observation IDs and source references are linked automatically from those citations.
3. Enter a rationale, uncertainty and your own confidence (required by the frozen v1 response contract). State provenance support; visually localized reference-based choices are not recorded machine edges.
4. Answer all event-label exposure/event-dependence/global-identity attestations and explicitly confirm human authorship. Those exposure/claim records may be saved but are not eligible seeds. If event interpretation is necessary, choose UNRESOLVED.
5. Press Save. The real save records UTC time, viewer submission provenance, policy/item hashes and an immutable response JSON. It cannot overwrite a previous response.

## Stop and resume

Close the Tk window at any time. Reopen with the same command; saved cases are shown as completed/read-only. Nothing is saved merely by navigating or playing. No autosave, auto-choice or agent-generated answers. To correct a saved answer, request a separate explicit correction/version workflow; this seven-case viewer never silently replaces an original. After seven valid responses, stop.

After review, run ` .\\.venv\\Scripts\\python.exe -B scripts/run_pass_t_phase1c.py --step finalize ` to validate authentic submissions and regenerate only new Phase1c reports. Earlier mappings/reports remain unchanged. Viewer attestations are not cryptographic proof of human authorship.
'''
    write(REVIEW/'HUMAN_REVIEW_INSTRUCTIONS.md',instructions,exclusive=True)
    write(REVIEW/'reports/review_preparation.json',{'items_ready':7,'responses_written_by_agent':0,
                                                  'policy_hash_verified':True,'runtime_counters':dict(COUNTERS)})
    return {'items_ready':7,'response_count':0,'viewer':'native Tk; local-only; no server'}
