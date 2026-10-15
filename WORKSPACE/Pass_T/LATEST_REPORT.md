# WORKSPACE 最新報告

來源：[VLM_PHYSICAL_STATE_EXPERIMENT_REPORT.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/VLM_PHYSICAL_STATE_EXPERIMENT_REPORT.md)；更新：2026-10-15（Asia/Taipei）。

# Phase 3 — VLM-first Physical-State Feasibility

更新：2026-10-15（Asia/Taipei）。建議：**REVISE_VLM_OBSERVATION_APPROACH**。

## 結論

**已完成授權的兩次真實 Qwen 生成，重試0、追加呼叫0。** test5 的輸出文字有正確的手機 PICKUP 與 before/after 敘述；test7 的文字卻否認可見的手機拿起。**兩份原始回應均不符合 JSON／V3 合約，有效結構化預測0筆。** 目前有繼續研究的局部訊號，尚不足以直接進入完整 Phase 3 整合；本次停止，沒有自動改 prompt 或補跑。

這是受既有 DEV 失敗啟發的兩視窗可行性實驗，非獨立或無偏 benchmark。沒有計算 accuracy、precision、recall、F1 或泛化能力。

## 真實執行設定

- 模型：既有本機 `Qwen/Qwen2.5-VL-7B-Instruct`；revision `cc594898137f460bfe9f0759e9844b3ce807cfb5`。沿用未修改的 `QwenNF4Runtime` 載入與生成方法，僅為新 V3 任務提供獨立的多圖 preprocessing adapter。
- 量化／裝置：bitsandbytes NF4、double quantization、BF16 compute、SDPA、CUDA；沒有換模型、下載權重或 CPU offload。Transformers4.57.6、bitsandbytes0.50.2、Torch2.10.0+cu128。
- 每窗恰好8張 frozen Uniform8 原始PNG，16/16 SHA驗證相符，保留各自 alias、source index、native PTS、hash與順序，無近鄰替代。詳見 [configuration.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/configuration.json)。沒有解碼原影片。
- 表示：**8張獨立 chronological multi-image stills**，不是 native video。原圖1280×720，實際 `Qwen2VLImageProcessorFast` resize為588×336；每張197,568 pixels，符合 max200,704/min3,136設定。八個 image grids各 `[1,24,42]`，共2,016 visual tokens；沒有 video grid／video temporal units。
- 同一份 system/task/schema，圖片前逐一標示 `Image N corresponds exactly to frame alias Fxxxx`。Task未提 smartphone、basketball、test5、test7或預期答案。模型未收到PTS、私人路徑、人工答案、YOLO／SAM結果、舊call outcomes或GT。
- Greedy：`do_sample=False`、seed42、`max_new_tokens=1024`、generation deadline300秒，無品質重試、額外warmup或替代表示。沒有傳temperature；checkpoint繼承的temperature在非sampling模式被忽略的警告已保留於runtime.log。Seed不代表所有GPU計算保證可重現。
- 保留原硬體門檻：載入前≥10GiB free VRAM／≥8GiB RAM；生成前≥2GiB free VRAM；全GPU使用>14.5GiB、owned RSS>20GiB或系統RAM<2GiB等停止條件。兩次生成皆到EOS，未觸及token cap或generation deadline。

| Call／視窗 | 生成完成 | 生成tokens | input tokens | 生成秒數 | Torch峰值allocated／reserved | 原始JSON | V3 schema／citation／semantic |
|---|---|---:|---:|---:|---|---|---|
| A：test5 W05 | 是，EOS | 335 | 3174 | 104.08 | 6.197／6.865 GiB | FAIL | NOT_EVALUATED：JSON解析失敗 |
| B：test7 W05 | 是，EOS | 47 | 3174 | 2.00 | 6.197／6.865 GiB | FAIL | NOT_EVALUATED：JSON解析失敗 |

模型載入27.48秒，載入峰值allocated6.744GiB。從parent start至最後一筆完成163.59秒；兩次長度／啟動條件不同，不能當受控效能比較。Torch數字不是整張GPU的峰值。

## 原始輸出與嚴格處理

