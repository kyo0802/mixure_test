# Phase 2b — Human-Adjudicated Error Analysis

更新：2026-10-15T10:28:53.421415+00:00。**PASS_T_PHASE2B_HUMAN_ADJUDICATED_ERROR_ANALYSIS_COMPLETE**。

權威分析目錄：`artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1`。本報告整理使用者提交的五份人工審閱；不是新 inference、GT 或重新驗證模型輸出。

## 1. 摘要：事件假說有用，但現有輸出還不能直接使用

五筆人工作業全部完成且 provenance 核對通過：**3 筆 SUPPORTED_BY_OBSERVED_EVIDENCE、2 筆 WRONG_TARGET**。其他三種 disposition 與 UNREVIEWED 均為 0。沒有排除提交。

三筆 supported 只表示審閱者支持 physical-event-level PICKUP；不代表目標綁定、精確時間、state citations 或輸出合約全對。五筆全部仍是 strict-invalid；**strict-valid event-bearing predictions 維持 0**，不得回填 authoritative structured matching。

**五筆審閱文字都指出 exact event timing 不受引用影格支持。** Raw Q5 選項是 4 筆 CITATION_UNSUPPORTED、1 筆 NOT_ASSESSABLE（Call 1）；本報告沒有改選項，5 筆 timing 問題是明示人工 notes 的摘要。

人工回覆支援「兩個視窗中的手機 pickup 具有可見依據」；不能進一步說所有模型聲稱的物件、事件瞬間或完整因果鏈都成立。Call 1/4 的 terminal WRONG_TARGET 必須保留，不能因畫面另有 phone pickup 而改成 supported。

| Call | 視窗 | Representation | 人類 disposition（原值） | Supporting aliases（原值） |
|---|---|---|---|---|
| 1 | test5 W05 | NATIVE_VIDEO_ARRAY | WRONG_TARGET | F0001, F0016, F0062, F0077 |
| 3 | test5 W05 | STORYBOARD | SUPPORTED_BY_OBSERVED_EVIDENCE | F0001, F0016, F0062, F0077 |
| 4 | test7 W05 | STORYBOARD | WRONG_TARGET | F0001, F0031, F0046, F0062 |
| 8 | test7 W05 | NATIVE_VIDEO_ARRAY | SUPPORTED_BY_OBSERVED_EVIDENCE | F0001, F0016, F0031, F0046 |
| 10 | test5 W05 | MULTI_IMAGE | SUPPORTED_BY_OBSERVED_EVIDENCE | F0001, F0047, F0062, F0077 |

## 2. 匯入驗證、審閱者與保存

- 5/5 protocol、template SHA、raw SHA、call/window/representation、完成欄位、Q1–Q6 enums、UTC 提交時間及所有引用 aliases 通過。template SHA：`d0827edb333b4d341fbbc8fe3ee3cc0ff7c88d6c35685092276ff8876eb34170`。
- Reviewer：Call 3 原值 `review_0`，其他 `reviewer_0`。使用者明確確認「同一位，Call 3 是拼字差異」。以獨立 identity-resolution sidecar 記錄，同一 canonical reviewer_0，原檔不變。**這是一位 reviewer，不是多位獨立仲裁者。**
- 五份 Downloads 原始檔逐 byte 複製至 human_submissions/；保留原路徑與 SHA。既有 evidence review template/cards 繼續保留當時 UNREVIEWED 的歷史狀態；現行已完成結果在本分析，不覆寫歷史模板。
- 匯入格式／來源 PASS 不代表人工判斷無誤；Q1/notes 等一致性問題在下節公開。

## 3. 錯誤分層：不將 human support 等同完整正確

| Call | 目標 grounding：人工文字摘要 | Q5 原始選項 | Before/after citation：人工文字摘要 | Full strict |
|---|---|---|---|---|
| 1 | 人工 WRONG_TARGET：card 與所見 smartphone 不一致 | NOT_ASSESSABLE | 模型 F0016 held claim 與人類 F0016 on-surface 描述衝突 | FAIL，維持排除 |
| 3 | 人工認為 phone 與操作目標一致 | CITATION_UNSUPPORTED | 模型 F0016 不足；人類引用 F0062/F0077 | FAIL，維持排除 |
| 4 | 人工 WRONG_TARGET：將 phone 操作歸到 ball | CITATION_UNSUPPORTED | ball HELD_BY_PERSON 未觀察；人類看到 held smartphone | FAIL，維持排除 |
| 8 | 泛稱 object；人工保留 target association 未解 | CITATION_UNSUPPORTED | 模型 F0016 不足；人類引用 F0031/F0046 | FAIL，維持排除 |
| 10 | 人工認為 phone 與操作目標一致 | CITATION_UNSUPPORTED | F0077 支持 AFTER，不支持 BEFORE 或 exact pickup | FAIL，維持排除 |

