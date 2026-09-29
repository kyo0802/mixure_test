# V2.9.2 Canonical Pipeline Implementation Plan

> **For agentic workers:** implement inline from this user-authorized plan, completing and checking each task in order.

**Goal:** Create one fresh raw-video V2.9.2 path that validates cross-module identity, mask, event, memory, VLM and physical-gate contracts on all nine videos.

**Architecture:** Reuse the existing YOLO11s, local tracker, SAM2.1, MobileNetV3, V2.6 Identity Guard, V2.9 relation gate and V2.8 search policy behind a canonical run context. Persist identity/relation events once, then derive timeline, registry, memory, search and visualizations from those events.

**Tech Stack:** Python 3.12, PyTorch/CUDA, OpenCV, Ultralytics, official SAM2.1, Transformers Qwen2.5-VL-3B, pytest, SHA-256 manifests.

---

## Scope and immutable inputs

Create only `src/memory_graph/v292/`, `scripts/run_v292.py`, a V2.9.2 config, and `outputs_v292/` for implementation and benchmark artifacts. Historical outputs `outputs_v21/` through `outputs_v291/` and sibling `mixure_test/` are read-only. Existing reports and manual notes may only be consulted after prediction freeze. Raw input map: `task1=test1.mp4`, `task2=test2.mp4`, plus `test3.mp4`…`test9.mp4`.

## Planned modules

- `src/memory_graph/v292/contracts.py`: typed identity authorization, state transitions, canonical anchor IDs, event and episode records.
- `src/memory_graph/v292/masks.py`: single trusted-mask authorization and resolvable frame/video/object references.
- `src/memory_graph/v292/events.py`: per-loss recovery, placement/event selection and complete-coverage cache validation.
- `src/memory_graph/v292/vlm_pairs.py`: one target/anchor/event visualization, pair-specific temporal frame choice and grounding validation.
- `src/memory_graph/v292/physical.py`: pair-specific geometry adapter into existing V2.9 physical gate.
- `src/memory_graph/v292/memory.py`: one authoritative event store and derived temporal/lifetime/local/search views.
- `src/memory_graph/v292/pipeline.py`: raw-video RunContext and one canonical stage order, same for all videos.
- `configs/v292_canonical.yaml`, `scripts/run_v292.py`, and focused `tests/test_v292_*.py`.
- `outputs_v292/`: stage checkpoints with canonical signatures, per-video artifacts, validators, prediction freeze, evaluations and report.

## Tasks and gates

### Task 1: Freeze scope and create config/run context

- [ ] Record available raw clips, mainline checkpoints, current GPU/runtime and source hashes.
- [ ] Define one canonical config hash and `RunContext`; make the runner accept one raw file, video ID and output folder without opening prior-version prediction artifacts.
- [ ] Add tests for nine source paths, identical config serialization and historical-output path rejection.

### Task 2: Identity authorization and state contract

- [ ] Add a single identity vocabulary for visible, lost, propagation resumed, detection resumed, confirmed, provisional, ambiguous and rejected.
- [ ] Represent confirmation with video/frame/candidate, similarity, competitor, semantics, contradiction, mask-quality, guard decision and provenance.
- [ ] Make only a guard authorization create `IDENTITY_CONFIRMED` and `MATCHED`; derive timeline and registry transitions from the event record.
- [ ] Add propagation-only, detector-only, authorized confirmation, missing-authorization and registry/timeline consistency tests.

### Task 3: One mask authorization and provenance path

- [ ] Reuse one function in all videos, requiring mask existence/decodability, matching video/frame/object, identity state, continuity, drift/conflict and explicit reacquisition authorization.
- [ ] Keep all mask references resolvable to stored RLE and authorization records; never infer a per-frame mask from a candidate's session-level seed.
- [ ] Add mismatch, missing RLE, decode failure, unauthorized SAM, drift and future-only-after-confirmation tests.

### Task 4: Events, recovery episodes and dense cache

