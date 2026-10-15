# Matched Video 8 CPU 預檢

只載本機processor/tokenizer，沒有model。原uniform_positions round ties-to-even、首末包含算法保留；DEV六窗逐項重現此前八個位置。test3未建立input。Synthetic六評估+一warmup均來自先鎖影格。

Public API直接接受RGB ndarray為video；有video_grid_thw，不是Multi-image。_preprocess輸入觀察器逐frame核對canonicalRGB digest與順序；8frame→4 temporal patches、2frame/pair，未pad/drop/dup。內部CPU張量僅記shape/digest，未持久化。原runtime仍AVI/fps4路徑，nativearray尚未接入；不能用本CPU成功宣稱runtime consumption成功。

時間：無container，所以encoded frame time每項null（NOT_APPLICABLE）。processor fps=7/native span；沒有源PTS逐點輸入。second_per_grid_ts=temporal_patch_size/fps；installed modeling get_rope_index用這個值與tokens_per_second构造時間position。未呼叫model/forward，僅來源碼驗證與processor輸出。時序是uniform重建，非native PTS exact。Multi/Storyboard ORDER_ONLY；原PTS仍private sidecar，無新time header。報告同時列每frame nominal重建與實際temporal-unit重建 deviation，不能只用較小nominal數字忽略pair時間量化。Video per-frame aliases有8個，時間位置只有4個；membership validator能接受8，但模型是否分辨每一張尚未證明，需human alias policy。

0.1s容許只是proposal，不是批准。FRAME_MATCHED_ONLY表示source/order/CPUconsumption可核對但時間粒度／distortion或政策不足；不能默認18-call arm已獲准。整體budget有固有差異，沒有time-information/token/pixel parity聲稱。

| Case | Kind | Outcome | Reason / max patch deviation |
|---|---|---|---|
| test1 | DEV | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5150000190734856 |
| test5 | DEV | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.3476190090179436 |
| test7 | DEV | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5147619597117092 |
| test8 | DEV | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5683333333333351 |
| test2 | DEV | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5161904446283971 |
| test5 | DEV | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5142857154210407 |
| X_9466c22b82dad731 | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5 |
| X_1de7663247196813 | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5 |
| X_685180893dee1e85 | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5 |
| X_1c1b2f1aa6ae3ac2 | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5 |
| X_abef8149c15bfb7e | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5 |
| X_6a46f3734a47a8a3 | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5 |
| X_0009ab2fbef22158 | WARMUP | FRAME_MATCHED_ONLY | ['CFR_TIME_DISTORTION'] / 0.5 |

## 逐窗與逐fixture完整資料

### W_5597d9b003977e053d70 (DEV)

Authorized count=107; first/last=S000157/S000263; positions=[0, 15, 30, 45, 61, 76, 91, 106]; previousagreement=True.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | S000157 | 5.235 | d56989cc5537985f7ac2f24d10183c4fb800c91ef6b87d6b11bdfad93093255c | 0.0 | 0.0 |
| F0016 | S000172 | 5.736666666666666 | 788ab981a94498d0da3225017988e03b1d79864e804e83ec2cfa3def738ef28e | 0.0033333333333338544 | -0.501666666666666 |
| F0031 | S000187 | 6.236666666666666 | 18b249a0c5a674b9b7b0f1c7db27ef8aeae70f561f9e502d2cff7e760134b4b1 | 0.008333333333333748 | 0.008333323796590797 |
| F0046 | S000202 | 6.736666666666666 | f9ef57c27085eaed14c96eaa27ebe674b22827c7b3fc967f16921d92b41d3a96 | 0.013333333333333641 | -0.4916666762034092 |
| F0062 | S000218 | 7.27 | 71c0e5140d97941a344aa52cb0e6241c287ba4f50b584e8e18720bb9937fcf4d | -0.01499999999999968 | -0.015000019073485582 |
| F0077 | S000233 | 7.77 | 6992a47cace574b30fbb0bcbc047b4fd323a961d4a734cc08e1cc71b3a007cee | -0.009999999999999787 | -0.5150000190734856 |
| F0092 | S000248 | 8.27 | 1e85f0f489b6171f21b102e91669f0e7e4d621d7e56597ee26c1ed16869b02da | -0.004999999999999893 | -0.005000028610228746 |
| F0107 | S000263 | 8.77 | 2501502672f4ad77860e1a644efc3a5fad29c66c777e9a429bb255eafe59d727 | 0.0 | -0.5050000286102287 |

Native gaps=[0.501666666666666, 0.5, 0.5, 0.5333333333333332, 0.5, 0.5, 0.5]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "d888ad94b2cc95e83b7bd51758400a3370dfaa89f21ca55e8eeac51af8bc8292", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "d9126e65fa18cb4e34017dcf4c5a6c814f47933ce8e4ddc6083cb890a202143f", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "446bd2fa4f47d72a49791e9203f1d57e3fb58e64deeeb6bf4d004c6695ea38c6", "second_per_grid_ts": [1.0099999904632568], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0016", "F0031", "F0046", "F0062", "F0077", "F0092", "F0107"], "aliases_by_temporal_unit": [["F0001", "F0016"], ["F0031", "F0046"], ["F0062", "F0077"], ["F0092", "F0107"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "86410cf8b6ab5127b3b84e389c2da1a00ee1c2c72851e2b3a8f7e345d638b7e3", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/W_5597d9b003977e053d70.json)。