- [Call A原文](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/call_A_raw.txt)／[驗證診斷](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/call_A_parsed.json)：外層有 ```` ```json ```` code fence，第一字元即不符合JSON。**不去除fence、不修復或重新解析為有效預測。** 報告作者直接閱讀文字另發現兩個`other_objects`缺少schema必填的`evidence`；這是人工式文字檢視，並非修復後的schema驗證結果。
- [Call B原文](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/call_B_raw.txt)／[驗證診斷](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/call_B_parsed.json)：同樣有code fence。直接閱讀可見只有`status`／`notes`，缺少必填`events`。也未以補上空陣列的方式轉成有效NO_EVENT。
- 正式 parser 兩筆均為 **INVALID_MODEL_OUTPUT**，`parsed=null`；schema/citation/semantic皆未執行而非通過。沒有任何一筆被提升為 `VLM_EVENT_CANDIDATE` 或 `VLM_NO_CONFIRMED_EVENT`。
- 原始UTF-8回應在驗證前立即原樣落盤並fsync；原始內容、SHA與EOS／token／resource receipts均保留。沒有修改歷史Phase2b strict-invalid結果。

## 生成完成後的質性對照

以下是**報告作者的 qualitative reviewer analysis**，參照原影格及既有人工審閱；不是新增人類GT、獨立感測器或deterministic SUPPORTED Decision。

| 問題 | test5 W05：Call A文字 | test7 W05：Call B文字 |
|---|---|---|
| 操作物件 | 明確寫`phone`，符合可見手機，沒有誤說card | notes寫`phone`，物件類型辨認合理，但否認pickup |
| 事件／狀態 | 寫PICKUP、ON_SURFACE→HELD_BY_PERSON，與主要可見轉換相符 | 沒有before/after狀態或事件記錄；「does not show the phone being picked up」與影格脈絡衝突 |
| BEFORE引用 | F0001/F0016/F0032/F0047；桌面手機與手接近的脈絡合理 | 沒有引用 |
| AFTER引用 | F0062/F0077可見手持手機；F0093手機已在箱口、受箱邊／手遮擋，不能單獨證明仍完全由手支撐 | F0031/F0046可見直立手機被手抓握，卻未被用來支持事件 |
| 其他物件／錯球 | 將basketball及box列為ON_SURFACE、NOT_OBSERVED manipulation；球的文字敘述與所引畫面相容 | 沒有球pickup claim，但也沒有球的狀態或理由；不能把避開所有事件當作可靠的球／手機辨別成功 |
| 不確定性／時間 | `uncertainty=NONE`對F0093遮擋過於肯定；未發明精確timestamp。這些aliases是狀態引用，不是事件精確發生時間 | 未發明精確時間，但缺乏引用；未用UNCERTAIN表達不足，而是文字上否認事件 |

既有人工審閱：test5舊Calls03/10在physical-event-level支持手機pickup，舊Call01的card attribution錯誤；test7舊Call08支持generic pickup但target grounding有限，舊Call04的ball pickup錯誤。本次A的文字與test5人工事件說明一致、避免card／ball歸因；本次B對test7的文字否認與原人工事件說明及F0031/F0046不符。**這只是對照與可見事件遺漏的質性描述，不是正式false-negative計分。** 原人工答案與舊calls皆未改寫。

可直接查看原始關鍵影格：[test5 F0047](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/human_seed_review/items/test5__W05/frames/S000388.png)、[F0093](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/human_seed_review/items/test5__W05/frames/S000434.png)、[test7 F0031](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/human_seed_review/items/test7__W05/frames/S000403.png)、[F0046](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/human_seed_review/items/test7__W05/frames/S000418.png)。

## 執行收尾錯誤及保全

兩份raw、execution與parsed receipts落盤、log寫出`CALL_COMPLETED A/B`後，parent在資源輪詢遇到子程序已結束的`psutil.NoSuchProcess`，parent command exit1，未及寫總結。**這不是兩次模型生成失敗，也未觸發模型重跑。** [execution_summary.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/execution_summary.json)明確標示總結由已落盤receipts做CPU重建；worker exit code未捕獲，不宣稱為0。Parent記憶體中的RSS／整卡VRAM peak亦未落盤，標為未記錄，不能事後補造。

已保留 [runner_as_executed.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/runner_as_executed.py)（與freeze內runner SHA相同），只在目前新runner修正「poll後process消失」的例外分支。確切diff與before/after SHA見 [post_execution_monitor_patch.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/post_execution_monitor_patch.json)。以CPU deterministic exited-process mock及AST檢查通過，未重新推論；prompt、schema、配置、shared NF4程式完全不變。修補後runner對這份舊freeze會拒絕source hash不一致，**不可用它resume／補跑這次已耗完的2-call授權**；後續新實驗需新命名空間與另行授權。

四個必要parser CPU檢查通過：malformed不轉NO_EVENT、EVENTS不可空、UNCERTAIN與NO_CONFIRMED_EVENT可區分。551個既有source／reference／人工review／signal-spike檔案hash皆未變；16張PNG、prompt/config/schema及舊shared runtime hash均相符，詳細保全結果見 [verification.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/verification.json)。歷史 `PHASE3_SIGNAL_CHECKPOINT_BLOCKED` 保持不變，沒有Graph／persistent identity更新、commit或push。

## 固定輸入雜湊與入口

- Prompt：`86160b6e8797ad6a61e680afae326a5247816a2e2d37c36898b9c665a45cfbc9` — [prompt_v3.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/prompt_v3.json)
- Schema：`f9cd268d8e574ccba55b407d42fc4e1e7f0de378081d94bd002d002cda52ecb5` — [schema_v3.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/schema_v3.json)
- 配置：`7e3ebc404bb2c9f9bad579daca754c37d515dfc81c95c40fb0e4f2b783c5dc56` — [configuration.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/configuration.json)
- 所有執行前hash：[frozen_experiment.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/frozen_experiment.json)；精確rendered model-facing text、8張alias對應、processor設定、tensor metadata及canonical hashes：[A input receipt](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/call_A_input_receipt.json)／[B input receipt](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/vlm_physical_state_pilot_v1/call_B_input_receipt.json)。
- 可重用小型runner：[run_phase3_vlm_physical_state.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/scripts/run_phase3_vlm_physical_state.py)；保留at-most-once標記與現有輸出不可覆寫限制。不要直接重新執行此次已完成目錄。

## 下一步建議與限制

選擇 **REVISE_VLM_OBSERVATION_APPROACH**：test5有可讀的物理事件理解訊號，值得繼續研究；但test7漏掉明顯後狀態，兩份又都無法輸出合約可接受的JSON，現在直接整合會隱藏兩種失敗。

若後續另行授權，建議下一個實驗只針對**狀態觀察與引用的穩定性**做受控設計，保留原始回應與invalid gating；不要將本次文字補成通過結果。本次不選新prompt、不再生成、不開始完整整合。

即使文字正確，VLM仍同時提出事件與自述證據，沒有獨立physical-event validation；沒有證明persistent identity、長時追蹤、校準confidence、精確動作時間、false-negative performance或Graph寫入安全。588×336縮圖、Uniform8稀疏採樣、已知DEV案例與僅兩次生成也是限制。
