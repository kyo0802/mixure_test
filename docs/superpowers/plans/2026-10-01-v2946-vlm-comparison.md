# V2946 Frozen VLM Comparison Implementation Plan

> **For agentic workers:** Execute inline, task by task. No additional agents or historical edits.

**Goal:** Compare official Molmo2-O-7B once against frozen Qwen V2945, then select a development candidate and document validation readiness without touching held-out media.

**Architecture:** Reuse exact V2945 request text, event manifests, PNG paths and hashes. A separate official multi-image Molmo adapter feeds the unchanged V2945 parser/validator. Freeze nine raw predictions and source hashes before scoring against existing review labels; simulate memory only.

**Tech Stack:** Python 3.12 bundled executable plus existing project site-packages, transformers, torch CUDA, bitsandbytes NF4, official revision-pinned remote code, pytest.

---

### Task 1: Evidence and model preparation

Files: create `src/memory_graph/v2946/{common,pipeline}.py`, `scripts/run_v2946.py`, `outputs_v2946/benchmark/`.

- [ ] Verify frozen V2945 primary/review and upstream manifests with `memory_graph.v2945.freeze.verify()` and `memory_graph.v2945.common.protected()`.
- [ ] Build `benchmark()` returning only `(events, requests, rendering)` from exact explicit frozen manifest paths. Reject any ID/marker/frame/phase/image/prompt hash mismatch with `BENCHMARK_INPUT_MISMATCH`.
- [ ] Resolve official HF revision, download only that revision into `outputs_v2946/.model`, verify file size and upstream LFS SHA256; inspect downloaded Python source before trust-remote-code loading.

### Task 2: Interface and consistency tests

Files: create `src/memory_graph/v2946/model.py`, `tests/test_v2946_comparison.py`.

- [ ] Write tests for `benchmark()` equality, exact prompt and image order, no added anchors, enum identity, NONE/UNCERTAIN, invalid anchors, seven-key JSON and no geometry/citations, unchanged evaluation reference, no graph writes and no media discovery.
- [ ] Run `pytest tests/test_v2946_comparison.py` before implementing adapter; missing module must fail.
- [ ] Adapter uses `AutoProcessor` and `AutoModelForImageTextToText`, official ordered PIL image message parts and unchanged frozen prompt. Load NF4 double/BF16, SDPA if supported, all CUDA. Greedy generation, 1400 tokens/120 seconds, no canonical probes or retries. Store input tensor shapes, processor config, token/EOS trace and Monitor peaks.
- [ ] Run focused tests. Packaging tests use synthetic images/mock processor, not development inference.

### Task 3: Canonical execution and immutable prediction freeze

Files: create `src/memory_graph/v2946/freeze.py`, primary outputs under `outputs_v2946/molmo/`.

- [ ] `prepare()` records protected hashes and exact task sources before inference. `run()` checks them and uses a start marker refusing replay. Nine fresh Molmo calls only; Qwen calls zero.
- [ ] Save raw text, parsed JSON, unchanged validator results, model/runtime measurements and checkpoint/input provenance.
- [ ] `freeze()` independently re-parses raw and re-validates, verifies protected before/after, hashes artifacts plus all new source/test files. Review module not imported by prepare/run.

### Task 4: Post-freeze comparison and engineering visual review

Files: create `src/memory_graph/v2946/evaluation.py`, `comparison/`, `review/`, `benchmark/eligibility_reference.json`.

- [ ] Load frozen V2945 admissible-values review and eligibility only after freeze. Score all parsed predictions including invalid outputs, preserve 5 eligible/4 insufficient and indeterminate event values.
- [ ] Review all nine frozen contact sheets, record references without silently editing old labels. Use `REVIEW_REFERENCE_DISAGREEMENT` with both interpretations if needed.
- [ ] Report per-field paired counts, anchor category counts, complete event/relation distributions, underclaim/overclaim, appropriate NONE/UNCERTAIN, false real relations and unchanged simulated memory rules. Count actual graph/identity writes zero.
- [ ] Compare recorded load/inference/tokens/EOS/VRAM/RSS to frozen Qwen; no weighted score. Select candidate/readiness from eligible event+anchor improvement and safety, not diversity.

### Task 5: Regression, Traditional Chinese reports and handoff

Files: create `src/memory_graph/v2946/reports.py`, regression outputs, `V2946_PROGRESS_REPORT.md`, `V2946_REPORT.md`; conditional `VALIDATION_HANDOFF.md`.

- [ ] Run focused V2946/V2945/V2944/V2943/V293/V292 tests and full suite; preserve exactly the existing three historical hash failures and skip. Use `PYTHONDONTWRITEBYTECODE=1`, output-local pytest cache/temp/JUnit.
- [ ] Verify .60/.10 identity parameters and existing fusion/memory/recovery/unresolved/IDENTITY_ONLY/17 placement protections via unchanged frozen upstream artifacts and focused tests; no validation media inventory/open/decode.
- [ ] Report all 15 requested Chinese sections with factual source-linked per-event findings, sample/reviewer limitations and one exact next step. If selected candidate is ready, write model/revision/processor/parameters/schema/memory/one-run/postfreeze/no-tuning validation protocol without implementing or executing validation.
- [ ] Seal additive review/report hashes, verify primary+source+review+upstream integrity, finish and stop. No Git mutation: repository metadata is read-only.