### W_aef405003cc72cef0044 (DEV)

Authorized count=72; first/last=S000162/S000233; positions=[0, 10, 20, 30, 41, 51, 61, 71]; previousagreement=True.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | S000162 | 5.4 | 768102f2956b3448205da952baadb905779962c051b4372abca0d365ecca18fa | 0.0 | 0.0 |
| F0011 | S000172 | 5.733333333333333 | fc9d5105ba00ad2c65c0896b1f01763494254d7d655d19d441ea7e674543c4b8 | 0.0047619047619050225 | -0.33333333333333304 |
| F0021 | S000182 | 6.066666666666666 | 4424f4fe82be735338001e8253ecd00bd9f516a063c9bc890cd5fe5418b6af0e | 0.009523809523810045 | 0.009523828824361757 |
| F0031 | S000192 | 6.4 | 4d44b394282005ac9f48100c279208dfd9cd17d132805323b35b75d0d7df6690 | 0.014285714285714013 | -0.32380950450897217 |
| F0042 | S000203 | 6.766666666666667 | 3543715ce73da10b4644bc27e5c7b4f2b3b254e826a9fbad41e61792c30dcd4e | -0.014285714285714013 | -0.014285675684610588 |
| F0052 | S000213 | 7.1 | b596c5900529f02517d4dde63547355195e8c1fbaba654cb90cfb6eb12a17af0 | -0.009523809523809046 | -0.3476190090179436 |
| F0062 | S000223 | 7.433333333333334 | e4a98a4419bf6f44e9e945859fcc1fb4d27729ebb55759ca051ef84ef36bcf21 | -0.004761904761905189 | -0.004761846860249719 |
| F0072 | S000233 | 7.766666666666667 | 68e65a6145adc66be3ef190f505780dc17baef84d95db5c58dda44a7fbab7bc8 | 0.0 | -0.33809518019358276 |

Native gaps=[0.33333333333333304, 0.33333333333333304, 0.3333333333333339, 0.36666666666666625, 0.33333333333333304, 0.3333333333333339, 0.33333333333333304]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "44cd1f2906eb7bd7afcb6b6d3a9fa5763ad743996e5f7ea8b80177f9e86c9f40", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "d6742f2c3e4a274c353e1bbe72083f558554fd61f407ade40eced4f2d7bff515", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "63021ce94ad8edea69a404cf784293bec6e2dd821dd7b76a0dddcdc29ef3f4b5", "second_per_grid_ts": [0.6761904954910278], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0011", "F0021", "F0031", "F0042", "F0052", "F0062", "F0072"], "aliases_by_temporal_unit": [["F0001", "F0011"], ["F0021", "F0031"], ["F0042", "F0052"], ["F0062", "F0072"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "eeb5fa8ed029e2cdc5ea408399292b140f090c7f59b31414e9bdd141e934f33e", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/W_aef405003cc72cef0044.json)。

### W_b8a53fea6aa8b92dc94f (DEV)

Authorized count=107; first/last=S000373/S000479; positions=[0, 15, 30, 45, 61, 76, 91, 106]; previousagreement=True.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | S000373 | 12.435 | acc2d33195c0de19adfe0e2cebf8dd82f56441ac2d3ec33e374c540368e3ddf9 | 0.0 | 0.0 |
| F0016 | S000388 | 12.935 | 9c7fecf9e100c481b127f32f452b0da186d80ea7fad8f80784726c2a7a8c1dae | 0.005476190476190301 | -0.5 |
| F0031 | S000403 | 13.436666666666667 | c2e6ebdbc18e2bcc16f36c222bcd364af2b5d96087802e409832b3c940b73753 | 0.009285714285713675 | 0.0092856868108111 |
| F0046 | S000418 | 13.936666666666667 | e113f445b223c6a749f73eb615184a6d9765bdd0edf56e35d113d732c894f150 | 0.014761904761904088 | -0.4907143131891889 |
| F0062 | S000434 | 14.471666666666666 | 837beacb014be7b83c12284a8085d2ed366f8b1dade85e3196d36384e4b0945d | -0.014761904761904088 | -0.014761959711709238 |
| F0077 | S000449 | 14.971666666666666 | 4be4d85a7eaae7628c3c96a09735c94aab649c891696e255d4834e3266577a45 | -0.009285714285713897 | -0.5147619597117092 |
| F0092 | S000464 | 15.471666666666666 | 7e9f9417c9c1c83833a45ba0dadd263aad367586138f0387dc3fffb50739f45a | -0.003809523809523263 | -0.003809606234231211 |
| F0107 | S000479 | 15.973333333333333 | d2156294d78c477cf0d251603a50a686b5c44137bb9e8d33b58786b396450666 | 0.0 | -0.5054762729008981 |

