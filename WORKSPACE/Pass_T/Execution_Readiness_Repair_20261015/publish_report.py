"""Publish repair reports; no model/GT/media/runtime imports."""
import sys
sys.dont_write_bytecode=True
import json,hashlib,datetime,re
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
def read(n):return json.loads((OUT/n).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def put(n,v):(OUT/n).write_text(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def link(label,path):return f'[{label}]({Path(path).as_posix()})'
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(v).replace('|','\\|').replace('\n',' ') for v in row)+' |\n' for row in rows)
tests=read('CPU_TEST_RESULTS.json');changes=read('SOURCE_CHANGE_MANIFEST.json');draft=read('DRAFT_CONFIGURATION_CANDIDATE.json')
elapsed=re.search(r'Ran 53 tests in ([0-9.]+)s',(OUT/'cpu_tests_final.log').read_text(encoding='utf8')).group(1)
assert tests['tests_run']==53 and not tests['failures'] and not tests['errors'] and not tests['model_modules_loaded'] and not tests['guard_denials']
assert not changes['protected_changes']
assert changes['git_before']['head']==changes['git_after']['head'] and changes['git_before']['index_sha256']==changes['git_after']['index_sha256'] and changes['git_before']['staged_diff_sha256']==changes['git_after']['staged_diff_sha256']
for x in changes['files']:assert sha(ROOT/x['path'])==x['after_sha256']
dh=hashlib.sha256(canonical(draft)).hexdigest()
confirmation='APPROVE_PHASE2B_V1D_FREEZE '+dh+' NO_EXECUTION'
assert draft['status']=='DRAFT' and draft['protocol_approval'] is None and draft['execution_authorization'] is None
status='ENGINEERING_READY_FOR_HUMAN_FREEZE_REVIEW'
source_table=table(['File','Before SHA-256','After SHA-256'],[[link(x['path'],ROOT/x['path']),x['before_sha256'] or 'NEW FILE',x['after_sha256']] for x in changes['files']])
matrix=table(['Blocker','Responsible interface','Repair','CPU verification','Remaining scope'],[
 ['A / T01','video_array_bridge.prepare_video_array + v1d_protocol.bridge_eligibility','新增real_pilot_mode=FROZEN_V1D_PILOT_V1；驗frozen/21decision approval/獨立執行授權、V1D/V2/schema/runtime/bridge hashes及call/alias/PTS；保留synthetic原guard','缺freeze、缺授權、hash/rep/alias/PTS/prompt/system/預算/洩漏遭改均拒絕；MOCK records在真正preprocessor之前拒絕','真實array/processor/GPU仍未執行；8source→4unit、FRAME_MATCHED_ONLY不變'],
 ['B / T02','v1d_protocol + v1d_execution + explicit CLI','獨立versioned draft/freeze/run介面；三格式in-process共18call；不走legacy prompt_path/HTTP/AVI fallback；21項仍PENDING','真實metadata dry-run成功；18call軟體mock一個runtime factory；授權nonce lease與call claim防重播；預設CLI不執行','未建立human-approved frozen protocol；currentmedia與weights未驗證'],
 ['C / T04','evaluation.match_known_events / CLOSED_INTERVAL_GAP_V1','版本化closed-interval gap；historical default LEGACY_OVERLAP_V0仍原行為','點內/端點/前後/overlap/touch/disjoint/zero-width；0/.2/.5邊界與一對一、unknown/缺時/關聯不確定測試通過','這是待核准candidate semantics，不是已核准科學決策'],
 ['Strict output / T03','v1d_outputs + record_call_result/evaluate_recorded_call','原raw durable/exclusive保存，5stage分開，schema early return標NOT_ASSESSED；invalid與缺結果不得進matching；定性另存','invalid/schema/semantic/citation/absent/有效NO_EVENT分支；mock18call中2invalid仍保留並繼續；nonexhaustive額外預測UNEVALUATED','不宣稱schema/temporal match證明physical correctness'],
 ['Media / M01','draft_protocol/validate_draft/load_envelope','pin來源metadata、全authorized-list SHA/boundary、Uniform8、8alias/nativePTS及sourcePNG/storyboard hashes；執行時先授權再開檔驗bytes','現有文字metadata一致性核對；未授權loader在任何媒體開檔前拒絕；mock receipt綁protocol/auth/source','PENDING_AUTHORIZED_EXECUTION；本次沒有重新hash/read真實媒體或原始source video']])

