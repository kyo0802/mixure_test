# Unresolved Decisions — 67b59d603e36

**21項human decisions全部PENDING；候選可審閱，執行仍阻擋。** Source review能證明既有實作/失敗，不能替人核准。

## 優先級 P0：不得繞過

| ID | Readiness finding | Evidence | Required follow-up |
| --- | --- | --- | --- |
| T01 BLOCKING_REAL_NATIVE_V1D | V1D prompt pin requires synthetic_only=True; honest real DEV deployment must not impersonate synthetic data. | E25 lines74-79 | Separately authorized future implementation review for a real-DEV V1D route, preserving the prompt/schema and approval boundary; no bypass/patch in this task. |
| T02 BLOCKING_AS_IS_FREEZE_AND_18_CALL_RUNNER | Legacy freezer pins templates/event_reasoning_prompt_v1.txt; transport/prepared configurations use MULTI_IMAGE/STORYBOARD/REENCODED_AUTHORIZED_VIDEO and synthetic allowlists, not the proposed complete V1D native-array protocol. No verified approved real V1D 18-call manifest/config exists. | E27 lines75-79, E28 lines17-18/92-99, E29; existing prepared deployments | Future source/metadata-only integration authorization and newly reviewed component hashes before a supported freeze; do not label the present legacy path ready. |
| T03 UNVERIFIED_INTEGRATED_REPORTING_AND_GATING | Strict validator early returns on schema errors; evaluator accepts a prediction object and has no built-in full-strict-status parameter. Existing primitives do not alone prove all18 calls are gated and all3 sensitivities/stages are reported. | E23/E29/E30 | Before actual execution, verify a caller gates matching on full strict validity and reports unassessed stages without repair; no evaluator/schema changes authorized now. |
| M01 UNVERIFIED_CURRENT_MEDIA_INTEGRITY_AND_REAL_SERIALIZATION | Uniform8/native PTS/source IDs/recorded hashes verified against existing JSON; no source media bytes, actual video pixels, real native arrays or final18 V1D processor receipts were opened/created. | E07/E08 plus six INPUT metadata files | Do not invent current media/payload hashes. Actual file integrity and real input receipts remain future authorized preflight/execution gates. |
| T04 BLOCKING_CLOSED_INTERVAL_MATCH_SEMANTICS | For nonzero-width GT intervals and a predicted point strictly inside, overlap length is zero and E30 uses distance to an endpoint instead of zero interval gap. Thus current implementation can reject a contained point at tolerance0. No actual GT times were opened to determine which six-window cases would trigger it. | E30 lines36-45 | Human must approve the intended closed-interval rule (H14), then separately authorize and verify minimal matcher integration/correction before scoring/freeze; do not silently use the current edge-case behavior or change evaluator in this task. |


T01/T02/T04為as-is實際blocker；T03為整合驗證缺口；M01為現行媒體/真實serialized input證據缺口。後兩者不能用本次不允許的像素讀取/processor實作補完。T04不宣稱這六窗必定已計錯，只指出目前公式不完整實作候選的point/closed-interval契約。沒有新增模型權重下載問題，也沒有假稱目前RAM/VRAM足夠。

## 優先級 P1：人類必須決定

