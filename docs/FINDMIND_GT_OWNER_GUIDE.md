# FindMind 人工 GT 收件與裁決（主持人）

審閱者不需 Python。以下僅由專案負責人在 repository 根目錄使用 Python 3 執行，工具全部使用標準函式庫。實際人工標註與測試資料必須分開；不要將 tests 產生的模擬標籤收為 GT。

## 發送

獨立套件：`dist/findmind-gt-annotator.zip`。解壓後只有 HTML/CSS/JS、schema、manifest、說明與九支完整原片。沒有模型答案、舊 GT、模型權重或環境。

重新建置及驗證原片（本專案既有 PyAV 只在這個步驟使用）：

```powershell
.venv\Scripts\python.exe -X utf8 -B scripts/build_findmind_gt_package.py
```

只重包已驗證的影片，仍檢查 hash、不再解碼：

```powershell
python scripts/build_findmind_gt_package.py --zip-only
```

九個 MP4 各約 8–12 MB，可使用一般 Git；`.gitignore` 僅對此工具的 videos/ 開放 MP4，ZIP 不應與同一套影片重複提交。GitHub 一般 Git 單檔上限 100 MiB，超過 50 MiB 警告；獨立 ZIP 建議作 Release asset，不與來源重複入版控。Release asset 上限 2 GiB。官方說明：[大檔限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)、[Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)。本任務不 commit、push 或發布。

## 收件

將各人的 JSON 放進 `collected_gt/`。每個人應建立自己的 reviewer/session；同一 reviewer 的不同 session 不自動視為獨立審閱者。收件目錄只放人工提交，不放 manifest.json。

```powershell
python scripts/import_findmind_gt.py --input-dir collected_gt --output-dir artifacts/vlmtest/human_gt_collection_01
```

輸出目錄必須是新的，避免覆蓋先前收件。驗證失敗的檔案記錄於摘要，CLI exit code 為 2；其他合格檔仍保存。僅備份時間／BACKUP/FINAL 不同的相同內容列為重複；原始有效 JSON 位元組均保留在 submissions/。相同 session 的不同內容全部保留並列 revision conflict，不依時間自動選最新版。

輸出：

- `collection.json`：逐片原始 events、states、coverage 與 reviewer/session/source provenance。
- `submissions/`：原始提交；收件後不要編輯。
- `event_inventory.csv`：每筆事件／非事件觀察與原始審閱者。
- `event_correspondence.csv`：跨提交相距最多 1 秒的**可能對應**，列 type/category/time/state/local-ID 差異。不是物理事件合併，不是正式一致率。可用 `--candidate-gap` 明訂候選搜尋距離，不影響 VLM 評估 tolerance。
- `state_comparison.csv`：相近時間 state/visibility/category/ID 的差異候選。
- `adjudication.json`：所有決策預設 UNRESOLVED；沒有自動投票或 final GT。
- `import_summary.json`：有效、重複、拒絕、revision conflict 與候選數。

## 明確人工裁決

1. 複製 adjudication.json 為 `adjudication_reviewed.json`，依原片與人工證據審閱。
2. 事件逐筆選 ACCEPT（保留原標籤）、CORRECT（主持人明確改正）、REJECT（不納入物理正例）、UNRESOLVED。REJECT 不刪除原標籤，非事件觀察可用此方式排除於正例 ontology；必填理由。
3. ACCEPT/CORRECT 填 `adjudicator_id`、`reviewed_object_id`、`final_event_id`，並明確填 `evidence_supported=true` 與 `target_identity_confirmed=true`。正例需 PICKUP/PLACEMENT、正確前後 state 及可見證據時間。不得只憑原標籤就代填為 true。
4. 同一真實事件可在各來源列填相同 final_event_id，但最終 type/object/interval/states/evidence 必須一致；必要時使用 CORRECT。也可合併 source_refs，刪除對應重複決策列；每筆原始 ref 只能決策一次且不能消失。不同 session 的片內 ID 不會自動視為同一實物。建議最終 object ID 使用 `test1:object_A` 等片內命名。
5. State 決策同樣需人工 ID、支持、最終物件 ID 與 `final_state_id`；同一觀察可填同一 final_state_id，但最終時間、物件、state、visibility、certainty 必須一致才合併來源。不會補齊未標註的 state。
6. Coverage 選 ACCEPT_EXHAUSTIVE 需原始提交至少有一份合格事件完整性聲明、主持人六項再確認、完整原片區間，且本片所有事件／觀察列均已決策。存在未解事件就禁止成為完整 GT。RETAIN_LIMITED 或 UNRESOLVED 不提供全片 FP/FN 資格。
7. 未解者保留 UNRESOLVED。不要為產生分數硬填答案。完整性只限 PICKUP/PLACEMENT，且僅適用此 DEV 通用物件任務；不是舊 Phase 2a eligibility／causality／leakage 的 override，也不自動合併回舊 GT。

```powershell
python scripts/import_findmind_gt.py --finalize artifacts/vlmtest/human_gt_collection_01 --adjudication artifacts/vlmtest/human_gt_collection_01/adjudication_reviewed.json --output artifacts/vlmtest/human_gt_collection_01/final_gt.json
```

輸出檔須尚不存在。`truth` 與 `coverage` 可交給既有 `three_vlm_evaluation.event_metrics`；supported_events_non_exhaustive 只作探索／質性分析。`states` 是明確裁決的逐物件觀察。重疊窗的模型預測仍須另做人工 instance mapping、evidence review 與 event grouping，工具不把 reviewer local ID 當模型 ID 或 PersistentEntity。

finalize 會核對原始提交 hash 及 collection 標籤，拒絕偷偷更改來源。未裁決衝突不進 authoritative truth；缺完整覆蓋不計正式 accuracy/precision/recall/F1。本工具不執行 VLM 或寫入 Memory Graph。
