# Native Annotated Event Video Implementation Plan

> Inline execution in this task. The writing-plans execution sub-skills are not installed; execute sequentially with frozen checkpoints. User authorizes experiment implementation and inference. Existing frozen source/output bytes remain protected.

**Goal:** Compare native 15-fps processor video with the frozen 5-fps image results for exactly nine complete event packs.

**Architecture:** Add isolated experiment utilities under the existing reasoning package; reuse Backend, render_frame, strict parser, minimal validator, scoring and offline simulation. Encode original-FPS 800x600 MP4 from frozen boundaries with exact-frame authority only. Native transformers video processor performs frame selection. No upstream or baseline changes.

**Tech Stack:** Existing Python/Qwen NF4 runtime, transformers 4.57.6 native video path, PyAV H.264 encoding, pytest.

### 1. Protected input audit

- [x] Verify `final_integrity_manifest.json` without rewriting existing files; read all three current reports and exact source.
- [x] Resolve only request pack IDs from frozen event manifest, timelines and six explicit source paths; hash known development videos only.
- [x] Store prior handoff hash, baseline requests/responses/review/source hashes in experiment config.

### 2. Exact clips and native processor

Files: create `src/memory_graph/reasoning/video_experiment.py`, `scripts/run_video_event_experiment.py`, `tests/test_video_event_experiment.py`.

- [x] Implement inclusive start/end source-frame ranges with normal one-frame duration tolerance. Render existing frame authority/context; unmatched frames have no T or anchor fill.
- [x] Encode H.264 CFR source FPS, no audio; decode/verify dimensions, pts spacing, frame count and source timestamp containment.
- [x] Build request `{'type':'video','path':clip_path}` plus adapted current text; call official `processor.apply_chat_template(..., tokenize=True, return_dict=True, fps=15, do_sample_frames=True)`.
- [x] Measure native selected indices with a transparent observer around original processor sample_frames; record metadata/tokens without changing sampling.
- [x] Assert actual frames/duration >=10 for every clip before semantic inference.

### 3. Preflight and freeze

- [x] One preflight event: longest frozen clip chosen from duration only. Persist response without semantic review.
- [x] Only GPU OOM permits one global 15→10 FPS fallback. A second failure stops experiment. No alternative FPS search.
- [x] Hash clips, requests, policy, source data, schema/validator/model config/review before nine canonical generations.

### 4. Canonical and paired evaluation

- [x] Generate once per exact nine IDs, preserve every failure, no answer retry; freeze raw/parsed/validator/compute outputs before review.
- [x] Use unchanged review labels, separately ALL9/eligible8/action6/release3/unique release2. Do not deduplicate before inference.
- [x] Review frozen annotated playback after predictions; record disagreements without changing reference labels. Recompute candidate safe/unsafe/material flags for new answers from frozen evidence.
- [x] Report distribution, paired correctness, abstention, unsafe claims, exact offline P/C/U/R and zero actual writes.

### 5. Tests, delivery and selection

- [x] Required focused experiment tests, existing focused tests, full suite; preserve prior inventory/test outputs and write new experiment regression evidence.
- [x] Write required 16-section Traditional Chinese report and all experiment JSON artifacts. Check existing 370-file delivery and identity/reference manifests unchanged.
- [x] Select video only for meaningful primary temporal benefit without unsafe regression. Change handoff only after final freeze if video wins; otherwise preserve bytes.
- [x] Hash final artifacts; deliver requested 16-point summary and three decision tokens. Do not access/run held-out validation.

Commands (cwd `mixure_test_SAM`):

```powershell
.venv/Scripts/python.exe -X utf8 -B scripts/run_video_event_experiment.py prepare
.venv/Scripts/python.exe -X utf8 -B scripts/run_video_event_experiment.py run
.venv/Scripts/python.exe -X utf8 -B scripts/run_video_event_experiment.py evaluate
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_video_event_experiment.py -q -p no:cacheprovider
```
