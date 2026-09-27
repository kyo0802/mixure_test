# V2.7 Target-Centric Spatial Memory Implementation Plan

**Goal:** Convert frozen trusted target observations into sparse temporal/lifetime memory and explainable search plans.

**Architecture:** One episode/event store generates both graph views. Read V2.6 entity history and per-frame candidate authorizations; never infer identity from the final track alias map. Image relations remain observations. Stable anchor context is explicitly image-relative; physical promotion additionally requires a structured, independently supported interaction/event/VLM assertion.

**Execution:** Inline, within `mixure_test_SAM`; no upstream changes or model inference.

## 1. Data and identity boundary

- Add typed models and a frozen-input adapter under `src/memory_graph/v27/`.
- Consume original trusted history plus exact current `CONFIRMED_MATCH` events; retain all other target/candidate observations as observation-only.
- Preserve upstream entity IDs for anchors and track IDs only in provenance.
- Confirm availability of existing VLM evidence: all 56 inspected event graphs have `skipped_events_only`; their 2D edges cannot authorize physical relations.

## 2. Memory and search

- Add geometry observations, stable relevant-anchor admission (at most 3 current anchors), evidence promotion and temporal episode storage.
- Merge adjacent support, close episodes only from trusted updates, retain last trusted context on loss, and create snapshots only for state/relation/context events.
- Generate lifetime view and ranked search candidates by last physical location, last context, previous stable context, older trusted context; exclude HELD_BY from location results.

## 3. Regression validation

- Add the 18 specified regression cases and boundary cases for future evidence, causal reconfirmation, rejected same-frame phones, loss without physical evidence, and snapshot immutability.
- Run `.venv/Scripts/python.exe -m pytest tests/test_v27_memory.py -q`.

## 4. Seven-video outputs and freeze

- Add CLI scripts to replay existing evidence and render relation-node Mermaid/PNG graphs.
- Run `scripts/run_v27.py` and `scripts/render_v27_graphs.py` on test3–test9 only, then hash all predictions and visuals.
- Keep physical uncertainty explicit; missing box/depth/interaction evidence is a limitation, never a synthetic relation.

## 5. Evaluation and report

- Only after freeze, evaluate the supplied narrative in `scripts/evaluate_v27.py`.
- Produce each video's evaluation and all 15 requested report answers in `outputs_v27/V27_REPORT.md`.
- Inspect representative graph PNGs, validate unchanged input hashes, and stop.
