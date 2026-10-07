# Identity Authorization Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Eliminate unguarded identity writes while measuring the continuity/recall cost.

**Architecture:** Raw observations enter a single guard, with causal epochs, immutable evidence, opaque one-use capabilities, a reversible ledger, and lineage-aware banks. Final downstream rows are materialized from the final ledger. Historical identity implementations and downstream reasoning bytes remain preserved.

**Tech Stack:** Python 3.12, pytest, existing frozen YOLO/SAM/MobileNet and dense-image Qwen interfaces.

Execution is inline under existing user authorization. The execution subskills are not installed. No worktree relocation is needed: all additions must stay in mixure_test_SAM. Do not commit the unrelated dirty working tree.

## Ordered work

- [x] Inspect the validation reports and trace every persistent identity write. Save audit Markdown/JSON before implementation.
- [x] Verify the prechange source/artifact snapshot and run the existing suite with explicit local PYTHONPATH and a writable temporary directory outside protected outputs.
- [x] Add `tests/test_identity_authorization.py`: post-gap SAM+YOLO overlap cannot bind; provisional cannot commit core; forged, replayed, wrong-scope tokens fail; short continuity works; revocation removes all descendants; complete lineage; synthetic strong evidence can confirm while a single high score cannot.
- [x] Run `.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_identity_authorization.py -q` and record the expected missing-module failure.
- [x] Add `src/memory_graph/identity/contracts.py`: frozen observations and policy, finite input normalization, box overlap, normalized appearance comparison. No validation-specific constants.
- [x] Add `src/memory_graph/identity/guard.py`: causal candidate history, epoch closure before continuity, binding-only initial capabilities, guarded writes, explicit confirmation gate audit, quarantine/negative/core lineage, revocation and final ledger.
- [x] Repeat the identity tests until contract cases pass. Add a test for every concrete defect discovered.
- [x] Add `src/memory_graph/identity/pipeline.py`: normalized evidence replay, new core extraction from causal observations, isolated raw perception adapter, frozen builder/render adapter. Never read legacy alias or trusted-bank status as authority.
- [x] Add `scripts/run_findmind.py`: the single current identity entrypoint; reject historical/protected output directories and overwrites.
- [x] Add `scripts/evaluate_identity_rebuild.py`: development-only calibration first, freeze policy, run development cases, then known validation cases. Save per-video source hashes and before/after authorized counts. Do not infer correctness from an empty alias table.
- [x] Determine confirmation support using historical development similarity evidence. If insufficient independently labeled multi-time data, production confirmation stays provisional; synthetic fixtures test the full confirmation contract separately.
- [x] Run tests before known validation. Verify test2 short continuity, test7/test9 safety, test8 f804 and forward recovery explicitly; disclose losses.
- [x] Replay all 11 known validation videos with policy hash unchanged. Save all candidate/epoch/decision/bank/ledger records. Assert known wrong aliases and contaminated descendants are absent, keeping case identifiers only in evaluation code.
- [x] Exercise frozen Event Window Builder, rendering and unchanged Qwen request/validator interface on the final ledger; do not change physical reasoning logic or claim improved physical accuracy.
- [x] Full pytest, focused suite, historical V293 verification, and preserved file hashes. Separate environment/setup failures from test regressions.
- [x] Write contract/state/bank/revocation docs, migration map, active import manifest and 19-section Traditional Chinese report with explicit readiness decision.

## Invariants used in tests

```python
assert not guard.final_observations_after_revoked_alias()
assert provisional_token is None
assert continuity_capabilities == {"AUTHORIZE_OBSERVATION"}
assert production_policy.automatic_confirmation_enabled is False  # until calibrated
```

These describe assertions to implement against concrete snapshots; they are not an alternate runtime API. Synthetic confirmation fixtures must be labeled synthetic and cannot change the deployed confirmation policy.

## Completion record

Implemented and measured on 2026-10-03. Final runs: outputs/identity_rebuild/development/runs_final and known_validation_regression/runs_final. Production strong confirmation and core promotion deliberately remain disabled pending calibration; these are explicitly reported limitations. CURRENT_PIPELINE.md replaces the planned README edit because README is byte-frozen by the historical reference. Full suite: 389 passed, 1 skipped.
