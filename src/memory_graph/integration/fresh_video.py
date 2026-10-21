"""Fresh-video CPU contracts and isolated-session orchestration. No GT imports."""
import bisect
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

from .adapters import read, sha, key, adapt_cv, adapt_nemotron
from memory_graph.experiments.three_vlm_contract import choose_uniform8, PROMPT, SCHEMA


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def query_category(query):
    q = query.strip().lower().rstrip("?？")
    aliases = {"phone":"phone", "smartphone":"phone", "cell phone":"phone", "手機":"phone",
               "keys":"keys", "key":"keys", "鑰匙":"keys", "wallet":"wallet", "錢包":"wallet",
               "bottle":"bottle", "水瓶":"bottle", "cup":"cup", "杯子":"cup"}
    q = re.sub(r"^(where\s+(?:is|are)\s+)?(?:my\s+|the\s+|a\s+)?", "", q).strip()
    if q in aliases: return aliases[q]
    if not q or len(q)>80: raise ValueError("Provide a short object category or --target-category")
    return q


def validate_timeline(rows):
    if not rows: raise ValueError("EMPTY_OR_UNREADABLE_VIDEO")
    for i, row in enumerate(rows):
        if row["index"] != i or row["pts"] is None or not math.isfinite(row["source_time_s"]):
            raise ValueError("NATIVE_PTS_REQUIRED")
        if row["source_time_s"] < 0: raise ValueError("NEGATIVE_NATIVE_PTS_NOT_SUPPORTED")
        if i and row["source_time_s"] <= rows[i-1]["source_time_s"]:
            raise ValueError("NATIVE_PTS_NOT_STRICTLY_MONOTONIC")


def probe_video(path):
    # Reuse the project's native PyAV dependency/codec checks. No FPS-derived time.
    from memory_graph.pass_t.media import require_media
    av = require_media()
    path = Path(path).resolve(strict=True)
    if path.suffix.lower() != ".mp4" or not path.is_file(): raise ValueError("LOCAL_MP4_REQUIRED")
    digest = sha(path)
    rows=[]
    with av.open(str(path)) as container:
        if not container.streams.video: raise ValueError("NO_VIDEO_STREAM")
        stream=container.streams.video[0]
        width,height=stream.width,stream.height
        for i, frame in enumerate(container.decode(stream)):
            if frame.pts is None or frame.time_base is None: raise ValueError("NATIVE_PTS_UNAVAILABLE")
            if (frame.width,frame.height)!=(width,height): raise ValueError("VARIABLE_DIMENSIONS_UNSUPPORTED")
            rows.append(dict(index=i,pts=frame.pts,time_base=str(frame.time_base),
                source_time_s=float(frame.pts*frame.time_base),
                duration_s=float(frame.duration*frame.time_base) if frame.duration else None))
        fps=float(stream.average_rate) if stream.average_rate else None
        codec=stream.codec_context.name
    validate_timeline(rows)
    if len({r['time_base'] for r in rows})!=1: raise ValueError("VARIABLE_TIME_BASE_UNSUPPORTED")
    deltas=[b['source_time_s']-a['source_time_s'] for a,b in zip(rows,rows[1:])]
    step=statistics.median(deltas) if deltas else (rows[0]['duration_s'] or (1/fps if fps else None))
    if not step or step<=0: raise ValueError("END_DURATION_UNAVAILABLE")
    end=rows[-1]['source_time_s']+(rows[-1]['duration_s'] or step)
    if sha(path)!=digest: raise ValueError("SOURCE_CHANGED_DURING_PROBE")
    return dict(video_id="video_"+digest[:20],source_path=str(path),original_filename=path.name,
        source_sha256=digest,source_duration_s=end,presentation_start_s=rows[0]['source_time_s'],
        presentation_duration_s=end-rows[0]['source_time_s'],width=width,height=height,
        fps=fps or 1/step,frame_count=len(rows),frame_timeline=rows,time_base=rows[0]['time_base'],codec=codec,
        variable_frame_rate=max(deltas,default=step)-min(deltas,default=step)>1e-6,
        timestamp_policy="NATIVE_PTS; FPS_ONLY_APPROXIMATE_TRANSPORT_METADATA",
        duration_end_policy="LAST_NATIVE_PTS_PLUS_FRAME_DURATION_OR_MEDIAN_DELTA")


