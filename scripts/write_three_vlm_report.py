"""Publish one comparative report from recorded results; no inference or labels."""
from pathlib import Path
import json,collections,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/pass_t/phase3/three_vlm_full_v1'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def link(name,label=None):return f'[{label or name}](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/{name})'
def num(x,d=2):return f'{x:.{d}f}' if x is not None else '不可估計／未量測'
def pct(n,d):return f'{n}（{100*n/d:.1f}%）' if d else f'{n}（不可估計）'
def error_classes(rows,normalized=False):
    counts=collections.Counter()
    for row in rows:
        validation=row.get('validation',{})
        diag=(validation.get('normalized_body') or {}).get('validation',{}) if normalized else validation.get('raw',{})
        counts.update({('JSON_SYNTAX' if e.startswith('JSON:') else 'SCHEMA' if e.startswith('SCHEMA:') else 'UNSUPPLIED_ALIAS' if e.startswith('UNSUPPLIED:') else e) for e in diag.get('errors',[])})
    return dict(counts.most_common())
def main(replace_own_report=False,publication_date='2026-10-17'):
    ds=read(OUT/'dataset.json');rs=read(OUT/'model_results.json');gt=read(OUT/'gt_evaluation.json');matched=read(OUT/'matched_inputs.json');verify=read(OUT/'verification.json');cfg=read(OUT/'configuration.json');freeze=read(OUT/'dataset_freeze.json')
    all_complete=all(r['completed']==freeze['unique_inputs'] and not r['failed'] for r in rs.values())
    status='THREE_VLM_FULL_DATASET_INFERENCE_COMPLETE' if all_complete else 'THREE_VLM_EVALUATION_PARTIAL_WITH_EXPLICIT_BLOCKERS'
    notes=read(OUT/'qualitative_analysis.json') if (OUT/'qualitative_analysis.json').exists() else {'summary':'尚無新增人工 physical adjudication；未審閱案例不判為正確。','cases':[]}
    lines=['# FindMind：test1–test9 三模型完整時間軸評估','',f'更新：2026-10-17。狀態：**{status}**。','',
    '## 1. 本次結論','',
    f'共同資料集涵蓋九支來源影片的全部視覺時間軸：69 個既有條目＋145 個新增覆蓋視窗＝214 條目，去除相同輸入後 **184 個不同輸入**。三模型實際共同完成 **{len(matched["all_three_completed"])}／184**；Qwen／VideoLLaMA 共同完成 **{len(matched["qwen_videollama_completed"])}／184**。執行完成不代表預測正確。','',
    '**最終建議：No model yet suitable for direct graph updates（目前沒有模型適合直接寫入 Graph）。** 結構有效、生成事件文字、物件類別辨識與確認同一物理實體／轉移，是不同層次。新資料仍缺全影片人工事件與逐格 state GT，不能給正式整體模型排名。','',
    notes['summary'],'',
    '## 2. 資料集與完整時間覆蓋','',
    '九支來源檔案均與既有 development_inputs 的 SHA-256 相符，無完全相同來源檔案 hash；但不因此認定為九個獨立 recording sessions。時長以下採完整解碼的 native video PTS 至最後影格 presentation end，不是音軌或容器延伸時間。','',
    '| 影片 | 視覺時長（秒） | 原始影格數 | 既有窗 | 新增窗 | 不同輸入 | 時間範圍覆蓋 |', '|---|---:|---:|---:|---:|---:|---|']
    for v in ds['videos']:
        n=sum(w['video_id']==v['video_id'] and w['status']=='ELIGIBLE' and not w['duplicate_of'] for w in ds['windows'])
        lines.append(f'| {v["video_id"]} | {v["duration_seconds"]:.3f} | {v["frame_count"]} | {v["original_windows"]} | {v["added_coverage_windows"]} | {n} | {"完整" if v["timeline_coverage_complete"] else "有缺口"} |')
    lines += ['',
    '固定規則：每窗最多 8 張，依窗內 native PTS 均勻分位點，取最近且嚴格遞增的 source index、同距取較早影格；不足 8 張則全部不同影格、不重複 padding。既有與新增窗一律同規則。新增覆蓋採 4 秒窗、2 秒 stride，從首個 PTS 起算，僅在區間未被既有或先前 coverage grid 完整覆蓋時加入；短尾端截至影片末端。時長依既有約 1–6 秒、典型約 3.6 秒的窗設計選定，沒有使用 GT 或先前模型答案。','',
    '保留舊 start/end，依現有 producer/validator 的 closed indices 解讀；舊 Phase 2a 的 half-open authorized scope 另外保留，不能混同。52 個原本沒有 frames 的條目現在都已從來源影片補齊；沒有再排除 test6。所有輸入是原片解碼的乾淨 PNG。','',
    '214 條目中 30 個是相同 source evidence 的重複別名，模型每組只生成一次。另驗證 184 組中沒有額外完全相同的 ordered PNG sequence。重疊窗及其 identities 全部保存，不能當作 184 個獨立真實事件或獨立樣本。完整時間配置覆蓋不等於 8 張圖觀察了每一瞬間，也不構成 exhaustive human negative。','',
    '實際共有 1,411 個不同 source frames 被採樣，來源合計 9,958 格（約 14.17%）；「全時間軸覆蓋」是所有時段都有所屬評估視窗，不是逐格觀察或完整捕捉所有短暫轉移。','',
    f'完整來源／邊界／重疊／去重／frame hash／PTS：{link("dataset.json")}；逐原始影格時間：{link("timelines", "timelines/")}；凍結憑證：{link("dataset_freeze.json")}。','',
    '![九影片完整時間範圍與實際採樣點](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/timeline_coverage.png)','',
    '## 3. 共同任務與實際部署','',
    '三模型使用同一份英文 observation-first task 與最小 schema：每物件逐 alias 的 ON_SURFACE／HELD_BY_PERSON／OTHER／UNKNOWN，之後可選 PICKUP／PLACEMENT。固定連續 aliases F0001–F0008，附原生 source PTS。沒有特定目標類別、預期答案、GT、舊模型結果或 tracker/identity metadata；Reference NONE。任務與 schema 在本輪生成前固定，沒有根據結果修改。','',
    '| 模型 | 固定 revision | 部署 | 有效視覺表示 |','|---|---|---|---|']
    q=cfg['models']['qwen'];v=cfg['models']['videollama'];n=cfg['models']['nemotron']
    lines += [f'| Qwen2.5-VL-7B-Instruct | `{q["revision"]}` | 原有 NF4／BF16 compute、SDPA、Windows 環境 | 8 張 chronological images；既有 200704 pixel budget，每張通常 588×336 |',f'| VideoLLaMA3-7B | `{v["revision"]}` | 原官方實作、語言 NF4、視覺/projector BF16、SDPA、隔離 Transformers 4.46.3 | 8 張 chronological images；合計 4096 visual-token 上限，通常每張 420×224 |',f'| Nemotron Nano 12B v2 VL | `{n["revision"]}` | 官方 NVFP4-QAD、WSL2、vLLM {n["vllm_version"]}、Torch 2.13 cu130 | 官方 video array 8 張、512×512、temporal patch 1、EVS pruning=0；GPU成功情況依下節實測 |','',
    '全部固定 greedy／seed 42／max output 1536 tokens／generation timeout 300 秒，無品質重試。seed 不是跨硬體逐 bit determinism 的保證。使用各模型官方 chat template；Nemotron video 使用官方 no-think 格式控制。模型循序執行，同一 GPU 不同時載入兩個重 VLM。','',
    '來源 PNG、索引、native PTS 與順序共用，但實際 tokenizer、影格尺寸、視覺 token/tiling、量化與 engine 不同。**這是 deployment-configuration comparison，不是完全相同內部 tensor 的純模型能力比較。** 不把各模型 token 數當成相同計算單位。','',
    'Nemotron 的 official video processor 實際輸出 [8,3,512,512]，不是將八張減成四張；GPU 生成完成數以下節 raw receipts 為準。官方 vLLM video timestamps 以 floor(1000/source_fps) 毫秒乘原始 index，會與 native PTS 漂移；原生時間完整另外提供，未把近似時間冒充 authoritative PTS，亦未宣稱 frame-level attention 已驗證。逐次 input receipt 保存實際有效表示。','',
    'Nemotron 官方變體與授權來源：[NVFP4-QAD 模型卡](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-NVFP4-QAD)、[官方 BF16／video 使用說明](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-BF16)。本次沒有用 BF16 塞入 16GB，也沒有換成較小模型。Windows 磁碟上的 WSL wheel cache rename 問題改用原生 uv 安裝相同 Linux wheels；保留 eager 模式，在 Ubuntu 安裝 g++ 15.2、python3.14-dev 與 ninja-build，供官方 CUDA/Triton launcher 使用。IPC socket 改放 Linux /tmp，持久 artifacts/cache 留在專案。Windows 兩個既有環境保持原樣。','',
    '## 4. 真實生成、合約與效率結果','',
    '| 模型 | 已完成 raw／184 | failed | 未執行 | raw JSON | raw schema | raw full strict | fence body full-valid（另列） |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for m,r in rs.items():lines.append(f'| {m} | {r["completed"]} | {r["failed"]} | {r["not_executed"]} | {pct(r["raw_json_parse_count"],r["completed"])} | {pct(r["raw_schema_valid_count"],r["completed"])} | {pct(r["raw_strict_valid_count"],r["completed"])} | {r["normalized_body_full_valid_count"]} |')
    lines += ['',
    '分母是已返回並保存 raw 的完成呼叫；未執行不冒充模型負例。token-cap／timeout 可留下 partial raw，會在下一表另列。每份 raw 立即保存，JSON/語法、schema、引用、semantic consistency 分開驗證；invalid 不變成 NO_EVENT。只允許獨立記錄單一完整外層 Markdown fence 提取，不修補 JSON、不補 uncertainty/events/citations、不提升 raw strict。fence-body 是 descriptive proposal view，不是 authoritative accepted structured output。','',
    '| 模型 | 逐窗總處理秒數 | median／p95 秒 | EOS／token-cap／timeout | Torch peak GiB | 全 GPU used peak MiB | 輸出 tokens median／max |','|---|---:|---|---|---|---|---|']
    for m,r in rs.items():
        ts=r['output_token_stats'];lines.append(f'| {m} | {r["end_to_end_window_seconds_sum"]:.2f} | {num(r["median_window_latency_s"])}／{num(r["p95_window_latency_s_nearest_rank"])} | {r["eos_count"]}／{r["token_cap_count"]}／{r["timeout_count"]} | {num(r["peak_torch_allocated_gib"])} | {r["peak_global_gpu_used_mib_includes_other_processes"] if r["peak_global_gpu_used_mib_includes_other_processes"] is not None else "未量測"} | {ts["median"] if ts["median"] is not None else "不可估計"}／{ts["max"] if ts["max"] is not None else "不可估計"} |')
    lines += ['',
    '逐窗處理時間包括 render/preprocess/generate/保存/validation，載入、下載、資料建置與等待其他模型另計；完整 load receipts 保存在每模型 run 目錄。p95 採 nearest-rank。Torch peak 是該模型 process allocator；Nemotron worker 的全 GPU used 另含 display/其他 process，兩種數字不可直接當成相同量測比較。','',
    '| 影片 | Qwen 完成／不同輸入 | VideoLLaMA 完成／不同輸入 | Nemotron 完成／不同輸入 |','|---|---:|---:|---:|']
    for vid in [v['video_id'] for v in ds['videos']]:
        cells=[f'{rs[m]["per_video"][vid]["completed"]}／{rs[m]["per_video"][vid]["unique_inputs"]}' for m in rs];lines.append('| '+vid+' | '+' | '.join(cells)+' |')
    lines += ['', '### 觀察與事件候選（不是正確率）','', '各模型可能只回部分影格的 state；漏列不等於 UNKNOWN，也不能由未列某格推定 processor 丟掉該格。以下 state entries 是描述性輸出量，並非不同實體數或 state accuracy。候選事件數包含跨重疊窗重複與 strict-invalid 的可解析假說，不是真實事件數；較多不等於較高 recall。','']
    for m,r in rs.items():
        top=sorted(r['object_description_frequencies'].items(),key=lambda x:-x[1])[:8];lines += [f'- **{m}**：物件描述次數 `{json.dumps(dict(top),ensure_ascii=False)}`；state entries `{json.dumps(r["state_claim_frequencies"],ensure_ascii=False)}`；parsed/fence hypotheses {r["event_proposal_count"]}，raw-strict hypotheses {r["strict_event_proposal_count"]}，類型 `{json.dumps(r["event_claim_types"])}`。UNKNOWN 僅為模型自述，不當成錯誤標籤。']
        lines += [f'  狀態宣告 `{json.dumps(r["descriptive_status_counts"])}`；UNKNOWN 占可解析 state claims {num(100*r["unknown_state_claim_fraction"]) if r["unknown_state_claim_fraction"] is not None else "不可估計"}%；有引用的可解析輸出 {r["citation_membership_assessable_count"]}，全部 alias 存在 {r["citation_membership_valid_count"]}，無引用 {r["no_citations_count"]}。這是 membership，並非影像支持。輸入 token median／min／max：`{json.dumps(r["input_token_stats"])}`，不跨 tokenizer 比較計算量。']
        lines += [f'  Raw validation 錯誤類別（每窗每類最多計一次）：`{json.dumps(error_classes(r["rows"]),ensure_ascii=False)}`。fence-body 錯誤另列：`{json.dumps(error_classes(r["rows"],True),ensure_ascii=False)}`。完整原始錯誤訊息保留在 model_results.json。']
    for m,r in rs.items():
        for e in r['load_failures']:
            label='已排除的啟動錯誤' if r['completed']==freeze['unique_inputs'] else '載入／工程證據'
            evidence_path=e['path'].replace('\\','/').split('three_vlm_full_v1/')[-1]
            lines += ['',f'**{m} {label}**：`{e["error_type"] if "error_type" in e else "ERROR"}`：{str(e.get("error",""))[:600]}。完整 trace：{link(evidence_path)}。這些失敗發生於生成前，不是品質重試。']
    lines += ['',
    f'完整逐模型／逐窗／parser 分層、資源、object/state summaries：{link("model_results.json")}。來源相同的交集清單：{link("matched_inputs.json")}。候選事件與 source-time evidence brackets：{link("event_proposals.json")}；括號不是物理事件持續時間，也不自動視為 true event interval。','',
    '## 5. GT 適用範圍與一致評估','',
    '既有人工來源保留：3 個 local-target strict-negative units（test1 W03/W05 去重、test2 W01、test5 W01）、2 個非完整 PICKUP 正例（test5/test7 W05）、1 個證據不足窗；test3 W07 繼續隔離。另讀既有五份 human-adjudicated model-call review，僅用其可支持的 physical-event/context 範圍，不把舊模型預測當 GT 或新模型答案。','',
    '**沒有新的人類 GT、沒有全九影片 exhaustive annotation、沒有正式 PLACEMENT positive。** 舊 GT formal_eligible=0，且主要只針對一個 local target；不能拿來評估通用 task 的所有物件與全影片負事件。舊 half-open GT 與本次 closed 端點也不同，部分最後一格超出原 GT 授權範圍，已逐筆列出。','',
    '| 指標 | 本次可報內容 |','|---|---|',
    '| Object recognition recall／class confusion／wrong-target rate | 新逐物件人類標籤與 instance mapping 尚缺；不可估計，不能把 category 相同當同一 PersistentEntity |',
    '| State accuracy／per-state confusion／unsupported-state frequency | 缺 reviewed frame-object-state/support GT；不可估計。模型 UNKNOWN/各 state 頻次另列，不把 unknown/unreviewed 算錯 |',
    '| PICKUP precision／recall／F1 | 沒有本通用任務的 exhaustive eligible truth 與 reviewed identity/proposal groups；不可估計。known-positive cases 只作探索性描述 |',
    '| PLACEMENT recall／F1 | 沒有 eligible positive，不可估計，不報 0 |',
    '| Before/after/object/transition citation support | alias membership 與 consistency 可自動驗證；實際影像支持需人工，未審閱不判為成功 |',
    '| JSON/schema/citation membership/truncation/efficiency | 可對實際完成 calls 報告，與 physical correctness 分開 |','',
    '同一 evaluator 對三模型一致處理。temporal matching 明定 0／0.2／0.5 秒（primary 0.2），閉區間距離 max(c−b,a−d,0)，one-to-one maximum-cardinality；需相同已人工確認 object ID/type/source video。無時間或身分則不匹配。精確 input duplicates 已去除；跨重疊窗的真實同一事件必須由人賦予同一 reviewed_event_group，不能只靠相似描述／重疊 bracket 把不同事件併成一件。未審閱 proposals 不入 authoritative matching，不重複數同一 human event。','',
    f'所有 GT 來源 hashes、逐舊窗 eligibility／超出範圍 indices、sidecar 與不可估計原因：{link("gt_evaluation.json")}。非完整窗的未列事件一律 UNEVALUATED，絕不自動算 FP。','',
    '### 舊負例與不確定範圍的描述性警報','',
    '以下只列新輸入是否產生候選，不計 FP：原 GT 僅針對 local phone target，且邊界可能比本次少最後一格。前三個 unit 是舊負例，test8 W07 則是證據不足，不能作正例或負例。沒有候選也不證明負例正確。test1 W03/W05 是同一負例單位，只列 canonical input。','',
    '| 舊 GT unit | 模型 | 新輸入狀態宣告 | raw/fence 候選事件 | raw full strict |','|---|---|---|---|---|']
    by_window={w['window_id']:w for w in ds['windows']}
    for wid in ('test1__W03','test2__W01','test5__W01','test8__W07'):
        canonical=by_window[wid]['duplicate_of'] or wid
        for m,r in rs.items():
            row=next(x for x in r['rows'] if x['window_id']==canonical)
            content=row.get('descriptive_content') or {}
            if not isinstance(content,dict):content={}
            es=content.get('events',[])
            if not isinstance(es,list):es=[]
            claims='; '.join(str(e.get('type'))+' '+str(e.get('object')) for e in es if isinstance(e,dict)) or '無可解析事件候選'
            lines.append(f'| {wid} → {canonical} | {m} | {content.get("status","不可解析／未完成")} | {claims} | {row.get("validation",{}).get("raw",{}).get("full_valid",False)} |')
    lines += ['', '## 6. 物理證據與錯誤分析','',
    '以下是助理對實際選取影格及模型原文的 retrospective analysis，不是新的 human adjudication；案例選取包含既有 known positives 與實際格式／引用失敗，不代表隨機抽樣全體。','']
    for case in notes.get('cases',[]):lines += [f'### {case["window_id"]}','',case['evidence'],'',case['analysis'],'']
    lines += [
    '其他未逐格審閱的 state／target claims 保持 UNREVIEWED；不能因狀態描述合理或 schema 有效就標 correct。camera-motion-only 不能證明 manipulation；遮擋後的確定 HELD／ON_SURFACE、把類別當 instance、前後不匹配與不存在的 aliases 都需分開檢查。沒有對未審閱全體臆造錯誤率。','',
    '## 7. 人工審閱套件與交付入口','',
    f'直接開啟 **{link("human_review/INDEX.html", "九影片人工審閱頁")}**：184 張 actual-frame contact sheets，source-video links，可另開完整 PNG；沒有預填模型答案。','',
    '- `events.csv`：video/type/object/time interval/support source frames/identity certainty/coverage review/reviewer。',
    '- `states.csv`：1,411 個不同 source frames 的空白列；按物件填 state/visibility/support certainty/review status，同格多物件可新增列。',
    '- `coverage.csv`：9 個 full-video review scopes，預設 UNREVIEWED；需完整區間、人類 exhaustive attestation、無可藏事件的缺口及 target association resolved，才可建立 exhaustive negative。',
    '- `object_mapping.csv`／`proposal_review.csv`：人工辨認 model object、物理實體、事件群與 before/after/identity/transition support。',
    '這是可編輯檔案與靜態頁面，不是新標註 web application。新填答案必須另行驗證，不能自動覆寫歷史 GT。','',
    f'程式／原始資料：{link("runs", "三模型 runs/")}；{link("configuration.json")}；{link("prompt.json")}；{link("schema.json")}；{link("execution_components.json")}；{link("execution_integration_revisions.json")}；{link("verification.json")}。','',
    '## 8. 保存、限制與下一步','',
    f'保存檢查：{verify["historical_protected_files"]} 個既有檔案，變動 {len(verify["changed_historical_files"])}；凍結資料／frames 變動 {len(verify["changed_frozen_dataset_or_frames"])}；原片變動 {len(verify["changed_source_videos"])}；{verify["completed_input_receipts_checked"]} 份完成輸入 receipts 的 frames／共同 task／schema／表示檢查失敗 {len(verify["input_integrity_failures"])}；未記錄的 execution-component 變動 {len(verify["unexpected_execution_component_changes"])}。相容性修正另存 before/after 與真實錯誤證據；沒有改 prompt/schema/source selection 或根據輸出品質調整。8 個 CPU contract checks 通過，無視覺 fixtures、無品質重試。','',
    f'CPU 檢查：`.venv/Scripts/python.exe -X utf8 -B -m unittest discover -s tests -p test_three_vlm_contract.py -v`；結果 {link("cpu_tests_final.log")}。這些只驗證採樣／parser／matcher／GT eligibility contracts，不是模型品質測試。','',
    '沒有改歷史 Qwen／VideoLLaMA／V297／GT／人工 review；沒有訓練、Graph 更新、commit 或 push。資料是開發用錄影，已被專案反覆使用，不能宣稱 held-out generalization。','',
    '**下一步：先在這個共同資料集完成事件／state／coverage 的人工審閱，再在相同 outputs 上重算 eligible metrics；不先換 prompt 或追加生成。** VLM 保持 physical-event hypothesis producer，deterministic software 負責 evidence/identity/temporal validation；本次沒有重新設計 Event-to-Graph。']
    lines += ['', '### 重現用 SHA-256', '', '| 固定輸入／組件清單 | SHA-256 |', '|---|---|']
    for name in ('dataset_freeze.json','configuration.json','prompt.json','schema.json','execution_components.json','execution_integration_revisions.json'):
        lines.append(f'| {link(name)} | `{hashlib.sha256((OUT/name).read_bytes()).hexdigest()}` |')
    text='\n'.join(lines)+'\n';report=OUT/'THREE_VLM_COMPARATIVE_REPORT.md'
    with report.open('w' if replace_own_report else 'x',encoding='utf8') as f:f.write(text)
    header=f'> WORKSPACE 閱讀副本；更新 {publication_date}；推論報告資料為 2026-10-17，本次完成發布與回查。權威來源：'+link(report.name)+'。\n\n'
    workspace=ROOT/'WORKSPACE/VLMtest';workspace.mkdir(parents=True,exist_ok=True)
    (workspace/'LATEST_REPORT.md').write_text(header+text,encoding='utf8')
    print(str(report));print(status)
if __name__=='__main__':main()
