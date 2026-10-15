# V1D Output Contract 根因診斷報告

**D4_NO_DEFECT_FOUND**  
Task: `PASS_T_PHASE2B_QWEN_NF4_V1D_CONTRACT_DIAGNOSIS`  
日期：2026-10-15；目前流程：Pass I/T 平行標註與實作，尚未 protocol freeze。

本次診斷未載入模型權重、未初始化 CUDA／執行 GPU 推論、未產生新 VLM 預測、未建立新 fixtures、未存取真實 Phase 2a DEV 媒體或 GT、未修改既有檔案、未 freeze、未執行實際 pilot。這些敘述限於本次工具操作與受限 CPU 腳本；不是全機或外部程序的行為證明。Git 只讀 metadata／diff／status；模型資產只沿用既有文字回條，不讀取權重。

本報告及所有新增資料只在本目錄。依本次較嚴格的唯讀限制，不覆寫既有 `WORKSPACE/Pass_T/LATEST_REPORT.md`、README 或捷徑；本報告就是此次 WORKSPACE 交付入口。

## 1. Primary classification

**D4_NO_DEFECT_FOUND**：八次原始執行保留的模型端序列化文字均含完整 V1D 與三段新增要求。未發現鼓勵必填欄位為空的輸出範本，未發現直接矛盾指令，也沒有已驗證的指令未送達證據。因此沒有依據將此批空值歸因於 C1–C3 的可見工程缺陷。

這是「在此次既有證據中未找到指定缺陷」，不是宣稱模型會遵守契約、runtime 全無缺陷、token/pixel 路徑逐位元完整驗證，或視覺推理正確。不能把找不到缺陷解釋為已證明模型能力不足或單一原因。

依鎖定優先序：D2 未成立（未見 E1 缺失／截斷）；D3 未成立（無直接矛盾）；D1 未成立（無傳入空值範本／特定複製證據）；D5 不作主要分類（八次文字皆有可歸屬的 E1 捕獲，足以回答此限定問題）。未保存 token/pixel 全量值仍列為限制。

## 2. Evidence completeness 與可追溯性

- 原始 authoritative root：`artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c`。
- 判準先鎖：SHA-256 `a7846cfbb52086ab5ab933cd1a6a223b78d140bbe8940445486e8e9bed05a08b`；[獨立鎖定回條](diagnosis_lock_receipt.json)。判準未修改。
- V1D SHA：`7008254e618dc8bacdbdeaae3cbf471220afb5efd6c80afc8b9ea5fb5c96b9b0`；V1C SHA：`3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722`，均由實檔核實。
- 原執行 manifest SHA：`f4a91abc2c43a8c8247c784a7b6d861aeba6e453e17381e79d75515101673c60`。最終 deliverable manifest、其列出的檔案、各 completed→raw/runtime SHA、runtime→rendered SHA、runtime→CPU rendered SHA 均核實。
- E1：8/8 runtime 的 captured `rendered_prompt`、輸入 token 數、processed aliases、EOS/cap 等，且與各 attempt 的 completed 回條綁定。影像六次另保有 prompt_contract；native 兩次有 task SHA 與 tensor inventory，不要求所有表示具有同一可選欄位。
- E3：既有 runtime/bridge/worker 文字支持 rendered→processor→generate 的程式路徑與 hash 檢查；不以今日程式單獨取代 E1。schema、V1C/V1D、V2、fixture manifest 亦屬靜態證據。
- E2：沒有重建輸入、沒有重載 tokenizer／processor。沒有把重建內容冒充捕獲。
- E4：未保留完整歷史 input_ids 或完整 transformed tensors；無法事後逐 token 定位三段指令，無法從 decoded text 取得全部視覺資訊。詳第 10 節。

[evidence_index.json](evidence_index.json) 提供每項引用之 source SHA、attempt／表示、精確引文、字元／byte 或行位置及 E 等級。rendered 引文的位置明示為 JSON `/rendered_prompt` 解碼後的字元座標，另列原 JSON 字串範圍，避免與來源 JSON escape bytes 混淆。

## 3. C1 — Template placeholders

檢查八次全部 captured text，共記錄 120 個欄位／關鍵語彙命中。實際文字中 `""` literal 為 0，空陣列 literal 為 0；沒有發現用於必填 uncertainty/citation 欄位的空值範本、保留空值指令或待替換空值 skeleton。

