# FindMind — 人工 GT 整合與三模型評估準備報告

更新：2026-10-19。狀態：**AWAITING_OWNER_ADJUDICATION**。

可自動執行的驗證、對齊、差異分類、格式統計及評估指令已完成。現在需要你填寫實際裁決；尚未產生 authoritative final GT，也沒有用模型答案解決人工分歧。

## 先開這兩份 CSV

1. **[adjudication.csv](adjudication.csv)**：34 組人工事件／非事件裁決。
2. **[coverage_adjudication.csv](coverage_adjudication.csv)**：41 個待核准局部範圍；可只核准確定可評分的區間。

完整欄位與兩條執行指令見 **[EDITING_GUIDE.md](EDITING_GUIDE.md)**。只讀對齊見 [gt_alignment.csv](gt_alignment.csv)，差異摘要見 [gt_disagreement_summary.md](gt_disagreement_summary.md)。CSV 已用 UTF-8 BOM，Excel 可顯示中文；儲存時維持 CSV UTF-8。

## 原始資料驗證

兩份指定 Downloads JSON 都存在，已驗證 schema、dataset manifest digest、九支原片 SHA、原生 duration，並逐位元組保存於 originals/。完整原始路徑與 hash 見 [original_submission_receipt.json](original_submission_receipt.json)。原始檔案沒有修改。

| 審閱者 | 全部紀錄 | PICKUP／PLACEMENT | 非事件觀察 | State 紀錄 |
|---|---:|---:|---:|---:|
| annotator_huang | 19 | 19 | 0 | 17 |
| KUO | 34 | 28 | 6 | 16 |
| 合計 | 53 | 47 | 6 | 33 |

47 筆是兩人的原始物理事件標記總數，含對應／重複候選，**不是 47 個已確認真實事件**。6 筆非事件包含接觸、攝影機移動與遮擋證據不足。

已核對 2,235 個輸入／歷史檔案，包含兩份保存 JSON、九支原片、時間與資料集 manifests、552 組 raw／receipt／input／validation 等；所有 raw hash 與 receipt 相符。214 個設定視窗的 1,712 次影格引用均與原片原生時間表對上；相同影格會跨視窗重複引用。去重後依然是原有 184 組輸入 × 3 模型 = 552 次生成，沒有新推論。

## 對齊與需要裁決的差異

53 筆對齊為 **34 組**：19 組雙人對應候選、15 組單人紀錄。採相同 video／category、優先同 event type、時間交集或最多 0.5 秒間距的互相唯一最佳候選。這是候選搜尋規則，不是自動證明同一事件，也不是修改模型評估 tolerance。

每組最多各一位審閱者的紀錄；模糊多對多保持分開。不同 reviewer-local ID 名稱不直接算成不同實物。時間重疊不會自動合併真實事件。

| 主要分類 | 群組數 |
|---|---:|
| UNCERTAIN_EVIDENCE | 16 |
| ONE_REVIEWER_ONLY | 12 |
| EVENT_TYPE_DISAGREEMENT | 2 |
| NON_EVENT_CONFLICT | 4 |
| AGREED_CANDIDATE／單獨 TIMING_DISAGREEMENT／單獨 IDENTITY_DISAGREEMENT | 0 |

主分類只選一項；`all_flags` 保留所有問題：27 組有證據不確定旗標、26 組身分未解、14 組時間差異、15 組有單人紀錄。這些數字會重疊。

**優先看 G003／G004（test1）、G022／G023 與 G024／G025（test7）**：有人認為是轉變，附近另有接觸、遮擋或另一事件型別。這些可能是不同連續事件，因此只提示相關群組，不自動判誰錯或合併。

huang 的 19 筆皆帶 UNCERTAIN／UNKNOWN metadata；即使備註描述可見放下，系統也不能自動覆蓋原始信心。所有 agreement 都須你明確接受，沒有已偷偷升成 GT 的紀錄。

## Coverage 與負例資格

兩人的九片共 18 份 video record 全為 `EXHAUSTIVELY_REVIEWED`，但 `event_list_exhaustiveness` 都是 **NOT_ATTESTED**。目前自動取得 exhaustive 負例資格的影片數為 **0**。

41 個 scope 依原始不確定區間邊界切開；「未報 gap」仍只是候選。你可以只確認某支影片的局部時間與特定物件，其他時間保留未知。Full watched、事件列完整、可見度足夠、實物身分釐清分別確認。已知遮擋若可能藏事件，不能直接接受為負例。

最終生成會阻擋範圍內仍未解的人工紀錄，並保留所有未解／拒絕／非事件、來源、信心與證據。原始 NOT_ATTESTED 保持原值，新 scope 以你本次明確聲明作證。

## 現有三模型可立即報告的結果

