"""Lightweight input-only HTML, contact sheets and editable human annotation files."""
import sys,json,csv,html,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'outputs/current_development/video_event_experiment/.deps')]
from PIL import Image,ImageDraw
OUT=ROOT/'artifacts/pass_t/phase3/three_vlm_full_v1';REVIEW=OUT/'human_review';REVIEW.mkdir(exist_ok=True)
data=json.loads((OUT/'dataset.json').read_text(encoding='utf8'));unique=[w for w in data['windows'] if w['status']=='ELIGIBLE' and not w['duplicate_of']]
def csvwrite(name,fields,rows):
 with (REVIEW/name).open('x',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
def link(p):return html.escape(os.path.relpath(p,REVIEW).replace('\\','/'),quote=True)
video_by_id={v['video_id']:v for v in data['videos']};sections=[];states={}
for w in unique:
 sheet=REVIEW/'contact_sheets'/f'{w["window_id"]}.jpg';sheet.parent.mkdir(exist_ok=True)
 image=Image.new('RGB',(1680,520),'white');draw=ImageDraw.Draw(image)
 for i,f in enumerate(w['frames']):
  im=Image.open(ROOT/f['path']).convert('RGB');im.thumbnail((420,236));x=i%4*420;y=i//4*260;image.paste(im,(x,y+24));draw.text((x+4,y+4),f'{f["alias"]} S{f["source_frame_index"]:06d} {f["native_pts_s"]:.6f}s',fill='black')
  states[(w['video_id'],f['source_frame_index'])]={'video_id':w['video_id'],'video_sha256':w['source_video_sha256'],'source_frame_index':f['source_frame_index'],'native_pts_s':f['native_pts_s'],'image_path':f['path'],'object_id':'','object_class':'','physical_state':'','visibility':'','physical_support_certainty':'','review_status':'UNREVIEWED','reviewer_id':'','notes':''}
 image.save(sheet,quality=90)
 a,b=w['presentation_interval_half_open'];source=Path(video_by_id[w['video_id']]['path'])
 frames=' '.join(f'<a target="_blank" href="{link(ROOT/f["path"])}">{f["alias"]} full PNG</a>' for f in w['frames'])
 sections.append(f'<details id="{w["window_id"]}"><summary>{w["window_id"]} — {a:.3f}–{b:.3f}s — {w["kind"]}</summary><a href="{link(source)}#t={a},{b}">開啟來源影片</a><video controls preload="none" src="{link(source)}#t={a},{b}" width="840"></video><p>{frames}</p><img loading="lazy" width="100%" src="{link(sheet)}"></details>')
csvwrite('states.csv',list(next(iter(states.values())).keys()),states.values())
csvwrite('events.csv',['event_id','video_id','video_sha256','type','object_id','object_class','start_s','end_s','support_source_frames','target_identity_certainty','temporal_coverage_reviewed','review_status','reviewer_id','notes'],[])
coverage=[]
for v in data['videos']:
 coverage.append({'scope_id':v['video_id']+'__FULL_VIDEO','video_id':v['video_id'],'video_sha256':v['sha256'],'start_s':v['native_interval_half_open'][0],'end_s':v['native_interval_half_open'][1],'coverage':'UNREVIEWED','entire_interval_reviewed':'','all_pickup_placement_annotated':'','no_unobservable_gap':'','target_association_resolved':'','ontology':'PICKUP_PLACEMENT_ONLY','review_status':'UNREVIEWED','reviewer_id':'','notes':''})
csvwrite('coverage.csv',list(coverage[0].keys()),coverage)
csvwrite('proposal_review.csv',['model','window_id','event_index','object_description','reviewed_object_id','reviewed_event_group','physical_review_status','before_supported','after_supported','identity_supported','transition_supported','reviewer_id','notes'],[])
csvwrite('object_mapping.csv',['model','window_id','object_description','reviewed_object_id','reviewed_class','review_status','reviewer_id','notes'],[])
intro='''<!doctype html><meta charset="utf-8"><title>FindMind 三模型共同資料人工審閱</title><style>body{font:16px system-ui;max-width:1700px;margin:30px auto}details{border:1px solid #bbb;padding:12px;margin:8px}summary{cursor:pointer}video{display:block}a{margin-right:12px}</style><h1>FindMind：九影片共同證據人工審閱</h1><p>此頁只顯示原始視覺輸入，不顯示模型答案。預設全部 UNREVIEWED，沒有新增人工 GT。</p><p>用文字編輯器或試算表編輯本資料夾的 events.csv、states.csv、coverage.csv、object_mapping.csv、proposal_review.csv。事件需填真正可支持的轉移時間區間、物件、source frame indices、身分確定性及 reviewer ID；state 需逐物件填 ON_SURFACE／HELD_BY_PERSON／OTHER／UNKNOWN、遮擋及支持確定性。同格多物件可新增列。</p><p><b>八張圖片與視窗時間覆蓋不能證明無事件。</b>只有看完完整指定區間、標完所有可確認 PICKUP/PLACEMENT、沒有可能藏事件的不可觀察缺口且目標關聯可判定，才能簽 EXHAUSTIVE_ATTESTED。否則使用 NOT_ATTESTED／INSUFFICIENT_EVIDENCE／UNREVIEWED；不可從 NO_CONFIRMED_EVENT 模型輸出建立負例。完整性只限兩事件 ontology。</p><p>原始標註與本套件分開保存；不要改寫歷史答案。跨窗同一物理事件需使用相同 event_id；模型 proposal 的同一事件群需由人確認 reviewed_event_group，不能僅靠外觀或重疊區間自動認定。</p>'''
(REVIEW/'INDEX.html').write_text(intro+'\n'.join(sections),encoding='utf8')
print('Human review package',len(unique),'contact sheets',len(states),'unique source-frame rows; all UNREVIEWED')