- [ ] Detect repeated loss/recovery episodes from canonical states; keep propagation resumed distinct from identity reconfirmation.
- [ ] Store candidates, actual mask availability, appearance/competitor evidence and decisions within each loss episode.
- [ ] Reuse dense cache only for a covering interval and exact video/config/source signature; otherwise rerun the full requested interval.
- [ ] Test both interval-bound failures, stale signatures, second loss, no retroactive trust and common event/placement stages for all nine videos.

### Task 5: Anchors and pair-grounded VLM

- [ ] Namespace local anchors with video + event + local ID and carry the same ID through every artifact.
- [ ] Pick BEFORE/DURING/AFTER frames for the exact pair where authorized target and queried anchor are visible; emit `EVIDENCE_UNAVAILABLE` otherwise.
- [ ] Render only one queried anchor as highlighted and label both IDs; validate subject, pair, frame applicability and grounding, rejecting wrong-subject but valid JSON.
- [ ] Test pair isolation, missing target/anchor evidence, schema and grounding outcomes.

### Task 6: Physical gate and authoritative memory

- [ ] Compute distance, overlap, containment and ordered approach/boundary/visibility/release evidence against the queried anchor only.
- [ ] Adapt facts into the existing V2.9 relation-specific gate; preserve its thresholds and all four outcomes.
- [ ] Add positive, candidate, uncertain and counterevidence fixtures.
- [ ] Store real frame-derived times, support IDs, status and provenance once; derive temporal, lifetime, sparse local graph, search and plots from the same store.
- [ ] Fail on unauthorized MATCHED, placeholder times, bad status transitions, graph pollution, namespace collision or broken provenance round-trip.

### Task 7: Confirmed recovery feedback loop

- [ ] On a guard-authorized match, update state at the exact frame, update registry forward, seed SAM2.1 at the current candidate observation and permit future guarded appearance/memory updates.
- [ ] Never retroactively authorize the prior loss interval; start a fresh recovery episode after later loss.
- [ ] Add future-only reinitialization, repeated-loss and later-mask trust tests.

### Task 8: Focused test release gate

- [ ] Run all V2.9.2 focused tests; do not launch model inference until all pass.
- [ ] Run path/config/stage-sequence tests against all nine video IDs and verify no historical predictions are read by canonical stages.
- [ ] Stop at this gate if a correctness defect remains and fix a general rule, not video-specific frames or IDs.

### Task 9: Fresh nine-video benchmark

- [ ] Run sequentially from all nine raw videos through the exact same ordered stages and config.
- [ ] Persist signature-checked checkpoints and per-stage timing/errors; do not consult manual labels during inference.
- [ ] Produce requested JSON, graphs and debug video where runtime/storage permits; report explicit failures without substituting historical artifacts.

### Task 10: Freeze, evaluate and report

- [ ] Hash source, canonical config, model identifiers/checkpoints and raw input videos; hash all prediction artifacts before manual evaluation.
- [ ] Validate all nine manifests agree on pipeline, models, policy, prompt, gate and memory schema; reject historical-prediction dependencies, orphan masks, bad identity states/timestamps and broken evidence references.
- [ ] Verify historical output trees unchanged where practical; keep known historical hash failures separate from V2.9.2 regressions.
- [ ] Only after freeze, review existing manual references and write per-video/aggregate metrics, test8/test9 findings, comparison table and `outputs_v292/V292_REPORT.md`.
- [ ] End with exactly one required V2.9.2 result classification, then stop.

## Verification commands

- Focused: invoke the configured project pytest on `tests/test_v292_*.py`; require zero failures before inference.
- Canonical smoke: invoke `scripts/run_v292.py` for one raw video and verify its stage artifacts, then run all nine sequentially with the same config hash.
- Release: run the canonical consistency validator and prediction manifest verifier before post-freeze evaluation; run the complete existing test suite after focused tests.

## Acceptance

Follow the V2.9.2 user prompt Sections 26–32 exactly. A single passed unit gate does not imply model success: the final status depends on nine fresh raw runs, contract validation, manifest verification and the post-freeze regression review.
