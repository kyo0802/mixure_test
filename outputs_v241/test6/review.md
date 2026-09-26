# test6 — post-freeze review

- Evaluation-only scenario: smartphone near microwave beside doll.
- Target initialization: correct; YOLO track 31 at f192 → SAM phone_track31 → phone_01.
- Last trusted phone_01 observation: f384 (12.81s); registry ends UNOBSERVED and retains phone_01.
- SAM initial span f192 to f372: 31 masks, 0 loss events, 0 rejected guard conflicts.
- Late candidates: fixed candidate at f594 is a distinct landline
- Later target evidence: target visible in hand at f630 with no corresponding raw/local YOLO box
- Re-ID: candidate_phone_01 0.425 AMBIGUOUS.
- Failure attribution: **DETECTION_LIMITED**. Spatial diagnostic: ANCHOR_CONTEXT_COULD_HELP.
- Exact final physical location is not established by frozen inference.

| Reviewed visible target frame | Raw YOLO target hit | Local target hit |
|---:|---|---|
| 192 | True | True |
| 384 | True | True |
| 630 | False | False |

Frame samples are sparse manual review, not exhaustive video GT. A landline box at the same frame is not counted as a target hit.
