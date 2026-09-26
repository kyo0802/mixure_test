# V2.4.1 — Frozen Seven-Video Generalization & Failure Attribution

## 1. Research question

Does the V2.4 identity system safely maintain one physical phone across seven unseen videos, and where does evidence first fail? **The evaluation found multiple upstream failures.** It made no reviewed false match, but also recovered no later target identity. This is a failure-discovery run, not evidence that the pipeline generalizes.

## 2. Frozen V2.4 baseline

The YOLO11s model/config, SAM 2.1 small checkpoint/config and mask diagnostics, V2.3 `EntityRegistry` and identity guard, and V2.4 MobileNetV3 appearance embedding and Re-ID gates were unchanged. Similarity threshold **0.60**, uniqueness margin **0.10**, and trusted prototype rules remained fixed. Qwen was disabled (`events-only`), and SAM3 and Spatial Memory Graph were not introduced. [Frozen manifest](frozen_baseline_manifest.json) records model, config, source, checkpoint, parameter, and video hashes.

**Material portability limit:** V2.2–V2.4 production runners hardcode `task1/task2`, chosen track IDs, frame windows, and the Task2 late frame. Seven new videos cannot pass through those runners literally. A predeclared V2.4.1 input adapter routed frames into the unchanged SAM `run_segment`, applied V2.3 registry operations in their original order, and called V2.4 `decide` unchanged. It selected the earliest repeated local phone track with a confidence ≥0.5 view; SAM propagated for 180 frames at step 6. At the first raw phone frame at least 108 frames after that window, it seeded **all phone boxes in that one frame** and propagated 78 frames. This routing/candidate policy is a new generalization wrapper, **not a validated frozen V2.4 capability**. Its single late window is itself a major limitation exposed by this run.

## 3. Seven-video evaluation design

All `test3.mp4`–`test9.mp4` (about 33–44 seconds, 1280×720, ~30 fps) ran through V2.1 YOLO/local tracking, SAM 2.1, V2.3 fusion, and V2.4 appearance gates where a candidate existed. The 5 fps V2.1 sample grid and V2.2 six-frame propagation step were retained. No inference logic branched on a test number or scenario description. The [per-video timelines](test3/timeline.png) show raw phone boxes and the persistent target state; matching files exist for all seven videos.

## 4. GT isolation

Stage A finished seven blind predictions before any evaluation-only scenario was used. The [prediction manifest](prediction_manifest.json), SHA-256 `0ed8de03e35d6fa869a13f0137532ca6d6eebfc143e0b72606965970280d87a0`, hashes each V2.1 manifest, SAM log, identity timeline, and Re-ID audit. The evaluation script verifies those hashes, unchanged V2.4 components, and inference-code hashes **before** loading its reviewed scenario/sample data. Post-freeze review and spatial diagnostic tags cannot alter predictions. The V2.4 parameter manifest hash also remained unchanged.

## 5. Per-video results

All times below are video frame indices; approximately divide by 30 for seconds. `phone_01` remained in the registry after becoming `UNOBSERVED`; that persistence alone does not mean the later phone was reidentified. Every selected late candidate received `AMBIGUOUS`, so the per-video outcome was `NO_SAFE_MATCH`.

| Video | Initialization / last trusted | Late candidate(s), max cosine | Post-freeze review and earliest meaningful limitation |
|---|---|---|---|
| [test3](test3/review.md) | track39 f216 / f438 | f786 landline .466 | Target seen at f450 but YOLO misses that frame; the phone then goes into a box. Final interior is not visually verified. Conservative no-match is appropriate for the selected landline. |
| [test4](test4/review.md) | track36 f204 / f384 | f798 landline .530 | Target seen on a separate local track at f426 and again at f1050, outside the fixed late candidate window. Local fragmentation and candidate routing block recovery. |
| [test5](test5/review.md) | track13 f0 / f30 | f288 gray phone .398 | **Initialization selected a visually different white phone**, while the later gray target is visible at f288/f366. The .398 score is not evidence that Re-ID rejected the same physical phone. Final placement beside box is unfilmed. |
| [test6](test6/review.md) | track31 f192 / f384 | f594 landline .425 | Target is visible in hand at f630 but has no matching raw/local YOLO phone box. Detection is an upstream blocker; final placement near microwave/doll is not asserted by inference. |
| [test7](test7/review.md) | track29 f204 / f390 | f636 landline .295 | Target detected by later tracks at f720 and f888 near the doll, but neither entered the fixed Re-ID candidate set. Candidate generation/fragmentation dominates. Exact inside-doll state remains unverified by inference. |
| [test8](test8/review.md) | track29 f186 / f432 | f624 landline .406 | Target and two phone-like distractors appear later; target local tracks are present at f888/f918, but the matcher only saw the earlier landline. **The intended three-phone Re-ID stress test was not actually exercised**, so its safety is unresolved. |
| [test9](test9/review.md) | track53 f534 / f618 | f822 two landlines .332/.401 | Guard rejected an expanded SAM mask at f606; SAM then lost its mask after f624. Target is visibly held at f810 without a matching YOLO target box. Both landlines were left separate. Detection and continuity evidence are mixed. |

