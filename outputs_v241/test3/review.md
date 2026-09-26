# test3 — post-freeze review

- Evaluation-only scenario: smartphone placed inside box.
- Target initialization: correct; YOLO track 39 at f216 → SAM phone_track39 → phone_01.
- Last trusted phone_01 observation: f438 (14.60s); registry ends UNOBSERVED and retains phone_01.
- SAM initial span f216 to f396: 31 masks, 0 loss events, 0 rejected guard conflicts.
- Late candidates: fixed candidate at f786 is a distinct landline
- Later target evidence: phone visible in hand at f450, then enters box; final interior not directly visible
- Re-ID: candidate_phone_01 0.466 AMBIGUOUS.
- Failure attribution: **FINAL_STATE_NOT_VISUALLY_VERIFIABLE**. Spatial diagnostic: IDENTITY_OK_FINAL_LOCATION_UNCERTAIN.
- Exact final physical location is not established by frozen inference.

| Reviewed visible target frame | Raw YOLO target hit | Local target hit |
|---:|---|---|
| 216 | True | True |
| 420 | True | True |
| 450 | False | False |

Frame samples are sparse manual review, not exhaustive video GT. A landline box at the same frame is not counted as a target hit.