def sampling_plan(video, window_seconds=12., cv_fps=5.):
    if not 1<=window_seconds<=120 or not .1<=cv_fps<=30: raise ValueError("SAMPLING_OUT_OF_RANGE")
    pts=[r['source_time_s'] for r in video['frame_timeline']]
    start=pts[0]; end=video['source_duration_s']; windows=[]; lo=0
    for number in range(math.ceil((end-start)/window_seconds)):
        hi=bisect.bisect_left(pts,start+(number+1)*window_seconds)
        if hi>lo:
            indices=choose_uniform8(list(range(lo,hi)),pts)
            windows.append(dict(window_id=f"window_{number+1:04d}",video_id=video['video_id'],
                source_video_sha256=video['source_sha256'],source_frame_interval_closed=[lo,hi-1],
                selected_indices=indices,sampling="NATIVE_PTS_UNIFORM_UP_TO_8_DISTINCT",overlap=False))
        lo=hi
    cv=set();next_time=start
    for i,t in enumerate(pts):
        if t+1e-9>=next_time:
            cv.add(i);next_time=start+(math.floor((t-start)*cv_fps+1e-8)+1)/cv_fps
    cv.add(len(pts)-1)
    cv.update(i for w in windows for i in w['selected_indices'])
    return windows,sorted(cv)


def extract_frames(root, session, video, indices):
    from memory_graph.pass_t.media import require_media
    from PIL import Image
    from .regions import scope
    av=require_media();wanted=set(indices);frames=[]
    with av.open(video['source_path']) as c:
        for i,f in enumerate(c.decode(c.streams.video[0])):
            if i not in wanted: continue
            row=video['frame_timeline'][i]
            if f.pts!=row['pts'] or str(f.time_base)!=row['time_base']:raise ValueError("DECODE_TIMELINE_CHANGED")
            image=f.to_ndarray(format='rgb24');path=session/'evidence'/'source'/f'f{i:08d}.png'
            path.parent.mkdir(parents=True,exist_ok=True);Image.fromarray(image).save(path)
            frames.append(dict(**scope(video,i),frame_id=key(video['source_sha256'],i),
                path=str(path.relative_to(root)),sha256=sha(path),width=video['width'],height=video['height'],
                native_pts_s=row['source_time_s'],model_canvas=[1008,560]))
    if len(frames)!=len(wanted) or sha(video['source_path'])!=video['source_sha256']:raise ValueError("SOURCE_EXTRACTION_INCOMPLETE_OR_CHANGED")
    return frames


