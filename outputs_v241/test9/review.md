# test9 — post-freeze review

- Evaluation-only scenario: early basketball occlusion; later between HomePad and alcohol bottle.
- Target initialization: correct; YOLO track 53 at f534 → SAM phone_track53 → phone_01.
- Last trusted phone_01 observation: f618 (20.60s); registry ends UNOBSERVED and retains phone_01.
- SAM initial span f534 to f714: 16 masks, 15 loss events, 1 rejected guard conflicts.
- Late candidates: two fixed candidates at f822 are distinct landline handsets, both left ambiguous
- Later target evidence: target visibly held at f810 but no matching raw/local phone box; SAM lost after f624 and f606 expansion was rejected
- Re-ID: candidate_phone_01 0.332 AMBIGUOUS; candidate_phone_02 0.401 AMBIGUOUS.
- Failure attribution: **MIXED**. Spatial diagnostic: CAMERA_MOTION_SPATIAL_CONTEXT_LOST.
- Exact final physical location is not established by frozen inference.

| Reviewed visible target frame | Raw YOLO target hit | Local target hit |
|---:|---|---|
| 534 | True | True |
| 810 | False | False |

Frame samples are sparse manual review, not exhaustive video GT. A landline box at the same frame is not counted as a target hit.