Native gaps=[0.5, 0.5016666666666669, 0.5, 0.5349999999999984, 0.5, 0.5, 0.5016666666666669]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "446c1c39f82de1a901cda03de70b7b88b6824997df3fbbedce40b0145a4896da", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "905cdcf1882f42f848c2689733e785bdc27e55bae5a95656ce8f9b799ea927a3", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "833a7b719a740b8c416df7f2ddc44fa0c578b5eef4bbaf3f6a5b2d68c6cfd36e", "second_per_grid_ts": [1.010952353477478], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0016", "F0031", "F0046", "F0062", "F0077", "F0092", "F0107"], "aliases_by_temporal_unit": [["F0001", "F0016"], ["F0031", "F0046"], ["F0062", "F0077"], ["F0092", "F0107"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "312f5113aad1c254886e5c638bd18203caa0055efd82597ca1687e313690cfc5", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/W_b8a53fea6aa8b92dc94f.json)。

### W_db55b29f820c2b3e3afb (DEV)

Authorized count=118; first/last=S000936/S001053; positions=[0, 17, 33, 50, 67, 84, 100, 117]; previousagreement=True.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | S000936 | 31.211666666666666 | 4abac694625b666bcf7e68b256a5f2c7120408677788a0b56c4f0a769c9d75ef | 0.0 | 0.0 |
| F0018 | S000953 | 31.78 | cb9d5dab3a8004a2ef5656e863c47e3e1303cecdbca880a7799d7bf8747ad9ef | -0.012619047619049306 | -0.5683333333333351 |
| F0034 | S000969 | 32.31333333333333 | 3a78d9dd9de1855de3ee952deeb8883a5d9d2c32981242faf53341505a5d029b | 0.009761904761905082 | 0.009761951764424737 |
| F0051 | S000986 | 32.88166666666667 | 197920020b7af48f1a19af9f7cf5589640f8364930d401ca63e2620d64e1732b | -0.0028571428571444457 | -0.5585713815689104 |
| F0068 | S001003 | 33.44833333333333 | f8c5039472b0baea79f97a6440c7e93ff9fcc1148b959892e3d8472b31d4d8c4 | -0.013809523809521274 | -0.013809429804481965 |
| F0085 | S001020 | 34.0 | 4712f44764fa37fcb2daab2f470fa15dad7aa624022b1aa36736e0818d5a5f78 | -0.009761904761905082 | -0.5654760964711514 |
| F0101 | S001036 | 34.53333333333333 | 9d888fcb5b15acf9d7783066e4407e58344b5d69504dd4926f5f636988aa0236 | 0.012619047619049084 | 0.01261918862660849 |
| F0118 | S001053 | 35.10166666666667 | 485795c8cffe56acc1c19e6465d1e09c697414a56ca6939a3632a1be17eb4b3f | 0.0 | -0.5557141447067266 |

Native gaps=[0.5683333333333351, 0.5333333333333314, 0.5683333333333351, 0.5666666666666629, 0.5516666666666694, 0.5333333333333314, 0.5683333333333351]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "537aad88aa7d78709534be8c3266852ff4dad6c9bc31b6b10209f77f31d73170", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "7a453c46a9953cf23176a6dd198132ac998e449753e47f51130a34b3c34f2653", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "45193c3346a001f79968b1db2a954ddec4c53b06b7b5a9418035783e51e7cfd5", "second_per_grid_ts": [1.1114286184310913], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0018", "F0034", "F0051", "F0068", "F0085", "F0101", "F0118"], "aliases_by_temporal_unit": [["F0001", "F0018"], ["F0034", "F0051"], ["F0068", "F0085"], ["F0101", "F0118"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "f2d863e56cf978391c2bf6ce22890099b12f1c5e37d20d783dec2b58251268c4", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/W_db55b29f820c2b3e3afb.json)。

### W_ec4751640324779435e6 (DEV)

Authorized count=108; first/last=S000180/S000287; positions=[0, 15, 31, 46, 61, 76, 92, 107]; previousagreement=True.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | S000180 | 6.008333333333334 | 96a42d2509cca38e7b0a4896149ad2fec923eb285ef1116d5193137687503583 | 0.0 | 0.0 |
| F0016 | S000195 | 6.51 | 576597f51b8970e380b81a79a3b60280dc3060392768f1281a225f345ac2d995 | 0.008571428571429118 | -0.501666666666666 |
| F0032 | S000211 | 7.043333333333333 | 68c7ccc6a7c55ad6c557159106e639af3f1b3ea207be708f78f1602b039a1327 | -0.01452380952380894 | -0.014523777961730211 |
| F0047 | S000226 | 7.545 | 3b28096e1d199b5e2b2318e11243ef587ea102dd70f1f3bfecbd377e7b46b89c | -0.005952380952380709 | -0.5161904446283971 |
| F0062 | S000241 | 8.045 | 700897d88332a8144f19a37eef15f6e4b75330658f621592ef84bc888563e6d3 | 0.004285714285714448 | 0.004285777409871905 |
| F0077 | S000256 | 8.545 | 646248fa7cdc116815d6d4a9cf6b13229875e78c522f2a55e43c753deef295cd | 0.014523809523809827 | -0.4957142225901281 |
| F0093 | S000272 | 9.08 | 865548b72ad75b19731d2b50f350937a4dbe438edf685a2e7beb9a6d99627ab3 | -0.01023809523809538 | -0.010238000551859194 |
| F0108 | S000287 | 9.58 | 75dd170805e7a7ec96be8cc991616a63c333f90f8bf01740f91936566dfd8cdb | 0.0 | -0.5102380005518592 |

