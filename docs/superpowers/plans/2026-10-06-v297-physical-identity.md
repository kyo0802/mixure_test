# V297 Interaction-Conditioned Physical Identity Implementation Plan

**Goal:** Add causal physical and interaction evidence with explicit gates; preserve safe main and V296, review nine development scenarios before policy, freeze before known regression.

**Architecture:** Opt-in V297 package composes unchanged CandidateEpoch, integrity, official DINO/LightGlue and Guard capability sinks. PersonEpoch is short temporal geometry, PhysicalIdentityState stores authorized target history only. Camera translation requires stable-anchor consensus. Physical/interaction providers produce states without identity authority; Guard alone confirms and backfills.

**Tech stack:** Existing Python, OpenCV, NumPy, Pillow, PyTorch and official V295 backbones; no new models. Existing Qwen2.5 NF4 only after safety acceptance. Execute inline under the user's explicit direct-execution instruction; do not dispatch agents or pause for plan approval. No commits that include unrelated dirty history.

## Task 1 — Preserve

- [x] Run `python -X utf8 -B scripts/preflight_v297.py`; require manifest exists and all old sources/results included. Create `codex/V297` branch without resetting changes.
- [x] Write only new source/scripts/tests; all experiment artifacts under `outputs/v297_physical_identity`.

## Task 2 — Scenario GT before decision policy

**Create:** `scripts/build_v297_scenarios.py`; `development_gt/test1_identity_scenario.json` through test9; acceptance Markdown and clean original review sheets.

- [x] Read reviewed DEVELOPMENT positive/negative labels and provenance only. Map explicit observation IDs to visibility runs, known distractor intervals, initial binding, expected target recoveries and unknown intervals. Detector absence is detector absence, not proof of target invisibility.
- [x] Inspect clean source contact sheets for all nine videos. Record review method/hash and UNKNOWN wherever physical identity cannot be established. GT is evaluation-only; never import it in identity inference.
- [x] Store fixed criteria: correct initial target; zero reviewed negative authorizations/Core/aliases; expected recovery where listed; explicitly required unresolved ambiguity preserved. Freeze scenario hashes before tuning.

## Task 3 — Inputs and independent physical observations

**Create:** `src/memory_graph/v297_physical_identity/{io,inputs,person,physical}.py`.

- [x] Reuse V296 original verified crops and DINOv3 caches read-only, verify original video/raw-source/crop/mask hashes. New DINOv2 and LightGlue writes must redirect solely into V297 through bounded runtime adapters.
- [x] Inspect available raw person tracks, anchor tracks, scene/camera metadata and target observations. Record coverage counts per development video before implementing policy. Missing evidence returns UNKNOWN.
- [x] Implement PersonEpoch without appearance: scene/reset/gap/motion breaks, unique short-gap geometry stitch only. API `PersonEpochBuilder.process(time, people, image_size, scene_break=False)` returns person hypotheses and no authority.
- [x] Add failing tests for person gap/recycle, simultaneous conflict, one-frame proximity and pan cancellation; then implement and rerun.

```python
def test_person_epoch_break_drops_interaction():
    state = PhysicalIdentityState('phone_01', PhysicalPolicy())
    assert state.snapshot()['interaction_state'] == 'NO_INTERACTION_CONTEXT'
```

## Task 4 — Physical state and gates

**Create:** `physical.py`, `policy.py`, `guard.py`.

- [x] Maintain last authorized observation/time/bbox/position/scene, raw/compensated velocity, uncertainty, person relation and anchor region. Update target state only from Guard authorized current ledger rows.
- [x] Estimate conservative camera translation from at least three persistent detector-supported static anchors with small residual, reject scale/scene discontinuity. Record raw/compensated vectors and reliability. No optical flow/SLAM/depth.
- [x] Reachability depends on elapsed time, reliable compensation, measured speed envelope, size/scene consistency and candidate lineage; long unsupported gaps return UNKNOWN.
- [x] Person proximity persists multiple frames; motion coupling requires multiple compensated nonzero joint movements with direction and stable relative position. Pure pan is UNKNOWN/NOT_COUPLED.
- [x] Store overlap/disappearance while same PersonEpoch remains as occlusion hypothesis; expires on scene/person break or configured horizon. Reappearance support requires same person, plausible relative position/motion/timing, multiple current frames; no semantic action assertions.
- [x] Record KnownDistinct entity only with simultaneous Guard-authorized target plus separate candidate and persistent spatial separation. Preserve epoch/observation/authorization lineage across short safe stitching; arbitrary raw-ID reuse cannot inherit it. Strong clean visual link to a known negative is veto-only, never positive authority.
- [x] Candidate pre-existence/history supplies explicit contradictions and candidate competition. No weighted scores, no video/frame IDs in policy.

