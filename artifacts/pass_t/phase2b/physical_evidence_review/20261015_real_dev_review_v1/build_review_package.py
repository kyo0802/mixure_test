"""CPU-only, existing sampled evidence -> offline review derivatives. No ML imports."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json, hashlib, html, textwrap, collections, datetime, re, os
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
RUN=ROOT/'artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f'
EXPECTED='b7929b0e6ecaa651d7a316e838efe0b4c6437920a93b5b33bf41b6ce34740c9d'
EVENT_IDS=[1,3,4,8,10]
ALL_IDS=[1,2,3,4,8,10]
HYPOTHESES=[]; LIMITATIONS=[]; SOURCES={}; RECORDS={}
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v): return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf-8')
def rel(p): return Path(p).resolve().relative_to(ROOT).as_posix()
def href(p,base=OUT): return Path(os.path.relpath(Path(p).resolve(),Path(base).resolve())).as_posix()
def esc(v): return html.escape(str(v),quote=True)
def dump(p,v):
    p=OUT/p;p.parent.mkdir(parents=True,exist_ok=True)
    assert p.resolve().is_relative_to(OUT)
    with p.open('w',encoding='utf-8',newline='\n') as f: f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def write(p,v):
    p=OUT/p;p.parent.mkdir(parents=True,exist_ok=True)
    assert p.resolve().is_relative_to(OUT)
    with p.open('w',encoding='utf-8',newline='\n') as f:f.write(v)
def register(p,expected=None,role='source'):
    p=Path(p);key=rel(p)
    observed=sha(p) if p.is_file() else None
    status='MISSING' if observed is None else ('VERIFIED' if expected and observed==expected else 'HASH_MISMATCH' if expected else 'OBSERVED_HASH_ONLY')
    value={'path':key,'absolute_path':str(p),'recorded_sha256':expected,'observed_sha256':observed,'status':status,'role':role}
    if key not in SOURCES or expected:SOURCES[key]=value
    if status in ('MISSING','HASH_MISMATCH'):LIMITATIONS.append(value)
    return value
def image_link(p,label,base=OUT):return f'<a href="{esc(href(p,base))}" target="_blank">{esc(label)}</a>'
def pretty(v):return json.dumps(v,ensure_ascii=False,indent=2)

assert ROOT.name=='mixure_test_SAM'
bundle=read(RUN/'frozen_bundle.json'); draft=bundle['protocol']['draft']
assert hashlib.sha256(canonical(bundle['protocol'])).hexdigest()==EXPECTED==bundle['freeze_receipt']['protocol_sha256']
assert hashlib.sha256(canonical(draft)).hexdigest()==bundle['freeze_receipt']['draft_sha256']
run_receipt=read(RUN/'run_receipt.json');auth=read(RUN/'authorization_use.json')
assert run_receipt['worker_exit_code']==0 and run_receipt['stop_reason'] is None and not run_receipt['missing_call_ids']
assert len(draft['run_order'])==18
# Preservation scope: the original pilot directory and all pinned components.
for p in RUN.rglob('*'):
    if p.is_file():register(p,role='historical_pilot')
for path,expected in draft['components_sha256'].items():register(ROOT/path,expected,'frozen_component')
protocol_parent=ROOT/'artifacts/pass_t/phase2b/v1d_protocols/3f10dfb6bdb03ae2209745e87467d2ad0d1af84502c03eccdbc8dc2e27bd189a'
for p in protocol_parent.rglob('*'):
    if p.is_file():register(p,role='frozen_protocol_and_receipt')
for p in (ROOT/'artifacts/pass_t/phase2b/v1d_freeze_approvals/20261015_reviewer_0_c799b5d13a77').rglob('*'):
    if p.is_file():register(p,role='human_freeze_record')
old_manifest=read(RUN/'report_v1_20261015/DELIVERABLE_HASHES.json')
for path,expected in old_manifest.items():register(ROOT/path,expected,'historical_manifest_entry')
eligibility_path=ROOT/'artifacts/pass_t/phase2b/readiness/eligibility.json'
eligibility=read(eligibility_path);register(eligibility_path,role='approved_eligibility')
gt_path=ROOT/eligibility['authority']['dataset_path'];register(gt_path,role='approved_GT_read_only')
gt=read(gt_path)
for folder in ['artifacts/pass_t/phase2a/v2/exhaustive_reviews/adjudicated_7e28b9edf80a8e4da88caa66',
               'artifacts/pass_t/phase2a/v2/contracts']:
    for p in (ROOT/folder).rglob('*'):
        if p.is_file():register(p,role='GT_sidecar_or_frozen_policy')
names={'PT2A_eb60192e6986cb4f':'test5 W05','PT2A_c58b4df88a2f6801':'test7 W05'}
windows={w['item_id']:w for w in draft['windows'] if w['item_id'] in names}
metadata={}
for wid,w in windows.items():
    register(ROOT/w['source_metadata_path'],w['source_metadata_sha256'],'native_PTS_metadata')
    metadata[wid]=read(ROOT/w['source_metadata_path'])
    register(ROOT/w['storyboard_media']['path'],w['storyboard_media']['sha256'],'original_storyboard')
    # Metadata only; the full movie is never opened or hashed during this task.
    for m in w['selected']:register(ROOT/m['source_path'],m['recorded_source_png_sha256'],'existing_sampled_PNG')

for cid in ALL_IDS:
    folder=RUN/f'call_{cid:02d}'; c=read(folder/'call_receipt.json');rt=read(folder/'runtime_receipt.json')
    call=c['call'];w=windows[call['item_id']]; pred=c['classification']['prediction']
    raw_info=register(folder/'raw_output.txt',c['raw_sha256'],'unchanged_raw_output')
    register(folder/'runtime_receipt.json',c['runtime_receipt_sha256'],'original_runtime_receipt')
    assert c['protocol_sha256']==EXPECTED and c['execution_authorization_sha256']==run_receipt['authorization_sha256']
    if cid in EVENT_IDS:
        assert len(pred['events'])==1 and pred['events'][0]['event_type']=='PICKUP'
        assert c['classification']['classification']=='STRICT_INVALID' and c['classification']['authoritative_prediction'] is None
    else:assert cid==2 and pred['window_outcome']=='NO_CONFIRMED_EVENT' and c['classification']['stages']['FULL_STRICT']=='PASS'
    event=pred['events'][0] if pred['events'] else None
    event_cites=set(event['cited_frame_aliases']) if event else set()
    window_cites=set(pred.get('window_cited_frame_aliases',[]))
    before=event.get('before_state',{}).get('supporting_frame_alias') if event else None
    after=event.get('after_state',{}).get('supporting_frame_alias') if event else None
    timing=event.get('timing',{}) if event else {}
    timing_aliases={v for k,v in timing.items() if k.endswith('frame_alias') and isinstance(v,str)}
    refs=event_cites|window_cites|({before} if before else set())|({after} if after else set())|timing_aliases
    last_alias=pred.get('last_directly_supported_state',{}).get('supporting_frame_alias')
    if last_alias:refs.add(last_alias)
    mapping=c['provenance']['frame_alias_mapping'];seq=[]
    map_equal=mapping==w['selected'] or all(all(m.get(k)==f.get(k) for k in f) for m,f in zip(mapping,w['selected'])) and len(mapping)==len(w['selected'])
    assert len(mapping)==8
    unit_map=rt.get('alias_unit_mapping',[])
    for i,m in enumerate(mapping):
        sm=metadata[call['item_id']]['frames'][w['positions'][i]]
        matches={'call_vs_frozen_mapping':map_equal,'native_PTS':sm['source_timestamp_s']==m['native_source_pts_s'],
                 'source_frame_id':sm['frame_id']==m['source_frame_id'],
                 'source_path':sm['image_path']==m['source_path'],
                 'recorded_source_hash':sm['sha256']==m['recorded_source_png_sha256'],
                 'source_frame_index':sm['source_frame_index']==m['source_frame_index'],
                 'within_approved_bounds':w['window_boundaries']['half_open_frames'][0]<=m['source_frame_index']<w['window_boundaries']['half_open_frames'][1]}
        info=register(ROOT/m['source_path'],m['recorded_source_png_sha256'],'existing_sampled_PNG')
        tags=[];a=m['supplied_alias']
        if a in event_cites:tags.append('EVENT CITE')
        if a in window_cites:tags.append('WINDOW CITE')
        if a in timing_aliases:tags.append('TIMING CLAIM')
        if a==before:tags.append('BEFORE CLAIM')
        if a==after:tags.append('AFTER CLAIM')
        units=[u['unit'] for u in unit_map if a in u['aliases']]
        available=info['status']=='VERIFIED' and all(matches.values())
        seq.append({**m,'sample_order_1based':i+1,'authorized_window_index_0based':w['positions'][i],
                    'alias_number_in_window_1based':w['positions'][i]+1,'source_file':info,
                    'verification_checks':matches,'available_for_display':available,'claim_roles':tags,
                    'recorded_temporal_unit_0based':units[0] if len(units)==1 else None})
        if not all(matches.values()):LIMITATIONS.append({'call_id':cid,'alias':a,'mapping_checks':matches})
    unresolved=sorted(refs-{m['supplied_alias'] for m in mapping})
    if unresolved:LIMITATIONS.append({'call_id':cid,'unresolved_aliases':unresolved})
    source_order_ok=all(seq[i]['native_source_pts_s']<seq[i+1]['native_source_pts_s'] for i in range(7))
    assert source_order_ok
    original_fields={'window_outcome':pred['window_outcome'],'event':event,'window_uncertainty':pred.get('uncertainty'),
                     'window_rationale':pred.get('rationale'),'window_cited_frame_aliases':pred.get('window_cited_frame_aliases'),
                     'last_directly_supported_state':pred.get('last_directly_supported_state')}
    record={'call_id':cid,'window':names[call['item_id']],'item_id':call['item_id'],'representation':call['representation'],
            'protocol_sha256':EXPECTED,'run_path':rel(RUN),'authorization_sha256':run_receipt['authorization_sha256'],
            'raw_output_source':raw_info,'call_receipt_path':rel(folder/'call_receipt.json'),
            'runtime_receipt_path':rel(folder/'runtime_receipt.json'),'original_fields':original_fields,
            'original_validation':c['classification']['validation'],'original_stages':c['classification']['stages'],
            'classification':'STRICT_INVALID_DESCRIPTIVE_ONLY' if event else 'STRICT_VALID_NO_CONFIRMED_EVENT_COMPARATOR',
            'referenced_aliases':sorted(refs),'unresolved_aliases':unresolved,'sampled_sequence':seq,
            'source_order_verified':source_order_ok,'storyboard_source':SOURCES[rel(ROOT/w['storyboard_media']['path'])],
            'processor_metadata':{k:rt[k] for k in ['input_image_dimensions','resized_dimensions_hw','grids','processor_frame_count',
               'processor_selected_indices','alias_unit_mapping','actual_model_positions','representation_status','source_rgb_sha256',
               'rendered_prompt_sha256','tensor_records','static_timeline','processor_fps','second_per_grid_ts','native_pts_model_visible'] if k in rt},
            'human_adjudication':'UNREVIEWED'}
    RECORDS[cid]=record
    if event:HYPOTHESES.append(record)
dump('SOURCE_PRESERVATION_BASELINE.json',SOURCES)

# Presentation derivatives only: no crops, new sampling, masks, model inference or attention visualization.
fontpath=Path('C:/Windows/Fonts/arial.ttf')
font=lambda n:ImageFont.truetype(str(fontpath),n)
def wrap(draw,text,font,width):
    lines=[]
    for para in text.split('\n'):
        line=''
        for word in para.split():
            trial=(line+' '+word).strip()
            if draw.textlength(trial,font=font)>width and line:lines.append(line);line=word
            else:line=trial
        lines.append(line)
    return lines
def sheet(cid):
    r=RECORDS[cid];event=r['original_fields']['event'];claim=event['rationale'] if event else 'NO_CONFIRMED_EVENT (comparison only; not an event hypothesis)'
    width=2400;header=250;footer=180;tile_w=600;tile_h=455;h=header+2*tile_h+footer
    im=Image.new('RGB',(width,h),'#101827');d=ImageDraw.Draw(im)
    d.text((24,18),f"Call {cid:02d} | {r['window']} | {r['representation']}",font=font(32),fill='white')
    for j,line in enumerate(wrap(d,'MODEL CLAIM (unchanged): '+claim,font(24),width-48)):d.text((24,65+j*30),line,font=font(24),fill='#fff1b8')
    d.text((24,136),'STRICT INVALID - DESCRIPTIVE ONLY; physical evidence UNREVIEWED' if event else 'STRICT VALID NO_CONFIRMED_EVENT - comparator; physical evidence UNREVIEWED',font=font(23),fill='#ffad9c' if event else '#a4e6cc')
    native=r['representation']=='NATIVE_VIDEO_ARRAY'
    d.text((24,175),'FRAME_MATCHED_ONLY - 8 source frames / 4 temporal units' if native else 'Exact existing eight source frames, ordered as supplied; display derivatives',font=font(23),fill='#b4cff9')
    d.text((24,211),'Orange = event citation / timing claim | Blue = window citation / state claim | borders are metadata, not adjudication',font=font(19),fill='#d3dcea')
    for j,m in enumerate(r['sampled_sequence']):
        x=j%4*tile_w;y=header+j//4*tile_h
        color='#ffa43a' if any(t in m['claim_roles'] for t in ['EVENT CITE','TIMING CLAIM']) else '#68b6f0' if m['claim_roles'] else '#344458'
        d.rounded_rectangle((x+8,y+6,x+tile_w-8,y+tile_h-6),radius=8,outline=color,width=5)
        label=f"#{j+1} {m['supplied_alias']} | {m['source_frame_id']} | {m['native_source_pts_s']:.6f}s"
        d.text((x+20,y+19),label,font=font(21),fill='white')
        roles=' / '.join(m['claim_roles']) or 'CONTEXT FRAME'
        if native:roles+=f" | UNIT {m['recorded_temporal_unit_0based']}"
        for k,line in enumerate(wrap(d,roles,font(18),tile_w-40)):d.text((x+20,y+49+k*22),line,font=font(18),fill=color if m['claim_roles'] else '#c5d1e3')
        if m['available_for_display']:
            with Image.open(ROOT/m['source_path']) as original:
                original.load();rgb=original.convert('RGB')
            derived=ImageOps.contain(rgb,(tile_w-40,325),Image.Resampling.LANCZOS)
            im.paste(derived,(x+(tile_w-derived.width)//2,y+116+(325-derived.height)//2))
            m['presentation']={'source_dimensions':list(rgb.size),'derivative_display_dimensions':list(derived.size),'cropped':False}
        else:d.text((x+24,y+220),'EVIDENCE UNAVAILABLE - NO SUBSTITUTE',font=font(20),fill='#ffad9c')
    y=header+2*tile_h+10
    text='BEFORE/AFTER are original model claims, not confirmed physical states. '
    text+=pretty({'before':event.get('before_state'),'after':event.get('after_state'),'timing':event.get('timing')}) if event else 'No event predicted by this comparator.'
    # Compact, metadata-only footer; detailed raw claims and structural defects are in the accompanying HTML card.
    if event:text=f"BEFORE CLAIM: {event.get('before_state')}\nAFTER CLAIM: {event.get('after_state')}\nTIMING CLAIM: {event.get('timing')}"
    for j,line in enumerate(wrap(d,text,font(18),width-48)[:4]):d.text((24,y+25*j),line,font=font(18),fill='#d3dcea')
    d.text((24,h-35),'HUMAN REVIEW: UNREVIEWED | Decision: __________  Evidence aliases: __________  Rationale: ____________________',font=font(19),fill='white')
    path=OUT/f'CONTACT_SHEETS/call_{cid:02d}_eight_frames.png';path.parent.mkdir(exist_ok=True);im.save(path)
    return path

for cid in ALL_IDS:sheet(cid)

CATEGORIES=['SUPPORTED_BY_OBSERVED_EVIDENCE','UNSUPPORTED_BY_OBSERVED_EVIDENCE','INDETERMINATE','WRONG_TARGET','INSUFFICIENT_VISUAL_QUALITY']
QUESTIONS=[
 ('Q1_TARGET_IDENTITY','目標身分','目標能否辨識？模型名詞符合影像嗎？是否模糊不清或描述了另一物件？',['IDENTIFIABLE_AND_CONSISTENT','AMBIGUOUS','POSSIBLY_DIFFERENT_OBJECT','NOT_ASSESSABLE']),
 ('Q2_BEFORE','BEFORE 證據','事件前是否直接看見物件由所稱表面支撐？指出 alias；不要將推論當觀察。',['DIRECTLY_OBSERVED','INFERRED_ONLY','NOT_OBSERVED','NOT_ASSESSABLE']),
 ('Q3_AFTER','AFTER 證據','事件後是否直接看見人手持有物件？指出 alias；不要將推論當觀察。',['DIRECTLY_OBSERVED','INFERRED_ONLY','NOT_OBSERVED','NOT_ASSESSABLE']),
 ('Q4_PHYSICAL_TRANSITION','物理轉換','ON_SURFACE → HELD_BY_PERSON 是否可見？有直接 manipulation 證據嗎？是否僅由消失／遮擋推論？其他解釋是什麼？',['DIRECT_TRANSITION_VISIBLE','BRACKETED_STATES_ONLY','DISAPPEARANCE_OR_OCCLUSION_ONLY','ALTERNATIVE_EXPLANATION','NOT_ASSESSABLE']),
 ('Q5_TEMPORAL_SUPPORT','時間支持','citation 支持轉換瞬間，還是只有某狀態？是否只有 before/after bracket？實際瞬間是否未觀察？alias 有效不代表時間主張正確。',['OBSERVED_TRANSITION_TIME','STATE_ONLY','BRACKET_ONLY_MOMENT_UNOBSERVED','CITATION_UNSUPPORTED','NOT_ASSESSABLE']),
 ('Q6_CONTRADICTIONS','矛盾與不確定','before/after、timing 與 rationale 是否一致？指出遮擋、缺失觀察、抽樣間隙或替代解釋。',['NO_CONTRADICTION_IDENTIFIED','CONTRADICTION_IDENTIFIED','IMPORTANT_OBSERVATION_GAPS','NOT_ASSESSABLE'])]
template={'schema_version':'PASS_T_PHASE2B_PHYSICAL_EVIDENCE_HUMAN_REVIEW_V1','protocol_sha256':EXPECTED,
          'review_labels_are_not_GT':True,'allowed_dispositions':CATEGORIES,
          'questions':[{'key':q[0],'title':q[1],'guidance':q[2],'options':q[3]} for q in QUESTIONS],
          'records':[{'call_id':cid,'window':RECORDS[cid]['window'],'representation':RECORDS[cid]['representation'],
                      'reviewer_id':'','disposition':'UNREVIEWED','supporting_frame_aliases':[],
                      'rationale':'','question_answers':{q[0]:{'answer':None,'frame_aliases':[],'notes':''} for q in QUESTIONS},
                      'reviewed_at_utc':None,'raw_output_sha256':RECORDS[cid]['raw_output_source']['observed_sha256']} for cid in EVENT_IDS]}
dump('HUMAN_ADJUDICATION_TEMPLATE.json',template)

css='''body{font:17px/1.6 system-ui,sans-serif;max-width:1500px;margin:0 auto;padding:28px;background:#f4f6fa;color:#172235}h1,h2,h3{line-height:1.25}a{color:#1558b0}nav{display:flex;gap:20px;flex-wrap:wrap}section,.panel,fieldset{background:white;padding:22px;margin:22px 0;border:1px solid #d3dbe8;border-radius:10px}img.sheet{width:100%;height:auto}figure{margin:18px 0}figcaption{font-size:15px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf1f7;padding:16px}table{width:100%;border-collapse:collapse;font-size:15px}th,td{padding:10px;text-align:left;border:1px solid #ced7e4;vertical-align:top;overflow-wrap:anywhere}td.hash{font-size:12px;max-width:260px}.badge{display:inline-block;padding:5px 10px;background:#fff0db;color:#713c00;border-radius:5px}.warning{border-left:6px solid #d67b18;padding:16px;background:#fff6e8}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px}.original img{width:100%;height:auto}.original{background:white;padding:12px;border:2px solid #d2dae7}.cited{border-color:#d77a10}.timing{box-shadow:0 0 0 3px #f8bd6d}.pill{font-size:13px;font-weight:700;color:#8d4900}label{display:block;margin:10px 0}input,select,textarea,button{font:inherit;padding:9px;box-sizing:border-box}input,textarea{width:100%;max-width:100%}textarea{min-height:90px}button{background:#164e9d;color:white;border:0;border-radius:5px;cursor:pointer}button:disabled{background:#a8b2c3}.small{font-size:14px;color:#41536b}details{margin:12px 0}code{overflow-wrap:anywhere}.status{font-weight:bold}'''
write('review.css',css)
js='''"use strict";
const config=JSON.parse(document.getElementById('review-config').textContent);
const form=document.getElementById('human-review');
function aliases(value){return value.trim()?value.trim().split(/[\\s,，]+/).filter(Boolean):[];}
function collect(){const record=structuredClone(config.initial);record.reviewer_id=form.elements.reviewer_id.value.trim();record.disposition=form.elements.disposition.value;record.rationale=form.elements.rationale.value.trim();record.supporting_frame_aliases=aliases(form.elements.supporting_frame_aliases.value);for(const key of config.question_keys){record.question_answers[key]={answer:form.elements[key].value||null,frame_aliases:aliases(form.elements[key+'_aliases'].value),notes:form.elements[key+'_notes'].value.trim()};}return record;}
form.addEventListener('submit',event=>{event.preventDefault();let r=collect();const all=[...r.supporting_frame_aliases,...Object.values(r.question_answers).flatMap(q=>q.frame_aliases)];const bad=all.filter(a=>!config.aliases.includes(a));let message='';if(bad.length)message='無效 aliases：'+bad.join(', ');else if(r.disposition!=='UNREVIEWED'&&(!r.reviewer_id||!r.rationale||!r.supporting_frame_aliases.length||Object.values(r.question_answers).some(q=>!q.answer)))message='完成審閱需要 reviewer ID、總結 rationale、至少一個有效 supporting alias，以及 Q1–Q6 的回答。';if(message){document.getElementById('save-status').textContent=message;return;}r.reviewed_at_utc=r.disposition==='UNREVIEWED'?null:new Date().toISOString();const result={schema_version:config.schema_version,protocol_sha256:config.protocol_sha256,review_labels_are_not_GT:true,source_template_sha256:config.source_template_sha256,records:[r]};const blob=new Blob([JSON.stringify(result,null,2)+'\\n'],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='call_'+String(r.call_id).padStart(2,'0')+'_human_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.getElementById('save-status').textContent='已下載獨立 JSON。請保留檔案；原始 annotations / GT / template 均未改寫。';});
'''
write('review.js',js)
def page(title,body,base=OUT,script=''):
    return '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><link rel="stylesheet" href="'+esc(href(OUT/'review.css',base))+'"></head><body><nav>'+image_link(OUT/'PHYSICAL_EVIDENCE_REVIEW_INDEX.html','審閱首頁',base)+' '+image_link(OUT/'TEST5_W05_REPRESENTATION_COMPARISON.html','test5 比較',base)+' '+image_link(OUT/'TEST7_W05_REPRESENTATION_COMPARISON.html','test7 比較',base)+'</nav><h1>'+esc(title)+'</h1>'+body+script+'</body></html>'
def table(headers,rows):return '<table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table>'
def form_html(cid):
    initial=next(x for x in template['records'] if x['call_id']==cid)
    options='<option value="UNREVIEWED" selected>UNREVIEWED — 尚未人工判定</option>'+''.join('<option>'+x+'</option>' for x in CATEGORIES)
    s='<section><h2>空白人工審定表 — Q1–Q7</h2><p>這是 review labels，不是新 GT。沒有預選物理結論。請以可觀察影像為依據，不以 schema 成敗或既有非完整 GT 代替判斷。</p><form id="human-review"><label>Reviewer ID<input name="reviewer_id" autocomplete="off"></label>'
    for key,title,guidance,opts in QUESTIONS:
        s+=f'<fieldset><legend>{esc(key)}：{esc(title)}</legend><p>{esc(guidance)}</p><label>回答<select name="{key}"><option value="" selected>尚未回答</option>'+''.join('<option>'+x+'</option>' for x in opts)+f'</select></label><label>Supporting aliases（逗號／空白分隔）<input name="{key}_aliases"></label><label>具體觀察、替代解釋與限制<textarea name="{key}_notes"></textarea></label></fieldset>'
    s+='<fieldset><legend>Q7：Human disposition</legend><label>判定<select name="disposition">'+options+'</select></label><label>Supporting frame aliases<input name="supporting_frame_aliases"></label><label>總結 rationale<textarea name="rationale"></textarea></label></fieldset><button type="submit">下載本筆人工審閱 JSON</button><p id="save-status" role="status"></p></form><p class="small">本頁不向伺服器傳送資料、不自動保存。離開前請下載；每筆一個 JSON，請保存在另外的人工作業位置。下載檔案不會自動匯入 GT。</p></section>'
    config={'schema_version':template['schema_version'],'protocol_sha256':EXPECTED,'source_template_sha256':sha(OUT/'HUMAN_ADJUDICATION_TEMPLATE.json'),
            'initial':initial,'aliases':[m['supplied_alias'] for m in RECORDS[cid]['sampled_sequence']],'question_keys':[q[0] for q in QUESTIONS]}
    return s,'<script id="review-config" type="application/json">'+json.dumps(config,ensure_ascii=False).replace('<','\\u003c')+'</script><script src="../review.js"></script>'

for cid in EVENT_IDS:
    rec=RECORDS[cid];base=OUT/'EVENT_REVIEW_CARDS';e=rec['original_fields']['event']
    body='<p class="badge">OUTPUT_CONTRACT_FAILURE：STRICT_INVALID_DESCRIPTIVE_ONLY</p><p class="badge">PHYSICAL_EVIDENCE_ASSESSMENT：UNREVIEWED</p>'
    body+='<h2>原始模型 claim</h2><blockquote>'+esc(e['rationale'])+'</blockquote><pre>'+esc(pretty(rec['original_fields']))+'</pre>'
    body+='<div class="warning">以上是模型原話，不是已驗證的物件身分或事件。單張持有狀態不證明何時何地拿起；首張 observation 不等於事件瞬間。</div>'
    body+='<h2>原始驗證缺陷</h2><pre>'+esc(pretty(rec['original_validation']))+'</pre>'
    native=rec['representation']=='NATIVE_VIDEO_ARRAY'
    if native:body+='<p><strong>FRAME_MATCHED_ONLY — 8 source frames / 4 temporal units</strong></p><pre>'+esc(pretty(rec['processor_metadata']['alias_unit_mapping']))+'</pre><p>此圖不是 attention 或模型內部 visual-token perception 的重現。unit 為原始 receipt 的零基底編號。</p>'
    body+='<figure><a href="'+esc(href(OUT/f'CONTACT_SHEETS/call_{cid:02d}_eight_frames.png',base))+'"><img class="sheet" alt="八張原始 sampled frames 的 display derivative" src="'+esc(href(OUT/f'CONTACT_SHEETS/call_{cid:02d}_eight_frames.png',base))+'"></a><figcaption>點圖可放大。橘框為模型 event citation／timing claim，藍框為其他 window citation／state claim；這些標記不代表人工認定。保持 source aspect ratio，未裁切。</figcaption></figure>'
    body+='<h2>個別原始影格 — 可點選原尺寸</h2><div class="grid">'
    for m in rec['sampled_sequence']:
        classes='original'+(' cited' if m['claim_roles'] else '')+(' timing' if 'TIMING CLAIM' in m['claim_roles'] else '')
        body+=f'<div class="{classes}"><strong>#{m["sample_order_1based"]} {esc(m["supplied_alias"])} · {esc(m["source_frame_id"])}</strong><br>native PTS {m["native_source_pts_s"]:.9f}s<br><span class="pill">{esc(" / ".join(m["claim_roles"]) or "CONTEXT")}</span>'
        if m['available_for_display']:
            link=href(ROOT/m['source_path'],base)
            body+=f'<a href="{esc(link)}" target="_blank"><img loading="lazy" alt="{esc(m["supplied_alias"])} 原始影格" src="{esc(link)}"></a>'
        else:body+='<p>EVIDENCE UNAVAILABLE — 不使用替代影格</p>'
        body+='</div>'
    body+='</div><h2>來源 mapping</h2>'+table(['order','alias','window index (0)','source index','native PTS','roles','status','SHA-256'],[[m['sample_order_1based'],esc(m['supplied_alias']),m['authorized_window_index_0based'],m['source_frame_index'],m['native_source_pts_s'],esc(', '.join(m['claim_roles'])),m['source_file']['status'],f'<code>{m["source_file"]["observed_sha256"]}</code>'] for m in rec['sampled_sequence']])
    if rec['representation']=='STORYBOARD':
        sb=rec['storyboard_source'];p=ROOT/sb['path'];body+='<h2>模型實際使用的既有 storyboard</h2><p>原圖內嵌標籤與排列保留；不是本次新製作的 contact sheet。原圖為 1440×906，3 欄×3 列，依左至右、上至下排列 8 張，第九格留白；每格上方為既有 alias／native PTS 標籤。processor resize／grid 原始記錄見下。</p>'
        if sb['status']=='VERIFIED':body+=f'<a href="{esc(href(p,base))}"><img class="sheet" alt="exact original model storyboard" src="{esc(href(p,base))}"></a>'
        else:body+='<p>STORYBOARD UNAVAILABLE / HASH MISMATCH</p>'
    body+='<details><summary>原始 processor resize / grids / temporal metadata</summary><pre>'+esc(pretty(rec['processor_metadata']))+'</pre></details>'
    if cid in [1,3,4,8]:body+='<section><h2>首影格 timing claim 提醒</h2><p>此 call 宣稱 F0001 發生 PICKUP。F0001 是首個 supplied observation；本套 evidence 沒有更早 sampled observation。請分開檢查 BEFORE、AFTER 及 transition，不能由 alias 排序自動判定事件時間。兩張不同 state 支持的 bracket 也不是已觀察的瞬間。</p></section>'
    if cid==10:body+='<section><h2>F0077 來源確認</h2><p>F0077 是第 6 張 sampled frame、window position 76，來源 S000418、native PTS 13.933333333333334s。它是合法 alias，不是 F0007 的 typo。</p></section>'
    form,script=form_html(cid);body+=form
    body+='<h2>追溯來源</h2><p>Protocol SHA：<code>'+EXPECTED+'</code></p><p>Raw output SHA：<code>'+rec['raw_output_source']['observed_sha256']+'</code></p><p>'+image_link(RUN/f'call_{cid:02d}/raw_output.txt','原始 raw output',base)+' | '+image_link(RUN/f'call_{cid:02d}/call_receipt.json','原始 call receipt',base)+' | '+image_link(RUN/f'call_{cid:02d}/runtime_receipt.json','原始 runtime receipt',base)+' | '+image_link(RUN/'authorization_use.json','原始 execution authorization',base)+' | '+image_link(OUT/'EVIDENCE_PROVENANCE_MANIFEST.json','來源與衍生圖 manifest',base)+'</p>'
    write(f'EVENT_REVIEW_CARDS/call_{cid:02d}.html',page(f"Call {cid:02d} — {rec['window']} — {rec['representation']}",body,base,script))
    dump(f'EVENT_REVIEW_CARDS/call_{cid:02d}.json',rec)

def comparison(title,ids):
    rows=[]
    for cid in ids:
        r=RECORDS[cid];e=r['original_fields']['event']
        link=image_link(OUT/f'EVENT_REVIEW_CARDS/call_{cid:02d}.html',f'Call {cid}') if cid in EVENT_IDS else 'Call 2 comparator（不是第六個事件）'
        rows.append([link,esc(r['representation']),esc(r['original_fields']['window_outcome']),esc(e['rationale']) if e else 'NO_CONFIRMED_EVENT',esc(pretty(e['timing'])) if e else '—',esc(r['classification'])])
    body='<p>同一 window 的 exact eight sampled source frames；圖的標記屬於原始模型 claims，不是人類 event adjudication。</p>'+table(['call','表示','outcome','原始 rationale','timing','contract status'],rows)
    body+='<div class="warning">名詞差異不能單獨證明 WRONG_TARGET；strict-invalid 不能轉成 valid event。Call 2 的 valid NO_CONFIRMED_EVENT 也不自動是 false negative。</div>'
    for cid in ids:
        body+=f'<h2>Call {cid} · {esc(RECORDS[cid]["representation"])}</h2><img class="sheet" alt="call {cid} exact eight frames" src="CONTACT_SHEETS/call_{cid:02d}_eight_frames.png">'
        if cid==2:
            body+='<h3>Call 2 原始完整輸出</h3><pre>'+esc((RUN/'call_02/raw_output.txt').read_text(encoding='utf-8'))+'</pre><p>'+image_link(RUN/'call_02/raw_output.txt','原始 raw')+' | '+image_link(RUN/'call_02/runtime_receipt.json','runtime receipt')+' | '+image_link(RUN/'call_02/call_receipt.json','call receipt')+'</p>'
    write(title+'_REPRESENTATION_COMPARISON.html',page(title+' representation comparison',body))
    md='# '+title+' Representation Comparison\n\n'
    md+='[開啟離線比較頁]('+title+'_REPRESENTATION_COMPARISON.html)\n\n| Call | Representation | Outcome | Exact model rationale | Timing | Contract |\n|---|---|---|---|---|---|\n'
    for cid in ids:
        r=RECORDS[cid];e=r['original_fields']['event']
        md+='| '+ ' | '.join(map(str,[cid,r['representation'],r['original_fields']['window_outcome'],e['rationale'] if e else 'No event claim',e['timing'] if e else '—',r['classification']]))+' |\n'
    md+='\n只比較既有表示的輸出；不宣稱哪個較好。名詞不代表 verified identity。五個事件假說皆 invalid；格式與物理證據分開。\n'
    if 2 in ids:md+='\nCall 2 strict-valid NO_CONFIRMED_EVENT 為 disagreement comparator，不是自動 false negative，也不是第六個 event-bearing hypothesis。\n'
    write(title+'_REPRESENTATION_COMPARISON.md',md)
comparison('TEST5_W05',[1,3,10]);comparison('TEST7_W05',[2,4,8])

limitations='''# Review limitations

- 只顯示既有八張 sampled source frames；沒有完整影片、額外 seek 或新取樣。影格間隙可遮蔽轉換，沒有 prior observation 不能補推 BEFORE。
- 影格 hash/alias/PTS 對上不證明物理事件正確；來源 PTS 是既有 metadata，本次未重新從原始影片驗證時鐘或 movie SHA。
- 一張 held-state 影像不能確立 pickup 時間與位置；不同狀態之間的 bracket 不是直接觀察的 event duration。
- Native FRAME_MATCHED_ONLY：8 source frames / 4 temporal units，不能推稱八個獨立被注意的時間位置；processor resize/grid metadata 也不是 attention 的視覺重現。
- Storyboard 為一張既有帶標籤拼圖；multi-image 為分別供應，native 為 video array。原始 source sequence 相同不等於模型視覺感知相同。
- test5/test7 是 non-exhaustive known PICKUP windows；既有 GT 只是 scoped reference，不能把 unmatched prediction 當 FP，或把 Call 2 當經人工確認的 FN。無 validated PLACEMENT positive。
- 模型 card/phone/ball/object 名詞不可當作 target identity；畫面狀態差異不可自動推定特定因果。
- OUTPUT_CONTRACT_FAILURE 與 PHYSICAL_EVIDENCE_ASSESSMENT 分開：五筆 event-bearing outputs 都是 strict-invalid，沒有修復，不進 authoritative matching。
- 全部五筆 human disposition 都為 UNREVIEWED；套件製作完成不等於 physical PICKUP 正確性已驗證。沒有新 GT、exhaustive list 或正式統計指標。
- HTML 不需網路或外部 JavaScript。原始資產以 repo 相對路徑連結：需保留 repository 結構，單獨移走此目錄會失去原始圖連結。下載 human JSON 是唯一保存方式；不自動寫入 annotations/GT。
'''
write('REVIEW_LIMITATIONS.md',limitations)
context=[]
for row in gt['records']:
    if row['annotation_item_id'] in windows:
        context.append({'annotation_item_id':row['annotation_item_id'],'source':rel(gt_path),
                        'scoring_permission':'KNOWN_EVENT_MATCHING_ONLY','non_exhaustive':True,
                        'original_known_events':row['response']['events'],
                        'interpretation':'Existing scoped reference only; not an adjudication of Qwen claims.'})
dump('SCOPED_GT_REFERENCE.json',{'records':context,'human_adjudication':'UNREVIEWED','source_sha256':sha(gt_path)})

body='<p class="warning">五筆既有 PICKUP hypotheses，全部 STRICT_INVALID_DESCRIPTIVE_ONLY。這是人工 evidence inspection，不是新實驗或自動事件判定。</p><p>逐卡檢查 Q1–Q6，再選 Q7 disposition 並下載 JSON。請保留五個下載檔；本包初始模板仍維持 UNREVIEWED。</p>'
body+=table(['Call','Window','Representation','原始 rationale','Evidence','Human status'],[[image_link(OUT/f'EVENT_REVIEW_CARDS/call_{r["call_id"]:02d}.html',f'Call {r["call_id"]}'),esc(r['window']),esc(r['representation']),esc(r['original_fields']['event']['rationale']),f'{sum(m["available_for_display"] for m in r["sampled_sequence"])}/8 verified','UNREVIEWED'] for r in HYPOTHESES])
body+='<section><h2>先讀這四點</h2><ul><li>Calls 1/3/4/8 宣稱 F0001 發生事件；首個 observation 不證明 transition timing。</li><li>Call 10 的 F0077 是有效 alias，對應第六張 sampled image。</li><li>test5：card / phone / phone；test7：ball / object。只作文字對照，不自動裁定 target error。</li><li>test7 Call 2 strict-valid NO_CONFIRMED_EVENT 僅作比較，不是第六個事件或已確證的 false negative。</li></ul></section>'
body+='<h2>檔案與操作</h2><ul>'+''.join('<li>'+image_link(OUT/f,label)+'</li>' for f,label in [('PHYSICAL_EVIDENCE_REVIEW_REPORT.md','研究摘要'),('HUMAN_ADJUDICATION_TEMPLATE.json','五筆空白人工作業 JSON'),('SCOPED_GT_REFERENCE.json','既有非完整 GT 參考（不代替審定）'),('EVIDENCE_PROVENANCE_MANIFEST.json','來源與 derivative 雜湊'),('REVIEW_LIMITATIONS.md','限制'),('READONLY_PRESERVATION_REPORT.md','只讀保存稽核')])+'</ul><p>請先自行查看全八張與原尺寸圖，再閱讀／填寫各問題。沒有預選 disposition，也不根據模型或 GT 自動填答。</p>'
write('PHYSICAL_EVIDENCE_REVIEW_INDEX.html',page('Phase 2b — 五筆 PICKUP 物理證據人工審閱',body))

# Audit original bytes after rendering; no full movie, extra frames, model weights or CUDA touched.
changed=[]
for path,before in SOURCES.items():
    p=ROOT/path;after=sha(p) if p.is_file() else None
    if after!=before['observed_sha256']:changed.append({'path':path,'before':before['observed_sha256'],'after':after})
status='UNCHANGED_WITHIN_AUDITED_SCOPE' if not changed else 'PRESERVATION_FAILED'
write('READONLY_PRESERVATION_REPORT.md',f'''# Read-only preservation report

Status: **{status}**.

Compared {len(SOURCES)} original files before/after package construction; changed files: {len(changed)}.
Scope includes all historical pilot files, frozen component hashes, freeze/approval receipts, referenced metadata, exact sampled PNGs, original storyboard assets, approved GT dataset and identified policy/sidecar files. Exact list and byte hashes: SOURCE_PRESERVATION_BASELINE.json.
Historical deliverable manifest entries were compared, not regenerated. Source SHA mismatches / missing records: {len(LIMITATIONS)} (see provenance manifest). Full movies/model weights were not opened or rehashed; no full repository preservation claim is made.
Workspace navigation copies are intentionally updated separately and are not immutable execution reports. No inference, GT mutation, validator/runtime change, Memory Graph write, commit or push occurs in this builder.

Changes detected: {pretty(changed)}
''')
summary='| Call | Window | Representation | Timing alias | Exact model rationale | Sequence |\n|---|---|---|---|---|---|\n'
for r in HYPOTHESES:
    e=r['original_fields']['event'];summary+=f'| {r["call_id"]} | {r["window"]} | {r["representation"]} | {e["timing"]} | {e["rationale"]} | {sum(m["available_for_display"] for m in r["sampled_sequence"])}/8 verified |\n'
write('PHYSICAL_EVIDENCE_REVIEW_REPORT.md',f'''# Pass T Phase 2b — Physical Evidence Review Package

更新：2026-10-15。**PASS_T_PHASE2B_PHYSICAL_EVIDENCE_REVIEW_PACKAGE_READY**。

[直接開啟離線人工審閱頁](PHYSICAL_EVIDENCE_REVIEW_INDEX.html)。權威目錄：`{rel(OUT)}`。

## 內容與來源檢查

Exactly 5 event-bearing hypotheses；Call 2 僅是 test7 comparator。五筆 raw outputs 原值、structural defects 與 strict-invalid 身分均保留；五個人類 disposition 全為 **UNREVIEWED**。

{summary}

五筆 sequence 共 40 個 frame references（16 個不同 sampled PNG）；比較用 Call 2 另外引用 test7 的同一組 8 張。來源缺漏／hash mismatch／mapping unresolved 記錄：{len(LIMITATIONS)}。沒有 substitute、新取樣或 full-video decode。
Hash 只驗證既有 sampled assets/receipts；原始 movie SHA、native PTS 的產生流程本次沒有重新從影片驗證。缺少歷史 hash 的檔案以 OBSERVED_HASH_ONLY 標記，不能宣稱獲得歷史認證。

## Citation / timing 重點

- Calls 1/3/4/8 宣稱 F0001 的 EXACT_SUPPLIED_FRAME 是 PICKUP 時間。首張 supplied observation 沒有更早 sampled observation；需人工分辨 transition、狀態與 evidence bracket。
- Call 10 F0077 為合法第 6 張 sampled frame、window index 76，S000418、native PTS 13.933333333333334s。未視為 typo 或修正 alias。
- 卡片完整保留 event/window citations，以及 before/after state supporting aliases，框線標示僅表示模型主張。所有 referenced alias 均逐 call 檢查，不跨視窗混用 F0001。
- 每張 contact sheet 2400×1340，兩列八張、不裁切、標籤置於影像外。HTML 可逐張開啟 original sampled PNG。

## Representation 比較

- [test5 W05：Calls 1/3/10](TEST5_W05_REPRESENTATION_COMPARISON.html)：三種表示都提出 PICKUP；card / phone / phone，前兩個 F0001，Multi-image F0077。全部 strict-invalid，不選最佳表示、不裁定 noun mismatch 的物理錯誤。
- [test7 W05：Calls 2/4/8](TEST7_W05_REPRESENTATION_COMPARISON.html)：Storyboard ball 與 Native object 的 PICKUP 皆 invalid；Multi-image Call 2 為 strict-valid NO_CONFIRMED_EVENT。這是有用的 disagreement，不能自動稱 false negative。
- Storyboard 卡片連結 exact original storyboard、完整 source contact sheet 及 processor resize/grids。Native 明標 FRAME_MATCHED_ONLY — 8 source frames / 4 temporal units，不模擬 attention。

## 格式與物理證據分開

OUTPUT_CONTRACT_FAILURE：五筆 event timing_uncertainty 與 window uncertainty 空字串；Call 10 另有不符合三位數格式的 event ID。保持 invalid，不修復、不進 authoritative matching。
PHYSICAL_EVIDENCE_ASSESSMENT：全為 UNREVIEWED。本包沒有替人類決定事件真偽；schema pass 也不等於 physical correctness。既有 known PICKUP GT 只作 non-exhaustive scoped reference，不產生新事件時間、身分或完整事件清單。

## 人工下一步

1. 在 index 開啟 Calls 1、3、4、8、10，各查看全八張、原尺寸圖與 before/after/timing claims。
2. 依 Q1–Q6 評估目標、支撐面、持有、轉換、時間及不確定；以具體 aliases 引用可見證據。
3. 填 reviewer ID、Q7 disposition、總結 rationale 和 supporting aliases；每張卡下載獨立 human review JSON。五種可選 disposition 均為 review labels，不是新 GT。
4. 檢查兩個 representation comparison 頁，特別是 test7 Call 2；不要把格式與事件判斷混為一談。

## 保存與限制

保存結果：**{status}**；{len(SOURCES)} 個 original files 前後比對，{len(changed)} 變更。[完整範圍](READONLY_PRESERVATION_REPORT.md)、[來源與 derivatives manifest](EVIDENCE_PROVENANCE_MANIFEST.json)、[限制](REVIEW_LIMITATIONS.md)。
未初始化 CUDA、未載入模型、沒有新 VLM generation、沒有完整影片 decode、未改原圖/GT/凍結元件/歷史執行報告；沒有 Memory Graph、commit 或 push。
包裝完成不代表 PICKUP 正確性已驗證。在此停止，等待五筆人工 evidence review。
''')

template_check=read(OUT/'HUMAN_ADJUDICATION_TEMPLATE.json')
assert len(template_check['records'])==5 and all(r['disposition']=='UNREVIEWED' and not r['reviewer_id'] for r in template_check['records'])
assert sorted(r['call_id'] for r in HYPOTHESES)==EVENT_IDS
assert len(list((OUT/'EVENT_REVIEW_CARDS').glob('*.html')))==5
assert len(list((OUT/'CONTACT_SHEETS').glob('*.png')))==6
badlinks=[]
for p in OUT.rglob('*.html'):
    for target in re.findall(r'(?:href|src)="([^"]+)"',p.read_text(encoding='utf-8')):
        target=html.unescape(target)
        if target.startswith(('http:','https:','//')):raise AssertionError('External network dependency')
        resolved=(p.parent/target).resolve()
        # The manifest is written last to avoid circular hashes; verify its links after publication.
        if resolved==OUT/'EVIDENCE_PROVENANCE_MANIFEST.json':continue
        if not target.startswith('#') and not resolved.exists():badlinks.append({'page':rel(p),'target':target})
checks={'status':'PASS' if not changed and not badlinks else 'FAILED','event_hypotheses':5,'comparator_call_ids':[2],
        'event_cards':5,'contact_sheets':6,'unique_source_PNG':len({m['source_path'] for r in HYPOTHESES for m in r['sampled_sequence']}),
        'event_frame_references':40,'verified_event_frame_references':sum(m['available_for_display'] for r in HYPOTHESES for m in r['sampled_sequence']),
        'unresolved_aliases':{str(r['call_id']):r['unresolved_aliases'] for r in HYPOTHESES},'source_limitations':LIMITATIONS,
        'broken_HTML_links':badlinks,'preservation_changed_files':changed,'human_labels':'ALL_UNREVIEWED',
        'new_model_calls':0,'full_video_decodes':0,'CUDA_initialized':False,'GT_written':False,'Memory_Graph_written':False}
dump('PACKAGE_CHECKS.json',checks)
artifact_hashes={rel(p):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='EVIDENCE_PROVENANCE_MANIFEST.json'}
dump('EVIDENCE_PROVENANCE_MANIFEST.json',{'schema_version':'PASS_T_PHASE2B_PHYSICAL_EVIDENCE_REVIEW_PROVENANCE_V1',
     'protocol_sha256':EXPECTED,'execution_authorization_sha256':run_receipt['authorization_sha256'],'run_path':rel(RUN),
     'original_sources':SOURCES,'review_records':RECORDS,'derivative_hashes':{k:v for k,v in artifact_hashes.items() if '/CONTACT_SHEETS/' in k},
     'review_artifact_hashes':artifact_hashes,'limitations':LIMITATIONS,'preservation_status':status,
     'manifest_self_hash':'EXCLUDED_TO_AVOID_SELF_REFERENCE','human_adjudication':'UNREVIEWED'})
assert (OUT/'EVIDENCE_PROVENANCE_MANIFEST.json').is_file()
assert checks['status']=='PASS',pretty(checks)
print(pretty({'status':'PACKAGE_BUILT','output':str(OUT),'checks':checks,'manifest_sha256':sha(OUT/'EVIDENCE_PROVENANCE_MANIFEST.json')}))
