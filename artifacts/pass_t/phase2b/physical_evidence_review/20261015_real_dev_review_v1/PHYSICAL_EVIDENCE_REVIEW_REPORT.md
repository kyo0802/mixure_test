# Pass T Phase 2b — Physical Evidence Review Package

更新：2026-10-15。**PASS_T_PHASE2B_PHYSICAL_EVIDENCE_REVIEW_PACKAGE_READY**。

[直接開啟離線人工審閱頁](PHYSICAL_EVIDENCE_REVIEW_INDEX.html)。權威目錄：`artifacts/pass_t/phase2b/physical_evidence_review/20261015_real_dev_review_v1`。

## 內容與來源檢查

Exactly 5 event-bearing hypotheses；Call 2 僅是 test7 comparator。五筆 raw outputs 原值、structural defects 與 strict-invalid 身分均保留；五個人類 disposition 全為 **UNREVIEWED**。

| Call | Window | Representation | Timing alias | Exact model rationale | Sequence |
|---|---|---|---|---|---|
| 1 | test5 W05 | NATIVE_VIDEO_ARRAY | {'frame_alias': 'F0001', 'status': 'EXACT_SUPPLIED_FRAME'} | The card is picked up from the table. | 8/8 verified |
| 3 | test5 W05 | STORYBOARD | {'frame_alias': 'F0001', 'status': 'EXACT_SUPPLIED_FRAME'} | The phone is picked up from the surface. | 8/8 verified |
| 4 | test7 W05 | STORYBOARD | {'frame_alias': 'F0001', 'status': 'EXACT_SUPPLIED_FRAME'} | The ball is picked up from the surface in frame F0001. | 8/8 verified |
| 8 | test7 W05 | NATIVE_VIDEO_ARRAY | {'frame_alias': 'F0001', 'status': 'EXACT_SUPPLIED_FRAME'} | The object is picked up from the table. | 8/8 verified |
| 10 | test5 W05 | MULTI_IMAGE | {'frame_alias': 'F0077', 'status': 'EXACT_SUPPLIED_FRAME'} | The phone is lifted from the table. | 8/8 verified |


五筆 sequence 共 40 個 frame references（16 個不同 sampled PNG）；比較用 Call 2 另外引用 test7 的同一組 8 張。來源缺漏／hash mismatch／mapping unresolved 記錄：0。沒有 substitute、新取樣或 full-video decode。
Hash 只驗證既有 sampled assets/receipts；原始 movie SHA、native PTS 的產生流程本次沒有重新從影片驗證。缺少歷史 hash 的檔案以 OBSERVED_HASH_ONLY 標記，不能宣稱獲得歷史認證。

## Citation / timing 重點

- Calls 1/3/4/8 宣稱 F0001 的 EXACT_SUPPLIED_FRAME 是 PICKUP 時間。首張 supplied observation 沒有更早 sampled observation；需人工分辨 transition、狀態與 evidence bracket。
- Call 10 F0077 為合法第 6 張 sampled frame、window index 76，S000418、native PTS 13.933333333333334s。未視為 typo 或修正 alias。
- 卡片完整保留 event/window citations，以及 before/after state supporting aliases，框線標示僅表示模型主張。所有 referenced alias 均逐 call 檢查，不跨視窗混用 F0001。
- 每張 contact sheet 2400×1340，兩列八張、不裁切、標籤置於影像外。HTML 可逐張開啟 original sampled PNG。

## Representation 比較

- [test5 W05：Calls 1/3/10](TEST5_W05_REPRESENTATION_COMPARISON.html)：三種表示都提出 PICKUP；card / phone / phone，前兩個 F0001，Multi-image F0077。全部 strict-invalid，不選最佳表示、不裁定 noun mismatch 的物理錯誤。
- [test7 W05：Calls 2/4/8](TEST7_W05_REPRESENTATION_COMPARISON.html)：Storyboard ball 與 Native object 的 PICKUP 皆 invalid；Multi-image Call 2 為 strict-valid NO_CONFIRMED_EVENT。這是有用的 disagreement，不能自動稱 false negative。
- Storyboard 卡片連結 exact original storyboard、完整 source contact sheet 及 processor resize/grids。Native 明標 FRAME_MATCHED_ONLY — 8 source frames / 4 temporal units，不模擬 attention。

## 格式與物理證據分開

OUTPUT_CONTRACT_FAILURE：五筆 event timing_uncertainty 與 window uncertainty 空字串；Call 10 另有不符合三位數格式的 event ID。保持 invalid，不修復、不進 authoritative matching。
PHYSICAL_EVIDENCE_ASSESSMENT：全為 UNREVIEWED。本包沒有替人類決定事件真偽；schema pass 也不等於 physical correctness。既有 known PICKUP GT 只作 non-exhaustive scoped reference，不產生新事件時間、身分或完整事件清單。

## 人工下一步

1. 在 index 開啟 Calls 1、3、4、8、10，各查看全八張、原尺寸圖與 before/after/timing claims。
2. 依 Q1–Q6 評估目標、支撐面、持有、轉換、時間及不確定；以具體 aliases 引用可見證據。
3. 填 reviewer ID、Q7 disposition、總結 rationale 和 supporting aliases；每張卡下載獨立 human review JSON。五種可選 disposition 均為 review labels，不是新 GT。
4. 檢查兩個 representation comparison 頁，特別是 test7 Call 2；不要把格式與事件判斷混為一談。

## 保存與限制

保存結果：**UNCHANGED_WITHIN_AUDITED_SCOPE**；139 個 original files 前後比對，0 變更。[完整範圍](READONLY_PRESERVATION_REPORT.md)、[來源與 derivatives manifest](EVIDENCE_PROVENANCE_MANIFEST.json)、[限制](REVIEW_LIMITATIONS.md)。
未初始化 CUDA、未載入模型、沒有新 VLM generation、沒有完整影片 decode、未改原圖/GT/凍結元件/歷史執行報告；沒有 Memory Graph、commit 或 push。
包裝完成不代表 PICKUP 正確性已驗證。在此停止，等待五筆人工 evidence review。
