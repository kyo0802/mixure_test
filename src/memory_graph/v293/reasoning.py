"""Pair overlays, observable facts, grounding and the unchanged V29 physical gate."""
import json
import re
import time
from pathlib import Path
import cv2
import numpy as np
from .audit import ROOT, OUT
from memory_graph.v292.vlm_pairs import FACT_KEYS as ORIGINAL_FACTS
from memory_graph.v292.physical import ordered_boundary_transition, relation_verification
from memory_graph.v29.physical_candidates import generate_candidates
from memory_graph.v29.physical_gate import decide as v29_decide

FACT_KEYS=(*ORIGINAL_FACTS,'target_not_observed_after','target_anchor_overlap_increases','target_disappears_after_release')

# Conservative language compatibility, not semantic relabeling of detections.
# A wrong detector hypothesis can cause a false rejection; uncertainty is kept
# unresolved rather than silently accepting a description of a nearby object.
ANCHOR_TERMS={
    'person':('person','people','human','hand','arm','man','woman','boy','girl'),
    'potted plant':('plant','flower','foliage','leaves','orchid','pot'),
    'refrigerator':('refrigerator','fridge','cabinet','drawer','appliance'),
    'sports ball':('ball','basketball','football','soccer','baseball','volleyball'),
    'cell phone':('phone','smartphone','mobile'),
    'bottle':('bottle','flask'), 'chair':('chair','seat','stool'),
    'couch':('couch','sofa'), 'dining table':('table','desk'),
    'tv':('tv','television','screen','monitor'), 'teddy bear':('bear','plush','stuffed','toy'),
}


def anchor_description_compatible(raw_label,description):
    label=str(raw_label or '').lower().strip()
    if not label or label=='unknown':return False
    terms=ANCHOR_TERMS.get(label,(label,))
    return any(re.search(r'\b'+re.escape(term)+r's?\b',str(description),re.I) for term in terms)

def validate_answer(pack,answer):
    bad={'grounding_valid':False,'schema_valid':False,'status':'VLM_SCHEMA_INVALID'}
    if not isinstance(answer,dict) or any(answer.get(k) not in {'YES','NO','UNCERTAIN'} for k in FACT_KEYS):
        return {**bad,'reason':'Missing/invalid observable facts'}
    bad.update(schema_valid=True,status='VLM_GROUNDING_INVALID')
    placeholders=('describe the green highlighted phone','describe only the magenta highlighted object',
                  'cite visible changes','state missing evidence')
    if any(str(answer.get(k,'')).strip().lower() in placeholders for k in
           ('target_visual_description','anchor_visual_description','evidence_summary','uncertainty')):
        return {**bad,'reason':'Copied prompt placeholder is not visual grounding'}
    expected={'subject_reference':pack['target_id'],'anchor_reference':pack['anchor_id'],'event_reference':pack['event_id']}
    if any(answer.get(k)!=v for k,v in expected.items()):return {**bad,'reason':'Wrong target, queried anchor or event'}
    frames={'BEFORE':pack['before_frames'],'DURING':pack['during_frames'],'AFTER':pack['after_frames']}
    if answer.get('evidence_frames')!=frames:return {**bad,'reason':'Frame citations differ from supplied sequence'}
    if any(r['anchor_id']!=pack['anchor_id'] or r['anchor_observation_authorization']['status']!='OBSERVATION_AUTHORIZED' for r in pack['selected_frames']):
        return {**bad,'reason':'Queried anchor is not represented'}
    if any(r['target_observation_authorization']['status']!='OBSERVATION_AUTHORIZED' for r in pack['selected_frames'] if r['phase'] in {'BEFORE','DURING'}):
        return {**bad,'reason':'Target is not represented during the cited transition'}
    if any(answer.get(k)=='NO' for k in ['target_visible_before','target_visible_during','anchor_remains_visible']):
        return {**bad,'reason':'Response contradicts represented highlighted subject/anchor'}
    after=[r for r in pack['selected_frames'] if r['phase']=='AFTER']
    if after and all(r['target_visible_state']=='TARGET_NOT_OBSERVED_WITH_ANCHOR_VISIBLE' for r in after) and answer['target_visible_after']=='YES':
        return {**bad,'reason':'Response describes another object as the target after non-observation'}
    if not re.search(r'phone|smartphone|mobile',str(answer.get('target_visual_description','')),re.I):
        return {**bad,'reason':'Subject description does not ground to a phone'}
    if not str(answer.get('anchor_visual_description','')).strip():return {**bad,'reason':'Missing queried-anchor visual description'}
    if not anchor_description_compatible(pack['anchor'].get('raw_label'),answer['anchor_visual_description']):
        return {**bad,'reason':'Anchor description incompatible with detector hypothesis; semantic uncertainty unresolved'}
    return {'status':'VLM_GROUNDING_VALID','schema_valid':True,'grounding_valid':True,
        'target_id':pack['target_id'],'anchor_key':pack['anchor_id'],'event_id':pack['event_id'],
        'evidence_frames':frames,'grounding_limit':'Automatic consistency validation; not independent human ground truth'}

