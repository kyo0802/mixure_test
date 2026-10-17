# FindMind 離線人工 GT 標註工具完成報告

更新：2026-10-18。狀態：**OFFLINE_GT_ANNOTATION_TOOL_READY**。

已完成獨立離線工具、九支完整影片、JSON 提交契約、主持人收件／裁決工具及 ZIP。專案負責人已回報「已完成播放、標註與匯出再匯入」。這項實機回報與自動測試分開記錄；未提供瀏覽器版本，也未逐項確認完整人工驗收表。

## 1. 直接使用的檔案

| 用途 | 專案根目錄下的位置 |
|---|---|
| 雙擊啟動工具 | `tools/findmind-gt-annotator/index.html` |
| 發給其他審閱者的獨立套件 | `dist/findmind-gt-annotator.zip` |
| 瀏覽器內操作指南 | `tools/findmind-gt-annotator/guide.html` |
| 主持人收件／裁決說明 | `docs/FINDMIND_GT_OWNER_GUIDE.md` |
| 收件與明確裁決 CLI | `scripts/import_findmind_gt.py` |
| 套件建置／媒體驗證 | `scripts/build_findmind_gt_package.py` |
| 最終完整性紀錄 | `artifacts/vlmtest/gt_tool/verification.json` |

**ZIP 必須完整解壓後開啟 index.html。** 審閱者不需 Python、Node、模型、環境、伺服器或網路。使用 classic scripts 與本機 HTML5 video；沒有 fetch、ES modules 或 CDN。

舊的 `artifacts/pass_t/phase3/three_vlm_full_v1/human_review/INDEX.html` 確實存在，但它是輸入與 contact sheet 檢視頁，不能取代本次可保存、編輯及匯出標註的工具。

## 2. 操作介面與功能

介面為繁體中文三欄：左側九影片／分工與完成狀態；中央完整影片、速度、時間滑桿、跳轉與原生 PTS 導航；右側事件、state、coverage 表單及可編輯清單。

- 每位審閱者建立自己的 reviewer ID、session 及分工，避免共用答案。
- 事件支援 PICKUP／PLACEMENT 與非事件觀察，保存物件類別、片內 ID、時間區間、前後 state、可見度、證據秒數、確定程度與備註。可跳轉、播放區間、編輯、刪除。
- 物理狀態與可見度分開記錄，不把遮擋直接當成物理狀態。
- Coverage 由人填寫已審閱及不確定區間。看完播放或按 FINAL 均不會自動取得事件完整性資格。
- 全片審閱與 `EXHAUSTIVE_ATTESTED` 分開。後者另需明確聲明、完整區間及沒有可能隱藏事件的未解缺口；修改標註會撤銷先前完整性確認，要求重新檢查。
- localStorage 只是續做方便；不可用時顯示警告。真正可攜的提交是 Blob 下載 JSON。匯入先驗證，再確認取代；壞檔不改寫目前標註。
- 審閱者套件不含模型答案、舊 GT、追蹤分數或預填事件。

## 3. 原片、時間與套件

test1–test9 均以原始完整 H.264／yuv420p MP4 原位元組複製，沒有剪輯、轉碼或變速。建置時 CPU 解碼全部 **9,958 格**；最終重新確認九支 source／preview／manifest SHA 一致。各片格數依序為 967、924、1169、1169、1117、993、1316、1103、1200。

| 項目 | 最終值 |
|---|---|
| 媒體總大小 | 85,887,683 bytes（約 81.91 MiB） |
| 完整工具資料夾 | 88,476,445 bytes（約 84.38 MiB） |
| ZIP | 86,041,705 bytes（約 82.06 MiB） |
| ZIP 檔案數 | 21（含九支 MP4） |
| ZIP SHA-256 | `7c6c513d5a22e9e2f0002fbbdebf4a88806c7c748873b00c62bcb53b97129007` |
| Dataset manifest SHA-256 | `86ab0644ba2a40c97149a81ceea7d94e061b90820ed5d0c3ab5d3fbf66739ce0` |

Manifest 保存來源 hash、duration、fps、time base、完整原生 PTS 與零 offset 映射。逐格按鈕是原生 PTS **seek 目標**；HTML5 實際顯示可能落在鄰近格，不能聲稱 frame-accurate。匯出保留 `source_frame_index=null`，鄰近索引只用於導航。

ZIP CRC、21 個檔案與磁碟內容逐位元組一致、index 本機依賴路徑均通過檢查。

九個 MP4 各約 8–12 MB，工具影片可用一般 Git；ZIP 已忽略，避免同份媒體重複入版控。GitHub 的一般 Git 單檔限制與 Release asset 規則見[大檔官方說明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)與[Release 官方說明](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)。工具實作階段只準備本機套件。後續依使用者明確要求推送時，採主開發分支保存程式與報告、獨立 `codex/offline-gt-annotator` 分支只保留工具及原片；GitHub 可直接產生該分支 ZIP，不需額外上傳重複壓縮檔。

