# V2.1 Persistent Identity and Bottleneck Evaluation Implementation Plan

> **For agentic workers:** Execute inline in this session. The user explicitly requested implementation, GPU runs and reporting; preserve existing V1/V2 files. No segmentation implementation.

**Goal:** Separate detector, local tracking, persistent association, admission and reasoning errors using inference-isolated evaluation.

**Architecture:** Add `memory_graph/v21` with quality, association, missed-context reasoning, graph promotion and orchestration. Reuse unchanged V2 perception/events/backend in a nested V2.1 output. Add independent `memory_graph/evaluation_v21` and evaluation-only annotations. Snapshot hashes before changes; freeze predictions before annotations are consumed.

**Tech Stack:** Existing Python/Pydantic/OpenCV/NumPy/Matplotlib/Transformers stack and existing Qwen 7B NF4 GPU configuration.

- [x] Add typed contracts and conservative quality/resolver. Numeric entity IDs unrelated to labels; temporal overlap prohibits merging; require short-gap spatial, appearance and motion evidence; ambiguous candidates remain distinct. Future 3D/mask fields remain null.
- [x] Add tests with synthetic tracks: equal semantics is insufficient, co-visible identical chairs separate, clear short-gap continuation matches, ambiguous alternatives do not merge, detector absence preserves last-confirmed observation without a current bbox.
- [x] Add generic crop extraction and track/entity contact sheets. Quality includes gaps, normalized bbox jumps, velocity change, appearance and semantic consistency. Diagnostic flags do not assert GT ID switches.
- [x] Add V2.1 orchestration: verified reuse of perception, resolve all usable tracks before V2 event execution, retain unknown entities regardless of event selection. Save all decisions and V2 admission comparison.
- [x] Add missed-context analysis with the existing backend: selected frames plus last confirmed crops/IDs, no invented bbox; strict NONE/UNCERTAIN/SUPPORTED result and endpoint/phase validation. Content-addressed cache includes prompt, image and backend hashes.
- [x] Separate IMAGE_* observations from candidate/promoted physical relations. Confidence provenance stays separate; geometry-only claims never enter physical memory. Persist supporting times, stale status and rejection reasons.
- [x] Build independent GT review tool and annotation template, raw-frame and detector overlays. Store supplied narrative only under evaluation. Sparse manual annotations retain exact frame indices and review provenance; no automatic narrative-to-frame conversion.
- [x] Implement evaluator tests: no detection is detection failure, occluded frames excluded, no reappearance requirement, distinct phones false merge, recoverability only explicitly annotated, missing coverage reports NOT MEASURABLE FROM CURRENT GT.
- [x] Run both videos using the fixed GPU model; inspect raw VLM outputs, association histories and graphs. Freeze prediction hashes before evaluator runs.
- [x] Review relevant smartphone sequences and distinct phones/chairs manually. Calculate only supported metrics with denominators and sparse-sample scope. Attribute errors and diagnose bottleneck without modifying inference thresholds based on GT.
- [x] Write README_V21.md and V21_VALIDATION.md with requested ten-part report, exact commands, preservation/test results and controlled A/B proposal. Cite official SAM3 and R4DSG sources; do not claim SAM replaces semantic interaction reasoning.

Validation: `uv run --extra vlm --extra gpu --extra quantized pytest -q`; `scripts/run_video_v21.py test1.mp4 --reuse-v2 outputs_v2/task1 --output outputs_v21/task1` (same for task2); `scripts/review_v21.py`; `scripts/evaluate_v21.py`; compare baseline hashes. Tests and artifacts are reviewed before success claims.

