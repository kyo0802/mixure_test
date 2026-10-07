# Molmo Runtime Recovery Implementation Plan

> **For agentic workers:** Execute inline; latest user explicitly authorizes fixing Molmo until measurable. Preserve prior failed V2946 freeze and do not access validation.

**Goal:** Repair NF4 vision dtype and run a separately recorded, identical nine-pack benchmark.

**Architecture:** Keep original failed source/output hashes unchanged. Add a recovery subclass using official BitsAndBytesConfig exclusion for patch_embedding and existing lm_head; all other NF4/BF16/SDPA settings, images and prompts stay unchanged. Prove full six-image forward finite before starting generation; freeze fresh nine predictions and then reuse evaluation labels/validator.

**Tech Stack:** Existing transformers4.57.6/torch2.10CUDA/bitsandbytes0.50.2, same official Molmo revision, isolated outputs_v2946/runtime_recovery.

---

Files: create `src/memory_graph/v2946/recovery.py`, `scripts/run_v2946_recovery.py`, `tests/test_v2946_recovery.py`; no edits to frozen original sources.

- [x] Add quantization config test: `quantization().llm_int8_skip_modules == ['lm_head','patch_embedding']` and NF4/double/BF16 unchanged; run failing test before implementation.
- [x] Implement subclass loader with those exclusions. Assert patch_embedding is torch.nn.Linear with floating BF16 weight, rest contains Linear4bit and official vision dtype is floating. No model code monkeypatch.
- [x] Process exact first event's six frozen images and same text, call full `model(...,use_cache=False,logits_to_keep=1)` once; require finite logits, record norm input dtype and zero generated/decoded answers. If infrastructure still fails, diagnose before any canonical generation.
- [x] Save user reauthorization, identical benchmark/request/hash verification and preserved failed-run artifact snapshot. Start separate nine-generation run only after preflight success, no Qwen rerun, no semantic prompt edits/retries.
- [x] Reparse/revalidate and freeze raw/parsed/runtime/config/source SHA before reviewing predictions. Use same V2945 labels and 5/4 strata; no GT inference input or actual memory writes.
- [x] Focused recovery and full required prior suites, full regression retaining exactly three known historical hash failures. Write updated Chinese reports at recovery output root; conditional validation handoff only if supported by actual results.
- [x] Verify original failed run and historical inputs/sources/reports unchanged; seal recovery review/report hashes, stop after measurable comparison.

## Completion

2026-10-01: Official NF4 patch_embedding exclusion repaired full forward and nine successful EOS generations. Original failed run/source/output freeze remains unchanged. Primary27/source12/review34 hashes verified. Focused272 passed; full565 passed, same3 historical failures and1skip. Eligible Qwen/Molmo event0/1, actor1/1, release4/1, visibility1/1, finalrelation3/0 (each denominator5). Molmo unsafe proposals prevented integration; select frozen Qwen for one held-out evaluation under user readiness criteria, not deployment. No validation media accessed. Reports and Qwen handoff completed; stop.