2026-10-18 發送文件補充：README 已加入獨立分支下載連結、權限／404 排解、正式分工、備份與修訂交件步驟。此次重包只更新說明，未更動影片、標註契約或 UI 行為；表中為最新本機 ZIP hash，GitHub 自動產生 ZIP 的封裝 hash 不必相同。

## 4. 收件、來源保存與明確裁決

主持人 CLI 使用 Python 標準函式庫，審閱者無需執行它。它驗證 schema、dataset/source hashes、時間、ID、coverage 與語意，保留原始有效 JSON 位元組及 reviewer/session/hash 來源。

- 重複備份去重但原檔仍保留；同 session 不同內容列為 revision conflict，不自動挑最新版。
- 逐影片輸出事件清單、可能對應、state 差異、coverage、收件摘要與 `adjudication.json`。
- 事件相距一秒內只是可能對應搜尋，並非物理事件合併或模型評估 tolerance；沒有多數決。
- 初始裁決一律 UNRESOLVED。人工 ACCEPT／CORRECT／REJECT 後才可輸出；改標必須明確 CORRECT，來源不能偷偷改寫。
- 正例需要支持的物理轉變、前後證據與實物身分確認。跨 reviewer 的 local ID 不自動合併。
- 未裁決衝突不進 authoritative truth；缺完整 coverage 的正例只進 `supported_events_non_exhaustive`，不可推成全片負例或計正式 FP/FN。
- 最終 `truth`／`coverage` 保持既有 `three_vlm_evaluation.event_metrics` 所需形狀；state 與完整裁決來源另存。模型 instance mapping、證據審閱與重疊窗事件去重仍需後續明確處理。

收件指令（輸出目錄必須是新的）：

```powershell
python scripts/import_findmind_gt.py --input-dir collected_gt --output-dir artifacts/vlmtest/human_gt_collection_01
```

人工填好獨立裁決檔後才執行：

```powershell
python scripts/import_findmind_gt.py --finalize artifacts/vlmtest/human_gt_collection_01 --adjudication artifacts/vlmtest/human_gt_collection_01/adjudication_reviewed.json --output artifacts/vlmtest/human_gt_collection_01/final_gt.json
```

## 5. 驗證結果與限制

| 驗證 | 結果 | 實際範圍 |
|---|---|---|
| Node contract | 13 通過 | JSON round trip、嚴格解析、錯誤拒絕、時間／來源、coverage 完整性 |
| Node UI controller | 16 通過 | 實際 app.js 搭配 DOM test doubles；操作、編輯、刪除、保存、Blob JSON、再匯入、session 隔離及錯誤提示 |
| Python owner import | 16 通過 | JS/Python 契約一致、原檔保存、重複／revision、爭議、來源防竄改、裁決門檻與實際 CLI collect/finalize |
| 原片 CPU 解碼 | 九支通過 | 共 9,958 格；未改原片 |
| 最終 ZIP 完整性 | 通過 | CRC、21 個內容與目前檔案一致、九片 source hash、本機依賴 |
| 使用者實機 smoke | 已回報成功 | 「已完成播放、標註與匯出再匯入」 |

自動測試共 **45 項通過、0 失敗**。指令：

```powershell
node tests/test_findmind_gt_contract.cjs
node tests/test_findmind_gt_ui.cjs
.venv\Scripts\python.exe -X utf8 -B -m unittest discover -s tests -p test_findmind_gt_import.py -v
```

測試標籤僅在記憶體或獨立暫存測試目錄，沒有作為影片 GT。紀錄位於同目錄的 `contract_tests.log`、`ui_controller_tests.log`、`import_tests.log`、`build.log`、`package.log`、`verification.json`；build.log 的早期 ZIP hash 已由 package.log 的最終值取代。

內建 browser 工具禁止 file://，因此代理未完成自動 Chromium 實機驗收，也未繞過限制。使用者 smoke 已確認可用，但瀏覽器版本、其他平台相容性及 `MANUAL_ACCEPTANCE.md` 每項操作尚無獨立紀錄。DOM doubles、CPU 解碼與使用者回報均不可冒充完整跨瀏覽器測試。

## 6. 下一個人工動作

1. 將 ZIP 傳給審閱者，完整解壓後用 Chrome／Edge 開啟 index.html。
2. 另建正式 reviewer/session，選分工；先讀畫面內準則，只看原片判斷。`MANUAL_TEST_ONLY` 測試提交不能混入正式 GT。
3. 標事件、state 與 coverage；離開前下載備份。完成後匯出 JSON 回傳主持人。
4. 主持人依 owner guide 收件、檢查衝突並明確裁決；不要直接把多人 JSON 當最終 GT。

本次沒有新模型推論、歷史 GT 改寫或 Memory Graph 寫入。工具完成不代表九支影片的正式人工 GT 已完成，也不代表三模型物理正確率已建立。
