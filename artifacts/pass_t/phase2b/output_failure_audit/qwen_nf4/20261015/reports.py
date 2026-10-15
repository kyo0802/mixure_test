"""Reports and prospective designs only; no inference or implementation repair."""
import json
from pathlib import Path
import statistics
import hashlib
from collections import Counter
import audit

O=audit.OUT;R=audit.ROOT;B=audit.BASE/'v2_20261014_owned_tree'
P=R/'artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003'

def md(name,text):
    with (O/name).open('x',encoding='utf-8',newline='\n') as f:f.write(text.strip()+'\n')

def table(headers,rows):
    def fmt(v):return str(v).replace('|','\\|').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(fmt(v) for v in row)+' |' for row in rows])

def source(path):return f'[{Path(path).name}](<{(R/path).as_posix()}>)'

def main():
    s=audit.read(O/'analysis_summary.json');rows=audit.read(O/'primary_attempts.json')
    schema_path='src/memory_graph/pass_t/phase2b/contracts/prediction_v1.json'
    validator_path='src/memory_graph/pass_t/phase2b/predictions.py'
    sources=[schema_path,validator_path,'src/memory_graph/pass_t/phase2b/evaluation.py',
      'src/memory_graph/pass_t/phase2b/builders.py','src/memory_graph/pass_t/phase2b/local_vlm/qwen_contract.py',
      'src/memory_graph/pass_t/phase2b/local_vlm/nf4.py','artifacts/pass_t/phase2a/v2/contracts/event_gt_annotation_schema_v2.json',
      'artifacts/pass_t/phase2b/reports/PASS_T_PHASE2B_INFRASTRUCTURE_REPORT.md',
      'artifacts/pass_t/phase2b/local_runtime/qwen_nf4/reports/f3436312a71176901cb7333c5e7b496a22c5be23c6010a8dfdd26f0708295f4a/PASS_T_PHASE2B_QWEN_NF4_INTEGRATION_REPORT.md',
      'artifacts/pass_t/phase2b/local_runtime/qwen_nf4/reports/f57aac2072c7a127691fc99a7d8b3e6c872a68da0fd97f92958a16cda94e2f02/PASS_T_PHASE2B_QWEN_NF4_INTEGRATION_REPORT.md',
      audit.relative(P/'PASS_T_PHASE2B_QWEN_NF4_PROTOCOL_PREFLIGHT_REPORT.md'),
      audit.relative(P/'sampling_policy_candidate.json'),audit.relative(P/'private/candidate_manifests.json'),
      audit.relative(P/'private/timing.json'),audit.relative(P/'VIDEO_PROCESSOR_OBSERVATIONS.md'),
      audit.relative(B/'PASS_T_PHASE2B_QWEN_NF4_BLOCKER_REMEDIATION_REPORT.md'),
      audit.relative(B/'QWEN_NF4_PROTOCOL_DECISION_SHEET_V2.md'),audit.relative(B/'QWEN_NF4_VIDEO_ADAPTER_PARITY_REPORT.md'),
      audit.relative(B/'engineering_completion_receipt.json'),audit.relative(B/'capacity_results.json')]
    inspected=[]
    for n in sources:
        text=(R/n).read_text(encoding='utf-8');inspected.append({'path':n,'sha256':audit.sha(R/n),'lines':len(text.splitlines())})
    historical_inventory=audit.read(B/'protected_before_extended.json')['files']
    validator_identity={n:{'historical_sha256':historical_inventory[n],'current_sha256':audit.sha(R/n),
        'unchanged':historical_inventory[n]==audit.sha(R/n)} for n in [schema_path,validator_path]}
    assert all(x['unchanged'] for x in validator_identity.values())
    authority={
      'dataset':'artifacts/pass_t/phase2a/v2/external_returns/datasets/ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c/external_dev_gt.json',
      'sidecar':'artifacts/pass_t/phase2a/v2/exhaustive_reviews/adjudicated_7e28b9edf80a8e4da88caa66/adjudicated_dev_view.json',
      'policy':'artifacts/pass_t/phase2a/v2/contracts/EVENT_GT_ANNOTATION_POLICY_V2.md'}
    authority_sha={k:audit.sha(R/n) for k,n in authority.items()}
    assert authority_sha['dataset']=='ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c'
    assert authority_sha['sidecar']=='fa0133e4e49e54bdbac2ba59420d29b504e8bf219fa8179b57cd1b35261a005c'
    assert authority_sha['policy']=='c90f527eb01e3b320138961570c5647670536d3611feae3c4b7a1d10e33fdac4'
    # GT read only for authority shape, not to pick frames or optimize predictions.
    authority_objects={k:audit.read(R/n) for k,n in authority.items() if k!='policy'}
    audit.write('source_authority.json',{'sources':inspected,'historical_validator_identity':validator_identity,
        'phase2a':{'paths':authority,'hashes':authority_sha,'top_level_keys':{k:list(v) for k,v in authority_objects.items()},
                  'event_gt_used_to_tune':False},'model_weights_not_read_or_loaded':True})
    manifests=audit.read(P/'private/candidate_manifests.json')
    timing=audit.read(P/'private/timing.json')
    uniform=[m for m in manifests if m['name']=='UNIFORM_8_MULTI_IMAGE']
    if len(uniform)!=6:raise ValueError('Six-window UNIFORM_8 source inventory not recovered')
    cohort={t['item_id']:t for t in timing}
    sample=[]
    for m in uniform:
        t=cohort[m['item_id']];sampling=m['sampling']
        matches=[x for x in manifests if x['item_id']==m['item_id'] and x['name']=='UNIFORM_8_STORYBOARD']
        assert len(matches)==1 and matches[0]['sampling']['positions']==sampling['positions']
        sample.append({'item_id':m['item_id'],'opaque_id':m['opaque_id'],'source':t['source'],
          'native_window_frames':t['frame_count'],'positions':sampling['positions'],
          'source_frame_ids':sampling['native_frame_ids'],'native_pts_s':sampling['native_pts_s'],
          'source_hashes':sampling['source_hashes'],'existing_multi_media_paths':m['media_files'],
          'aliases':[Path(n).stem for n in m['media_files']],
          'permission':t['eligibility']['pilot_scoring_permission'],'multi_story_source_match':True,
          'matched_video_verified_for_this_window':False})
    sample.sort(key=lambda m:m['opaque_id'])
    assert all(x['source']!='test3' for x in sample)
    audit.write('prospective_uniform8_inventory.json',sample)
    proposed_order=[]
    for x in sample:
        for rep in ['MULTI_IMAGE_8','STORYBOARD_8','VIDEO_MATCHED_8']:
            key=f"PASS_T_PILOT_ORDER_V1/{x['opaque_id']}/{rep}/NONE/1"
            proposed_order.append({'item_id':x['item_id'],'opaque_id':x['opaque_id'],'representation':rep,
                'reference':'NONE','repeat':1,'order_hash':hashlib.sha256(key.encode()).hexdigest()})
    proposed_order.sort(key=lambda v:v['order_hash'])
    audit.write('prospective_run_order_18.json',{'status':'PROPOSED_NOT_APPROVED_NOT_FROZEN','rows':proposed_order})
    matches=[audit.read(B/'fixtures'/c/'fixture.json') for c in ['MULTI_8_P200704','STORY_8_P200704','VIDEO_SHORT8_P200704']]
    existing8match=all(f['source_frame_pixel_digests']==matches[0]['source_frame_pixel_digests'] for f in matches)
    assert existing8match
    md('QWEN_NF4_STRUCTURED_OUTPUT_FAILURE_REPORT.md',f'''
# Qwen NF4 結構化輸出失敗稽核

日期：2026-10-15。CPU-only，原始輸出不改寫。

## 母體與證據

PRIMARY = `v2_20261014_owned_tree`，11 條件 × (1 warmup + 2 measured) = 33 次生成，15 pass / 18 fail。Warmup 6/11 pass，measured 9/22 pass；沒有排除 warmup。ENGINEERING_HISTORY = `v1_20261014`，另 33 次，12 pass / 21 fail。CSV 有 66 列，以 population 欄分組；不能把 66 列當獨立研究樣本。CPU processor replay、mock、smoke 不納入母體。

兩輪所有 raw、iteration receipt、transport raw/receipt 都找回；66/66 strict replay 與歷史完整 error object 相同。schema/validator 檔案與歷史 inventory hash 相符。主要 completion receipt 驗證 422 檔，capacity_results 的 hash：`{s['receipt_integrity'][0]['capacity_results_actual_sha256']}`。原始 capacity、資源回條、prompt/rendered SHA、generation settings、allowlist 與 EOS 逐列記錄在 [primary_attempts.json](primary_attempts.json) 與 [CSV](QWEN_NF4_STRUCTURED_OUTPUT_AUDIT.csv)。早期回條獨立核對，不混入主要比例。

## 最先失敗與被遮住的錯誤

13/33 次 `EMPTY_REQUIRED_UNCERTAINTY`：`events[i].timing_uncertainty == ""`，違反 minLength=1，共 18 個事件欄位；5/33 次 `EMPTY_REQUIRED_CITATIONS`：`window_cited_frame_aliases == []`，違反 minItems=1。這 18 次最先失敗階段均為 SCHEMA，必填欄位未遺漏，值為空。

其中 11/33 次另有 `OTHER_SEMANTIC_ERROR`：宣稱已知狀態而 supporting_frame_alias=null。獨立逐欄診斷發現，但歷史 validator 的 schema early-return 尚未走到該檢查；不把它說成原本已回報的 semantic error，不修改模型回答以使 replay 繼續。全部 18 次的 exact path/constraint、次要訊息與來源 hash 见下表及 JSON。

33/33 raw 可嚴格解析為 JSON object，33/33 明確 EOS（末 token 在 receipt EOS IDs 中）；0 timeout、0 output cap、0 Markdown fence、0 不支持／未處理 alias、0 reference 當事件 alias、0 replay mismatch。EOS 是 token receipt 證據，不是看起來像完整 JSON 的推測。citation 檢查是 alias 與範圍核對，不是像素 grounding 正確性保證。

## 報告事件數與通過

{table(['解析事件數','Attempts','Pass','Fail','Token range','EOS / cap / timeout'],[(k,g['attempts'],g['passes'],g['failures'],g['tokens_range'],f"{g['eos_observed']} / {g['cap_reached']} / {g['timeout']}") for k,g in s['PRIMARY']['event_count_groups'].items()])}

結論：**SUPPORTED_DESCRIPTIVELY**。事件非空的 13 份全失敗；零事件 20 份中 15 pass / 5 fail。更多事件帶來更多 object/key/citation 及更多必填欄位，觀察到複雜度與失敗相關。可確認的直接原因是欄位約束違反；沒有確認「複雜度造成」違反。事件數與表示法、frame count、reference、視覺 token 都混雜。

通過回答全為 NO_CONFIRMED_EVENT；這是格式相容，不證明能偵測事件。gradient/checkerboard 合成 fixture 沒有本研究使用的人工物理 GT，不能把輸出事件數當真正事件數。

## 長度與結構

{table(['群組','Token range','Token median','Raw character range'],[(k,g['tokens_range'],g['tokens_median'],g['chars_range']) for k,g in s['PRIMARY']['pass_vs_fail'].items()])}

事件回答 344–633 tokens，零事件回答 174–285。最短失敗 174 tokens，比通過回答還短；最長回答 633/1024，未截斷。無證據以增加輸出 cap 作為優先修補。真實多事件仍可能超過 1024，該上限尚不具充分性保證。

複雜度定義：解析 event entries、distinct types、object/key/array element count、JSON depth、citation entries/aliases、missing required、populated optional、uncertainty 欄位與 timing alias fields。structural_complexity_score = object_count + key_count + array_element_count，是描述性計數而非經驗證難度指標。現在 optional_fields=0，missing_required=0；不能把空值稱為漏欄位。Malformed outputs 的 event_count 必須 UNKNOWN；本母體沒有 malformed case，不用 regex 猜事件數。

## 逐條件

{table(['Condition','Strict pass','Source / consumed','Visual tokens','Reference','Generated tokens'],[(c,f"{g['passes']}/{g['attempts']}",f"{next(r for r in rows if r['condition']==c)['source_frames']} / {len(next(r for r in rows if r['condition']==c)['consumed_aliases'])}",next(r for r in rows if r['condition']==c)['visual_tokens'],next(r for r in rows if r['condition']==c)['reference_count'],g['tokens_range']) for c,g in s['PRIMARY']['conditions'].items()])}

Multi-image：3/12 pass；Storyboard：5/9；Video：7/12。共用一個 V3 task+schema hash 與 V2 system hash、greedy、1024 cap；frame/pixel/token/reference 因子不同，不能作為表示法的因果效果。

Multi8 NONE 是 0-event 3/3 pass，Multi8 REF1 是 1-event 0/3 pass；Long118 low-budget NONE 0-event 3/3 pass，REF1 1-event 0/3 pass。兩對 source pixel-digests 與非 reference 設定相同（詳 source metadata）；reference 額外 54 visual tokens、67 input tokens且更改 prompt framing。沒有 reference alias 當 event 引用、target_id 漏寫或未知 alias。REF1 輸出較長且有事件，但不能由 3 次重複斷言 reference 造成 JSON failure；也不能以失敗降低而推論 NONE 更準。

## 每個主要失敗

{table(['Condition/iteration','Event count','Exact historical errors','Secondary diagnostic','EOS/cap','Raw source'],[(f"{r['condition']}/{r['iteration']}",r['features']['event_count'],'; '.join(r['historical_validation']['structural_errors']),' ; '.join(d['path']+':'+d['message'] for d in r['error_details'] if d['stage']=='DIAGNOSTIC_ONLY') or 'none','true/false',source(r['raw_path'])) for r in rows if not r['strict_pass']])}

空 timing 的 minLength 和空 citations 的 minItems 是明確規則。known-state/null-support 也有明確現行 semantic guard。真正內部認知機制（模型是否將空字串理解成沒有不確定性）未證實；不將一種合理猜測寫成 root cause。NEXT：prospective prompt field clarification + 獨立 target/time 語意檢視，再經授權做新合成 regression。歷史15/33永不改寫。

## 早期歷史

早期33：12 pass、21 fail；15次空 timing、6次空 window citations，14次被遮住的known-state/null-support。CPU監控第一輪曾只監控launcher；該CPUpeak無效，但raw/生成/EOS/validator回條仍可核對。兩輪並非独立dataset，差異展示greedy+seed也不能保證穩定性。本次audit首版matcher把 adapter後加citation_allowed_aliases誤當transport原欄位，造成匹配報警；中間產物保存在diagnostic_initial，核對程式來源後排除僅該後加欄位，其他resource欄位、raw SHA、耗時全部精確匹配。最终66次無遺漏；未改來源回條。
''')
    md('QWEN_NF4_PREDICTION_CONTRACT_SEMANTICS_REVIEW.md',f'''
# Prediction V1 語意檢視

權威：{source(schema_path)}；{source(validator_path)}；{source('artifacts/pass_t/phase2a/v2/contracts/event_gt_annotation_schema_v2.json')}。具體來源 hash 在 source_authority.json；這些不是本次新 schema。

| 欄位 | 現有約束 | 空/null/漏欄位 |
|---|---|---|
| events[i].timing_uncertainty | 每一個 event 必填、string、minLength=1，沒有 exact-time 例外 | 空字串invalid；null invalid type；漏寫required violation；明確寫無額外可觀察不確定性可合法，不必捏造不確定性 |
| timing.status | EXACT_SUPPLIED_FRAME / BOUNDED_SUPPLIED_FRAMES / TIMING_UNKNOWN oneOf，各有對應alias要求 | status是enum/const；不是timing_uncertainty文字欄的替代 |
| window_cited_frame_aliases | 每個window outcome都必填array，minItems=1，uniqueItems，Fdddd pattern | 空清單invalid，null invalid type，漏寫invalid；沒有abstention例外 |
| event.cited_frame_aliases | 每個event最少1alias | 只檢查存在/格式，不保證before-after兩種物理證據均充分 |
| supporting_frame_alias | schema允許string/null；validator已知state要求非null、unknown要求null | schema nullability與semantic guard為分層規則，沒有互相矛盾 |
| top uncertainty | 必填非空free text | 不限LOW等enum；可說association無法判斷 |

V1對四種結果都要求window引用：CONFIRMED_EVENTS支援事件、NO_CONFIRMED_EVENT支援觀察範圍、INSUFFICIENT_EVIDENCE引用可用但不足的視覺內容、TARGET_NOT_OBSERVABLE引用支持不可見的所提供內容。引用存在不是連續可評估性的證明。不存在可引用內容時应pre-generation input eligibility阻擋，不能捏造alias來通過。沒有科學理由只為把五份failure變pass而移除minItems。

無現行空欄位矛盾可證實；應先維持V1。科學語意仍須獨立確認：

- NO_CONFIRMED_EVENT與INSUFFICIENT_EVIDENCE的界線：前者需要該任務可評估而無確認事件，後者可因target association不足；現validator沒證明full-window assessability。
- NONE + TARGET_A是opaque名稱，不是物理定位。INSUFFICIENT_EVIDENCE配合uncertainty已可表達身分／局部關聯不足；TARGET_NOT_OBSERVABLE不能等同多手機中不知道哪支是target。
- event.target_association_uncertainty允許NONE/POSSIBLE/HIGH，validator未禁止HIGH搭CONFIRMED_EVENTS；未見本母體此缺陷，但其評估解讀需前瞻批准。evaluator僅NONE可known-event matching；不能強迫model填NONE。
- end_visibility是所供影格末端還是authorized window end？Long118只處理14張且可能沒看到最後一張，必须區分；未知尾段保持UNKNOWN。
- PICKUP/PLACEMENT目前validator沒有硬編before/after state型別轉換；UNKNOWN狀態可能合理，不能自行發明transition-state violation。
- `SCHEMA_SEMANTICS_AMBIGUOUS`用於上述政策待釐清，未歸責為這18份失敗的直接原因。沒有生成新版schema或validator。

引用分類：編碼clip内存在 ≠ processor有看見；只可引用processed aliases；static reference無event aliases，不可引用作事件。Timing/state aliases也受相同allowlist約束。診斷更檢查unsupported vs supplied-but-unconsumed；primary全零。timestamp correctness需private native PTS，raw只有alias無numeric timestamp，citation timestamp mismatch在本母體不可直接量測。

關於狀態／物理猜測：11份known-state無支持是現規則可直接確認的錯誤。某回答宣稱placement卻before_state UNKNOWN，在V1未被禁止，僅列advisory，不能自造fail。安全assertions=false只是聲明，不能證明沒有視覺推理越界。

修補層級：先版本化prompt清楚說明非空理由、每種outcome的引用、known/unknown state支持及NONE下target ambiguity。獨立ontology語意審閱若真的發現不可表達且必要的狀態，才另提schema V2+validator版本+舊新結果分離。本任務不更動任何現行契約。
''')
    md('QWEN_NF4_STRUCTURED_OUTPUT_REMEDIATION_OPTIONS.md','''
# 最小修補選項（提案，未實作）

優先：PROMPT_CHANGE_PROPOSED，維持Prediction V1、V2 JSON system與runtime。另行獨立target/time語意審閱，不為歷史pass rate改schema。

| Group | Evidence | Root-cause confidence | Interpretation | Minimal repair | Schema / prompt / decoding | Risks | Required approval | Limited regression |
|---|---|---|---|---|---|---|---|---|
| 空timing_uncertainty | 13次、18event fields | 規則違反已證實；內在生成機制未知 | 非空free text，exact timing亦必填 | PROMPT_CHANGE_PROPOSED：說明精確時可寫無額外可觀察不確定性，不捏造uncertainty | 否 / 提案 / 否 | 可能誘導confidence措辭、改event count | 批准單因子prompt候選與離線preflight | 凍結合成inputs，baseline/candidate雙臂，原strict parser |
| 已知state卻null支持 | 11次secondary | 已由既有guard規則證實 | known requires alias；unknown requires null | 同一prompt說明保守state證據規則 | 否 / 提案 / 否 | 可能偏向UNKNOWN；不可強制known state | 與上項同一prompt intervention | before/after/last nullability CPU tests及原樣保存GPUraw |
| 空window citations | 5次 | minItems違反已證實 | 所有outcomes都需引用，引用不保證連續可評估 | 同一prompt说明引用可用支持/不足證據，不補假alias | 否 / 提案 / 否 | 虛構引用可通過格式，仍須grounding review | 同上 | no-event/uncertain contract CPU tests；GPU不得強制答案 |
| Target association / end visibility | 無此primary直接fail證据；政策有空隙 | SCHEMA_SEMANTIC_REVIEW_REQUIRED | NONE和opaque target无物理辨識保證 | 獨立ontology review，先以現INSUFFICIENT_EVIDENCE表达 | 只有獨立論證必要才提新schema / 待批准 / 否 | 影響scientific task definition | 人工批准語意；另任務，不能與格式放寬混在一起 | ambiguous-target、末端未見 CPU fixtures |
| Syntax / fences / truncation | primary 0/33 | 目前無直接需要 | NO_CHANGE_REQUIRED | decoding作後續備選，不優先 | 否 / 否 / 目前否 | constrained decoding不能保证semantic/citation正确，新增engine差異 | 未來若needed另批DECODING_CHANGE_PROPOSED | syntax only新版本，保留semantic validator |
| Alias scope | primary unsupported 0/33 | 無直接根因 | NO_CHANGE_REQUIRED，維持processor allowlist | 只在promptclarification重申已處理alias，無alias修補器 | 否 / 可隨同fieldclarification / 否 | 列表valid不等於精確grounding | 同prompt批准；不得改raw | supplied-but-unprocessed、reference alias拒絕CPUfixture |
| Output/time cap | 33EOS、max633/1024、zero timeout | INSUFFICIENT_EVIDENCE為調大cap的依據 | NO_CHANGE_REQUIRED for existing configuration | 保留1024提案，後續多事件需另檢capacity | 否 / 否 / 否 | 真實多事件仍可能超cap，timeout上限非保證 | 未來若需要RUNTIME_BUDGET_CHANGE_PROPOSED另批 | 另固定schema complexity bounds，不adaptive retry |

不提供修補patch，不新增full-schema答案example。全schema example可能把事件數與outcome向單一模板偏移；目前所有pass都是零事件，避免用confirmed或no-event例子造成答案偏置。候選prompt只寫規則與條件语意，確切文字需要下一任務審核、hash和批准。

下一授權任務名稱：`PREPARE_QWEN_NF4_PROMPT_CLARIFICATION_AND_MATCHED8_CPU_PREFLIGHT`。它應只產生版本化候選prompt、NONE語意提案、matched8 CPU輸入/processor計畫和receipt，不執行GPU、freeze或real pilot。待候選定稿，另授權 `RUN_QWEN_NF4_MINIMAL_SYNTHETIC_REGRESSION`。不是本audit授權。
''')
    md('QWEN_NF4_MINIMAL_SYNTHETIC_REGRESSION_PLAN.md','''
# 最小合成regression設計 — 未執行、未批准

先決：exact candidate prompt完成；Prediction V1/V2 system維持；8-frame三表示法CPU模型消費alias證明及input/hash inventories齊全。若gate失敗，不替換Video為Multi、不改frames、pixels或encoder，stop該regression計畫。

固定資料：沿用已保存的8張gradient/checkerboard synthetic source，digest一致；無真實Phase2a pixels、GT、答案或外部服務。Multi8 8張fullcontext、Storyboard8 3col/480×270+32label、Video8 FFV1/AVI 4fps，encoder時間0…1.75s。需要先确认processor indices0…7、temporal grid4、alias8個。最低限度不新增實體場景/事件GT；測的是格式可能性。這些输入不一定誘发所有event branch，因此即使全部pass也不能聲稱完整事件schema穩定；未走到的分支標UNTESTED。

唯一主要變因：task-level field clarification prompt baseline V3 vs proposed新版本。V2 system、schema、checkpoint、NF4/BF16/SDPA、processor200704、sampling、greedy、seed42、1024、300s generation/330 request/120 load均固定。三表示法分别是部署條件；不是三個獨立sample。計畫同時兩個prompt arms，每arm每rep 1warmup+2measured：3×2×3=18calls（6warmup+12measured）。不可另加未登記生成。單臂9calls能確認可行，但無同時baseline對照且歷史greedy不穩，因此不建議將其作效果證據。

固定run order：依sha256(SYNTH_REGRESSION_V1/representation/prompt_sha/iteration)排序；先公布hash/index並逐臂warmup在該臂measured之前。沒有依結果重試，沒有轉換模型/精度/像素。可接受預先批准的一次「generation開始前」transport/load infra retry，必須記錄證据；generated任何token後重試一律零。

所有raw、resource、generation-start、token EOS、alias observer、schema/citation/semantic結果、ownedtreeCPU和PyTorch/globalVRAM分開保存。先報strict各stage與branch coverage，再看event_count descriptive。parser不去fence、不補字、不替換引用。Fail照保存，不為有利output挑選迭代。

若candidate需要schema改動，這個prompt-only計畫失效，必須另立semantic/schema版本與單因子研究。若需要新的decodingengine或tokenbudget，同樣分開。無適應性加calls；沒有synthetic模型accuracy聲稱。GPU執行必須另收到 `RUN_QWEN_NF4_MINIMAL_SYNTHETIC_REGRESSION` 明確授權。
''')
    timing_rules='''
時間規則為prospective decision，未改現行evaluation.py：GT schema status有EXACT_OBSERVED_TRANSITION、BOUNDED_BY_BEFORE_AFTER_EVIDENCE、TIMING_UNCERTAIN，均有start/endframe+native timestamp，但status決定可用性，不能單看數值是否相等。

- 精確GT：必須確保對應source frame/timebase一致，優先source PTS tick+time_base有理數比較；僅有JSON數字時Decimal(str(number)) exact來源表示，不新加float epsilon。0s是無額外容許量，不把十進位近似說成sensor exact；缺少timebase/frame對照須標UNRESOLVED。prediction點與GT點的絕對差；prediction bounded interval內含GT點僅叫interval-compatible，單獨報interval寬度，不等於exact localization。
- bounded GT：確認event_time是人工存的bounded欄位，不能拿整個BEFORE/AFTER evidence envelope自行扩大。兩interval最短距離 max(0, max(start)-min(end))，與所有0/.2/.5 threshold分別比較。point在bounded interval内也距離0（現require_overlap分支會拒絕這情況，需獨立review）；報交集/寬度/點或區間類型，不能稱精確時間正確。
- TIMING_UNCERTAIN GT或TIMING_UNKNOWN prediction：時間matching UNDEFINED，event-type可独立描述；不能把不確定GT時間包當真值。
- 每窗event_type且target_association_uncertainty=NONE且citation valid才列time-compatible邊；一對一最大匹配，先最大cardinality，再最小總distance，再按GT/pred ID決定tie。當前greedy matcher未證明max-cardinality，下一獨立CPU regression需測反例；本次不實作或計分。
- 0.0/0.2/0.5全報，無primary最佳threshold選取。0.2僅sensitivity，0.5較寬鬆；不以UNIFORM_8 gap/2增容。分開報event-type、GT時間compatibility、prediction uncertainty、citation validity、target association、sampling gap。no exact timing保証。
'''
    media_rules='''
UNIFORM_8使用現builders.uniform_positions：位置round(i*(N-1)/7)，Python ties-to-even，8個唯一位置、包含首末；不足8frame則阻擋，不dup補幀。不讀GT選frame，不改offset。所有source frame ids/native PTS/hashes/aliases在prospective_uniform8_inventory.json，現Multi/Storyboard六窗都同選8張。

VIDEO_MATCHED_8提案：把同一8張source畫面依序lossless FFV1/AVI編碼，4fps，encoded frame k時間k/4，8frames 0…1.75s；私有mapping保存每個k→original source frame index/native PTS/alias/hash。這是時間壓縮/非等距native時序再CFR編碼，不可把播放器秒數當source秒數。processor4fps官方sampling、實際observer必須取indices0…7，各2frame temporal grouping，grid temporal4；引用允許8個source aliases，exact citation只允許有直接可辨識證据，temporal merge不保证精確區分每張frame。native PTS可用於private evaluator，模型不得利用clip 0…1.75時長猜source timing。

既有VIDEO_SHORT8同source digests的技術實驗已證明這種4fps8frame模態可消費8個aliases；不是fullclip118frame=14consumer的替代。六個真實窗尚未有matched8建構/processor receipts，因此 `VIDEO_MATCHED_8_NOT_YET_VERIFIED`。現build_video會編所有source frames，不能只把fullclip條件改名字成matched8。後續需独立versionedbuilder/alias timestampmapping與CPUprocessor预flight；必要時新合成GPU確認，不在本次做。

Storyboard提案沿既有3col、480×270tile+32label，8frame canvas1440×906；processor cap200704針對整張montage，target實際縮小，低cap曾為240visualtokens。Multi8每張336×588=197568pixels，2016visualtokens；Video8同spatialcap、4temporalgrids=1008tokens。frame/timecoverage可matched，visual information/target pixels/patchcompression不matched；不可把差異全歸表示法。937664 video是另pixel sensitivity，Uniform12/16是另density sensitivity，均不加入primary18runs。
'''
    decisions=[
      ('01 Baseline','VERIFIED：歷史health/revision資產metadata','原Qwen2.5-VL7B NF4 double/BF16/SDPA；revision cc594898137f460bfe9f0759e9844b3ce807cfb5','不換AWQ/3B','只有local revision provenance；無官方獨立checksum','REQUIRES_APPROVAL'),
      ('02 Prompt/system','VERIFIED：V3 task/schema與V2system各1hash','保留baseline，候選prompt另版本','原V3直接pilot','13event全失敗','REQUIRES_APPROVAL'),
      ('03 Repair','VERIFIED：13空timing、5空cite、11secondary','PROMPT_CHANGE_PROPOSED；V1schema維持','独立schema review若必要','prompt改後branchcoverage未測','REQUIRES_APPROVAL'),
      ('04 Frame count','VERIFIED：8frame各3/3pass','PROPOSED UNIFORM_8','12/16另sensitivity','passing均no-event，非準確度','REQUIRES_APPROVAL'),
      ('05 Sampling','VERIFIED：existinguniform8 source inventory','round/endpoint/tie算法原樣','fixedFPS另實驗','coarse gap漏短事件','REQUIRES_APPROVAL'),
      ('06 Video matched8','VERIFIED synthetic8 indices0..7；DEV未建','PROPOSED FFV1/AVI4fps8sourceframes','維持UNRESOLVED，不替換fullclip','VIDEO_MATCHED_8_NOT_YET_VERIFIED','UNRESOLVED'),
      ('07 Storyboard','VERIFIED：3col/480×270+32','PROPOSED 1440×906 canvas8frame','其他layout另版','整張縮圖降低targetpixel','REQUIRES_APPROVAL'),
      ('08 Pixels','VERIFIED：200704有效上限','PROPOSED common200704+actualgridreceipt','高cap另pixelstudy','不匹配各representation總token','REQUIRES_APPROVAL'),
      ('09 Reference','VERIFIED NONE已有offline六窗','PROPOSED NONE commonprimary','5-windowpaired另授權','TARGET_A opaque≠localization','REQUIRES_APPROVAL'),
      ('10 Target ambiguity','VERIFIED I_E+uncertainty可表达','PROPOSED unresolved target→INSUFFICIENT_EVIDENCE','独立newschema若必要','confirmed HIGH目前validator允許','UNRESOLVED'),
      ('11 Fairness','VERIFIED 2016/240/1008tokens','matchedsource/time、部署條件描述比較','匹配token另protocol','不能純representation因果聲稱','REQUIRES_APPROVAL'),
      ('12 Output budget','VERIFIED max633/1024、无cap','PROPOSED 1024','另budgetstudy','真實multi-event未驗證','REQUIRES_APPROVAL'),
      ('13 Decoding','VERIFIED do_sample=false seed42','PROPOSED greedy，inactive temperature/top-p','decoding另study','seed不保證determinism','REQUIRES_APPROVAL'),
      ('14 Repeat','VERIFIED repeatedsynthetic會變動','PROPOSED 1 per DEV condition','2repeat另stabilitystudy','一次只表可能性','REQUIRES_APPROVAL'),
      ('15 Deadlines','VERIFIED existingprobe generation300s','PROPOSED load120/gen300/request330','另budgetproposal','18×330=99min不含load','REQUIRES_APPROVAL'),
      ('16 Retry','VERIFIED preservingfailedraw工具存在','PROPOSED generation0、pre-generationinfra最多1','完全0infra retry','開始判定/ownedPID證明須固定','REQUIRES_APPROVAL'),
      ('17 Run order','VERIFIED deterministic proposed18list','PROPOSED SHA排序固定，不因結果改','另固定humanorder','modelsession順序可影響latency','REQUIRES_APPROVAL'),
      ('18 Tolerance','VERIFIED三敏感度已列草案','PROPOSED全報0/.2/.5','獨立tasktolerance另提','沒有選最好或gap/2','REQUIRES_APPROVAL'),
      ('19 GT time matching','VERIFIED status三種；現matcher有空隙','PROPOSED status-aware最大一對一closedinterval','保留UNRESOLVED直至CPU規則定稿','Decimal/timebase、greedy與pointinside需修復審查','UNRESOLVED'),
      ('20 Cohort','VERIFIED 6clean；test3excluded','PROPOSED固定6窗×3×1=18','不加test3','DEVselected，session independence未知','REQUIRES_APPROVAL'),
      ('21 Analysis','VERIFIED authority用途限制','PROPOSEDknown-only/negativealerts/descriptive','正式metrics禁止','formaleligible0、CAUSALITY_UNVERIFIED','REQUIRES_APPROVAL'),
      ('22 Hashes','VERIFIEDhistoricalcapacity/authority','PROPOSEDfinalprompt/config/input/order全hash','目前不freeze','finalcandidate與matchedvideoassets尚缺','UNRESOLVED'),
      ('23 Regression','VERIFIED allreported-eventsfail','PROPOSED先候選preflight後18syntheticcalls','無regression直接pilot風險高','regression未批准/未執行','REQUIRES_APPROVAL'),
      ('24 Freeze','VERIFIED humanapproval本task未給','PROTOCOL_NOT_READY_TO_FREEZE','補完後独立freeze任務','兩道human gate仍存在','UNRESOLVED'),
    ]
    audit.write('decision_table.json',[dict(zip(['decision','verified_evidence','proposed_choice','alternatives','risk','human_approval'],d)) for d in decisions])
    md('QWEN_NF4_FINAL_PILOT_DECISION_DRAFT.md',f'''
# 首次Qwen NF4 pilot決策草案

**PROPOSED_NOT_APPROVED_NOT_FROZEN；formal real pilot 0。**

{table(['Decision','Verified evidence','Proposed choice','Alternatives','Remaining risk','Human approval'],decisions)}

## 六窗用途

{table(['Source','Item ID','Opaque ID','Native frames','Usage'],[(x['source'],x['item_id'],x['opaque_id'],x['native_window_frames'],x['permission']) for x in sample])}

test1 W03/W05是同一窗已dedup、test2 W01、test5 W01只case-level false-event alerts；known-negative附加独立review仍不足，不可population FP率。test5 W05/test7 W05只人工已支持PICKUP conditional matching，額外event UNEVALUATED；test8 W07只uncertainty/abstention描述，不能binarytruth；test3 W07從inference/scoring排除。formal_benchmark_eligible=0，CAUSALITY_UNVERIFIED，沒有accuracy/precision/recall/F1/hallucination_rate/統計顯著或泛化宣稱。raw dataset須與sidecar合讀，不產生新GT。

## Sampling與表示法

{media_rules}

## Target NONE

NONE是可提案的commonprimary，18run無staticref、無refextra tokens/額外資產授權問題。它沒有建立目标身分。若未能將動作唯一關聯到指定target，INSUFFICIENT_EVIDENCE + explicit uncertainty，不把generic scene event變target event；不可把TARGET_NOT_OBSERVABLE和identity ambiguous混用。現schema有可用表达，因此没有必然schema-change blocker，但语意humanapproval仍UNRESOLVED。五窗referencepaired另研究且另授權；不包含於primary。

## 時間判定

{timing_rules}

## 執行設定／預算提案

6×3×1=18generations（不是18獨立event samples）。max_new_tokens1024，do_sample=false，seed42不保證determinisim；load120s、gen300s、request330s。18request上限99分鐘，若六模型session各load120上限再12分鐘；pre-generation infra retry最多一，若每session重載再多最多12分鐘。額外CPUprep、kill/unload和資源不足等待未包含，未設其gate不可宣稱globaldeadline。未批准任何retry。

歷史generation4.14–175.04s（含warmup），measured上至87.28s，長輸出與硬體排程均不穩。可供預留約2–3小時工程時段（假設有限prep、既有環境穩定、至多六次pre-generationreload），不是runtime保證或由DEV量測得出的range，超時仍按原gate結束。不得保證30分鐘。cap1024沒有真實multi-event充分性證明；更長不能由本18failure推得有用。

失敗規則：OOM preserve receipt→runtime failure，不自動減frame/pixel或換精度；timeout preservepartialraw並標stage，不依答案增deadline；invalidJSON/schema/citation保持原字串，strictfailure不是no-event，no-qualityretry；target ambiguity允許abstain。generation開始後0retry；infraretry最多1仅token生成前有可查證start boundary。實驗repeat=1與重試分別列。每次保存attempt，不因favorable結果改runorder。

Hash要求：exact model asset metadata/manifests、prompt/system/schema/validator/adapter source、generation與resource設定、cohort/eligibility/sidecar、每個selectedsource frame+mapping、renderedinput/processedalias/grid、native與encodedtimeline、final18order；目前只有歷史版本與prospective order，候選prompt與matchedDEVassets尚無finalhash。

Gate1：completeprotocol review後另授權freeze task；Gate2：有效freeze receipt後另授權RUN_PHASE2B_EXPLORATORY_PILOT。此task不通過任一gate。
''')
    md('QWEN_NF4_FREEZE_READINESS_AUDIT.md','''
# Freeze readiness

**PROTOCOL_NOT_READY_TO_FREEZE**。

已完成：historicalbaseline/模型revision metadata、33raw完整性、66strictreplay、18失敗/secondary分類、條件數核對、GT authority與已排除cohort核對、prospectiveuniform8原frame inventory、18run order提案。無模型load／新generation。

| Blocker | Minimal next action | Current state |
|---|---|---|
| 事件回答沒有strictpass；必填欄位反覆空 | 审查单因子promptclarification候選，另批固定syntheticregression | 未生成候選prompt／未授權 |
| matchedVideo8真實6窗沒有build/processor/alias receipts | 版本化8frame encoder/mapping提案與CPUprocessorpreflight，防止fullclip替換 | VIDEO_MATCHED_8_NOT_YET_VERIFIED |
| NONE target opaque定位與abstention語意 | 人工批准有限任務意義與INSUFFICIENT_EVIDENCE解讀，confirmed HIGH仍需明確政策 | UNRESOLVED |
| native GT point/interval/uncertain matching | 独立CPUtest pointinside/endpoint/uncertain/最大一對一，source PTS精度 | 現evaluator不能直接當新規則完成 |
| settings/layout/pixels/timeouts/retry/session/order | 固定final decisions，不用這次audit充作批准 | REQUIRES_APPROVAL |
| hashinventory incomplete | candidateprompt/新input/config及codefreeze前hash核對 | UNRESOLVED |
| 大部分strictnegative缺额外独立逐格review、無exhaustivepositive/placement | 保留exploratory用途，後續另資料品質task；非要改成formal | formaleligible0 |
| 正式humanapproval | completionprotocol審閱后另授權freeze；freeze成功後再獨立RUN_PHASE2B_EXPLORATORY_PILOT | 沒有推定批准 |

第一個建議授權：PREPARE_QWEN_NF4_PROMPT_CLARIFICATION_AND_MATCHED8_CPU_PREFLIGHT（候選規則與離線證明，不GPU）。第二個：RUN_QWEN_NF4_MINIMAL_SYNTHETIC_REGRESSION，精確candidate/hash定稿後再批。全部關鍵設定與語意經人工選擇後，才可準備freeze，接著pilot另一道gate。
''')
    md('PASS_T_PHASE2B_QWEN_NF4_OUTPUT_AUDIT_REPORT.md',f'''
# FindMind Pass T Phase2b — 輸出失敗稽核與pilot決策

2026-10-15。狀態：`PASS_T_PHASE2B_QWEN_NF4_OUTPUT_AUDIT_COMPLETE_AWAITING_USER_DECISIONS`。

## 回答九個問題

1. **18次為何失敗？** 13次event timing_uncertainty空字串、5次window引用空清單；全部先被schema擋。另11次既有known-state支持規則違反被early-return遮住，已獨立列出。
2. **事件多／結構複雜是否相關？** SUPPORTED_DESCRIPTIVELY：0事件20次中15pass；1事件8次全fail；2事件5次全fail。更多欄位與更多error機會可解釋觀察，但沒有因果證據；與frame/representation/reference混雜，非33獨立科學樣本。
3. **schema壞、格式、引用、截斷還是其他？** 33份strict JSON皆可解析，EOS皆有token證據、zero cap/timeout。直接是mandatory value錯誤；引用問題是清單空，不是不存在或未看過alias。11次semantic缺support。未發現導致這18次的schema自相矛盾或parse/instrumentation錯誤；完整replay一致。
4. **該改schema嗎？** 沒有以這批failure為依據的科學必要。非空文字可說無額外可觀察不確定性，引用規則可按任務解釋，無須為pass rate放寬。target/outcome/time語意仍需独立review；必要才另提versionedcontract。
5. **最小repair？** PROMPT_CHANGE_PROPOSED：以新task prompt明示非空uncertainty、每種outcome引用、known/unknown state與target ambiguity；保留V1schema/V2system/runtime。没有寫promptpatch，也沒有constraineddecoder或增加budget。
6. **三種8frame能同source嗎？** 現Multi/Storyboard六窗uniform8已核對一致，synthetic8三者source pixel digests一致，Video8原receipt確實消費indices0..7。DEV六窗matchedVideo8仍未建/verify，VIDEO_MATCHED_8_NOT_YET_VERIFIED；native→CFR時序、alias與2frame temporal merge必须单独核對。共同8frames≠共同pixel/tokenbudget。
7. **NONE可用嗎？** 可以作有限firstexploratory提案，6窗同政策，無refextra tokens；無target identity證明。association不明時INSUFFICIENT_EVIDENCE，而非強迫event或把identityambiguous當targetnotobservable。该語意仍待人工批准。
8. **Freeze缺什麼？** 候選prompt及另批regression、matchedDEVvideo receipts、targetNONE语意批准、point/interval/uncertain/nativePTS与一對一matching、finalsetting/retry/order/assets hashes、完整humanapproval。formaleligible仍0、causality未驗證。
9. **精確下一任務？** `PREPARE_QWEN_NF4_PROMPT_CLARIFICATION_AND_MATCHED8_CPU_PREFLIGHT`，需你另行授權。先做候選prompt與CPUpreflight，再以固定hash另批18callsyntheticregression；随后freeze審閱和realpilot各自授權。此audit不授權任何生成或freeze。

## 交付入口

- [逐次CSV（66列，primary/history分欄）](QWEN_NF4_STRUCTURED_OUTPUT_AUDIT.csv)
- [完整failure與18案來源](QWEN_NF4_STRUCTURED_OUTPUT_FAILURE_REPORT.md)
- [契約語意](QWEN_NF4_PREDICTION_CONTRACT_SEMANTICS_REVIEW.md)
- [最小修補矩陣](QWEN_NF4_STRUCTURED_OUTPUT_REMEDIATION_OPTIONS.md)
- [未執行syntheticregression設計](QWEN_NF4_MINIMAL_SYNTHETIC_REGRESSION_PLAN.md)
- [24項human決策、18run pilot草案](QWEN_NF4_FINAL_PILOT_DECISION_DRAFT.md)
- [Freeze未就緒](QWEN_NF4_FREEZE_READINESS_AUDIT.md)
- [保存／測試驗證](QWEN_NF4_OUTPUT_AUDIT_PRESERVATION_REPORT.md)

最後33 = 11warmup+22measured、15/33strictpass；較早33 = 12/33，只engineeringhistory。全部raw/token/resource與來源回條已核對，未把synthetic輸出當真實event accuracy。actualPhase2a pilot0，newmodelcalls0。

十八run提案：6clean DEV窗×Multi8/Storyboard8/MatchedVideo8×repeat1，UNIFORM8、NONE、200704pixelcap、1024output、greedyseed42、load120/gen300/request330秒、generationretry0，所有0/.2/.5sensitivity全報。這些是PROPOSED；不是已批准配置。request上限99分鐘未含load/prep/retry，無30分鐘承諾。

早期文件採不同階段名稱V1/V2/V3，這裡primary明確指20261014_owned_tree capacityround、V3共用taskcontract+V2formatting、PredictionV1。全部來源与摘要hash在source_authority.json；已核對finalcapacity receipt與schema源碼版本，不靠舊摘要推定結果。
''')
    print(json.dumps({'reports_written':8,'uniform8_windows':len(sample),'proposed_order':len(proposed_order),'source_files_inspected':len(inspected),'validator_source_identity':validator_identity}))

if __name__=='__main__':main()
