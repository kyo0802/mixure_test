# Final Qwen NF4 Exploratory Pilot — 人工審查候選

Task: `PASS_T_PHASE2B_QWEN_NF4_FINAL_PROTOCOL_REVIEW`  
2026-10-15；Review ID **67b59d603e36**；candidate semantic SHA-256 `67b59d603e36bb11b9e496afc3796e9ea531d0cbca06d6d29359993a32726edf`。

**READY_FOR_HUMAN_REVIEW — NOT_APPROVED — NOT_FROZEN — EXECUTION_BLOCKED_AS_IS。** 這是可審閱的完整提案，不是已核准部署。既有 V1D strict 1/8 的失敗結果不變；D4 只排除可見的特定序列化/指令缺陷，未證明 physical reasoning 正確，也未解除任何人類 gate。

本次只讀既有文字、schema、metadata、manifest 和回條；未載入模型、CUDA、GPU、新 VLM generations，未讀／decode 真實 DEV 像素，未建立 fixtures、修改既有檔案/Phase2a GT、freeze、pilot、Memory Graph、commit/push。僅本 WORKSPACE 新目錄有新增文件；依 narrower scope 不更新既有 LATEST_REPORT/README。

## 1. 研究目的與四個獨立軸

主要目的：觀察 Qwen 在真實 FindMind 有限視窗是否提出有可見證據支持的 PICKUP/PLACEMENT 物理事件假說。

A. **Execution reliability**：計畫18、實際開始/完成/失敗/未執行數、OOM/timeout/EOS/cap、runtime/resource記錄。  
B. **Structured contract**：syntax/schema/semantic/citation/full strict 分開，分母明示。  
C. **Physical reasoning/support**：人工檢查可見狀態變化、target association、遮擋/缺口、cites 是否支持；不從 label claim 或 schema pass 推定 physical correctness。  
D. **Representation differences**：同六窗三表示的描述性對照；相同 source selection 不等於相同 token/detail/temporal precision，不宣稱 superiority。

VLM 負責事件假說；本次不重設 Event-to-Graph，未來 deterministic evidence normalization/Graph construction 不在此任務範圍。

## 2. Proposed configuration（所有值均待人工核准）

| Component | Proposed value / exact source |
| --- | --- |
| Model | Existing Qwen2.5-VL-7B-Instruct NF4 double / BF16 / SDPA; revision cc594898137f460bfe9f0759e9844b3ce807cfb5 (E15/E24) |
| Task/system | Exact immutable V1D (E16), exact V2 system (E18), existing schema (E22); no new identity clause |
| Representations | Multi-image8 / Storyboard8 / Native Video Array8; same Uniform8 source set; six windows × three =18 planned calls |
| Sampling | round(i*(N-1)/7), i=0..7, Python ties-to-even over authorized ordered frame list; endpoints; no GT event positions |
| Reference/citations | NONE; C3 retains supplied frame aliases; paired video units reported privately, no change to validator |
| Native video | FRAME_MATCHED_ONLY, 8 source frames→4 units, no dropped frames/no padding, do_sample_frames=False; fps=7/source PTS span; native PTS remains private authority |
| Pixels/storyboard | min3136/max200704 effective spatial pixels; tiles480×270 +32 label, 3columns, canvas1440×906; no new timestamp overlay |
| Generation | do_sample=False; seed42; max_new_tokens1024; repeat1; warmup0; no quality retry |
| Timeouts | load120 / gen300 / supervised request330 seconds; proposed whole6060 seconds (new bound, not old synthetic3200) |
| Failure handling | Transport retry0 proposed; strict-invalid retained and continue if healthy; hard safety/process/deadline failures stop and preserve missing results |
| Safety | load free GPU≥10GiB/RAM≥8GiB; generation freeGPU≥2GiB; stop usedGPU>14.5GiB, ownedRSS>20GiB, systemRAM<2GiB; nominal polling1s |
| Matching | Full strict valid only; 0/.2/.5s all reported; proposed greedy one-to-one closed-interval gap=max(0,gs-pe,ps-ge), require_overlap=False; T04 prevents claiming current source fully implements this; unknown timing unmatchable, no invented midpoint |
| Reporting | Four separate axes execution/contract/physical support/representation; no formal model metrics, no Memory Graph writes |


