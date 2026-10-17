# FindMind — 從這裡開始

更新：2026-10-14。**目前在 Pass I/T 平行標註＋實作。**

日常只需開啟 [WORKSPACE](WORKSPACE/)：

| 要做什麼 | 入口 |
|---|---|
| 看身分標註結果、QC、六案複核 | [Pass I](WORKSPACE/Pass_I/README.md) |
| 看事件標註、GT 政策、契約與相關實作 | [Pass T](WORKSPACE/Pass_T/README.md) |
| 看 VLM 測試報告、開啟九影片離線 GT 標註工具 | [VLMtest](WORKSPACE/VLMtest/README.md) |
| 找影片、資料、外部標註包、V297 基線 | [資料](WORKSPACE/Data/README.md) |
| 看這次搬移、驗證與完整資料夾說明 | [整理報告](docs/project_organization/REPORT.md) |

Windows 檔案總管可以直接點選各資料夾內中文命名的捷徑；Markdown 入口可跨環境閱讀。

## Workflow 與目前進度

Freeze → 模型篩選 → Stage 0 Smoke → **Pass I/T 平行標註＋實作（目前）** → Qwen baseline 對照實驗 → Shadow mode → End-to-end → Memory Graph

| 階段 | 狀態與邊界 |
|---|---|
| Freeze | V297 安全基線、既有資料與已批准契約保留；不代表後續 Qwen pilot protocol 已凍結 |
| 模型篩選 / Stage 0 Smoke | 已有前期工作；本次僅沿用既有結果，不聲稱所有模型均通過 |
| Pass I | 本輪標註、QC、Pilot 1 與爭議複核已結案；仍受身分資訊不足限制 |
| Pass T | 事件標註與實作進行中；DEV GT 有限制。Qwen 合成容量測試完成，協定待決策 |
| Qwen baseline 對照實驗 | 尚未進入此正式比較階段；下一步先審閱 Pass T 待決策清單、定稿與凍結 |
| Shadow mode / End-to-end / Memory Graph | 後續階段；歷史原型存在不等於這條 workflow 已驗收 |

## 檔案放置規則

- `WORKSPACE/`：目前工作入口。更新同一份索引，不再用新版本目錄充當日常入口。
- `src/`、`scripts/`、`configs/`、`tests/`：程式、執行腳本、設定、測試。
- `artifacts/pass_i/`、`artifacts/pass_t/`：唯一原始資料與追溯紀錄。既有版本／SHA 保留在底層。
- `archive/`：歷史實驗與舊測試暫存。部分歷史產物仍是上游來源，不能任意刪除。
- `docs/project_organization/`：本次整理紀錄、路徑映射與驗證。

新進度與常用連結維護在本頁和 WORKSPACE；只有不可覆寫的實驗證據才需要有獨立 run/version。舊 README.md 和 CURRENT_PIPELINE.md 因歷史封存保留，並非今日進度入口。
