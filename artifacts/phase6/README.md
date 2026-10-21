# Phase 6 output navigation

Completed: [Traditional Chinese report](PHASE6_REPORT.md), [visual inspection](VISUAL_REVIEW.md), [CPU tests](CPU_TEST_RESULTS.md), [closeout provenance](CLOSEOUT_VERIFICATION.md). Six genuine missed-phone recoveries; tabletop queries partly improve; microwave-top segmentation remains unreliable. Zero verified locations.

- `pixel_demo/`: final explicit 1008 × 560 model-canvas coordinate run. Original source image dimensions and native timestamps are preserved; processor canvas is verified, then coordinates are deterministically mapped back.
- `demo/`: retained initial normalized-coordinate diagnostic. 21 calls, 12 schema-invalid outputs. Even in-range outputs do not establish that the model followed normalized coordinates. Do not use this attempt as the final localization evaluation.
- The final human-readable report is published at `WORKSPACE/VLMtest/LATEST_REPORT.md` and preserved here as `PHASE6_REPORT.md` after visual inspection.

Both attempts retain original model outputs. No reinterpretation of the first attempt as pixel coordinates, no silent clipping, and no modification of historical Phase 4/5 outputs.

Query saved graphs with `scripts/run_phase6_demo.py --memory artifacts/phase6/pixel_demo/test8/memory_graph.json --query "Where is my phone?"`. This loads no model and decodes no video. New execution requires a fresh output directory. Optional `--bundle` supplies `source_manifest` and `phase5_graphs`; optional `--reference-image` is appearance context only and cannot grant persistent identity.
