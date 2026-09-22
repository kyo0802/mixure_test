# Event-Driven Semantic Memory Implementation Plan

**Goal:** Extend the working V1 with event-selected multi-image VLM analysis and temporal semantic graphs without modifying V1 artifacts.
**Architecture:** Reuse detector/tracker/video contracts, wrap tracker identities in fixed numeric IDs, propose events from sparse timelines, select before/during/after images, validate VLM JSON and geometry, aggregate semantics and temporal evidence. Independent V2 CLI/config/output paths preserve comparison.
**Tech Stack:** Existing Python/uv stack plus optional Transformers, Pillow, Hugging Face Hub and psutil for a small CPU-capable multi-image model.
**Spec:** docs/specs/v2-request.md (verbatim user request).

## Constraints
No hard-coded object corrections, identity merges, lost-object reasoning, UI, depth or SLAM. No model inference on every frame. Cache raw responses using image content, model revision, prompt and metadata. VLM failure is an explicit per-event result, never substituted semantic evidence. Unknown is valid. Existing V1 files and outputs are checksum-checked.

## Execution
- [ ] Baseline: read V1, run its 19 tests, snapshot checksums, inspect RAM/CUDA before model download.
- [ ] Models/config: create config_v2.py, events/models.py, perception/track_timeline.py, vlm/schemas.py, scene_graph/models.py with fixed numeric IDs, controlled predicates, confidence and time validation.
- [ ] Perception/events: implement track_manager.py, interaction_signals.py, event_proposer.py and keyframe_selector.py; propose persistence-gated appearance/disappearance, sparse proximity, persistent co-motion and neighborhood changes; bounded overlap merging and priority budget; ordered phase-aware visibility/sharpness selection.
- [ ] VLM: add backend Protocol, local Transformers and configurable HTTP-compatible backend, compact grounding prompt, strict parser, content-addressed cache and hardware report. Use SmolVLM2-500M on this CPU as a bounded real-inference attempt, not a semantic quality guarantee.
- [ ] Graphs/memory: aggregate semantic evidence without merging IDs, admit persistent/event-supported tracks, keep unknowns and rejection reasons, validate geometry against phase-specific co-visibility, preserve sparse evidence times and interactions, and derive conservative observed changes.
- [ ] Presentation/CLI: create general semantic network PNGs with attribute nodes (no anchor panels), timeline, event input images, annotated video, run/inspect/compare scripts and full debug JSON.
- [ ] Tests: synthetic approaching tracks, sustained disappearance, co-motion, transitive event merging, phase order, unknown/invalid IDs/predicates, semantic correction, separate chairs, geometry conflict, temporal gaps, cache invalidation, per-event failures and full mocked integration; preserve baseline tests.
- [ ] Actual execution: event-only task1 first, inspect windows, attempt real VLM, inspect outputs, run task2, verify artifacts and compare known-object results honestly. Check V1 hashes and tests after implementation.
- [ ] Documentation: write V2 architecture, schemas, configuration, backend setup, actual validation/comparison report and V3 bottleneck recommendation.

## Validation commands
```powershell
uv sync --extra vlm
uv run pytest
uv run python scripts/run_video_v2.py task1.mp4 --events-only
uv run python scripts/run_video_v2.py task1.mp4
uv run python scripts/run_video_v2.py task2.mp4
uv run python scripts/inspect_memory_v2.py outputs_v2/task1/memory_graph.json
uv run python scripts/inspect_memory_v2.py outputs_v2/task2/memory_graph.json
```