`"type": "string"`、`"type": "array"` 是 schema 型別宣告；schema 同時要求 `minLength: 1`／`minItems: 1`。它們不是空字串／空陣列輸出範例。task 更明確拒絕空 timing_uncertainty，要求每種 outcome 的 nonempty root uncertainty 及至少一個 window cite。source schema 的根欄位確為 `/uncertainty`。

逐次、逐命中 context／section／offset 見 [C1_placeholder_inspection.json](C1_placeholder_inspection.json) 與 evidence index。未將泛用 JSON 語法當作因果證據。

## 4. C2 — V1D instruction delivery

| Attempt | 表示 | 原始 runtime tokens／CPU tokens | A timing／B root／C cites | 結論 |
| --- | --- | --- | --- | --- |
| R01_C01 | MULTI_IMAGE | 3973 / 3973 | 全段逐字一致 | DELIVERED_VERIFIED |
| R02_C06 | STORYBOARD | 2162 / 2162 | 全段逐字一致 | DELIVERED_VERIFIED |
| R03_C08 | NATIVE_VIDEO_ARRAY | 2930 / 2930 | 全段逐字一致 | DELIVERED_VERIFIED |
| R04_C03 | MULTI_IMAGE | 3973 / 3973 | 全段逐字一致 | DELIVERED_VERIFIED |
| R05_C04 | STORYBOARD | 2162 / 2162 | 全段逐字一致 | DELIVERED_VERIFIED |
| R06_C07 | NATIVE_VIDEO_ARRAY | 2930 / 2930 | 全段逐字一致 | DELIVERED_VERIFIED |
| R07_C02 | MULTI_IMAGE | 3973 / 3973 | 全段逐字一致 | DELIVERED_VERIFIED |
| R08_C05 | STORYBOARD | 2162 / 2162 | 全段逐字一致 | DELIVERED_VERIFIED |


A = Timing evidence；B = Window uncertainty (/uncertainty)；C = Citation scope。全部 24 段（8×3）逐字吻合，完整 task 與隨附 schema 亦吻合；各段 SHA 及 offset 見 [C2_instruction_delivery.json](C2_instruction_delivery.json)。這是 E1 捕獲序列化文字的送達判定，不是只查今日 source。

八次 runtime/CPU token count 相符。native 兩次原執行 tensor_records 的 canonical hashes 亦與 CPU 預檢匹配；multi-image/storyboard 六次只有 CPU input_ids hash 與執行 token count，沒有原執行逐 tensor input_ids hash。所有完整 token IDs 均未保存，所以逐 token 的指令定位為 UNVERIFIED，沒有聲稱歷史 tokenizer output 已獨立重算驗證。

未觀察到 input truncation：完整 captured task 保留，source 的此三種路徑直接將 rendered text 送 processor，未見截斷配置；但沒有以 source 或 token 數相同冒充完整 token-stream 證明。8/8 原回條 EOS=true、output_cap_reached=false，支持這批沒有 output cap 截斷；輸出 EOS 與輸入截斷是不同問題。

## 5. C3 — Explicit instruction conflicts

人工語義檢查 72 個相關段落（9 種段落×8），並檢查 schema、representation alias/media framing 和 chat 包裝。**definite direct contradictions = 0；suspected direct contradictions = 0。** 沒有要求 unknown→空字串、空 cite 陣列、empty 表示無 uncertainty、保留 placeholder，或與必填條款直接相反的 optional 要求。

- V2：`Keep rationale and uncertainty strings short`，對照 V1D：`this required root-level string must be nonempty for every window outcome`。兩者允許短且非空文字，沒有矛盾。system/user 級別、各 attempt 位置見 C3 引用。
- `TIMING_UNKNOWN` 是 timing 狀態；`STATE_UNKNOWN` 的 supporting_frame_alias=null 是另一個明確可 nullable 的欄位，不是 uncertainty 空字串許可。
- `If a required citation genuinely cannot be supported, acknowledge the evidentiary conflict truthfully rather than inventing an alias.` 對照 `at least one window_cited_frame_aliases entry` 及 Citation scope 的 assessment/limitations cites：沒有明示空陣列例外。這是保持真實性的約束，非撤銷 schema。若未來視窗完全無可支持引用，仍需人工 protocol 決策；本批皆有八個供應 alias，沒有建立這種直接不可滿足的輸入情形。

