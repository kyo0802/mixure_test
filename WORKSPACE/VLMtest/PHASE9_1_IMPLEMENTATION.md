# Phase 9.1 Implementation Plan

**Goal:** Reduce redundant Nemotron asset verification and expose real persisted memory through an interactive, read-only Graph page.

**Architecture:** Keep sequential model ownership and the existing job lock. Add pinned asset verification receipts and monotonic boundary timings to the existing video worker. Adapt persisted records into bounded visualization nodes/edges; use a local Streamlit component with selection events and the existing evidence viewer.

**Tech stack:** Python standard library, existing Streamlit custom-component API, local SVG/JavaScript, existing Pillow evidence rendering. No new frontend framework or GPU service.

## Tasks and acceptance

- [x] Inspected jobs, logs, metadata, TemporalMemory and saved session hashes.
- [x] Implemented pinned asset verification, receipt reuse, invalidation, strict/force and atomic fail-closed receipts; byte-file tests passed.
- [x] Added monotonic traces across job wrapper, Windows subprocess, Linux launcher and Nemotron operation boundaries. Input prompt/generation AST comparison passed.
- [x] Added read-only adapter with stable session-scoped record IDs, exact pointers, cache validation and bounded filters.
- [x] Added local SVG Streamlit component, actual node/edge click events, pan/zoom/reset, detail panel, existing source evidence and search handoff.
- [x] CPU tests and real test8 browser journey completed; unknown keys and test2 cross-session isolation verified. One separate DEMO_PRESENTATION check confirmed then undone.
- [x] Full SHA 63.723 s; cached metadata 0.324 s. GPU startup/new-video speed pending by design. Reports and workspace navigation updated; no commit/push.

## Commands

Existing app: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/start_findmind_demo.ps1`.

Focused tests: `.venv/Scripts/python.exe -X utf8 -B -m unittest discover -s tests -p test_phase9_1*.py` and existing `test_findmind_*.py` / `test_phase[4-7]_*.py` patterns. Use project-local TEMP/TMP. Expected: all executed tests pass; real-artifact tests remain explicitly distinct from deterministic mock data.

## Inspection findings

Two completed real sessions exist. Historical test8 Nemotron stage 482.359 s / load aggregate 435.121 s; log reports weight loading 48.97 s, model loading 67.225 s (overlapping), engine init 8.77 s. Other overhead is not yet attributed. A second completed session reports 519.031 s / load 490.045 s. No active GPU job was found; Windows CIM process inspection was denied, so no process was terminated.

Model reuse is already per video subprocess across windows. Retaining ~10 GiB model weights plus KV cache across Qwen/SAM would conflict with the existing 16 GiB sequential lifecycle; do not add a persistent server in this task.
