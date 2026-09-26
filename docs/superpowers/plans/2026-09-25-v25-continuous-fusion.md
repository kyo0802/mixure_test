# V2.5 Continuous Identity Fusion Implementation Plan

> **For agentic workers:** Implement inline; do not modify V2.4.1 or earlier artifacts. No subagent delegation is required.

**Goal:** Ensure later phone observations continuously reach candidate hypotheses and frozen Re-ID, with an auditable swappable target binding.

**Architecture:** Reuse hashed V2.4.1 V2.1 detections/tracks. Bind the target online from current/past track evidence, run the unchanged SAM 2.1 predictor across the remaining video, admit all scene phone observations frame by frame, group cautiously with temporal/geometry/coexistence evidence, build trusted multi-frame appearance views, and submit jointly active candidates to unchanged V2.4 `decide`. Freeze outputs before reading reviewed identities.

**Tech Stack:** Python 3.12, CUDA/PyTorch, SAM 2.1, OpenCV, torchvision MobileNetV3, NumPy, pytest.

---

### Task 1: Baseline and binding

**Files:** `outputs_v25/architecture_manifest.json`, `src/memory_graph/v25/binding.py`.

- [ ] Hash frozen models/configs/code/input manifests and record the generic parameters before inference.
- [ ] Implement swappable `TargetBinding` plus deterministic online automatic policy and ambiguous outcome.
- [ ] Write per-video binding audits without reviewed identity labels.

### Task 2: Continuous evidence

**Files:** `src/memory_graph/v25/sam_route.py`, `src/memory_graph/v25/candidates.py`, `src/memory_graph/v25/pipeline.py`.

- [ ] Route bound target through unchanged SAM 2.1 across the remaining sampled video.
- [ ] Admit every later raw/local phone observation into conservative candidate groups; record distinct same-frame coexistence.
- [ ] Keep ambiguous candidates active and select up to four quality-ranked views per group.
- [ ] Reuse frozen MobileNet features and V2.4 Re-ID gates repeatedly with current competitors.
- [ ] On safe MATCH, preserve provenance and authorize/execute same-identity SAM reinitialization when feasible.

### Task 3: Freeze and evaluate

**Files:** `scripts/run_v25.py`, `scripts/freeze_v25_predictions.py`, `scripts/evaluate_v25.py`, `outputs_v25/`.

- [ ] Run test3–test9 without scenario GT; write binding, candidate stream/grouping, Re-ID, registry, timeline, SAM logs.
- [ ] Hash all predictions; verify GT isolation and prior-version hashes.
- [ ] Post-freeze review sparse target samples, test8 phone distractors, failures, and metrics.
- [ ] Write failure matrix, summary, and nineteen-section report.

### Task 4: Tests

**Files:** `tests/test_v25_fusion.py`.

- [ ] Add the eighteen requested focused tests for binding, candidate continuity, grouping, gate safety, GT isolation, and provenance.
- [ ] Run all previous and new tests; verify earlier prediction hashes unchanged.
