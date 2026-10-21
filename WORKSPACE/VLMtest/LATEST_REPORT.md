# Phase 9：完整競賽 Demo — 離開提醒與找物 Agent

更新：2026-10-21。**PHASE9_COMPETITION_DEMO_IMPLEMENTED_AND_VALIDATED**

正式來源：`artifacts/phase9/PHASE9_REPORT.md`。已在既有 Streamlit 應用中接上持久化必帶清單、離開檢查與 Object Search。完整流程已用真實保存的 test8 記憶在瀏覽器操作驗證；未重新執行 GPU 推論。

## 開啟與展示

本機入口：**http://127.0.0.1:8514/**

從 `C:\Users\smile\Desktop\test2\mixure_test_SAM` 啟動：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_findmind_demo.ps1
```

使用既有環境，保持啟動程序執行即可。詳細展示步驟見 `artifacts/phase9/DEMO_GUIDE.md`。

**首頁 → 選影片記憶 → 我要出門了 → 尋找手機 → 看同格原片 → 返回清單 → 手動確認 → 完成 → 開始新檢查。**

本機目前保留一份「展示已完成」歷史紀錄，以及一份新的三件未確認檢查，可直接重複展示。所有此次瀏覽器驗收確認均標為 DEMO_PRESENTATION／UI_DEMO_CONFIRMATION，**不代表使用者真的已攜帶任何物品**。

## 本次完成內容

| 功能 | 實際行為 |
|---|---|
| 首頁 | 同一份記憶下提供 Find an Item、I'm Leaving、Analyze New Video |
| 必帶物品設定 | 新增、改名、設定搜尋類別、啟用／停用、移除；預設手機／鑰匙／錢包只是範例 |
| 離開檢查 | 依選定記憶開始或續用當次檢查，保存建立時間、物品快照與確認事件 |
| 手動確認與撤銷 | 只由明確按鈕操作改變；重複相同狀態不增加事件 |
| 提醒 Agent | 直接向既有 Graph 搜尋取證，說明未確認物品與歷史線索，不聲稱忘帶 |
| 找物串接 | 點物品的 Find，填入正確問題與類別，在同一記憶自動執行原搜尋 |
| 證據 | 重用既有框／mask、區域、native PTS、來源影格與引用檢查 |
| 新檢查／重設 | 建立全新確認集合，不刪 Graph、不繼承舊確認，舊檢查可只讀檢視 |
| 跨記憶與重啟 | 每份記憶有各自 active check；設定與歷史在本機 JSON 保存 |
| 原有功能 | 保留中英搜尋、候選卡片、時間線、上傳、背景工作與 GPU 鎖 |

設定修改**套用到下一次新檢查**；當次與歷史紀錄保持自己的快照，避免改名／移除物品後歷史也被改寫。介面有明確提示。

首次在錄製模式開啟「我要出門了」會建立展示檢查。要記錄一次實際使用者出門檢查，在「開始新檢查」前取消「展示檢查」勾選；其來源記為 USER_MANUAL_CONFIRMATION，仍是使用者自述，不是影像驗證持有。

## 清單、觀察與打包不是同一種資料

`packing_status` 與 `evidence_status` 分開保存和顯示：

- **USER_CONFIRMED_PACKED**：這次檢查有明確手動確認，並保留來源及時間。
- **NEEDS_CONFIRMATION**：仍需本人確認。即使有物體、手持或位置線索，也不會自動帶妥。
- **HAS_LOCATION_CANDIDATE**：Graph 有歷史位置線索；仍不保證是同一件個人物品或現在仍在原處。
- **NO_RELEVANT_OBSERVATION**：沒有相關可用觀察，不表示忘記攜帶。
- 若只有物體觀察、沒有區域，另記 **OBSERVATION_ONLY**，仍需手動確認。

本版所有 `possession_verified` 都是 false。人工確認只進清單紀錄，**不會寫成 PICKUP、改 Graph 或升成 VERIFIED**。所有 enabled snapshot items 明確確認後才顯示完成；沒有啟用物品時會請先設定，不會空清單自動恭喜完成。

## 真實瀏覽器驗收

使用現有 Phase 7 test8 session，實際操作：

1. 首頁點 I'm Leaving，顯示 **3 件需確認**。
2. 手機取得 13.803333 秒桌面相關候選；鑰匙／錢包無相關可用觀察。
3. 點「尋找手機」開啟原搜尋，顯示 3 筆底層紀錄整理成 2 組時間／區域證據，包含 f414、f180 原片。
4. 返回後仍是 **3 件未確認**，沒有因搜尋自動勾選。
5. 手動確認手機後剩 **2 件**；撤銷後回到 **3 件**。
6. 再逐項確認，出現「你已在本次檢查手動確認所有必帶物品」。
7. 開始新檢查後，3 件全回未確認；之前的 COMPLETE 紀錄仍可檢視。
8. 真正重啟 Streamlit 服務，再開頁面；保留 3 個清單設定、2 次檢查、同一份新的未確認 active check。
9. 新檢查點「尋找鑰匙」，正確回 **UNKNOWN**，沒有顯示舊手機結果；返回後仍是 3 件未確認。
10. 首頁「分析新影片」仍開啟原上傳表單；無檔提交會阻擋，沒有啟動推論。

瀏覽器驗收紀錄：
已完成展示檢查 `295aa5eebc334a869ef1af57284de059`，5 個操作事件（含一次撤銷），3 件確認；目前新檢查 `c6e55439a90849f1ad1ff92eb3be1a65`，0 個確認事件。兩者皆為展示用途。

這是**實際瀏覽器操作**。不同記憶的隔離、清單 CRUD 與並非現有真實資料的分支另以 CPU／AppTest 驗證，不把測試 fixture 說成影片真值。

## 測試與完整性

**101／101 項通過：**

| 範圍 | 結果 |
|---|---|
| Phase 9 清單／提醒／串接與 AppTest | 15／15，9.257 秒 |
| Phase 8 搜尋／工作／證據回歸 | 15／15，4.213 秒 |
| Phase 4–7 原有 focused tests | 71／71，0.127 秒 |

新增測試涵蓋：設定保存、增刪改與停用、新檢查／續用／提交去重、確認與撤銷、舊確認不移轉、跨記憶隔離、快照不被設定編輯改寫、全確認與空清單、展示來源、候選不確認打包、無觀察不等於忘帶、正確 handoff、真實 Graph 提醒、其他指定類別、完整 UI 往返與重新開啟。

另外確認：
- 新 Python process 載入同一清單後保留 COMPLETE／OPEN 兩份紀錄。
- 提醒評估一次含三種物品 Graph 查詢，冷啟動量測約 **635 ms**；此數值不含完整頁面及影像渲染。
- 錄製／清單路徑未匯入 torch、vLLM、Ultralytics、Transformers。
- 原 session Graph／manifest、Nemotron raw hashes 未變，3,273 個歷史保護檔未變。
- 沒有新增 GPU 工作、模型推論、GT 裁決、production memory write、commit 或 push。

## 實作與儲存位置

新增：
`src/findmind_demo/checklist_store.py`、`departure.py`、`departure_ui.py`、`tests/test_findmind_departure.py`。

修改：
既有 `apps/findmind_demo.py` 加入首頁與導航；
`agent.py` 增加由清單明確指定類別的搜尋，沿用原查詢 API 及類別正規化；
原 Demo UI 測試補上新的首頁導航操作。

偏好與檢查資料：
**`artifacts/findmind_demo/checklist_state.json`**。
使用 OS 檔案鎖及 flush／fsync／atomic replace，避免重跑與多視窗覆寫。這個 store 不接受 Graph 路徑，也沒有 Graph 寫入功能。

正式報告、截圖與測試：
`artifacts/phase9/`。
日常入口：
`WORKSPACE/VLMtest/LATEST_REPORT.md`。

## 保留的限制

這是**使用者啟動的離開助理**，沒有自動偵測出門、背景攝影機、地理圍欄、忘帶判定或實體持有量測。手機候選可能不是本人同一支手機，鑰匙／錢包的感知效果仍未驗證，現有真實記憶仍 **0 VERIFIED locations**。

本次沒有重跑完整新影片 GPU 流程；保留 Phase 7／8 已完成的背景串接及其品質限制。實際多個不同真實影片的離開流程尚未擴大測試，記憶隔離已以明確的 store／Agent／UI 測試驗證。

競賽流程現在可連續操作，完成訊息代表**本次清單的明確手動確認完成**，不代表系統已從視覺證實物品隨身。