每項完整成對文字與位置可由 [C3_semantic_review_findings.json](C3_semantic_review_findings.json) 的 claim IDs 回到 evidence index。原始 72 段另保留於 [C3_instruction_review_inventory.json](C3_instruction_review_inventory.json)。不從實際違規反推 prompt 必然矛盾。

## 6. C4 — Output/template similarity

六次 event-bearing 回應各有空 root uncertainty，全部九個 event timing_uncertainty 為空；另 R01_C01 的 window citations=[]。所有 16 個空必填欄位都記錄 JSON path、原始 raw offset 及 exact substring。

八次沒有找到與 captured prompt 相同的連續 6-word 以上自然語言 leaf overlap，因此也沒有達 12-word substantive overlap。固定 JSON keys／enum／schema 結構為契約要求，不算具辨識性的複製。prompt 中沒有空 literal，因此空輸出也無可配對的傳入空值範本。詳 [C4_output_similarity.json](C4_output_similarity.json)。

跨回應重複四種非空自然語言字串：

- `The hand is visibly holding the phone.`：R04_C03/events/0/rationale, R04_C03/rationale, R07_C02/events/0/rationale, R07_C02/rationale
- `The phone is visibly picked up from the surface.`：R05_C04/events/0/rationale, R08_C05/events/0/rationale
- `The phone is visibly placed back on the surface.`：R05_C04/events/1/rationale, R08_C05/events/1/rationale
- `The phone is picked up and then placed back down.`：R05_C04/rationale, R08_C05/rationale

R05_C04 與 R08_C05 的完整 JSON values 相同；raw bytes 相同：**True**。兩者 private intended 為 zero／one，這是輸出重複的描述，不是物理 GT 或模板誘發的因果證明。上述重複句子未出現在任何 captured prompt；不成立 D1。逐引用見 [C4_repeated_output_findings.json](C4_repeated_output_findings.json)。

## 7. C5 — Empty-value distributions

固定分母：8 attempts；實際輸出共 9 event objects，分屬 6 event-bearing attempts。8/8 可解析 JSON；既有 authoritative strict pass 1/8；不重寫驗證器，也不把這些數字當作完整模型 accuracy。

| 表示方式 | attempts | 輸出事件物件 | timing 空值 attempts | timing 空值欄位 | root 空值 attempts | window cites 空值 attempts |
| --- | --- | --- | --- | --- | --- | --- |
| MULTI_IMAGE | 3 | 2 | 2 | 2 | 2 | 1 |
| STORYBOARD | 3 | 6 | 3 | 6 | 3 | 0 |
| NATIVE_VIDEO_ARRAY | 2 | 1 | 1 | 1 | 1 | 0 |


| Attempt | 表示 | 實際 outcome | 實際 events | private intended | timing 空欄位 | root 空 | window cites 空 | 既有 strict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R01_C01 | MULTI_IMAGE | NO_CONFIRMED_EVENT | 0 | 0 | 0 | False | True | False |
| R02_C06 | STORYBOARD | CONFIRMED_EVENTS | 2 | 2 | 2 | True | False | False |
| R03_C08 | NATIVE_VIDEO_ARRAY | CONFIRMED_EVENTS | 1 | 1 | 1 | True | False | False |
| R04_C03 | MULTI_IMAGE | CONFIRMED_EVENTS | 1 | 2 | 1 | True | False | False |
| R05_C04 | STORYBOARD | CONFIRMED_EVENTS | 2 | 0 | 2 | True | False | False |
| R06_C07 | NATIVE_VIDEO_ARRAY | NO_CONFIRMED_EVENT | 0 | 0 | 0 | False | False | True |
| R07_C02 | MULTI_IMAGE | CONFIRMED_EVENTS | 1 | 1 | 1 | True | False | False |
| R08_C05 | STORYBOARD | CONFIRMED_EVENTS | 2 | 1 | 2 | True | False | False |


### 實際 outcome

| 分組 | attempts | 輸出事件物件 | timing 空 attempts | timing 空欄位 | root 空 attempts | window cites 空 attempts |
| --- | --- | --- | --- | --- | --- | --- |
| NO_CONFIRMED_EVENT | 2 | 0 | 0 | 0 | 0 | 1 |
| CONFIRMED_EVENTS | 6 | 9 | 6 | 9 | 6 | 0 |

