# 一天內完成：人工裁決與既有三模型評估

先用 Excel 開啟 `adjudication.csv`。儲存時選 **CSV UTF-8（逗號分隔）**，不要覆寫兩份原始 JSON。所有 owner 欄位目前空白；final 欄位的預填只是第一位來源的草稿，不是 GT。

## 1. 先裁決 34 組人工紀錄

只依原片與兩位人的證據判斷，這一步不要使用模型輸出。

| 欄位 | 怎麼填 |
|---|---|
| `group_id`、`video_id`、`source_refs`、huang/kuo 欄位 | 原始對齊與來源；一般保持不動。兩位的原始事件 ID、時間、物件、信心、Before/After 證據秒數都在同列 |
| `classification`、`all_flags`、`related_groups` | 提醒先看哪裡；相關群組可能是不同連續事件，不能因重疊就合併 |
| `owner_decision` | `ACCEPT` 保留預填來源判斷；`MODIFY` 改成你的判斷；`REJECT` 不納入正例；`UNCERTAIN` 證據不足。空白也會保留未解 |
| `owner_reviewer_id`、`decision_notes` | 每項決策必填你本次 reviewer ID 與依據。不能只寫「同意」而沒有可見轉變的說明 |
| `final_event_type`、`final_object_category` | 最後事件／非事件類型與物件類別。PICKUP 是表面→持握；PLACEMENT 相反 |
| `final_object_id` | 你的片內實物 ID，例如 `test1:phone_01`；只有同一實物才沿用。同名或同色不等於同實物，不跨片強行合併 |
| `final_start_s`、`final_end_s` | 原片秒數的轉變範圍；不要直接把兩張證據圖距離當動作持續時間。更改需用 MODIFY |
| `final_before_state`、`final_after_state` | PICKUP 要 ON_SURFACE→HELD_BY_PERSON；PLACEMENT 要反向。看不到支撐改變就用 UNCERTAIN |
| `final_before_visibility`、`final_after_visibility` | 確認轉變需 VISIBLE 或 PARTIALLY_OCCLUDED 下仍有支持；NOT_VISIBLE 不足以建立正例 |
| `final_before_evidence_times_s`、`final_after_evidence_times_s` | JSON 數字陣列，例如 `[3.50, 3.70]`；前後有序、位於原片內 |
| `same_real_event_confirmed` | 同列含兩人紀錄時，確定它們描述同一真實事件才填 `YES` |
| `physical_transition_confirmed`、`identity_resolved` | 要成為 PICKUP／PLACEMENT 正例，兩欄都要依實際證據填 `YES` |
| `final_event_id` | 預填的 GT_testN_Gxxx 可保留。不同真實事件必須不同 ID |

`IDENTITY_DISAGREEMENT` 包含 UNKNOWN／未建立身分，不表示已證實兩位看到不同實物。huang 的 19 筆皆有不確定 metadata，即使備註寫「可見」，程式也不能代替你升為 CONFIRMED。

若一個對齊群組實為兩個事件：複製該列；兩列用不同 `decision_id`、不同 `final_event_id`，將 `source_refs` 按 `|` 分開，每個原始 ref 只分配給其中一列；使用 MODIFY 並說明拆分原因。若兩群組其實是同一真實事件：可給相同 `final_event_id`，但最終型別／實物／區間／states／證據必須完全一致，兩列都填 `same_real_event_confirmed=YES`。不允許只為減少事件數而合併。

快速順序：先 `NON_EVENT_CONFLICT`、`EVENT_TYPE_DISAGREEMENT`；再單人新增事件；最後確認雙人候選的時間與身分。可看 `gt_alignment.csv` 只讀對齊版；原片在專案根目錄 test1.mp4～test9.mp4，也可用既有離線工具觀看，但不需要再建網站或重做整份標註。

## 2. 核准局部可評分範圍

開啟 `coverage_adjudication.csv`。41 列依兩人原始不確定區間切分，**沒有任何一列已經獲得負例資格**。可只核准能確定的前半段，其餘保留 UNCERTAIN；不用為了全片分數猜測遮擋期間。