put('BLOCKER_RESOLUTION_MATRIX.md',f'''# Blocker Resolution Matrix

Task `PASS_T_PHASE2B_QWEN_NF4_EXECUTION_READINESS_REPAIR`；2026-10-15。**{status}**。

{matrix}

工程完成不等於protocol approval、freeze、real execution或科學驗證。歷史review package未修改。新source manifest和draft取代舊候選的runtime hash適用性；舊核准識別句不可機械沿用。
''')

put('MATCHER_SEMANTICS_REVIEW.md',f'''# Matcher Semantics Review

## Discrepancy before repair

舊 `evaluation._compatible` 在GT有寬度時先計overlap length。若預測是GT區間內的point，overlap長度=0，舊碼改算到endpoint的距離，可能大於0並拒絕tolerance0。這是程式邊界問題；沒有讀真實GT判定六窗是否觸發。

## Versioned candidate implementation

- 新policy：`CLOSED_INTERVAL_GAP_V1`。點t與GT[a,b]：`max(a-t,0,t-b)`；GT[a,b]與prediction[c,d]：`max(c-b,a-d,0)`。
- 使用 `Decimal(str(timestamp))` 做固定十進位容差比較，沒有私自epsilon。既有native PTS數值原樣使用，不重建或校準GT。
- Point在區間內／端點、interval相交／接觸均gap0；disjoint為最近間隙。missing、nonfinite、反向interval不match；unknown時間與uncertain target association不match；沒有event citations也不match。
- 同type、greedy按(distance,GT index,pred index)排序，GT/pred各用一次。不是optimal maximum-cardinality。
- `match_known_events` 預設仍 `LEGACY_OVERLAP_V0`，歷史 `_compatible` 本體未變。只有顯式新policy才改用新公式；新pilot draft另pin此policy，且須人類核准。未知policy拒絕，不默認fallback。
- 新policy要求 `bounded_interval_overlap_required=False`。0、0.2、0.5秒在新gated evaluation均輸出，不選事後最好的tolerance。
- BEFORE/AFTER evidence brackets是時間相容區間，不是物理動作duration；不創midpoint、不推持續狀態。nonexhaustive已知PICKUP仍只match已支持子集，額外pred為UNEVALUATED；uncertain window不當negative。

CPU tests包含上述幾何/邊界、0.1→0.3的0.2秒邊界、略超界不match、duplicate一對一、missing/unknown/insufficient association與legacy復現。這些是software mock timing，不是physical-event GT。

Source差異：{link('EXACT_SOURCE_DIFF.patch',OUT/'EXACT_SOURCE_DIFF.patch')}；最終測試共53/53通過。
''')