### 3.1 Output contract

五筆 event timing_uncertainty 與 window uncertainty 為空；Call 10 event_id `PRED_EVT_0001` 亦不符三位數格式。這是既有 validator 失敗原因，未修復、未弱化、不因 human support 轉為 valid。

### 3.2 Target grounding / action-object association

- Calls **1、4** 的人工 terminal disposition 為 WRONG_TARGET。人工不是僅依 noun 不同下結論，而有手機/籃球操作、表面支撐與 held-state 的影格說明。
- Call **8** 的 generic object 假說獲 event-level 支持，但 reviewer 明確保留 explicit target-object association 未解，不能當完成 target binding 或全域身分確認。
- Calls **3、10** 的人工文字認為 phone 與可見物件一致。沒有因此建立 PersistentEntity 或修改 identity authorization。

### 3.3 Temporal localization

- Calls **1、3、4、8** 指到 F0001；人工指出該影格仍是 surface state，或所稱 ball 沒有 pickup。第一個 supplied observation 不等於 transition time。
- Call **10** 的 F0077 為有效 alias，對應第六張 sampled source S000418、13.933333333333334 秒。人工認為該處已是 held-state，不能支撐精確拿起瞬間。
- 人工可以支持 action-level transition，同時無法確定 separation 的精確時刻。Q4 的 DIRECT_TRANSITION_VISIBLE 原選項不自動產生 exact frame GT，也不將 before/after bracket 當事件 duration。

### 3.4 State evidence / citations

- Calls 1/3/8 的 F0016 after-state claim 與人類所指可見 state 不符或不足；Call 4 對 ball 的 held-state 沒有可見支持。這四個個案的具體證據見逐 call 表，不能只因後續有手機被拿起而替原 citation 補證。
- Call 10 以 F0077 同時證明 ON_SURFACE、HELD_BY_PERSON 與 exact event。人工接受它作 AFTER，指出它不能支撐 BEFORE 或 transition instant。
- 每一 human alias 都經現有 call mapping 驗證；alias 合法性與 cited evidence 是否支持主張是不同問題。

### 3.5 人工表單一致性警示（不自動修正）

- Calls **1、4** Q1 均選 IDENTIFIABLE_AND_CONSISTENT，但 notes 與 terminal WRONG_TARGET 指出 model-object mismatch。兩者並列保存；不把 Q1 的 5/5 該選項解讀成 5/5 正確 target grounding。
- Call **8** Q1 相同選項，但 notes 保留 explicit target association 未解；不能抹去限定語。
- Call **1** Q5 選 NOT_ASSESSABLE，notes 明確否定 F0001 exact timing。原 enum 計數與 notes 摘要分別報告。
- 上述不一致提醒日後若要做欄位級定量分析，需人類明確澄清；目前 terminal disposition 計數只忠實統計提交原值，未替人類重選。

## 4. 原始問項統計（只統計所選欄位）

| Question | 原始回答 counts |
|---|---|
| Q1_TARGET_IDENTITY | {'IDENTIFIABLE_AND_CONSISTENT': 5} |
| Q2_BEFORE | {'DIRECTLY_OBSERVED': 5} |
| Q3_AFTER | {'DIRECTLY_OBSERVED': 4, 'NOT_OBSERVED': 1} |
| Q4_PHYSICAL_TRANSITION | {'DIRECT_TRANSITION_VISIBLE': 4, 'ALTERNATIVE_EXPLANATION': 1} |
| Q5_TEMPORAL_SUPPORT | {'NOT_ASSESSABLE': 1, 'CITATION_UNSUPPORTED': 4} |
| Q6_CONTRADICTIONS | {'CONTRADICTION_IDENTIFIED': 5} |

報告 secondary themes 的 codes 在 HUMAN_ADJUDICATED_CALLS.json 逐項引用 human notes/rationale，是分析者對已提交文字的摘要，不是新增 reviewer-selected 標籤；不同 theme 可重疊，不能相加當不同錯誤個案總數。

## 5. Representation 與 window 描述

| Representation | 本次五筆選定 event-bearing calls 的人類判定 |
|---|---|
| NATIVE_VIDEO_ARRAY | {'WRONG_TARGET': 1, 'SUPPORTED_BY_OBSERVED_EVIDENCE': 1} |
| STORYBOARD | {'SUPPORTED_BY_OBSERVED_EVIDENCE': 1, 'WRONG_TARGET': 1} |
| MULTI_IMAGE | {'SUPPORTED_BY_OBSERVED_EVIDENCE': 1} |

