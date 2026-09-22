# Video Memory Graph Implementation Plan

**Goal:** Process two complete local videos into inspectable temporal object/anchor graphs.
**Architecture:** Typed observations flow through independent video, perception, spatial, memory, and visualization modules. Store every intermediate stage; stable intervals are episode-scoped, identities persist across brief misses but reset at scene cuts.
**Tech Stack:** Python 3.12, uv, Ultralytics YOLO11n, ByteTrack, OpenCV, Pydantic, NetworkX, Matplotlib, pytest.
**Spec:** User's 28-section task in this conversation.

## Constraints
RGB bounding boxes are image-space evidence only. No ranking, reasoning, UI, training, or V2 modules. Preserve input videos. Actually execute both when available; report missing inputs honestly. User explicitly requests immediate implementation; execute inline without a handoff approval.

## Implementation sequence
- [x] Environment: inspect installed Python and accelerators; create pyproject, uv lock/environment; verify Python, torch, cv2 imports and CUDA.
- [x] Typed contracts and config: create models.py and config.py; validate positive sampling, bounded confidences and ordered boxes/times. Test invalid boxes and JSON round-trip.
- [x] Video: reader yields FrameInfo plus decoded image, including final sampled endpoint; segmenter uses HSV histogram distance, minimum duration and cooldown, merging short tails. Test synthetic abrupt cut and constant scenes.
- [x] Perception: detector yields raw Detection records; tracker uses ByteTrack with sample-rate-adjusted buffer and maps numeric identities to class-prefixed ObjectTrack IDs. Preserve unmatched detections and track history.
- [x] Spatial: geometry uses normalized coordinates, anchor selection combines semantic suitability, visibility, area and camera-relative stability; extractor emits typed relations for co-visible target/anchor pairs. Test left, above, near, overlap and containment.
- [x] Memory: group by pair/predicate/episode/reference frame, split on large gaps, require support and elapsed duration; graph builder creates MultiDiGraph and conservative transitions only between non-overlapping stable anchor intervals. Test single-frame noise, persistent changes, simultaneous anchors and serialization.
- [x] Presentation: save readable JSON, paginated graph PNG when crowded, sampled annotated MP4 and inspection CLI. Include exact output metadata and configuration.
- [x] Execution: run pytest, process task1 then task2, read JSON summaries, view PNGs and annotated frames, verify video endpoints and all artifacts. If source videos remain missing, test end-to-end with explicitly synthetic data without presenting it as real-video results.
- [x] Documentation: describe commands, artifacts, model vocabulary, tracker identity limitations, anchor heuristics, retrospective filtering and RGB-only geometry. Record actual validation status.

## Verification commands
```powershell
uv sync
uv run python --version
uv run python -c "import torch, cv2; print(torch.__version__, torch.cuda.is_available(), cv2.__version__)"
uv run pytest
uv run python scripts/run_video.py task1.mp4
uv run python scripts/run_video.py task2.mp4
uv run python scripts/inspect_graph.py outputs/task1/memory_graph.json
uv run python scripts/inspect_graph.py outputs/task2/memory_graph.json
```

## Completed execution
Both inputs arrived during implementation and were processed end to end. Final detector: YOLO11s at 960px, 5 sampled FPS. All 19 tests passed. See VALIDATION.md and outputs/validation_report.json for actual counts, full-frame checks, zero-transition analysis and visual QA. No V2 modules were added.