put('STRICT_INVALID_GATE_REPORT.md',f'''# Strict-invalid Gate Report

## Implemented caller policy

Protected `predictions.parse_raw/validate_prediction`與Prediction V1 bytes未變。新增 `v1d_outputs.classify_output` 呼叫原始介面，不複製／放寬validator。

{table(['Input / condition','Classification','Authoritative matching'],[
 ['No raw output','ABSENT_PREDICTION；各stage NOT_ASSESSED','不可進；不推NO_EVENT'],
 ['Malformed/duplicate-key/nonfinite/nonobject/invalid UTF8','INVALID_JSON；JSON/FULL FAIL','不可進；不做JSON repair'],
 ['Schema failure','STRICT_INVALID；SCHEMA FAIL；SEMANTIC/CITATION NOT_ASSESSED_DUE_TO_SCHEMA_FAILURE','不可進；不把early-return空error list誤標PASS'],
 ['Semantic / citation failure','SCHEMA PASS；分別記SEMANTIC/CITATION FAIL；FULL FAIL','不可進；不發明citation'],
 ['All original strict checks pass','VALID_*；FULL PASS','仍需frozen source/provenance及GT用途資格'],
 ['Valid zero-event outcome','VALID_NO_CONFIRMED_EVENT','與invalid/absent分開；不從格式推physical truth'],
 ['Runtime receipt mismatch','Raw及原receipt保存；authoritative_prediction=None','不可進；保留validation stage與receipt問題的區別']])}

`record_call_result` 用exclusive+flush+fsync先保存raw，接著保存原receipt，再分類。strict-invalid不轉成NO_EVENT或自動FN；定性review固定另列UNREVIEWED/DESCRIPTIVE_ONLY，沒有生成新人工標籤或GT。

`evaluate_recorded_call` 驗frozen/auth/raw/receipt綁定與window用途，再經gated evaluation；不自行讀GT，只有私有caller傳入的核准record可用，且從不進model payload。兩nonexhaustive窗的額外events為UNEVALUATED，test8保持descriptive；三negative只報case-level alert，沒有FPR或正式accuracy/precision/recall/F1/hallucination/generalization。

Parent run summary將 NOT_EXECUTED_AFTER_STOP、ABSENT_PREDICTION_AFTER_START、INCOMPLETE_RECEIPT_RAW_PRESERVED、各invalid與有效NO_EVENT分開，並分stage報PASS/FAIL/NOT_ASSESSED計數，不能從分母悄悄排除失敗。

## Evidence

- 最終53/53 CPU tests通過。18call metadata mock故意1個schema-invalid、1個invalid JSON、16個合法software NO_EVENT，驗證固定18次、無retry、raw全保存及invalid排除。**16/18不是VLM結果、不是模型accuracy。**
- protected historical V1D仍strict1/8，6個event-bearing全部strict-invalid；原8raw/receipt/report hashes在140項保存檢查內皆未變。沒有retroactive reclassification。
- 原schema failure early-return本身未改；未評估stage仍明示，不另造權威validator。
''')