Native gaps=[0.501666666666666, 0.5333333333333332, 0.5016666666666669, 0.5, 0.5, 0.5350000000000001, 0.5]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "8314f659d395707241329e6517f773a9df595ee9490fafb9bbdcfa55b03a4287", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "a84f55b9759374e1e8ccf842199b466eb1479ba6505363b3e20c92ef4b066e41", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "dcca7a5f056824025a26b3ce7e6c81100417360edb0921b039c9b8698a06ae21", "second_per_grid_ts": [1.020476222038269], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0016", "F0032", "F0047", "F0062", "F0077", "F0093", "F0108"], "aliases_by_temporal_unit": [["F0001", "F0016"], ["F0032", "F0047"], ["F0062", "F0077"], ["F0093", "F0108"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "d1ef2a32ea41b60b94e24afd0ad819dcb5870e6abe70c7121e0fb6455dbf0474", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/W_ec4751640324779435e6.json)。

### W_f1d4f821d33515975293 (DEV)

Authorized count=108; first/last=S000342/S000449; positions=[0, 15, 31, 46, 61, 76, 92, 107]; previousagreement=True.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | S000342 | 11.4 | 46344ecd116a96990fe0b678a27aa2ee4de92c4e86c63d2b515f1e02094de82f | 0.0 | 0.0 |
| F0016 | S000357 | 11.9 | 3f40a5991396f2d114c5d33291941e7b6f1c628d22a0c520ca73140fe5a67c41 | 0.00952380952380949 | -0.5 |
| F0032 | S000373 | 12.433333333333334 | ed2a10484015f8dc14470602bfb760ad272f3425c49dab8cf4a95bbf8dcfcf2b | -0.014285714285714235 | -0.014285715421040734 |
| F0047 | S000388 | 12.933333333333334 | 435f696e4cf32bdb7f7a112a87e5540cca85432675be5c193a1d91da53a29f2c | -0.004761904761904745 | -0.5142857154210407 |
| F0062 | S000403 | 13.433333333333334 | d76d02f89cdde7760f21f66041195257148a9652230a85b3b71b0bda4ae6e6ac | 0.004761904761904745 | 0.004761902491251746 |
| F0077 | S000418 | 13.933333333333334 | 1eccbfaf3ecf5371a40171081b9ca2254c4387583640a920977d35d2d6368fd0 | 0.014285714285714235 | -0.49523809750874825 |
| F0093 | S000434 | 14.466666666666667 | eeb4ea0c7a11955a77dd6a49cc04ed4c752a15b3aefcce226925fadd26c4b0f7 | -0.00952380952380949 | -0.009523812929788988 |
| F0108 | S000449 | 14.966666666666667 | 68e4b371f09981e0c7df126709ebdf72926d9a853854f409534ea71bc607abe9 | 0.0 | -0.509523812929789 |

Native gaps=[0.5, 0.5333333333333332, 0.5, 0.5, 0.5, 0.5333333333333332, 0.5]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "b5953d69c0106ffb4795955cd9dd878a44639d00711a78275c0e24e144f05d38", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "4cdfce5369e49f72b368de58d3a29ccf45b8a83f524a80a380f18085920a5e38", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "d729cc4b334bd4d226797acfc52a3627346a0e673861fd5eb521361520cfce4a", "second_per_grid_ts": [1.0190476179122925], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0016", "F0032", "F0047", "F0062", "F0077", "F0093", "F0108"], "aliases_by_temporal_unit": [["F0001", "F0016"], ["F0032", "F0047"], ["F0062", "F0077"], ["F0093", "F0108"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "e4840ebd29e77c7602cc4846fb5212ecc9b48191141ff8204b9dfbbe9af8e4a6", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/W_f1d4f821d33515975293.json)。

### X_9466c22b82dad731 (SYNTHETIC_EVAL)

