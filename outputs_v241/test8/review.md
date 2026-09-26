# test8 — post-freeze review

- Evaluation-only scenario: smartphone placed beside two other phones.
- Target initialization: correct; YOLO track 29 at f186 → SAM phone_track29 → phone_01.
- Last trusted phone_01 observation: f432 (14.40s); registry ends UNOBSERVED and retains phone_01.
- SAM initial span f186 to f366: 31 masks, 0 loss events, 0 rejected guard conflicts.
- Late candidates: fixed candidate at f624 is a distinct landline; later target and two landlines coexist
- Later target evidence: target visible in hand at f810 without target YOLO box; later target phone has local tracks f888/f918 but was not scored against distractors
- Re-ID: candidate_phone_01 0.406 AMBIGUOUS.
- Failure attribution: **FUSION_LIMITED**. Spatial diagnostic: ANCHOR_CONTEXT_COULD_HELP.
- Exact final physical location is visually reviewable at sampled frame(s).

| Reviewed visible target frame | Raw YOLO target hit | Local target hit |
|---:|---|---|
| 186 | True | True |
| 810 | False | False |
| 888 | True | True |
| 918 | True | True |

Frame samples are sparse manual review, not exhaustive video GT. A landline box at the same frame is not counted as a target hit.