三個 temporal sensitivities 都是固定 report 欄位；0.2s 不作唯一主結果、不依結果挑選 tolerance。native PTS 不用模型整數化時間或 sampling_gap/2 取代；before/after evidence brackets 也不自動等於物理事件 duration。

## 3. Exact six-window cohort

| 視窗（去重單位） | Item ID / opaque ID | 用途 | 既有來源 frames / PTS span |
| --- | --- | --- | --- |
| test1__W03 / test1__W05 | PT2A_9d15d2a6b56b56d0 / W_5597d9b003977e053d70 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS | S000157–S000263 (107 frames); 5.235000–8.770000s |
| test2__W01 | PT2A_b35d807b28b92101 / W_ec4751640324779435e6 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS | S000180–S000287 (108 frames); 6.008333–9.580000s |
| test5__W01 | PT2A_fe0910d66f4c5614 / W_aef405003cc72cef0044 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS | S000162–S000233 (72 frames); 5.400000–7.766667s |
| test5__W05 | PT2A_eb60192e6986cb4f / W_f1d4f821d33515975293 | KNOWN_EVENT_MATCHING_ONLY | S000342–S000449 (108 frames); 11.400000–14.966667s |
| test7__W05 | PT2A_c58b4df88a2f6801 / W_b8a53fea6aa8b92dc94f | KNOWN_EVENT_MATCHING_ONLY | S000373–S000479 (107 frames); 12.435000–15.973333s |
| test8__W07 | PT2A_5dbb180e8ff88762 / W_db55b29f820c2b3e3afb | DESCRIPTIVE_UNCERTAINTY_ONLY | S000936–S001053 (118 frames); 31.211667–35.101667s |


test1 W03/W05 是同一項，只跑一個單位；test3 W07 污染揭露維持排除。三 strict-negative 的原 attestation 不等於新增獨立全窗品質認證；兩 known PICKUP 不是 exhaustive positive；test8 不是 negative；沒有 validated PLACEMENT positive。詳 [cohort/GT 限制](PILOT_COHORT_AND_GT_LIMITATIONS.md)。

## 4. Strict-invalid preregistration

每個 raw output byte-for-byte 保存，不修文字、不補欄位、不發明引用、不放寬 parser/schema/validator。只有 full-strict valid 能進 authoritative structured matching。strict-invalid 不是 NO_EVENT，也不計為合法模型 abstention；只可另列 descriptive qualitative review。缺失/失敗/未執行保留原因及各階段狀態，不能從分母移除。詳 [strict-invalid 政策](STRICT_INVALID_AND_QUALITATIVE_REVIEW_POLICY.md)。

## 5. Prior evidence and risk

- V1C engineering closeout：既有12-call Variant B strict2/12、9個 event-bearing 均 invalid；不與後來新 fixtures 的 V1D 當作受控改善實驗。
- V1D：JSON8/8，full strict1/8，event-bearing6/8全部invalid；9個 timing_uncertainty 空、6個root uncertainty空、1個window citations空。既有原始回應/結果不變。
- D4_NO_DEFECT_FOUND：八次捕獲文字保留全部三段新增指令，無直接矛盾/空值範本；沒有 full historical token/pixel 值，故非底層路徑與模型能力的全面證明。
- 原 V1D 人工套件說不建議 freeze，candidate technically eligible=False；本新任務只授權提出探索性風險接受方案，**沒有把原 gate 改成 PASS**。H01 必須明確人工接受這個例外。

## 6. 現況與核准邊界

