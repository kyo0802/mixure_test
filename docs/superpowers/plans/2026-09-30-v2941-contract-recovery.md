# V2.9.4.1 Grounding Contract Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Compare frozen A/B with a conservative region-local C using exactly 11 packs and 20 balanced synthetic development controls.

**Architecture:** New V2941 modules read frozen V293/V294 without mutation. Controls isolate question formulation; C independently describes assigned regions, then cites temporal observations. Upstream provenance rejects same-entity pairs; unchanged V294 fact validation and V29 gate protect temporal and physical reasoning.

**Tech Stack:** Python, Pillow/OpenCV, pytest, existing Qwen2.5-VL-3B BF16/SDPA/greedy, JSON SHA256 manifests. Execute inline in the authorized SAM workspace.

### Task 1 — audit and controls
- [x] Create `src/memory_graph/v2941/common.py`: output guard, protected baseline hashes, fixed input access, model wrapper with new cache.
- [x] Create `experiment.py`: verify A/B inputs, prompts, responses and failure matrix; create 10 same-object exact-crop duplicate controls and 10 same-frame distinct-region controls from frozen authorized development crops. Record provenance and limitation (synthetic duplication is easier than temporal Re-ID).
- [x] Reuse exact frozen A/B fixed-pair responses only after hash checks. Controls are fresh diagnostic adaptations, never claimed to be exact baseline reruns.
- [x] Inspect all baseline review sheets using a montage and retain per-pair failures.
- [x] Run frozen B formulation on all controls before implementing C.

### Task 2 — conservative C and unit tests
- [x] Create `contract.py`: independent region-local visible/description/confidence schema; no distinct boolean gate; upstream same-entity/provenance contradictions fail outside the model. Semantic states EXACT_COMPATIBLE/BROADLY_COMPATIBLE/UNKNOWN/INCOMPATIBLE. UNKNOWN stays unresolved instead of silently accepting wrong anchors.
- [x] Add `tests/test_v2941_contract.py` with supplied role, semantic, citation, authorization, unchanged gate/routing and historical safety cases. Expected correct descriptions pass even with diagnostic distinct_objects=NO; same upstream identity fails.
- [x] Use existing frozen isolated B0 references for local descriptions and frozen chronological T/A composites for temporal extraction. Representation variant 1 only initially; never reselect frames.
- [x] Inspect backend coordinate processing and record LOCALIZATION_SANITY_CHECK_NOT_USED if no validated mapping exists.

### Task 3 — controlled inference and physical check
- [x] Run adapted A and C on the same 20 controls; include nonbinding same/distinct diagnostics with explicit uncertainty and no identity authorization.
- [x] Run C on fixed 11; preserve prompts, image hashes, raw answers, schema/grounding failures and model provenance. At most 2 visual variants; no pair-specific tuning.
- [x] Call unchanged `v293.reasoning.evaluate_gate` only for valid C pairs, retaining provenance to V2941 facts. Report all six relations and false HELD_BY rejection.
- [x] Render every control and fixed-pair sheet with descriptions, phase/frame IDs and validator reasons.

### Task 4 — verification, freeze, reports
- [x] Run new tests plus V294/V293/V292 focused suites, then full suite; save JUnit XML. Preserve known historical hash failures.
- [x] Create numeric comparison, safety regression and contract validation JSON; reverify protected V292/V293/V294 artifacts, routing, identity/memory and source hashes.
- [x] Freeze all numerical artifacts and V2941 sources; verify, then generate both Traditional Chinese reports (13 owner sections), separate report hashes and final readiness/model-upgrade decisions.
- [x] Reverify all frozen outputs and stop. No validation, V295, event coverage changes, 7B inference or UI.

Execution entry: `scripts/run_v2941.py audit`, `controls-b`, `controls-ac`, `fixed-c`, `finalize`, `verify`. Bundled Python adds existing `.venv/Lib/site-packages` and `src` to import paths. Example correctness checks: `assert validate_regions(pack, answer_with_distinct_NO)['grounding_valid']`; `assert not validate_regions(same_entity_pack, answer)['grounding_valid']`; `assert verify()['valid']` after freeze. All baseline comparisons and selection decisions must come from saved actual inference, not predicted outcomes.

Completed 2026-09-30: two representation variants, one prompt/representation iteration after initial; final conservative validator additionally rejects competing phone/remote descriptions and observed-AFTER visible=NO. Final C 0/11; V2941_GROUNDING_CONTRACT_FAILED, CONTRACT_C_WORSE_THAN_V293, NOT_READY_FOR_NEW_VALIDATION_VIDEOS. Focused 153 passed, full 446 passed / 3 known historical failures / 1 skip. Freeze verification valid: 139 artifacts, 8 sources, 3 narratives. No validation, 7B, event coverage or UI started.
