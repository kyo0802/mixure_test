# Full Held-Out Validation Implementation Plan

**Goal:** Execute frozen dense-image FindMind on all eleven raw validation videos and evaluate only after immutable prediction freeze.
**Architecture:** Add isolated validation IO adapters; call unchanged perception, binding, SAM, fusion, appearance, authorization, dense evidence, adaptive windows and Qwen modules. Preserve original source/artifact hashes. TXT content is inaccessible before the prediction marker.
**Tech Stack:** Python, PyTorch, SAM2.1, YOLO11s, MobileNetV3, Qwen2.5-VL-7B NF4, OpenCV.

## Tasks
- [x] Register exact eleven MP4/TXT pairs using byte hashes and video metadata only; check development collision and prior manifests.
- [x] Add `scripts/run_held_out_validation.py` and `src/memory_graph/validation/` IO runner. Route legacy raw paths, outputs, and caches to the validation run. Preserve all algorithms and log routing differences.
- [x] Run fresh technical pilots val_1 and val_2. Validate artifacts and runtime, without reading TXT or judging semantic performance. Restart pilots after substantive integration repairs.
- [x] Freeze all executable Python/config/model identities. Run eleven videos in isolated fresh directories; no development cache reuse. Save stage timing and failures.
- [x] Freeze machine artifacts and create PREDICTION_FREEZE_COMPLETE.txt, verifying hashes before allowing TXT access.
- [x] Preserve verbatim TXT, review video evidence, create structured GT and per-pack/episode evaluation including indeterminate labels.
- [x] Report stage results, release/identity safety, safe search outcomes, runtime, eleven cases and one final validation status. Freeze report artifacts; implement no follow-up development.

## Verification
Use original final manifest SHA256 checks, synthetic IO-boundary tests, fresh pilot artifact checks, pre-run source hashes checked per video and at prediction freeze. Any genuine post-GT defect remains documented without repair/rerun. Review-dependent memory simulation runs after freeze; pre-freeze output records unreviewed proposals without presenting them as trusted memory.

## Completion
11/11 fresh formal runs complete; 10,872 machine artifacts verified unchanged after GT review. All 39 selected physical packs and eleven overviews reviewed. Sixteen-section report, case report, release table, structured metrics and final manifests delivered. Result: VALIDATION_UNSAFE. No post-GT inference repair or rerun.