- **test5 W05**：Native Call 1 WRONG_TARGET；Storyboard Call 3 supported，但 F0001 timing / F0016 after citation 有問題；Multi-image Call 10 supported，但 F0077 被錯當 before 與 exact timing。這是同一 source window 的三種輸出，不是三個獨立實例或排名。
- **test7 W05**：Storyboard Call 4 WRONG_TARGET（ball/phone association）；Native Call 8 supported at event level，但 explicit target association 與時間定位仍有問題。
- test7 Multi-image **Call 2** 原為 strict-valid NO_CONFIRMED_EVENT，這次五份提交沒有 Call 2 adjudication。雖然同視窗其他輸出的人工文字支持 phone pickup，仍不能把 Call 2 自動標成 human-adjudicated false negative。

## 6. 與完整 18-call pilot 的關係

既有 pilot 18/18 完成，10 筆 strict-valid 全為 NO_CONFIRMED_EVENT，8 筆 strict-invalid；本次只審閱其中 **5 筆 event-bearing strict-invalid**。另外 3 筆 invalid 與 10 筆 valid no-event 不因這次審閱獲得 physical correctness label。
原有 known-event matching、strict-negative case alerts 與不確定視窗結果均未改寫。人類支持不授權繞過 strict gate，也不構成新 structured prediction、NO_EVENT、更動過的 GT 或全視窗完整性。

## 7. 保守結論與當前瓶頸

此 pilot 的人類審閱顯示 VLM 可以提出有可見依據的 physical-event-level hypotheses（Calls 3/8/10），但目前仍同時存在 **structured-output contract failure、target/action misassociation 或 unresolved binding、temporal localization 與 state-citation grounding** 問題。現有輸出不能直接視為可靠的可執行事件記錄。
本結果支持把「是否有 pickup 依據」與「哪個物件、何時、哪些影格支持」分開評估；不證明 deterministic software 已能修復缺失，也不授權改寫模型事件。
架構維持 VLM 產生 physical-event hypothesis；deterministic software 後續做 evidence validation/temporal resolution/Memory Graph construction。這次沒有重新設計接口或實作修補。

**科學限制：** 僅一位 reviewer、兩個 non-exhaustive DEV windows、五個事先選定 event-bearing calls；重複 window/表示相依。八影格抽樣有未觀察間隙；Native 為 8 source frames / 4 temporal units。沒有 independent blinded inter-rater adjudication、沒有完整事件清單、沒有 validated PLACEMENT positive，也沒有新增 exact-event-time GT。人工對敘述的支持不能推廣到其他影片或完整系統。
不報正式 accuracy、precision、recall、F1、FPR、hallucination rate 或 generalization；3/5 是這五份提交的 disposition 計數，不是模型準確率。

## 8. 逐 case 完整審閱與證據

### Call 1 — test5 W05 / NATIVE_VIDEO_ARRAY

**人類原始判定：WRONG_TARGET**；原始 reviewer `reviewer_0`，確認後同一人 `reviewer_0`；提交時間 `2026-10-15T10:02:17.231Z`。

模型原話：The card is picked up from the table.

原始 timing：`{"frame_alias": "F0001", "status": "EXACT_SUPPLIED_FRAME"}`；before：`{"state": "ON_SURFACE", "supporting_frame_alias": "F0001"}`；after：`{"state": "HELD_BY_PERSON", "supporting_frame_alias": "F0016"}`。

**人工總結原文（保留限定語）：**

> The visual evidence supports a smartphone being picked up from the table, but the model incorrectly identifies the target as a card. The model also assigns the event to F0001, which shows the smartphone still on the table. Therefore, the prediction is classified as WRONG_TARGET, with an additional temporal-grounding error.

