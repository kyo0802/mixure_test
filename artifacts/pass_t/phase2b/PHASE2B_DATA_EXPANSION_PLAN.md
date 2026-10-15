# Prospective Phase 2b Data Expansion Plan

This plan applies only to a future, prospectively collected benchmark. It does not extend, relabel, or promote the fixed Phase 2a windows.

## Required strata

- Exhaustively reviewed PICKUP positive windows.
- Exhaustively reviewed PLACEMENT positive windows.
- Random or prospectively sampled negative controls.
- Occlusion without a physical transition.
- Target leaving the field of view.
- Short-duration events whose transition timing is still directly observable.
- Multiple-event sequences with every confirmable PICKUP and PLACEMENT annotated.
- Unknown physical-state cases with explicit unobservable intervals.
- Box, pocket, bag, and handover sequences without forcing them into PICKUP or PLACEMENT when the two-event ontology does not support that label.
- Target-identity ambiguity and visually similar distractors.
- Different viewpoints and visibility levels.

## Independence and annotation

- Collect independent recording sessions prospectively and document session IDs at capture time.
- Do not count multiple windows from the same video as independent sessions.
- Do not infer session independence from filenames.
- Use independent human annotators and a predeclared adjudication rule.
- Record full-window assessability, start/middle/end coverage, gaps, target association, event timing, and explicit two-event-list completeness.
- Keep reference images, target binding, and identity authorization provenance separate from event labels.

## Sampling and sample size

- Freeze the sampling frame before looking at model predictions.
- Define inclusion, exclusion, overlap, deduplication, and session-level split rules prospectively.
- Select sample size from a stated precision or power objective after estimating event prevalence with a separate planning sample.
- Reserve a held-out benchmark whose labels and media selection were not used for prompt, threshold, representation, or model choice.
- Report clustered uncertainty at the recording-session level when a session contributes more than one window.

## Promotion requirements

A future window becomes eligible for full-window false-positive, false-negative, precision, recall, or hallucination evaluation only after the frozen policy validates exhaustive confirmed-event annotation or strict `NO_CONFIRMED_EVENT` semantics. Exhaustiveness cannot override identity uncertainty, leakage exclusions, target-association uncertainty, or causality status.

