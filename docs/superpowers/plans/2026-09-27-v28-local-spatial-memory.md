# V2.8 Local Spatial Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and evaluate a target-centered 1–2 hop spatial memory that can preserve physical-relation hypotheses without weakening identity safety or changing V2.7.

**Architecture:** Reuse the frozen V2.7 input adapter and entity observation model, then perform an offline causal replay into a new V2.8 store. A local-graph builder admits stable Hop 1 anchors and Hop 2 anchor context, while a separate temporal reasoner calculates geometry features and applies relation-specific hard gates. One episode/event store generates temporal, lifetime, final-local-subgraph, and search views.

**Tech Stack:** Python 3.11, dataclasses, JSON, Matplotlib/Pillow, pytest; frozen V2.6 observations and V2.7 helpers.

---

## File map

- Create `src/memory_graph/v28/models.py`: V2.8 config and candidate/edge records.
- Create `src/memory_graph/v28/geometry.py`: complete bbox temporal feature extraction.
- Create `src/memory_graph/v28/roles.py`: deterministic label-to-role compatibility.
- Create `src/memory_graph/v28/local_subgraph.py`: stable Hop 1/Hop 2 admission and connected graph construction.
- Create `src/memory_graph/v28/physical_reasoner.py`: temporal patterns and relation-specific hard gates.
- Create `src/memory_graph/v28/memory.py`: event snapshots, lifetime history, loss retention.
- Create `src/memory_graph/v28/search_planner.py`: five-rule graph search order.
- Create `src/memory_graph/v28/pipeline.py`: frozen replay, evidence audit, output/freeze validation.
- Create `src/memory_graph/v28/visualization.py`: readable relation-node PNG and Mermaid rendering.
- Create `scripts/run_v28.py`, `scripts/render_v28_graphs.py`, `scripts/evaluate_v28.py`: inference, rendering/freeze, and isolated post-freeze evaluation.
- Create `tests/test_v28_memory.py`: the 32 required behavior and regression boundaries.
- Create `outputs_v28/**`: seven-video artifacts, freeze manifest, evaluation, and report.
- Preserve `src/memory_graph/v27/**`, `outputs_v27/**`, and sibling `mixure_test` byte-for-byte.

### Task 1: Evidence and model boundaries

**Files:**
- Create: `src/memory_graph/v28/models.py`
- Create: `src/memory_graph/v28/roles.py`
- Test: `tests/test_v28_memory.py`

- [ ] **Step 1: Write role and identity boundary tests**

```python
def test_hop0_is_always_present():
    assert empty_graph()["nodes"][0]["entity_id"] == "phone_01"

def test_person_requires_interaction_evidence():
    assert semantic_role("person") == "INTERACTION_AGENT"
    assert not interaction_admissible("person", evidence=[])
```

- [ ] **Step 2: Run the boundary tests and verify failure**

Run: `.venv\Scripts\python.exe -m pytest tests\test_v28_memory.py -q`
Expected: collection/import failure because V2.8 does not exist.

- [ ] **Step 3: Add immutable configuration and deterministic semantic roles**

```python
ROLE_LABELS = {
    "SUPPORT": {"table", "dining table", "desk", "counter", "shelf"},
    "CONTAINER": {"box", "bag", "container", "drawer"},
    "INTERACTION_AGENT": {"person", "hand"},
}

def semantic_roles(label: str) -> list[str]:
    return [role for role, labels in ROLE_LABELS.items() if label.casefold() in labels] or ["LANDMARK"]
```

- [ ] **Step 4: Run the focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests\test_v28_memory.py -q`
Expected: new role/model tests pass.

### Task 2: Geometry and temporal physical reasoning

**Files:**
- Create: `src/memory_graph/v28/geometry.py`
- Create: `src/memory_graph/v28/physical_reasoner.py`
- Modify: `tests/test_v28_memory.py`

- [ ] **Step 1: Add tests that image relations never directly promote physical truth**

```python
@pytest.mark.parametrize("image_relation,physical", [
    ("IMAGE_NEAR", "NEAR"), ("IMAGE_ABOVE", "ON"),
    ("IMAGE_OVERLAP", "INSIDE"), ("IMAGE_OVERLAP", "OCCLUDED_BY")])
