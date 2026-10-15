# Qwen NF4 V1D Execution Readiness Repair Plan

Task: PASS_T_PHASE2B_QWEN_NF4_EXECUTION_READINESS_REPAIR

Goal: remove only the existing engineering integration blockers and prove the guards using CPU-only deterministic metadata mocks. No approval, freeze, model, CUDA, media/GT reads, new visual fixture, predictions, Graph, commit or push.

## Responsible files/functions before editing

- A: `src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py:prepare_video_array`; V1D selection at expected_prompt_sha256 requires synthetic_only=True. Add an explicit separate real-pilot authorization branch before heavy imports, retain old branch verbatim for synthetic callers. Shared `local_vlm/nf4.py` stays unchanged.
- B: `phase2b/protocol.py:prompt_path/prepare_protocol/freeze_protocol/verify_frozen_protocol`, `local_vlm/transport.py:construct_request/invoke`, `phase2b/inference.py:run_real`; legacy base prompt/encoded-video interfaces cannot represent the V1D in-process array. Add an explicit versioned V1D protocol/execution integration, with no fallback into legacy transport. Keep all 21 proposed human decisions in the draft. Frozen content/source component hashes and independent execution receipt must be checked before any media/model boundary.
- C: `phase2b/evaluation.py:_compatible/match_known_events/evaluate_item`; overlap-length logic gives a nonzero endpoint distance for an interior predicted point. Add a versioned closed-interval matcher, preserve default historical matcher. Unknown/missing timing and unsupported association cannot match.
- Strict output: `phase2b/predictions.py:parse_raw/validate_prediction` is protected. Add a reporting/gating caller that preserves raw bytes, separates unassessed semantic/citation stages after schema failure, and never sends strict-invalid/missing outputs to structured matching.
- Provenance: explicit metadata manifest with approved ordered source list, Uniform8 selection, per-frame source SHA/native PTS/aliases and per-window boundary hashes. Current media checks remain PENDING_AUTHORIZED_EXECUTION. No historical payload hash reused as a V1D input hash.

## Steps

1. Snapshot exact sources, protected prompt/schema/runtime/report hashes and Git metadata before any source modification; back up only affected text files here.
2. Add CPU-only V1D draft/freeze/execution guard and provenance integration. Do not manufacture a human approval or frozen artifact during this task.
3. Connect the Bridge with a separate explicitly guarded real path; retain legacy/synthetic behavior and shared NF4 source.
4. Add versioned matcher and strict-invalid classification/reporting; no changes to strict validator semantics.
5. Add an explicit CPU dry-run CLI and an authorized in-process orchestration path, with late model/media access only after gates. No legacy fallback.
6. Run narrowly scoped unittest/mock tests under an import/file/socket guard. Mock data are software fixtures, not physical-event GT; no image/video fixtures.
7. Verify all source changes, exact diffs and before/after SHA, protected artifacts and historical 1/8 result preservation. Record pending real media/GPU checks honestly.
8. Publish the eight required repair reports here and latest readable report in WORKSPACE/Pass_T; stop for human freeze review, never call freeze/run.

No additional agents/worktrees. Task restrictions override skill defaults about commits and execution handoff.