| 模型 | 完成生成 | Raw JSON 合格 | Raw schema 合格 | Raw full-strict | 事件假說 | strict 假說 |
|---|---:|---:|---:|---:|---:|---:|
| Qwen2.5-VL-7B NF4 | 184 | 0 | 0 | 0 | 6 | 0 |
| VideoLLaMA3-7B | 184 | 147 | 144 | 83 | 15 | 2 |
| Nemotron Nano V2 VL（既有 NVFP4 部署） | 184 | 166 | 163 | 108 | 146 | 58 |

Qwen 的 raw schema 是 **184 份均未能進入 schema 評估**，不是 184 次獨立 schema 錯誤；完整逐層 pass／fail／not-assessable 已列在 [evaluation.json](evaluation_readiness/evaluation.json)。既有 Qwen fence-body 157 份 full-valid 仍屬另列描述結果，不能升成 raw strict-valid。

原始模型 state claims 共 6,420 筆。既有 validator 的 EVENT_STATE_CITATIONS_INCONSISTENT 在 VideoLLaMA3 raw 出現 5 個 calls、Nemotron raw 47 個 calls；Qwen fence-body 4 個 calls。這是引用 state 內部矛盾診斷，不等於人工判定物理 state 錯誤。

**目前事件 precision／recall／F1、wrong-target 及物理 state 正確性尚無人工依據，保持未評分。** 不能以假說數較多或 strict 合格較多選出物理事件勝者。簡明比較另見 [三模型比較報告](evaluation_readiness/THREE_VLM_COMPARATIVE_REPORT.md)。

## 最小可重用工作流程

新增兩支標準函式庫 CPU CLI，沿用既有 matcher，沒有新網站或框架：

- `scripts/consolidate_findmind_gt.py`：prepare／verify／finalize。
- `scripts/evaluate_consolidated_vlm.py`：prepare-review／evaluate。

完成兩份人工 CSV 後，在專案根目錄執行：

```powershell
.venv\Scripts\python.exe -X utf8 -B scripts/consolidate_findmind_gt.py finalize --output artifacts/vlmtest/gt_consolidation_v1/final
```

生成 final_gt.json、final_gt_summary.md、gt_eligibility.json 與 receipt。沒有任何 owner 決策時會拒絕生成。每個被裁決真實事件只有一個唯一 final_event_id，原始來源保留；拆／合必須明確決策。

已有 **[prediction_review.csv](prediction_review.csv)**，列出原有 167 筆模型假說、來源圖片／PTS、raw 路徑及可填的實物與事件群組。人工 GT 判斷先獨立完成，模型表不能用來改寫人工答案。只需要審閱欲評估 scope 內的假說，其餘可保留待審；物件描述與重疊時間不足以自動解決 wrong-target 或去重。這是既有結果的證據審閱，不是新推論或另一個網站。

```powershell
.venv\Scripts\python.exe -X utf8 -B scripts/evaluate_consolidated_vlm.py evaluate --gt artifacts/vlmtest/gt_consolidation_v1/final/final_gt.json --output artifacts/vlmtest/gt_consolidation_v1/evaluation
```

評估分 physical_candidates／strict_valid；候選層保留 strict-invalid 的描述價值，strict 層禁止它們進入 matching。模型未審、無時間、無法解析或跨 scope 邊界會列出具體門檻，不當成 NO_EVENT。原生引用時間是定位界限，不是事件 duration。One-to-one 與 tolerance 0／0.2／0.5 秒保持既有規則。

跨視窗重複依你明確認定的 reviewed_event_group 去重；保留各來源，固定選字典序最早視窗作代表，不對 GT 挑最有利時間。不同真實事件即使重疊仍保留不同群組。各模型／表示的結果只在可評分局部 scope 計算；全資料集 overall F1 保持 null。

## 測試、保存與停止點

**21 項 CPU 測試通過**，涵蓋七種分類、跨群組替代解釋、重疊但不同事件、原生 PTS、原始來源防竄改、NOT_ATTESTED、局部 coverage、不可見轉變禁止升正例、未知時間、邊界 tolerance、一對一配對、人工去重、wrong-target 與 strict-invalid。測試資料只在獨立暫存目錄，沒有混入人工 collection。

初次測試遇到 Windows sandbox 預設 temp 目錄權限問題；改用專案內測試暫存目錄後通過。失敗紀錄保留於 cpu_tests.log，最終結果為 cpu_tests_final_v2.log。

原始人類 JSON、影片、模型輸出與歷史報告未改寫；沒有模型生成、Graph 更新、commit 或 push。現在停止於 **真正需要你的裁決**。完成 CSV 後可以直接生成 GT 並計算有依據的指標，不再引入規劃階段；仍無人工依據的項目會保持未評分。
