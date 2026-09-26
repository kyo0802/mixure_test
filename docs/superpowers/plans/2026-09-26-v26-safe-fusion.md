# V2.6 Safe Fusion Implementation Plan

> **For agentic workers:** Execute inline in this task. Preserve all prior outputs and code. Steps use checkboxes for tracking.

**Goal:** Prevent a sole weak phone candidate from permanently merging into `phone_01`, continue candidate audit, and preserve the confirmed test8 match.

**Architecture:** Verify the fresh-input V2.5 rerun and render read-only baseline figures first. Reuse frozen V2.5 candidate, SAM, registry, and appearance inputs from `outputs_v25_rerun`; write only V2.6 decisions and audit artifacts to `outputs_v26`. Apply a single generic authorization layer around the unchanged V2.4 scorer, then freeze blind predictions before adding reviewed labels.

**Tech Stack:** Python 3.12, PyTorch/MobileNetV3, OpenCV, Matplotlib, pytest.

---

### Task 1: Baseline integrity and visualization

**Files:** `scripts/v26_baseline.py`, `scripts/render_v26.py`, `outputs_v26/baseline_manifest.json`, `outputs_v26/baseline_visualization/test3/` through `test9/`.

- [x] Verify `outputs_v25_rerun/prediction_manifest.json`, every current video hash, V2.1 input hash, and frozen YOLO/SAM/MobileNet configuration; write their hashes to a new baseline manifest.
- [x] Render each baseline identity timeline, Re-ID timeline, and contact sheet from the frozen V2.5 outputs. Use frame labels, boxes, candidate IDs, scores, decisions, and admission/evaluation markers.
- [x] Inspect test7 and test8 baseline figures for readable candidate evidence, including unevaluated later target candidates.

### Task 2: Minimal safe authorization and continued audit

**Files:** `src/memory_graph/v26/authorization.py`, `src/memory_graph/v26/pipeline.py`, `scripts/run_v26.py`.

- [x] Test a synthetic single eligible candidate at similarity 0.611 with no second competitor: expected `PROVISIONAL_MATCH`, no alias, no SAM reinit.
- [x] Test a synthetic unique multi-candidate result at 0.681 versus 0.422: expected `CONFIRMED_MATCH` with unchanged 0.60/0.10 gates.
- [x] Reuse V2.5's frozen bank/candidate construction, score every eligible later candidate frame, and continue writing audit events after provisional or confirmed decisions. Preserve candidate identity separately from `phone_01` until confirmation.
- [x] Write per-video Re-ID audit, candidate stream, aliases, SAM authorization/audit, and timeline source data to `outputs_v26/testN/`.

### Task 3: Blind freeze and post-freeze evaluation

**Files:** `scripts/freeze_v26.py`, `scripts/evaluate_v26.py`, `outputs_v26/prediction_manifest.json`, `outputs_v26/v25_vs_v26_summary.json`.

- [x] Hash all inference code and outputs, verify seven input hashes, and freeze before importing reviewed identities.
- [x] Compare V2.5/V2.6 candidate decisions and physical identity labels. Calculate confirmed/provisional matches, reviewed false merges, later candidate audits, and test8 regression.
- [x] Render V2.6 timelines/contact sheets plus presentation figures for test7 and test8, with reviewed labels in post-freeze artifacts only.

### Task 4: Regression and report

**Files:** `tests/test_v26_safe_fusion.py`, `outputs_v26/fusion_summary.json`, `outputs_v26/V26_SAFE_FUSION_REPORT.md`.

- [x] Implement the 13 named behavior, visualization, and GT-isolation tests from the spec.
- [x] Run V2.6 tests and existing regressions; document the preexisting V2.4.1 test5 video-hash mismatch separately.
- [x] Write the required 16 report sections and choose exactly one result classification and next architecture decision.

