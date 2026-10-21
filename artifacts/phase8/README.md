# FindMind 互動找物 Demo

目前本機入口：[開啟 FindMind](http://127.0.0.1:8514/)。

從專案根目錄啟動：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_findmind_demo.ps1
```

要更換埠或上傳上限，加上 `-Port 8514 -MaxUploadMB 200`。自己啟動服務時請保留 PowerShell 程序；網址只供本機使用。使用現有 .venv 與 vendored Streamlit，不需要安裝新前端或雲端服務。

## 展示流程

1. 選「錄製結果 Demo」，開啟已保存的影片記憶。
2. 問「我的手機在哪裡？」或 “Where did you last see my phone?”。
3. 查看回答、候選卡片、同格框／遮罩和原生時間。展開可下載原始影格並查引用。
4. 切到「空間記憶時間線」，查看最早、最後與事件假說摘要。
5. 如要處理新影片，切「新影片分析」，選 MP4、勾選使用 GPU 再提交。其後可重新整理，從最近背景工作查看磁碟保存的狀態與日誌。

錄製模式不跑模型。新影片會呼叫既有 Phase 7 CLI；先前 36.77 秒影片約需 12 分鐘。已有的原片輸出不會被新分析覆寫。

手機實跑結果目前是「候選位置」，還沒有真實 VERIFIED 位置案例。Keys／wallet 能理解問題，但其感知效果尚未驗證。不要在展示時把類別候選說成使用者的特定物品，也不要將歷史畫面說成現在仍在原處。

## 背景工作與故障

`artifacts/findmind_jobs/<job_id>/state.json` 保存狀態，`pipeline.log` 保存 Phase 7 輸出，`execution.json` 保存實際命令。`artifacts/findmind_uploads/` 保存上傳原始 MP4；原 Phase 7 session 儲存在 `artifacts/findmind_sessions/`。

如果有工作正在執行，新提交會被單一 GPU 鎖阻擋。同一個提交 token 不會重複啟動。timeout／失聯可能留下 `artifacts/findmind_jobs/gpu.lock`；請先檢查該 job 的 PID、日誌和 WSL 模型程序，確認全部停止後才由操作者解除。系統不提供盲目解鎖或自動 generation retry。

若頁面拒絕連線，確認啟動 PowerShell 尚在執行，並查看 `artifacts/phase8/server.log`／`server_error.log`；不要同時開第二個同埠服務。若顯示 Graph／來源 hash 錯誤，請檢查原 session 檔案，不要手動把其他影片／影格換進去。

[完整報告](PHASE8_REPORT.md) · [日常最新報告](../../WORKSPACE/VLMtest/LATEST_REPORT.md) · [瀏覽器實際畫面](FINDMIND_DEMO.png) · [Demo 測試紀錄](demo_tests.log) · [Phase 4–7 測試](phase4_to_7_tests.log)