Authorized count=8; first/last=0/7; positions=[0, 1, 2, 3, 4, 5, 6, 7]; previousagreement=N/A_NEW_LOCKED_FIXTURE.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | 0 | 0.0 | 11f2e0245ab2f2988e1480c01bddfcab0ff1e0cb440076f73a5c6e7abf0df791 | 0.0 | 0.0 |
| F0002 | 1 | 0.5 | 11f2e0245ab2f2988e1480c01bddfcab0ff1e0cb440076f73a5c6e7abf0df791 | 0.0 | -0.5 |
| F0003 | 2 | 1.0 | 11f2e0245ab2f2988e1480c01bddfcab0ff1e0cb440076f73a5c6e7abf0df791 | 0.0 | 0.0 |
| F0004 | 3 | 1.5 | 11f2e0245ab2f2988e1480c01bddfcab0ff1e0cb440076f73a5c6e7abf0df791 | 0.0 | -0.5 |
| F0005 | 4 | 2.0 | 11f2e0245ab2f2988e1480c01bddfcab0ff1e0cb440076f73a5c6e7abf0df791 | 0.0 | 0.0 |
| F0006 | 5 | 2.5 | 11f2e0245ab2f2988e1480c01bddfcab0ff1e0cb440076f73a5c6e7abf0df791 | 0.0 | -0.5 |
| F0007 | 6 | 3.0 | 11f2e0245ab2f2988e1480c01bddfcab0ff1e0cb440076f73a5c6e7abf0df791 | 0.0 | 0.0 |
| F0008 | 7 | 3.5 | 11f2e0245ab2f2988e1480c01bddfcab0ff1e0cb440076f73a5c6e7abf0df791 | 0.0 | -0.5 |

Native gaps=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "00584fe9928538c1a341d859b5b8c8fbf1055dfce1b36822e0b575176e609fa3", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "c2ffa3a8a6f886b3fa8941f0c50f1d3d60abcdf953b741a9cbbc325029242615", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "eb79250a331011ed52514dda9b845790b74b4f9c24367b1ee6bc75000693445d", "second_per_grid_ts": [1.0], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0002", "F0003", "F0004", "F0005", "F0006", "F0007", "F0008"], "aliases_by_temporal_unit": [["F0001", "F0002"], ["F0003", "F0004"], ["F0005", "F0006"], ["F0007", "F0008"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "66a86c1a1f5f551e2dccf31f83a4df69c44d0cdecb5ad8fb49dbc4ce1259ba5f", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/X_9466c22b82dad731.json)。

### X_1de7663247196813 (SYNTHETIC_EVAL)

Authorized count=8; first/last=0/7; positions=[0, 1, 2, 3, 4, 5, 6, 7]; previousagreement=N/A_NEW_LOCKED_FIXTURE.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | 0 | 0.0 | 7c4fd8f399bba009852d71adf8b806a578cd4c1fcfa1e1b260696c181b46510b | 0.0 | 0.0 |
| F0002 | 1 | 0.5 | 7c4fd8f399bba009852d71adf8b806a578cd4c1fcfa1e1b260696c181b46510b | 0.0 | -0.5 |
| F0003 | 2 | 1.0 | 7c4fd8f399bba009852d71adf8b806a578cd4c1fcfa1e1b260696c181b46510b | 0.0 | 0.0 |
| F0004 | 3 | 1.5 | 7c4fd8f399bba009852d71adf8b806a578cd4c1fcfa1e1b260696c181b46510b | 0.0 | -0.5 |
| F0005 | 4 | 2.0 | 7c4fd8f399bba009852d71adf8b806a578cd4c1fcfa1e1b260696c181b46510b | 0.0 | 0.0 |
| F0006 | 5 | 2.5 | 7c4fd8f399bba009852d71adf8b806a578cd4c1fcfa1e1b260696c181b46510b | 0.0 | -0.5 |
| F0007 | 6 | 3.0 | 7c4fd8f399bba009852d71adf8b806a578cd4c1fcfa1e1b260696c181b46510b | 0.0 | 0.0 |
| F0008 | 7 | 3.5 | 7c4fd8f399bba009852d71adf8b806a578cd4c1fcfa1e1b260696c181b46510b | 0.0 | -0.5 |

Native gaps=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "92223e8dff20caf8e2c4ec9b3c17ca87eaed633e123853e8c5f7a065440e8549", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "29b31fefcba11a099bcde582391f9304b562967be008765d4b68b10f36aff508", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "2b033bd82f82ce9bfea78db356b24f1883d9e11446bb975eecf27d907ec16f79", "second_per_grid_ts": [1.0], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0002", "F0003", "F0004", "F0005", "F0006", "F0007", "F0008"], "aliases_by_temporal_unit": [["F0001", "F0002"], ["F0003", "F0004"], ["F0005", "F0006"], ["F0007", "F0008"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "37ccc8ed070923dff6da200ca94cd372f17d952d7a6a2c4e7b72d656b4c66fd4", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/X_1de7663247196813.json)。

### X_685180893dee1e85 (SYNTHETIC_EVAL)