put('PILOT_EXECUTION_GUARD_REPORT.md',f'''# Pilot Execution Guard Report

## Three distinct states

1. `draft_protocol` / CLI `dry-run`：metadata only、status=DRAFT、21決策PENDING、approval=None、execution=None、媒體PENDING。新的canonical draft SHA：`{dh}`。
2. 人類核准後才可呼叫新的freeze writer。要求逐字freeze confirmation、非空reviewer、21個正確decision digests及各APPROVED、execution_authorized=false；核對完整draft/component後寫獨立freeze bundle/receipt。**本次未呼叫writer、未建立freeze。**
3. 實際run另要求綁frozen protocol SHA的execution confirmation、reviewer、32hex nonce、UTC expiry、18call IDs/budget，並保留原 `PASS_T_LOCAL_RUNTIME_APPROVAL` 與 `PASS_T_PHASE2B_REAL_RUN_PERMISSION` 外部環境gate。沒有任何自動設環境permission的程式。

MOCK reviewer records只用於CPU in-memory contracts；production freeze writer、真正model factory與real Bridge preprocessor拒絕MOCK。測試沒有把假資料提升成真正freeze/執行授權。

## A / Native integration

原Bridge預設synthetic path及V1C/V1D pin條款保留。只有明確 `real_pilot_mode=FROZEN_V1D_PILOT_V1` 且synthetic_only=false才走新的guard；guard於torch/processor imports之前檢查frozen/auth/runtime/bridge/schema/prompt/system/representation/source aliases/native PTS與model-visible限制。未認得mode、缺資料或hash不同直接拒絕，沒有globally移除synthetic guard。

FRAME_MATCHED_ONLY、8source/4units、dtype/order/PTS/RGB/patch/cap原有檢查保留；不宣稱8獨立temporal positions或attention。模型端引用語法不變；C3 temporal-unit disclosure只在receipt/report。

## B / Explicit execution route

`scripts/run_pass_t_v1d_pilot.py` 的預設是CPU dry-run，freeze/run均需各自明確參數與授權。新in-process route直接調原shared NF4，沒有HTTP/AVI/legacy prompt_path fallback；舊interfaces保留以供復現。原 `nf4.py`、`runtime.py`、`qwen_contract.py`、legacy transport/protocol/config/inference未改。

新CLI沿用已成功V1D worker的src、`artifacts/pass_i/runtime/vendor`、`outputs/current_development/video_event_experiment/.deps`三個既有搜尋路徑。本機venv不直接提供jsonschema，因此這個顯式整合是必要修補；沒有安裝/下載/換環境。獨立CLI import檢查可載入execution介面，model imports=[]。

新ObservedNF4 subclass只觀測原CPU preprocessing回傳的tensors、canonical hashes、完整input_ids、rendered text/system。它不修改原inputs、不替換generation controls、不修改shared generate。native既有tensor records還會比對相等。模型權重驗證/既有10GiB GPU/8GiB RAM loader gate及2GiB generation gate仍由原NF4執行。

supervisor在授權後才spawn worker／query資源：load120s、generation300s、request330s、proposed whole6060s；globalGPU>14.5GiB/ownedRSS>20GiB/systemRAM<2GiB停止。1s nominal polling保留觀察限制。獨佔authorization-use目錄與每call started claim防止同一permission/call重播；不重試、不加warmup。strict-invalid在健康時繼續；安全/程序/deadline問題停止並保存可用raw與缺結果狀態。

## Model-visible / media provenance

延用未改的既有payload schema/key/serialized-leak guard。Native in-process array的**validation-only projection**將已核准source descriptors映射到既有image schema，以執行同一key/leak檢查；projection不送模型。原actual Native payload仍media=[]，array由Bridge獨立驗形狀/順序/RGB。這不是放寬schema或隱藏新媒體；original payload/task/system hash另記。

執行時在任何媒體讀取前驗授權，逐PNG與已核准hash比對，確認index/nativePTS在hash-pin的authorized half-open boundary內，Uniform8固定；storyboard沿用已存在、已記錄hash的canvas，不生成新visual fixture。raw source video本體hash本次未驗；未來input PNG驗證與nativePTS provenance以已核准source metadata為依據，不能冒稱重新decode原影片取PTS。

每call receipt綁frozen protocol/auth、component hashes、source metadata/full-frame-list SHA、frame alias/native PTS、actual media hashes、payload/generation/rendered/tensor hashes和temporal limitations。

## Remaining execution-only checks

Current real PNG/storyboard identity、actual pixel decode/array/processor grids、weights/currentGPU capacity、CUDA數值/timeout enforcement及真實18call均為 **PENDING_AUTHORIZED_EXECUTION**。CPU tests只驗guard與mock orchestration，未聲稱這些已通過。所記錄核准JSON是信任的人類來源記錄，不是cryptographic human-authorship簽章。
''')