| ID | Readiness finding | Evidence | Required follow-up |
| --- | --- | --- | --- |
| T01 BLOCKING_REAL_NATIVE_V1D | V1D prompt pin requires synthetic_only=True; honest real DEV deployment must not impersonate synthetic data. | E25 lines74-79 | Separately authorized future implementation review for a real-DEV V1D route, preserving the prompt/schema and approval boundary; no bypass/patch in this task. |
| T02 BLOCKING_AS_IS_FREEZE_AND_18_CALL_RUNNER | Legacy freezer pins templates/event_reasoning_prompt_v1.txt; transport/prepared configurations use MULTI_IMAGE/STORYBOARD/REENCODED_AUTHORIZED_VIDEO and synthetic allowlists, not the proposed complete V1D native-array protocol. No verified approved real V1D 18-call manifest/config exists. | E27 lines75-79, E28 lines17-18/92-99, E29; existing prepared deployments | Future source/metadata-only integration authorization and newly reviewed component hashes before a supported freeze; do not label the present legacy path ready. |
| T03 UNVERIFIED_INTEGRATED_REPORTING_AND_GATING | Strict validator early returns on schema errors; evaluator accepts a prediction object and has no built-in full-strict-status parameter. Existing primitives do not alone prove all18 calls are gated and all3 sensitivities/stages are reported. | E23/E29/E30 | Before actual execution, verify a caller gates matching on full strict validity and reports unassessed stages without repair; no evaluator/schema changes authorized now. |
| M01 UNVERIFIED_CURRENT_MEDIA_INTEGRITY_AND_REAL_SERIALIZATION | Uniform8/native PTS/source IDs/recorded hashes verified against existing JSON; no source media bytes, actual video pixels, real native arrays or final18 V1D processor receipts were opened/created. | E07/E08 plus six INPUT metadata files | Do not invent current media/payload hashes. Actual file integrity and real input receipts remain future authorized preflight/execution gates. |
| T04 BLOCKING_CLOSED_INTERVAL_MATCH_SEMANTICS | For nonzero-width GT intervals and a predicted point strictly inside, overlap length is zero and E30 uses distance to an endpoint instead of zero interval gap. Thus current implementation can reject a contained point at tolerance0. No actual GT times were opened to determine which six-window cases would trigger it. | E30 lines36-45 | Human must approve the intended closed-interval rule (H14), then separately authorize and verify minimal matcher integration/correction before scoring/freeze; do not silently use the current edge-case behavior or change evaluator in this task. |


目前 protocol **可供人工審查，但不能使用現有 legacy 路徑直接 freeze/執行**。特別不得將 real DEV 假標為 synthetic_only=True 來繞過 T01，不得退回 V1C、舊AVI或改少於18call作替代。T04另記目前matcher與候選closed-interval規則的不一致，不能先計分再決定解釋。

下一個人類核准字串：

`APPROVE_PHASE2B_QWEN_NF4_EXPLORATORY_PROTOCOL 67b59d603e36 FREEZE_ONLY NO_EXECUTION`

此字串表示對本候選值/風險的 freeze-only 明確授權要求，**本次未收到、未生效**；不代表 execution permission，也不授權本任務修改 source。即使未來收到，T01/T02/T04 的現有程式 gate/語義差異仍不能跳過；必須先另行授權所需整合、以更新後 component hashes 重新人工確認，才可使用支援的路徑 freeze。若任何候選內容或 component 改變，必須新的 review ID，不能沿用本次核准。這裡沒有提供可自動執行的 freeze 指令。

## 7. Proposed call order

排序 key=SHA256 UTF-8 `PASS_T_PILOT_ORDER_V1/{opaque_id}/{representation}/NONE/1`，升序；不依 GT/答案排序。舊 draft ref=UNRESOLVED/encoded-video 的 order 不直接沿用。

