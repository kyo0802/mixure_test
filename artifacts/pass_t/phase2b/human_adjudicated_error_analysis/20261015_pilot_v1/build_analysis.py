"""CPU-only human-return audit/report; no ML, image decoding or pipeline mutation."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,hashlib,collections,datetime,shutil

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
REVIEW=ROOT/'artifacts/pass_t/phase2b/physical_evidence_review/20261015_real_dev_review_v1'
RUN=ROOT/'artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f'
IDS=[1,3,4,8,10]
PROTOCOL='b7929b0e6ecaa651d7a316e838efe0b4c6437920a93b5b33bf41b6ce34740c9d'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def save(name,value):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:
        f.write(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def table(headers,rows):
    cell=lambda x:str(x).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(map(cell,row))+' |' for row in rows])
def link(p,title):return '['+title+']('+p.as_posix()+')'

assert ROOT.name=='mixure_test_SAM'
now=datetime.datetime.now(datetime.timezone.utc)
manifest=read(REVIEW/'EVIDENCE_PROVENANCE_MANIFEST.json')
template=read(REVIEW/'HUMAN_ADJUDICATION_TEMPLATE.json');template_sha=sha(REVIEW/'HUMAN_ADJUDICATION_TEMPLATE.json')
assert template['protocol_sha256']==PROTOCOL
preservation={}
for path,record in manifest['original_sources'].items():
    p=ROOT/path
    assert p.is_file() and sha(p)==record['observed_sha256'],f'Original-source mismatch: {path}'
    preservation[str(p)]=sha(p)
for path,expected in manifest['review_artifact_hashes'].items():assert sha(ROOT/path)==expected,f'Review artifact mismatch: {path}'
for p in REVIEW.rglob('*'):
    if p.is_file():preservation[str(p)]=sha(p)
inputs={cid:Path(f'C:/Users/smile/Downloads/call_{cid:02d}_human_review.json') for cid in IDS}
for p in inputs.values():preservation[str(p)]=sha(p)
save('SOURCE_PRESERVATION_BASELINE.json',preservation)

resolution={'status':'HUMAN_CONFIRMED_ALIAS','canonical_reviewer_id':'reviewer_0','raw_ids':['reviewer_0','review_0'],
 'scope':'Only the five supplied Phase 2b human review returns; call 3 uses review_0.',
 'human_confirmation_verbatim':'同一位，Call 3 是拼字差異',
 'confirmation_source':'Direct human reply in this task to the reviewer identity clarification.',
 'recorded_at_utc':now.isoformat(),'original_files_modified':False,
 'independent_reviewer_count':1,'interpretation':'One reviewer; not independent multi-rater adjudication.'}
save('REVIEWER_IDENTITY_RESOLUTION.json',resolution)

# These are report-author summaries anchored to explicit submitted text, NOT additional human-selected labels.
themes={
 1:[('TARGET_GROUNDING_WRONG','rationale'),('EXACT_EVENT_TIME_UNSUPPORTED','question_answers.Q5_TEMPORAL_SUPPORT.notes'),('AFTER_STATE_CITATION_CONFLICT','question_answers.Q2_BEFORE.notes + original event.after_state')],
 3:[('EXACT_EVENT_TIME_UNSUPPORTED','question_answers.Q5_TEMPORAL_SUPPORT.notes'),('AFTER_STATE_CITATION_UNSUPPORTED','question_answers.Q3_AFTER.notes')],
 4:[('TARGET_GROUNDING_WRONG','rationale'),('TARGET_AFTER_STATE_UNSUPPORTED','question_answers.Q3_AFTER.notes'),('EXACT_EVENT_TIME_UNSUPPORTED','question_answers.Q5_TEMPORAL_SUPPORT.notes'),('CAMERA_MOVEMENT_IS_NOT_PICKUP_EVIDENCE','question_answers.Q6_CONTRADICTIONS.notes')],
 8:[('TARGET_ASSOCIATION_UNRESOLVED','rationale'),('EXACT_EVENT_TIME_UNSUPPORTED','question_answers.Q5_TEMPORAL_SUPPORT.notes'),('AFTER_STATE_CITATION_UNSUPPORTED','question_answers.Q3_AFTER.notes')],
 10:[('EXACT_EVENT_TIME_UNSUPPORTED','question_answers.Q5_TEMPORAL_SUPPORT.notes'),('BEFORE_STATE_CITATION_WRONG','question_answers.Q2_BEFORE.notes')]
}
warnings={
 1:[{'field':'Q1_TARGET_IDENTITY','issue':'Selected IDENTIFIABLE_AND_CONSISTENT, but notes and final WRONG_TARGET identify a model/object-description inconsistency. Preserve both; do not use Q1 alone to count correct grounding.'},
    {'field':'Q5_TEMPORAL_SUPPORT','issue':'Selected NOT_ASSESSABLE; notes explicitly reject F0001 exact timing. Raw selection remains NOT_ASSESSABLE, not recoded to CITATION_UNSUPPORTED.'}],
 4:[{'field':'Q1_TARGET_IDENTITY','issue':'Selected IDENTIFIABLE_AND_CONSISTENT, but notes and final WRONG_TARGET describe basketball/phone misassociation. Preserve the contradiction.'}],
 8:[{'field':'Q1_TARGET_IDENTITY','issue':'Selected IDENTIFIABLE_AND_CONSISTENT, while notes/rationale retain unresolved explicit target association. This is a scope qualification, not fully validated target binding.'}]
}
records=[];audits=[];question_counts={q['key']:collections.Counter() for q in template['questions']}
for cid in IDS:
    path=inputs[cid];submission=read(path)
    assert submission['schema_version']==template['schema_version']
    assert submission['protocol_sha256']==PROTOCOL and submission['source_template_sha256']==template_sha
    assert submission['review_labels_are_not_GT'] is True and len(submission['records'])==1
    human=submission['records'][0];card=read(REVIEW/f'EVENT_REVIEW_CARDS/call_{cid:02d}.json')
    raw=RUN/f'call_{cid:02d}/raw_output.txt';receipt=read(RUN/f'call_{cid:02d}/call_receipt.json')
    assert human['call_id']==cid and human['window']==card['window'] and human['representation']==card['representation']
    assert human['raw_output_sha256']==sha(raw)==receipt['raw_sha256']
    assert human['reviewer_id']==('review_0' if cid==3 else 'reviewer_0')
    assert human['disposition'] in template['allowed_dispositions']
    assert human['rationale'].strip() and human['supporting_frame_aliases']
    date=datetime.datetime.fromisoformat(human['reviewed_at_utc'].replace('Z','+00:00'))
    assert date.tzinfo is not None and date<=now
    mapping={m['supplied_alias']:m for m in card['sampled_sequence']}
    all_aliases=set(human['supporting_frame_aliases'])
    assert set(human['question_answers'])==set(question_counts)
    for q in template['questions']:
        answer=human['question_answers'][q['key']]
        assert answer['answer'] in q['options'] and answer['notes'].strip()
        assert isinstance(answer['frame_aliases'],list)
        all_aliases.update(answer['frame_aliases']);question_counts[q['key']][answer['answer']]+=1
    assert all_aliases<=set(mapping),f'Unknown aliases call {cid}: {all_aliases-set(mapping)}'
    assert receipt['classification']['stages']['FULL_STRICT']=='FAIL'
    assert receipt['classification']['authoritative_prediction'] is None
    destination=OUT/f'human_submissions/call_{cid:02d}_human_review.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    assert not destination.exists();shutil.copyfile(path,destination);assert sha(path)==sha(destination)
    report_record={'call_id':cid,'window':card['window'],'representation':card['representation'],
       'human_submission_original_path':str(path),'preserved_submission_path':rel(destination),'submission_sha256':sha(path),
       'human_record_unchanged':human,'resolved_reviewer_id':'reviewer_0',
       'reviewer_identity_resolution':rel(OUT/'REVIEWER_IDENTITY_RESOLUTION.json'),
       'model_claim_unchanged':card['original_fields'], 'raw_output_path':rel(raw),'raw_output_sha256':sha(raw),
       'strict_validation_unchanged':receipt['classification']['stages'],
       'structural_errors_unchanged':receipt['classification']['validation']['structural_errors'],
       'authoritative_structured_matching_eligible':False,
       'human_evidence_alias_provenance':{a:{k:mapping[a][k] for k in ['source_frame_id','source_frame_index','source_path','native_source_pts_s','recorded_source_png_sha256','sample_order_1based']} for a in sorted(all_aliases)},
       'report_author_secondary_themes':[{'theme':theme,'source_field':field,'authority':'SUMMARY_OF_SUBMITTED_HUMAN_TEXT_NOT_NEW_ADJUDICATION'} for theme,field in themes[cid]],
       'human_form_consistency_warnings':warnings.get(cid,[])}
    records.append(report_record)
    audits.append({'call_id':cid,'submission_sha256':sha(path),'protocol_binding':'PASS','template_binding':'PASS',
       'call_window_representation_binding':'PASS','raw_output_binding':'PASS','required_human_fields':'PASS',
       'reviewer_identity':'HUMAN_CONFIRMED_ALIAS' if cid==3 else 'EXACT_RECORDED_ID',
       'alias_validation':'PASS','original_copy_bytes':'IDENTICAL',
       'source_text_consistency':'WARN' if warnings.get(cid) else 'NO_FLAG_IDENTIFIED',
       'human_values_corrected':False})

counts=collections.Counter(r['human_record_unchanged']['disposition'] for r in records)
assert counts=={'SUPPORTED_BY_OBSERVED_EVIDENCE':3,'WRONG_TARGET':2}
rep={}
for r in records:
    rep.setdefault(r['representation'],collections.Counter())[r['human_record_unchanged']['disposition']]+=1
theme_counts=collections.Counter(theme for values in themes.values() for theme,_ in values)
save('ADJUDICATION_IMPORT_AUDIT.json',{'status':'PASS_WITH_DISCLOSED_FORM_CONSISTENCY_WARNINGS','protocol_sha256':PROTOCOL,
 'template_sha256':template_sha,'submitted':5,'completed':5,'excluded':0,'unreviewed':0,'canonical_reviewers':1,
 'reviewer_identity_resolution':resolution,'records':audits,'preservation_baseline':rel(OUT/'SOURCE_PRESERVATION_BASELINE.json'),
 'interpretation':'Provenance/format checks do not establish human visual correctness. Warnings retained, not repaired.'})
save('HUMAN_ADJUDICATED_CALLS.json',{'schema_version':'PASS_T_PHASE2B_HUMAN_ADJUDICATED_ERROR_ANALYSIS_V1',
 'protocol_sha256':PROTOCOL,'primary_disposition_counts':dict(counts),
 'question_answer_counts_raw':{k:dict(v) for k,v in question_counts.items()},
 'representation_counts_selected_event_hypotheses':{k:dict(v) for k,v in rep.items()},
 'report_author_secondary_theme_counts':dict(theme_counts),'records':records,
 'no_GT_modified':True,'no_strict_invalid_reclassified':True,'new_model_generations':0,
 'scope':'Five selected strict-invalid event-bearing calls from two non-exhaustive DEV windows; no population metrics.'})

primary_rows=[];dimension_rows=[];details=[]
grounding={1:'人工 WRONG_TARGET：card 與所見 smartphone 不一致',3:'人工認為 phone 與操作目標一致',
 4:'人工 WRONG_TARGET：將 phone 操作歸到 ball',8:'泛稱 object；人工保留 target association 未解',10:'人工認為 phone 與操作目標一致'}
after={1:'模型 F0016 held claim 與人類 F0016 on-surface 描述衝突',3:'模型 F0016 不足；人類引用 F0062/F0077',
 4:'ball HELD_BY_PERSON 未觀察；人類看到 held smartphone',8:'模型 F0016 不足；人類引用 F0031/F0046',10:'F0077 支持 AFTER，不支持 BEFORE 或 exact pickup'}
for r in records:
    h=r['human_record_unchanged'];cid=r['call_id'];e=r['model_claim_unchanged']['event']
    primary_rows.append([cid,r['window'],r['representation'],h['disposition'],', '.join(h['supporting_frame_aliases'])])
    dimension_rows.append([cid,grounding[cid],h['question_answers']['Q5_TEMPORAL_SUPPORT']['answer'],after[cid],'FAIL，維持排除'])
    text=f'### Call {cid} — {r["window"]} / {r["representation"]}\n\n'
    text+=f'**人類原始判定：{h["disposition"]}**；原始 reviewer `{h["reviewer_id"]}`，確認後同一人 `reviewer_0`；提交時間 `{h["reviewed_at_utc"]}`。\n\n'
    text+='模型原話：'+e['rationale']+'\n\n原始 timing：`'+json.dumps(e['timing'])+'`；before：`'+json.dumps(e['before_state'])+'`；after：`'+json.dumps(e['after_state'])+'`。\n\n'
    text+='**人工總結原文（保留限定語）：**\n\n> '+h['rationale']+'\n\n'
    text+=table(['欄位','人工原選項','引用 aliases','人工說明原文'],[[k,v['answer'],', '.join(v['frame_aliases']),v['notes']] for k,v in h['question_answers'].items()])+'\n\n'
    text+='**引用影格來源（只映射既有 PTS，不建立新 GT 時間）：**\n\n'
    text+=table(['Alias','Source frame','Native PTS 秒','Source PNG SHA-256'],[[a,v['source_frame_id'],v['native_source_pts_s'],v['recorded_source_png_sha256']] for a,v in r['human_evidence_alias_provenance'].items()])+'\n\n'
    text+='結構缺陷維持原樣：`'+json.dumps(r['structural_errors_unchanged'],ensure_ascii=False)+'`。\n\n'
    if r['human_form_consistency_warnings']:text+='**保留的人工表單一致性警示：** '+ ' '.join(w['issue'] for w in r['human_form_consistency_warnings'])+'\n\n'
    text+=link(ROOT/r['preserved_submission_path'],'原始人工提交副本')+' | '+link(ROOT/r['raw_output_path'],'原始模型輸出')+' | '+link(REVIEW/f'EVENT_REVIEW_CARDS/call_{cid:02d}.html','歷史證據卡（初始空白表單）')+'\n'
    details.append(text)

report=f'''# Phase 2b — Human-Adjudicated Error Analysis

更新：{now.isoformat()}。**PASS_T_PHASE2B_HUMAN_ADJUDICATED_ERROR_ANALYSIS_COMPLETE**。

權威分析目錄：`{rel(OUT)}`。本報告整理使用者提交的五份人工審閱；不是新 inference、GT 或重新驗證模型輸出。

## 1. 摘要：事件假說有用，但現有輸出還不能直接使用

五筆人工作業全部完成且 provenance 核對通過：**3 筆 SUPPORTED_BY_OBSERVED_EVIDENCE、2 筆 WRONG_TARGET**。其他三種 disposition 與 UNREVIEWED 均為 0。沒有排除提交。

三筆 supported 只表示審閱者支持 physical-event-level PICKUP；不代表目標綁定、精確時間、state citations 或輸出合約全對。五筆全部仍是 strict-invalid；**strict-valid event-bearing predictions 維持 0**，不得回填 authoritative structured matching。

**五筆審閱文字都指出 exact event timing 不受引用影格支持。** Raw Q5 選項是 4 筆 CITATION_UNSUPPORTED、1 筆 NOT_ASSESSABLE（Call 1）；本報告沒有改選項，5 筆 timing 問題是明示人工 notes 的摘要。

人工回覆支援「兩個視窗中的手機 pickup 具有可見依據」；不能進一步說所有模型聲稱的物件、事件瞬間或完整因果鏈都成立。Call 1/4 的 terminal WRONG_TARGET 必須保留，不能因畫面另有 phone pickup 而改成 supported。

{table(['Call','視窗','Representation','人類 disposition（原值）','Supporting aliases（原值）'],primary_rows)}

## 2. 匯入驗證、審閱者與保存

- 5/5 protocol、template SHA、raw SHA、call/window/representation、完成欄位、Q1–Q6 enums、UTC 提交時間及所有引用 aliases 通過。template SHA：`{template_sha}`。
- Reviewer：Call 3 原值 `review_0`，其他 `reviewer_0`。使用者明確確認「同一位，Call 3 是拼字差異」。以獨立 identity-resolution sidecar 記錄，同一 canonical reviewer_0，原檔不變。**這是一位 reviewer，不是多位獨立仲裁者。**
- 五份 Downloads 原始檔逐 byte 複製至 human_submissions/；保留原路徑與 SHA。既有 evidence review template/cards 繼續保留當時 UNREVIEWED 的歷史狀態；現行已完成結果在本分析，不覆寫歷史模板。
- 匯入格式／來源 PASS 不代表人工判斷無誤；Q1/notes 等一致性問題在下節公開。

## 3. 錯誤分層：不將 human support 等同完整正確

{table(['Call','目標 grounding：人工文字摘要','Q5 原始選項','Before/after citation：人工文字摘要','Full strict'],dimension_rows)}

### 3.1 Output contract

五筆 event timing_uncertainty 與 window uncertainty 為空；Call 10 event_id `PRED_EVT_0001` 亦不符三位數格式。這是既有 validator 失敗原因，未修復、未弱化、不因 human support 轉為 valid。

### 3.2 Target grounding / action-object association

- Calls **1、4** 的人工 terminal disposition 為 WRONG_TARGET。人工不是僅依 noun 不同下結論，而有手機/籃球操作、表面支撐與 held-state 的影格說明。
- Call **8** 的 generic object 假說獲 event-level 支持，但 reviewer 明確保留 explicit target-object association 未解，不能當完成 target binding 或全域身分確認。
- Calls **3、10** 的人工文字認為 phone 與可見物件一致。沒有因此建立 PersistentEntity 或修改 identity authorization。

### 3.3 Temporal localization

- Calls **1、3、4、8** 指到 F0001；人工指出該影格仍是 surface state，或所稱 ball 沒有 pickup。第一個 supplied observation 不等於 transition time。
- Call **10** 的 F0077 為有效 alias，對應第六張 sampled source S000418、13.933333333333334 秒。人工認為該處已是 held-state，不能支撐精確拿起瞬間。
- 人工可以支持 action-level transition，同時無法確定 separation 的精確時刻。Q4 的 DIRECT_TRANSITION_VISIBLE 原選項不自動產生 exact frame GT，也不將 before/after bracket 當事件 duration。

### 3.4 State evidence / citations

- Calls 1/3/8 的 F0016 after-state claim 與人類所指可見 state 不符或不足；Call 4 對 ball 的 held-state 沒有可見支持。這四個個案的具體證據見逐 call 表，不能只因後續有手機被拿起而替原 citation 補證。
- Call 10 以 F0077 同時證明 ON_SURFACE、HELD_BY_PERSON 與 exact event。人工接受它作 AFTER，指出它不能支撐 BEFORE 或 transition instant。
- 每一 human alias 都經現有 call mapping 驗證；alias 合法性與 cited evidence 是否支持主張是不同問題。

### 3.5 人工表單一致性警示（不自動修正）

- Calls **1、4** Q1 均選 IDENTIFIABLE_AND_CONSISTENT，但 notes 與 terminal WRONG_TARGET 指出 model-object mismatch。兩者並列保存；不把 Q1 的 5/5 該選項解讀成 5/5 正確 target grounding。
- Call **8** Q1 相同選項，但 notes 保留 explicit target association 未解；不能抹去限定語。
- Call **1** Q5 選 NOT_ASSESSABLE，notes 明確否定 F0001 exact timing。原 enum 計數與 notes 摘要分別報告。
- 上述不一致提醒日後若要做欄位級定量分析，需人類明確澄清；目前 terminal disposition 計數只忠實統計提交原值，未替人類重選。

## 4. 原始問項統計（只統計所選欄位）

{table(['Question','原始回答 counts'],[[k,dict(v)] for k,v in question_counts.items()])}

報告 secondary themes 的 codes 在 HUMAN_ADJUDICATED_CALLS.json 逐項引用 human notes/rationale，是分析者對已提交文字的摘要，不是新增 reviewer-selected 標籤；不同 theme 可重疊，不能相加當不同錯誤個案總數。

## 5. Representation 與 window 描述

{table(['Representation','本次五筆選定 event-bearing calls 的人類判定'],[[k,dict(v)] for k,v in rep.items()])}

- **test5 W05**：Native Call 1 WRONG_TARGET；Storyboard Call 3 supported，但 F0001 timing / F0016 after citation 有問題；Multi-image Call 10 supported，但 F0077 被錯當 before 與 exact timing。這是同一 source window 的三種輸出，不是三個獨立實例或排名。
- **test7 W05**：Storyboard Call 4 WRONG_TARGET（ball/phone association）；Native Call 8 supported at event level，但 explicit target association 與時間定位仍有問題。
- test7 Multi-image **Call 2** 原為 strict-valid NO_CONFIRMED_EVENT，這次五份提交沒有 Call 2 adjudication。雖然同視窗其他輸出的人工文字支持 phone pickup，仍不能把 Call 2 自動標成 human-adjudicated false negative。

## 6. 與完整 18-call pilot 的關係

既有 pilot 18/18 完成，10 筆 strict-valid 全為 NO_CONFIRMED_EVENT，8 筆 strict-invalid；本次只審閱其中 **5 筆 event-bearing strict-invalid**。另外 3 筆 invalid 與 10 筆 valid no-event 不因這次審閱獲得 physical correctness label。
原有 known-event matching、strict-negative case alerts 與不確定視窗結果均未改寫。人類支持不授權繞過 strict gate，也不構成新 structured prediction、NO_EVENT、更動過的 GT 或全視窗完整性。

## 7. 保守結論與當前瓶頸

此 pilot 的人類審閱顯示 VLM 可以提出有可見依據的 physical-event-level hypotheses（Calls 3/8/10），但目前仍同時存在 **structured-output contract failure、target/action misassociation 或 unresolved binding、temporal localization 與 state-citation grounding** 問題。現有輸出不能直接視為可靠的可執行事件記錄。
本結果支持把「是否有 pickup 依據」與「哪個物件、何時、哪些影格支持」分開評估；不證明 deterministic software 已能修復缺失，也不授權改寫模型事件。
架構維持 VLM 產生 physical-event hypothesis；deterministic software 後續做 evidence validation/temporal resolution/Memory Graph construction。這次沒有重新設計接口或實作修補。

**科學限制：** 僅一位 reviewer、兩個 non-exhaustive DEV windows、五個事先選定 event-bearing calls；重複 window/表示相依。八影格抽樣有未觀察間隙；Native 為 8 source frames / 4 temporal units。沒有 independent blinded inter-rater adjudication、沒有完整事件清單、沒有 validated PLACEMENT positive，也沒有新增 exact-event-time GT。人工對敘述的支持不能推廣到其他影片或完整系統。
不報正式 accuracy、precision、recall、F1、FPR、hallucination rate 或 generalization；3/5 是這五份提交的 disposition 計數，不是模型準確率。

## 8. 逐 case 完整審閱與證據

{chr(10).join(details)}

## 9. 交付與停止

- {link(OUT/'ADJUDICATION_IMPORT_AUDIT.json','Import/provenance audit')}
- {link(OUT/'HUMAN_ADJUDICATED_CALLS.json','Machine-readable human records and sourced error themes')}
- {link(OUT/'REVIEWER_IDENTITY_RESOLUTION.json','Human-confirmed reviewer identity correction')}
- {link(OUT/'READONLY_PRESERVATION_REPORT.json','Original-source preservation audit')}
- {link(OUT/'DELIVERABLE_HASHES.json','Deliverable SHA-256 manifest')}

五份人類標註皆已完成；沒有待補的 terminal disposition。欄位級 Q1/Q5 一致性限制仍如上揭露，不在本任務自動改答案。此處停止，不調 prompt、不重跑、不追加模型、不更動 GT、不寫 Memory Graph、不 commit/push。
'''
save('PHASE2B_HUMAN_ADJUDICATED_ERROR_ANALYSIS.md',report)
changed=[{'path':path,'expected':expected,'observed':sha(Path(path)) if Path(path).is_file() else None}
         for path,expected in preservation.items() if not Path(path).is_file() or sha(Path(path))!=expected]
save('READONLY_PRESERVATION_REPORT.json',{'status':'UNCHANGED_WITHIN_AUDITED_SCOPE' if not changed else 'FAIL',
 'audited_source_files':len(preservation),'changed':changed,'Downloads_untouched':True,'historical_review_template_still_UNREVIEWED':True,
 'scope':'139 original review-scope files plus the full prior review package and five source human submissions; baseline lists exact paths.',
 'GT_modified':False,'prompt_or_validator_modified':False,'new_model_calls':0,'new_image_or_video_decodes':0,'Memory_Graph_written':False,
 'workspace_navigation_updated_separately':True})
assert not changed
assert all(r['disposition']=='UNREVIEWED' for r in read(REVIEW/'HUMAN_ADJUDICATION_TEMPLATE.json')['records'])
save('DELIVERABLE_HASHES.json',{rel(p):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='DELIVERABLE_HASHES.json'})
print(json.dumps({'status':'PASS_T_PHASE2B_HUMAN_ADJUDICATED_ERROR_ANALYSIS_COMPLETE','completed':5,
 'human_dispositions':dict(counts),'source_files_unchanged':len(preservation),'report':str(OUT/'PHASE2B_HUMAN_ADJUDICATED_ERROR_ANALYSIS.md'),
 'report_sha256':sha(OUT/'PHASE2B_HUMAN_ADJUDICATED_ERROR_ANALYSIS.md')},ensure_ascii=False))
