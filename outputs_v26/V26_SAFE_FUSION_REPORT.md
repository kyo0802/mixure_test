# V2.6 — Safe Re-ID Fusion, Continued Audit, and Identity Visualization

Date: 2026-09-26. Authoritative comparison baseline: the fresh-input seven-video `outputs_v25_rerun`, not the earlier mixed-input `outputs_v25`. All V2.6 files were written within `mixure_test_SAM/outputs_v26` and `src/memory_graph/v26`; prior output folders and `mixure_test` were not edited.

**Prediction provenance:** The first seven-video blind prediction was frozen before physical-identity review and is preserved in `outputs_v26/initial_blind/`. A post-review regression exposed inherited V2.5 merge provenance in the copied registry, not a V2.6 authorization error. We made a generic source-cleanup repair and reran all seven videos. The final manifest marks `B_POSTFREEZE_PROVENANCE_REPAIR`; it does not claim the repaired files were frozen before review. All 2,793 per-candidate categorical Re-ID decisions across the seven videos were identical to the initial blind run. Tiny GPU floating-point score differences did not change any decision. The final manifest SHA-256 is `41fcaedc7b6ffb078ae87f02b80ddbdd872ea4874f8747247dbbb2edddf76043`.

## 1. Research Question

Can a generic match-authorization rule prevent a weak lone-candidate false physical merge while retaining the known strong multi-candidate Re-ID match? Can the pipeline keep later candidate evidence auditable after a match decision?

## 2. Authoritative V2.5 Rerun Baseline

The current test3–test9 video SHA-256 values, each fresh V2.1 input manifest, the V2.5 rerun predictions, YOLO/SAM/MobileNet configuration, and frozen 0.60 similarity / 0.10 uniqueness margin were checked and recorded in `baseline_manifest.json`. The workspace had normalized previously generated Windows text files from CRLF to LF; reconstructing the original line endings reproduced the pinned V2.5 hashes, including the mixed-line-ending Re-ID patch. Video and image hashes matched byte-for-byte. V2.5's reviewed baseline had 174 hypotheses, 6/6 reviewed eligible late target boxes admitted, one correct test8 MATCH, and one false test7 landline MATCH.

## 3. V2.5 Identity Failure Visualization

Before modifying Re-ID behavior, all seven videos received read-only V2.5 `identity_timeline.png`, `reid_timeline.png`, and `reid_contact_sheet.png` under `baseline_visualization/testN/`. The test7 contact sheet directly contrasts trusted original smartphone crops with the f636 landline and later true smartphone crops at f720/f888. The timeline shows V2.5 matching the landline at 0.611 with no competitor, then not evaluating the later targets. Test8 shows the trusted black smartphone, correct f804 match, and later target/landline hypotheses.

## 4. V2.6 Match Authorization Change

V2.6 reuses the unchanged V2.4 MobileNetV3 scorer and its hard contradiction, quality, temporal, similarity, and margin gates. A separate authorization step distinguishes `AMBIGUOUS`, `PROVISIONAL_MATCH`, `CONFIRMED_MATCH`, and `REJECTED`. An irreversible match requires frozen score ≥0.60, a real second eligible candidate with margin ≥0.10, no scorer contradiction, and a current observation of the winning candidate. The current-observation condition stops an old provisional candidate from gaining confirmation solely because a weaker different phone appears much later. No per-video constants or reviewed labels occur in inference code.

## 5. Single-Candidate Safety Rule

No eligible second candidate means uniqueness is unproven. An otherwise matching sole candidate is `PROVISIONAL_MATCH`; it keeps a separate candidate record, does not alias `phone_01`, does not enter the trusted bank, and cannot trigger same-identity SAM. `phone_01` remains its original persistent entity, possibly `UNOBSERVED`.

## 6. Continued Candidate Audit

All seven videos were run blind over their existing sampled V2.5 candidate streams. V2.6 does not break after provisional or confirmed decisions. It records scores and decisions for later candidate observations, including post-confirmation `CONTINUATION_EVIDENCE`, `NEW_DISTINCT_CANDIDATE`, `CONFLICTING_IDENTITY_EVIDENCE`, or `INSUFFICIENT_EVIDENCE` roles when supported. These roles are audit labels and do not authorize another destructive alias. V2.5's matched candidate observation was removed from the clean comparison query before V2.6 scoring, preventing the old false alias from contaminating the trusted target bank. Original frozen V2.5 files were read-only.

## 7. Test7 False-Merge Case

At f636, `candidate_004` is visibly a landline. It scored 0.611 with no eligible second candidate. V2.5: `MATCH`, false alias, false SAM reinitialization. V2.6: `PROVISIONAL_MATCH`, **no alias and no SAM reinitialization**. Later reviewed target candidates `candidate_014` at f720 and `candidate_015` at f888 reached the Re-ID/audit layer; their sampled-frame similarities were about 0.535 and 0.512 and remained ambiguous. The original phone was kept safe, but long-gap target recovery is unresolved. The full video has 94 candidate-audit event frames in V2.6, compared with V2.5 stopping after its first match.

## 8. Test8 Positive Re-ID Regression

