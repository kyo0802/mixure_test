# V2.9 Placement Evidence Recovery Implementation Plan

> For agentic workers: execute this plan in the current task. Keep all source and generated artifacts inside the V2.9 paths. Do not modify historical predictions.

**Goal:** Connect accepted SAM2.1 masks to authorized identity, detect placement transitions, reinspect short source-video windows, and verify physical relation candidates before enriching V2.8 memory.

**Architecture:** `v29` reads frozen V2.6 and V2.8 evidence. The mask adapter joins RLE to the V2.6 fusion audit and identity timeline. Event detection uses only trusted observations. Dense processing is limited to inferred windows. Relation gates consume time ordered evidence and scoped VLM output. V2.8 graph and search modules remain the baseline.

**Tech Stack:** Python, OpenCV, NumPy, PyTorch, SAM2.1, Ultralytics, Transformers/Qwen VLM, pytest.

---

### Task 1: Audit and trusted mask adapter

- [ ] Inspect `outputs_v25_rerun/test*/sam/sam_continuity_log.json`, `outputs_v26/test*/entity_registry.json`, and V2.6 identity decisions; record exact authorization joins.
- [ ] Implement `src/memory_graph/v29/mask_evidence.py` and tests for accepted, drift, provisional, ambiguous, and mismatched masks.
- [ ] Write `outputs_v29/mask_evidence_audit.json` before new inference.

### Task 2: Placement events

- [ ] Implement generic transition detector in `src/memory_graph/v29/placement_events.py` using trusted target, masks, anchor geometry, and loss state.
- [ ] Test approach/overlap/loss and disappearance only controls.
- [ ] Emit `outputs_v29/test*/placement_event_candidates.json` using no narrative labels.

### Task 3: Dense windows

- [ ] Implement targeted frame extraction and frozen YOLO/SAM2.1 processing in `src/memory_graph/v29/dense_reinspection.py`.
- [ ] Keep recovered phone candidates distinct until identity authorization; retain unknown anchors as candidates.
- [ ] Save compact frame references, observations, mask evidence, features, and before/during/after contact sheets only in `outputs_v29/test*/dense_windows/`.
- [ ] Produce test9 evidence-chain JSON and PNG with first failure category.

### Task 4: Candidate verification and memory

- [ ] Build candidate relations from dense temporal evidence, with positive, negative, and missing evidence.
- [ ] Run local Qwen only for eligible candidate windows and cache structured results.
- [ ] Apply relation-specific gates so image overlap, detector miss, uncertain VLM, or identity ambiguity cannot promote a relation.
- [ ] Adapt decisions into V2.8-compatible memory, graphs, and search ranking without changing V2.8 files.

### Task 5: Verification, freeze, report

- [ ] Run V2.9 safety tests and V2.7/V2.8 regressions; verify historical manifests.
- [ ] Hash V2.9 source and prediction artifacts into `outputs_v29/prediction_manifest.json`.
- [ ] Only after freeze, evaluate test3–test9 against narrative, write `evaluation_summary.json` and `V29_REPORT.md`, then stop.