def test_image_geometry_alone_does_not_promote(image_relation, physical):
    decision = reason(segment(image_relation=image_relation), physical)
    assert decision["decision"] != "PROMOTED"
```

- [ ] **Step 2: Add relation-specific pattern tests**

```python
def test_strong_held_pattern_promotes():
    assert reason(held_segment(sync=.96, support=8, independent=True), "HELD_BY")["decision"] == "PROMOTED"

def test_disappearance_alone_is_not_behind():
    assert reason(disappearance_only(), "BEHIND")["decision"] in {"UNCERTAIN", "REJECTED"}
```

- [ ] **Step 3: Implement complete per-frame features and trend summaries**

Calculate IoU, target containment, normalized center position/distance, x/y overlap, target-bottom-to-anchor-top, relative size, bbox visibility proxy, overlap/distance trends, and target/anchor velocities. Record `mask_evidence_available=false` when no mask reference exists rather than substituting bbox area as mask evidence.

- [ ] **Step 4: Implement hard gates for HELD_BY, ON, INSIDE, OCCLUDED_BY, BEHIND, and NEAR**

Each output contains the exact schema fields `target`, `anchor`, `candidate_relation`, frame interval, identity state, geometry/temporal/semantic/VLM evidence, decision, reason, source observations, and source snapshots. A missing semantic role, temporal pattern, identity authorization, independent physical signal, or VLM support where required yields CANDIDATE/UNCERTAIN/REJECTED.

- [ ] **Step 5: Run physical-reasoning tests**

Run: `.venv\Scripts\python.exe -m pytest tests\test_v28_memory.py -q`
Expected: image-leak, candidate, promotion, BEHIND/OCCLUDED separation, and identity tests pass.

### Task 3: Target-centered local subgraph

**Files:**
- Create: `src/memory_graph/v28/local_subgraph.py`
- Modify: `tests/test_v28_memory.py`

- [ ] **Step 1: Add connectedness, capacity, and provenance tests**

```python
def test_hop2_has_primary_path():
    graph = build_fixture_graph()
    assert all(any(e["source"] == n["via_primary"] for e in graph["edges"])
               for n in graph["nodes"] if n["hop"] == 2)

def test_graph_does_not_expand_to_full_scene():
    assert len(build_noisy_fixture(100)["nodes"]) <= 10
```

- [ ] **Step 2: Implement temporal segment formation**

Group distinct-frame observations with no gap over 0.65 seconds. Require at least 3 frames and 0.35 seconds. Same-frame duplicates count once.

- [ ] **Step 3: Implement deterministic Hop 1 admission**

Require trusted target/anchor, a useful semantic role, a stable target-anchor segment, and a local image relation. Keep at most three using recency, duration, stability, then entity ID.

- [ ] **Step 4: Implement deterministic Hop 2 expansion**

For each admitted primary, require stable multi-frame primary-context support and a useful localization role; exclude unrelated co-visible objects and interaction agents without interaction evidence. Keep at most two per primary, include `via_primary`, and ensure every node has a path of length at most two from `phone_01`.

- [ ] **Step 5: Run local graph tests**

Run: `.venv\Scripts\python.exe -m pytest tests\test_v28_memory.py -q`
Expected: Hop 0/1/2, no-full-scene, no-unrelated-node, and person safety tests pass.

### Task 4: Memory and search views

**Files:**
- Create: `src/memory_graph/v28/memory.py`
- Create: `src/memory_graph/v28/search_planner.py`
- Modify: `tests/test_v28_memory.py`

- [ ] **Step 1: Add event snapshot and search tests**

```python
def test_unobserved_retains_local_subgraph():
    memory = replay_fixture()
    assert memory.target["state"] == "UNOBSERVED"
    assert memory.last_trusted_local_subgraph["nodes"]

def test_candidate_is_labeled_unconfirmed():
    row = find(candidate_memory())["candidates"][0]
    assert row["priority_rule"] == 3 and row["confirmed"] is False
