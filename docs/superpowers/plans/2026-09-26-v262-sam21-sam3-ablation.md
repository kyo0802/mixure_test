# V2.6.2 SAM 2.1 vs SAM 3 Implementation Plan

> **For agentic workers:** Execute this plan inline in the current session. V2.6 and V2.6.1 are read-only evidence.

**Goal:** Decide whether official SAM 3 can practically replace SAM 2.1 for the frozen FindMind target-phone task.

**Architecture:** Build an isolated SAM 3 runtime and run a matched eight-frame test8 f804 smoke gate. Only a passing gate permits seven-video inference. Freeze predictions before physical-identity review. Record the decision and measured limits in V2.6.2 artifacts.

**Tech Stack:** Python 3.12, PyTorch 2.10 CUDA 12.8, official Meta SAM 3, official SAM 2.1, OpenCV, pytest.

---

### Task 1: Source and access audit

**Files:** Create `outputs_v262/SAM3_TECHNICAL_REVIEW.md`, `outputs_v262/environment_manifest.json`, `outputs_v262/experiment_manifest.json`.

- [ ] Verify official Meta builder, prompt/propagation API and checkpoint selection in `facebookresearch/sam3`.
- [ ] Check authenticated `facebook/sam3/sam3.pt` access and record revision/hash without recording credentials.
- [ ] Verify frozen input hashes from `outputs_v261/experiment_manifest.json`, then copy only metadata into V2.6.2.

### Task 2: Matched Stage A gate

**Files:** Create `src/memory_graph/v262/smoke.py`, `src/memory_graph/v262/sam21_smoke.py`, `outputs_v262/smoke/{sam21,sam3}/`, `outputs_v262/stage_a_feasibility.json`.

- [ ] Set up `.venv_sam3` without changing `.venv` or `.venv_sam31`.
- [ ] Rerun SAM 2.1 on frames 804:846:6 using the frozen V2.6 CONFIRMED_MATCH box.
- [ ] Run official SAM 3 with `sam3.pt`, the same frames, and the same normalized box. Assert checkpoint and builder are SAM 3 rather than SAM 3.1.
- [ ] Measure build, session, prompt, propagation, FPS, memory, mask count, actual attention execution, and errors.
- [ ] Apply the explicit runtime gate and stop before Stage B on failure.

### Task 3: Conditional Stage B

**Files:** Create V2.6.2 adapters and seven `outputs_v262/testN/` review artifacts only if `stage_a_feasibility.json` says PASS.

- [ ] Use frozen V2.6 input events and authorizations; prohibit test7 f636 PROVISIONAL_MATCH reinitialization.
- [ ] Generate SAM 2.1 and SAM 3 predictions before reading physical-target labels; hash and freeze them in `prediction_manifest.json`.
- [ ] Review paired overlays, compute denominator-based safety/continuity metrics, and generate seven video timelines/contact sheets.

### Task 4: Audit, test, and report

**Files:** Create `tests/test_v262_ablation.py`, `outputs_v262/comparison_summary.json`, `outputs_v262/recommendation.json`, `outputs_v262/V262_SAM21_VS_SAM3_REPORT.md`, and `outputs_v262/SAM3_RUNTIME_BLOCKED.md` if the gate fails.

- [ ] Test historical output immutability, checkpoint/revision, matched prompts, guard rules, attention execution, Stage B gate, drift counting, and prediction freeze.
- [ ] Run V2.6.2 tests and verify artifact schemas/hashes.
- [ ] Report only measured results, mark unavailable quality metrics N/A, and choose one required final classification.