| 欄位 | 人工原選項 | 引用 aliases | 人工說明原文 |
|---|---|---|---|
| Q1_TARGET_IDENTITY | IDENTIFIABLE_AND_CONSISTENT | F0001, F0016, F0032, F0047 | The manipulated object appears to be a smartphone rather than a card. The model's target description is inconsistent with the visible object. The object is identifiable across the sampled frames. |
| Q2_BEFORE | DIRECTLY_OBSERVED | F0001, F0016 | A smartphone is visibly resting on the table in F0001 and F0016. This supports the ON_SURFACE state for the smartphone, but not the model's claimed card. |
| Q3_AFTER | DIRECTLY_OBSERVED | F0062, F0077 | The smartphone is visibly held above the table in F0062 and F0077. This supports the HELD_BY_PERSON state for the smartphone. It does not establish that a card was picked up. |
| Q4_PHYSICAL_TRANSITION | DIRECT_TRANSITION_VISIBLE | F0016, F0032, F0047, F0062, F0077 | The sampled sequence shows a hand interacting with the smartphone on the table, followed by the smartphone being lifted and held above the surface. This supports a PICKUP transition for the smartphone. However, the model identifies the manipulated object as a card, which is inconsistent with the visible evidence. |
| Q5_TEMPORAL_SUPPORT | NOT_ASSESSABLE | F0001, F0016, F0032, F0047, F0062 | The model cites F0001 as the exact PICKUP time, but the smartphone is still resting on the table at that frame. The subsequent frames show interaction with the object and its eventual lifting. The exact transition time is not established by F0001, so the model's timing claim is unsupported. |
| Q6_CONTRADICTIONS | CONTRADICTION_IDENTIFIED | F0001, F0016, F0062, F0077 | The model describes a card, whereas the visible manipulated object appears to be a smartphone. It also assigns the PICKUP event to F0001, when the smartphone remains on the table. Although the later frames support a smartphone PICKUP, the model's target identity and exact timing claims are inconsistent with the visual evidence. The sampled frames do not establish the precise instant of the transition. |

**引用影格來源（只映射既有 PTS，不建立新 GT 時間）：**

| Alias | Source frame | Native PTS 秒 | Source PNG SHA-256 |
|---|---|---|---|
| F0001 | S000342 | 11.4 | 10cc01413d92bd21672cfb1c7310f4be4b1e1fac3ac6708d525981d7b96c9f27 |
| F0016 | S000357 | 11.9 | 220497de57fab64e8a6964fbc022a682b814c4e548063b5a6ee58c0fb0b77d82 |
| F0032 | S000373 | 12.433333333333334 | b2c53d6b0b61b8326bd06b1b6758e516b1f19d8f8b2442c01d9a5ddd540311e7 |
| F0047 | S000388 | 12.933333333333334 | 8fd6ad4e1602cbc458eb214dd9ac606861c769b4238bae45123bfc715dcfa08d |
| F0062 | S000403 | 13.433333333333334 | 03b066756b322b77d1f723a4b30e3b3f23013d92bc01da1fdc37f5f08e70a487 |
| F0077 | S000418 | 13.933333333333334 | ae177c755952014df4259765c76b0e25eeceb318c5800a785e72f177a9053794 |

結構缺陷維持原樣：`["/events/0/timing_uncertainty:'' should be non-empty", "/uncertainty:'' should be non-empty"]`。

**保留的人工表單一致性警示：** Selected IDENTIFIABLE_AND_CONSISTENT, but notes and final WRONG_TARGET identify a model/object-description inconsistency. Preserve both; do not use Q1 alone to count correct grounding. Selected NOT_ASSESSABLE; notes explicitly reject F0001 exact timing. Raw selection remains NOT_ASSESSABLE, not recoded to CITATION_UNSUPPORTED.

[原始人工提交副本](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/human_submissions/call_01_human_review.json) | [原始模型輸出](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f/call_01/raw_output.txt) | [歷史證據卡（初始空白表單）](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/physical_evidence_review/20261015_real_dev_review_v1/EVENT_REVIEW_CARDS/call_01.html)

### Call 3 — test5 W05 / STORYBOARD

**人類原始判定：SUPPORTED_BY_OBSERVED_EVIDENCE**；原始 reviewer `review_0`，確認後同一人 `reviewer_0`；提交時間 `2026-10-15T10:13:10.081Z`。

模型原話：The phone is picked up from the surface.

原始 timing：`{"frame_alias": "F0001", "status": "EXACT_SUPPLIED_FRAME"}`；before：`{"state": "ON_SURFACE", "supporting_frame_alias": "F0001"}`；after：`{"state": "HELD_BY_PERSON", "supporting_frame_alias": "F0016"}`。

**人工總結原文（保留限定語）：**

> The sampled frames support a smartphone being picked up from the table. The model correctly identifies the target object and physical event type. However, its exact timing claim at F0001 is unsupported, and the cited after-state at F0016 does not clearly demonstrate the held state. The event is therefore supported by visual evidence, with temporal-grounding limitations.