```

- [ ] **Step 2: Implement one event/episode store**

Generate snapshots only for target state changes, primary/context changes, physical candidate/promotion/end, and interactions. On loss, deep-copy the last trusted connected local graph; preserve ENDED/STALE episodes.

- [ ] **Step 3: Implement five search priorities**

Order LAST_TRUSTED promoted INSIDE/BEHIND/ON, other promoted useful relations, candidate physical hypotheses, last trusted image context, then recent ended/stale context. Exclude HELD_BY/person as a location and attach Hop 2 localization context to its primary anchor result.

- [ ] **Step 4: Run memory/search tests**

Run: `.venv\Scripts\python.exe -m pytest tests\test_v28_memory.py -q`
Expected: last-memory, candidate wording, physical priority, Hop 2 context, and HELD_BY exclusion pass.

### Task 5: Frozen seven-video replay and evidence audit

**Files:**
- Create: `src/memory_graph/v28/pipeline.py`
- Create: `scripts/run_v28.py`
- Modify: `tests/test_v28_memory.py`

- [ ] **Step 1: Add leakage and historical-output tests**

Parse inference modules with `ast` and reject imports/text referencing evaluation, GT, narrative, or video-specific branches. Hash `outputs_v27/prediction_manifest.json` plus every file in its manifest before/after V2.8.

- [ ] **Step 2: Implement Stage A audit**

For each test3–test9, report trusted target frames, primary candidates, per-anchor co-visible frames and maximum continuous support, mask availability, placement-transition evidence, VLM availability, and `EVALUABLE`/`INSUFFICIENT_EVIDENCE` with reasons.

- [ ] **Step 3: Implement replay outputs**

Write all required per-video JSON/text files and aggregate `summary.json` plus `evidence_availability_summary.json`. Use only V2.6 frozen observations through the V2.7 authorization adapter; do not load perception models.

- [ ] **Step 4: Execute seven-video replay**

Run: `.venv\Scripts\python.exe scripts\run_v28.py`
Expected: test3–test9 all complete and `outputs_v27` hash verification passes.

### Task 6: Readable visualization and freeze

**Files:**
- Create: `src/memory_graph/v28/visualization.py`
- Create: `scripts/render_v28_graphs.py`

- [ ] **Step 1: Render entity → relation → entity graphs**

Create per-stage PNG/MMD, temporal overview, lifetime, search, and final local subgraph. Relation nodes carry relation/status/time while edges have no dense labels. Use left-to-right stage layout, separate shapes, enough spacing, and faded candidate/ended styles.

- [ ] **Step 2: Inspect all outputs for clipping and connectedness**

Run: `.venv\Scripts\python.exe scripts\render_v28_graphs.py`
Expected: every test has required PNG/MMD files and no disconnected node in JSON.

- [ ] **Step 3: Freeze predictions and code**

Run: `.venv\Scripts\python.exe scripts\render_v28_graphs.py --freeze`
Expected: `outputs_v28/prediction_manifest.json` hashes inference outputs, figures, and V2.8 source before narrative evaluation.

### Task 7: Post-freeze evaluation and report

**Files:**
- Create: `scripts/evaluate_v28.py`
- Create: `outputs_v28/V28_REPORT.md`

- [ ] **Step 1: Verify freeze before reading narrative mappings**

`evaluate_v28.py` calls `verify_freeze()` first and keeps all test3–test9 narrative text in the evaluation script only.

- [ ] **Step 2: Produce per-video and aggregate evaluation**

Report graph quality, physical candidate/promotion/uncertain counts, obvious false promotions, unauthorized updates, direct image-to-physical leaks, disconnected/irrelevant nodes, and search result categories. Write `evaluation.json` per video and `evaluation_summary.json` globally without modifying frozen inference outputs.

- [ ] **Step 3: Write the 16-question report**

Include concrete Hop counts, exact relation decisions/evidence, V2.7 comparison, post-freeze test3–test9 findings, visual review, safety, limitations, and the real bottleneck. State that a candidate is not a correct location.

- [ ] **Step 4: Run all regression gates**

Run: `.venv\Scripts\python.exe -m pytest tests\test_v27_memory.py tests\test_v28_memory.py -q`
Expected: all V2.7 and V2.8 tests pass.

Run: `.venv\Scripts\python.exe scripts\evaluate_v28.py`
Expected: frozen files/source and V2.7 historical hashes remain valid.

- [ ] **Step 5: Stop at V2.8**

Do not start V2.9, new VLM/model downloads, SAM/Re-ID experiments, SLAM, 3D reconstruction, GNN work, or training.
