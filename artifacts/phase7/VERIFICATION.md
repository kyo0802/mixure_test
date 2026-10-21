# Phase 7 verification and source provenance

2026-10-21. Session: `video_932b70d6ece1c5b31493_20261020T223911Z_3e1a9e`.

## Actual run hashes

- Source MP4: `932b70d6ece1c5b3149321bfd9d633d78da5c1961d88dbf1b06311b5eb9bdee4`.
- source_manifest.json: `cf513cd6ac7b15090953d17f5114631fd6a9ddc762ba162182f6429d7eebb506`.
- memory_graph.json: `ddfc9dd79d913c741205f42335c5d260e36d7a8256922971d701cca42d059464`.
- run_receipt.json: `2040a9f8e7029603b50709b955665a461279535cca32e4b046336ef840162a61`.
- Original search_result.json: `6ef843ddb17a0e9f09f017590eda27538ad92c9c81233a7b89409afac587edde`.

Each Nemotron generation.json contains its unchanged raw output hash. Its runtime.json pins model revision `16853d6c682223e967d5622c99d0082cb994b771`, vLLM 0.31.0, model asset hashes, source manifest and task/schema contract. Four actual official-video-array generations, no historical result reuse. Qwen input.json and generation.json preserve exact canvas/processor and source mapping for six actual generations. SAM receipt records eight actual prompts. No additional inference after this run.

The immutable run receipt records execution-time source hashes. Post-run `fresh_video.py` changed only: mandatory localization-frame inclusion in evidence rendering; category-query strict-validation diagnostic summary; early localization-budget validation. Before SHA: `67afbd987d0e050e8c8ade839d8b55a83edadcf384443b06d8ddfbbd04abb0cf`. Current SHA: `390c1146a0f5320d8255774a85d7b1c11c78d9ad88bbb4e3e3a07215f1ed1483`. Saved Graph, manifests, inference artifacts and original query result were not regenerated. CPU evidence rendering added the missing focus frames. These are display/reporting changes, not a second experiment.

## CPU command and results

```powershell
$env:TEMP = (Resolve-Path artifacts\phase6\test_tmp).Path
$env:TMP = $env:TEMP
.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_phase*_*.py"
```

Final: 71 tests, 0 failures/errors, 0.176 seconds. 9 new Phase 7 cases plus 62 existing Phase 4–6 checks. New cases cover native VFR mapping, strict PTS order, category query normalization, bounded/reasoned fallback, tracker IDs not identity, invalid VLM not negative, partial empty evidence memory, no-subprocess persisted query/hash protection, and aliases preserving native times.

Fresh Python process search checks:

- Phone: POSSIBLE_LOCATIONS, 3 candidates; list exactly equals original saved result.
- Bottle: POSSIBLE_LOCATIONS, 83 candidate relationships (not unique objects or verified accuracy).
- Unenrolled explicit entity: UNKNOWN, 0 candidates.
- No torch/vllm/ultralytics/transformers modules loaded; no model worker invoked.

Integrity: all 208 source PNG hashes match; all 3,273 protected historical input hashes from Phase 6 remain unchanged; Phase 6's 21 final raw outputs remain unchanged. No GT imported at runtime or used to select answers.

## Visual checks and limitations

Viewed source and annotated f180 (6.008333 s), f414 (13.803333 s), f1020 (34.0 s). The first two show the phone near/on the tabletop but partial clipping/hand occlusion and approximate surface geometry prevent physical-support verification. f1020's distant-phone localization is imprecise and has no grounded surface; it does not become a confirmed user-phone location. Existing CV extents and new polygons are only proposals. These checks are AI developer observations, not human GT and not fed into runtime.

Stage COMPLETE denotes execution completion, not output correctness: Nemotron strict 1/4; Qwen localization schema 5/6; no independent contact measurements or persistent identity authorizations. One CV NMS time-limit warning was logged; detection exhaustiveness is not claimed. GPU workers exited sequentially. No commit/push.
