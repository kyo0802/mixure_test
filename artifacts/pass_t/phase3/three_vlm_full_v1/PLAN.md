# Full three-VLM implementation plan

**Goal:** Common answer-independent Uniform8 dataset with full test1–test9 timeline coverage, real sequential inference, and one evidence-limited comparison.

**Architecture:** New experiment namespace; preserve historical runners/results and Graph. Reuse Qwen NF4 loader and official VideoLLaMA adapter. Pin official Nemotron NVFP4 and isolate Linux vLLM under the repository. Human evidence stays outside inference inputs.

- [ ] Build `scripts/build_three_vlm_dataset.py`: verify nine videos, decode native PTS; preserve historical boundaries with explicit semantics; Uniform8 nearest native PTS without repeated source indices; fixed 4-second/2-second coverage grid; exact visual deduplication and overlap/timeline manifests.
- [ ] Add `src/memory_graph/experiments/three_vlm_contract.py`: shared compact observation-first prompt/schema, raw/fence/schema/citation/semantic diagnostics; explicit provenance and temporal matching/deduplication. Freeze dataset/configs/revisions before new outputs.
- [ ] Add `scripts/run_three_vlm_dataset.py`: isolated model paths, reusable adapters, one model at a time, raw-first resumable ledger, at-most-once completed generations. Run Qwen and VideoLLaMA on every unique input; attempt official Nemotron video8 through Linux vLLM, preserve any actual blocker.
- [ ] Add `scripts/evaluate_three_vlm.py`: consistent structured diagnostics, eligible existing GT only, deduplicated event proposals, missing-label exclusions; generate contact sheets, original-video links and editable human event/state/coverage files without fake labels.
- [ ] Run bounded CPU contract/coverage tests plus actual inference verification; publish one Traditional Chinese comparison under this namespace and WORKSPACE/Pass_T/LATEST_REPORT.md. No training, historical changes, Graph writes, commit or push.