The visual review distinguishes the smartphone from the desk's cordless/landline handsets; a YOLO `cell phone` label on a handset is not physical identity. Test5's incorrect seed makes its case unsuitable for a same-identity appearance score. Scenario descriptions were used only in this post-freeze section.

## 6. Detection and local tracking

Across **20 sparse, manually reviewable target-phone frames**, raw YOLO had a target box on **16/20 (80%)**; local tracking retained **16/16** of those raw target hits. The four reviewed target misses are test3 f450, test6 f630, test8 f810, and test9 f810. A landline box in the same frame did not count as a target hit. This is a purposefully selected sample, not a population detection rate. Test5's earliest repeated-phone seed is a different phone from the gray target: **6/7 target initializations were correct on review**. Local track fragments for the target are visible in test4, test7, and test8.

## 7. SAM continuity and drift

The initial SAM window yielded masks at all 31 sampled frames in test3, test4, test6, test7, and test8. Test5 produced 6 masks then 25 `LOST` events after its wrong-seed phone disappeared; this does not prove a SAM backbone defect. Test9 produced 16 masks then 15 `LOST` events as visibility changed. At test9 f606, the unchanged fusion guard **rejected** one enlarged mask (IoU .223 to a phone box; bbox-area ratio 4.40). There were **0 accepted reviewed drift events** and **1 rejected guard conflict**. The adapter ends initial propagation at its fixed window boundary; `UNOBSERVED` after that boundary must not be counted automatically as SAM tracking failure. SAM masks were present on **9/20** reviewed visible-phone sample frames under these deliberately short windows. Late candidate SAM seeds were separate hypotheses, not same-identity reinitializations.

## 8. Fusion and persistent identity

For the six correctly seeded videos, `phone_01` survived `UNOBSERVED` (**6/6**, or **6/7** videos overall). No reviewed false physical merge into `phone_01` occurred. This is registry persistence, not correct final association. Three reviewed videos (test4, test7, test8) created separate later local target tracks, leaving identity fragmented. Test5's seeded `phone_01` represents the wrong physical phone. The generic candidate wrapper selected the first later raw-phone frame, which often fell on desk handsets rather than the later target. This is the dominant observed candidate-admission problem.

## 9. Long-gap Re-ID

There were **8 attempts: 0 MATCH, 8 AMBIGUOUS, 0 NEW_ENTITY, 0 REJECT**. All selected similarities (.295–.530) were below frozen 0.60. Thus the matcher did not force a highest-score match; **0 false Re-ID matches / 0 matches** and **0 reviewed false merges** were observed. Seven selected candidates were reviewed as distinct desk handsets; test5's candidate is the gray target but its query was a different white phone. Five correctly initialized videos had later visible target evidence needing association (test4, test6, test7, test8, test9), yet none reached a safe match because detection and/or candidate generation had already dropped that evidence. The eight ambiguous outcomes do **not** validate long-gap Re-ID on the intended target candidates.

## 10. Same-class distractor stress test

Test8 contains the target smartphone near two desk phones. Frozen YOLO produced later target tracks and desk-phone tracks, but the adapter's single late candidate frame f624 included only one desk handset. The matcher never compared the later three-phone group concurrently. It made no false merge, but **the critical distractor discrimination question remains unmeasured**. This is recorded as insufficient Re-ID evidence in the [failure matrix](failure_matrix.json), not a pass.

