# Human Approval Checklist — 67b59d603e36

**全數 PROPOSED／未收到人工核准。** 使用者授權建立此套件，不等於逐項 protocol approval。舊 synthetic deployment.approved=True、環境變數或舊 policy approval 不是 real pilot 授權。

| ID / decision | Proposed value | Evidence | Human approval | Limitation |
| --- | --- | --- | --- | --- |
| H01 Failed-regression risk acceptance | Use immutable V1D for exploratory hypotheses despite strict 1/8; six event-bearing outputs all invalid | `E12`, `E13`, `E14`, `E19` | PROPOSED_AWAITING_HUMAN_APPROVAL | Explicit exception to prior decision package warning; D4 did not turn REGRESSION_FAIL into PASS |
| H02 Model/revision | Existing local Qwen2.5-VL-7B-Instruct NF4 double quantization, BF16, SDPA; revision cc594898137f460bfe9f0759e9844b3ce807cfb5 | `E15`, `E24` | PROPOSED_AWAITING_HUMAN_APPROVAL | Existing asset receipts only; weights not reopened and no model substitution |
| H03 Prompt/system/schema | Exact V1D + unchanged V2 + unchanged Prediction V1/parser/validator; no V1E | `E16`, `E18`, `E22`, `E23` | PROPOSED_AWAITING_HUMAN_APPROVAL | Full 18 real-input serialized hashes not captured or newly built |
| H04 Representation choice | All three representations, 8 source frames each; 18 planned calls, no 12-call fallback | `E10`, `E13`, `E25` | PROPOSED_AWAITING_HUMAN_APPROVAL | Native route not presently real-DEV capable; T01/T02 |
| H05 Sampling | Uniform8 round(i*(N-1)/7), Python ties-to-even, include endpoints; same selection all representations | `E07`, `E08` | PROPOSED_AWAITING_HUMAN_APPROVAL | Can miss brief transitions; no offset/GT-driven frame selection |
| H06 Target reference and ambiguity clause | NONE for all six windows; no new identity-ambiguity clause; existing prompt/outcomes unchanged | `E10`, `E13`, `E16`, `E37` | PROPOSED_AWAITING_HUMAN_APPROVAL | Opaque TARGET_A can remain ambiguous; this protocol does not authorize global identity or an implicit new prompt instruction |
| H07 Citation C3 | Retain supplied per-frame aliases; native 8 aliases / 4 temporal units disclosed in report only | `E10`, `E25` | PROPOSED_AWAITING_HUMAN_APPROVAL | No unit-level validator replacement, invented alias, precision claim or claim model distinguishes both paired frames |
| H08 Native time contract | FRAME_MATCHED_ONLY; private native source PTS authoritative; fps=7/(last-first), seconds/unit=2/fps, do_sample_frames=False | `E25`, `E07`, `E08` | PROPOSED_AWAITING_HUMAN_APPROVAL | Model time is not native PTS faithful; no extra timestamp text/header; actual position_ids not instrumented |
| H09 Pixel/layout budget | min_pixels=3136, max effective spatial pixels=200704; storyboard 3 columns, 480x270 tile +32 alias row, 1440x906 canvas | `E15`, `E24`, `E25`, `E26`, `E07` | PROPOSED_AWAITING_HUMAN_APPROVAL | Equal selected source frames does not imply equal visual token budget or retained detail; real grids must be logged later |
| H10 Generation | Greedy do_sample=False; seed42; max_new_tokens=1024; repeat1; temperature/top_p/top_k inactive | `E15`, `E26` | PROPOSED_AWAITING_HUMAN_APPROVAL | Seed is not cross-platform determinism; no stability study or extra warmup |
| H11 Timeouts | load120s, generation max_time300s, supervised request330s; whole pilot6060s from load-start (derived 120+18*330) | `E05`, `E15`, `E31` | PROPOSED_AWAITING_HUMAN_APPROVAL | 6060s is a new proposed whole-run bound, not the old 8-call synthetic whole3200s; no verified real supervisor yet |
| H12 Hardware gates | Before load free GPU>=10GiB/RAM>=8GiB; generation free GPU>=2GiB; stop global GPU>14.5GiB, owned-tree RSS>20GiB or available RAM<2GiB; 1s nominal polling | `E15`, `E24`, `E31` | PROPOSED_AWAITING_HUMAN_APPROVAL | Historical synthetic enforcement/measurements only; transient peaks can occur between polls; current free resources not probed |
| H13 Failure/retry/continuation | No generation-quality retry or automatic repair; proposed transport pre-generation retry0; continue on strict-invalid JSON if healthy; stop on hardware breach/OOM/process failure/deadline, mark remaining NOT_EXECUTED | `E05`, `E13`, `E29`, `E31` | PROPOSED_AWAITING_HUMAN_APPROVAL | Changes historical proposed transport retry1 to explicit conservative retry0; no calls hidden as warmups or replacements |
| H14 Time sensitivity and matching | All 0,0.2,0.5s equally reported; greedy one-to-one closed-interval gap=max(0,GT_start-PRED_end,PRED_start-GT_end), require_overlap=False, stable GT then prediction order; TIMING_UNKNOWN unmatched/unresolved | `E10`, `E30` | PROPOSED_AWAITING_HUMAN_APPROVAL | 0.2 is not privileged; existing E30 interior-point case disagrees with proposed closed-interval semantics (T04); no matcher repair here; no optimal-cardinality or invented midpoint/duration claims |
| H15 Cohort and GT permissions | Three negative units, two nonexhaustive known PICKUP units, one uncertain; test1 W03/W05 deduplicated; exclude test3 W07 | `E01`, `E02`, `E03`, `E04` | PROPOSED_AWAITING_HUMAN_APPROVAL | No validated PLACEMENT positive; independent negative quality review incomplete; causality/session independence unestablished |
| H16 Strict-invalid exclusion and qualitative retention | Every raw unchanged; full-strict valid only in structured matching; separate syntax/schema/semantic/citation/full status; invalid not NO_EVENT | `E22`, `E23`, `E29`, `E30` | PROPOSED_AWAITING_HUMAN_APPROVAL | Validator early-return must remain; unassessed stages reported NOT_ASSESSED, not false PASS; T03 |
| H17 Physical reasoning assessment | Qualitative manual support review separate from schema/GT matching; unsupported/uncertain/unreviewed remain distinct; no new adjudicated labels here | `E13`, `E19`, `E02` | PROPOSED_AWAITING_HUMAN_APPROVAL | No physical correctness inferred solely from event claim, match or schema validity |
| H18 Reporting and metrics | Execution/contract counts, known-event case matching, negative case alerts, uncertain descriptive review, representation descriptions only | `E01`, `E02`, `E30` | PROPOSED_AWAITING_HUMAN_APPROVAL | No accuracy/precision/recall/F1/FPR/hallucination rate/generalization/statistical superiority |
| H19 Run order/budget | 18 deterministic prospective rows; sha256 UTF8 PASS_T_PILOT_ORDER_V1/opaque/representation/NONE/1; one repeat, no extra generations, local API budget USD0 | `E05`, `E10` | PROPOSED_AWAITING_HUMAN_APPROVAL | Order regenerated for final NONE/native-array labels, not reuse obsolete unresolved-reference order; no measured USD hardware cost |
| H20 Model-visible information and time disclosure | Neutral supplied aliases, authorized media, exact V1D/V2/schema only; private PTS/GT/eligibility/tracker and review metadata excluded | `E16`, `E18`, `E26`, `E37` | PROPOSED_AWAITING_HUMAN_APPROVAL | No new model-visible time map; native time distortions disclosed privately/report-only |
| H21 Freeze vs execution approval | Separate explicit freeze-only authorization; later separately authorize exactly18 real calls after technical blockers resolved | `E28`, `E29`, `E13` | PROPOSED_AWAITING_HUMAN_APPROVAL | This request approves preparation only; flags/env values/old synthetic approvals grant no real-run authorization |


