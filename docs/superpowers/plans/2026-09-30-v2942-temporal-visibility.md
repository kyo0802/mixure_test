# V2.9.4.2 Region-Assigned Temporal Observation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Evaluate one-request Contract D on the same 11 frozen packs with semantic naming diagnostic only and conservative region/visibility validation.

**Architecture:** V2942 reads A/B/C frozen results and V294 marked temporal images. A standalone validator checks roles, frame citations, upstream visibility authority and impossible marked-region geometry. Only validated observable facts go through the unchanged V293 adapter and V29 gate. Existing identity, evidence selection and V294 routing remain untouched.

**Tech Stack:** Python, pytest, existing Qwen2.5-VL-3B BF16/SDPA/greedy/800px/1400 tokens, Pillow/OpenCV, JSON SHA256 manifests. Execute inline only in the authorized SAM workspace.

### Task 1 — frozen input and visibility audit
- [x] Create `src/memory_graph/v2942/common.py`: guarded output writes, same model with a new V2942 cache, verify V292/V293/V294/V2941 and protected source hashes.
- [x] Create `audit.py`: fixed 11 pack hashes, frozen A/B/C failure matrix, exact image hashes, per-frame T/A authority and mask/bbox overlap references. Unknown/detector-only absence never becomes authoritative invisibility.
- [x] Inspect frozen raw answers and marked review sheets; keep all event IDs, masks, phase/frame selection and authorization unchanged.

### Task 2 — D contract and focused tests
- [x] Add `tests/test_v2942_contract.py`: no identity/semantic/distinct gate, UNKNOWN and phone/remote naming do not independently reject, wrong role/unmarked reference/geometry fails, invalid frame/phase fails, authoritative visibility conflicts fail, detector absence alone stays unknown, synthetic valid facts reach original physical gate, no identity writes and historical routing/safety.
- [x] Create `contract.py`: one structured response with frame-keyed T/A visibility and overlap; temporal facts cite existing frame IDs. Validate schema before facts; split hard rejection reasons from diagnostic semantic warnings. Map valid D states to existing observable fact keys without changing physical thresholds.
- [x] Run focused new tests. Expected: `validate(pack, valid_answer_with_unknown_names)['grounding_valid']` and `not validate(pack, wrong_role_answer)['grounding_valid']`.

### Task 3 — actual controlled inference and review
- [x] Create `pipeline.py` and `scripts/run_v2942.py`: audit → run. All changed prompts require fresh inference, exactly one request per pair; per-request prompt/image SHA, raw/parsed answers, runtime and resolved model provenance retained.
- [x] Generate 11 review sheets containing frame/phase metadata, response, facts, hard/soft validation and status relative A. Independently inspect accepted cases before final selection; save explicit unsafe-acceptance findings rather than hiding them.
- [x] At most two general D development iterations, justified by saved systematic failures. Preserve attempts and do no per-pair tuning.
- [x] Only automatic grounding-valid D results enter unchanged physical gate. Save P/C/U/R for all six relations and historical false HELD_BY diagnostic check.

### Task 4 — tests, freeze and reports
- [x] Run V2942/V2941/V294/V293/V292 focused tests and full suite with separate new basetemp directories inside V2942. Preserve known three historical hash failures.
- [x] Create `finalize.py` and `reports.py`: final numerical comparison, regression, contract validation, all 14 Traditional Chinese owner report sections and technical provenance. Decide better/comparable/worse and readiness from safe recovery of original five plus manual review, not raw count alone.
- [x] Freeze numerical artifacts and V2942 source/test hashes, verify, then generate narrative reports and separate report hashes. Reverify protected baselines and stop.

Commands use bundled Python after `site.addsitedir(ROOT/'.venv/Lib/site-packages')` and `sys.path.insert(0,'src')`; CLI phases `audit`, `run`, `finalize`, `verify`. Only new `src/memory_graph/v2942`, `scripts/run_v2942.py`, `tests/test_v2942_contract.py`, `outputs_v2942` and this plan may be edited. No validation, event-selection repair, SigLIP2, 7B or UI work begins.

## Completion — 2026-09-30 (Asia/Taipei)

Experiment complete; final 1/11 grounding-valid versus V293 5/11. Original valid pairs preserved 1/5; new safe recoveries 0/6. P/C/U/R 0/0/1/2. Initial run plus two bounded general repairs: 33 fresh requests total. Focused 178 passed; full 471 passed / 3 unchanged historical hash failures / 1 skipped. Numerical freeze and two reports verified: 76 artifacts, 9 source/test files. Final classifications: V2942_GROUNDING_PARTIAL and NOT_READY_FOR_NEW_VALIDATION_VIDEOS. Contract D does not replace V293. No additional inference, validation videos, event-selection repair, SigLIP2 or UI work started.
