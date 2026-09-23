# V2 GPU Validation Implementation Plan

> **For agentic workers:** Execute the following tasks inline in this session; the user has already requested implementation and validation.

**Goal:** Validate the existing V2 on test1.mp4 and test2.mp4 with real GPU VLM evidence, preserving V1 and honestly recording model limitations.

**Architecture:** Keep selective event windows and fixed track IDs. Keep event-only artifacts separate from local-VLM runs and regenerated V1 comparison artifacts. Strict schema and geometry validation remain the boundary before temporal memory.

**Tech Stack:** Python 3.12, uv, PyTorch CUDA, Ultralytics, Transformers, Pydantic, OpenCV, pytest.

## Tasks

- [x] Verify V1 source hashes against docs/v1_preservation_manifest.json; record absent historical outputs separately from modified files.
- [x] Install optional dependencies and verify an actual CUDA tensor operation on the RTX 5070 Ti.
- [x] Inspect tests/test_v2_events.py::test_event_budget_is_enforced and reset `event.selected = False` and `event.skip_reason = None` before selecting each merged event. Add zero-budget and stale-selection regression coverage. Run all tests.
- [x] Update scripts/run_all_v2.py to accept explicit video paths and model-download authorization, preserving old task1/task2 defaults.
- [x] Run both videos with --events-only into outputs_v2_events/task1 and task2; inspect event contact sheets, timelines and JSON.
- [x] Run real local VLM into outputs_v2/task1 and task2. Verify model compatibility, raw responses, structured parsing, supplied IDs, geometry conflicts, unknowns and distinct chairs. Record failures without replacing them with invented results.
- [x] Add meaningful integration/regression tests for any discovered contract failures; run the complete suite.
- [x] Regenerate V1 comparison results under outputs_v1_comparison/task1 and task2, without writing historical outputs/task1 or outputs/task2.
- [x] Create scripts/audit_v2.py and a twenty-criterion validation report; verify images, complete decoded videos, event budgets, mappings, temporal fields and V1 preservation. Document basketball/trash-can/chair observations with event IDs and timestamps.
- [x] Write README_V2.md with commands, architecture, actual outcomes, limitations and output links. No lost-object ranking, UI, 3D claims or work beyond V2.

## Commands

```powershell
uv sync --extra vlm
uv run pytest -q
uv run python scripts/run_video_v2.py test1.mp4 --events-only --output outputs_v2_events/task1
uv run python scripts/run_video_v2.py test2.mp4 --events-only --output outputs_v2_events/task2
uv run python scripts/run_video_v2.py test1.mp4 --backend local --allow-model-download --output outputs_v2/task1
uv run python scripts/run_video_v2.py test2.mp4 --backend local --allow-model-download --output outputs_v2/task2
uv run python scripts/run_video.py test1.mp4 --output outputs_v1_comparison/task1
uv run python scripts/run_video.py test2.mp4 --output outputs_v1_comparison/task2
```

Success requires inspecting actual results; passing synthetic tests alone is not evidence of semantic correction on these videos.

## Completion record

Completed 2026-09-23. Full suite: 50 passed. Four V2 artifact audits passed. Original failing-test count was not reproduced before the fix. Real 7B NF4 inference completed on both videos; final geometry validation replays cached original responses. See V2_VALIDATION.md for the twenty criteria and remaining semantic limitations; trash-can correction, interactions and transitions are not claimed successful.

