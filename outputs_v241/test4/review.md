# test4 — post-freeze review

- Evaluation-only scenario: behind basketball; later observed in difficult final region.
- Target initialization: correct; YOLO track 36 at f204 → SAM phone_track36 → phone_01.
- Last trusted phone_01 observation: f384 (12.80s); registry ends UNOBSERVED and retains phone_01.
- SAM initial span f204 to f384: 31 masks, 0 loss events, 0 rejected guard conflicts.
- Late candidates: fixed candidate at f798 is a distinct landline
- Later target evidence: same target appearance seen at f426 and detected again at f1050; neither is compared by frozen late candidate window
- Re-ID: candidate_phone_01 0.530 AMBIGUOUS.
- Failure attribution: **MIXED**. Spatial diagnostic: ANCHOR_CONTEXT_COULD_HELP.
- Exact final physical location is visually reviewable at sampled frame(s).

| Reviewed visible target frame | Raw YOLO target hit | Local target hit |
|---:|---|---|
| 204 | True | True |
| 426 | True | True |
| 1050 | True | True |

Frame samples are sparse manual review, not exhaustive video GT. A landline box at the same frame is not counted as a target hit.
