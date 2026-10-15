# Matched Video 8 CPU 預檢

只載本機processor/tokenizer，沒有model。原uniform_positions round ties-to-even、首末包含算法保留；DEV六窗逐項重現此前八個位置。test3未建立input。Synthetic六評估+一warmup均來自先鎖影格。

Public API直接接受RGB ndarray為video；有video_grid_thw，不是Multi-image。_preprocess輸入觀察器逐frame核對canonicalRGB digest與順序；8frame→4 temporal patches、2frame/pair，未pad/drop/dup。內部CPU張量僅記shape/digest，未持久化。原runtime仍AVI/fps4路徑，nativearray尚未接入；不能用本CPU成功宣稱runtime consumption成功。

時間：無container，所以encoded frame time每項null（NOT_APPLICABLE）。processor fps=7/native span；沒有源PTS逐點輸入。second_per_grid_ts=temporal_patch_size/fps；installed modeling get_rope_index用這個值與tokens_per_second构造時間position。未呼叫model/forward，僅來源碼驗證與processor輸出。時序是uniform重建，非native PTS exact。Multi/Storyboard ORDER_ONLY；原PTS仍private sidecar，無新time header。報告同時列每frame nominal重建與實際temporal-unit重建 deviation，不能只用較小nominal數字忽略pair時間量化。Video per-frame aliases有8個，時間位置只有4個；membership validator能接受8，但模型是否分辨每一張尚未證明，需human alias policy。

0.1s容許只是proposal，不是批准。FRAME_MATCHED_ONLY表示source/order/CPUconsumption可核對但時間粒度／distortion或政策不足；不能默認18-call arm已獲准。整體budget有固有差異，沒有time-information/token/pixel parity聲稱。

| Case | Kind | Outcome | Reason / max patch deviation |
|---|---|---|---|
| test1 | DEV | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| test5 | DEV | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| test7 | DEV | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| test8 | DEV | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| test2 | DEV | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| test5 | DEV | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| X_9466c22b82dad731 | SYNTHETIC_EVAL | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| X_1de7663247196813 | SYNTHETIC_EVAL | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| X_685180893dee1e85 | SYNTHETIC_EVAL | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| X_1c1b2f1aa6ae3ac2 | SYNTHETIC_EVAL | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| X_abef8149c15bfb7e | SYNTHETIC_EVAL | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| X_6a46f3734a47a8a3 | SYNTHETIC_EVAL | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |
| X_0009ab2fbef22158 | WARMUP | NOT_MATCHED | ['PROCESSOR_BEHAVIOR_UNVERIFIABLE'] / UNVERIFIED |

## 逐窗與逐fixture完整資料

### W_5597d9b003977e053d70 (DEV)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### W_aef405003cc72cef0044 (DEV)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### W_b8a53fea6aa8b92dc94f (DEV)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### W_db55b29f820c2b3e3afb (DEV)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### W_ec4751640324779435e6 (DEV)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### W_f1d4f821d33515975293 (DEV)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### X_9466c22b82dad731 (SYNTHETIC_EVAL)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### X_1de7663247196813 (SYNTHETIC_EVAL)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### X_685180893dee1e85 (SYNTHETIC_EVAL)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### X_1c1b2f1aa6ae3ac2 (SYNTHETIC_EVAL)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### X_abef8149c15bfb7e (SYNTHETIC_EVAL)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### X_6a46f3734a47a8a3 (SYNTHETIC_EVAL)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

### X_0009ab2fbef22158 (WARMUP)

Unable to create tensor, you should probably activate padding with 'padding=True' to have batched tensors with the same length.

Metadata leakage掃描無private item/sourceID/GTroles/answers/reviewer/oldprediction/targetref；像素本身可能暴露物理事件，PIXEL_SEMANTIC_LEAKAGE_UNDETERMINED。正常scene evidence不是新增metadata answer；不聲稱影像可完全概念盲化。
