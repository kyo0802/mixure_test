"""Read-only CPU analysis of the completed authorized run; never invokes inference."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import json, hashlib, collections, datetime

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'artifacts/pass_i/runtime/vendor'),
                str(ROOT/'outputs/current_development/video_event_experiment/.deps')]
from memory_graph.pass_t.phase2b.v1d_protocol import verify_frozen
from memory_graph.pass_t.phase2b.v1d_execution import evaluate_recorded_call

OUT = Path(__file__).resolve().parent
RUN = OUT.parent
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_new(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(value, ensure_ascii=False, indent=2)+'\n' if not isinstance(value,str) else value)
def cell(value): return str(value).replace('|','/').replace('\n',' ')
def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(cell(v) for v in row)+' |' for row in rows])

receipt = read(RUN/'run_receipt.json')  # Requires completed supervisor receipt.
bundle = read(RUN/'frozen_bundle.json')
auth = read(RUN/'authorization_use.json')
draft = verify_frozen(bundle, ROOT)
elig_path = ROOT/'artifacts/pass_t/phase2b/readiness/eligibility.json'
elig = read(elig_path)
gt_path = ROOT/elig['authority']['dataset_path']
gt = read(gt_path)
private_hashes_before = {str(p.relative_to(ROOT)):sha(p) for p in [elig_path,gt_path]}
records = {r['annotation_item_id']:r for r in gt['records']}
eligible = {r['annotation_item_id']:r for r in elig['records']}
names = {'PT2A_9d15d2a6b56b56d0':'test1 W03/W05 (dedup)',
         'PT2A_b35d807b28b92101':'test2 W01','PT2A_fe0910d66f4c5614':'test5 W01',
         'PT2A_eb60192e6986cb4f':'test5 W05','PT2A_c58b4df88a2f6801':'test7 W05',
         'PT2A_5dbb180e8ff88762':'test8 W07'}
statuses = {r['call_id']:r for r in receipt['call_statuses']}
analysis=[]; rows=[]; hypothesis_rows=[]; matching_rows=[]; negative_rows=[]; uncertain_rows=[]
stages={k:collections.Counter() for k in ['JSON_SYNTAX','SCHEMA','SEMANTIC','CITATION','FULL_STRICT']}
rep=collections.defaultdict(lambda:collections.Counter())
for call in draft['run_order']:
    cid=call['proposed_call_index']; item=call['item_id']; directory=RUN/f'call_{cid:02d}'
    entry={'call':call,'execution_status':statuses[cid], 'human_physical_adjudication':'UNREVIEWED'}
    cp=directory/'call_receipt.json'
    if not cp.exists():
        rows.append([cid,names[item],call['representation'],statuses[cid]['status'],'NOT_AVAILABLE','—','—'])
        entry['evaluation']={'matching_status':'NOT_AVAILABLE','no_event_inferred':False}
        analysis.append(entry);continue
    c=read(cp); rt=read(directory/'runtime_receipt.json'); cl=c['classification']
    assert sha(directory/'raw_output.txt')==c['raw_sha256']
    assert sha(directory/'runtime_receipt.json')==c['runtime_receipt_sha256']
    ev=evaluate_recorded_call(directory,bundle,auth,records[item],eligible[item],ROOT)
    entry.update(classification=cl,evaluation=ev,runtime_receipt_error=c['runtime_receipt_error'],
                 raw_sha256=c['raw_sha256'],runtime_receipt_sha256=c['runtime_receipt_sha256'],
                 runtime_seconds=rt.get('runtime_seconds'),request_total_seconds=rt.get('request_total_seconds'),
                 peak_inference_vram_bytes=rt.get('peak_inference_vram_bytes'),generated_tokens=rt.get('generated_tokens'))
    for key in stages: stages[key][cl['stages'][key]]+=1
    rep[call['representation']]['recorded']+=1
    rep[call['representation']][cl['classification']]+=1
    pred=cl.get('prediction') or {}
    rows.append([cid,names[item],call['representation'],statuses[cid]['status'],cl['classification'],
                 pred.get('window_outcome','—'),round(rt.get('runtime_seconds',0),2)])
    for event in pred.get('events',[]):
        hypothesis_rows.append([cid,event.get('event_type'),event.get('timing'),
                                event.get('cited_frame_aliases'),event.get('rationale'),
                                'STRUCTURED_ELIGIBLE' if cl['authoritative_prediction'] is not None else 'STRICT_INVALID_DESCRIPTIVE_ONLY'])
    for tol,result in (ev.get('sensitivity_results') or {}).items():
        if eligible[item]['pilot_scoring_permission']=='KNOWN_EVENT_MATCHING_ONLY':
            matching_rows.append([cid,names[item],tol,len(result.get('matches',[])),
                                  result.get('unmatched_supported_gt_event_ids','see JSON'),
                                  'UNEVALUATED'])
        elif eligible[item]['pilot_scoring_permission']=='STRICT_NEGATIVE_CASE_ALERT_ANALYSIS' and tol=='0':
            negative_rows.append([cid,names[item],result.get('case_level_false_event_alert'),result.get('prediction_outcome')])
        elif eligible[item]['pilot_scoring_permission']=='DESCRIPTIVE_UNCERTAINTY_ONLY' and tol=='0':
            uncertain_rows.append([cid,names[item],result.get('prediction_outcome'),'DESCRIPTIVE_ONLY'])
    analysis.append(entry)

for path,expected in private_hashes_before.items(): assert sha(ROOT/path)==expected
verify_frozen(bundle, ROOT)
write_new(OUT/'CALL_ANALYSIS.json',{'protocol_sha256':receipt['protocol_sha256'],
    'authorization_sha256':receipt['authorization_sha256'],'private_source_hashes':private_hashes_before,
    'records':analysis,'stage_counts':{k:dict(v) for k,v in stages.items()},
    'representation_counts':{k:dict(v) for k,v in rep.items()},'physical_adjudication':'UNREVIEWED'})

samples=receipt.get('resource_samples',[])
resource={key: (min(s[key] for s in samples) if key=='ram_available_gib' else max(s[key] for s in samples))
          for key in ['gpu_used_gib','owned_rss_gib','ram_available_gib']} if samples else {}
resource['supervised_elapsed_s']=max((s['elapsed_s'] for s in samples),default=0)
resource['sampling_note']='Sampled values; not a guarantee that all transient peaks were captured.'
write_new(OUT/'RESOURCE_SUMMARY.json',resource)
completed=sum((RUN/f"call_{c['proposed_call_index']:02d}/call_receipt.json").exists() for c in draft['run_order'])
fullpass=sum(a.get('classification',{}).get('stages',{}).get('FULL_STRICT')=='PASS' for a in analysis)
title='PASS_T_PHASE2B_V1D_REAL_DEV_PILOT_COMPLETED' if completed==18 and receipt['worker_exit_code']==0 and not receipt['stop_reason'] else 'PASS_T_PHASE2B_V1D_REAL_DEV_PILOT_STOPPED'
text=f'''# Phase 2b — Real DEV Qwen NF4 V1D Exploratory Pilot

更新：{datetime.datetime.now(datetime.timezone.utc).isoformat()}。權威來源：`{OUT.relative_to(ROOT).as_posix()}`。

## 執行結論

**{title}**。保存完整 call 回條 {completed}/18；full strict 通過 {fullpass}/{completed}。
Supervisor stop reason：`{receipt['stop_reason']}`；worker exit code：`{receipt['worker_exit_code']}`。
未完成 call IDs：`{receipt['missing_call_ids']}`；generation retries：0。各筆狀態以下表及原始 supervisor receipt 為準。
Strict-invalid 不是 NO_EVENT，未納入 authoritative structured matching；模型推論完成也不代表事件正確。

## 授權、設定與完整性

- Protocol canonical SHA-256：`{receipt['protocol_sha256']}`。
- Authorization canonical SHA-256：`{receipt['authorization_sha256']}`；reviewer：`{auth['reviewer_id']}`。
- 既有 local Qwen2.5-VL-7B-Instruct NF4；immutable V1D/V2；Uniform8、Reference NONE、C3；greedy、seed 42、max_new_tokens 1024。
- Multi-image8 / Storyboard8 / Native Video Array8；Native 為 FRAME_MATCHED_ONLY，8 source frames 對應 4 temporal units，不代表八個獨立 temporal positions。
- 固定 source PTS 為 authoritative；每筆 provenance、alias mapping、rendered text、processor/tensor records 保留於 call/runtime receipts。
- 凍結元件在分析前後通過原有 verify_frozen；private GT/eligibility 的分析前後 hash 一致。未修改 prompt、GT、validator、runtime 或 Memory Graph。
- 媒體完整性只對實際成功 load_envelope 的 call 適用；未執行者不得稱已驗證。runtime_receipt_error 另列於 CALL_ANALYSIS.json。

## 固定 cohort

{table(['視窗','item_id','允許用途'],[[names[w['item_id']],w['item_id'],w['permission']] for w in draft['windows']])}

test3 W07 排除；test1 W03/W05 為一個去重單位。兩個 known-PICKUP 視窗非 exhaustive；test8 為 uncertain；無 validated PLACEMENT positive。

## 18-call 結果

{table(['call','視窗','representation','執行狀態','分類','模型 outcome','generation 秒'],rows)}

## 分階段 strict 驗證

{table(['stage','status counts'],[[k,dict(v)] for k,v in stages.items()])}

Schema 失敗時 semantic/citation 標為 NOT_ASSESSED_DUE_TO_SCHEMA_FAILURE，不得視作通過。Raw 未修復或補欄、未發明 citation。未輸出、strict-invalid、valid NO_CONFIRMED_EVENT 分別保留。

## 模型提出的事件假說與 citation（不是人工確認）

{table(['call','type','timing','citations','模型 rationale','可用範圍'],hypothesis_rows) if hypothesis_rows else '無保存的 event-bearing hypotheses；不代表已證實無事件。'}

Physical evidence review 全部 UNREVIEWED。本報告只引用模型文字與既有 GT scope；沒有新增人工 adjudication，也沒有將 event claim 當作確證的物理轉換。

## Known-PICKUP matching：0 / 0.2 / 0.5 秒

{table(['call','視窗','tolerance秒','matches','未匹配 known GT','額外假說'],matching_rows) if matching_rows else '無可進入 structured matching 的 known-PICKUP 結果；不是零事件或零錯誤。'}

僅 strict-valid 且 runtime receipt 合格的輸出進入 versioned closed-interval-gap one-to-one matcher。Point-to-interval=max(a-t,0,t-b)；interval-to-interval=max(c-b,a-d,0)。未知時間、target association uncertainty 與 unsupported evidence 不補推。BEFORE/AFTER evidence brackets 不轉成推定事件持續時間。詳細匹配及 unmapped/unknown 情況保留於 CALL_ANALYSIS.json。

## Strict-negative 個案警示

{table(['call','視窗','case alert','outcome'],negative_rows) if negative_rows else '無可評估的 strict-valid negative-window 結果。'}

只作 case-level alerts，不是 population false-positive rate。Invalid/未執行不能當作無警示。負例的額外獨立視覺品質複核有限；test1 僅局部 spot-check，test2/test5 W01 沒有新增逐格視覺複核。

## Uncertain-window 描述

{table(['call','視窗','outcome','scope'],uncertain_rows) if uncertain_rows else '無 strict-valid uncertain-window 結果；invalid hypotheses 僅供上方描述。'}

test8 不當作 negative，也不作完整事件清單主張。

## Representation-specific 描述

{table(['representation','counts'],[[k,dict(v)] for k,v in rep.items()])}

三種表示的差異僅為同一個小型 DEV cohort 的描述，不作模型排名或泛化主張。Storyboard 空間拼圖、multi-image 序列及 native 四 temporal units 的資訊表達不同。

## 資源與時間

`{resource}`

GPU used 含其他進程；owned RSS 含受監控 worker 子樹；runtime 的 per-call peak allocated 與 sampled global GPU usage 不同，詳見 CALL_ANALYSIS.json 與原始 runtime receipts。所有 raw outputs、失敗或未執行狀態保留，未進行 quality retry。

## 科學限制與停止邊界

本次分開報告 execution reliability、contract compliance、physical-event hypotheses 及 representation 描述。格式正確不等於視覺正確；文字中的 PICKUP 不等於已確認的物理 PICKUP。
非 exhaustive 視窗的 unmatched predictions 為 UNEVALUATED；無 validated PLACEMENT positives；small selected DEV、causality unverified、target association 與抽樣間隙均限制解讀。
不報 formal accuracy、precision、recall、F1、false-positive rate、hallucination rate 或 generalization。未新增 GT 或人工審定，未寫 Memory Graph。
依本次授權在此停止；不重跑、不修 prompt、不追加模型呼叫。

## 原始檔案

- [run_receipt.json](../run_receipt.json)：supervisor 原始結果與 resource samples。
- [CALL_ANALYSIS.json](CALL_ANALYSIS.json)：逐 call 分階段驗證、GT-scoped evaluation、hashes。
- [RESOURCE_SUMMARY.json](RESOURCE_SUMMARY.json)：資源彙整。
- [frozen_bundle.json](../frozen_bundle.json)、[authorization_use.json](../authorization_use.json)。
- 每筆 call_01…call_18（存在者）的 raw_output.txt、runtime_receipt.json、call_receipt.json 均保持原樣。
'''
write_new(OUT/'REAL_DEV_PILOT_EXECUTION_REPORT.md',text)
manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(RUN.rglob('*')) if p.is_file() and p.name!='DELIVERABLE_HASHES.json'}
write_new(OUT/'DELIVERABLE_HASHES.json',manifest)
print(json.dumps({'status':title,'completed':completed,'strict_pass':fullpass,'report':str(OUT/'REAL_DEV_PILOT_EXECUTION_REPORT.md'),
                  'report_sha256':sha(OUT/'REAL_DEV_PILOT_EXECUTION_REPORT.md'),'manifest_sha256':sha(OUT/'DELIVERABLE_HASHES.json')},ensure_ascii=False))
