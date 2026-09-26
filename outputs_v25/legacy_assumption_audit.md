# Legacy task-specific assumptions audited before V2.5 implementation

| Location | Assumption | V2.5 treatment |
|---|---|---|
| `src/memory_graph/v22/sam_tracking.py:117-134` | Task1/2 target track IDs 17/22 and seed frames 240/78; Task2 late frame 528 | Route a generic bound target and dynamically admitted candidate seeds into unchanged SAM `run_segment` and guard logic. |
| `src/memory_graph/v22/sam_tracking.py:159,211` | Video path branches to `test1.mp4`/`test2.mp4`; fixed propagation windows | Use selected video path; initial target propagation covers remaining sampled video. |
| `src/memory_graph/v23/fusion.py:263,280,289` | Target track and representative frames hardcoded to task1/task2 | V2.5 owns target binding and frame loop; reuses V2.3 `sam_guard` and persistent entity semantics. |
| `src/memory_graph/v24/appearance.py:56,172` | Video path and trusted SAM source names fixed to task1/task2 | Use same crop, model, preprocessing, trusted-view selection, and embedding cache via a generic video path. |
| `src/memory_graph/v24/reid.py:228-232` | Exactly three Task2 candidate source IDs | Submit the live active candidate set to unchanged `decide()` each evaluation. |
| `src/memory_graph/v241/adapter.py:24-25,63-81` | 180-frame initial window, 108-frame gap, first later raw phone frame, 78-frame late window | Replace with continuous frame-by-frame admission and candidate hypotheses. |
| `src/memory_graph/v241/adapter.py:41-58` | Earliest repeated local phone track binds target | Replace with swappable `TargetBinding`; automatic policy uses only accumulated current/past track evidence and may return ambiguous. |

Model checkpoints, YOLO configuration, SAM diagnostics, MobileNet preprocessing, and V2.4 Re-ID threshold/margin are frozen. V2.4.1 artifacts remain immutable.