def prompt(pack):
    frames={'BEFORE':pack['before_frames'],'DURING':pack['during_frames'],'AFTER':pack['after_frames']}
    template={'subject_reference':pack['target_id'],'anchor_reference':pack['anchor_id'],
        'event_reference':pack['event_id'],'evidence_frames':frames,
        **{k:'YES|NO|UNCERTAIN' for k in FACT_KEYS},'target_visual_description':'',
        'anchor_visual_description':'','evidence_summary':'','uncertainty':''}
    return ('These images are ordered in time, each labeled with phase and original frame number. '
        'GREEN identifies the phone target; MAGENTA identifies exactly one queried anchor. '
        f'The anchor detector raw class is {pack["anchor"].get("raw_label","unknown")}; its class may be uncertain. '
        'Describe only this highlighted pair, never another phone or another object. '
        'A missing GREEN box AFTER means target not observed with anchor visible, NOT physical absence. '
        'Return observable visual facts only; do not name a final physical relation or infer hidden objects. '
        'Choose one of YES, NO, UNCERTAIN separately for each fact from the images; do not copy schema placeholders. '
        'Fill descriptions with visible appearance of the GREEN phone and MAGENTA anchor, plus an evidence summary and uncertainty. '
        'Keep IDs and frame arrays exactly as supplied. '
        'Return only one JSON object using this schema: '+json.dumps(template))

def dispatch(pack,images,call):
    if pack['eligibility_status']!='ELIGIBLE':
        return {'status':'VLM_NOT_CALLED','grounding_valid':False,'schema_valid':False,'called':False,
            'evidence_status':'EVIDENCE_UNAVAILABLE','reason':pack['failure_reason']}
    started=time.monotonic();raw=None;question=prompt(pack)
    try:
        raw=call(images,question)
        match=re.search(r'\{.*\}',raw or '',re.S)
        answer=json.loads(match.group(0)) if match else None
        result=validate_answer(pack,answer)
    except (ValueError,TypeError) as exc:
        answer=None;result={'status':'VLM_SCHEMA_INVALID','schema_valid':False,'grounding_valid':False,'reason':str(exc)}
    except Exception as exc:
        answer=None;result={'status':'VLM_RUNTIME_FAILED','schema_valid':False,'grounding_valid':False,'reason':f'{type(exc).__name__}: {exc}'}
    return {**result,'called':True,'raw_output':raw,'observable_facts':answer,'prompt':question,
        'runtime_seconds':time.monotonic()-started,'images':[str(p) for p in images]}

class LocalVLM:
    def __init__(self):self.backend=None
    def __call__(self,images,question):
        if self.backend is None:
            from types import SimpleNamespace
            from memory_graph.vlm.local_backend import LocalBackend
            self.backend=LocalBackend(SimpleNamespace(device='cuda',cpu_threads=4,cache_dir=str(OUT/'.vlm_cache'),
                revision='main',local_files_only=True,model=str(ROOT/'.models/Qwen2.5-VL-3B-Instruct'),
                load_in_4bit=False,max_new_tokens=768,image_longest_edge=800,max_inference_seconds=120,
                ground_entities_individually=False))
        from PIL import Image
        loaded=[]
        for p in images:
            with Image.open(p) as im:loaded.append(im.convert('RGB'))
        return self.backend._generate(loaded,question,768)

