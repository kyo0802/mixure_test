# SAM 3 Smartphone Concept Supplement Implementation Plan

> Execution: inline in this task; user has already requested completion and final stop.

**Goal:** Measure whether official SAM 3 text prompt `smartphone` produces test8 candidates and stable local IDs over the V2.6.2 sampled windows, without any identity merge.

**Architecture:** A standalone script in this directory reads the frozen test8 window frame lists and video, calls the official SAM 3 video predictor with only a text prompt at each window's first frame, and records every returned local ID and nonempty mask. A separate review of five required frames feeds one contact sheet and a concise report. No files outside this new directory are edited.

**Tech Stack:** Python 3.12, existing isolated `.venv_sam3`, official pinned SAM 3 and `sam3.pt`, OpenCV, NumPy, Pillow.

---

### Task 1: Capture unchanged inputs

- [x] Read test8 frame lists from `outputs_v262/experiment_manifest.json` and hash `test8.mp4`, model checkpoint, and comparison JSON.
- [x] Record that the two independent sessions are f204–f1098 (150 sampled frames) and f804–f1098 (50 sampled frames). Treat their local IDs as separate namespaces.

### Task 2: Run native text detection

- [x] Create `outputs_v262/supplementary_sam3_concept/run_concept.py`.
- [x] Use `build_sam3_predictor(version="sam3")`, `start_session`, `add_prompt(text="smartphone", frame_index=0)`, and `propagate_in_video` for each frozen window.
- [x] Record all output IDs, `out_probs`, masks, bounding boxes, nonempty counts, propagation time, and CUDA peak memory. Do not select or bind an ID to `phone_01`.

### Task 3: Inspect and visualize

- [x] Review f804, f840, f852, f864, and f900 from the f804 session against original frames and all candidate overlays.
- [x] Create one `test8_sam3_concept_contact_sheet.png` showing masks, boxes, IDs, and probabilities for the five required frames plus f924/f942.

### Task 4: Compare and stop

- [x] Create `comparison.json` with the existing test8 box/point metrics and new text metrics, including local-ID continuity and limitations.
- [x] Create `SAM3_CONCEPT_TEST.md` with one of the four specified classifications and the three required final answers.
- [x] Verify the three deliverables and unchanged V2.6.2 prediction hashes. Stop SAM experiments.
