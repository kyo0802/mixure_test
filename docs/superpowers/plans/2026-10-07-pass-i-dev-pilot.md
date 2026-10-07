# Pass I DEV Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a fixed-prompt GPT-6.1 Sol pilot on 40 existing DEV pairs and prepare blind-first human review.

**Architecture:** Validate existing artifacts without rebuilding them. Freeze the supplied prompt and deterministic pilot selection; send whitelisted image requests through authenticated local Codex app-server. Preserve raw responses before strict parsing and keep pilot annotations in a separate store.

**Tech Stack:** Existing Python/Pillow/Streamlit/pytest, Codex app-server JSON-RPC.

---

- [x] Verify existing hashes, numbering, metadata boundary and UI.
- [x] Extract exact supplied prompt between markers; save prompt/schema/hash manifest.
- [x] Select 40 DEV pairs and 6 blind-first items using fixed seed and available sampling strata.
- [x] Implement app-server transport with exact base instructions, fresh ephemeral threads, data-URI images and disabled browsing/shell/apps; record request audits.
- [x] Persist each raw completion before parsing; invalid outputs remain PRELABEL_PARSE_FAILED without repair.
- [x] Compute review priority deterministically; implement Pilot review scope with separate annotation storage and blind-first reveal gate.
- [x] Test deterministic selection, DEV-only transport, request sanitization, strict parsing, priority and blind-first UI controls.
- [x] Execute every pilot request, report counts/runtime, verify unchanged dataset/split/V297 hashes and stop before frozen inference.

Execution is inline. No dataset rebuild, gold freeze, identity changes or other-model benchmarks.