put('CPU_TEST_RESULTS.md',f'''# CPU-only Test Results

**53 tests passed；0 failures；0 errors；0 skipped。** 最終時間{elapsed}秒（unittest回條）。沒有full repository suite。

Repository working directory：`{ROOT}`。

```powershell
.\\.venv\\Scripts\\python.exe -B tests\\test_pass_t_v1d_readiness.py
.\\.venv\\Scripts\\python.exe -B scripts\\run_pass_t_v1d_pilot.py dry-run --output WORKSPACE\\Pass_T\\Execution_Readiness_Repair_20261015\\DRAFT_CONFIGURATION_CANDIDATE.json
```

另執行獨立CPU介面檢查：`python -B -c "import runpy,sys; runpy.run_path('scripts/run_pass_t_v1d_pilot.py',run_name='cpu_import_check'); import memory_graph.pass_t.phase2b.v1d_execution; print([n for n in ('torch','transformers','PIL','cv2') if n in sys.modules])"`；結果 `[]`，CLI local dependency integration OK。這是import/配置檢查，不是額外模型call；沒有將其與53個unit tests相加。最終草案亦由相同dry_run函式更新並驗過source hashes，見CPU_DRY_RUN_RECEIPT.json。

實際測試stdout/stderr另存 {link('cpu_tests_final.log',OUT/'cpu_tests_final.log')}；structured result {link('CPU_TEST_RESULTS.json',OUT/'CPU_TEST_RESULTS.json')}。log SHA `{sha(OUT/'cpu_tests_final.log')}`；result SHA `{sha(OUT/'CPU_TEST_RESULTS.json')}`。

{table(['Coverage','Verified result'],[
 ['Freeze/auth','缺frozen、缺獨立auth、expiry/budget/call inventory/nonce/改hash/缺21decisions拒絕；未造人類批准'],
 ['Configuration/security','三rep/六窗/18call、Uniform8/NONE、V1D/V2/model/schema/runtime/bridge pin；legacy或identity clause等變動拒絕'],
 ['Bridge','CPU eligibility 8→4 units；欠context與MOCK都在heavy imports前拒絕；alias/PTS/task/system/leak/generation變動拒絕'],
 ['Matcher','closed points/intervals各分支、0/.2/.5邊界、decimal邊界、一對一、unknown/缺時/關聯不確定與legacy復現'],
 ['Strict output','absent/malformed/schema/semantic/citation/validNO_EVENT分開；invalid不match；raw不修補；nonexhaustive extra UNEVALUATED；uncertain不當negative'],
 ['Mock integration','1個software runtime factory、18次mock calls；故意2invalid仍繼續，無模型/媒體，receipts綁protocol/source且明示MOCK_METADATA_ONLY'],
 ['Replay/stops','exclusive authorization lease拒重播；not-started/no-output/incomplete-raw分開；hardware門檻以deterministic numbers驗'],
 ['Preservation','原V1D 1/8與6event-bearing全invalid回條保持；140個protected檔案SHA不變']])}

測試audit hook封鎖模型/像素library import、媒體/權重/raw real GT reads及socket；未發生任何guard denial，model_modules_loaded=[]、actual_model_calls=0、freeze writer未呼叫。mock事件與時間只測程式契約，不是physical GT，也沒有生成visual fixtures。

先前42/46測試是同一有界修補的早期run，不與最終53相加。最後53包含CLI輸出格式與mock不得進真實模型的回歸檢查；沒有optional full-suite擴張。
''')

approvals=[{'id':d['id'],'decision':d['decision'],'proposed_value':d['proposed_value'],'decision_sha256':hashlib.sha256(canonical(d)).hexdigest(),'status':'PENDING_HUMAN_APPROVAL'} for d in draft['human_decisions']]
put('HUMAN_APPROVAL_REQUIREMENTS.json',{'draft_sha256':dh,'confirmation_required':confirmation,'approval_received':False,'reviewer_id':None,'decisions':approvals,'execution_authorized':False})
put('REMAINING_HUMAN_APPROVALS.md',f'''# Remaining Human Approvals

**工程可送人工freeze review；21項仍PENDING。** 本次實作授權不等於科學protocol批准，也沒有把舊failed regression改成pass。

{table(['ID','Decision','Proposed value','Human status'],[[d['id'],d['decision'],d['proposed_value'],'PENDING'] for d in draft['human_decisions']])}

上述decision文字保留原review的來源快照，部分risk字句提到當時T01/T02/T04；目前工程解決狀態見BLOCKER_RESOLUTION_MATRIX，不改寫歷史review。新draft另有engineering_resolution和當前component hashes。

## Next explicit freeze-only approval

本次canonical draft SHA：`{dh}`。需要人類提供reviewer ID、逐項確認21個decision digests/APPROVED，及下列完整confirmation：

`{confirmation}`

{link('HUMAN_APPROVAL_REQUIREMENTS.json',OUT/'HUMAN_APPROVAL_REQUIREMENTS.json')} 目前全PENDING、未有reviewer、approval_received=false；它不是可執行的已批准回條。新的freeze writer會驗完整draft/source hashes及21項核准；若code/config再改，hash變動必須重新人審。舊review ID `67b59d603e36` 不能代替本新draft授權。

freeze後還要**另外**提供綁實際frozen protocol SHA的執行確認、nonce、到期UTC與恰好18個call IDs，並保留既有外部runtime/real-run環境gate。當前沒有frozen protocol SHA，因此本任務沒有製造execution authorization。

V1D仍strict1/8；6event-bearing全部invalid的已知風險、NONE的target ambiguity、C3/FRAME_MATCHED_ONLY四units、負例品質/非完整GT、三tolerance及定性限制均需人工接受。不得因CPU測試通過就推定這些已批准或real model已驗證。

到此STOP。不freeze、不載入Qwen、不跑18call、不寫Graph、不commit/push、不自動新增工程階段。
''')

