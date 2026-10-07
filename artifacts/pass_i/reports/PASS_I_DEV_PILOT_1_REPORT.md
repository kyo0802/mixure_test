# Pass I DEV Pilot 1 Report

Status: **PASS_I_PILOT1_READY_FOR_HUMAN_REVIEW**

Pilot 1 manifest SHA-256: `1bd2db7e538daf5f22c1e14372a350bb0a26686a15e116ee398de4944605b0a8`.
Prompt: `pass_i_visual_annotator_v1`; SHA-256: `b6057e19de893514fabba7842dbd3a91957fc17e7255c2e9bfb2a3b16dd7b53d` (matches Pilot 0).
CASE_CHANGE_POLICY: `UNKNOWN`.
DEV only. Pilot 0 item IDs and unordered Q/R epoch combinations are disjoint; Frozen items sent: 0.

## Clean pool and selection

- Human QC reviewed epochs at selection: 120.
- Clean DEV pair pool excluding Pilot 0: 390.
- Pilot 1 pairs: 40; PRIMARY_VALID 30; HARD_VALID 10; blind-first 6.
- Session/video composition: test4 8, test7 6, test8 5, val_5 7, val_6 8, val_7 6.

## GPT-6.1 Sol pre-label

- Completed: 40/40.
- Schema-valid: 40/40; invalid: 0.
- Valid labels: SAME 0, DIFFERENT 0, AMBIGUOUS 40.
Raw responses are saved separately before parsing. The model-visible package contains only item ID, case policy, and numbered Q/R crops.

## Human identity review

- Reviewed: 0; excluded: 0; pending: 40.
Open the Streamlit tool → Workflow: Identity Annotation → Dataset scope: DEV Pilot 1. Complete the six blind-first items before revealing their GPT pre-labels.
The Pilot 1 GPT-vs-human table and Pilot 0 descriptive comparison are deferred until human Pilot 1 annotation is complete.
