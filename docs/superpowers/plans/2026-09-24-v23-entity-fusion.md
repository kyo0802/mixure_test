# V2.3 YOLO + SAM Entity Fusion Implementation Plan

> **For agentic workers:** Implement inline, with no subagent work.

**Goal:** Demonstrate one persistent entity registry receiving full-scene frozen YOLO tracks and selected SAM 2.1 smartphone observations.

**Architecture:** V2.3 reads frozen V2.1 tracks/detections and V2.2 SAM masks, verifies hashes, then streams source-neutral observations into an EntityRegistry. The phone's SAM target inherits its YOLO-established registry identity; later YOLO overlap can confirm it. A contradiction gate prevents an expanding SAM mask from poisoning trusted phone memory. GT is read only by a separate V2.3 review script.

**Tech Stack:** Python 3.12, NumPy, OpenCV, Matplotlib, existing V2.1/V2.2 JSON artifacts.

---

### Task 1: Build source-neutral fusion

- [x] Create `src/memory_graph/v23/fusion.py` with Observation, EntityRegistry, decisions, inherited SAM identity, contradiction guard, and audit history.
- [x] Use existing V2.1 track-to-entity hypotheses as conservative scene priors; all final registry IDs are separate from YOLO/SAM IDs.
- [x] Keep unmatched later phone candidates distinct and preserve unobserved entities.

### Task 2: Run and inspect

- [x] Create `scripts/run_fusion_v23.py`, read only frozen V2.1/V2.2 inputs, output registries/audits/graph snapshots/timelines under `outputs_v23`.
- [x] Inspect task1 continuity and desk-phone negative control, task2 track22/43, frame312 guard, late candidates and distinct desk phones.
- [x] Create separate evaluation/report code which alone reads `evaluation/v21`.

### Task 3: Verify and report

- [x] Add eight focused tests required by the spec.
- [x] Run all old and new tests, verify input hashes, and produce `V23_FUSION_REPORT.md` and `fusion_summary.json`.
