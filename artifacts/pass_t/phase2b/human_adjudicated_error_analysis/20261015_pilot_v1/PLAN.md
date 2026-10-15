# Phase 2b Human-Adjudicated Error Analysis Plan

**Goal:** 匯入五份使用者完成的 review JSON，核對 provenance，以人類原始判定建立正式 error analysis，保留原始 annotation、GT、輸出及凍結元件。

**Architecture:** 單一 CPU-only 資料彙整器；只讀既有 JSON／文字與檔案 hashes，不讀取影像像素或載入模型。回傳的五份檔案逐 byte 複製至本版的 human_submissions/。Reviewer 拼字更正以獨立人類確認 sidecar 記錄，不重寫原檔。

**Files:** `build_analysis.py`、`human_submissions/call_XX_human_review.json`、`REVIEWER_IDENTITY_RESOLUTION.json`、`ADJUDICATION_IMPORT_AUDIT.json`、`HUMAN_ADJUDICATED_CALLS.json`、`PHASE2B_HUMAN_ADJUDICATED_ERROR_ANALYSIS.md`、`READONLY_PRESERVATION_REPORT.json`、`DELIVERABLE_HASHES.json`。

## Steps

- [x] 核對五份 schema/protocol/template SHA/raw SHA/call ID/表示/視窗，以及 reviewer、UTC 時間、Q1–Q7、所有 evidence aliases。
- [x] 對原始 review package、run、凍結元件、GT 等既有範圍建立 read-only preservation baseline，拷貝原始提交。
- [x] 記錄使用者確認：Call 3 的 review_0 是 reviewer_0 的拼字差異；不改原始字串。
- [x] 彙整 terminal disposition、question answer counts、representation 分層、時間與 before/after citations，以及 secondary error themes 的逐欄位來源。
- [x] 保留 Q1 選項與 notes 的衝突、Call 1 Q5 選項與文字範圍差異；不得自動修正人工欄位或將新摘要當新人工標籤。
- [x] 製作正式報告，明確保留 strict-invalid gate、非完整 GT、兩視窗相依性、單人審閱與 Call 2 未審定限制。
- [x] 驗證匯入副本、統計與 preservation hashes，發布 WORKSPACE/Pass_T 最新報告並更新導航，停止。

本任務不 commit/push，不修改 prompt、validator、runtime、matcher、GT 或 Memory Graph，也不啟動後續實驗。
