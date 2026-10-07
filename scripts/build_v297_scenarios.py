"""Development-only reviewed scenario definitions, before V297 decision logic."""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib,cv2
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/v297_physical_identity';PREV=ROOT/'outputs/v296_reid';OLD=ROOT/'outputs/v295_reid'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf8')
def intervals(frames,step=6):
    values=sorted(set(frames));out=[]
    for f in values:
        if out and f-out[-1]['end_frame']<=step:out[-1]['end_frame']=f;out[-1]['frames'].append(f)
        else:out.append({'start_frame':f,'end_frame':f,'frames':[f]})
    return out
def main():
    if not (OUT/'baseline/preservation_manifest.json').exists():raise RuntimeError('Preserve first')
    if (OUT/'development_gt/SCENARIOS_FROZEN_BEFORE_POLICY.json').exists():raise FileExistsError('Scenario files already defined')
    positive=read(OLD/'benchmark/positive_observations.json');negative=read(OLD/'benchmark/negative_observations.json');provenance=read(OLD/'benchmark/label_provenance.json');review=read(PREV/'development/visual_review.json')
    sourcehash={str(p.relative_to(ROOT)):sha(p) for p in [OLD/'benchmark/positive_observations.json',OLD/'benchmark/negative_observations.json',OLD/'benchmark/label_provenance.json',PREV/'development/visual_review.json']}
    summaries=[];coverage={};initials=[]
    for i in range(1,10):
        vid=f'test{i}';rows=read(PREV/f'inputs/{vid}/observations.json');frames=read(PREV/f'inputs/{vid}/frames.json');md={r['observation_id']:r for r in rows};identity=read(PREV/f'development/runs/{vid}/identity.json');initial=identity['aliases'][0];initial_oid=initial['evidence_refs'][0]
        pos={x['observation_id'] for x in positive if x['video_id']==vid};neg={x['observation_id'] for x in negative if x['video_id']==vid}
        adjudicated_unknown={'test1':{'raw:231@114'},'test6':{'raw:547@372'},'test4':{'raw:1439@1038'}}.get(vid,set())
        pos-=adjudicated_unknown;neg-=adjudicated_unknown
        reviewed=[x for x in review['confirmations'] if x['video']==vid and x['classification']=='TARGET'];pos.update(x['observation_id'] for x in reviewed)
        events=[]
        for x in reviewed:
            audit=next(a for a in identity['confirmation_audit'] if a['current_observation']==x['observation_id']);fs=[md[oid]['frame'] for oid in audit['observation_ids']]
            events.append({'event_id':f'{vid}:recovery:{x["confirmation_frame"]}','window':[min(fs),x['confirmation_frame']+12],'reviewed_target_observations':[x['observation_id']],
                'automatic_recovery_required':True,'basis':'Original frame/crop manual target review, V296 review sheet hash; V296 decision is not itself GT'})
        # Additional independently reviewed target reappearance intervals, not policy hints.
        late=intervals([md[o]['frame'] for o in pos if md[o]['frame']>initial['confirmation_frame']+90])
        for seg in late:
            previous=max((md[o]['frame'] for o in pos if md[o]['frame']<seg['start_frame']),default=None)
            if previous is not None and seg['start_frame']-previous<=12:continue
            if any(a['window'][0]<=seg['start_frame']<=a['window'][1] for a in events):continue
            known=[o for o in pos if seg['start_frame']<=md[o]['frame']<=seg['end_frame']]
            if len(seg['frames'])>=3 and seg['end_frame']-seg['start_frame']>=12:
                events.append({'event_id':f'{vid}:reviewed_return:{seg["start_frame"]}','window':[seg['start_frame'],seg['end_frame']],
                    'reviewed_target_observations':known,'automatic_recovery_required':True,'basis':'Existing independently reviewed development target observations; not val or runtime labels'})
        knownframes={md[o]['frame'] for o in pos};unknown_frames=[f['frame'] for f in frames if f['candidate_present'] and f['frame'] not in knownframes and not all(r['observation_id'] in neg for r in rows if r['frame']==f['frame'])]
        ambiguous=[{'start_frame':r['start_frame'],'end_frame':r['end_frame'],'identity':'UNKNOWN','basis':'Unreviewed or visually insufficient phone hypothesis; detector/old authorization is not physical GT'} for r in intervals(unknown_frames)]
        absent=intervals([f['frame'] for f in frames if not f['candidate_present']]);target_intervals=intervals([md[o]['frame'] for o in pos]);distractor_intervals=intervals([md[o]['frame'] for o in neg])
        scenario={'video':vid,'video_sha256':sha(ROOT/f'{vid}.mp4'),'stage':'DEFINED_BEFORE_V297_DECISION_LOGIC','scope':'Partial reviewed development identity scenario; all unsupported identities UNKNOWN, not full-frame GT',
            'initial_target_binding':{'observation_id':initial_oid,'frame':initial['confirmation_frame'],'local_track':md[initial_oid]['candidate_id'],'candidate_epoch':initial['candidate_id'],'expected_correct':True,'visual_review_status':'PENDING'},
            'known_target_visibility_intervals':target_intervals,'disappearance_intervals':[{**x,'meaning':'NO_PHONE_DETECTION; actual target visibility UNKNOWN'} for x in absent],
            'reappearance_events':events,'known_target_local_tracks':sorted({md[o]['candidate_id'] for o in pos}),
            'reviewed_target_observation_ids':sorted(pos),'reviewed_distractor_observation_ids':sorted(neg),'known_distractor_intervals':distractor_intervals,
            'genuinely_ambiguous_or_unreviewed_intervals':ambiguous,
            'no_automatic_confirmation_intervals':[{'start_frame':x['start_frame'],'end_frame':x['end_frame'],'restriction':'Do not authorize reviewed distractor observations; UNKNOWN identity must remain unresolved unless independent reviewed physical support is established'} for x in distractor_intervals],
            'expected_unresolved_behavior':{'required':vid=='test9','reason':'Insufficient trustworthy multi-frame long-gap identity evidence, sparse late physical identity review'},
            'pass_criteria':{'initial_binding_correct':True,'reviewed_distractor_authorizations':0,'reviewed_distractor_active_aliases':0,'reviewed_distractor_core_updates':0,
                'all_required_recovery_events':True,'unknown_recovery_confirmation':'UNKNOWN result unless new original-frame review establishes target physical identity','unresolved_requirement_preserved':True},
            'label_provenance':[x for x in provenance if x['video_id']==vid],'original_reviewed_confirmations':reviewed,'source_hashes':sourcehash,'labels_never_read_by_inference':True}
        scenario['adjudicated_unknown_observations']=sorted(adjudicated_unknown)
        scenario['adjudication_basis']='Original review: partial duplicate detection on the same phone is not a distinct physical entity; distant blurred target-shaped object is insufficient identity. Historical labels remain untouched.'
        save(OUT/f'development_gt/{vid}_identity_scenario.json',scenario);summaries.append(scenario);initials.append((vid,md[initial_oid]))
        people=Counter(a['raw_label'] for f in frames for a in f['anchors']);coverage[vid]={'sampled_frames':len(frames),'phone_observations':len(rows),'person_observations':people['person'],'frames_with_person':sum(any(a['raw_label']=='person' for a in f['anchors']) for f in frames),'anchors':dict(people),'camera_source':'Unchanged window_builder.py provides median translation from>=2 local anchors, no reliability guarantee; V297 must add reliability/UNKNOWN policy'}
        points=[md[initial_oid]]+[md[x['observation_id']] for x in reviewed]
        for ids in [pos,neg]:
            candidates=sorted([md[o] for o in ids],key=lambda x:x['frame'])
            if candidates:points.append(candidates[-1])
        unique={p['observation_id']:p for p in points};points=list(unique.values())[:6];sheet=Image.new('RGB',(1050,250*len(points)),(240,240,240));draw=ImageDraw.Draw(sheet);cap=cv2.VideoCapture(str(ROOT/f'{vid}.mp4'))
        for j,r in enumerate(points):
            draw.text((5,j*250+4),f'{vid} original {r["observation_id"]}  source review',fill='black');crop=Image.open(r['raw_crop_path']).convert('RGB');crop.thumbnail((190,215));sheet.paste(crop,(5,j*250+28));cap.set(cv2.CAP_PROP_POS_FRAMES,r['frame']);ok,im=cap.read();assert ok;img=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));img.thumbnail((790,215));sheet.paste(img,(220,j*250+28))
        cap.release();dest=OUT/f'development_gt/review_sheets/{vid}.png';dest.parent.mkdir(parents=True,exist_ok=True);sheet.save(dest)
    overview=Image.new('RGB',(1140,630),(240,240,240));draw=ImageDraw.Draw(overview)
    for j,(vid,r) in enumerate(initials):
        x=j%3*380;y=j//3*210;draw.text((x+5,y+4),f'{vid} initial {r["observation_id"]}',fill='black');im=Image.open(r['raw_crop_path']).convert('RGB');im.thumbnail((360,170));overview.paste(im,(x+5,y+30))
    overview.save(OUT/'development_gt/review_sheets/initial_binding_overview.png');save(OUT/'development_gt/available_evidence_inventory.json',coverage)
    text='# Development Scenario Acceptance — test1–test9\n\nDefined before V297 decision tuning. Reviewed original observations supply labels; previous Guard authorization alone is not new visual proof. Unsupported front/back or missing-source intervals are UNKNOWN. Detector absence is not guaranteed physical disappearance.\n\n'
    text+='| Video | Initial frame | Reviewed target observations | Distractors | Required recovery windows | Expected unresolved |\n|---|---:|---:|---:|---|---|\n'
    for s in summaries:text+=f'| {s["video"]} | {s["initial_target_binding"]["frame"]} | {len(s["reviewed_target_observation_ids"])} | {len(s["reviewed_distractor_observation_ids"])} | {[(e["window"],e["automatic_recovery_required"]) for e in s["reappearance_events"]]} | {s["expected_unresolved_behavior"]["required"]} |\n'
    text+='\nPASS requires correct initial binding, zero reviewed distractor aliases/authorizations/Core, all required recovery windows achieved with reviewed target evidence, and required unresolved behavior. FAIL means a known criterion fails. UNKNOWN means the observed new confirmation cannot be physically identified from the reviewed source. No aggregate 9/9 claim without nine real PASS results. Scenario hashes are sealed after the pending original-frame inspection and before any V297 policy source is written.\n'
    (OUT/'development_gt/DEVELOPMENT_SCENARIO_ACCEPTANCE.md').write_text(text,encoding='utf8');print('Created9 scenario definitions and original review sheets',flush=True)
if __name__=='__main__':main()
