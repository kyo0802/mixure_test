# Pass T — Human-Adjudicated Error Analysis 已完成

最新：五份人工 review 全部完成並保全；**3 SUPPORTED_BY_OBSERVED_EVIDENCE（Calls 3/8/10）、2 WRONG_TARGET（Calls 1/4）**。五筆人工說明皆不支持模型的精確時間 claim。人類支持僅限 physical-event-level，不代表 target binding、timing、citations 與合約都通過。

五筆仍 strict-invalid，未重新放入 authoritative structured matching。Call 2 不在這次五份 review，未標成 human-adjudicated false negative。Q1/notes 一致性限制、Call 1 Q5 NOT_ASSESSABLE 原值與 reviewer typo resolution 全部列入正式報告。沒有改標註、GT、prompt、validator、runtime 或 Memory Graph。

當前已沒有待補的五筆 terminal disposition。[最新正式報告](LATEST_REPORT.md)；[保全原始提交與來源稽核](../../artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1)。後續實驗尚未啟動。

## 歷史 pilot 與 evidence package 背景

2026-10-15：freeze 與獨立 execution authorization 均通過。execution reviewer 為 reviewer_0，nonce/expiry/call_ids 由本人另行明確確認。**18/18 calls 完成；重試 0；guard stop 無；沒有追加模型呼叫。**

Frozen protocol SHA：`b7929b0e6ecaa651d7a316e838efe0b4c6437920a93b5b33bf41b6ce34740c9d`。

Full strict 10/18，全部 NO_CONFIRMED_EVENT；另外 8 筆 invalid，其中包含全部 5 筆 PICKUP 假說。Known-PICKUP 只有一筆 valid NO_CONFIRMED_EVENT 可評估，三種容忍值皆無匹配。Strict negatives 8/9 可評估且沒有 case alert，另 1 筆 invalid。不可轉成正式模型 accuracy、recall 或誤報率。

本次在報告完成後停止。Physical evidence adjudication 仍為 UNREVIEWED；沒有自動修 prompt、修輸出、重跑、寫 GT 或 Memory Graph。未替人類核准下一個實驗。

已建立五張事件卡（Calls 1/3/4/8/10）與 test5/test7 比較頁。40 個 event frame references（16 張不同 PNG）全部核對，原始來源沒有變更。Call 2 僅作 test7 NO_CONFIRMED_EVENT 對照。

**歷史證據入口：** [離線 evidence review 頁](../../artifacts/pass_t/phase2b/physical_evidence_review/20261015_real_dev_review_v1/PHYSICAL_EVIDENCE_REVIEW_INDEX.html) 保持初始空白模板不變。五筆已下載的完成結果已在最新 error analysis 另外保存，原頁面的 UNREVIEWED 不代表目前人工工作尚未完成。

[最新報告](LATEST_REPORT.md)；[已核准授權檔](Post_Freeze_Verification_20261015/execution_authorization.APPROVED.json)；proposal 保留為歷史提案，不是現行授權。
