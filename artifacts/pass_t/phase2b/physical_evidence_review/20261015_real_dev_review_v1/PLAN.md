# Physical Evidence Review Package Implementation Plan

**Goal:** 將既有五筆 strict-invalid PICKUP 假說整理為可追溯的離線人工審閱包，保留所有實際判定為 UNREVIEWED。

**Architecture:** 單一工作樹、單一 CPU-only 產生器；只讀取既有 sampled PNG、storyboard、metadata、raw 與 receipts。不執行 inference、不重新取樣、不修改原始資料。新增檔案集中在本目錄；發布固定 WORKSPACE/Pass_T 最新報告入口。

**Tech Stack:** Python standard library + Pillow；離線 HTML/CSS/原生 JavaScript，人工表單透過下載獨立 JSON 保存，不覆寫 GT。

## 執行步驟

- [x] 建立完整來源雜湊 baseline：原始 pilot 全部檔案、frozen component files、核准記錄、兩個視窗 metadata/16 張 sampled PNG/2 張 storyboard、GT 與相關 sidecar。
- [x] 核對 frozen protocol、call receipts/raw SHA、八影格 mapping/順序/native PTS、storyboard SHA，缺漏不替換。
- [x] 逐 call 產生來源不裁切的兩列 contact sheet，框線標示 timing/citation/before/after，native 標示四個 units。
- [x] 產生五張 HTML 卡、各自 JSON 原值紀錄、兩個 representation 比較頁；test7 對照 call 2 但不新增事件審定記錄。
- [x] 建立 Q1–Q7 人工表單及初始 UNREVIEWED JSON；下載人工填寫結果，必須有 reviewer/rationale/有效 aliases，無自動事件判定。
- [x] 產生研究摘要、限制、來源與 derivative provenance manifest、preservation report。
- [x] 驗證五筆事件、六筆比較 calls、所有 references、表單初始狀態、檔案 links、hashes、原始檔案前後一致；目視檢查 contact sheets、檢查 HTML 內容與 JavaScript 表單。未宣稱完整 browser end-to-end 測試。
- [x] 發布 WORKSPACE/Pass_T 最新報告，停止，不 commit/push 或追加實驗。

產生器：`build_review_package.py`。交付檔名依使用者要求；額外附 `SOURCE_PRESERVATION_BASELINE.json`、`PACKAGE_CHECKS.json` 及卡片 JSON，供重現與稽核。
