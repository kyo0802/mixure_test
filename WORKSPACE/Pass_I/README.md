# Pass_I

本輪已結案：PASS_I_CLOSED_ACQUISITION_LIMITED。40 組 Pilot 1 已人工標註；六案複核已完成。主要瓶頸是可辨識身分資訊不足，另有部分人工可判斷案例的模型棄答。連結均指向原檔，不複製標註。

[回到總入口](../../START_HERE.md)

| 找什麼 | 開啟原檔／資料夾 |
|---|---|
| 本輪結案與限制 | [開啟](<../../artifacts/pass_i/reports/PASS_I_PHASE_CLOSEOUT.md>) |
| Pilot1人工標註稽核 | [開啟](<../../artifacts/pass_i/reports/PASS_I_DEV_PILOT_1_POST_HUMAN_AUDIT.md>) |
| 六案爭議複核結果 | [開啟](<../../artifacts/pass_i/reports/PASS_I_PILOT1_DISAGREEMENT_ADJUDICATION_REPORT.md>) |
| 證據品質QC | [開啟](<../../artifacts/pass_i/reports/PASS_I_EVIDENCE_QC_REPORT.md>) |
| Pilot1資料與原標註 | [開啟](<../../artifacts/pass_i/pilot1>) |
| 獨立複核資料 | [開啟](<../../artifacts/pass_i/adjudication>) |
| 標註工具啟動腳本 | [開啟](<../../scripts/start_pass_i_annotation.ps1>) |
| 實作程式 | [開啟](<../../src/memory_graph/pass_i>) |

**重開工具：** 在專案根目錄執行 `powershell -ExecutionPolicy Bypass -File scripts/start_pass_i_annotation.ps1`，服務啟動後再開 http://127.0.0.1:8511/ 。本次整理沒有啟動服務或要求重新標註。
