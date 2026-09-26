# V2.5 — Generalized Target Binding and Continuous Fusion Report

> **2026-09-25 input-provenance correction:** The test5 result below is **invalid as a test of the updated video**. `test5.mp4` was updated at 01:06:18, after the V2.1 YOLO detection/tracking cache was generated at 00:23:03. V2.5 used those old detections/tracks for binding and candidate admission, but later ran SAM and image crops on the updated video. Exclude test5 from performance totals and conclusions until the updated video receives fresh detection/tracking and a complete new frozen run. The original numbers below remain as an audit of the mixed-input run; for the six input-consistent videos, reviewed later target-box admission was 6/6, correct binding was 6/6, and MATCH outcomes were one true target (test8) and one false distractor (test7).

Date: 2026-09-25. Scope: test3–test9.mp4. All implementation, inference, evaluation, and new outputs were confined to `mixure_test_SAM`; `mixure_test` was not changed.

## 1. Research Question

Can a general phone target binding and continuous scene-phone candidate stream deliver later observations to the unchanged V2.4 Re-ID gate without unsafe physical identity merges?

## 2. Why V2.4.1 Failed to Generalize

V2.4.1 evaluated fixed late candidate windows. Reviewed later target boxes often fell outside those windows, while fixed candidates were landlines. This conflated missing admission with appearance failure. Its frozen prediction manifest remains the comparison baseline.

## 3. Removed Task-Specific Assumptions

`legacy_assumption_audit.md` records earlier task, track, and frame assumptions. V2.5 inference source contains no test3–test9 track IDs or named late candidate frames. All sampled frames are processed, and every raw phone box is considered.

## 4. Generalized Target Binding

`TargetBinding` accepts an observation, tracklet, or box prompt through one interface. The automatic policy binds the first mature local phone track using at least three observations, 0.4 s span, mean confidence at least 0.5, and a 0.1 quality tie margin. It uses no future frames or reviewed labels. All seven videos bound; manual review found 6/7 correct. test5 bound the white phone at frame 12 instead of the intended later gray phone.

## 5. Continuous Candidate Admission

Every sampled raw phone observation is sent to the continuous stream. The seven videos produced 178 candidate hypotheses. At eight sparsely reviewed later target frames where a target detector box exists and the bound entity is unobserved, all eight boxes appeared in the stream (8/8). This is a reviewed-sample admission measure, not full-video recall. Only two of these eight were evaluated by Re-ID before the first MATCH stopped that video's evaluation.

## 6. Multi-frame Candidate Hypotheses

Candidates retain observation histories, source track IDs, up to four confidence-ranked and temporally diverse appearance views, optional SAM support, decision history, and same-frame coexistence. Conservative short-gap geometry grouping does not treat a raw track ID as physical identity. The 178 hypotheses also indicate fragmentation, especially for moving/overlapping landlines.

## 7. YOLO/SAM Evidence Routing

The frozen V2.1 YOLO outputs and original SAM 2.1 model/rules were reused. The target SAM was propagated over the remaining sampled video; candidate SAM was seeded when eligible. The V2.3 SAM guard decides whether target masks can enter trusted registry evidence. A raw target miss can still leave an entity unobserved, and SAM-only observations are not automatically trusted.

## 8. Persistent Entity Fusion

`phone_01` persists through unobserved gaps; candidate hypotheses are separate from physical entities until a safe Re-ID MATCH. Registry, source, frame, candidate, and SAM reinitialization provenance are saved. The test7 MATCH demonstrates that the unchanged gate can still make an unsafe merge when a distractor is the sole eligible competitor.

## 9. Frozen Re-ID Integration

The V2.4 MobileNetV3 weights, preprocessing, cosine gate 0.60, uniqueness margin 0.10, trusted-bank criteria, semantic/temporal checks, and `decide` logic were unchanged. Inference used a V2.5-only embedding cache. Re-ID reevaluated active hypotheses while the target was unobserved; a MATCH triggered actual same-identity SAM reinitialization. Predictions were hashed before reviewed identities were loaded. Architecture manifest SHA-256: `938921c01f3601809e9d876f778bd1301d2c4c682f1cfdc194e4e8171df326e2`; prediction manifest SHA-256: `f86055c99b849fdac78dd15278df5fadefd89ebae8455693c2dd40968868c967`.

## 10. Per-video Results

