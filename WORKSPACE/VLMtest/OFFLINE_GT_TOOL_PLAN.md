# Offline Human GT Tool Implementation Plan

> **For agentic workers:** Execute inline in the existing repository. The user requests a working tool now; no handoff, worktree, commit, or inference.

**Goal:** Deliver a standalone, model-blind Traditional Chinese annotation application and an owner-side provenance-preserving consolidation utility.

**Architecture:** Classic JavaScript and local HTML5 video; a generated script embeds verified source metadata. Versioned JSON exports are portable submissions; localStorage is best-effort. Python owner tooling validates the same schema, preserves original submissions and prepares explicit adjudication rather than voting.

**Tech Stack:** HTML/CSS/JavaScript, Python standard library; existing PyAV only for owner-side packaging verification.

## Tasks

- [x] Build package: nine original hashes, 9,958 decoded frames, unchanged H.264 copies, generated metadata and ZIP.
- [x] Build classic JS and Python contracts for reviewer/session/source/time/evidence/coverage validation.
- [x] Build standalone Traditional Chinese UI with event/state editing, coverage, backup/export/import and native PTS navigation disclosure.
- [x] Build provenance-preserving owner collection, duplicate/revision/conflict handling and explicit adjudication/finalization.
- [x] Pass 45 isolated Node/Python checks; no test labels used as GT.
- [x] Verify all nine source hashes and final 21-entry ZIP contents. Agent file browser remains policy-blocked; human reports successful playback, annotation and JSON round trip. Detailed manual checklist remains available without invented checkmarks.
- [x] Publish report, current decisions and fixed navigation in WORKSPACE/VLMtest.

## Acceptance boundary

No new model calls, historical GT changes, Memory Graph writes, automatic human labels, commit or push. No server, local fetch, ES module, CDN or reviewer runtime installation. A finished review with limitations is distinct from exhaustive event eligibility; uncertainty cannot silently become a negative.
