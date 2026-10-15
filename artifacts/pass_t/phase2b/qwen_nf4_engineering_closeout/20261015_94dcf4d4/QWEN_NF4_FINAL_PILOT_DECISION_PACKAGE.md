# Qwen NF4 Final Pilot Decision Package

PROPOSED_AWAITING_HUMAN_REVIEW; PROTOCOL_NOT_FROZEN.

**當前不建議 freeze：Variant B 2/12 strict pass，REGRESSION_FAIL。** 請先人工決定如何處理10份失敗輸出的 contract問題；任何後續prompt／contract實驗需另行授權。本次不自動開新實驗。Video integration engineering已通過，不會消除這個regression限制。

| Decision | Verified evidence | Proposed setting | Risk / limitation | User approval required |
|---|---|---|---|---|
| Three representations | B 2/12 strict; Video smoke engineering=True | Multi8/Story8/VideoArray8 exploratory | Smoke is not Video regression or real event accuracy | YES |
| Video frame/time | 7synthetic CPU matches, warmup GPU route | FRAME_MATCHED_ONLY;8frames/4units | CFR/temporal quantization; not equal time/tokens/spatial information | YES |
| Video citation | Existing F membership only | Choose C1/C2/C3; suggest report-only C3 | Single F citation does not prove individual attention | YES |
| Target Reference NONE | Synthetic inputs contain no reference | TARGET_REFERENCE_NONE | Does not uniquely establish target identity | YES |
| Target identity ambiguity | Clause NOT_APPROVED_NOT_ENABLED | Keep separate decision | Unknown identity not auto TARGET_NOT_OBSERVABLE; clause not merged | YES |
| Uniform8 | Fixed existing synthetic source membership | GT-independent round ties-to-even, endpoints | Sparse transitions/observability limits | YES |
| Pixel/layout | CPU original pixel parity | cap200704,min3136;story3cols480x270+32,1440x906 | Global storyboard resize loses detail; budgets not equivalent | YES |
| Generation | Actual shared parameters recorded | 1024,greedy,seed42,repeat1 | Seed/greedy not bitwise reproducibility guarantee | YES |
| Timeouts | Supervisor and runtime receipts | load120/gen300/request330 | Samples/deadline checks not continuous instruction-level timeout | YES |
| Event timing | No real GT scoring in this run | native PTS; point/closed interval/uncertain separately;1-to-1;0/.2/.5s all report | Evidence brackets are not event duration; exact matching semantics still need approval | YES |
| Retry | No B retry; authorized smoke allowance bounded | generation0;never output-based retry | Any future infra retry needs defined pre-generation boundary | YES |
| Strict JSON failure | {'EMPTY_TIMING_UNCERTAINTY': 9, 'SCHEMA_MINLENGTH': 6, 'EMPTY_WINDOW_CITATIONS': 1} | Preserve raw; full strict gating unchanged | Syntax/schema alone not full validity; no repair | YES |
| Six DEV eligibility | Read existing metadata policy only; no DEV pixels | 2known nonexhaustive PICKUP,3case negatives,1uncertain;test3excluded | formal_eligible0; no confirmed PLACEMENT; CAUSALITY_UNVERIFIED | YES |
| Interpretation | Synthetic engineering only | Descriptive exploratory pilot; no formal metrics | No precision/recall/F1/accuracy/population hallucination/generalization/significance | YES |
| Final hashes | execution manifest d59da5a0bcf9187842c5037574e588af710134d894fd5b7e088e56d484bfc256 | Pin approved final runtime/task/schema/assets/order separately | V1C approved only for synthetic candidate; final DEV prompt not approved | YES |
| Human protocol freeze submission | REGRESSION_FAIL | Submit decision package after remaining choices | No automatic freeze; no DEV run authorization implied | YES_SEPARATE_FINAL_GATE |

First pilot proposal: six DEV windows × three representations =18 calls, referenceNONE, uniform8,1024greedyseed42repeat1,retry0. **No DEV images or model calls occurred here.** Additional positives in nonexhaustive windows UNEVALUATED; strict-negative case-level alerts only; uncertain descriptive only. No formal metrics.

Next required decisions: final citation option and time interpretation; identity ambiguity clause/NONE policy; budget/layout/generation/timeouts/retry/failure/matching rules; final DEV prompt and component fingerprints; explicit human protocol freeze approval; actual exploratory DEV run remains separate authorization. Synthetic outcome does not automatically pass these gates.
