"""Current development evidence preparation and one-shot clean Qwen execution."""
import time
from pathlib import Path
from collections import Counter
from .common import ROOT,OUT,read,write,sha256,canonical_hash
from .contract import prompt,parse_json
from .validator import DirectReasoningValidator

def freeze_files(folder,paths):
    return {p.relative_to(folder).as_posix():sha256(p) for p in paths if p.is_file()}

def verify_manifest(folder,manifest):
    x=read(manifest);errors=[]
    for rel,digest in x['files'].items():
        p=folder/rel
        if not p.is_file() or sha256(p)!=digest:errors.append(rel)
    for rel,digest in x.get('sources',{}).items():
        if not (ROOT/rel).is_file() or sha256(ROOT/rel)!=digest:errors.append(rel)
    return {'valid':not errors,'files_checked':len(x['files']),'errors':errors}

def source_hashes():
    paths=list((ROOT/'src/memory_graph/reasoning').glob('*.py'))+[ROOT/'src/memory_graph/events/window_builder.py',ROOT/'src/memory_graph/events/development_sources.py',ROOT/'scripts/run_current_pipeline.py',ROOT/'scripts/run_development_eval.py']
    return {p.relative_to(ROOT).as_posix():sha256(p) for p in paths}

def render_frame(image,row,event,contexts,path):
    """Same 800x600 full-scene plus same-frame panels as the clean baseline."""
    from PIL import Image,ImageDraw,ImageFont
    import cv2
    original=Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB));scene=original.resize((768,432))
    canvas=Image.new('RGB',(800,600),(20,20,20));canvas.paste(scene,(16,32));draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',11)
    draw.text((16,8),f"{event['pack_id']} | f{row['frame']} {row['phase']} | T externally assigned",fill='white',font=font)
    w,h=original.size;sx=768/w;sy=432/h;boxes=[]
    if row['identity_authorized']:boxes.append(('T',row['target_bbox'],(0,235,235)))
    lookup={a['anchor_key']:a for a in row['anchors']}
    colors=[(255,170,0),(230,60,235),(70,230,70),(230,80,80),(150,160,255)]
    for i,c in enumerate(contexts):
        if c['key'] in lookup:boxes.append((c['marker'],lookup[c['key']]['bbox'],colors[i]))
    if row.get('mask_reference'):
        p=ROOT/row['mask_reference'];mask=cv2.imread(str(p),cv2.IMREAD_GRAYSCALE)
        if mask is not None:
            overlay=Image.new('RGB',original.size,(0,230,230));masked=Image.composite(Image.blend(original,overlay,.17),original,Image.fromarray(mask))
            canvas.paste(masked.resize((768,432)),(16,32));draw=ImageDraw.Draw(canvas)
    for marker,b,color in boxes:
        bb=(16+b[0]*sx,32+b[1]*sy,16+b[2]*sx,32+b[3]*sy);draw.rectangle(bb,outline=color,width=2)
        draw.rectangle((bb[0],max(32,bb[1]-13),bb[0]+14,max(32,bb[1]-13)+13),fill=color);draw.text((bb[0]+2,max(32,bb[1]-13)),marker,fill='black',font=font)
    for index,marker in enumerate(['T']+[c['marker'] for c in contexts]):
        x=16+index*128;box=next((b for m,b,_ in boxes if m==marker),None);color=next((c for m,_,c in boxes if m==marker),'white')
        draw.text((x,477),marker+' same-frame reference',fill=color,font=font)
        if box:
            crop=original.crop(tuple(max(0,int(v)) for v in box));crop.thumbnail((118,84));canvas.paste(crop,(x,493));draw.rectangle((x,493,x+crop.width,493+crop.height),outline=color)
        else:draw.text((x,514),'UNMARKED',fill='gray',font=font)
    path.parent.mkdir(parents=True,exist_ok=True);canvas.save(path)
    return canvas