### 實際 event 數

| 分組 | attempts | 輸出事件物件 | timing 空 attempts | timing 空欄位 | root 空 attempts | window cites 空 attempts |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 2 | 0 | 0 | 0 | 0 | 1 |
| 2 | 3 | 6 | 3 | 6 | 3 | 0 |
| 1 | 3 | 3 | 3 | 3 | 3 | 0 |

### private designer intention

| 分組 | attempts | 輸出事件物件 | timing 空 attempts | timing 空欄位 | root 空 attempts | window cites 空 attempts |
| --- | --- | --- | --- | --- | --- | --- |
| zero | 3 | 2 | 1 | 2 | 1 | 1 |
| multiple | 2 | 3 | 2 | 3 | 2 | 0 |
| one | 3 | 4 | 3 | 4 | 3 | 0 |


### Event index 與共現

- event[0]：6/6 欄位為空；event[1]：3/3 欄位為空。總計 9/9 timing 欄位，不是 9 個獨立 attempts。
- timing 空與 root 空同時出現：6/8 attempts，全部為 CONFIRMED_EVENTS。
- 只有 window cites 空：1/8（R01_C01，NO_CONFIRMED_EVENT，沒有 event timing 欄位）。
- 三項均不空：1/8（R06_C07，NO_CONFIRMED_EVENT，timing 不適用）。沒有「root 空但 timing 非空」的 attempt。

這些只是八個固定合成案例的描述；表示方式與場景內容混雜，沒有母體 failure rate、顯著性、representation 因果比較、物理 accuracy 或 hallucination rate。private designer intention 只用分組，不當 adjudicated GT。完整分組見 [C5_descriptive_tables.json](C5_descriptive_tables.json)。

## 8. C6 — R05_C04 source/citation audit

原 raw SHA：`f7544ed65389c4893f617689bf42bd01719648ad1a996792178cb1e022531a29`，與 completed 回條一致。原樣保留的兩個 event：

| event | type | timing | event citations | before | after | timing uncertainty | rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PRED_EVT_001 | PICKUP | {"status": "EXACT_SUPPLIED_FRAME", "frame_alias": "F0001"} | F0001 | {"state": "ON_SURFACE", "supporting_frame_alias": "F0001"} | {"state": "HELD_BY_PERSON", "supporting_frame_alias": "F0002"} | 空字串 | The phone is visibly picked up from the surface. |
| PRED_EVT_002 | PLACEMENT | {"status": "EXACT_SUPPLIED_FRAME", "frame_alias": "F0008"} | F0008 | {"state": "HELD_BY_PERSON", "supporting_frame_alias": "F0008"} | {"state": "ON_SURFACE", "supporting_frame_alias": "F0008"} | 空字串 | The phone is visibly placed back on the surface. |


Window citations：F0001–F0008 全八個。last_directly_supported_state=HELD_BY_PERSON@F0008；end_visibility=NOT_VISIBLE；root uncertainty 為空。PLACEMENT 的 after_state=ON_SURFACE@F0008 與最後狀態不同，是待人工檢查的內部語義警訊，並不由此診斷自動改標。

| Alias | source position | synthetic time (s) | RGB equal F0001 |
| --- | --- | --- | --- |
| F0001 | 0 | 0.0 | True |
| F0002 | 1 | 0.5 | True |
| F0003 | 2 | 1.0 | True |
| F0004 | 3 | 1.5 | True |
| F0005 | 4 | 2.0 | True |
| F0006 | 5 | 2.5 | True |
| F0007 | 6 | 3.0 | True |
| F0008 | 7 | 3.5 | True |


八張 `media/S_1f6c0b92d95b9803/F0001.png`–`F0008.png` 的檔案 SHA 皆為 `34d97a03da8327471dd18d85fa10288c9a1b76a0178399c4d09d716089fea44f`；本次以 PIL CPU 解碼成 1280×720 RGB，逐 byte 完全相同，canonical RGB SHA 皆為 `fb18a0c34143cf7e7583c479a0a04f50512e87f5be286b724451351820f4ec22`。不是只比較 manifest 所寫 hash。

