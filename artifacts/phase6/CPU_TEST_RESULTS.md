# Phase 6 focused verification

2026-10-21. Final: **62 tests passed**, 0 failures/errors, 0.091 seconds.

```powershell
New-Item -ItemType Directory -Force -Path artifacts\phase6\test_tmp | Out-Null
$env:TEMP = (Resolve-Path artifacts\phase6\test_tmp).Path
$env:TMP = $env:TEMP
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_phase*_*.py"
```

Includes Phase 4/5 regression and 18 Phase 6 cases: frame geometry, bounds, canvas conversion without clipping, mask provenance, missing-not-negative, held-not-supported, unknown identity, historical unlocalized claims, no identity transfer, arbitrary video IDs, other-object fixture query, persistence, trusted history, category conflicts, region deduplication and entity-scoped supplementary results.

Earlier 61-test repeat had one Windows sandbox TEMP PermissionError in Phase 5 persistence test (graph.json creation/cleanup); no assertion failure. The same suite passed after directing TEMP/TMP to this repository. The final entity query guard added the 62nd test. An ad-hoc verification command initially imported TemporalMemory from the wrong module; corrected to memory_graph.scene_graph.models without any production-code change.

Real saved Graph checks: all nine graphs load, both saved phone/cup queries match current query code (18/18). Original run also checked save/reload consistency. 3,273 protected input files and 21 final raw outputs rehashed unchanged at closeout. No inference during CPU verification.
