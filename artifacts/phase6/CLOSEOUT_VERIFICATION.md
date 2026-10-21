# Phase 6 closeout provenance

2026-10-21.

- Final run receipt SHA-256: `b95b75a951a6a7dd3a4ac33907397c1cab2a86a864dba109b58a6978c578041e`.
- Input manifest SHA-256: `c7607d7860353b538542328d12c99db6c829630597d9924ffba7af27853d2986`.
- Phase 5 receipt preserved: `73805c46204bd863962864e7139fa852bab0e3f48d79b2b8f99caa23b6674c2c`.
- All 3,273 protected files rehashed unchanged; all 21 final raw output hashes unchanged.
- Source hashes for inference/integration are in pixel_demo/run_receipt.json. One post-run CPU query-only change: target_surface.py filters supplemental localizations using the resolved requested_entity_id and normalizes category consistently. Before: `be1e8d86ba9c7f5032f446faa9f4200b3955834b803ed465b7a126c173005137`; after: `847e9761ecfe44701c894d6c009ac22fe6d67725eb5c0ab43789fe6f6f7a1313`.
- This guard has a new negative test: an enrolled entity cannot receive an unbound category localization. No model prompt, output, mask, or saved Graph changed. Current code reproduces all 18 saved category queries exactly.
- Attempting --reuse-perception against the completed run correctly stopped with FINAL_RESULT_EXISTS. Existing run outputs/receipt were preserved; no reintegration or model call occurred.
- The comparison-rendering CLI helper was added during inference; it did not alter the running inference/finish path. All comparison images were subsequently generated CPU-only with the current helper.
- No commit/push, historical GT edits, benchmark rerun, or production Graph write.