| Video | Binding | Hypotheses | Re-ID | Reviewed result | Main limitation |
|---|---:|---:|---|---|---|
| test3 | correct | 23 | NO_SAFE_MATCH | No visible final interior target | Final location unverifiable |
| test4 | correct | 22 | NO_SAFE_MATCH | Target track 107 at f1050 admitted and evaluated; similarity 0.335, ambiguous | Appearance/competition |
| test5 | wrong | 22 | MATCH at f30 | Recovered the *wrong initially bound white phone*, not the intended gray phone | Target binding; true target f288/f366 not evaluated after MATCH |
| test6 | correct | 22 | NO_SAFE_MATCH | Visible target at f630 lacked a target YOLO box | Detection/continuity |
| test7 | correct | 27 | MATCH at f636 | **False landline merge**, similarity 0.611; later true target f720/f888 admitted but not evaluated | Identity safety/early stop |
| test8 | correct | 24 | MATCH at f804 | Correct black target phone, similarity 0.681; SAM restarted | Later continuity not established |
| test9 | correct | 38 | NO_SAFE_MATCH | Visible target at f810 lacked a target YOLO box | Detection/continuity |

Each video has `review.md`, `timeline.png`, and frozen machine-readable inference artifacts.

## 11. Test8 Multi-phone Stress Case

The black target reappeared as raw-only `candidate_009` at f804. Eight eligible candidates were compared then; landline competitors scored at most 0.422, giving the target a 0.259 margin and a safe MATCH. At f888 and f918, the target `candidate_014` and two landlines `candidate_018`/`candidate_020` were separately admitted and recorded as mutually coexisting. The exact later three-phone set was **not** jointly scored because Re-ID stopped after the f804 MATCH. `test8/contact_sheet.png` documents candidate IDs and phone appearances. Thus the earlier distractor test succeeded, but full later multi-phone continuity remains unproven.

## 12. Detection Failure Analysis

Reviewed target-visible f630 in test6 and f810 in test9 had no corresponding target YOLO observation. test3 f450 and test8 f810 also had reviewed target raw misses; test8 was recovered from adjacent f804 evidence. These misses are outside candidate admission's denominator and cannot be called Re-ID failures. No detection model or threshold was changed.

## 13. Candidate Admission Analysis

Reviewed later target boxes: 8 admitted / 8 present, across test4 (1), test5 (2), test7 (2), and test8 (3). Re-ID reached 2/8 before the first MATCH. In test5 and test7, early MATCH cut off subsequent true target evidence; in test8, later observations should be handled by post-match continuity rather than a new identity match. The stream has no reviewed target box omission in this sparse audit.

## 14. Re-ID After Correct Admission

The correct target reached Re-ID in test4 at f1050 and test8 at f804. test4 `candidate_018` scored 0.335 and remained AMBIGUOUS while other candidates were present. test8 `candidate_009` scored 0.681 with a 0.259 margin and matched. These two cases do not establish robust appearance generalization. test5's f30 match belongs to the wrongly bound white phone.

## 15. Identity Safety / False Merge Analysis

test7 `candidate_004` at f636 is visually a separate landline. It scored 0.611, just over the frozen 0.60 threshold; no second eligible candidate existed, so the margin was null. The unchanged gate returned MATCH, aliased it to `phone_01`, and executed SAM reinitialization. This is one confirmed false physical merge among three MATCH events. No GT-driven threshold adjustment or retroactive prediction edit was made.

## 16. Regression Results

All 18 requested V2.5 focused tests pass. The full suite has **118 passed, 1 failed**. The failing V2.4.1 regression checks the old `test5.mp4` digest (`51a05f…`) against the current file (`da637b…`). The V2.5 architecture manifest records that same current digest before inference, and V2.5 freeze verification passes. This mismatch predates the V2.5 evaluation in this run; the original bytes are unavailable here, so the old V2.4.1 exact-video reproducibility check cannot be certified. Existing V2.4.1 outputs and code were not modified.

## 17. Remaining Limitations

The first MATCH ends Re-ID evaluation for that video, allowing a false early merge to suppress later true candidates. Executed SAM reinitialization masks are logged but are not subsequently routed through the V2.3 guard and registry, so post-match persistent continuity is unproven. Candidate grouping fragments phone hypotheses under viewpoint motion. Automatic first-mature-track binding selects the wrong physical object in test5. Sparse reviewed frames limit recall claims. No spatial memory graph was built.

## 18. Result Classification

`MULTIPLE_UPSTREAM_FAILURES_REMAIN`. Continuous admission improved and one true long-gap match was demonstrated, but binding, detector evidence, false fusion, and post-match continuity each remain material in different videos.

## 19. Next Architecture Decision

`IMPROVE_FUSION_AGAIN`. The immediate next experiment should prevent a sole weak distractor from causing irreversible identity merge, continue candidate/identity audit after MATCH, and route reinitialized SAM masks through the frozen trust guard. Target binding and detector misses should remain separately tracked. These changes require a newly frozen version and evaluation, rather than altering V2.5 predictions.
