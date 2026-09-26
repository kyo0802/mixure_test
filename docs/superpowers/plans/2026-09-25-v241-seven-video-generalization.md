# V2.4.1 Seven-Video Generalization Implementation Plan

> **For agentic workers:** Implement inline. V2.4 inference and its parameters remain frozen. The evaluation adapter may change input/output routing only; record any baseline incompatibility.

**Goal:** Run a blind seven-video identity evaluation, freeze predictions, then attribute failures using evaluation-only scenario descriptions.

**Architecture:** Reuse V2.1 perception, V2.2 SAM predictor and guards, V2.3 registry, and V2.4 appearance matcher. Route new-video data through V2.4.1 artifacts without modifying earlier versions. Freeze hashes before reading scenario GT. Evaluate coverage and failure modes separately.

**Tech Stack:** Python 3.12, PyTorch/CUDA, Ultralytics YOLO, SAM 2.1, torchvision MobileNetV3, OpenCV, pytest.

---

### Task 1: Inventory and freeze

**Files:** Create `outputs_v241/frozen_baseline_manifest.json`, `scripts/run_v241_blind.py`.

- [x] Record video metadata and frozen code/config/checkpoint hashes.
- [x] Verify the seven videos have no preexisting GT-derived inference artifacts.
- [x] Write the frozen manifest before processing test3–9.

### Task 2: Blind inference

**Files:** Create `src/memory_graph/v241/adapter.py`, `scripts/run_v241_blind.py`, `outputs_v241/test3` through `test9`.

- [x] Run frozen V2.1 perception on all seven videos with the existing model/config.
- [x] Apply a predeclared, GT-free target initialization policy from early detections.
- [x] Run frozen SAM 2.1 propagation, V2.3 fusion, and V2.4 appearance gates where evidence permits.
- [x] Write per-video identity timelines and Re-ID audits; hash all prediction artifacts in `prediction_manifest.json`.

### Task 3: Post-freeze review

**Files:** Create `scripts/evaluate_v241.py`, per-video `review.md`/`timeline.png`, `generalization_summary.json`, `failure_matrix.json`, `V241_GENERALIZATION_REPORT.md`.

- [x] Programmatically verify prediction hashes and GT isolation before reading scenario descriptions.
- [x] Review visible target events at exact video frames, with explicit uncertainty for blind placements.
- [x] Separate detection, local tracking, SAM, fusion, and Re-ID failure attribution.
- [x] Write aggregate counts with denominators and choose one result classification and next step.

### Task 4: Verification

**Files:** Create `tests/test_v241_generalization.py`.

- [x] Add the eleven requested V2.4.1 isolation/safety tests.
- [x] Run all old and new tests; verify V2.4 hashes unchanged.
