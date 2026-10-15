# VLM input contract draft V0 for Phase 2a V2 — non-binding

This is a Stage A discussion contract, not a preregistration or model-run authorization. No VLM inference or A/B/C result is produced in Phase 2a.

## Frozen GT boundary

The Phase 2a Event GT policy/schema defines only PICKUP and PLACEMENT, direct physical state, independent visibility and four separate outcomes. Event, state and location citations use only authorized in-window native frames. Reference crops are recognition material, never GT citations. Human local target selection is not global identity or verified tracking continuity.

## Decisions reserved for Phase 2b

| Decision | Current value |
|---|---|
| Future A/B/C arm modalities and comparison | TBD; preregister before runs |
| Cropped window frames, neutral target overlays, native video or other permitted visual representation | TBD; explicit authorized asset allowlist required |
| Pre-window reference crops in model input | TBD; must state whether each arm receives them |
| Model/provider/version, execution/transmission authorization | TBD |
| Sampling stride and temporal grid/offset | TBD |
| Frame count and image/video limits | TBD |
| Prompt format, output schema and token/inference parameters | TBD |
| Scoring, abstention handling, matching tolerances and denominators | TBD; no silent mapping to old Pass T v1 taxonomy |

Annotators may have used permitted pre-window references to recognize the local target. A future arm without references is a different information condition; disclose it. Never provide human GT, Phase 1c rationale, prior answers, model outputs, experimental keys, physical GT, aliases, scores, hidden identities or material beyond authorized bounds as model-visible input. Separately define allowed neutral localization metadata rather than inheriting private preflight fields.

## Descriptive sampling-resolvability table

Stage B finalize takes an explicit list of human-supplied positive integer candidate strides in full-rate frame units; none is selected here. For each event and stride, enumerate every phase offset and test intersection with the cited BEFORE and AFTER spans, as defined in policy §9. Report both-role hits for every offset, misses, all-offset result, native durations and short-transition flags. No supplied list means SAMPLING_NOT_REQUESTED, not a hidden default. No confirmed events means NO_CONFIRMED_EVENTS.

The diagnostic does not choose input frames from GT, tune a model, estimate accuracy, guarantee visual evidence throughout a span or certify fair scoring. Phase 2b must decide uniform sampling/input eligibility prospectively, acknowledge aliasing and insufficient evidence, and freeze all parameters before any model run. Current DEV has selected event-expected windows, no sampled negative controls, single-annotator limitations, unresolved recording-session independence and automatic binding causality; no formal benchmark claim is supported.


## V2 event-list completeness and evaluation evidence boundary

Full-window target PICKUP/PLACEMENT FP, FN, precision, recall and hallucination-rate evaluation needs validated EXHAUSTIVE_ATTESTED confirmed-event windows or validated strict NO_CONFIRMED_EVENT windows, plus all inherited DEV eligibility, association, leakage and dependence/stratum gates. Non-exhaustive/unknown confirmed lists are not exhaustive negatives; their supported events may serve separately reported exploratory matching or qualitative analysis. Unknown outcomes have no completeness claim. An attestation does not upgrade Phase1c eligibility, identity, causality or formal eligibility.

This adds no inference authorization, arm/model/sampling settings, scoring rule or hallucination-rate definition. Matching tolerances, metric denominators, zero-denominator handling and model information fairness must still be preregistered in Phase 2b. Human completeness does not guarantee sampled model inputs contain the necessary evidence; preserve the inherited sampling-resolvability diagnostic.

