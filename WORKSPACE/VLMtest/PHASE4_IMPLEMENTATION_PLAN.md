# Phase 4 integration implementation plan

Goal: Replay recorded Nemotron and independently sourced CV evidence into the existing TemporalMemory store and execute evidence-driven object search.

Architecture: Add a small `integration` package. Reuse `three_vlm_contract.validate_raw`, `SemanticEntity`, `TemporalMemory`, and `memory_store.save_json`. Preserve raw validation separately from event decisions. Runtime never loads annotation/review verdicts. Existing CV geometry supplies observations and IdentityGuard authorizations, but no invented physical-state/location measurements.

Implementation checklist:

- [x] `src/memory_graph/integration/adapters.py`: raw/future Nemotron adapter, native-frame verification, recorded IdentityGuard/CV adapter.
- [x] `src/memory_graph/integration/pipeline.py`: evidence decision, conservative grouping, existing Graph persistence, deterministic search.
- [x] `scripts/run_phase4_demo.py`: CPU-only recorded/future input CLI; isolated immutable output; input preservation receipt.
- [x] `tests/test_phase4_integration.py`: 22 focused CPU tests pass.
- [x] Nine-video replay and Graph reload complete; report in WORKSPACE/VLMtest/LATEST_REPORT.md.

Validation command: `.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_phase4_integration.py -v`.

No production writes, model inference, benchmark scoring, commit, or push. Implementation proceeds inline in the existing working tree under the user's explicit instructions.
