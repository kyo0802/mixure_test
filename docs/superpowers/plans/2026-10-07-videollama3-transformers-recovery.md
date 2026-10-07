# VideoLLaMA3 Transformers Recovery Implementation Plan

> **For agentic workers:** Execute inline in order. Keep all new deployment and smoke artifacts under the isolated VideoLLaMA3 Transformers recovery directories.

**Goal:** Load pinned official VideoLLaMA3-7B through Transformers in a fresh WSL2 environment and complete its strict Stage-0 smoke gate on the RTX 5070 Ti.

**Architecture:** Preserve the existing vLLM/SGLang trials and all v2.10.1 inputs. Create a distinct WSL environment, run one-image, multi-image, bounded video, then the frozen nine-event smoke, and save raw outputs plus strict validation and resource measurements under new recovery paths.

**Tech Stack:** WSL2, Python 3.12, PyTorch/CUDA compatible with RTX 5070 Ti, Transformers 4.46.3, Accelerate 1.0.1, FlashAttention 2, official `DAMO-NLP-SG/VideoLLaMA3-7B` custom code, existing v2.10.1 schema and semantic validator.

---

### Task 1: Freeze the exact inputs and inspect official loader metadata

**Files:**
- Read: `artifacts/v2.10.1/smoke/input_manifest.json`
- Read: `artifacts/v2.10.1/deployment/videollama3/config.json`
- Create: `artifacts/v2.10.1/deployment/videollama3_transformers/`
- Create: `artifacts/v2.10.1/smoke/videollama3_transformers/`

- [x] Verify the nine event records, all referenced frame/video hashes, exact model revision, GPU availability and free VRAM.
- [x] Inspect the pinned snapshot's `auto_map`, processor registration, weight filenames and official inference signature. Do not alter the frozen input manifest or prior engine logs.

### Task 2: Create and characterize the isolated environment

**Files:**
- Create: `artifacts/v2.10.1/deployment/videollama3_transformers/config.json`
- Create: `artifacts/v2.10.1/deployment/videollama3_transformers/environment.json`
- Create: `artifacts/v2.10.1/deployment/videollama3_transformers/optimization_trials.json`

- [x] Build a fresh WSL virtual environment without modifying existing vLLM/SGLang environments; pin the preferred Transformers and Accelerate versions and a compatible PyTorch/CUDA build.
- [x] Verify CUDA visibility, FlashAttention import/kernel path, and custom model class import; record exact versions, device, disk/VRAM and trial errors.

### Task 3: Prove loader and select a stable precision

**Files:**
- Create: `scripts/run_videollama3_transformers_recovery.py`
- Write: `artifacts/v2.10.1/deployment/videollama3_transformers/optimization_trials.json`

- [x] Attempt BF16 as a bounded diagnostic. If memory is insufficient, try supported 8-bit and then NF4 4-bit with BF16 compute; never make CPU offload the final configuration.
- [x] Use only batch one, context at most 4096, max 128 output tokens, original or downscaled images, FlashAttention 2, and resource sampling. Select a configuration only after image and video generation work.

### Task 4: Run staged multimodal smoke tests

**Files:**
- Write: `artifacts/v2.10.1/smoke/videollama3_transformers/responses.json`
- Write: `artifacts/v2.10.1/smoke/videollama3_transformers/runtime.json`

- [x] Test one image, then the existing safe two-image input with order preserved.
- [x] Test the same frozen temporal inputs at no more than 3 frames first, then no more than 8 frames if stable; record selected frames and timestamps.
- [x] Stop and record the blocking failure if basic image generation cannot complete without OOM or crash.

### Task 5: Run and report the nine-event Stage-0 gate

**Files:**
- Write: `artifacts/v2.10.1/smoke/videollama3_transformers/responses.json`
- Write: `artifacts/v2.10.1/smoke/videollama3_transformers/runtime.json`
- Create: `artifacts/v2.10.1/reports/VIDEOLLAMA3_RECOVERY_REPORT.md`

- [x] Reuse exactly the frozen nine event inputs; save unmodified raw responses, per-request completion/JSON/schema/semantic results, runtime, frame counts, peak GPU memory, OOM and errors.
- [x] Mark Stage-0 PASS only when every gate in the user prompt is met; otherwise mark FAIL and report the precise blocker. State whether the candidate is ready for Pass I/T without modifying benchmark logic.
- [x] Confirm prior vLLM/SGLang files and protected subsystems remain untouched.
