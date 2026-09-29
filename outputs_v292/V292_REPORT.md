# V2.9.2 Canonical Pipeline Report

## 1. Canonical pipeline status

- Videos completed from raw input: **9/9**.
- Same canonical configuration verified: **True** (`3a8600b58392e9501b9098c46948c74f0df98f6e4ccc3466b214f62539990761`).
- Canonical consistency and frozen artifact validation: **True**.
- Full-suite legacy hash failures are listed separately below; historical outputs were not changed.

## 2. Contract repairs completed

The runner uses one V2.9.2 raw-video path for all nine inputs. Identity confirmation is sourced only from V2.6 Identity Guard authorizations; propagation and detector resumption remain separate states. Mask artifacts are saved and checked against video, frame, object, event, provenance, authorization and file hash. Event-local anchors use `video::event::local_id`. Dense windows bind their requested interval and model/config signature. VLM requests contain one target, one anchor and one event; observable facts are checked against the pair and cited frames before reaching the existing V2.9 relation gate. Temporal, lifetime and search views are derived from the same event store.

## 3. Nine-video fresh-run summary

| Video | Run | Frames | YOLO | Tracks | Trusted masks | Guard matches | Losses | Anchors P/E | VLM grounded/calls | Physical P/C/U/R | Runtime |
|---|---|---|---|---|---|---|---|---|---|---|---|
| test1 | COMPLETE | 162 | 1125 | 77 | 42 | 0 | 3 | 25/11 | 0/0 | PROMOTED:0,CANDIDATE:0,UNCERTAIN:0,REJECTED:0 | 71.3s |
| test2 | COMPLETE | 155 | 1511 | 96 | 38 | 0 | 3 | 32/4 | 0/0 | PROMOTED:0,CANDIDATE:0,UNCERTAIN:0,REJECTED:0 | 58.7s |
| test3 | COMPLETE | 196 | 1805 | 114 | 23 | 0 | 3 | 34/2 | 0/0 | PROMOTED:0,CANDIDATE:0,UNCERTAIN:0,REJECTED:0 | 65.9s |
| test4 | COMPLETE | 196 | 1677 | 111 | 15 | 0 | 3 | 35/1 | 0/0 | PROMOTED:0,CANDIDATE:0,UNCERTAIN:0,REJECTED:0 | 63.2s |
| test5 | COMPLETE | 187 | 1672 | 103 | 31 | 0 | 3 | 35/1 | 0/0 | PROMOTED:0,CANDIDATE:0,UNCERTAIN:0,REJECTED:0 | 67.1s |
| test6 | COMPLETE | 167 | 1342 | 86 | 32 | 0 | 3 | 29/7 | 0/0 | PROMOTED:0,CANDIDATE:0,UNCERTAIN:0,REJECTED:0 | 56.9s |
| test7 | COMPLETE | 221 | 1791 | 88 | 23 | 0 | 3 | 25/11 | 0/0 | PROMOTED:0,CANDIDATE:0,UNCERTAIN:0,REJECTED:0 | 82.4s |
| test8 | COMPLETE | 185 | 1523 | 81 | 66 | 1 | 2 | 22/14 | 0/0 | PROMOTED:0,CANDIDATE:0,UNCERTAIN:0,REJECTED:0 | 72.9s |
| test9 | COMPLETE | 201 | 1764 | 106 | 3 | 0 | 3 | 35/1 | 0/0 | PROMOTED:0,CANDIDATE:0,UNCERTAIN:0,REJECTED:0 | 66.7s |

## 4. Identity results

- Identity Guard confirmations: **1**.
- Unauthorized `MATCHED` states: **0**.
- `test2` track 22 / 43 fusion review: `{"track22_phone_01": true, "track43_phone_01": true, "track22_mapping": "phone_01", "track43_mapping": "phone_01"}`.
- `test7` provisional-candidate memory contamination: **False**.

## 5. Event / recovery results

Each video records loss episodes separately. `test8` forward recovery loop closed: **True**. `test9` unresolved: **True**; first failing stage: **identity_guard**.

## 6. VLM grounding results

- Pair calls: **0**.
- Grounding-valid calls: **0**.
- Calls with unavailable phase evidence: **54**.

## 7. Physical relation results

Aggregated V2.9 gate decisions: **PROMOTED 0**, **CANDIDATE 0**, **UNCERTAIN 0**, **REJECTED 0**. Relation-specific breakdowns are in each video's `physical/relation_decisions.json`. The gate thresholds were not lowered.

## 8. Memory/search consistency

The automatic validator checked timestamp integrity, relation status, memory provenance round trips, mask references, VLM grounding references and anchor namespaces. Final graph output uses V2.8's capped target-centered local subgraph; broader candidates remain in audit artifacts.

## 9. Per-video failures

- **test1**: none
- **test2**: none
- **test3**: none
- **test4**: none
- **test5**: none
- **test6**: none
- **test7**: none
- **test8**: none
- **test9**: none

## 10. Regression tests

- V2.9.2 focused contracts: **66 passed, 0 failed**.
- Full existing suite: **359 passed, 3 failed, 1 skipped**.
- Historical frozen-artifact failures: `test_v241_generalization::test_prediction_manifest_written_before_evaluation`, `test_v241_generalization::test_spatial_diagnostic_does_not_modify_inference`, `test_v25_rerun::test_prediction_manifest_covers_all_rerun_artifacts`.

## 11. Frozen artifact verification

Prediction freeze precedes evaluation: **True**. Artifact and canonical manifest verification: **True**. Frozen artifacts are listed in `artifact_manifest.json` and `canonical_manifest.json`.

## 12. Remaining bottleneck

Pair-grounded VLM evidence was unavailable because target and anchor did not share the required authorized BEFORE/DURING/AFTER frames.

## 13. Recommended next step

Improve event-window target/anchor co-visibility coverage before changing VLM or physical thresholds.