| 順序 | opaque unit | representation |
| --- | --- | --- |
| 1 | W_f1d4f821d33515975293 | NATIVE_VIDEO_ARRAY |
| 2 | W_b8a53fea6aa8b92dc94f | MULTI_IMAGE |
| 3 | W_f1d4f821d33515975293 | STORYBOARD |
| 4 | W_b8a53fea6aa8b92dc94f | STORYBOARD |
| 5 | W_5597d9b003977e053d70 | STORYBOARD |
| 6 | W_db55b29f820c2b3e3afb | NATIVE_VIDEO_ARRAY |
| 7 | W_ec4751640324779435e6 | NATIVE_VIDEO_ARRAY |
| 8 | W_b8a53fea6aa8b92dc94f | NATIVE_VIDEO_ARRAY |
| 9 | W_aef405003cc72cef0044 | NATIVE_VIDEO_ARRAY |
| 10 | W_f1d4f821d33515975293 | MULTI_IMAGE |
| 11 | W_db55b29f820c2b3e3afb | MULTI_IMAGE |
| 12 | W_5597d9b003977e053d70 | MULTI_IMAGE |
| 13 | W_ec4751640324779435e6 | STORYBOARD |
| 14 | W_db55b29f820c2b3e3afb | STORYBOARD |
| 15 | W_ec4751640324779435e6 | MULTI_IMAGE |
| 16 | W_5597d9b003977e053d70 | NATIVE_VIDEO_ARRAY |
| 17 | W_aef405003cc72cef0044 | MULTI_IMAGE |
| 18 | W_aef405003cc72cef0044 | STORYBOARD |


## 8. Exact component and evidence identities

[FINAL_COMPONENT_HASH_MANIFEST.json](FINAL_COMPONENT_HASH_MANIFEST.json) 列候選語義身分、全部 component SHA、文件 SHA、原8 raw/receipt SHA、六窗 metadata 和 proposed configuration。不是 freeze receipt。真實媒體 hash 只保留既有記錄，不假稱本次重新驗證；真實18個完整V1D序列化 hash 未建立。

