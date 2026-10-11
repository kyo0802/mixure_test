# Pass T Annotation Handoff Implementation Plan

> **For agentic workers:** Execute this scoped plan inline. The user authorized preparing and pushing a usable annotator version; preserve the existing working tree changes and all original annotations/contracts.

**Goal:** Let another Windows user review the seven authorized Phase 2a V2 DEV windows and return immutable human submissions.

**Architecture:** Create a standalone repository subtree containing byte-identical Stage B code, frozen contracts, neutral review items and their authorized images at the same relative paths. A new package preservation baseline covers only that subtree; the original full-project baseline and all source artifacts remain unchanged. No responses are copied into the release.

**Tech Stack:** Python 3.12, Tk, Pillow 11.3.0, jsonschema 4.26.0, Git.

## Steps

- [x] Create `annotation_handoff/pass_t_phase2a_v2/README.md`, `requirements.txt`, `.gitignore`, and `review.py`: offline GUI, integrity check, progress, separately hashed return ZIP.
- [x] Create `scripts/build_pass_t_annotation_handoff.py`: explicit allowlist, new destination only, unchanged code/contracts/items/backend/image bytes, receipt and package-only preservation baseline. Do not include model/environment/Frozen/old answers/source videos.
- [x] Build the package and verify 7 windows, 728 frames, 16 references, policy SHA and unchanged source manifest/item/visual hashes.
- [x] Test a relocated copy with an independent minimal virtual environment: all assets load, real Tk widgets start blank, synthetic saves remain isolated, tampering and duplicate submissions fail, return ZIP links to the original manifest.
- [x] Stage only an explicit release allowlist; verify the 8,302 pre-existing tracked changes are unaffected and no prior index changes are included.
- [ ] Commit and push `codex/pass-i-current` to the configured origin; verify the remote commit and provide clone/start/return instructions.

## Acceptance

`python review.py check` succeeds without local vendor paths, source videos or CUDA. `python review.py gui` displays only the seven authorized windows. Original policy/schema/receipt/item hashes match; the package baseline explicitly does not claim full-repository preservation. Human responses and returned archives are ignored by Git. Remote branch points to the new reviewed commit.