Authorized count=8; first/last=0/7; positions=[0, 1, 2, 3, 4, 5, 6, 7]; previousagreement=N/A_NEW_LOCKED_FIXTURE.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | 0 | 0.0 | 309587eb5c0eccf48a5223d6dc2836547ef5cbea5c41c866ffad5bcbeac11bcc | 0.0 | 0.0 |
| F0002 | 1 | 0.5 | 1e02d93b77ece0079220d80a4ea0af0cbd1b649a75db045be65607f14d698971 | 0.0 | -0.5 |
| F0003 | 2 | 1.0 | 5c9f1ee3193aa69763f0739070f3c337be3913a89536fbec8f475df788328947 | 0.0 | 0.0 |
| F0004 | 3 | 1.5 | 68e59d08c0d295e2f88279322fed3db4c2caf2d7efa8fc0fa1880943c422aa9c | 0.0 | -0.5 |
| F0005 | 4 | 2.0 | c7b019fd432d84989f4d809e587c22c0eeb50576d9d0724d108de5a274206a02 | 0.0 | 0.0 |
| F0006 | 5 | 2.5 | 674597c433badcedef39413db03fe7e64d1a8160378645c3a27ce6bf877c41f8 | 0.0 | -0.5 |
| F0007 | 6 | 3.0 | 6cb606087a7f4ad26755d60e60a825ea6f8bec83cf0a2d54db0f99d953f01e12 | 0.0 | 0.0 |
| F0008 | 7 | 3.5 | 3f22e00ba1fa15407421f24ec335423e23ef8523dbeb550b8d6eb8dd2cbcc9ff | 0.0 | -0.5 |

Native gaps=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "f276201c55b525ab2b7781ca6dae7e35b07cd7995ab0b40261824a718409fb76", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "239c0b00b66419a365c93014178d99c032ef9182a1d15f95bb882336c9223ebd", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "d9f6cde6004f3c2f3e8c220cdc1f5adab23940f7aca9db5c7612c37d06b2f52a", "second_per_grid_ts": [1.0], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0002", "F0003", "F0004", "F0005", "F0006", "F0007", "F0008"], "aliases_by_temporal_unit": [["F0001", "F0002"], ["F0003", "F0004"], ["F0005", "F0006"], ["F0007", "F0008"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "9b48794c0bc7c78c69c126697987b55503af85e699797f7acdadaf40286cea16", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/X_685180893dee1e85.json)。

### X_1c1b2f1aa6ae3ac2 (SYNTHETIC_EVAL)

Authorized count=8; first/last=0/7; positions=[0, 1, 2, 3, 4, 5, 6, 7]; previousagreement=N/A_NEW_LOCKED_FIXTURE.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | 0 | 0.0 | 88f634782605de61b4b95c23fa30ac57b17c1f24274b55b724889574b01f1800 | 0.0 | 0.0 |
| F0002 | 1 | 0.5 | a10882cd3ba5586c5e8615b4984c6b9a1ce951b919b3727c7020979af6a9961f | 0.0 | -0.5 |
| F0003 | 2 | 1.0 | dd507d7ad8fc86a3864825d56750e49b03844870d5bd433e6dce7da0354dc3d4 | 0.0 | 0.0 |
| F0004 | 3 | 1.5 | 94b0082fe3ad491ba616ecdde6786533e508182df4dc4168350bd11e6fb564b2 | 0.0 | -0.5 |
| F0005 | 4 | 2.0 | d2e5bed7eae4fe959188dd7d6f5282db750a9d0da2fe826d1ab9836d481982bd | 0.0 | 0.0 |
| F0006 | 5 | 2.5 | d2e5bed7eae4fe959188dd7d6f5282db750a9d0da2fe826d1ab9836d481982bd | 0.0 | -0.5 |
| F0007 | 6 | 3.0 | e8ca4294c76b4e3bc24a2bb12db5968f3be3a07bb26031cde593ded50c730c25 | 0.0 | 0.0 |
| F0008 | 7 | 3.5 | e8ca4294c76b4e3bc24a2bb12db5968f3be3a07bb26031cde593ded50c730c25 | 0.0 | -0.5 |

Native gaps=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "3f3f3e243ae006ccee58ae52b5cc16d19f09150308eefff659c9d77249aa8dcf", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "e4954a4606c0e75d2c35914e31493a2d4dad5bbebd98ddf49fa7e20ee39e2d8b", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "f1caaa1a0047391184e6b95277aacd294a013a6a60c0739aedde4b5157d12894", "second_per_grid_ts": [1.0], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0002", "F0003", "F0004", "F0005", "F0006", "F0007", "F0008"], "aliases_by_temporal_unit": [["F0001", "F0002"], ["F0003", "F0004"], ["F0005", "F0006"], ["F0007", "F0008"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "aa20bbc683e92b56f5009ab3b2fe3fb104973c007be3c847b4b679b223cfe75b", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/X_1c1b2f1aa6ae3ac2.json)。

### X_abef8149c15bfb7e (SYNTHETIC_EVAL)

