# V2945 Clean Direct Reasoning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Those subskills are unavailable in this session; execute inline under the user's existing implementation authorization. No additional worktree or git commit: use the explicitly requested SAM checkout and isolated version directories, preserving read-only Git state.

**Goal:** Measure Qwen7B event reasoning on the exact nine frozen V2944 event packs using a short seven-field contract without citation or geometry.

**Architecture:** Read and verify immutable V2944 event/render bytes, build a clean prompt, reuse the successful NF4 loader and generation method with a V2945 cache. A lightweight validator assesses references/enums/internal consistency only; no physical-memory decision or write occurs. Freeze predictions before reading V2944 review labels and before image review; evaluate all events and a label-defined eligible subset separately, and simulate memory after review.

**Tech Stack:** Python, pytest, Transformers/Qwen2.5-VL-7B NF4, Pillow, SHA256/JSON manifests. Revision cc594898137f460bfe9f0759e9844b3ce807cfb5, BF16 compute, SDPA, greedy, unchanged 800px input stack, 1400-token/120-second maximum.

## File responsibilities

All paths below are relative to `C:/Users/smile/Desktop/test2/mixure_test_SAM`.

- `src/memory_graph/v2945/common.py`: guarded isolated writes, frozen upstream integrity snapshot.
- `src/memory_graph/v2945/contract.py`: exact enums/seven keys, short example-free prompt, strict JSON parser reuse.
- `src/memory_graph/v2945/validator.py`: `V2945DirectReasoningValidator.validate(event, answer)`; schema/reference/obvious contradiction only.
- `src/memory_graph/v2945/pipeline.py`: exact frozen inputs, one canonical request per pack, raw traces/zero-write audit.
- `src/memory_graph/v2945/model.py`: NF4 constructor/cache isolated; inherit unchanged frozen generate/preprocess/monitor.
- `src/memory_graph/v2945/freeze.py`: verify outputs and policy hashes, primary/review manifests, JUnit audit.
- `src/memory_graph/v2945/evaluation.py`: review-only eligibility, correctness counters, simulated memory, comparisons.
- `src/memory_graph/v2945/reports.py`: 13-section Traditional Chinese progress report and technical report, full-sized review sheets.
- `scripts/run_v2945.py`: prepare/run/freeze/verify entry point.
- `tests/test_v2945_reasoning.py`: focused input/schema/prompt/reference/safety/evaluation tests.

### Task 1: Write failing tests and the minimal output contract

- [x] Write focused tests first and run expecting a missing V2945 module.

```python
def test_minimal_answer():
    e = {'pack_id': 'unit', 'markers': {'A': 'frozen-anchor'}}
    a = dict(event_type='CARRIED_OR_HELD', interaction_anchor='NONE', released='NO',
             target_visible_after='YES', final_relation='NONE', final_relation_anchor='NONE', confidence='HIGH')
    assert V2945DirectReasoningValidator().validate(e, a)['valid']
```

- [x] Define the exact allowed sets:

```python
EVENT_TYPES = {'STATIC','PICKED_UP','CARRIED_OR_HELD','PLACED_OR_PUT_DOWN','BECAME_OCCLUDED','REAPPEARED','NO_CLEAR_INTERACTION','UNCERTAIN'}
RELATIONS = {'ON','INSIDE','BEHIND','OCCLUDED_BY','NEAR','HELD_BY','NONE','UNCERTAIN'}
KEYS = {'event_type','interaction_anchor','released','target_visible_after','final_relation','final_relation_anchor','confidence'}
```

- [x] Implement the short prompt using task/identity/supplied markers/enums/exact keys/conservative rules only. Prompt carries phase labels in chronological order, no event/video IDs, numbers, sample JSON values, semantic classes, frame metadata or historical answers.
- [x] Implement lightweight schema validator: dictionary with exactly seven string fields, known enums, dynamic marker/NONE/UNCERTAIN references; NONE relation requires NONE anchor, UNCERTAIN requires NONE/UNCERTAIN anchor; real relation requires real marker. Flag placement+releaseNO, static+releaseYES, heldBy+releaseYES/incompatible event or mismatched actor. No support citations, region features, confidence promotion or upstream visibility gate.
- [x] Run focused tests. Accept NONE for unprovided actors and UNCERTAIN, including self-consistent low-confidence results.

### Task 2: Freeze and verify the input, then infer once

- [x] Verify V2944 primary/review manifests and upstream historical protections; record before snapshot. Read only frozen event_pack_manifest/render_manifest plus checkpoint/input SHA metadata; do not enumerate raw/new videos.

```python
events = read(ROOT/'outputs_v2944/event_packs/event_pack_manifest.json')
rendering = read(ROOT/'outputs_v2944/event_rendering/render_manifest.json')
assert len(events) == 9
for image in rendering['renders']:
    assert sha256(image['path']) == image['sha256']
```

