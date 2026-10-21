# Phase 5 Spatial Memory Implementation Plan

Goal: grounded, queryable location observations in the existing TemporalMemory, independent of confirmed events.

Architecture: frame-scoped scene registry → conservative object/region geometry → identity-scoped location history → existing search dispatch. Reuse Phase 4 normalized observations and unchanged event decisions. CPU extraction only; no new model generation, GT lookup, commits or production memory.

## Implementation

- [x] `src/memory_graph/integration/regions.py`: validate native source/frame identities; propose detector extents and edge-derived convex surface candidates from decoded original frames. Frame-only validity and independent viewpoint IDs prevent unsupported propagation. Optional reviewer definitions retain provenance and cannot silently become automatic evidence.
- [x] `src/memory_graph/integration/spatial.py`: distinguish projected containment/overlap/near/above from physical support; resolve VLM/CV only with localizing evidence; store candidate and authorized verified history separately in TemporalMemory metadata and graph edges. Search preserves ties, later uncertainty and history.
- [x] `scripts/run_phase5_demo.py`: verify Phase 4 inputs, original videos and timelines, decode only needed source frames, build all nine spatial graphs, persist/reload, query, output counts and representative evidence sheets under `artifacts/phase5/`.
- [x] `tests/test_phase5_spatial.py`: CPU geometry/identity/time/visibility/authority/persistence tests, plus unchanged Phase 4 regression tests. No synthetic visual fixtures or GPU runtime.
- [x] Inspect original representative image sequences; record limitations separately from runtime evidence. Verify input hashes unchanged and publish Traditional Chinese report to WORKSPACE/VLMtest.

## Verification

Run the focused unittest modules with `.venv/Scripts/python.exe -B`, then `scripts/run_phase5_demo.py --output artifacts/phase5/demo`. Verify reload/query equality, unchanged Phase 4 decisions, raw input digests and no GT/reviewer verdict imports. Named detector extents remain candidate regions; edge polygons do not establish support or depth. Missing localization keeps VLM association unresolved, even with only one category-compatible CV detection. Report actual counts, including zero verified observations when appropriate.
