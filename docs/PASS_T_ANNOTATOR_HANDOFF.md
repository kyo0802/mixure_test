# Pass T Phase 2a V2 — Annotation handoff

The shareable Windows tool is [annotation_handoff/pass_t_phase2a_v2](../annotation_handoff/pass_t_phase2a_v2/README.md).

## Included

- Seven authorized DEV event windows, 728 original full-rate frames and 16 pre-window references: 469,212,523 image bytes (447.48 MiB).
- Byte-identical Stage B Python modules, frozen V2 policy/schema/receipt, review manifest/items and neutral backend provenance.
- Native Tk GUI, blank human forms, semantic validation, immutable saves, progress, and separately hashed annotation-return ZIPs.
- Minimal dependencies: Python 3.12 with Tk, Pillow 11.3.0, jsonschema 4.26.0. No models or CUDA runtime.

The handoff receipt covers 784 immutable files. Its package preservation baseline covers only the standalone subtree; it does not replace or relax the original project baseline. Original policy SHA256 remains `c90f527eb01e3b320138961570c5647670536d3611feae3c4b7a1d10e33fdac4`; original review manifest SHA256 remains `1c423256cd31ea0e585b1bc3e57610fc8b215fcbe2757108db3bd96736af9e46`.

## Verification

Four integration checks passed in an independent minimal virtual environment:

1. Relocated directory with spaces: all receipt, source item and image hashes verified; no local vendor paths or source videos required.
2. Actual Tk widgets: all seven windows opened at first/last frames, answers blank, attestations unchecked, selected candidate overlay by default.
3. Altered authorized image rejected by the integrity check.
4. Isolated artificial image fixture: semantic save and immutable receipt succeeded, duplicate rejected, returned ZIP hashes verified. No test answer entered production.

Test command: `python -B scripts/test_pass_t_annotation_handoff.py`. The owner-only builder is `scripts/build_pass_t_annotation_handoff.py`; an existing released package is not overwritten. Cross-platform Git text conversion is disabled for the handoff subtree to preserve the frozen SHA256 byte contracts.

Before publication, the original full-project preservation check still passed for 19,264 files, frozen V2 contracts were unchanged, and the 8,302 pre-existing tracked working-tree changes were untouched. Only the handoff subtree, its builder/integration test, and these new handoff documents are in this publication's allowlist.

## Annotator action

Use the sparse clone instructions in the tool README. Install Python 3.12 with Tk, then double-click `Start_Annotation.cmd`. Complete all seven first-round windows using a personal reviewer ID. Double-click `Return_Annotations.cmd` and send the new ZIP plus displayed SHA256 to the owner. No Git push permission is needed for annotators.

Real human event annotation remains **0/7 at release**. Frozen data, original annotations, GPT prompts/outputs, V297, models/environments and unbounded source videos were not included or modified. Responses and return archives are Git-ignored. Returned human judgments require owner validation and are not automatically imported into GT or Memory Graph. Causality remains unverified and formal eligibility remains zero.
