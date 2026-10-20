# Qwen Observation Ablation Implementation Plan

**Goal:** Finish four authorized Qwen generations and prepare a small cross-model boundary without new-model execution.

**Architecture:** Preserve A; create B/C output directories and a bounded runner reusing unmodified QwenNF4Runtime. Strict validation and explicitly non-authoritative semantic extraction remain separate. Add the model-neutral adapter interface after the four attempts.

**Tech Stack:** Existing Python, transformers, bitsandbytes NF4, Pillow, jsonschema; official web metadata for candidate compatibility.

- [x] Prepare `scripts/run_phase3_observation_ablation.py`, C prompt/schema and immutable B/C configurations. B uses exactly A prompt/schema and doubles max pixels to401408, subject to CPU processor and hardware checks. C retains200704 pixels and uses a compact state-first contract. Same eight source PNGs, greedy/seed42/1024 tokens, no retries.
- [x] Verify exact PNG hashes, processor dimensions/token accounting, four-call limits and strict-invalid behavior before freezing. Save runtime/asset hashes and preservation baseline. No human-review labels in runtime.
- [x] Run one controller with two sequential condition workers using shared NF4 loading, exactly B/test5,B/test7,C/test5,C/test7. Durable per-call budget markers, raw-first output capture, existing hardware gates and timeouts. Stop affected condition after technical failure; no substitutions or retries.
- [x] After all attempts, compare A/B/C with the same descriptive rubric: target, states, temporal references, event, wrong target, uncertainty, structure. Inspect human evidence only now. Fenced-body extraction may aid qualitative analysis, never strict validity.
- [x] Add `src/memory_graph/experiments/observation_interface.py` and a CPU-only contract test: model-neutral input, adapter load/preprocess/render/generate/resource methods and raw-first capture; no Qwen-specific processor assumptions. No extra model generations.
- [x] Verify official Nemotron Nano V2 VL and VideoLLaMA3-7B identifiers, inputs, licenses and integration limits. Write one combined report plus short compatibility/interface guide. Update WORKSPACE/Pass_T fixed report/navigation and stop. No commit/push.

Scope overrides skill defaults: one existing worktree, inline execution, no new administrative approvals, no extensive tests, no commits. This is development data; no generalization metrics or per-video runtime rules. No constrained decoding in B/C. C changes task and output contract together; JSON validity is not an isolated measure of visual reasoning.
