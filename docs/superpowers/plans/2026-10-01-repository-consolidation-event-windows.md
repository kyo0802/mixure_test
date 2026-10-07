# Repository Consolidation and Event Windows Implementation Plan

> Execution: inline in this session. The user has authorized implementation and safe deletion. All writes remain in `mixure_test_SAM`.

**Goal:** Retain reproducible V293 and clean Qwen reasoning, remove unused experiments, and evaluate adaptive transition windows on manifested development inputs.

**Architecture:** Keep the frozen identity/perception lineage intact. Consolidate clean Qwen utilities into `memory_graph.reasoning`; add a deterministic builder under the existing `memory_graph.events` package. Audit and freeze artifacts in `outputs/current_development`.

**Tech Stack:** Python 3.12, PyTorch CUDA, Qwen2.5-VL-7B NF4, OpenCV, pytest, native PowerShell deletion.

## A. Dependency audit and safe consolidation

- [x] Inventory source, scripts, tests, models and generated outputs; exclude raw/unknown media and validation paths from traversal.
- [x] Build AST import closure from `memory_graph.v293.runner`, `memory_graph.v292.pipeline`, and the clean Qwen runtime; record literal file/model dependencies and frozen manifest references.
- [x] Preserve all V293 source/output hashes and model dependencies; copy the nine-pack clean Qwen baseline, labels, rendered inputs, model configuration and reports to a compact reference.
- [x] Create independent `reasoning/model.py`, `contract.py`, `validator.py`, using the successful V2945 loader and generation method unchanged.
- [x] Write audit, history, cleanup plan and before manifest. Dry-run `verify_baseline_contract(full_hashes=True)`, `v293.report.verify()`, import smoke and checkpoint existence before deletion.
- [x] Delete only manifest entries with verified workspace containment and no active dependencies; produce after manifest and import smoke.

## B. Deterministic adaptive event windows

- [x] Create `events/window_builder.py`: globally configured seconds-based state timeline, stable PRE/POST search, independent lifecycle/physical budgets, complete-window gate and actor/location roles.
- [x] Add focused tests for timebase, boundary truncation, gaps, identity chain changes, independent queues and no identity mutation.
- [x] Use authorized frozen V292/V293 rows and explicit historical development manifests. Do not decode unknown or held-out media.
- [x] Produce dense ordered images with target marking only on authorized observations and supplied context roles. Freeze config, timelines, boundaries, selections and review sheets before review.

## C. Fresh reasoning and regression

- [x] Create `scripts/run_current_pipeline.py` and `run_development_eval.py` with guarded prepare/run/verify commands; only COMPLETE physical windows may enter Qwen.
- [x] Run the existing Qwen checkpoint/config once on frozen requests; persist raw outputs, parse results, runtime, peak VRAM and deterministic validator metrics. No retries to improve answers.
- [x] Freeze predictions before engineering review; review sheets and record field truth, window eligibility and specified failure causes without modifying predictions.
- [x] Compare the clean Qwen baseline against new windows, stratified by review eligibility; evaluate conservative searchable-memory proposals through unchanged trust policy.
- [x] Classify remaining tests and run import smoke, focused tests and the full active suite; explicitly distinguish removed obsolete tests from repaired failures.

## D. Freeze and reports

- [x] Hash current sources, parameters, model configuration, requests, responses, parsed outputs and metrics; verify all frozen artifacts.
- [x] Write CLEANUP_REPORT, EVENT_WINDOW_BUILDER_REPORT (16 requested sections), CURRENT_PIPELINE_REPORT, and readiness/handoff if executable and safe.
- [x] Deliver the requested eleven-section Traditional Chinese summary, with measured results and one improvement/readiness decision.