At f804, `candidate_009` scored 0.681 versus a 0.422 second eligible candidate, margin 0.259. V2.6 retained `CONFIRMED_MATCH`, aliasing this reviewed true target to `phone_01`, and executed same-identity SAM reinitialization within `outputs_v26`. Later f888/f918 target and two landline hypotheses remained in the audit. These later observations were not destructively re-aliased. The SAM reinitialization output is logged, but its masks are not fully routed back through the EntityRegistry guard; the recorded state is `POST_MATCH_CONTINUITY_NOT_FULLY_INTEGRATED`.

## 9. Per-video Results

| Video | V2.5 outcome | V2.6 confirmed | V2.6 provisional | V2.6 audit event frames | Reviewed interpretation |
|---|---|---|---|---:|---|
| test3 | NO_SAFE_MATCH | none | none | 39 | final box interior not directly visible |
| test4 | NO_SAFE_MATCH | none | none | 32 | later target evaluated, appearance still insufficient |
| test5 | NO_SAFE_MATCH | none | none | 28 | updated-video target retained earlier; no safe late match |
| test6 | NO_SAFE_MATCH | none | none | 30 | reviewed visible target has YOLO miss |
| test7 | false landline MATCH | none | `candidate_004` | 94 | false physical merge prevented; later target candidates evaluated but ambiguous |
| test8 | correct target MATCH | `candidate_009` | none | 40 | correct positive match preserved; later phones audited |
| test9 | NO_SAFE_MATCH | none | none | 64 | reviewed visible target has YOLO miss |

Each `testN/` contains machine-readable V2.5/V2.6 candidate comparisons (JSON and CSV), identity and Re-ID timelines, a contact sheet, Re-ID audit, candidate stream/history, entity registry, SAM log, and post-freeze review notes. The preserved initial blind artifacts are under `initial_blind/testN/`.

## 10. False-Merge Safety

Across the seven reviewed videos: **1 confirmed match, 1 provisional match, 1 true confirmed match, 0 false confirmed matches, 0 reviewed false physical merges**. In V2.5 the same reviewed set had one false permanent merge. Three distinct reviewed later target candidates that V2.5 left unevaluated after its first MATCH (test7's two and test8's later target) now have V2.6 audit scores. Provisional uncertainty is not counted as successful Re-ID.

## 11. Visualization Outputs

The seven pre-change baseline figures are in `baseline_visualization/testN/`. Each V2.6 `testN/` contains `identity_timeline.png`, `reid_timeline.png`, and `reid_contact_sheet.png`, with candidate IDs, frames, source tracks, scores/margins, V2.5/V2.6 decisions, and post-freeze physical identity labels. `test7/test7_identity_failure_explainer.png` and `test8/test8_correct_reid_explainer.png` provide large crop comparisons for presentation. The JSON/CSV comparison retains the full candidate table beyond the selected crops in the contact sheets. Figure labels for displayed candidate crops use scores from the *same displayed frame*.

## 12. Regression Tests

All **16 V2.6 focused tests pass**, including the 13 named specification requirements, test7's no-alias/no-SAM condition, and test8's confirmation/SAM condition. The final full suite reports **136 passed, 3 failed**. Those three failures are in older byte-exact snapshot tests: two V2.4.1 checks and one V2.5 rerun check compare text files after this workspace normalized generated CRLF to LF. The earlier V2.4.1 test5 input also still carries the known old-video hash expectation. The V2.6 baseline verifier independently restored and checked the pinned original text hashes. The post-review repair was checked against the preserved blind decision list and changed no categorical Re-ID result. No old tests or output files were edited merely to force a green suite.

## 13. Known Detection Limitations

Reviewed target-visible frames test6 f630 and test9 f810 lack a corresponding target YOLO box; test8 f810 also has a local miss after an adjacent successful match. V2.6 does not alter the detector, confidence threshold, SAM model, or target binding. These misses cannot be solved by the new authorization rule.

## 14. Limitations

Test7's true later phone reaches audit but remains ambiguous under the frozen appearance model; no recovery claim is made. After test8's confirmed match, SAM masks are generated and recorded but not fully reintegrated into the registry. The current post-match roles provide observability, not complete long-term entity continuity. Candidate fragmentation and sparse manually reviewed identity labels remain limits on generalization claims. The generic registry provenance repair occurred after review, with the initial blind artifacts retained and categorical decisions verified identical. No final-location or spatial-memory inference was attempted.

## 15. Result Classification

`FALSE_MERGE_PREVENTED_BUT_TARGET_RECOVERY_UNRESOLVED`. The known false irreversible merge is prevented without regressing the known correct match, but test7's later true target still lacks sufficient appearance evidence for confirmation.

## 16. Next Architecture Decision

`PROCEED_TO_MINIMAL_SPATIAL_MEMORY_GRAPH`. The prototype identity layer now behaves conservatively on the known safety case and retains the positive test8 match. Keep provisional/ambiguous identity explicit in any spatial graph, and do not promote uncertain candidates into physical `phone_01` relations. Treat post-match SAM-to-registry continuity and test6/test9 detector misses as separately recorded limitations, not as solved by this milestone.
