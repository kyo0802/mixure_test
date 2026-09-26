# V2.2 SAM 2.1 smartphone tracking A/B

## 1. Experimental question

Does SAM 2.1 video mask propagation improve local smartphone continuity over the V2.1 tracker after the same YOLO initialization?

## 2. Experimental control

Both branches use `test1.mp4`/`test2.mp4` and the same frozen V2.1 YOLO evidence. Branch A is the validated V2.1 local tracks; Branch B is official SAM 2.1 box-prompted propagation. The V2.1 manifest hashes of detections, track timelines, and video metadata were verified before inference and evaluation. GT was read only by the separate evaluator. Resolver, events, Qwen VLM, graphs, and memory were not rerun or changed. Baseline HEAD before changes: `bf23daaefb459cfc64eab98dbef6cccc5e1aaa42`; the copied worktree already held uncommitted V2.1 files. The original `mixure_test` folder was not accessed or modified.

## 3. SAM configuration

Official Meta `facebookresearch/sam2` commit `2b90b9f5ceec907a1c18123530e92e794ad901a4`; checkpoint `sam2.1_hiera_small.pt` SHA-256 `6d1aa6f30de5c92224f8172114de081d104bbd23dd9dc5c58996f0cad5dc4d38`; config `configs/sam2.1/sam2.1_hiera_s.yaml`. Python 3.12.8, PyTorch 2.10.0+cu128, CUDA 12.8, RTX 5070 Ti, BF16 autocast, official `SAM2VideoPredictor`, no postprocessing, six original frames per sampled step. Missing Hydra/Iopath packages were installed in `.sam2_deps`, leaving the V2.1 `.venv` unchanged. No VLM calls.

## 4. Task1 smartphone

| Reviewed metric | A tracker | B SAM |
|---|---:|---:|
| Visible local coverage | 3/8 (37.5%) | 8/8 (100%) |
| Raw YOLO to local retention | 3/6 (50%) | 6/6 (100%) |
| Reviewed local fragments | 1 | 1 |

SAM stayed on the phone across frames 360, 372, 384, 396, and 408 after A ended at 348. The mask disappeared at frame 420, which GT marks occluded. No confirmed identity drift or reinitialization on the reviewed visible frames. The full-video fragment count, exact ID switches, and purity are `NOT_MEASURABLE_FROM_CURRENT_GT`. See [task1 contact sheet](task1/tracking_ab/smartphone_sam_contact_sheet.jpg) and [timeline](task1/tracking_ab/smartphone_ab_timeline.png).

## 5. Task2 smartphone

| Reviewed metric | A tracker | B SAM |
|---|---:|---:|
| Initial window visible coverage (frames 90–312) | 6/9 | 8/9 |
| Late window visible coverage (frames 528–594) | 0/8 | 8/8 candidate-inclusive |
| All visible local coverage | 6/17 (35.3%) | 16/17 (94.1%) candidate-inclusive |
| Raw YOLO to local retention | 6/11 (54.5%) | 10/11 (90.9%) candidate-inclusive |

One SAM object initialized from the frozen YOLO box at frame 78 carried the phone across V2.1's track22 to track43 gap. It followed the phone through frame 306, then drifted onto the hand at frame 312; this is one confirmed false identity continuation. The fixed area/motion diagnostic missed that drift, which manual overlay review found. At frame 528 three frozen cell-phone detections seeded three independent candidate masks. One matched the original phone in all eight late reviewed frames, but the inference system did not link it to the early object. This is **candidate-level coverage**, not continuous identity recovery or a verified reinitialization. Full-video gaps, purity, and exact ID switches remain `NOT_MEASURABLE_FROM_CURRENT_GT`. See [task2 contact sheet](task2/tracking_ab/smartphone_sam_contact_sheet.jpg) and [timeline](task2/tracking_ab/smartphone_ab_timeline.png).

## 6. Failure attribution

- `YOLO_INITIALIZATION_MISS`: none for either initial benchmark window.
- `YOLO_INTERMITTENT_DETECTION_MISS`: two task1 and six task2 visible reviewed samples lacked raw detection.
- `CURRENT_TRACKER_CONTINUATION_FAILURE`: five task1 and eleven task2 visible reviewed samples had no A observation; three task1 and five task2 such samples had raw YOLO evidence.
- `SAM_PROPAGATION_FAILURE`: task1's mask became empty at occluded frame 420; task2 missed the visible phone at frame 312.
- `SAM_MASK_DRIFT`: one confirmed task2 event at frame 312, onto the hand.
- `SAM_REINITIALIZATION_REQUIRED`: late task2 object identity is unresolved; three independent YOLO candidates were tested, with zero verified same-identity reinitializations.
- `ASSOCIATION_FAILURE`: V2.1 resolver did not merge task2 tracks22/43; SAM's early continuous local object bypassed that association on reviewed frames. Resolver was not changed or credited.
- `INSUFFICIENT_EVIDENCE`: sparse GT cannot establish a safe automatic link to late candidate 1 or full-video identity purity.

## 7. Compute cost

SAM propagation processed 31 task1 and 54 task2 sampled frames. Measured propagation loop times were 1.48 s and 3.22 s, respectively; peak allocated GPU memory was about 0.68 GiB per segment. These omit model load, video decoding, JPEG staging, and reporting. **A/B SPEED COMPARISON NOT VALID** because V2.1 timing was not measured under the same conditions.

## 8. Tracking conclusion

`SAM_IMPROVES_COVERAGE_BUT_DRIFTS`. Task1 has a clear reviewed continuation gain. Task2 has early continuity gain and useful late candidate masks, but frame312 demonstrates false continuation and late identity selection remains unresolved. These are selected diagnostic cases, not a population accuracy claim.

## 9. Architecture recommendation

`SAM21_NEEDS_MORE_CONTROLLED_TESTING`. Keep this as an isolated local-observation experiment until a GT-free identity selection and loss rule avoids the confirmed hand drift. Phase 2 was not run because the Phase 1 win is not clean. Preserve the V2.1 resolver, VLM, and graph architecture.

## 10. Remaining uncertainty

GT consists of sparse, non-random reviewed frames. Unreviewed frames can contain additional drift or gaps. Late candidate-inclusive task2 coverage is an upper bound until an inference-time identity selector is verified. Exact full-video ID switches, purity, and statistical superiority cannot be claimed. The test suite reports 70 passed (65 existing plus 5 V2.2).
