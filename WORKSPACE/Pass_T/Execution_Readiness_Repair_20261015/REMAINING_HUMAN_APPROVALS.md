# Remaining Human Approvals

**工程可送人工freeze review；21項仍PENDING。** 本次實作授權不等於科學protocol批准，也沒有把舊failed regression改成pass。

| ID | Decision | Proposed value | Human status |
| --- | --- | --- | --- |
| H01 | Failed-regression risk acceptance | Use immutable V1D for exploratory hypotheses despite strict 1/8; six event-bearing outputs all invalid | PENDING |
| H02 | Model/revision | Existing local Qwen2.5-VL-7B-Instruct NF4 double quantization, BF16, SDPA; revision cc594898137f460bfe9f0759e9844b3ce807cfb5 | PENDING |
| H03 | Prompt/system/schema | Exact V1D + unchanged V2 + unchanged Prediction V1/parser/validator; no V1E | PENDING |
| H04 | Representation choice | All three representations, 8 source frames each; 18 planned calls, no 12-call fallback | PENDING |
| H05 | Sampling | Uniform8 round(i*(N-1)/7), Python ties-to-even, include endpoints; same selection all representations | PENDING |
| H06 | Target reference and ambiguity clause | NONE for all six windows; no new identity-ambiguity clause; existing prompt/outcomes unchanged | PENDING |
| H07 | Citation C3 | Retain supplied per-frame aliases; native 8 aliases / 4 temporal units disclosed in report only | PENDING |
| H08 | Native time contract | FRAME_MATCHED_ONLY; private native source PTS authoritative; fps=7/(last-first), seconds/unit=2/fps, do_sample_frames=False | PENDING |
| H09 | Pixel/layout budget | min_pixels=3136, max effective spatial pixels=200704; storyboard 3 columns, 480x270 tile +32 alias row, 1440x906 canvas | PENDING |
| H10 | Generation | Greedy do_sample=False; seed42; max_new_tokens=1024; repeat1; temperature/top_p/top_k inactive | PENDING |
| H11 | Timeouts | load120s, generation max_time300s, supervised request330s; whole pilot6060s from load-start (derived 120+18*330) | PENDING |
| H12 | Hardware gates | Before load free GPU>=10GiB/RAM>=8GiB; generation free GPU>=2GiB; stop global GPU>14.5GiB, owned-tree RSS>20GiB or available RAM<2GiB; 1s nominal polling | PENDING |
| H13 | Failure/retry/continuation | No generation-quality retry or automatic repair; proposed transport pre-generation retry0; continue on strict-invalid JSON if healthy; stop on hardware breach/OOM/process failure/deadline, mark remaining NOT_EXECUTED | PENDING |
| H14 | Time sensitivity and matching | All 0,0.2,0.5s equally reported; greedy one-to-one closed-interval gap=max(0,GT_start-PRED_end,PRED_start-GT_end), require_overlap=False, stable GT then prediction order; TIMING_UNKNOWN unmatched/unresolved | PENDING |
| H15 | Cohort and GT permissions | Three negative units, two nonexhaustive known PICKUP units, one uncertain; test1 W03/W05 deduplicated; exclude test3 W07 | PENDING |
| H16 | Strict-invalid exclusion and qualitative retention | Every raw unchanged; full-strict valid only in structured matching; separate syntax/schema/semantic/citation/full status; invalid not NO_EVENT | PENDING |
| H17 | Physical reasoning assessment | Qualitative manual support review separate from schema/GT matching; unsupported/uncertain/unreviewed remain distinct; no new adjudicated labels here | PENDING |
| H18 | Reporting and metrics | Execution/contract counts, known-event case matching, negative case alerts, uncertain descriptive review, representation descriptions only | PENDING |
| H19 | Run order/budget | 18 deterministic prospective rows; sha256 UTF8 PASS_T_PILOT_ORDER_V1/opaque/representation/NONE/1; one repeat, no extra generations, local API budget USD0 | PENDING |
| H20 | Model-visible information and time disclosure | Neutral supplied aliases, authorized media, exact V1D/V2/schema only; private PTS/GT/eligibility/tracker and review metadata excluded | PENDING |
| H21 | Freeze vs execution approval | Separate explicit freeze-only authorization; later separately authorize exactly18 real calls after technical blockers resolved | PENDING |


上述decision文字保留原review的來源快照，部分risk字句提到當時T01/T02/T04；目前工程解決狀態見BLOCKER_RESOLUTION_MATRIX，不改寫歷史review。新draft另有engineering_resolution和當前component hashes。

## Next explicit freeze-only approval

本次canonical draft SHA：`c799b5d13a7721a02e88d25f9474081b6d5975bb2b6f71a72f61bf1ba7a00f02`。需要人類提供reviewer ID、逐項確認21個decision digests/APPROVED，及下列完整confirmation：

`APPROVE_PHASE2B_V1D_FREEZE c799b5d13a7721a02e88d25f9474081b6d5975bb2b6f71a72f61bf1ba7a00f02 NO_EXECUTION`

[HUMAN_APPROVAL_REQUIREMENTS.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/HUMAN_APPROVAL_REQUIREMENTS.json) 目前全PENDING、未有reviewer、approval_received=false；它不是可執行的已批准回條。新的freeze writer會驗完整draft/source hashes及21項核准；若code/config再改，hash變動必須重新人審。舊review ID `67b59d603e36` 不能代替本新draft授權。

freeze後還要**另外**提供綁實際frozen protocol SHA的執行確認、nonce、到期UTC與恰好18個call IDs，並保留既有外部runtime/real-run環境gate。當前沒有frozen protocol SHA，因此本任務沒有製造execution authorization。

V1D仍strict1/8；6event-bearing全部invalid的已知風險、NONE的target ambiguity、C3/FRAME_MATCHED_ONLY四units、負例品質/非完整GT、三tolerance及定性限制均需人工接受。不得因CPU測試通過就推定這些已批准或real model已驗證。

到此STOP。不freeze、不載入Qwen、不跑18call、不寫Graph、不commit/push、不自動新增工程階段。
