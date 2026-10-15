# Qwen NF4 engineering closeout implementation plan

Execute sequentially in the existing worktree. This supersedes unfinished Track 1; no prior Track 1 result is claimed. No commits, additional worktrees, real DEV pixel reads, new fixtures or prompt changes.

1. Verify old holdout receipt, seven synthetic fixture assets, V1C, shared formatting, schema, Validator and historical runtime. Snapshot protected source/metadata without opening DEV imagery. Preserve exact old NF4 source before authorized minimal integration.
2. Add standalone `video_array_bridge.py` and one explicit default-disabled branch in `QwenNF4Runtime.preprocess`; reuse shared generation unchanged. Reject unknown mode, array on disabled route and missing native input. Pin 8 RGB frames, 4 units, FPS span and source hashes. No transport/server redesign.
3. Guarded CPU tests only on locked synthetic frames. Compare pixel values, IDs, grids, time metadata and aliases to original preflight. Record source-faithful integer conversion before temporal multiplication; preserve old proxy report.
4. Create `docs/preregistered_criteria.md` plus machine-readable manifest, immutable hashes and exact original B order/coverage before loading Qwen. Record budgets, hard stops, warnings and bounded smoke recovery. Lock six evaluations plus separate existing warmup.
5. One supervised GPU worker loads existing NF4 once. One video-array warmup smoke, then exactly 12 original-order Multi-image/Storyboard generations with flag OFF. No output-based retries. Preserve raw bytes and start/completion markers before validation; watchdog covers owned process tree, VRAM/RAM, load120s/request330s, generation300s.
6. Use unchanged strict Validator; independent diagnostic stages and known-state findings cannot override its decisions. Report coverage and engineering warnings after scheduled calls, no physical accuracy metric.
7. Consolidate report, 16-decision package, diffs, resource/guard/preservation receipts. Publish full latest report in `WORKSPACE/Pass_T`, update existing navigation. Stop for human protocol review; do not freeze or run DEV.