## 11. Blind and unobserved final states

Test3's box interior, test5's unfilmed final placement, test6's exact microwave/doll placement, test7's inside-doll state, and test9's exact HomePad/bottle final relation were not established by blind inference. The pipeline can state its last trusted frame and `UNOBSERVED`, but it must not assert the scenario's final location. Test4 and test8 contain later reviewable target evidence; the pipeline nevertheless did not safely reconnect identity. `FINAL_STATE_NOT_VISUALLY_VERIFIABLE` is used where the placement action/location itself cannot be verified from available visual evidence.

## 12. Failure matrix

Full machine-readable matrix: [failure_matrix.json](failure_matrix.json). `PASS` for a rejected false merge means no reviewed error in this small sample; `INSUFFICIENT_EVIDENCE` marks a gate that was not fairly exercised.

| Layer | test3 | test4 | test5 | test6 | test7 | test8 | test9 |
|---|---|---|---|---|---|---|---|
| Detection | FAIL | PASS | PASS | FAIL | PASS | FAIL | FAIL |
| Local tracking / initialization | PASS | FAIL | FAIL | PASS | FAIL | FAIL | PASS |
| SAM continuity | not measurable | not measurable | not measurable | not measurable | not measurable | not measurable | insufficient evidence |
| SAM drift guard | PASS | PASS | PASS | PASS | PASS | PASS | PASS (one rejected conflict) |
| Fusion / candidate admission | PASS | FAIL | FAIL | not measurable after target detection miss | FAIL | FAIL | not measurable after target detection miss |
| Re-ID on intended target | not applicable | insufficient | invalid query | insufficient | insufficient | insufficient | insufficient |
| Reviewed false merge | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

The machine-readable matrix uses its allowed controlled vocabulary and includes identity survival, final visibility, and spatial-memory rows. The table here adds the explanatory distinction between an untested matcher and an invalid query.

## 13. Spatial-memory diagnostic

Useful last observed image-plane context exists in some videos, but no world-fixed anchor relation or exact placement is inferred. Test3/test5 show identity or location uncertainty around a container/box; test6/test7/test8 could benefit from future anchor-relative context; test9 camera motion loses the relation between early phone observations and later objects. These are **post-freeze diagnostic tags**, not inference features. Spatial Memory Graph may eventually help, but it cannot repair the current wrong seed, missed target detections, or unsubmitted Re-ID candidates.

## 14. Limitations

Only seven intentionally designed videos were used; the environment/layout and perhaps the target phone recur. Manual visual review sampled 20 visible frames and is not exhaustive frame-level GT. The generic adapter is a fixed extension of task-specific runners, not a validated production candidate generator. Initial and late SAM windows are sparse and truncated; no full-video SAM continuity claim follows. Some phone/distractor physical identities rely on visual appearance across sampled frames. Zero false merges with zero matches does not establish a false-merge rate. V2.4 parameters were deliberately not optimized on test3–9. Identity persistence does not imply successful location reasoning.

## 15. Generalization result classification

**`IDENTITY_PIPELINE_HAS_MULTIPLE_UPSTREAM_FAILURES`**. The frozen gates were conservative, but reviewed evidence exposes target initialization, detection, local fragmentation, and especially late candidate admission failures before safe Re-ID can be evaluated. The seven-video result does not support the prior single-case recommendation to proceed directly to spatial memory.

## 16. Next architecture decision

**`IMPROVE_FUSION_FIRST`**. In a future version, define GT-free target initialization and continuously admit all later phone hypotheses to the existing registry/Re-ID gate, instead of one fixed late frame. Validate that candidate stream and identity provenance before changing the SAM backbone or building spatial memory. This V2.4.1 run itself made **no algorithm or threshold changes**. A SAM2.1-versus-SAM3 ablation is not yet justified as the dominant intervention: most initial SAM windows remained coherent, and the critical misses often happened before candidate comparison.

## Verification

The eleven new isolation/safety tests passed. [Generalization summary](generalization_summary.json) records counts and denominators. All V2.4 baseline hashes and all seven prediction hashes were checked after review; prior-version outputs remained unchanged.