| ID | Decision | Proposed value | Human status |
| --- | --- | --- | --- |
| H01 | Failed-regression risk acceptance | Use immutable V1D for exploratory hypotheses despite strict 1/8; six event-bearing outputs all invalid | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H02 | Model/revision | Existing local Qwen2.5-VL-7B-Instruct NF4 double quantization, BF16, SDPA; revision cc594898137f460bfe9f0759e9844b3ce807cfb5 | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H03 | Prompt/system/schema | Exact V1D + unchanged V2 + unchanged Prediction V1/parser/validator; no V1E | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H04 | Representation choice | All three representations, 8 source frames each; 18 planned calls, no 12-call fallback | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H05 | Sampling | Uniform8 round(i*(N-1)/7), Python ties-to-even, include endpoints; same selection all representations | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H06 | Target reference and ambiguity clause | NONE for all six windows; no new identity-ambiguity clause; existing prompt/outcomes unchanged | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H07 | Citation C3 | Retain supplied per-frame aliases; native 8 aliases / 4 temporal units disclosed in report only | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H08 | Native time contract | FRAME_MATCHED_ONLY; private native source PTS authoritative; fps=7/(last-first), seconds/unit=2/fps, do_sample_frames=False | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H09 | Pixel/layout budget | min_pixels=3136, max effective spatial pixels=200704; storyboard 3 columns, 480x270 tile +32 alias row, 1440x906 canvas | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H10 | Generation | Greedy do_sample=False; seed42; max_new_tokens=1024; repeat1; temperature/top_p/top_k inactive | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H11 | Timeouts | load120s, generation max_time300s, supervised request330s; whole pilot6060s from load-start (derived 120+18*330) | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H12 | Hardware gates | Before load free GPU>=10GiB/RAM>=8GiB; generation free GPU>=2GiB; stop global GPU>14.5GiB, owned-tree RSS>20GiB or available RAM<2GiB; 1s nominal polling | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H13 | Failure/retry/continuation | No generation-quality retry or automatic repair; proposed transport pre-generation retry0; continue on strict-invalid JSON if healthy; stop on hardware breach/OOM/process failure/deadline, mark remaining NOT_EXECUTED | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H14 | Time sensitivity and matching | All 0,0.2,0.5s equally reported; greedy one-to-one closed-interval gap=max(0,GT_start-PRED_end,PRED_start-GT_end), require_overlap=False, stable GT then prediction order; TIMING_UNKNOWN unmatched/unresolved | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H15 | Cohort and GT permissions | Three negative units, two nonexhaustive known PICKUP units, one uncertain; test1 W03/W05 deduplicated; exclude test3 W07 | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H16 | Strict-invalid exclusion and qualitative retention | Every raw unchanged; full-strict valid only in structured matching; separate syntax/schema/semantic/citation/full status; invalid not NO_EVENT | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H17 | Physical reasoning assessment | Qualitative manual support review separate from schema/GT matching; unsupported/uncertain/unreviewed remain distinct; no new adjudicated labels here | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H18 | Reporting and metrics | Execution/contract counts, known-event case matching, negative case alerts, uncertain descriptive review, representation descriptions only | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H19 | Run order/budget | 18 deterministic prospective rows; sha256 UTF8 PASS_T_PILOT_ORDER_V1/opaque/representation/NONE/1; one repeat, no extra generations, local API budget USD0 | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H20 | Model-visible information and time disclosure | Neutral supplied aliases, authorized media, exact V1D/V2/schema only; private PTS/GT/eligibility/tracker and review metadata excluded | PROPOSED_AWAITING_HUMAN_APPROVAL |
| H21 | Freeze vs execution approval | Separate explicit freeze-only authorization; later separately authorize exactly18 real calls after technical blockers resolved | PROPOSED_AWAITING_HUMAN_APPROVAL |


尤其：H01明確接受strict1/8風險；H06不加identity clause；H07/C3與H08/FRAME_MATCHED_ONLY接受配對unit限制；H14批准三點全報及closed-interval gap規則並處理T04；H15接受負例品質與nonexhaustive GT限制；H13/H11批准transport0與6060s新上限；H21區分freeze和execute。沒有任何項目因本文件寫了proposed就視為approved。

## 最小後續步驟

1. 人類先審閱本套件、接受或修改H01–H21及技術缺口。
2. 如要解T01/T02/T04，另外授權有界的integration/source工作；本任務不執行也不提出patch，不改prompt/schema/validator/GT，不重啟prompt優化。
3. 更新後candidate及component hashes再次交人類；只有supported freeze gate可用、readiness缺口明示且明確核准才freeze。此候選的授權識別句：`APPROVE_PHASE2B_QWEN_NF4_EXPLORATORY_PROTOCOL 67b59d603e36 FREEZE_ONLY NO_EXECUTION`。任何內容/hash改變需新ID，不可機械沿用。
4. freeze完成仍需新的explicit permission才可啟動18call；本次不存在該permission。不得先改成12call或V1C/AVIfallback以規避review。

不重設Event-to-Graph；先完成Qwen exploratory baseline的現有路徑。當前任務只交付review package，不稱Phase2b完成。