| 欄位 | 人工原選項 | 引用 aliases | 人工說明原文 |
|---|---|---|---|
| Q1_TARGET_IDENTITY | IDENTIFIABLE_AND_CONSISTENT | F0001, F0062, F0077 | The manipulated object is identifiable as a smartphone, consistent with the model's description of a phone. The same object can be followed across the sampled frames. |
| Q2_BEFORE | DIRECTLY_OBSERVED | F0001, F0016 | The smartphone is visibly resting on the table in F0001 and F0016, providing direct evidence of the ON_SURFACE state before the pickup. |
| Q3_AFTER | DIRECTLY_OBSERVED | F0062, F0077 | The smartphone is visibly held above the table in F0062 and F0077, providing direct evidence of the HELD_BY_PERSON state after the pickup. The model's cited F0016 does not yet establish this after-state. |
| Q4_PHYSICAL_TRANSITION | DIRECT_TRANSITION_VISIBLE | F0016, F0032, F0047, F0062 | The sequence shows the hand interacting with the smartphone while it is on the table, followed by the smartphone being lifted and held above the surface. This directly supports a PICKUP transition. However, the precise instant of separation from the table is not fully resolved by the sampled frames. |
| Q5_TEMPORAL_SUPPORT | CITATION_UNSUPPORTED | F0001, F0047, F0062 | The model assigns the PICKUP event to F0001, but the smartphone is still on the table in that frame. The subsequent frames show the transition toward a held state. The evidence supports a pickup occurring later in the sampled sequence, not at the model's claimed exact frame. |
| Q6_CONTRADICTIONS | CONTRADICTION_IDENTIFIED | F0001, F0016, F0047, F0062 | The model correctly identifies the smartphone and the PICKUP action, but its exact event timing is inconsistent with the observed sequence. Its cited after-state frame F0016 does not clearly show the smartphone fully lifted. Sampling gaps also prevent precise localization of the separation from the table. |

**引用影格來源（只映射既有 PTS，不建立新 GT 時間）：**

| Alias | Source frame | Native PTS 秒 | Source PNG SHA-256 |
|---|---|---|---|
| F0001 | S000342 | 11.4 | 10cc01413d92bd21672cfb1c7310f4be4b1e1fac3ac6708d525981d7b96c9f27 |
| F0016 | S000357 | 11.9 | 220497de57fab64e8a6964fbc022a682b814c4e548063b5a6ee58c0fb0b77d82 |
| F0032 | S000373 | 12.433333333333334 | b2c53d6b0b61b8326bd06b1b6758e516b1f19d8f8b2442c01d9a5ddd540311e7 |
| F0047 | S000388 | 12.933333333333334 | 8fd6ad4e1602cbc458eb214dd9ac606861c769b4238bae45123bfc715dcfa08d |
| F0062 | S000403 | 13.433333333333334 | 03b066756b322b77d1f723a4b30e3b3f23013d92bc01da1fdc37f5f08e70a487 |
| F0077 | S000418 | 13.933333333333334 | ae177c755952014df4259765c76b0e25eeceb318c5800a785e72f177a9053794 |

結構缺陷維持原樣：`["/events/0/timing_uncertainty:'' should be non-empty", "/uncertainty:'' should be non-empty"]`。

[原始人工提交副本](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/human_submissions/call_03_human_review.json) | [原始模型輸出](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f/call_03/raw_output.txt) | [歷史證據卡（初始空白表單）](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/physical_evidence_review/20261015_real_dev_review_v1/EVENT_REVIEW_CARDS/call_03.html)

### Call 4 — test7 W05 / STORYBOARD

**人類原始判定：WRONG_TARGET**；原始 reviewer `reviewer_0`，確認後同一人 `reviewer_0`；提交時間 `2026-10-15T10:16:42.409Z`。

模型原話：The ball is picked up from the surface in frame F0001.

原始 timing：`{"frame_alias": "F0001", "status": "EXACT_SUPPLIED_FRAME"}`；before：`{"state": "ON_SURFACE", "supporting_frame_alias": "F0001"}`；after：`{"state": "HELD_BY_PERSON", "supporting_frame_alias": "F0016"}`。

**人工總結原文（保留限定語）：**

> The sampled frames show a smartphone being picked up from the table, while the basketball remains on the surface. The model incorrectly attributes the pickup event to the basketball and assigns it to F0001, where no such transition is observed. The prediction is therefore classified as WRONG_TARGET, with unsupported target-state and temporal claims.

