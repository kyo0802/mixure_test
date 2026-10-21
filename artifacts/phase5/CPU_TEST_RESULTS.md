# Phase 5 CPU verification

Command (repository root):

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_phase*_*.py"
```

Result: exit 0; 44 tests; 0 failures/errors; OK (0.078 s).

22 existing Phase 4 tests and 22 Phase 5 tests passed. Deterministic mock records are test contracts, not physical-event ground truth. No synthetic image/video fixtures, model loading or CUDA initialization.

Real integration: all nine source recordings replayed, event decisions unchanged, saved TemporalMemory reload/query equality asserted for every video. Exact input and preservation hashes, source-code hashes and per-video metrics are in `demo/run_receipt.json`.

Query-only CLI validated using the saved test2 graph; it returns POSSIBLE_LOCATIONS and retains source evidence. No media decoding or model inference is required for querying a saved graph.
