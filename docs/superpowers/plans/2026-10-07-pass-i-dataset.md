# Pass I Dataset and Annotation Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an unlabelled CandidateEpoch dataset and durable human annotation application without model inference.

**Architecture:** Read only canonical V297 development and known-regression runs. Separate hidden inventory/pair provenance from neutral numbered evidence. Store human visual gold, raw model responses and optional physical GT independently.

**Tech Stack:** Python 3.12, Pillow, OpenCV, SQLite, Streamlit, pytest.

---

### Task 1: Discover and build dataset
**Files:** Create `src/memory_graph/pass_i/{__init__,common,builder}.py`, `scripts/build_pass_i.py`.
- [x] Read `candidate_epochs.json`, `metadata.json` and verified source manifests; reject unverified/overlaid/hash-mismatched crops.
- [x] Normalize observed epoch bounds separately from the builder's discontinuity end time.
- [x] Group explicit sessions, duplicate video bytes and duplicate/near-duplicate original-frame evidence before deterministic recording split.
- [x] Select spaced, distinct original crops; export neutral evidence packages and deterministic within-session pairs.
- [x] Run `.venv/Scripts/python.exe scripts/build_pass_i.py` and save manifests, coverage and preservation checks in `artifacts/pass_i`.

### Task 2: Safe model boundary and annotation persistence
**Files:** Create `src/memory_graph/pass_i/{adapter,annotations}.py`.
- [x] Serialize only item ID, dataset case policy and numbered image data URIs; accept a separately supplied prompt and keep calls disabled by default.
- [x] Validate evidence indices and label/cause/tag combinations.
- [x] Store immutable raw prelabels, visual human labels and physical GT separately; use transactional persistence and incremental JSONL exports.

### Task 3: Human application
**Files:** Create `scripts/pass_i_annotation_app.py`, `artifacts/pass_i/requirements.txt`.
- [x] Implement blind, review and optional physical modes; navigation, filters, exclusion, evidence editing and native-image enlargement.
- [x] Install Streamlit only in an isolated Pass I vendor directory, leaving the model environment unchanged.

### Task 4: Validation and delivery
**Files:** Create `tests/test_pass_i.py`, report under `artifacts/pass_i/reports`.
- [x] Test real manifests for session/frame/hash/numbering consistency and protected-file preservation.
- [x] Test actual model serialization, persistence after restart, annotation validation and raw-prelabel separation.
- [x] Run Streamlit AppTest for blind save, exclusion, resume, review and physical modes.
- [x] Deliver counts, launch command and remaining limitations. Do not generate labels, invoke models or run the formal benchmark.

Execution is inline as explicitly requested; no worktree change, unrelated edits, commit or model inference is needed.
