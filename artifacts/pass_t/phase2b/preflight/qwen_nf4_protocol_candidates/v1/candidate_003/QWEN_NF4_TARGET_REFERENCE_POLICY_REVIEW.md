# Target reference provenance and approval boundary

| Private source/item | Existing references | First immutable candidate | Human authorization | Model authority / event citations |
|---|---|---|---|---|
| test8/PT2A_5dbb180e8ff88762 | 3 | R000186 | Frozen human-only viewer | Awaiting explicit protocol approval / NON_CITABLE |
| test1/PT2A_9d15d2a6b56b56d0 | 0 | MISSING_REFERENCE | Frozen human-only viewer | Awaiting explicit protocol approval / NON_CITABLE |
| test2/PT2A_b35d807b28b92101 | 3 | R000078 | Frozen human-only viewer | Awaiting explicit protocol approval / NON_CITABLE |
| test7/PT2A_c58b4df88a2f6801 | 3 | R000186 | Frozen human-only viewer | Awaiting explicit protocol approval / NON_CITABLE |
| test5/PT2A_eb60192e6986cb4f | 2 | R000078 | Frozen human-only viewer | Awaiting explicit protocol approval / NON_CITABLE |
| test5/PT2A_fe0910d66f4c5614 | 2 | R000078 | Frozen human-only viewer | Awaiting explicit protocol approval / NON_CITABLE |

Sources: frozen EVENT_GT_ANNOTATION_POLICY_V2.md §§110–112,191; phase2a_v2/projection.py:_verify_source; immutable visual references. At most three original seed observations (first/binding/last), deduplicated ascending, strictly pre-window. Existing crops have verified source translation and pixels; authority loader rechecks source PTS/hash/pixels. They assist local recognition only, are never event citations, and do not authorize persistent/global identity. Full per-asset paths, hashes, source index/PTS, transform and dimensions: private/reference_review.json.

Five of six windows have historical human references; test1 has none. Human viewing permission does not establish permission for model transmission: policy explicitly leaves model reference use to Phase2b preregistration. Therefore no reference image is copied into model_visible or passed to processor in this task.

Preferred prospective rule: if authorized, earliest verified existing pre-window reference by immutable source index, exactly one per available window, same asset across all representations. No event citation, GT time, quality score or expected result influences selection. Do not substitute an arbitrary in-window/event frame if missing. Available for five only; disclose asymmetry. Historical crops could show past physical context, but cannot support current events or prove cross-gap identity. Neutral localization from original authorized observations is an alternative requiring a separately approved mapping/overlay contract; it was not fabricated here.

Options: (A) approve one static reference for five windows and label test1 NONE as a separate localization-limited case; (B) authorize a consistent neutral local-target identification policy for all six in a future bounded task; (C) NONE primary only with explicit acceptance of any-phone/local-target ambiguity; (D) distinct NONE ablation, never pool its outcomes with reference conditions. Recommended B before the main target-centric pilot, or A with separate strata if human approves. No silent cohort removal.
