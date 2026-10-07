# Pass I Evidence QC and Pilot 1 Implementation Plan

> **For agentic workers:** Execute inline; human QC is an explicit checkpoint.

**Goal:** Preserve Pilot 0, make human Evidence QC mandatory, and prepare a clean DEV pool for a fresh Pilot 1.

**Architecture:** Keep existing manifests and Pilot 0 artifacts immutable. Build a deterministic 120-epoch DEV queue from the existing inventory and pair sampling attributes. Store crop and epoch QC in a separate SQLite database; generate cleaned evidence and Pilot 1 only from completed human QC. Keep source-frame overlays entirely inside the QC UI.

**Tech Stack:** Python, SQLite, OpenCV, Pillow, Streamlit.

---

- [x] Implement deterministic DEV-only QC queue and manifest with inventory hash, session diversity, crop size/count diversity, and pair sampling strata.
- [x] Implement crop and epoch QC persistence with exact state validation and resume support.
- [x] Add top-level Streamlit Evidence QC mode with original source-frame bbox overlays, every selected crop, navigation, filters, and Save & Next.
- [x] Add separate QC-cleaned epoch evidence, DEV pair-pool construction, and Pilot 1 selection gates that require human QC and exclude Pilot 0 pairs.
- [x] Write `PASS_I_EVIDENCE_QC_REPORT.md` with current manual-review counts and clean pool availability.
- [x] Verify Pilot 0 prompt/manifest hashes, confirm frozen files are untouched, and report `PASS_I_EVIDENCE_QC_WAITING_FOR_HUMAN` while QC is incomplete.