Authorized count=8; first/last=0/7; positions=[0, 1, 2, 3, 4, 5, 6, 7]; previousagreement=N/A_NEW_LOCKED_FIXTURE.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | 0 | 0.0 | 2d6b858c0b57b799721d0efc739c0a806b0ed2b247c3055f23bd6fe35dcf0348 | 0.0 | 0.0 |
| F0002 | 1 | 0.5 | 1f16b0550a05cdbda185c72d3251ce04220a8956b986858b5fc89318ba6ea716 | 0.0 | -0.5 |
| F0003 | 2 | 1.0 | d7fd1bba86308390af2b931a72e08a8cea8af2e2d0c7d77cd77ef772842ac063 | 0.0 | 0.0 |
| F0004 | 3 | 1.5 | 38fdc841ec4fd67130438680f9365adb54e278f41aab8bdc81340be9940f3017 | 0.0 | -0.5 |
| F0005 | 4 | 2.0 | 434cbe12654b59c01821c30bc3c4790b1102e48d2051758e8da5f79bc0c0e8fb | 0.0 | 0.0 |
| F0006 | 5 | 2.5 | e1d8d643383ced4a1c160488f55ff2b296d77a3dc147bd067a11abd99e52bf78 | 0.0 | -0.5 |
| F0007 | 6 | 3.0 | 1f16b0550a05cdbda185c72d3251ce04220a8956b986858b5fc89318ba6ea716 | 0.0 | 0.0 |
| F0008 | 7 | 3.5 | 2d6b858c0b57b799721d0efc739c0a806b0ed2b247c3055f23bd6fe35dcf0348 | 0.0 | -0.5 |

Native gaps=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "e52bb03d6221a69242ca86ddb4f968563b213b07cbde1543e3b7fa4413acfffe", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "41ca47807c18c9d6dec73bb9fa3df65bfe9dd2abcf0a149f71e11311044c617d", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "03ca9d3ec0b21e33340e776afdaea1239e90cd86e11f35efe61abf663e373afc", "second_per_grid_ts": [1.0], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0002", "F0003", "F0004", "F0005", "F0006", "F0007", "F0008"], "aliases_by_temporal_unit": [["F0001", "F0002"], ["F0003", "F0004"], ["F0005", "F0006"], ["F0007", "F0008"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "491c68a0cf1f2df36bdc1f22aeeceb9605d73470d8e0347800d5d7b3df64a51a", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/X_abef8149c15bfb7e.json)。

### X_6a46f3734a47a8a3 (SYNTHETIC_EVAL)

Authorized count=8; first/last=0/7; positions=[0, 1, 2, 3, 4, 5, 6, 7]; previousagreement=N/A_NEW_LOCKED_FIXTURE.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | 0 | 0.0 | 0136576a57717f22af2655f9f787490732e1a7dd11363da89366dec0080a7ab6 | 0.0 | 0.0 |
| F0002 | 1 | 0.5 | 0a0931e07bc163cd523bef86fc9c1d1c39587d50fe0f0d724088b43e052982cd | 0.0 | -0.5 |
| F0003 | 2 | 1.0 | 60decb77e33e15ec1be26e1ae327da1d73de0658438a1fd49dab1fda7e8be7f3 | 0.0 | 0.0 |
| F0004 | 3 | 1.5 | 2d44701efd20723eb01cab6cff4cc6ea5cc71a03120fc1886f5f221b5be6ecbb | 0.0 | -0.5 |
| F0005 | 4 | 2.0 | 60decb77e33e15ec1be26e1ae327da1d73de0658438a1fd49dab1fda7e8be7f3 | 0.0 | 0.0 |
| F0006 | 5 | 2.5 | acb8e15d9bf159db83430cf929af528e369748a12ce975f971836c38febc397f | 0.0 | -0.5 |
| F0007 | 6 | 3.0 | ad36da3004a5f84ad0ae994f1e3126938720c4c086d67ac3f08230e9fbe7ecef | 0.0 | 0.0 |
| F0008 | 7 | 3.5 | 029093d029fd1acda6cb400eed843c1ac3417a5cb046a4f543b6c3f44327d161 | 0.0 | -0.5 |

Native gaps=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "862b24b12c0a803370b6fcfc821116118e22c46f15098fa9e73d2d1fc16eb54e", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "56e4c002a3b877338b62094c67c5bc8f87a78ff658461c03f43d2c92a8efda70", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "b4dc5c1ba49f7419d0fd234ef99db791f7e0d9e3f2ea75d9a31246726fafc263", "second_per_grid_ts": [1.0], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0002", "F0003", "F0004", "F0005", "F0006", "F0007", "F0008"], "aliases_by_temporal_unit": [["F0001", "F0002"], ["F0003", "F0004"], ["F0005", "F0006"], ["F0007", "F0008"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "cb354a9965a3de3fedc7e62d6308dfdf98e11722d42fb8504a352b6a58685577", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/X_6a46f3734a47a8a3.json)。

### X_0009ab2fbef22158 (WARMUP)

Authorized count=8; first/last=0/7; positions=[0, 1, 2, 3, 4, 5, 6, 7]; previousagreement=N/A_NEW_LOCKED_FIXTURE.

