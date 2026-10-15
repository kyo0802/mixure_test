# Pass_T

最新更新：2026-10-15。**[最新完整報告](LATEST_REPORT.md)** 固定放在本資料夾，每次完成工作都更新同一入口。

目前主要工作仍在 Pass I/T 平行標註＋實作。**Phase 3 VLM-first兩次真實Qwen實驗已完成，建議 REVISE_VLM_OBSERVATION_APPROACH**：test5文字辨認出手機pickup；test7文字卻否認pickup。兩份均有Markdown fence而JSON解析失敗，有效V3結構化預測0筆。未修復輸出、未重試、未自動開始整合；原CV signal checkpoint仍為BLOCKED。詳細原文、質性對照、收尾監控錯誤及CPU修正見最新報告。沒有GT／Graph更新或commit／push。

[回到總入口](../../START_HERE.md)

| 找什麼 | 開啟原檔／資料夾 |
|---|---|
| 最新完整報告 | [直接閱讀](LATEST_REPORT.md) |
| 最新待批准決策 | [直接閱讀](LATEST_DECISIONS.md) |
| Phase 3 VLM-first：兩次真實生成、原始輸出與實驗報告 | [完整實驗資料夾](../../artifacts/pass_t/phase3/vlm_physical_state_pilot_v1) |
| Phase 3 物理訊號 checkpoint、逐格圖與封存計算結果 | [完整資料夾](../../artifacts/pass_t/phase3/signal_spike_v1) |
| Phase 3A 稽核（架構圖、48 欄 matrix、真實樣本與 roadmap） | [完整稽核資料夾](Phase3_Observation_Capability_Audit_20261015) |
| 最新 Human-Adjudicated Error Analysis 與五份原始提交 | [分析資料夾](../../artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1) |
| 歷史 PICKUP 人工審閱頁（保留初始空白表單；已完成結果看最新報告） | [開啟證據頁](../../artifacts/pass_t/phase2b/physical_evidence_review/20261015_real_dev_review_v1/PHYSICAL_EVIDENCE_REVIEW_INDEX.html) |
| 歷史 evidence review 完整資料 | [套件目錄](../../artifacts/pass_t/phase2b/physical_evidence_review/20261015_real_dev_review_v1) |
| 本次 Real DEV 權威報告、逐 call 分析與雜湊 | [執行報告資料夾](../../artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f/report_v1_20261015) |
| 本次原始 18-call 回條與輸出 | [原始執行資料夾](../../artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f) |
| 工程修補報告、source diff與測試 | [修補資料夾](Execution_Readiness_Repair_20261015) |
| 歷史18call草案（現已有獨立 freeze 與 execution authorization） | [DRAFT_CONFIGURATION_CANDIDATE.json](Execution_Readiness_Repair_20261015/DRAFT_CONFIGURATION_CANDIDATE.json) |
| 歷史V1D 8條件結果 | [RESULTS.csv](RESULTS.csv) |
| 歷史V1D固定條件（非Protocol Freeze） | [開啟](../../artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c/V1D_PREREGISTERED_CRITERIA.md) |
| 歷史V1D原始證據與raw outputs | [封存資料夾](../../artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c) |
| 歷史V1C closeout／Variant B | [保留原報告](../../artifacts/pass_t/phase2b/qwen_nf4_engineering_closeout/20261015_94dcf4d4/PASS_T_PHASE2B_QWEN_NF4_ENGINEERING_CLOSEOUT_REPORT.md) |
| 事件標註目前結論 | [開啟](<../../artifacts/pass_t/phase2a/v2/reports/current_status_20261013_48a92354/PHASE2A_CURRENT_REPORT.md>) |
| 事件標註正式政策 | [開啟](<../../artifacts/pass_t/phase2a/v2/contracts/EVENT_GT_ANNOTATION_POLICY_V2.md>) |
| 歷史 Qwen 容量測試（10/14） | [開啟](<../../artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/PASS_T_PHASE2B_QWEN_NF4_BLOCKER_REMEDIATION_REPORT.md>) |
| DEV事件資料原始匯出 | [開啟](<../../artifacts/pass_t/phase2a/v2/external_returns/datasets/ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c/external_dev_gt.json>) |
| DEV事件複核補充必須一起讀 | [開啟](<../../artifacts/pass_t/phase2a/v2/exhaustive_reviews/adjudicated_7e28b9edf80a8e4da88caa66/adjudicated_dev_view.json>) |
| 人工標註交接說明 | [開啟](<../../docs/PASS_T_ANNOTATOR_HANDOFF.md>) |
| 實作程式 | [開啟](<../../src/memory_graph/pass_t>) |

**GT 讀取規則：** 原始 DEV 匯出與第 07 項複核 sidecar 必須合併解讀。A/B 是非完整事件清單；test3 隔離。不可把原匯出單獨稱為完整最終 GT。

**標註工具：** 交接說明是歷史發布紀錄，文中的 0/7 不是今日進度。需要重開主工具時，由專案根目錄執行 `.venv/Scripts/python.exe -B scripts/run_pass_t_phase2a_v2.py gui`；該工具是 canonical 標註來源，並不自動呈現外部匯入＋複核 sidecar 的完整結論。今日狀態請看第 01 項。
