# Phase 7 Implementation Plan

Goal: one MP4 command -> fresh YOLO/ByteTrack, Nemotron video array, bounded Phase 6 localization -> isolated existing TemporalMemory -> persistent search.

Architecture: CPU session orchestration with subprocess model stages, existing adapters and Graph semantics. Native PyAV frame timestamps; deterministic disjoint 12-second windows, up to eight source frames each. CV at native-time 5 Hz plus VLM frames. At most six reason-selected localization frames by default. No historical model output/GT imports. Query-only mode never invokes model workers.

Tech stack: existing Windows Python/CV/NF4/SAM, WSL Ubuntu vLLM 0.31.0 Nemotron NVFP4-QAD. No dependency installation or commit/push. Implement directly in current repository, no modifying agents.

- [x] Add integration/fresh_video.py: ingestion, timing/sample contracts, query normalization, sessions, failure receipts, memory assembly and evidence.
- [x] Add integration/fresh_workers.py: reuse Detector/ObjectTracker and Phase 6 runtime in isolated workers.
- [x] Add integration/nemotron_video.py: parameterized existing supported video-array transport; preserve historical benchmark script.
- [x] Add scripts/run_findmind_video.py and internal Nemotron worker entrypoint.
- [x] Focused tests: VFR/time windows, tracker not identity, partial stage survival, invalid output not no-event, session integrity and model-free reload.
- [x] Execute one original development MP4 with fresh inference; inspect evidence and query in a new process.
- [x] Report actual stage times/results/failures and remaining limitations to LATEST_REPORT.md; preserve historical results.

Complete: test8 fresh inference, 723.39 seconds, 3 phone candidate relationships, 0 verified locations; 71 focused CPU tests pass. No claim of unseen-data generalization.
