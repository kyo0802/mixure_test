# Phase 8 implementation checklist

Goal: local Streamlit object-search demo over the existing Phase 7 CLI and persisted TemporalMemory, with real session evidence and disk-owned subprocess jobs. No new perception pipeline, inference benchmark, external LLM or Graph schema.

- [x] Add small CPU-only findmind_demo package: session discovery, deterministic bilingual intent/answers, evidence scope/hash validation and overlays, disk job ownership.
- [x] Add Streamlit app with separate recorded/new-video modes, candidate cards, evidence and concise history. Do not load GPU modules in recorded mode.
- [x] Add isolated job wrapper using the actual Phase 7 CLI, atomic shared GPU lock, idempotent submissions, disk states/logs and observable stage progress.
- [x] Focused user-journey tests and existing Phase 4–7 regressions; browser smoke using the real saved session if available.
- [x] Publish actual measured startup/query times, launch command, tested paths and limitations to WORKSPACE/VLMtest/LATEST_REPORT.md.

Complete: 15 Demo tests + 71 prior tests; actual browser verified Chinese/English phone search, UNKNOWN, upload validation and restart. No new GPU inference. Current service: 127.0.0.1:8514. Optional departure checklist omitted to prioritize search.

Files: apps/findmind_demo.py, src/findmind_demo/{agent,sessions,evidence,jobs}.py, scripts/run_findmind_job.py, scripts/start_findmind_demo.ps1, tests/test_findmind_demo.py. Use vendored Streamlit 1.50.0. Real GPU execution remains an explicit UI submission; validate the job launch contract with deterministic mocks rather than rerunning the 12-minute pipeline.