| 欄位 | 人工原選項 | 引用 aliases | 人工說明原文 |
|---|---|---|---|
| Q1_TARGET_IDENTITY | IDENTIFIABLE_AND_CONSISTENT | F0001, F0031, F0046, F0062 | The model identifies the target as a ball, but the object visibly picked up is a smartphone. The basketball remains on the table during the observed phone manipulation. The model appears to have associated the pickup action with the wrong object. |
| Q2_BEFORE | DIRECTLY_OBSERVED | F0001, F0016 | The basketball is visibly resting on the table in F0001 and F0016. This supports the ON_SURFACE state of the model's claimed target before the alleged pickup. However, it does not establish that the basketball was subsequently picked up. |
| Q3_AFTER | NOT_OBSERVED | F0031, F0046, F0062 | The basketball is not observed being held by a person. Instead, F0031 and F0046 show a smartphone being held, while the basketball remains on the table. The claimed HELD_BY_PERSON state for the basketball is unsupported. |
| Q4_PHYSICAL_TRANSITION | ALTERNATIVE_EXPLANATION | F0016, F0031, F0046, F0062 | The visible manipulation involves a smartphone being lifted from the table, not the basketball. The basketball remains on the surface while the phone is held. The model's ball PICKUP claim is better explained as incorrect association of the visible phone pickup with the basketball. |
| Q5_TEMPORAL_SUPPORT | CITATION_UNSUPPORTED | F0001, F0016, F0031, F0046 | The model assigns the basketball pickup to F0001, but the basketball is still resting on the table at that frame and remains visible on the surface in subsequent frames. No basketball pickup is observed at the cited time. The phone pickup occurs later in the sampled sequence. |
| Q6_CONTRADICTIONS | CONTRADICTION_IDENTIFIED | F0001, F0031, F0046, F0062, F0077 | The model claims that the basketball is picked up and held by a person, but the observed hand-held object is a smartphone. The basketball remains on the table in the earlier frames. The camera subsequently moves away, so the basketball leaving the field of view must not be interpreted as evidence of pickup. The target identity, claimed after-state, and event timing are inconsistent with the observed evidence. |

**引用影格來源（只映射既有 PTS，不建立新 GT 時間）：**

| Alias | Source frame | Native PTS 秒 | Source PNG SHA-256 |
|---|---|---|---|
| F0001 | S000373 | 12.435 | e7b2f09f119510a117c550138f5e8c659354f7f0df6ba737d2936b7e2a244ca1 |
| F0016 | S000388 | 12.935 | 4e8770c51400fa0105dcafd5b54b61826ba4417df99733b2eedce411e1dea8f7 |
| F0031 | S000403 | 13.436666666666667 | 5ec94a5b70fa68a9b144d78e94b3f0727c30944462adb6b3009bd3023a5acf67 |
| F0046 | S000418 | 13.936666666666667 | 12f6213b67ce89b8c300065de20809fc38c9963fe981fdbe95f8226d878cc43c |
| F0062 | S000434 | 14.471666666666666 | 7620fdb3160afaefcfb496588c2c2c3e084537e8d42c9c9d61453f334a219ba1 |
| F0077 | S000449 | 14.971666666666666 | a12f87d8dc22b55e7cee417cd2fc0a54b42cb7352646fc00b693087b653326d8 |

結構缺陷維持原樣：`["/events/0/timing_uncertainty:'' should be non-empty", "/uncertainty:'' should be non-empty"]`。

**保留的人工表單一致性警示：** Selected IDENTIFIABLE_AND_CONSISTENT, but notes and final WRONG_TARGET describe basketball/phone misassociation. Preserve the contradiction.

[原始人工提交副本](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/human_submissions/call_04_human_review.json) | [原始模型輸出](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f/call_04/raw_output.txt) | [歷史證據卡（初始空白表單）](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/physical_evidence_review/20261015_real_dev_review_v1/EVENT_REVIEW_CARDS/call_04.html)

### Call 8 — test7 W05 / NATIVE_VIDEO_ARRAY

**人類原始判定：SUPPORTED_BY_OBSERVED_EVIDENCE**；原始 reviewer `reviewer_0`，確認後同一人 `reviewer_0`；提交時間 `2026-10-15T10:19:16.306Z`。

模型原話：The object is picked up from the table.

原始 timing：`{"frame_alias": "F0001", "status": "EXACT_SUPPLIED_FRAME"}`；before：`{"state": "ON_SURFACE", "supporting_frame_alias": "F0001"}`；after：`{"state": "HELD_BY_PERSON", "supporting_frame_alias": "F0016"}`。

**人工總結原文（保留限定語）：**

> The sampled frames support a smartphone being picked up from the table, consistent with the model's generic PICKUP hypothesis. However, the model does not explicitly identify the smartphone, and its exact event timing at F0001 is unsupported. The prediction is therefore supported at the physical-event level, with unresolved target grounding and temporal localization.

