# CPU-only native-video observations

| Opaque window | Encoded / decoded audit frames | Processor selected frames | Grid | Last endpoint selected | Native selected PTS |
|---|---|---|---|---|---|
| W_db55b29f820c2b3e3afb | 118 | 14 | {'video_grid_thw': [[7, 52, 92]]} | False | [31.211666666666666, 31.47833333333333, 31.746666666666666, 32.04666666666667, 32.31333333333333, 32.61333333333334, 32.88166666666667, 33.181666666666665, 33.44833333333333, 33.715, 34.0, 34.266666666666666, 34.56666666666667, 34.833333333333336] |
| W_5597d9b003977e053d70 | 107 | 14 | {'video_grid_thw': [[7, 52, 92]]} | False | [5.235, 5.47, 5.736666666666666, 5.97, 6.236666666666666, 6.503333333333333, 6.736666666666666, 7.003333333333333, 7.27, 7.503333333333333, 7.77, 8.036666666666667, 8.27, 8.536666666666667] |
| W_ec4751640324779435e6 | 108 | 14 | {'video_grid_thw': [[7, 52, 92]]} | False | [6.008333333333334, 6.241666666666666, 6.51, 6.776666666666666, 7.01, 7.276666666666666, 7.545, 7.8116666666666665, 8.045, 8.311666666666667, 8.578333333333333, 8.813333333333333, 9.08, 9.346666666666666] |
| W_b8a53fea6aa8b92dc94f | 107 | 14 | {'video_grid_thw': [[7, 52, 92]]} | False | [12.435, 12.668333333333333, 12.935, 13.168333333333333, 13.436666666666667, 13.703333333333333, 13.936666666666667, 14.203333333333333, 14.471666666666666, 14.705, 14.971666666666666, 15.238333333333333, 15.471666666666666, 15.74] |
| W_f1d4f821d33515975293 | 108 | 14 | {'video_grid_thw': [[7, 52, 92]]} | False | [11.4, 11.633333333333333, 11.9, 12.166666666666666, 12.4, 12.666666666666666, 12.933333333333334, 13.2, 13.433333333333334, 13.7, 13.966666666666667, 14.2, 14.466666666666667, 14.733333333333333] |
| W_aef405003cc72cef0044 | 72 | 8 | {'video_grid_thw': [[4, 52, 92]]} | False | [5.4, 5.7, 6.0, 6.3, 6.6, 6.9, 7.2, 7.5] |

Original six CPU attempts failed before decoding because the tokenizing multimodal template iterated string system content as item dictionaries. Separate retained CPU-only repair uses system content=[{type:text,text:exact V2 system}], without modifying runtime. All six repaired calls succeeded. Original failures remain in private/failures.json and manifests; repair receipts: private/video_processor_repair_observations.json.

Installed Qwen2VLVideoProcessor.sample_frames computes total_num_frames / encoded FPS × requested FPS, clamps min_frames4/max_frames768 and total count, then floors to temporal_patch_size2. It selects torch.arange(0,N,N/K).int(), not nearest native-time sampling; last endpoint is not necessarily included. _preprocess repeats the last frame only when required for grouping; even input is not universally mandatory. second_per_grid_ts=0.5 is requested4fps grouping, not original PTS.

Full FFV1/OpenCV audit decoded every source frame and verified pixels. Decoder metadata exposes full frame inventory; observer exposes actual selected indices. Intermediate decoder materialized-frame count is UNABLE_TO_DETERMINE. Video selects14 frames for five clips and8 for shortest. Requested FIXED_FPS_4 for image sampling has different endpoint/selection rules.

Budget mismatch: AutoProcessor(max_pixels=200704) affects fast images but video _preprocess uses size.longest_edge=12845056. Actual video grid spatial52×92 => resized728×1288=937664pixels/frame, exceeding declared200704; 7temporal groups=>8372grid-derived visual tokens, shortest4=>4784. This is OFFLINE_VERIFIED, not GPU fit. A corrected video size needs new inputs/processor receipts and future capacity probe.

Current video payload describes all encoded aliases, while processor consumes a subset. Before pilot the adapter must expose only actually processed citation aliases and preserve native mappings. Alias text alone is not visual support. Existing video runtime omits V2 system, fixes greedy decoding and does not apply seed; future parity repair required. No model generated here.