- [x] Copy the event manifest JSON content without alteration; reuse exact 46 rendered paths/bytes and 36 source-frame byte hashes. Original evidence images/masks/source packs must match V2944 frozen values. Record phase/anchor/target/source-pair invariance and no new decode.
- [x] Save requests and policy source hashes before inference. Instantiate official NF4-only backend using an isolated cache. Keep Backend.__call__, identity and LocalBackend._generate unchanged. Do not load evaluation modules/review labels.
- [x] Write an execution-start marker before first request; refuse second run after that marker or any raw response. One fresh call per event, no quality retries or baseline reruns. Write each raw response and trace incrementally, validate minimal JSON, and record graph/identity/MATCHED writes=0 by design. Capture per-event tokens/runtime/EOS/global GPU/allocator/RSS plus loading metrics.

### Task 3: Test, freeze and then evaluate

- [x] Run V2945/V2944/V2943/V2942/V2941/V294grounding/coverage/V293/V292 focused tests and full suite; JUnit/cache/basetemp stay in V2945. Require only the same three historical V241/V25 hash failures.
- [x] Recompute prompts/input/source hashes and lightweight validator outputs; compare protected before/after; freeze primary numerical artifacts and code. No manual event interpretation yet.
- [x] Load V2944 post-freeze review ONLY in evaluation after verifying primary freeze. Assign eligibility before comparing new answers: target/window sufficiency, supplied interaction anchor or legitimate NONE/UNCERTAIN. Missing hand alone is not automatically ineligible. Record ambiguity/coverage separately; don't retrofit eligibility based on model success.
- [x] Review every exact temporal image sequence after freeze, record admissible event/anchor/release/visibility/relation labels, SUPPORTED/WEAKLY_SUPPORTED/INSUFFICIENT/INCORRECT, and model/upstream failures separately. Independent-human GT is unavailable: explicitly label execution-agent engineering visual review.
- [x] Summarize each of the six reasoning fields for ALL and ELIGIBLE, with correctness/incorrect/indeterminate counts and actual denominators; schema/validator validity separately. Report correct supplied anchor/NONE/UNCERTAIN, wrong/forced anchor, event/relation collapse, unsafe overclaim, uncertainty, correct/false relation classes. Never count indeterminate as correct.
- [x] Simulate P/C/U/R only after review: invalid or reviewed false relation R, insufficient U, strongly supported valid real relation P, weak meaningful search context C. NONE/UNCERTAIN no physical truth. Require no reviewed false assertion in a safe-searchable interpretation. No actual graph writes even for simulated P. Compare V2943 safe memory1 and frozen V2944 safe memory0 at task level.

### Task 4: Reports and final integrity

- [x] Generate complete review PNG canvas `1600 × (80 + 600*ceil(n/2))` from unchanged 800×600 inputs, with per-event MD raw reply/validator/review details. No truncation of odd final rows.
- [x] Write required reasoning/evaluation/comparison/regression/final JSONs, 13 owner-report headings and detailed Traditional Chinese technical report with architecture/source hashes/schema/eligibility/failures/compute/limits. Choose one result/operational/validation/next-task status based on reviewed eligible subset, not overall alone.
- [x] Seal review/report outputs in separate additive hash manifest; verify both layers and protected sources again. Update this checklist with actual outcomes; stop without next-task execution/integration/new validation.

## Exact runtime commands

From the SAM folder:

```powershell
& 'C:\Users\smile\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/run_v2945.py prepare
& 'C:\Users\smile\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/run_v2945.py run
& 'C:\Users\smile\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/run_v2945.py freeze
& 'C:\Users\smile\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' scripts/run_v2945.py verify
```

Every entry adds SAM `.venv/Lib/site-packages` and `src` before optional imports. Pytest bootstrap uses the same runtime; `pytest tests --junitxml=outputs_v2945/regression/full_tests.xml -o cache_dir=outputs_v2945/.pytest_cache_full --basetemp=outputs_v2945/.full_tmp`.

## Scope review

All spec sections map to contract/model/evidence/validator/freeze/evaluation/reports above. No changes to YOLO/SAM/Re-ID/.60/.10/IdentityGuard/TargetBinding/event selection/17 proposals/V28 search/main graph/historical versions/sibling/new-validation files. No geometry stage or citation API exists. The old image headers still display frozen frame IDs; their bytes are retained as required, while neither prompt/output nor validator requests or uses citations.

## Completion record

2026-10-01: first test run failed with missingV2945module as planned;31newfocusedtests passed before canonical run.9freshcalls/0retries;schema9valid/lightweightvalidator7valid.5eligible/4upstreaminsufficient fixed independently of results;eligibleevent0/5/anchor1/5/release4/5/visibility1/5/finalrelation3/5/anchor1/5.9NONEfinalrelations;2credibleheldbymissed;simulatedsafe-memory0.255focusedpassed,548fullpassed/3unchangedhistoricalhashfails/1skip.29primaryartifacts and11sources frozen before visual review.9full-sizedsheets reviewed;newvalidationunused. FinalstatusDIRECT_REASONING_FAILS_ON_ELIGIBLE_EVENTS/KEEP_V293_OPERATIONAL/NOT_READY_FOR_NEW_VALIDATION_VIDEOS. NextCOMPARE_DIRECT_REASONING_VLM selected but not executed.