| 欄位 | 人工原選項 | 引用 aliases | 人工說明原文 |
|---|---|---|---|
| Q1_TARGET_IDENTITY | IDENTIFIABLE_AND_CONSISTENT | F0001, F0031, F0046 | The visible manipulated object is a smartphone. However, the model refers to it only as "the object" without specifying its identity. The event description is compatible with the visible phone pickup, but the model does not establish an explicit target-object association. |
| Q2_BEFORE | DIRECTLY_OBSERVED | F0001, F0016 | A smartphone is visibly resting on the table in F0001 and F0016. This provides direct evidence of an ON_SURFACE state before the observed pickup. |
| Q3_AFTER | DIRECTLY_OBSERVED | F0031, F0046 | The smartphone is visibly held above the table in F0031 and F0046. This supports the HELD_BY_PERSON state for the smartphone. The model's cited F0016 does not clearly establish that the object has already been lifted. |
| Q4_PHYSICAL_TRANSITION | DIRECT_TRANSITION_VISIBLE | F0016, F0031, F0046 | The sampled sequence shows a smartphone on the table, followed by the same smartphone being held above the surface. This provides visual support for a PICKUP transition. However, the model's generic reference to "the object" does not explicitly identify the smartphone, and the exact moment of lifting is not resolved. |
| Q5_TEMPORAL_SUPPORT | CITATION_UNSUPPORTED | F0001, F0016, F0031 | The model assigns the pickup to F0001, but the smartphone remains on the table in that frame. F0016 still shows the hand interacting with the phone near the surface, while F0031 shows the phone being held above the table. The pickup is supported by the later state transition, but not at the model's claimed exact frame. |
| Q6_CONTRADICTIONS | CONTRADICTION_IDENTIFIED | F0001, F0016, F0031, F0046 | The visible sequence supports a smartphone pickup, but the model does not identify the target beyond the generic term "object". Its exact timing claim at F0001 is inconsistent with the observed ON_SURFACE state, and its cited after-state at F0016 is not clearly sufficient to establish that the object is already held. The precise transition time remains uncertain. |

**引用影格來源（只映射既有 PTS，不建立新 GT 時間）：**

| Alias | Source frame | Native PTS 秒 | Source PNG SHA-256 |
|---|---|---|---|
| F0001 | S000373 | 12.435 | e7b2f09f119510a117c550138f5e8c659354f7f0df6ba737d2936b7e2a244ca1 |
| F0016 | S000388 | 12.935 | 4e8770c51400fa0105dcafd5b54b61826ba4417df99733b2eedce411e1dea8f7 |
| F0031 | S000403 | 13.436666666666667 | 5ec94a5b70fa68a9b144d78e94b3f0727c30944462adb6b3009bd3023a5acf67 |
| F0046 | S000418 | 13.936666666666667 | 12f6213b67ce89b8c300065de20809fc38c9963fe981fdbe95f8226d878cc43c |

結構缺陷維持原樣：`["/events/0/timing_uncertainty:'' should be non-empty", "/uncertainty:'' should be non-empty"]`。

**保留的人工表單一致性警示：** Selected IDENTIFIABLE_AND_CONSISTENT, while notes/rationale retain unresolved explicit target association. This is a scope qualification, not fully validated target binding.

[原始人工提交副本](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/human_submissions/call_08_human_review.json) | [原始模型輸出](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f/call_08/raw_output.txt) | [歷史證據卡（初始空白表單）](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/physical_evidence_review/20261015_real_dev_review_v1/EVENT_REVIEW_CARDS/call_08.html)

### Call 10 — test5 W05 / MULTI_IMAGE

**人類原始判定：SUPPORTED_BY_OBSERVED_EVIDENCE**；原始 reviewer `reviewer_0`，確認後同一人 `reviewer_0`；提交時間 `2026-10-15T10:21:05.931Z`。

模型原話：The phone is lifted from the table.

原始 timing：`{"frame_alias": "F0077", "status": "EXACT_SUPPLIED_FRAME"}`；before：`{"state": "ON_SURFACE", "supporting_frame_alias": "F0077"}`；after：`{"state": "HELD_BY_PERSON", "supporting_frame_alias": "F0077"}`。

**人工總結原文（保留限定語）：**

> The sampled frames support a smartphone being picked up from the table, and the model correctly identifies the target object and event type. However, its citation of F0077 as the before-state, after-state, and exact event time is inconsistent with the observed sequence. The prediction is supported at the physical-event level, but its temporal localization and before-state citation are incorrect.

