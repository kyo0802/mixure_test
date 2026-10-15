# Package QA

- Five event HTML cards and five original-field JSON records; Call 2 appears only as comparator.
- 40/40 event-frame references verified, 16 unique PNGs. Source frame ordering, native PTS metadata, window indices and original file SHA-256 agree. Six contact sheets (including Call 2) use only these existing samples.
- Inspected both exact storyboard assets: 1440×906, 3 columns × 3 rows, eight cells in row-major order and final cell blank. Original assets remain linked directly.
- Visually inspected contact sheets for calls 1, 8 and 10: full aspect ratio, no destructive cropping, metadata outside evidence pixels, highlighted claims, readable labels and blank human section. Improved the contrast of context-only labels during package construction.
- 45 CPU in-memory JavaScript/DOM checks passed across five cards: initial UNREVIEWED state, null review date, template SHA binding, no automatic download, draft download, incomplete-review rejection, invalid-alias rejection, complete software-mock download branch, and unchanged on-disk template. Mock choices were never persisted as human decisions or GT.
- JavaScript tested with Node VM mocks, not a full browser end-to-end session. No browser adjudication was submitted.
- Initial link-check implementation produced false failures before manifest publication and on long Windows relative paths; corrected publication ordering and path normalization. Final links are resolved and checked after all package files exist.
- Original-source preservation scope: 139 files. 119 agree with available recorded hashes; 20 have observed baseline hashes only. All 139 remain byte-identical before/after generation. Full movies and model weights are outside the byte-audit scope and were not opened.
- No new VLM inference, video sampling, full movie decode, CUDA/model initialization, source-image modification, GT mutation, Memory Graph write, commit or push.

This QA validates the review package and software interaction branches. It does not adjudicate physical events.