put('READINESS_REPAIR_REPORT.md',f'''# Pass T Phase 2b — Final Pilot Execution Readiness Repair

Task：`PASS_T_PHASE2B_QWEN_NF4_EXECUTION_READINESS_REPAIR`  
日期：2026-10-15；結論：**{status}**。

Authoritative repair report：{link('本次修補報告',OUT/'READINESS_REPAIR_REPORT.md')}。WORKSPACE latest copy更新至同一內容。當前仍在Pass I/T平行標註＋實作；Phase2b尚未完成。

## 1. 完成事項

三個原始code blockers已處理；strict-invalid caller gating/reporting補齊。**53/53 CPU tests通過**，另完成真正CLI的metadata dry-run。只使用一個working tree，沒有平行修改agent。

{matrix}

## 2. 執行設定與人類狀態

新draft完整保留原候選六窗：test1 W03/W05去重、test2 W01、test5 W01、test5 W05、test7 W05、test8 W07；test3 W07排除。三negative僅case-level alerts、兩known PICKUP非完整清單、test8 uncertain；沒有validated PLACEMENT positive。

同一GT-independent Uniform8、ReferenceNONE、MI8/SB8/NativeArray8共18call、immutable V1D/V2、C3 report-only temporal-unit disclosure、FRAME_MATCHED_ONLY八source/四units、greedy42/1024/repeat1、無generation-quality retry/新identity clause/Graph。0/.2/.5全報，closed-interval matcher另有明確版本。21項scientific/protocol決策全部仍PENDING。

CLI dry-run輸出：draft canonical SHA `{dh}`、planned_calls=18、decisions_pending=21、model_initialized=false、calls_executed=0、protocol_frozen=false、media_integrity=PENDING_AUTHORIZED_EXECUTION。{link('可審閱草案',OUT/'DRAFT_CONFIGURATION_CANDIDATE.json')}。

## 3. 來源變更與不變項目

{source_table}

{link('完整逐行 source diff',OUT/'EXACT_SOURCE_DIFF.patch')} SHA：`{sha(OUT/'EXACT_SOURCE_DIFF.patch')}`。{link('SOURCE_CHANGE_MANIFEST.json',OUT/'SOURCE_CHANGE_MANIFEST.json')} 保存before/after SHA和Git狀態；before source文字在本目錄before_source。新增report/helper與WORKSPACE導航屬文件出版，不是runtime source改動。

**未修改** V1C/V1D、V2 system、Prediction V1/schema/strict Parser/Validator、shared NF4 loader/generate、legacy transport/protocol/config/inference或任何historical regression/review。140個protected text/source/receipt檔案SHA全相同；Git HEAD/index/staged diff不變，既有工作樹變更未重設。原GT未讀寫；本次未重算其內容hash，不把範圍外檔案宣稱為已逐byte驗證。

## 4. 測試與驗證證據

{link('CPU_TEST_RESULTS.md',OUT/'CPU_TEST_RESULTS.md')}、{link('最終測試log',OUT/'cpu_tests_final.log')}、{link('結果JSON',OUT/'CPU_TEST_RESULTS.json')}。

53tests/0fail/0error/0skip；no model modules loaded、no audit denials、actual model calls0。18call軟體mock是對控制流程的測試（故意schema-invalid1、invalidJSON1、其餘mockNO_EVENT16），不是模型表現或新VLM預測。沒有產生任何視覺fixture。

## 5. 尚未驗證且必須保留的邊界

- 真實PNG/storyboard/current media hashes、pixel decode/native array、actual processor grids/positions、模型權重/currentGPU resources、CUDA實際數值/安全timeout/真正18call均未執行。media mechanism已實作，現況仍 **PENDING_AUTHORIZED_EXECUTION**。
- native PTS來自pin住的既有source metadata；不宣稱本次重讀原video或重新驗original source-video SHA。8aliases不能解釋成8個獨立temporal positions；actual forward positions仍未instrumented。
- 新observer記錄CPU tensors/input IDs/rendered文本，尚無real DEV receipt可供驗證；相關功能只有mock/既有source契約證據。
- 凍結與執行授權記錄是可追溯的人類來源宣告，不是人類作者的密碼學簽章。沒有人類approval就不得建立真正freeze；MOCK資料不能載入模型。
- Python/file/import guard與相關SHA只覆蓋本次工具/程式；不是全機native-access trace。Git inventory受既有permission/long-path及normalized diff限制，保留範圍據實標示。

## 6. 科學結果未改

歷史 V1D regression仍 **REGRESSION_FAIL，strict1/8，6event-bearing全部strict-invalid**。D4僅表示沒有找到特定可見序列化缺陷。工程修補沒有改善或重新測量模型accuracy/precision/recall/F1/FPR/hallucination/generalization；這些正式指標仍不可宣稱。

VLM仍負責physical event hypotheses；deterministic software只做validation、temporal resolution和未來Graph更新。本次未重設Event-to-Graph，也沒有Graph寫入。

## 7. 下一個人類決策與停止

{link('REMAINING_HUMAN_APPROVALS.md',OUT/'REMAINING_HUMAN_APPROVALS.md')} 列21項及decision digests。下一個freeze-only confirmation是：

`{confirmation}`

另需reviewer及21項逐項approval記錄；本次未收到或自批。freeze後仍須獨立execution authorization才能18call。到此停止：**未freeze、未載入模型、未初始化CUDA、未讀真實媒體、未新推論、未commit/push**。沒有自動新增後續工程階段。
''')