| 欄位 | 人工原選項 | 引用 aliases | 人工說明原文 |
|---|---|---|---|
| Q1_TARGET_IDENTITY | IDENTIFIABLE_AND_CONSISTENT | F0001, F0062, F0077 | The manipulated object is identifiable as a smartphone, consistent with the model's description of a phone. The same object can be followed from its initial position on the table to the later hand-held state. |
| Q2_BEFORE | DIRECTLY_OBSERVED | F0001, F0016 | The smartphone is visibly resting on the table in F0001 and F0016, providing direct evidence of the ON_SURFACE state before the pickup. The model's cited F0077 does not support this before-state because the phone has already been lifted by that frame. |
| Q3_AFTER | DIRECTLY_OBSERVED | F0062, F0077 | The smartphone is visibly held above the table in F0062 and F0077. This directly supports the HELD_BY_PERSON state after the pickup, consistent with the model's after-state claim. |
| Q4_PHYSICAL_TRANSITION | DIRECT_TRANSITION_VISIBLE | F0016, F0032, F0047, F0062, F0077 | The sampled sequence shows a hand interacting with the smartphone on the table, followed by the smartphone being lifted and held above the surface. This supports a PICKUP transition rather than disappearance caused solely by occlusion. The exact moment of separation from the table is not fully resolved. |
| Q5_TEMPORAL_SUPPORT | CITATION_UNSUPPORTED | F0047, F0062, F0077 | The model assigns the exact PICKUP time to F0077 (13.933 s), but the smartphone is already held above the table in that frame. The transition is supported by earlier observations, particularly between the near-surface state in F0047 and the lifted state visible in F0062. F0077 supports the post-pickup state, not the exact instant of pickup. |
| Q6_CONTRADICTIONS | CONTRADICTION_IDENTIFIED | F0001, F0047, F0062, F0077 | The model correctly identifies the smartphone and the PICKUP event, but it cites F0077 as the before-state, after-state, and exact event time. Since the smartphone is already held above the table in F0077, that frame cannot establish the preceding ON_SURFACE state or the exact transition moment. Earlier frames provide the before-state evidence, while sampling gaps limit precise temporal localization. |

**引用影格來源（只映射既有 PTS，不建立新 GT 時間）：**

| Alias | Source frame | Native PTS 秒 | Source PNG SHA-256 |
|---|---|---|---|
| F0001 | S000342 | 11.4 | 10cc01413d92bd21672cfb1c7310f4be4b1e1fac3ac6708d525981d7b96c9f27 |
| F0016 | S000357 | 11.9 | 220497de57fab64e8a6964fbc022a682b814c4e548063b5a6ee58c0fb0b77d82 |
| F0032 | S000373 | 12.433333333333334 | b2c53d6b0b61b8326bd06b1b6758e516b1f19d8f8b2442c01d9a5ddd540311e7 |
| F0047 | S000388 | 12.933333333333334 | 8fd6ad4e1602cbc458eb214dd9ac606861c769b4238bae45123bfc715dcfa08d |
| F0062 | S000403 | 13.433333333333334 | 03b066756b322b77d1f723a4b30e3b3f23013d92bc01da1fdc37f5f08e70a487 |
| F0077 | S000418 | 13.933333333333334 | ae177c755952014df4259765c76b0e25eeceb318c5800a785e72f177a9053794 |

結構缺陷維持原樣：`["/events/0/event_id:'PRED_EVT_0001' does not match '^PRED_EVT_[0-9]{3}$'", "/events/0/timing_uncertainty:'' should be non-empty", "/uncertainty:'' should be non-empty"]`。

[原始人工提交副本](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/human_submissions/call_10_human_review.json) | [原始模型輸出](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f/call_10/raw_output.txt) | [歷史證據卡（初始空白表單）](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/physical_evidence_review/20261015_real_dev_review_v1/EVENT_REVIEW_CARDS/call_10.html)


## 9. 交付與停止

- [Import/provenance audit](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/ADJUDICATION_IMPORT_AUDIT.json)
- [Machine-readable human records and sourced error themes](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/HUMAN_ADJUDICATED_CALLS.json)
- [Human-confirmed reviewer identity correction](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/REVIEWER_IDENTITY_RESOLUTION.json)
- [Original-source preservation audit](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/READONLY_PRESERVATION_REPORT.json)
- [Deliverable SHA-256 manifest](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/DELIVERABLE_HASHES.json)

五份人類標註皆已完成；沒有待補的 terminal disposition。欄位級 Q1/Q5 一致性限制仍如上揭露，不在本任務自動改答案。此處停止，不調 prompt、不重跑、不追加模型、不更動 GT、不寫 Memory Graph、不 commit/push。