**處理鏈區分：** 此 attempt 真正輸入是 STORYBOARD（一張 1440×906 PNG），不是八張獨立 image tensors。原 renderer 依 source list 排 3 欄，逐張縮為 480×270，panel 上方加 alias；來源畫面相同不代表八格連標籤／空間位置的 presentation 完全相同。storyboard 實檔 SHA `5dc11bda088fc94a78ab6f3a0146ef409fb164bf8d23679085a2915cd5778c1c` 與 captured prompt_contract.media SHA 一致；processed aliases 回條列全八個，processor_frame_count=8 指 alias 覆蓋，不能誤稱八張獨立 processor images。

E1 回條 grid=image_grid_thw [1,24,40]、resize=336×560；CPU 預檢保存 input_ids／attention_mask／image_grid_thw／pixel_values canonical hashes。沒有保存完整 transformed pixel_values，也沒有此 storyboard 原 GPU receipt 的 pixel_values hash，故不能獨立證明 GPU transformed bytes 或推測注意力／模型解讀。沒有重新執行 processor。詳 [C6_source_frame_audit.json](C6_source_frame_audit.json)。

可以確立的結論只有：**來源 RGB 序列未觀察到跨影格變化，但回應宣稱兩個物理轉換。** 是否構成具體視覺誤判留為 `VISUAL_JUDGMENT_NOT_ADJUDICATED`；不計 adjudicated FP 或正式 hallucination rate。

## 9. Secondary observations

1. 空 timing/root 與 event-bearing 回應在本批完全共現，跨三種表示均發生；沒有證據支持只修單一表示的指令路由。
2. R05_C04/R08_C05 重複完整回應及四種 boilerplate 是可見輸出行為，不是 transmitted template 複製證明。
3. schema membership 通過不等於 citations 有物理證據效力；本次只核對 source mapping，不做視覺終審。
4. source/receipt 缺少完整 token/pixel 值是可追溯性的限制；不是已證實 runtime 未送 V1D。

## 10. Evidence limitations

- 未保留歷史完整 token IDs、actual forward position_ids、full processed pixel tensors。native 有原執行 tensor hashes；影像六次沒有同等原執行 input_ids/pixel_values hash。token count/hash 不能還原內容或證明模型理解指令。
- 此結論只涵蓋可觀察的序列化文字／明確指令／模板問題，不排除未捕獲的底層處理、模型遵循性或視覺理解問題。
- 原 runtime 的 rendered text 是 E1 捕獲文字，source 是 E3。兩者的用途分開；沒有 E2 內容升格，也沒有 decoded text=完整 multimodal input 的宣稱。
- 沒有人工視覺 GT，只有既有 private synthetic designer intention。沒有新增模型比較或統計推論。
- Python audit guard 限本程序；Git baseline 有既有 permission/long-path 警告，既有檔案 preservation 限 201 個直接 hash 與 Git 可讀 inventory。不是全機完整存取證明。
- 診斷腳本初次在 native 回條欄位差異處停止，修正的是本新目錄內診斷器假設，沒有修 runtime／receipt；已完整重新執行 CPU 分析，判準及鎖未變。見 [diagnostic_execution_notes.md](diagnostic_execution_notes.md)。

## 11. Minimum human decision required

**沒有由此次證據支持的最小工程修正。依 D4 停止這條 prompt／serialization 診斷線，不建立 V1E、不調 validator、不推測性重寫 prompt。**

下一步只交由人類審查最終 exploratory Qwen Pilot protocol：決定是否接受既有 V1D 在本批 strict 1/8 的限制、如何預先記錄／處理結構失敗，以及是否授權下一階段。這是待人類決策事項，不是本次自動 approve、freeze 或 DEV 執行。

## 12. Preservation results

詳 [readonly_preservation_report.md](readonly_preservation_report.md) 與 [preservation_after.json](preservation_after.json)：在交付前比較 Git HEAD/index/staged/worktree、201 個相關既有檔案及 criteria SHA。所有原始 prompt、schema、parser/validator、V2、bridge/NF4、八個 raw、73 個合成 assets、舊回條與既有 WORKSPACE 導覽檔均應相同；若有任何不一致即在 preservation 報告明示，絕不修回或忽略。

結案：**D4_NO_DEFECT_FOUND — STOP FOR HUMAN FINAL PILOT PROTOCOL REVIEW**。本次沒有批准或 freeze。
