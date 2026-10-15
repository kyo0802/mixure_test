# 最小合成regression設計 — 未執行、未批准

先決：exact candidate prompt完成；Prediction V1/V2 system維持；8-frame三表示法CPU模型消費alias證明及input/hash inventories齊全。若gate失敗，不替換Video為Multi、不改frames、pixels或encoder，stop該regression計畫。

固定資料：沿用已保存的8張gradient/checkerboard synthetic source，digest一致；無真實Phase2a pixels、GT、答案或外部服務。Multi8 8張fullcontext、Storyboard8 3col/480×270+32label、Video8 FFV1/AVI 4fps，encoder時間0…1.75s。需要先确认processor indices0…7、temporal grid4、alias8個。最低限度不新增實體場景/事件GT；測的是格式可能性。這些输入不一定誘发所有event branch，因此即使全部pass也不能聲稱完整事件schema穩定；未走到的分支標UNTESTED。

唯一主要變因：task-level field clarification prompt baseline V3 vs proposed新版本。V2 system、schema、checkpoint、NF4/BF16/SDPA、processor200704、sampling、greedy、seed42、1024、300s generation/330 request/120 load均固定。三表示法分别是部署條件；不是三個獨立sample。計畫同時兩個prompt arms，每arm每rep 1warmup+2measured：3×2×3=18calls（6warmup+12measured）。不可另加未登記生成。單臂9calls能確認可行，但無同時baseline對照且歷史greedy不穩，因此不建議將其作效果證據。

固定run order：依sha256(SYNTH_REGRESSION_V1/representation/prompt_sha/iteration)排序；先公布hash/index並逐臂warmup在該臂measured之前。沒有依結果重試，沒有轉換模型/精度/像素。可接受預先批准的一次「generation開始前」transport/load infra retry，必須記錄證据；generated任何token後重試一律零。

所有raw、resource、generation-start、token EOS、alias observer、schema/citation/semantic結果、ownedtreeCPU和PyTorch/globalVRAM分開保存。先報strict各stage與branch coverage，再看event_count descriptive。parser不去fence、不補字、不替換引用。Fail照保存，不為有利output挑選迭代。

若candidate需要schema改動，這個prompt-only計畫失效，必須另立semantic/schema版本與單因子研究。若需要新的decodingengine或tokenbudget，同樣分開。無適應性加calls；沒有synthetic模型accuracy聲稱。GPU執行必須另收到 `RUN_QWEN_NF4_MINIMAL_SYNTHETIC_REGRESSION` 明確授權。
