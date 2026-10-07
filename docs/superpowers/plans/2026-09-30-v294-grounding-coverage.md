# V2.9.4 Grounding and Event Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Run a controlled repair of the fixed 11 V293 pairs, then diagnose all 42 missing-BEFORE requests and repair only demonstrated general coverage defects.

**Architecture:** V294 reads immutable V292/V293 predictions. Stage A adds explicit T/A visual references, phase IDs, two structured Qwen3B interactions and deterministic validators before the unchanged physical gate. Stage B measures causal target/event alignment before routing or selectively recovering evidence under unchanged observation authority.

**Tech Stack:** Python, pytest, OpenCV/Pillow, existing local Qwen2.5-VL-3B, canonical YOLO11s/SAM2.1 only if a measured bounded interval needs recovery, JSON SHA256 manifests.

### Task 1: Immutable baseline and Stage A audit
- [x] Create `src/memory_graph/v294/common.py` for guarded writes, baseline validation and fixed-pair loading.
- [x] Create `src/memory_graph/v294/grounding_audit.py`; retain exact pack hashes, original image/prompt hashes, responses and primary/secondary failure reasons for all 11.
- [x] Verify V292 and all 419 V293 frozen files before audit. Inspect all failed contact sheets without opening new validation videos.

### Task 2: Visual and grounding contracts
- [x] Create `visuals.py` with per-frame 800-pixel composite: chronological pair crop and same-frame isolated T/A aids. Solid cyan T with existing mask; dashed orange A. Every image has B0/D0/A0 IDs and original frame.
- [x] Create `grounding.py`: Step 1 validates T/A regions and distinct roles, Step 2 extracts cited observable facts. Preserve raw detector class and compatibility uncertainty.
- [x] Add `tests/test_v294_grounding.py`: swapped region IDs, wrong phase IDs, wrong object descriptions, copied examples, incompatible neighboring objects and visibility contradictions must fail; authorized synthetic pair must pass; inputs remain immutable.
- [x] Run new tests and existing V292/V293 tests with the existing venv packages before inference.

### Task 3: Fixed Stage A experiment
- [x] Create `stage_a.py` and `scripts/run_v294.py`. Render all 11 without altering their selection or authorization. Record model revision, image and prompt hashes, actual call count and raw answers. Newly rendered input always requires new inference.
- [x] Generate sheets for every pair, preserving failed Step 1 and Step 2 outputs. Invoke the unchanged V293 geometry adapter / V29 gate only after both validations.
- [x] Save Stage A comparisons, recovered/regressed pairs, category counts and false-HELD_BY inspection. Complete this before any Stage B audit.

### Task 4: Root causes and justified routing
- [x] Create `coverage.py` only after Stage A completes. For each of 42 requests measure prior trusted/observation-authorized frames, causal gaps, raw detector/SAM evidence, anchor availability and event type.
- [x] Save start/peak/end alignment distributions and event-type analysis before implementing a repair. Separate no trusted origin, long loss, detector-only, missing mask, drift/conflict and event timing causes.
- [x] Add `tests/test_v294_coverage.py` for globally bounded search, no long-gap substitution, lifecycle-only routing, relevant physical events, preserved observation semantics and canonical recomputation provenance.
- [x] Apply a generic routing/realignment only when multiple measured cases support it. Keep all lifecycle events and all original requests traceable. Log zero recomputation if no safe new evidence can be obtained.
- [x] Replay the final evidence/VLM/gate paths; use Stage A responses only when their exact input and contract hashes match. Preserve unavailable reasons and report routed requests separately from raw evidence availability.

### Task 5: Tests, freeze and reports
- [x] Run `tests/test_v294_grounding.py`, `tests/test_v294_coverage.py`, `tests/test_v292_contracts.py`, `tests/test_v293_evidence.py`; then the full tests suite. Use `.runtime/v294-*` and write only V294 test logs. Record the known historical V241/V25 failures without altering their artifacts.
- [x] Create final benchmark, regression, contract and numerical evaluation artifacts. Verify fixed Stage A pairs and all protected source/identity/memory hashes.
- [x] Freeze prediction/evaluation SHA256 hashes, verify them, then write owner progress report with all 13 requested sections and technical report in Traditional Chinese. Decide readiness from final measurements, with one primary next action.
- [x] Reverify V292/V293/V294 hashes and stop. Do not start validation, V295 or UI.

Execution commands use the bundled Python with `site.addsitedir(ROOT/'.venv/Lib/site-packages')`, `sys.path.insert(0,'src')`, and `scripts/run_v294.py` commands `audit-a`, `stage-a`, `audit-b`, `stage-b`, `finalize`, `verify`. Execution is inline in the authorized SAM workspace.

Completed: 2026-09-30. Experiment status: V294_GROUNDING_REGRESSION; readiness: NOT_READY_FOR_NEW_VALIDATION_VIDEOS. Final verification passed for 220 artifacts, 12 sources, and 2 reports. No new validation run started.
