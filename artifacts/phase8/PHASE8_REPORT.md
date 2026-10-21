# Phase 8：FindMind 互動找物 Demo

更新：2026-10-21。**PHASE8_INTERACTIVE_DEMO_IMPLEMENTED_AND_VALIDATED**

正式來源：`artifacts/phase8/PHASE8_REPORT.md`。已建立可操作的本機 Streamlit 應用，接到原 Phase 7 Graph 搜尋與影片處理 CLI。這次沒有新模型推論、GT 修改或 commit／push。

## 開啟與操作

目前本機網址：**http://127.0.0.1:8514/**

從 `C:\Users\smile\Desktop\test2\mixure_test_SAM` 啟動：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_findmind_demo.ps1
```

啟動命令使用既有 .venv 與 vendored Streamlit 1.50.0；只監聽 127.0.0.1，不需要網際網路。自己啟動時需保持 PowerShell 程序執行。可用 `-Port 8514 -MaxUploadMB 200` 調整埠與上傳上限。

1. **錄製結果 Demo**：選擇已有 Graph／receipt 的記憶。系統自動提供手機範例查詢，不會啟動模型。
2. 問「我的手機在哪裡？」、「幫我找手機。」或 “Where did you last see my phone?”。
3. 看候選區域、原生時間、身分狀態與同格影像。展開可看原始 PNG、完整引用及下載證據。
4. **空間記憶時間線**：查看首次／最後觀察、候選位置及不確定事件假說。
5. **新影片分析**：上傳 MP4、勾選實際 GPU 分析後提交。可關閉／重新整理頁面，工作紀錄仍保留；完成後點「開啟這份記憶並搜尋」。

新影片仍需要原 Phase 7 的 Windows CV／Qwen／SAM 與 Ubuntu WSL Nemotron 環境，沒有另裝模型或套件。36.77 秒影片先前耗時約 12 分鐘；本頁不顯示虛構百分比，也不保證新的處理時間。

## 已完成的互動功能

- 自動從 `artifacts/findmind_sessions/` 發現 session，列出影片、日期、完整／部分狀態、Graph 與證據可用性；未硬編 test8 session ID。
- 輕量確定性 Agent 解析中英文找物語句，直接呼叫既有 `search_session`，沿用 Graph 證據排序。
- 區分類別查詢與已授權身分。沒有 enrolled personal identity 時，「我的手機」會明說是手機類別候選。
- 三種結果狀態：LAST_CONFIRMED_LOCATION、POSSIBLE_LOCATIONS、UNKNOWN。可信狀態只使用 Graph 原有的 verified 結果。
- 同格／同區域的多筆證據合併成展示組；保留每筆原紀錄與原先排序，**不合併 persistent identity、不把組數當成物體數量**。
- 以同一 session 的 source manifest、frame SHA 與 native PTS 取圖；CPU 疊加保存的物體框／mask 與區域幾何。越界路徑、跨 session 影格、壞 hash 會拒絕顯示。
- UNKNOWN 顯示缺少位置證據的原因，有最後相關觀察時顯示其原片。沒有相關偵測不會說物品不存在。
- 新影片後台工作使用原 Phase 7 CLI，不複製感知流程。磁碟記錄工作、日誌、session ID 與階段；同一提交 token 不會重跑，GPU 鎖避免 App 內同時載入兩個大型工作。
- 失敗保留日誌及部分 artifacts；有安全保存的部分 Graph 仍可查詢。timeout 或尚存程序保留鎖，不自動冒險啟動下一個 GPU 工作。

離開前清單是次要選配，本版沒有新增；主流程集中在可用的搜尋展示。

## 使用真實保存結果驗證

使用 Phase 7 已完成的 test8 session；沒有重新跑其模型或換掉 raw outputs。

中文與英文手機問題都回 **POSSIBLE_LOCATIONS**，底層 **3 筆紀錄**呈現為 **2 組時間／區域證據**：

- f414，native PTS **13.803333 秒**，桌面相關候選。
- f180，native PTS **6.008333 秒**，2 筆同格同區域證據；不呈現成兩支已確認手機。

畫面顯示候選與身分未確認，並保留不能保證目前仍在原處、投影不代表物理接觸等說明。原片遮擋、部分裁切及 surface geometry 不可靠的限制仍存在。Graph 本身 **0 VERIFIED locations**。

「幫我找鑰匙。」回 **UNKNOWN**，沒有生成虛構卡片。鑰匙／錢包雖能解析語意，其實際感知效果尚未驗證。新影片頁面不選檔直接提交，會顯示「請先選擇 MP4 影片」而不啟動工作。

## 測試與量測

**86 項測試通過：15 項 Phase 8＋71 項既有 Phase 4–7。**

Phase 8 包含：
中英語句、未支援／多物品問題、候選與 verified 模板、同格展示分組、session 發現／hash／越界防護、GPU-free 重複查詢、證據錯格／壞 hash、上傳型別與大小、提交去重及 GPU 鎖、實際 Phase 7 命令格式、失敗日誌、timeout 部分 Graph 鎖保留、Streamlit AppTest 的真實 Graph 查詢與模式切換、兩份測試 session 的舊結果清除。

新影片工作測試使用 deterministic mocks 核對 CLI 與狀態處理；**這次沒有從 UI 再做一次完整 GPU 推論**。實際 GPU 整合成功的依據仍為 Phase 7 的記錄，不能把 mock 回報成新模型執行。

實際瀏覽器自動操作驗證：開啟錄製記憶、中文預設／英文搜尋、鑰匙 UNKNOWN、新影片模式、空檔提交驗證，以及服務重啟後再開記憶。這是自動瀏覽器驗證，不是人工使用者驗收。

CPU 新 process 實測：
| 項目 | 耗時 |
|---|---:|
| 載入 CPU Demo 模組 | 91.4 ms |
| Session 發現 | 5.5 ms |
| Graph／manifest 完整性載入 | 13.9 ms |
| 第一筆中文手機查詢 | 473.3 ms |
| 後續英文手機查詢 | 95.9 ms |
| 鑰匙 UNKNOWN | 85.1 ms |

瀏覽器頁面另實測中文查詢約 293 ms、英文約 98 ms、UNKNOWN 約 93 ms；這些是 Agent 查詢耗時，不含整頁載入與影像傳輸。已確認錄製模式沒有匯入 torch、vLLM、Ultralytics、Transformers。

測試記錄：`artifacts/phase8/demo_tests.log`、`phase4_to_7_tests.log`。第一次瀏覽器啟動遇到受限程序未開啟埠；只重啟本次服務後成功，最終服務採隱藏視窗運行。沒有降低 XSRF／CORS 保護。視覺驗收也修正了深色主題與淺色卡片的對比問題。

## 檔案與工作資料

```text
apps/findmind_demo.py                Streamlit 應用
src/findmind_demo/
  agent.py                          語意解析、Graph 查詢與回答／歷史
  sessions.py                       發現與完整性檢查
  evidence.py                       同格證據、範圍檢查、CPU 疊圖
  jobs.py                           磁碟工作、提交去重、單 GPU 鎖
