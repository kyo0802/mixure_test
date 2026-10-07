# V2.9.3 Event Evidence Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Diagnose all 54 unavailable baseline requests, recover bounded event evidence, and exercise the existing VLM and physical gate without changing persistent identity.

**Architecture:** Read and hash-verify frozen V292 upstream artifacts. A new observation authorization layer and deterministic pair sequence selector feed the existing local Qwen model and unchanged relation gate. Only selected dense intervals with missing masks or authorized restart seeds are recomputed; identity, graph and search outputs remain read-only inputs.

**Tech Stack:** Python, pytest, OpenCV, existing YOLO11s/SAM2.1/Qwen2.5-VL, JSON manifests and Markdown reports.

---

### Task 1: Baseline audit
Files: `src/memory_graph/v293/audit.py`, `outputs_v293/evidence_failure_audit.{json,md}`.
- [x] Inspect `_authorize_dense_rows`, `_pair_vlm`, fixed phase selection, event artifacts and RLE counts.
- [x] Classify every request with one primary cause and secondary phase/anchor/mask reasons.
- [x] Run `run_audit()` and inspect all 54 records before implementing eligibility changes.

### Task 2: Observation and pair contracts
Files: `src/memory_graph/v293/evidence.py`, `tests/test_v293_evidence.py`.
- [x] Test authorization independently of identity: assert an authorized observation has no `MATCHED`, alias, merge or appearance-bank write effect.
- [x] Reject drift, conflicting detections, broken segments and noncausal seeds; use existing 0.4 s continuation limit.
- [x] Implement bounded expansion and adaptive BEFORE/DURING/AFTER selection from actual co-visible samples. Require scene/view continuity for AFTER non-observation.
- [x] Test exact queried anchor isolation, order, transition selection, absent AFTER semantics, and global expansion limits.

### Task 3: Frozen replay and selective dense recovery
Files: `src/memory_graph/v293/sources.py`, `scripts/run_v293.py`.
- [x] Validate raw hashes for `test1.mp4` through `test9.mp4` only and baseline model hashes before selective inference.
- [x] Read existing frozen masks from target_full and authorized reinitialized streams. Request new dense inference only where bounded windows intersect trusted source masks and RLE/coverage is missing.
- [x] Persist dense RLE before authorization filtering; record actual interval, seed, raw/config/model hashes and reason for recomputation.
- [x] Preserve anchor labels/confidence/provenance and distinguish event-local tracking from persistent identity.

### Task 4: Grounded VLM and unchanged physical gate
Files: `src/memory_graph/v293/reasoning.py`, `src/memory_graph/v293/runner.py`.
- [x] Render one target and one queried anchor per small sequence with visible frame and phase labels.
- [x] Call existing local Qwen only for eligible packs; preserve raw responses and explicit schema/grounding statuses.
- [x] Reject mismatched IDs, incorrect frame references and contradictions to represented target/anchor visibility.
- [x] Adapt authorized geometry to the existing candidate feature code; filter post-target absence to measured valid views. Call unchanged gate only with grounding-valid facts.
- [x] Test ineligible no-call, synthetic eligible call, wrong grounding rejection and grounded gate dispatch.

### Task 5: Replay, freeze and regression report
Files: `src/memory_graph/v293/report.py`, `outputs_v293/*`.
- [x] Run focused tests and existing V292 contract tests before GPU replay.
- [x] Replay all nine development videos and record funnel counts, primary rejection distribution, relation decisions, representative sheets and first failing stage per video.
- [x] Diagnose zero-call outcomes from actual evidence; fix only general evidence-layer bugs if necessary.
- [x] Freeze prediction hashes, then compare copied/read-only identity authorities and protected policy source hashes; verify test2/test7/test8/test9 conditions.
- [x] Produce report, benchmark, evaluation, regression, contract validation and frozen artifact manifest; reverify upstream and V293 hashes after reporting.

Execution: inline, already authorized by the user. No new validation video discovery, UI, threshold tuning, identity writes, or historical-output writes.
