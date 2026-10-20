# Pass T — 事件標註與契約

2026-10-18：VLM 模型測試與比較的目前結論已移至 [VLMtest](../VLMtest/LATEST_DECISIONS.md)。後續模型實驗報告使用該入口。

## 歷史 VideoLLaMA3 實際資料集推論

更新：2026-10-17。**VIDEOLLAMA3_AVAILABLE_WINDOW_INFERENCE_COMPLETE**。69 筆條目中 17 個具既有視覺配置，16 個不同輸入全部實際生成，test1 W05 明確共用 W03，0 執行失敗、0 重試。52 個空配置條目列 unavailable；test6 無推論，不臨時補採樣。

13／16 raw JSON 可解析，2／16 full strict-valid；2 份 token-cap 截斷、1 份括號錯誤。大量輸出只寫籃球，test5/test7 known PICKUP 均無可用手機事件假說。**VideoLLaMA 本配置不取代 Qwen、不進主流程、暫不做 hybrid。** 保留 Qwen C 為研究基線，不代表它已具可靠事件／身分／Graph 更新能力。

下一步僅建議人工盲評 test5/test7 同一組影格的逐物件 state 與 alias 支持，尚未啟動。沒有改 prompt、GT、Qwen runtime 或既有 Graph；沒有 commit／push。模型環境已可用，沒有未解決的載入／生成 blocker。

[最新完整報告](LATEST_REPORT.md)；[本次原始輸出與來源資料](../../artifacts/pass_t/phase3/videollama3_full_v1)。

## 歷史 Qwen Observation Ablation ＋ Cross-model Preparation

更新：2026-10-17。**STATE_FIRST_IS_PROMISING，僅限partial state-observation signal。** B高細節2次、C state-first2次全部完成，無重試；A未重跑。B未解決test7事件遺漏；C寫出test7手機桌面／手持，卻沒有PICKUP hypothesis並仍回NO_CONFIRMED_EVENT。部分HELD引用超出可見支持。六筆A/B/C原文都含Markdown fence，各strict0/2，沒有補欄位或提升invalid。

四次授權已結束；不再追加Qwen試驗。已備model-neutral adapter boundary與4個CPU contract tests，未下載／執行新VLM。下一個任務建議比較同8張source frames的逐物件可見狀態、alias與不確定性，事件另列；完整共享prompt與模型版本／量化／環境／call上限仍需使用者授權。較小候選VideoLLaMA3-7B的16GB量化／custom code相容性未驗證；Nemotron有更明顯記憶體／4-image與Linux依賴限制。沒有宣稱模型品質排名或直接開始下一實驗。

[最新完整報告](LATEST_REPORT.md)；[跨模型準備與官方來源](../../artifacts/pass_t/phase3/observation_ablation_v1/CROSS_MODEL_PREPARATION.md)。原CV checkpoint、歷史實驗、human reviews及GT不變；未寫Graph、未commit／push。

## 歷史 Phase 3 VLM-first Physical-State Experiment

**兩次授權真實生成已完成，建議 REVISE_VLM_OBSERVATION_APPROACH。** test5文字描述phone PICKUP與ON_SURFACE→HELD合理；test7文字否認pickup，與可見手持後狀態及既有人工事件說明不符。兩筆皆有Markdown fence，原始JSON解析失敗；A另缺other_objects.evidence，B缺events。沒有去fence、補欄位或把invalid當有效NO_EVENT。

本次實驗已停止，未自動啟動完整Phase 3整合或下一次推論；原CV checkpoint結論不變。VLM自述證據不是獨立physical validation，不能升格SUPPORTED Decision或寫Graph。兩次均EOS，沒有重試；parent結束監控race的錯誤與CPU修正已保全於 [最新報告](LATEST_REPORT.md)。

## 歷史 Phase 3 v2 Signal Checkpoint

**PHASE3_SIGNAL_CHECKPOINT_BLOCKED**。Step 1 的16張 exact PNG 已完成 YOLO11s／YOLO11n-pose、相對運動及既有 SAM／Guard 覆蓋檢查；兩個視窗均僅3/8張偵測到手機。Pose有玩偶誤判，沒有可靠 grip/contact/support producer；不可把幾何量升格成物理狀態。10/10完整性檢查通過，522個既有source/reference hashes未變。門檻修訂0次。

依使用者 Phase 3 v2 第6節停下；**尚未完成完整 Phase 3，沒有執行 Qwen、最終 Decision 或 Graph 更新**。目前需使用者決定是否另行允許限定的手／物接觸可行性測試，或改採報告列出的其他方法。最新結論、三個按成本與用途排序的選項及逐格圖見 [最新報告](LATEST_REPORT.md)。沒有自行啟動下一階段。

## 歷史 Phase 3A Observation Capability Audit

最新為只讀架構／資料能力稽核。**目前不足以自動 authoritative validate PICKUP 或 PLACEMENT**。

三個主要 P0：獨立 ON_SURFACE／HELD/contact/support 觀察不足；target association/authorization 與必要 reliability 不足；CV 採樣與 source PTS／alias 覆蓋未統一。test5/test7 W05 的 saved CV 與 Uniform8 exact-frame overlap 為1/8、0/8，current final-ledger target authorizations 皆0；這些不是「手機不存在」的證據。

Current builder 已有 camera median translation、MOVING/STATIONARY／carried_like heuristic；不能當作可靠手持狀態。V297 camera/interaction diagnostics 為另一條 legacy 分支。詳細證據見 [最新完整報告](LATEST_REPORT.md) 與 [Phase 3A 全部稽核文件](Phase3_Observation_Capability_Audit_20261015)。

**建議而未授權實作：** 先做3B只讀 Observation Adapter，只暴露既有真實欄位／來源／unknowns；再做3C CPU Decision checks及3D實際 observation gap test。未啟動任何下一階段、模型、schema freeze、Graph 更新或 commit/push。

## 歷史 Phase 2b Human-Adjudicated Error Analysis

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