scripts/
  start_findmind_demo.ps1            一個啟動命令
  run_findmind_job.py                背景 wrapper，呼叫原 Phase 7 CLI
artifacts/
  findmind_uploads/                  MP4 以內容 SHA 命名，保留原始顯示名
  findmind_jobs/<job_id>/            config／state／execution／logs
  findmind_sessions/<session_id>/    原 Phase 7 session 格式
  phase8/                           報告、測試與瀏覽器證據
```

原 Phase 7 runner、Graph schema、模型與排序都未改動。原 session Graph／manifest hash 檢查通過，沒有覆寫歷史記憶。

## 尚未完成與限制

- 未從 UI 重跑完整新影片 GPU 流程；本次驗證其呼叫契約及狀態處理，實際品質沿用 Phase 7。
- keys／wallet、跨場景與新物體辨識仍未做能力測量。0 verified 的現有 session 無法提供真實可信位置展示；verified 分支只做 CPU 契約測試。
- GPU 鎖只協調 Demo 啟動的工作，不能阻止其他手動程式占 GPU；原模型記憶體門檻仍有效。
- 無自動取消／中斷續跑。若 timeout 或程序失聯留下鎖，需先檢查相關模型程序與日誌，確認已停止後再由操作者解除；系統不會自動重試。
- 上傳預設 200 MB，先檢查 MP4 容器，再由 Phase 7 真正解碼／檢查 native PTS。離線 Demo 不需要網路。
- 原感知仍可能漏掉小物體、定位錯誤、誤認表面；Agent 只解釋這些證據，不能補出實體真值或目前位置。

**本版已可用於「選記憶 → 問物品 → 看候選與原片證據」的本機競賽展示；可靠找物產品仍須持續改善感知與身分。**
