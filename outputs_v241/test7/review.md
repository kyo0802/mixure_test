# test7 — post-freeze review

- Evaluation-only scenario: smartphone inserted into doll.
- Target initialization: correct; YOLO track 29 at f204 → SAM phone_track29 → phone_01.
- Last trusted phone_01 observation: f390 (13.00s); registry ends UNOBSERVED and retains phone_01.
- SAM initial span f204 to f384: 31 masks, 0 loss events, 0 rejected guard conflicts.
- Late candidates: fixed candidate at f636 is a distinct landline
- Later target evidence: target visible by doll at f720 and f888 in separate local phone tracks, omitted from Re-ID candidate set
- Re-ID: candidate_phone_01 0.295 AMBIGUOUS.
- Failure attribution: **FUSION_LIMITED**. Spatial diagnostic: ANCHOR_CONTEXT_COULD_HELP.
- Exact final physical location is not established by frozen inference.

| Reviewed visible target frame | Raw YOLO target hit | Local target hit |
|---:|---|---|
| 204 | True | True |
| 720 | True | True |
| 888 | True | True |

Frame samples are sparse manual review, not exhaustive video GT. A landline box at the same frame is not counted as a target hit.