def render_pack(video,pack,folder,contact_sheet=False):
    selected=pack['selected_frames'];folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    if not selected:return []
    boxes=[r[k] for r in selected for k in ('target_bbox','anchor_bbox') if r.get(k)]
    crop=[min(b[0] for b in boxes)-60,min(b[1] for b in boxes)-60,max(b[2] for b in boxes)+60,max(b[3] for b in boxes)+60]
    cap=cv2.VideoCapture(str(ROOT/f'{video}.mp4'));paths=[];panels=[]
    try:
        for n,r in enumerate(selected):
            cap.set(cv2.CAP_PROP_POS_FRAMES,r['frame']);ok,im=cap.read()
            if not ok:raise OSError(f'Could not read {video} frame {r["frame"]}')
            h,w=im.shape[:2];x0,y0,x3,y3=max(0,int(crop[0])),max(0,int(crop[1])),min(w,int(crop[2])),min(h,int(crop[3]))
            for box,color,label in [(r.get('target_bbox'),(0,255,0),'phone_01'),(r['anchor_bbox'],(255,0,255),'queried anchor')]:
                if box:
                    x1,y1,x2,y2=map(int,box);cv2.rectangle(im,(x1,y1),(x2,y2),color,3)
                    cv2.putText(im,label,(x1,max(18,y1-7)),cv2.FONT_HERSHEY_SIMPLEX,.55,color,2)
            im=im[y0:y3,x0:x3]
            scale=min(760/max(1,im.shape[1]),420/max(1,im.shape[0]));im=cv2.resize(im,None,fx=scale,fy=scale)
            canvas=np.zeros((500,800,3),dtype=np.uint8);canvas[40:40+im.shape[0],:im.shape[1]]=im
            cv2.putText(canvas,f"{video} {r['phase']} f{r['frame']}",(12,24),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),1)
            cv2.putText(canvas,r['target_visible_state'],(12,482),cv2.FONT_HERSHEY_SIMPLEX,.48,(255,255,255),1)
            path=folder/f'{n:02d}_{r["phase"]}_f{r["frame"]}.jpg'
            if not cv2.imwrite(str(path),canvas):raise OSError(path)
            paths.append(path);panels.append(cv2.resize(canvas,(480,300)))
    finally:cap.release()
    if contact_sheet:
        while len(panels)%3:panels.append(np.zeros_like(panels[0]))
        sheet=np.vstack([np.hstack(panels[i:i+3]) for i in range(0,len(panels),3)])
        cv2.imwrite(str(folder/'contact_sheet.jpg'),sheet)
    return paths

def evaluate_gate(video,event,pack,vlm,rows,masks,size):
    if not vlm.get('grounding_valid') or pack['eligibility_status']!='ELIGIBLE':return []
    key=pack['anchor_id'];selected=pack['selected_frames'];scene=selected[0]['scene_continuity']['segment']
    lo,hi=min(r['frame'] for r in selected),max(r['frame'] for r in selected)
    projected=[];authorized_masks={}
    for r in rows:
        if not lo<=r['frame']<=hi or r['scene_segment']!=scene:continue
        valid=r['target_authorization']['geometry_usable'] and r.get('chain_id')==pack['continuity_chain_id']
        anchors=[{**a,'entity_id':key,'label':a['raw_label']} for a in r['anchors'] if a['anchor_key']==key and a['authorized']]
        projected.append({**r,'identity_authorized':valid,'anchors':anchors,
            'sam_phone':r.get('sam_phone') if valid else None})
        if valid and str(r['frame']) in masks:authorized_masks[str(r['frame'])]=masks[str(r['frame'])]
    candidates=generate_candidates(video,event,{'rows':projected},authorized_masks,size)
    decisions=[]
    for c in candidates:
        c['candidate_id']=f"{event['event_id']}:{key.split('::')[-1]}:{c['candidate_relation']}"
        last=c['features']['last_frame']
        post=[r for r in projected if r['frame']>last and r['anchors'] and r['view_ok'] and r['scene_ok']
              and r['target_visible_state']=='NOT_OBSERVED' and not r['sam_present'] and not r['phone_candidates']]
        c['features']['post_anchor_without_target']=len(post)
        c['features']['target_disappears_after']=len(post)>=2
        geometry=[]
        from .evidence import _iou
        for r in projected:
            geometry.append({'frame':r['frame'],'target_authorized':r['identity_authorized'],
                'target_bbox':r.get('target_bbox'),'anchors':r['anchors'],
                'contact':bool(r.get('target_bbox') and any(_iou(r['target_bbox'],a['bbox'])>0 for a in r['anchors']))})
        c['ordered_boundary_transition']=ordered_boundary_transition(geometry,key)
        c['provenance']=[f'outputs_v293/{video}/pair_evidence_packs.json#{key}',
            f'outputs_v293/{video}/events/{event["event_id"]}/observation_rows.json']
        verification=relation_verification(c,vlm['observable_facts'],vlm)
        result=v29_decide(c,verification)
        decisions.append({**result,'features':c['features'],'grounding_status':vlm['status'],
            'observation_authorized':True,'identity_write_authorized':False,
            'legacy_feature_boolean_scope':'identity_authorized adapter field means usable observation geometry only; never persisted as identity'})
    return decisions