| Evidence | Existing source | SHA-256 |
| --- | --- | --- |
| E01 | [eligibility.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/readiness/eligibility.json) | c231967ccc7007749e80f570d0abb33c65ee964a036f5da51fb2f60cbbd5c07b |
| E02 | [GT_ELIGIBILITY_LIMITATIONS.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/readiness/GT_ELIGIBILITY_LIMITATIONS.md) | 5b1ad17c0398719d3c9a35762dadfe891a57b969f2a77b1e81d03112cf5322c5 |
| E03 | [PHASE2A_CURRENT_REPORT.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2a/v2/reports/current_status_20261013_48a92354/PHASE2A_CURRENT_REPORT.md) | c148ebbe914c8451b061a7f6052afb3c5b3720e303004a3559673ca68e9aba8e |
| E04 | [NEGATIVE_READINESS_REPORT.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2a/v2/readiness_checks/20261013_negative_review/NEGATIVE_READINESS_REPORT.md) | 96df7be2328a402a9675297a88743ffcadb72b650aa7da3cc833e001404ca986 |
| E05 | [pilot_preregistration_draft.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/pilot_preregistration_draft.json) | a91296147e184c608945bb328fd6802a2b89619e85f801ea56f030d4bc3281fd |
| E06 | [QWEN_NF4_PROTOCOL_DECISION_SHEET.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/QWEN_NF4_PROTOCOL_DECISION_SHEET.md) | 71ca5a35fdf885220bc8f5492614b6825f41949bdf1fa7105cbb1a9f9569e712 |
| E07 | [candidate_manifests.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/private/candidate_manifests.json) | dde3f7a1e8b6d541416f9c8d4318aad6bb846cd78c09f0b076cf3d91930b0c8f |
| E08 | [timing.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/private/timing.json) | be7b0a6ab0d35b5e869fde4a6591b640a38782830f25362c01c73c56a360cf2c |
| E09 | [actual_container_pts_metadata.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/private/actual_container_pts_metadata.json) | ffac6819f07599efdf03658e92ec6787d3e9995464fb4e46df039defa629978c |
| E10 | [QWEN_NF4_PILOT_DECISION_PACKAGE_V3.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/prompt_clarification_matched8_preflight/qwen_nf4/20261015_rev2_4f1c8d251b1e/QWEN_NF4_PILOT_DECISION_PACKAGE_V3.md) | f5e2486ccbeda92277f131c9bc1a0fe2b851e56c7adff5ef88426b7b6faf3b4d |
| E11 | [freeze_blockers.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/prompt_clarification_matched8_preflight/qwen_nf4/20261015_rev2_4f1c8d251b1e/freeze_blockers.json) | 055e06cc97d92c192d20412417a1c40942a4120e38ee1b3c69972f2e0dfb2c61 |
| E12 | [PASS_T_PHASE2B_QWEN_NF4_V1D_REGRESSION_REPORT.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c/PASS_T_PHASE2B_QWEN_NF4_V1D_REGRESSION_REPORT.md) | 626e1685e381bf368d1ad32ba24ff4d1069f5faf23013671f74716e7029c0fc4 |
| E13 | [V1D_HUMAN_PILOT_DECISION_PACKAGE.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c/V1D_HUMAN_PILOT_DECISION_PACKAGE.md) | f4224167ddd70801f8db1de120608a9820878b637ad6577452cc5b6dbf9cdce3 |
| E14 | [V1D_REGRESSION_SUMMARY.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c/V1D_REGRESSION_SUMMARY.json) | db57b314df9aa72938946c5ecf418d024dc2616fe17960459cc54d061193968e |
| E15 | [V1D_PREREGISTERED_EXECUTION_MANIFEST.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c/V1D_PREREGISTERED_EXECUTION_MANIFEST.json) | f4a91abc2c43a8c8247c784a7b6d861aeba6e453e17381e79d75515101673c60 |
| E16 | [QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c/QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt) | 7008254e618dc8bacdbdeaae3cbf471220afb5efd6c80afc8b9ea5fb5c96b9b0 |
| E17 | [QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/prompt_clarification_matched8_preflight/qwen_nf4/20261015_rev2_4f1c8d251b1e/QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt) | 3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722 |
| E18 | [v2_system_unchanged.txt](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/prompt_clarification_matched8_preflight/qwen_nf4/20261015_rev2_4f1c8d251b1e/prompt_candidate/v2_system_unchanged.txt) | 9b76b7e320dfb677a1cb8566c16dff15785759bc4915375123bc12dd118fd08e |
| E19 | [diagnosis_report.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/V1D_Contract_Diagnosis_20261015/diagnosis_report.md) | 0f3cb73c20de77db8b438e3166d6d28d9c129845f07f9a934a7ab1295f1727a6 |
| E20 | [diagnosis_decision.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/V1D_Contract_Diagnosis_20261015/diagnosis_decision.json) | 2eaf970c10b89e4d85c8e7449dbe07937ee81cedeb4d3e9e561389013d7f9f5e |
| E21 | [final_verification.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/V1D_Contract_Diagnosis_20261015/final_verification.json) | 96a6ca1914cfb994d5a16bdb5a07d002d768ae69159cdd37a3b09b916690c9d5 |
| E22 | [prediction_v1.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/contracts/prediction_v1.json) | f8b0dfb6c62301baabff5e1adfddf14dc6be9381aa84c884fc70f5318abcedc3 |
| E23 | [predictions.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/predictions.py) | c4b077374d50fc478c29d0009180d488c60a463fa8bffa183a179c5f736f1d37 |
| E24 | [nf4.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/local_vlm/nf4.py) | fc15d9012a3a992e4dcb9e66a3b458b242c319b1efe5f4d30dae19b81364547b |
| E25 | [video_array_bridge.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py) | 5cfebb8d93294585cc62531258fba79f2d5abc2cb57e0f1ba1e108664288ed4e |
| E26 | [qwen_contract.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/local_vlm/qwen_contract.py) | 6e52a2be7847ccb6c8e5f04bb7a229ded18d74908268967370169a5d42e1f397 |
| E27 | [transport.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/local_vlm/transport.py) | e385b2c86fc7f6f4b59d563c0d0639dc1e7e6d9c05c8f85ab9478e9ea34f8cc6 |
| E28 | [protocol.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/protocol.py) | bc860e6f89401ff54dc27c6dc2dcc7b0e7c794f59d12c8bad5f918381cecee32 |
| E29 | [inference.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/inference.py) | e6bdbf19d4e3fb9a84a318fc49a88fc4b1f41e9af889fc8b80f30377793ba67f |
| E30 | [evaluation.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/evaluation.py) | 4d69a83f361579b0e22a00075b3e1e9a5255daec416c9a5937240f22c7f19826 |
| E31 | [supervisor.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c/supervisor.py) | 8143afa6207c73a822997f6f5cb0db37a5cc217d344cb381ffffd788dc99b9d5 |
| E32 | [inputs.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c/inputs.py) | 14fc94869ca72121ea75fd84caf9ebb9b36b478574b1735da8b7320db910b579 |
| E33 | [V1D_RESOURCE_REPORT.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c/V1D_RESOURCE_REPORT.json) | f1a23eeb191aa37e41ad866efdcf08f7b6b65cdedeb95a076cf8f431eb3711ad |
| E34 | [PASS_T_PHASE2B_QWEN_NF4_ENGINEERING_CLOSEOUT_REPORT.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/qwen_nf4_engineering_closeout/20261015_94dcf4d4/PASS_T_PHASE2B_QWEN_NF4_ENGINEERING_CLOSEOUT_REPORT.md) | ec12a357c5e0a310ec215417fa508897af1fe5b8a5c0d31cc86d04c44699b1df |
| E35 | [QWEN_NF4_MATCHED_VIDEO8_CPU_PREFLIGHT_REPORT.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/prompt_clarification_matched8_preflight/qwen_nf4/20261015_rev2_4f1c8d251b1e/QWEN_NF4_MATCHED_VIDEO8_CPU_PREFLIGHT_REPORT.md) | 0c70170c5a38c4b37dfe9535a94f102688f30f83351d591f458ab8ec19bf6d5d |
| E36 | [protocol_decisions.template.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/config/protocol_decisions.template.json) | 69fa06e0f52039666f33338de3a9af060b6b7aece7f06a57851b822940eeea8e |
| E37 | [model_visible.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/model_visible.py) | c4707239d795167d2c054e1a23ef2c1e153ada3e34477e85939d4fa80c10889c |
| E38 | [config.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/config.py) | 64fae16245300fb52e51a1b1523fbd863004312b813b0e394b828b71954acea6 |
| INPUT-W_5597d9b003977e053d70 | [source.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/private/W_5597d9b003977e053d70/source.json) | f8ed581d87390a04e3c11cf8254b8a7921ca6ced4115abe3669bc343687a4d19 |
| INPUT-W_ec4751640324779435e6 | [source.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/private/W_ec4751640324779435e6/source.json) | 1e01bf71cc40e70aff6930708f32970482d491ee28b0efd05ddb0fac03f125f8 |
| INPUT-W_aef405003cc72cef0044 | [source.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/private/W_aef405003cc72cef0044/source.json) | 34cbd08d0b9b3e005ddb829545a48849918c56cf1249be300e9041fbdc07ecd5 |
| INPUT-W_f1d4f821d33515975293 | [source.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/private/W_f1d4f821d33515975293/source.json) | 2a11b86871e25fe785b48441aefedf08c303ea28d271e0c813622758ff6f47b1 |
| INPUT-W_b8a53fea6aa8b92dc94f | [source.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/private/W_b8a53fea6aa8b92dc94f/source.json) | 3ad2d21c87cd15c909544e37754bca65c34a35d49edcb2e41e670cc5844c6749 |
| INPUT-W_db55b29f820c2b3e3afb | [source.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/preflight/qwen_nf4_protocol_candidates/v1/candidate_003/private/W_db55b29f820c2b3e3afb/source.json) | 7f5f4f0326f15721028496357b7d60badbe8b01520af77f5b0b4cd9385f770c6 |


Stop: human review only. Phase2b 尚未完成。