## 逐項歷史 blocker 對照（21/21）

| 歷史項目 | 舊狀態（不改寫） | 此候選的處理/人工狀態 |
| --- | --- | --- |
| 1 collect-all replay | RESOLVED | Historical resolved; keep diagnostic non-gating. H16. |
| 2 Validator hash unchanged | RESOLVED | Preserved in E23, not weakened. H03/H16. |
| 3 known-state taxonomy | RESOLVED | Preserve schema/source; no new taxonomy. H03. |
| 4 prompt candidate approved | UNRESOLVED | H01/H03: propose V1D, not old V1C. PENDING. |
| 5 identity clause approved/rejected | UNRESOLVED | H06: do not add the optional clause. PENDING. |
| 6 fixtures locked before prompt | RESOLVED | Historical completed; no new fixtures. Not a new pilot gate. |
| 7 regression design approved | UNRESOLVED | Historical V1D completed; no new regression authorized. H01 accepts its limitation only if human approves. |
| 8 regression executed/reviewed | UNRESOLVED | Execution completed 8 calls; REGRESSION_FAIL remains. H01 risk acceptance PENDING. |
| 9 CPU preflight performed DEV/synthetic | RESOLVED | Historical metadata/CPU checks recorded; not new real V1D validation. M01. |
| 10 native/model-time mapping for approved use | UNRESOLVED | H08 FRAME_MATCHED_ONLY, native PTS only for authoritative matching. PENDING. |
| 11 runtime model-consumed alias policy/granularity | UNRESOLVED | H07 C3 retain aliases + report-only paired temporal-unit disclosure. PENDING; T01/T02. |
| 12 approved representation budgets | UNRESOLVED | H09 unchanged 200704/min3136/storyboard geometry. PENDING. |
| 13 point/interval/uncertain matching approved | UNRESOLVED | H14 closed-interval gap/no midpoint/unknown unresolved/one-to-one. PENDING; T04 current interior-point discrepancy. |
| 14 timing sensitivity approved | UNRESOLVED | H14 all 0/.2/.5 equally, no selected headline tolerance. PENDING. |
| 15 approved final model-visible prompt hashes | UNRESOLVED | H03 exact task/system/schema pinned; all18 real serialized hashes unavailable. T02/M01. |
| 16 generation settings approved | UNRESOLVED | H10/H11 greedy42/1024/repeat1/timeouts; PENDING. |
| 17 failure/retry approved | UNRESOLVED | H13/H16 no repair/no generation retry/transport0; PENDING. |
| 18 proposed run order fixed | RESOLVED | New final-label order is explicit 18 rows; H19 PENDING, not falsely old order unchanged. |
| 19 source cohort fixed | RESOLVED | E01 confirms same6; H15 PENDING exploratory permission/negative caveats. |
| 20 frame/fixture/sourceasset hashes verified | RESOLVED | Historical hashes retained; source media not rehashed. M01. No new fixture. |
| 21 explicit final protocol human approval | UNRESOLVED | H21 NOT_GRANTED; freeze/run separate. |