def contact_sheet(images,path,event):
    from PIL import Image,ImageDraw,ImageFont
    cols=4;tilew=400;tileh=300;count=len(images);canvas=Image.new('RGB',(cols*tilew,60+((count+cols-1)//cols)*tileh),'#161616');draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    draw.text((12,8),f"{event['pack_id']} {event['trigger']} {event['completeness']}",fill='white',font=font)
    draw.text((12,32),f"{event['start_time']:.2f}-{event['end_time']:.2f}s; images chronological; cyan T only on authorized frames",fill='white',font=font)
    for i,p in enumerate(images):
        with Image.open(p) as im:canvas.paste(im.resize((tilew,tileh)),((i%cols)*tilew,60+(i//cols)*tileh))
    path.parent.mkdir(parents=True,exist_ok=True);canvas.save(path)

def prepare():
    from memory_graph.events.development_sources import inputs,authorized_rows
    from memory_graph.events.window_builder import WindowConfig,target_timeline,select_events,select_context,dense_frames
    import cv2
    if (OUT/'event_windows/builder_freeze.json').exists():raise RuntimeError('Builder already frozen; no tuning/reselection')
    cfg=WindowConfig();write(OUT/'event_windows/config.json',{'initial_global_config':cfg.to_dict(),'general_corrections':0,'representation':'DENSE_ORDERED_EVENT_FRAMES'})
    dev=inputs();events=[];diagnostics=[];candidates=[];started=time.monotonic()
    write(OUT/'event_windows/development_inputs.json',dev)
    for item in dev:
        video=item['video_id'];raw,provenance=authorized_rows(video);rows=target_timeline(raw,cfg)
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
                        if not okay:raise OSError('Development frame decode failed')
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
    metrics={'development_videos':len(dev),'selected_physical_events':len(physical),'complete':counts['COMPLETE_EVENT_WINDOW'],
        'incomplete':counts['INCOMPLETE_EVENT_WINDOW'],'complete_rate':counts['COMPLETE_EVENT_WINDOW']/len(physical) if physical else 0,
        'qwen_eligible':sum(e['physical_reasoning_eligible'] for e in events),'lifecycle_selected':len(events)-len(physical),
        'per_video':diagnostics,'actor_available':sum(e['actor_available'] for e in physical),'location_available':sum(e['location_available'] for e in physical),
        'semantic_placement_release_coverage':'Requires post-freeze visual engineering review; no GT used for selection',
        'identity_writes':0,'new_YOLO_SAM_inference':0,'prepare_seconds':time.monotonic()-started}
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

def run():
    from .model import Backend,Monitor
    if (OUT/'qwen/execution_started.json').exists():raise RuntimeError('Canonical inference already started; no retries')
    check=verify_manifest(OUT,OUT/'event_windows/builder_freeze.json')
    if not check['valid']:raise RuntimeError(check)
    events={e['pack_id']:e for e in read(OUT/'event_windows/event_manifest.json')};requests=read(OUT/'qwen/requests.json')
    write(OUT/'qwen/execution_started.json',{'started_unix':time.time(),'actual_model_calls_planned':len(requests),'retries_allowed':0})
    started=time.monotonic()
    with Monitor() as monitor:backend=Backend()
    loading={'seconds':time.monotonic()-started,**monitor.result()};write(OUT/'qwen/model_config.json',backend.identity())
    validator=DirectReasoningValidator();responses=[];parsed=[];validations=[]
    for req in requests:
        e=events[req['pack_id']]
        if not e['physical_reasoning_eligible'] or req['prompt']!=prompt(e):raise ValueError('Dispatch gate violation')
        if any(sha256(p)!=h for p,h in zip(req['images'],req['image_sha256'])):raise ValueError('Image hash drift')
        print('Qwen',e['pack_id'],len(req['images']),'dense frames',flush=True)
        started=time.monotonic();raw='';answer=None;error=None;backend.last_trace={}
        try:raw=backend(req['images'],req['prompt'],1400);answer=parse_json(raw)
        except Exception as exc:error=type(exc).__name__+': '+str(exc)
        trace={**backend.last_trace,'wall_seconds':time.monotonic()-started};validation=validator.validate(e,answer)
        if not trace.get('ended_with_EOS'):
            validation['valid']=False;validation['errors'].append('INCOMPLETE_GENERATION');validation['status']='INVALID_MODEL_REASONING_OUTPUT'
        responses.append({'pack_id':e['pack_id'],'raw_output':raw,'answer':answer,'error':error,'compute_trace':trace,'actual_inference':True,'retries':0})
        parsed.append({'pack_id':e['pack_id'],'answer':answer});validations.append(validation)
        write(OUT/'qwen/responses.json',responses);write(OUT/'qwen/parsed_outputs.json',parsed);write(OUT/'qwen/validator_results.json',validations)
        print('Completed',round(trace['wall_seconds'],2),answer,validation['errors'],flush=True)
    runtime={'complete':len(responses)==len(requests),'canonical_calls':len(responses),'load':loading,
        'inference_seconds':sum(r['compute_trace']['wall_seconds'] for r in responses),'EOS_count':sum(r['compute_trace'].get('ended_with_EOS',False) for r in responses),
        'runtime_errors':sum(r['error'] is not None for r in responses),'timeouts':sum(not r['compute_trace'].get('ended_with_EOS',False) for r in responses),
        'peak_global_gpu_bytes':max([loading['global_gpu_used_peak_bytes']]+[r['compute_trace'].get('global_gpu_used_peak_bytes',0) for r in responses]),
        'schema_valid':sum(v['schema_valid'] for v in validations),'validator_valid':sum(v['valid'] for v in validations),'retries':0}
    write(OUT/'qwen/runtime.json',runtime)
    write(OUT/'qwen/deterministic_metrics.json',{'event_type_distribution':dict(Counter((r['answer'] or {}).get('event_type','MISSING') for r in responses)),
        'relation_distribution':dict(Counter((r['answer'] or {}).get('final_relation','MISSING') for r in responses)),
        'operational_graph_writes':0,'identity_writes':0,'trusted_bank_writes':0,'Search_Planner_updates':0})
    paths=[p for folder in ['event_windows','qwen'] for p in (OUT/folder).rglob('*') if p.is_file() and not any(part.startswith('.') for part in p.relative_to(OUT).parts)]
    write(OUT/'final/artifact_manifest.json',{'stage':'PREDICTIONS_FROZEN_BEFORE_ENGINEERING_REVIEW','freeze_unix':time.time(),
        'review_started':False,'files':freeze_files(OUT,paths),'sources':source_hashes()})
    return runtime

def verify_reference():
    ref=ROOT/'outputs/reference_qwen';return verify_manifest(ref,ref/'manifest.json')

def verify():
    result=verify_manifest(OUT,OUT/'final/artifact_manifest.json');write(OUT/'final/freeze_verification.json',result);return result
