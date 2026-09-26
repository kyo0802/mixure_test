# test5 — post-freeze review

- Evaluation-only scenario: smartphone beside box; placement itself not captured.
- Target initialization: wrong phone on visual review; YOLO track 13 at f0 → SAM phone_track13 → phone_01.
- Last trusted phone_01 observation: f30 (1.00s); registry ends UNOBSERVED and retains phone_01.
- SAM initial span f0 to f180: 6 masks, 25 loss events, 0 rejected guard conflicts.
- Late candidates: f288 candidate is gray phone; f0 seed is visually different white multi-camera phone
- Later target evidence: target gray phone visible at f288 and f366; exact final placement not filmed
- Re-ID: candidate_phone_01 0.398 AMBIGUOUS.
- Failure attribution: **FUSION_LIMITED**. Spatial diagnostic: IDENTITY_OK_FINAL_LOCATION_UNCERTAIN.
- Exact final physical location is not established by frozen inference.

| Reviewed visible target frame | Raw YOLO target hit | Local target hit |
|---:|---|---|
| 288 | True | True |
| 366 | True | True |

Frame samples are sparse manual review, not exhaustive video GT. A landline box at the same frame is not counted as a target hit.