```python
def confirmation_context(visual, physical):
    if physical['known_distinct'] or physical['preexistence_contradiction']:
        return 'REJECTED'
    if physical['reachability'] == 'PHYSICALLY_INCONSISTENT':
        return 'REJECTED'
    if not visual['strong_current_multiframe']:
        return 'PROVISIONAL'
    if physical['interaction'] == 'INTERACTION_CONTINUITY_SUPPORT':
        return 'INTERACTION_CONDITIONED_RECOVERY'
    if physical['reachability'] == 'PHYSICALLY_CONSISTENT' and physical['candidate_continuity_valid']:
        return 'CONTINUITY_RECOVERY'
    return 'AMBIGUOUS'
```

- [x] Guard policy extension uses unchanged `_issue`, `_check`, `write`, `_revoke`, final ledger. Retire V296 appearance-only route; both visual routes need additional V297 physical context. Proximity/reachability/motion/state never issue tokens.
- [x] Reject contradictory continuity before inheritance can authorize it. Same-epoch backfill only from individually valid physical/visual rows, no known-distinct/scene/switch intervals. Preserve future stabilization Core semantics, require physical-safe support before new recovered Core.

## Task 5 — Development calibration and acceptance

**Create:** `calibration.py`, `runner.py`, `scripts/run_v297_identity.py`, `scripts/report_v297.py`, `tests/test_v297_identity.py`.

- [x] Calibrate global normalized proximity/motion/gap/reachability from development only; conservative percentile+buffer, no per-video rules. Keep V296 visual policy frozen/read-only, do not broaden backbone search.
- [x] Execute test1–9 causal evidence replay, inspect every new recovery from original source. Evaluate predefined scenarios and record PASS/FAIL/UNKNOWN; test8 must remain explicit required recovery, never claim 9/9 if it fails.
- [x] Record all 22 required synthetic authority/context/backfill cases, including good interaction plus poor appearance rejected and visually identical known-distinct blocked.
- [x] If the actual footage lacks person/camera/physical evidence, preserve UNKNOWN and report the resulting recovery limit instead of inventing support.

## Task 6 — Freeze and one known regression

- [x] Write `FROZEN_V297_POLICY_MANIFEST.json` and calibration mirror with all inference sources, scenarios, visual/physical/person/motion/interaction/preexistence/bank/backfill configs and model revisions. Verify freeze before and after val1–11.
- [x] Run known val exactly once with fixed policy; no policy repair afterward. Evaluate V296 reviewed original physical distractor intervals and additional new confirmation frames only after run. Save full deterministic WHY explanations and capability/backfill provenance.

## Task 7 — Tests, conditional smoke and report

- [x] Run new, focused and full tests; legacy tests use separate temporary root outside `outputs`, logs live in V297. Preserve failure diagnostics and move completed temporary artifacts into experiment output after tests.
- [x] Only if known safety and development identity acceptance pass, fresh YOLO/SAM→V297→unchanged builder/dense images→Qwen2.5 NF4 smoke. Otherwise save `SKIPPED_IDENTITY_SAFETY_GATE` without loading Qwen.
- [x] Rehash protected files, verify source freeze and artifact coverage. Create 25-section Traditional Chinese report with architecture, per-video scenarios, baseline table, measured runtime/resource limits, failure audit and exact status/readiness. Keep normal safe main unchanged.

All shell commands explicitly use SAM repository workdir, `.venv/Scripts/python.exe -X utf8 -B`, `PYTHONPATH=src`, pytest `-p no:cacheprovider`. No writes to sibling repository or old artifacts.

## Recorded outcome

Implementation and prescribed experiment workflow completed. 37 new /108 focused /525 full tests passed,1 historical seal skip. Development3 PASS,6 FAIL; real test8 recovery not retained, a documented unmet functional goal. Known val5/9/10 reviewed wrong aliases/authorizations/Core0. Qwen skipped by acceptance gate. Experimental only; do not promote.
