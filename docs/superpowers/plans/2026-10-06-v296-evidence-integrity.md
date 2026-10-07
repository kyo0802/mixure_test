# V296 Evidence Integrity + Dual-Route Safe Re-ID

**Goal:** Implement current, independent, clean, attributable candidate-epoch evidence and two explicit Guard confirmation routes; preserve all prior source/results and safe default.

**Architecture:** New opt-in `memory_graph/v296_reid` modules. IdentityGuard capability/mutation/revocation methods remain inherited verbatim. Candidate epochs group raw observations, evidence integrity filters banks, DINOv3 primary and on-demand DINOv2 crosscheck plus photometric veto precede current-only LightGlue. Guard alone confirms/backfills with scoped tokens. No labels in runtime decisions.

**Tech stack:** Existing official DINOv3/DINOv2, SuperPoint/LightGlue, OpenCV/NumPy/Pillow/PyTorch; existing Qwen2.5 NF4 only after identity safety gates pass. Inline execution under explicit user authorization.

**Files:** `src/memory_graph/v296_reid/{io,epochs,integrity,appearance,geometry,evidence,guard,calibration,runner}.py`; `scripts/{preflight_v296,run_v296_reid,report_v296}.py`; `tests/test_v296_reid.py`. New results only `outputs/v296_reid`; V295 modules and cached inputs read only.

- [x] Snapshot active source and protected artifacts with `python -B scripts/preflight_v296.py`; create codex/V296.
- [x] Write epoch/integrity failure tests before implementation: gap reuse splits; unique short stitch groups candidates only; self/hash/same epoch/descendant/annotated/stale references rejected.
- [x] Implement causal epoch builder with development global gap/motion/scale and persistent local appearance change; ambiguity freezes evidence and prevents backfill across discontinuity.
- [x] Build original-frame provenance: video/frame/raw image SHA, crop SHA, no overlays, local/epoch/alias/authorization/bank lineage. Verify reused crops against original canonical extraction.
- [x] Reuse frozen DINOv3 vectors; resolve DINOv2 only for serious candidates and independent Core/negative shortlists. No broad backbone benchmark.
- [x] Measure robust foreground Lab/chroma development distributions; choose conservative contradiction-only cutoff with zero target vetoes. UNKNOWN supplies no positive evidence.
- [x] Repair LightGlue pair admissibility and current-side requirement, retain keypoints/inlier distribution, object-interior filtering and audit pair visualizations.
- [x] Implement explicit temporal matrices, G geometry and stricter A appearance routes, negative/photometric/competitor/coexistence vetoes; keep provisional quarantined.
- [x] Guard authorizes initial/continuity as before, closes target continuity on candidate-epoch breaks, commits diverse trusted views only after stabilization, backfills only checked same-epoch rows using `_issue` and `write`.
- [x] Run synthetic full-contract tests plus real test1–9 development replays; inspect every new confirmation from original frames, record test8/test2/test7/test9 without hardcoded logic.
- [x] Freeze source, model revisions, numeric policies, crop/cache hashes, bank/backfill/integrity config; then execute val1–11 once, no tuning afterward.
- [x] Audit named and additional physical distractors, aliases/authorized rows/bank contamination plus independent/current/clean/source leakage flags.
- [x] Run focused and full pytest with local basetemp; smoke fresh YOLO/SAM→V296→unchanged builder/Qwen2.5 only if identity safety passes; otherwise explicitly record skipped safety gate.
- [x] Verify protected bytes, save all requested reports/manifests, choose exact status/readiness; do not promote main by default.

Commands use `.venv/Scripts/python.exe -X utf8 -B`, `PYTHONPATH=src`, `pytest -p no:cacheprovider --basetemp=.v296_test_tmp`, explicit SAM repository workdir. Calibration reads development labels only; evaluation case IDs never enter runtime modules.


Execution complete: frozen V296 known regression failed safety (val9/val10). Conditional Qwen smoke was explicitly skipped per section4. No policy tuning after val, no main promotion. Full suite488 passed,1 legitimately-unsealed validation skip. All32,312 protected files unchanged.