def select_localization(frames, observations, category, budget=6):
    if not 0<=budget<=32:raise ValueError("LOCALIZATION_BUDGET_OUT_OF_RANGE")
    detected={f for o in observations if o['source']=='CV' and o['object_category']==category for f in o['source_frame_indices']}
    # Detector extents are not validated support surfaces. Half the budget covers
    # detected objects, half covers misses; both span source time deterministically.
    pools=[[f for f in frames if f['source_frame_index'] in detected],
           [f for f in frames if f['source_frame_index'] not in detected]]
    chosen=[]
    def take(pool,n):
        if not pool or n<=0:return []
        n=min(n,len(pool))
        return [pool[round(k*(len(pool)-1)/max(1,n-1))] for k in range(n)]
    chosen+=take(pools[0],(budget+1)//2)
    chosen+=take(pools[1],budget-len(chosen))
    chosen+=take([f for f in frames if f not in chosen],budget-len(chosen))
    return [dict(f,selection_reason="MISSING_USABLE_SURFACE" if f['source_frame_index'] in detected else "REQUESTED_OBJECT_NOT_DETECTED_AND_SURFACE_UNRESOLVED") for f in sorted(chosen,key=lambda f:f['source_frame_index'])]


def windows_with_frames(windows, frames):
    index={f['source_frame_index']:f for f in frames}
    return [dict(w,frames=[dict(index[i],alias=f"F{k+1:04d}") for k,i in enumerate(w['selected_indices'])]) for w in windows]


def linux_path(path):
    path=Path(path).resolve()
    if os.name!='nt':return str(path)
    return '/mnt/'+path.drive[0].lower()+path.as_posix()[2:]


def run_worker(root, session, stage, timeout):
    start=time.monotonic();log=session/(stage+'.log')
    if stage=='nemotron':
        py=root/'.runtime/nemotron/venv_linux/bin/python'
        args=[linux_path(py),linux_path(root/'scripts/run_findmind_nemotron.py'),'--session',linux_path(session)]
        command=['wsl','-d','Ubuntu','--exec',*args] if os.name=='nt' else args
    else:command=[sys.executable,'-X','utf8','-B',str(root/'scripts/run_findmind_video.py'),'--worker',stage,'--session',str(session)]
    with log.open('x',encoding='utf8') as out:
        process=subprocess.Popen(command,cwd=root,stdout=out,stderr=subprocess.STDOUT)
        try:code=process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Stop only this process tree; do not kill unrelated GPU processes.
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
            else:process.kill()
            process.wait();code=-9
    return dict(stage=stage,status='COMPLETE' if code==0 else 'FAILED',exit_code=code,
        elapsed_s=time.monotonic()-start,log=str(log.relative_to(root)),
        error=None if code==0 else 'WORKER_FAILURE_OR_TIMEOUT; inspect log; successful artifacts retained')


def session_cv(root, session, video):
    tracks_path=session/'cv/tracks.json'
    if not tracks_path.exists():return []
    ledger=read(session/'cv/identity_guard.json')
    return adapt_cv(read(tracks_path),ledger,video,dict(tracks=str(tracks_path),identity=str(session/'cv/identity_guard.json'),
        detector_model_sha256=read(session/'cv/configuration.json')['model_sha256']))


def assemble_memory(root, session, manifest):
    from .pipeline import build_memory,decide,group_candidates
    from .spatial import enrich_memory
    from .regions import propose_regions
    from .target_surface import integrate,parse
    import cv2
    video=manifest['video'];frames=manifest['frames'];observations=session_cv(root,session,video)
    hypotheses=[];receipts=[];errors=[]
    for w in manifest['windows']:
        raw=session/'vlm'/w['window_id']/'raw.txt'
        if not raw.exists():continue
        try:
            o,h,r=adapt_nemotron(raw.read_text(encoding='utf8'),w,video,str(raw),root)
            observations+=o;hypotheses+=h;receipts.append(r)
        except Exception as e:errors.append(dict(stage='VLM_ADAPTER',window=w['window_id'],error=str(e)))
    decisions=[decide(h,observations) for h in hypotheses];grouping=group_candidates(decisions)
    base=build_memory(video['video_id'],observations,decisions,receipts,grouping)
    regions=[]
    for f in frames:
        if sha(root/f['path'])!=f['sha256']:raise ValueError('FRAME_INTEGRITY_FAILURE')
        same=[o for o in observations if o['source']=='CV' and o['source_frame_indices']==[f['source_frame_index']]]
        if same:regions+=propose_regions(cv2.imread(str(root/f['path'])),video,f['source_frame_index'],same,f)
    enrich_memory(base,video,regions)
    perception={}
    plan=read(session/'localization/plan.json') if (session/'localization/plan.json').exists() else {'frames':[]}
    for f in plan['frames']:
        folder=session/'localization/perception'/f['frame_id'];raw=folder/'raw.txt'
        if not raw.exists():continue
        parsed,status=parse(raw.read_text(encoding='utf8'),[1008,560])
        if not status['valid']:continue
        refinement=read(folder/'refinements.json') if (folder/'refinements.json').exists() else {}
        for value in refinement.values():
            if value.get('accepted') and sha(root/value['mask_ref']['path'])!=value['mask_ref']['sha256']:
                raise ValueError('MASK_INTEGRITY_FAILURE')
        perception[f['source_frame_index']]=dict(parsed=parsed,raw_ref=str(raw),target_query=manifest['localization_query'],refinements=refinement)
    try:memory=integrate(base,video,frames,perception) if perception else base
    except Exception as e:
        errors.append(dict(stage='LOCALIZATION_INTEGRATION',error=str(e)));memory=base
    memory.metadata.update(fresh_video_version='phase7_v1',session_id=session.name,isolated_session=True,
        original_query=manifest['query'],incomplete_stage_errors=errors,production_memory_written=False,
        candidate_groupings=grouping,perception_coverage='SAMPLED_NATIVE_SOURCE_FRAMES_NOT_EXHAUSTIVE')
    return memory,errors


def search_session(root, session, query, entity_id=None):
    from memory_graph.scene_graph.models import TemporalMemory
    from .pipeline import search
    session=Path(session).resolve();graph=session/'memory_graph.json'
    receipt=read(session/'run_receipt.json')
    if sha(graph)!=receipt['graph_sha256']:raise ValueError('SESSION_GRAPH_HASH_MISMATCH')
    if sha(session/'source_manifest.json')!=receipt['manifest_sha256']:raise ValueError('SESSION_MANIFEST_HASH_MISMATCH')
    memory=TemporalMemory.model_validate(read(graph))
    result=search(memory,query_category(query),entity_id)
    regions={r['region_id']:r for r in memory.metadata.get('scene_regions',[])}
    objects={o['observation_id']:o for o in memory.metadata['observations']}
    frames={f['source_frame_index']:f for f in read(session/'source_manifest.json')['frames']}
    for c in result['candidates']:
        region=regions.get(c['region_id'],{});obj=objects.get(c['object_observation_id'],{})
        c.update(location_label=region.get('region_label','unresolved region'),source_frame=frames.get(c['source_frame_index']),
            object_bbox=obj.get('bbox'),object_mask=obj.get('candidate_mask_ref'),region_polygon=region.get('polygon'),
            region_mask=region.get('mask_ref'))
    result.update(user_query=query,session_id=session.name,query_reloaded_models=False,
        incomplete_stages=[r for r in receipt['stages'] if r['status']!='COMPLETE'],
        temporal_model_outputs=dict(total=len(memory.metadata.get('response_receipts',[])),
            strict_valid=sum(bool(r['validation']['raw']['full_valid']) for r in memory.metadata.get('response_receipts',[])),
            invalid_outputs_are_not_no_event=True),
        perception_claim='Category candidates, not current presence or enrolled identity')
    return result


def render_evidence(root, session, memory, frames):
    from PIL import Image,ImageDraw
    selected={c['source_frame_index'] for c in memory.metadata.get('candidate_location_history',[])}
    plan=session/'localization/plan.json'
    mandatory={f['source_frame_index'] for f in read(plan)['frames']} if plan.exists() else set()
    mandatory.update(i for o in memory.metadata.get('target_localizations',[]) for i in o['source_frame_indices'])
    # Evidence for every selected localization frame plus representative location
    # frames. The original PNGs remain available for all sampled observations.
    others=sorted(selected-mandatory);slots=max(0,24-len(mandatory))
    others=others if len(others)<=slots else [others[round(k*(len(others)-1)/max(1,slots-1))] for k in range(slots)]
    selected=mandatory|set(others)
    paths=[]
    for f in frames:
        if f['source_frame_index'] not in selected:continue
        im=Image.open(root/f['path']).convert('RGB');draw=ImageDraw.Draw(im)
        for r in memory.metadata.get('scene_regions',[]):
            if r['source_frame_index']==f['source_frame_index']:
                draw.line([tuple(p) for p in r['polygon']]+[tuple(r['polygon'][0])],fill='yellow',width=3)
        for o in memory.metadata['observations']:
            if o.get('bbox') and o['source_frame_indices']==[f['source_frame_index']]:
                draw.rectangle(o['bbox'],outline='lime',width=2)
                draw.text(tuple(o['bbox'][:2]),o['object_category']+' candidate',fill='lime')
        im.thumbnail((960,540));panel=Image.new('RGB',(960,600),'black');panel.paste(im,(0,0))
        ImageDraw.Draw(panel).text((10,545),f"f{f['source_frame_index']} native PTS {f['source_time_s']:.6f}s | identity unresolved | surfaces unverified\nCandidate projection only; not proof of current presence or contact",fill='white')
        path=session/'evidence'/f"f{f['source_frame_index']:08d}_annotated.jpg";panel.save(path);paths.append(str(path.relative_to(root)))
    return paths


def process_video(root, path, query, target_category=None, window_seconds=12., cv_fps=5., localization_budget=6):
    from memory_graph.scene_graph.models import TemporalMemory
    if not 0<=localization_budget<=32:raise ValueError('LOCALIZATION_BUDGET_OUT_OF_RANGE')
    started=time.monotonic();category=query_category(target_category or query)
    video=probe_video(path);windows,indices=sampling_plan(video,window_seconds,cv_fps)
    session=root/'artifacts/findmind_sessions'/(video['video_id']+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6])
    session.mkdir(parents=True,exist_ok=False)
    print('SESSION '+str(session),flush=True)
    frames=extract_frames(root,session,video,indices);windows=windows_with_frames(windows,frames)
    manifest=dict(video=video,frames=frames,windows=windows,query=query,target_category=category,
        localization_query='smartphone' if category=='phone' else category,
        config=dict(window_seconds=window_seconds,cv_fps=cv_fps,localization_budget=localization_budget,
                    seed=42,maximum_nemotron_generations=len(windows),no_quality_retries=True),
        sampling_limitations=['Disjoint windows can miss boundary events','Sparse samples are not exhaustive event coverage'],
        created_utc=datetime.now(timezone.utc).isoformat())
    save(session/'source_manifest.json',manifest)
    save(session/'vlm/contract.json',dict(prompt=PROMPT,schema=SCHEMA))
    stages=[dict(stage='ingestion',status='COMPLETE',elapsed_s=time.monotonic()-started)]
    for stage,limit in [('cv',max(300,len(frames)*5)),('nemotron',900+len(windows)*300)]:
        try:receipt=run_worker(root,session,stage,limit)
        except Exception as e:receipt=dict(stage=stage,status='FAILED',error=str(e))
        stages.append(receipt);save(session/(stage+'_stage.json'),receipt);print(json.dumps(receipt),flush=True)
        if receipt.get('exit_code')==-9:break
    cv=session_cv(root,session,video)
    plan=select_localization(frames,cv,category,localization_budget)
    save(session/'localization/plan.json',dict(frames=plan,query=manifest['localization_query'],
        policy='NATIVE_TIME_SPREAD_DETECTED_AND_MISSING_TARGET; NO_CONFIRMED_SUPPORT_SURFACE',budget=localization_budget))
    if any(s.get('exit_code')==-9 for s in stages):
        stages.append(dict(stage='localization',status='NOT_EXECUTED',error='PREVIOUS_PROCESS_TIMEOUT'))
    elif plan:
        for stage in ['localization','sam']:
            try:receipt=run_worker(root,session,stage,600+300*len(plan))
            except Exception as e:receipt=dict(stage=stage,status='FAILED',error=str(e))
            stages.append(receipt);save(session/(stage+'_stage.json'),receipt);print(json.dumps(receipt),flush=True)
            if receipt.get('exit_code')==-9:break
    else:stages.append(dict(stage='localization',status='NOT_EXECUTED',error='ZERO_BUDGET'))
    memory,errors=assemble_memory(root,session,manifest)
    save(session/'observations.json',memory.metadata['observations']);save(session/'event_decisions.json',memory.events)
    save(session/'memory_graph.json',memory.model_dump(mode='json'))
    loaded=TemporalMemory.model_validate(read(session/'memory_graph.json'))
    if loaded.model_dump()!=memory.model_dump():raise ValueError('GRAPH_RELOAD_MISMATCH')
    evidence=render_evidence(root,session,memory,frames)
    if sha(video['source_path'])!=video['source_sha256']:raise ValueError('SOURCE_CHANGED_DURING_PROCESSING')
    receipt=dict(session_id=session.name,source_sha256=video['source_sha256'],stages=stages,
        assembly_errors=errors,elapsed_s=time.monotonic()-started,graph_sha256=sha(session/'memory_graph.json'),
        manifest_sha256=sha(session/'source_manifest.json'),graph_reloaded=True,production_memory_written=False,
        historical_outputs_reused=False,evidence=evidence,source_hashes={str(p.relative_to(root)):sha(p) for p in
            [root/'scripts/run_findmind_video.py',root/'scripts/run_findmind_nemotron.py',*Path(__file__).parent.glob('*.py')]})
    save(session/'run_receipt.json',receipt)
    result=search_session(root,session,query);save(session/'search_result.json',result)
    save(session/'search_integrity.json',dict(search_result_sha256=sha(session/'search_result.json')))
    print(json.dumps(dict(session=str(session),status=result['status'],candidates=len(result['candidates']),
        elapsed_s=receipt['elapsed_s'],stages=[(s['stage'],s['status']) for s in stages]),ensure_ascii=False),flush=True)
    return session,result