- `owner_decision`：ACCEPT／MODIFY 核准目前 scope；REJECT 排除；UNCERTAIN／空白保留待定。
- `start_s`、`end_s` 可縮小或調整；新增／拆列時 `scope_id` 必須唯一。
- 填 `owner_reviewer_id`、`decision_notes`。
- `object_category_scope`、`object_ids_scope` 明確限定這段已完整審閱的物件，例：`Phone` 與 `test1:phone_01`。多個值用 `|`。只有確實審閱所有類別／所有實物才填 `ALL`。
- 核准需 `full_scope_reviewed`、`all_events_verified`、`event_visibility_sufficient`、`object_identity_resolved` 四欄全部 `YES`，分別確認已完整觀看此段、列完此段所有 PICKUP/PLACEMENT、可見度足以判斷、實物身分已釐清。
- 若範圍與原始 obscured／identity gap 重疊，必須縮小範圍或提供新的具體依據，填 `known_gaps_resolved=YES` 並解釋。真的看不到、可能藏事件時不可填 YES。
- 範圍內仍有未解人工事件時，程式會要求處理該事件或縮小範圍。把 UNKNOWN 改成負例並不能解決。

原始 `EXHAUSTIVELY_REVIEWED`、`NOT_ATTESTED` 不會改寫。這份表是你新的局部人工聲明。正例可以保留而沒有完整 coverage；但不能因此自動算全片 FP/FN。

## 3. 一條指令產生最終 GT

在 `C:\Users\smile\Desktop\test2\mixure_test_SAM` 開啟 PowerShell，執行：

```powershell
.venv\Scripts\python.exe -X utf8 -B scripts/consolidate_findmind_gt.py finalize --output artifacts/vlmtest/gt_consolidation_v1/final
```

產生 `final/final_gt.json`、`final/final_gt_summary.md`、`final/gt_eligibility.json`、來源核對 receipt。若尚未填任何決策會拒絕產生。未解列仍保留並排除 authoritative metrics。修改後重跑時使用新的輸出名稱（例如 final_02），不覆蓋既有結果。

## 4. 模型評估的必要人工界線

`prediction_review.csv` 共 167 列是原有模型假說，不能拿來反過來決定人工 GT。**先完成前兩份表，再檢查欲評分範圍內的模型假說**；不必把全部 167 列填完才能計局部結果。

原有模型只提供泛稱，例如 phone，沒有已核准的實物 ID。若不審查，程式只能報格式、假說數、待審數，不能誠實地產生 wrong-target、實物事件 TP/FP 或可靠跨視窗去重。

- 先依 `video_id`、引用秒數與核准 scope 篩選。`evidence_references` 內有原生 PTS、source frame index、圖片路徑；`raw_path` 可查看原文。可直接開圖片或用既有影片播放器跳轉。
- 填 `owner_reviewer_id`、`decision_notes`。
- `physical_review`：SUPPORTED／UNSUPPORTED／UNCERTAIN；這是你看過引用證據後的判斷。
- 填 `reviewed_object_category`、`reviewed_object_id`。同一真實實物需與最終 GT 的 ID 對上；不確定就不要猜。
- `reviewed_event_group`：同一模型跨視窗重複說同一件事才填相同 group，並填 `same_event_group_confirmed=YES`。可用各列 proposal_id 當獨立 group；有重複時必須明確歸組，不能因時間重疊就自動合併。
- `exact_claim_signature_candidate_only` 只提醒完全相同引用／描述候選，不是已確認同一真實事件。
- 模型時間固定採原始引用 PTS，不可以修改成更貼近 GT 的時間。`time_support_verified=YES` 代表你確認 before/after 引用可作為這項轉變假說的定位界限；這不是物理動作持續時間。
- `wrong_target`：YES／NO／UNKNOWN；`state_evidence_consistency`：SUPPORTED／CONTRADICTED／UNKNOWN。未審留空。

Strict-invalid 假說若經人工審閱，只進獨立 physical candidate 描述／局部分析，永不進 strict-valid 評分；無法解析不改成 NO_EVENT。範圍內仍有未知候選、未知時間、跨界事件或缺可用輸出時，相關分數會維持 null 並列原因。模型內部 states 符合格式不等於真實物理正確。

## 5. 一條指令評估既有三模型

```powershell
.venv\Scripts\python.exe -X utf8 -B scripts/evaluate_consolidated_vlm.py evaluate --gt artifacts/vlmtest/gt_consolidation_v1/final/final_gt.json --output artifacts/vlmtest/gt_consolidation_v1/evaluation
```

產生 `evaluation/evaluation.json` 與 `evaluation/THREE_VLM_COMPARATIVE_REPORT.md`。使用既有 tolerance 0／0.2／0.5 秒、一對一配對及人工明確認定的實物／事件去重。只計核准 scope 的 PICKUP／PLACEMENT 指標；未審範圍不算 FP/TN，全資料集 F1 不強行計算。

你也可以只把完成的 CSV 回傳給我；我會直接執行上述指令並報出可計算的結果與尚無依據的項目，不另開規劃階段。原始 552 次模型輸出、人工 JSON、影片與既有歷史檔案保持不變；本次沒有 commit 或 push。
