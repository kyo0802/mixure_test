# Pass I DEV Pilot Audit Implementation Plan

> **For agentic workers:** Execute these steps inline in the current workspace. Keep the pilot scope fixed at 40 DEV items.

**Goal:** Compare GPT and completed human labels, write the audit, and expose manual disagreement flags in Streamlit.

**Architecture:** Read the frozen pilot manifest, existing GPT drafts, and pilot human SQLite rows. Calculate counts from reviewed rows only, list exclusions separately, and keep manual adjudication in a separate pilot-only SQLite table. The UI reuses existing evidence images and writes only the adjudication flag.

**Tech Stack:** Python, Pillow, SQLite, Streamlit.

---

- [x] Add `src/memory_graph/pass_i/dev_pilot_audit.py` to load only manifest-listed DEV items, compute the matrix and challenge-tag strata, extract crop paths and dimensions, store manually chosen flags, and render `artifacts/pass_i/reports/PASS_I_DEV_PILOT_AUDIT.md`.
- [x] Add `scripts/report_pass_i_dev_pilot_audit.py` as a report entry point. Run it with `.venv/Scripts/python.exe scripts/report_pass_i_dev_pilot_audit.py` and inspect the 39 reviewed/1 excluded accounting.
- [x] Add a `Disagreement Review` mode to `scripts/pass_i_annotation_app.py`. Filter to the pilot's GPT/human label disagreements, show both labels and evidence, and save one of `MODEL_ERROR`, `EVIDENCE_INSUFFICIENT`, `DATA_ERROR`, or `UNREVIEWED` only after a human click.
- [x] Confirm that the report contains the 3×3 table, both AMBIGUOUS transition percentages, all false SAME cases, challenge-tag strata, the four AMBIGUOUS→DIFFERENT records with image metadata, and current manual flags. Confirm the prompt hash is unchanged and only DEV pilot inputs are loaded.
