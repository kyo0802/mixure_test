# Phase 6 bounded implementation

Closeout: the initial 21-call normalized-coordinate diagnostic exposed a coordinate contract problem. A separate explicit-pixel run processed the same 21 frames. Total 42 Qwen generations, not 21; both attempts retained, no reinterpretation of diagnostic outputs. Final results and limitations: LATEST_REPORT.md.

2026-10-21. Reuse Phase 5 Graph/search, existing Qwen7 NF4 and SAM2.1 small. No benchmark rerun, training, production writes, commit or push.

Scope: 21 original frames across nine videos. Inspection examples may select frames, never coordinates or answers. Remaining frames selected from existing metadata coverage gaps. One Qwen localization call per frame; raw outputs immutable. Sequential SAM image refinement, no unsupported cross-frame propagation. Estimated Qwen GPU use 8–11 GiB, existing 10 GiB free GPU / 8 GiB available RAM load gates. SAM runs after Qwen unload. No new model download.

Implement `target_surface.py` (CPU contracts, geometry and memory integration), `perception_runtime.py` (existing model reuse), `run_phase6_demo.py` (one CLI, stage receipts), and focused tests. Compare Phase 5 and Phase 6 on exactly the selected frames. Review output overlays separately from runtime; do not use GT/review answers in inference.

Report to WORKSPACE/VLMtest/LATEST_REPORT.md with authoritative artifacts/phase6 output. WORKSPACE/VERSION_STATUS.md does not exist; actual status entry is WORKSPACE/VLMtest/VERSION_STATUS.md.
