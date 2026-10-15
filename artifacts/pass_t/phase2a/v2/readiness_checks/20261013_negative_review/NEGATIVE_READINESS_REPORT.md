# 進 Phase 2b 前：strict-negative 狀態與 test1 抽查

## 身分澄清已接入 pending / finalize

原問題確實存在：澄清檔案已寫入，但消費端未讀取。本次新增 hash-linked downstream resolution，只解除指定 ZIP、指定 reviewer 的身分旗標，不正規化原 ID、不解除 test3 揭露排除、不更動歷史答案或匯出。

| Strict-negative | 身分待辦 | 現有 quality_cleared_for_model_scoring | 本次視覺檢查 |
|---|---|---|---|
| test1 W03/W05 | 已解除 | true | 7 / 107 張，助理抽查 |
| test2 W01 | 已解除 | true | 未抽查 |
| test5 W01 | 已解除 | true | 未抽查 |

**旗標語意：原 V2 資格成立且匯入待辦已清空。它不是獨立視覺複核證明。** 新增 quality_gate_basis 與 independent_visual_quality_review 明確記錄這個界線。不能據此宣稱三窗已完成獨立品質覆核或正式 benchmark 放行。

實際 pending：7 → 3；現有品質旗標：0 → 3；formal_eligible 仍為 0、CAUSALITY_UNVERIFIED。

剩下 3 筆 legacy pending 是 test3、test5 W05、test7 W05。此次只接入身分澄清；A/B 已完成的 NON_EXHAUSTIVE_CONFIRMED sidecar 仍獨立保存，不需要使用者再重複審閱。Phase 2b 必須讀取其 exhaustive_review_readiness=false。test3 維持隔離。

## test1 快速視覺抽查

親自查看授權原尺寸影格 S000157、S000162、S000170、S000180、S000190、S000207、S000263，包含三個 COVERAGE。

- 157／162／170／180：手指接觸手機，抽看的畫面未呈現手機明確抬離桌面的證據。
- 190／207／263：手已離開，手機可見地留在桌面。
- 因此「手碰手機」與無 PICKUP/PLACEMENT 並不矛盾。此次抽查沒有找到需要改標事件的證據。
- **未逐格看完 107 張，不排除未抽看影格的短暫事件；這是助理抽查，不是新人工標註、整窗無事件證明或正式品質放行。**

原中末 COVERAGE 文字「無」資訊量很低，但不能僅憑文字自動判定標註錯誤；本次所看中末影格均有手機在桌上的視覺支持。

## 驗證與輸出

新增 10 個 resolution 測試及既有 41 個 external-store 測試：51 passed。實際執行 pending、finalize、再次 finalize；兩次輸出 path/hash 完全一致，沒有覆寫歷史匯出。

保存驗證：20269 個既有檔案 SHA-256 不變，Git HEAD 與既有 tracked worktree 變更不變。

新匯出 SHA-256：`ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c`

新匯出：`C:\Users\smile\Desktop\test2\mixure_test_SAM\artifacts\pass_t\phase2a\v2\external_returns\datasets\ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c\external_dev_gt.json`

本次實際執行的命令（專案根目錄）：

```powershell
.\.venv\Scripts\python.exe -B scripts/run_pass_t_external_dev.py pending
.\.venv\Scripts\python.exe -B scripts/run_pass_t_external_dev.py finalize
```

未執行 Phase 2b 模型推論或計分、未改原始人類答案、未寫 Graph、未 commit/push。前瞻抽樣、負控制、獨立第二標註、session 獨立性與 preregistered scoring 的門檻仍保留。
