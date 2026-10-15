# Model temporal-position 補充稽核（無forward）

Step2 report中的model_visible_temporal_patch_time是processor輸出的second_per_grid_ts重建，尚未套model位置ID整數化。本補充是解讀該數值的必要補充，不覆寫Step2回條／報告。

安裝中的get_rope_index在modeling_qwen2_5_vl.py:1097–1100用expanded_range × second_per_grid_t × tokens_per_second，再.long()。本地config實際tokens_per_second=2，並非source docstring例子25。使用CPUscalar Tensor重現相同dtype/運算，不建model、不呼叫model函式。offset扣除後可得relativeposition的秒數proxy，不證明實際runtime消費或模型理解物理時間。

| Case | Temporal position IDs | Per-frame time proxy | Max absolute deviation |
|---|---|---|---|
| test1 | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.5349999999999993 |
| test5 | [0, 1, 2, 4] | [0.0, 0.0, 0.5, 0.5, 1.0, 1.0, 2.0, 2.0] | 0.6999999999999993 |
| test7 | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.5383333333333322 |
| test8 | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.8900000000000006 |
| test2 | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.5716666666666663 |
| test5 | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.5666666666666664 |
| X_9466c22b82dad731 | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.5 |
| X_1de7663247196813 | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.5 |
| X_685180893dee1e85 | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.5 |
| X_1c1b2f1aa6ae3ac2 | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.5 |
| X_abef8149c15bfb7e | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.5 |
| X_6a46f3734a47a8a3 | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.5 |
| X_0009ab2fbef22158 | [0, 2, 4, 6] | [0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0] | 0.5 |

全部仍FRAME_MATCHED_ONLY。nativePTS只在private mapping；images/storyboard ORDER_ONLY且無時間秒數輸入。4時間位置不能證明8個alias逐張可辨。0.1s是未批准提案，不能拿較小nominalCFR誤差代替此proxy。追加3個CPU測試：exactgrid、float32/long truncation、4unit數量，全部通過。
