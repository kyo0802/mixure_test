# Pass_T

目前主要工作。Phase 2a 的事件政策、工具、人工回傳與複核已完成，資料僅具有限 exploratory DEV 用途。Phase 2b 基礎設施與 Qwen NF4 合成容量測試完成，等待協定決策。最新一輪 11/11 條件可生成，嚴格輸出通過 15/33；不是事件 accuracy。實際 Phase 2a 模型推論尚未執行。

[回到總入口](../../START_HERE.md)

| 找什麼 | 開啟原檔／資料夾 |
|---|---|
| 事件標註目前結論 | [開啟](<../../artifacts/pass_t/phase2a/v2/reports/current_status_20261013_48a92354/PHASE2A_CURRENT_REPORT.md>) |
| 事件標註正式政策 | [開啟](<../../artifacts/pass_t/phase2a/v2/contracts/EVENT_GT_ANNOTATION_POLICY_V2.md>) |
| Qwen容量測試最新報告 | [開啟](<../../artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/PASS_T_PHASE2B_QWEN_NF4_BLOCKER_REMEDIATION_REPORT.md>) |
| 下一步待決策清單 | [開啟](<../../artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/QWEN_NF4_PROTOCOL_DECISION_SHEET_V2.md>) |
| 實驗計畫草案尚未凍結 | [開啟](<../../artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/QWEN_NF4_PILOT_PREREGISTRATION_DRAFT_V2.md>) |
| DEV事件資料原始匯出 | [開啟](<../../artifacts/pass_t/phase2a/v2/external_returns/datasets/ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c/external_dev_gt.json>) |
| DEV事件複核補充必須一起讀 | [開啟](<../../artifacts/pass_t/phase2a/v2/exhaustive_reviews/adjudicated_7e28b9edf80a8e4da88caa66/adjudicated_dev_view.json>) |
| 人工標註交接說明 | [開啟](<../../docs/PASS_T_ANNOTATOR_HANDOFF.md>) |
| 實作程式 | [開啟](<../../src/memory_graph/pass_t>) |

**GT 讀取規則：** 原始 DEV 匯出與第 07 項複核 sidecar 必須合併解讀。A/B 是非完整事件清單；test3 隔離。不可把原匯出單獨稱為完整最終 GT。

**標註工具：** 交接說明是歷史發布紀錄，文中的 0/7 不是今日進度。需要重開主工具時，由專案根目錄執行 `.venv/Scripts/python.exe -B scripts/run_pass_t_phase2a_v2.py gui`；該工具是 canonical 標註來源，並不自動呈現外部匯入＋複核 sidecar 的完整結論。今日狀態請看第 01 項。
