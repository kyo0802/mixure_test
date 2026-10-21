# FindMind 版本保存範圍

目前版本為 **Phase 9.1**，接續 Phase 5–9 的 `10357b07`。此版保存互動 Graph adapter／本機元件、搜尋交接、Nemotron 資產 manifest／verification cache、timing instrumentation、測試、報告與小型截圖。操作及環境說明見 [README](../../README.md)，實測限制見 [最新報告](LATEST_REPORT.md)。

驗收：149 tests 通過；full SHA 63.723 s、cached metadata 0.324 s。GPU cold／warm 與整支影片加速尚未量測。原始驗收報告的「未 commit／push」描述驗收完成時點；本頁與 Git 為版本發佈入口。

完整 session、模型、環境、影片、背景工作及個人清單留在本機。含完整展示清單的原始 `PRESERVATION_CHECK.json` 不發佈，改提供 [發佈驗證摘要](../../artifacts/phase9_1/RELEASE_VERIFICATION_SUMMARY.json)。既有 8,302 筆歷史檔案刪除及無關暫存不納入此次提交。

下方保留上一版 Phase 5–9 的保存範圍；實際 commit 與遠端 SHA 請以 Git 命令核對。

更新：2026-10-21。分支：`codex/pass-i-current`。

本次版本整理 Phase 5–9 的程式、測試、進度報告與展示指南，接續已提交的 Phase 4（`44620185`）。最新操作入口見 [專案 README](../../README.md)，功能與實測見 [最新報告](LATEST_REPORT.md)。實際 commit 與遠端狀態以 Git 為準：

```powershell
git log -1 --oneline
git rev-parse HEAD
git ls-remote origin refs/heads/codex/pass-i-current
```

## 此次保存

- Phase 5：表面區域、物體／區域關係候選與既有 TemporalMemory 搜尋整合。
- Phase 6：Qwen 目標／表面定位與 SAM2.1 refinement。
- Phase 7：新影片單一入口、原生 PTS／來源追溯、順序 GPU 階段與隔離 session。
- Phase 8：Streamlit 中英找物、歷史候選與同格證據、磁碟背景工作。
- Phase 9：可編輯必帶清單、每次檢查、本人確認／撤銷、找物交接、歷史與展示重設。
- 測試、各階段文字報告、Phase 8／9 小型展示截圖與測試紀錄。

Phase 9 完成時 101 focused tests 通過，並完成瀏覽器與服務重啟驗證。本次版本整理沒有新增模型推論。仍是候選空間記憶，0 VERIFIED；本人清單確認不等同視覺持有證明。

## 留在本機

模型、環境、原片、完整推論 session／Graph／證據影格、上傳資料、背景工作、個人清單與檢查紀錄，以及大型診斷／暫存。

其他人 clone 後需要另備相容環境與資料，才能執行 GPU 分析或查詢錄製結果。報告中的本機資產連結不代表它們已上傳。

這次僅提交明確選取的相關檔案。工作目錄中既有大量歷史刪除與無關暫存保留原狀，未納入提交；GitHub 保存的既有歷史檔案也未清除。