# Daily navigation copies are intentionally mutable; historical review/regression
# namespaces remain untouched. Absolute links work in both copy locations.
(ROOT/'WORKSPACE/Pass_T/LATEST_REPORT.md').write_bytes((OUT/'READINESS_REPAIR_REPORT.md').read_bytes())
(ROOT/'WORKSPACE/Pass_T/LATEST_DECISIONS.md').write_bytes((OUT/'REMAINING_HUMAN_APPROVALS.md').read_bytes())
required=['READINESS_REPAIR_REPORT.md','BLOCKER_RESOLUTION_MATRIX.md','SOURCE_CHANGE_MANIFEST.json','CPU_TEST_RESULTS.md','MATCHER_SEMANTICS_REVIEW.md','STRICT_INVALID_GATE_REPORT.md','PILOT_EXECUTION_GUARD_REPORT.md','REMAINING_HUMAN_APPROVALS.md']
assert all((OUT/n).exists() for n in required)
put('DELIVERABLE_MANIFEST.json',{'task_id':'PASS_T_PHASE2B_QWEN_NF4_EXECUTION_READINESS_REPAIR','classification':status,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
   'required_files_sha256':{n:sha(OUT/n) for n in required},'draft_canonical_sha256':dh,'draft_file_sha256':sha(OUT/'DRAFT_CONFIGURATION_CANDIDATE.json'),
   'source_diff_sha256':sha(OUT/'EXACT_SOURCE_DIFF.patch'),'cpu_tests':tests,'historical_protected_files':140,'protocol_frozen':False,'actual_model_calls':0,
   'human_decisions_pending':21,'media_integrity':'PENDING_AUTHORIZED_EXECUTION','next_freeze_confirmation_required':confirmation,
   'workspace_latest_copy_sha256':sha(ROOT/'WORKSPACE/Pass_T/LATEST_REPORT.md')})
print(json.dumps({'classification':status,'tests':tests['tests_run'],'failures':tests['failures'],'source_files_changed':len(changes['files']),
    'draft_sha256':dh,'next_freeze_confirmation':confirmation,'deliverable_manifest_sha256':sha(OUT/'DELIVERABLE_MANIFEST.json'),'main_report':str(OUT/'READINESS_REPAIR_REPORT.md')},ensure_ascii=False))