## 其他歷史決策是否遺漏

- E06 reference localization/symmetry → H06：NONE一致，不加入額外 reference ablation；沒有證明 target唯一。
- E06 encoded-video V2 parity → E18/E24/E25 的 native synthetic 路徑已用同V2，但 real-native仍 T01/T02。
- E06 max_pixels vs actual resized grids → H09；source有effective cap，real receipts未驗證。
- E06 tolerance justification → H14三點全報，不假稱經正式校準。
- E06 matched-shape capacity → V1D已有synthetic資源紀錄 E33；非real DEV capacity認證，H12/M01。
- E10 holdout/regression alternatives → 現有 regression 已完成；不重開fixtures/warmup/repeats或新推論。
- E13 warnings/time/reference/cohort/science/freeze → H01/H06–H08/H15/H17/H18/H21皆明列。
- Historical transport retry1 → 本候選明確提議0（H13）；whole3200s → pilot6060s新提案（H11），皆未核准。

## 人類下一個明確授權

`APPROVE_PHASE2B_QWEN_NF4_EXPLORATORY_PROTOCOL 67b59d603e36 FREEZE_ONLY NO_EXECUTION`

只限 freeze-only protocol approval；不包含18call執行、source改動或Graph。現在尚有 T01/T02/T04 與 M01/T03 readiness gates，不能由該句自動跨越。若需要修整合，另提明確授權後產生更新套件/新 hashes，再人工確認；本候選未處理技術 blocker，也未設 approved=true。