| Alias | Source ID | Native PTS | RGB SHA | Nominal Δ | Actual pair Δ |
|---|---|---|---|---|---|
| F0001 | 0 | 0.0 | 11ce2322c6b243f553a56071517596b1102d6ddf63803d5450772c37a5e77e43 | 0.0 | 0.0 |
| F0002 | 1 | 0.5 | 11ce2322c6b243f553a56071517596b1102d6ddf63803d5450772c37a5e77e43 | 0.0 | -0.5 |
| F0003 | 2 | 1.0 | 11ce2322c6b243f553a56071517596b1102d6ddf63803d5450772c37a5e77e43 | 0.0 | 0.0 |
| F0004 | 3 | 1.5 | 11ce2322c6b243f553a56071517596b1102d6ddf63803d5450772c37a5e77e43 | 0.0 | -0.5 |
| F0005 | 4 | 2.0 | 11ce2322c6b243f553a56071517596b1102d6ddf63803d5450772c37a5e77e43 | 0.0 | 0.0 |
| F0006 | 5 | 2.5 | 11ce2322c6b243f553a56071517596b1102d6ddf63803d5450772c37a5e77e43 | 0.0 | -0.5 |
| F0007 | 6 | 3.0 | 11ce2322c6b243f553a56071517596b1102d6ddf63803d5450772c37a5e77e43 | 0.0 | 0.0 |
| F0008 | 7 | 3.5 | 11ce2322c6b243f553a56071517596b1102d6ddf63803d5450772c37a5e77e43 | 0.0 | -0.5 |

Native gaps=[0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]; checks={'FRAME_SOURCE_MATCH': True, 'FRAME_ORDER_MATCH': True, 'PROCESSOR_SELECTED_FRAME_MATCH': True, 'NATIVE_TIME_MAPPING_VERIFIED': True, 'CITATION_ALIAS_MATCH': True, 'REPRESENTATION_BUDGET_DOCUMENTED': True}. Budget={"MULTI_IMAGE": {"image_grid_thw": [[1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42], [1, 24, 42]], "effective_spatial_hw": [[336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588], [336, 588]], "visual_tokens": 2016, "expanded_input_tokens": 3761, "pixel_tensor_shape": [8064, 1176], "pixel_tensor_sha256": "f88d94af3d4e56a1120a9d02a0f7f4a2df97ba23e49fb3041315f0f90201c8b6", "source_frame_count": 8, "processor_image_count": 8, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "STORYBOARD": {"image_grid_thw": [[1, 24, 40]], "effective_spatial_hw": [[336, 560]], "visual_tokens": 240, "expanded_input_tokens": 1950, "pixel_tensor_shape": [960, 1176], "pixel_tensor_sha256": "b6b078f1cb6aeeb3d7c544973076c0f513d45744c2d7384ea0e97fa0bd5c486e", "source_frame_count": 8, "processor_image_count": 1, "time_encoding_class": "ORDER_ONLY", "native_times_model_visible": false, "time_distortion_s": [null, null, null, null, null, null, null, null], "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED"}, "VIDEO": {"video_grid_thw": [[4, 24, 42]], "effective_spatial_hw": [[336, 588]], "visual_tokens": 1008, "expanded_input_tokens": 2718, "pixel_tensor_shape": [4032, 1176], "pixel_tensor_sha256": "3344f5eeb53b85dc69ffd4100985c130c4f1b791f44747b1de79c8bbb4bfc427", "second_per_grid_ts": [1.0], "source_frame_count": 8, "accepted_frames": 8, "selected_indices": [0, 1, 2, 3, 4, 5, 6, 7], "sampling_disabled_explicitly": true, "temporal_patch_size": 2, "temporal_patches": 4, "temporal_padding": 0, "supplied_aliases": ["F0001", "F0002", "F0003", "F0004", "F0005", "F0006", "F0007", "F0008"], "aliases_by_temporal_unit": [["F0001", "F0002"], ["F0003", "F0004"], ["F0005", "F0006"], ["F0007", "F0008"]], "alias_granularity": "8 supplied aliases but 4 temporal positional units; frame-specific distinguishability not runtime verified", "runtime_consumption": "RUNTIME_CONSUMPTION_NOT_VERIFIED", "native_array_sha256": "a67a89d2d62dcbf537f2b8e6071accc46229ec199cef3b3ebe924ac5e3332a99", "direct_api_path": "Qwen2_5_VLProcessor.__call__(videos=[RGB ndarray], do_sample_frames=False)", "V3_runtime_route": "NOT_INTEGRATED_NATIVE_FRAME_ARRAY; existing V3 uses encoded AVI path, no runtime change made"}}.

完整lineage/transform/aliases/timeline與pixel provenance：[private mapping](private_mappings/X_0009ab2fbef22158.json)。

Metadata leakage掃描無private item/sourceID/GTroles/answers/reviewer/oldprediction/targetref；像素本身可能暴露物理事件，PIXEL_SEMANTIC_LEAKAGE_UNDETERMINED。正常scene evidence不是新增metadata answer；不聲稱影像可完全概念盲化。
