# Qwen NF4 結構化輸出失敗稽核

日期：2026-10-15。CPU-only，原始輸出不改寫。

## 母體與證據

PRIMARY = `v2_20261014_owned_tree`，11 條件 × (1 warmup + 2 measured) = 33 次生成，15 pass / 18 fail。Warmup 6/11 pass，measured 9/22 pass；沒有排除 warmup。ENGINEERING_HISTORY = `v1_20261014`，另 33 次，12 pass / 21 fail。CSV 有 66 列，以 population 欄分組；不能把 66 列當獨立研究樣本。CPU processor replay、mock、smoke 不納入母體。

兩輪所有 raw、iteration receipt、transport raw/receipt 都找回；66/66 strict replay 與歷史完整 error object 相同。schema/validator 檔案與歷史 inventory hash 相符。主要 completion receipt 驗證 422 檔，capacity_results 的 hash：`7d8fed22e866609b30b85f7f4d34b3beffdf46e98220dd435a0450391d6fc712`。原始 capacity、資源回條、prompt/rendered SHA、generation settings、allowlist 與 EOS 逐列記錄在 [primary_attempts.json](primary_attempts.json) 與 [CSV](QWEN_NF4_STRUCTURED_OUTPUT_AUDIT.csv)。早期回條獨立核對，不混入主要比例。

## 最先失敗與被遮住的錯誤

13/33 次 `EMPTY_REQUIRED_UNCERTAINTY`：`events[i].timing_uncertainty == ""`，違反 minLength=1，共 18 個事件欄位；5/33 次 `EMPTY_REQUIRED_CITATIONS`：`window_cited_frame_aliases == []`，違反 minItems=1。這 18 次最先失敗階段均為 SCHEMA，必填欄位未遺漏，值為空。

其中 11/33 次另有 `OTHER_SEMANTIC_ERROR`：宣稱已知狀態而 supporting_frame_alias=null。獨立逐欄診斷發現，但歷史 validator 的 schema early-return 尚未走到該檢查；不把它說成原本已回報的 semantic error，不修改模型回答以使 replay 繼續。全部 18 次的 exact path/constraint、次要訊息與來源 hash 见下表及 JSON。

33/33 raw 可嚴格解析為 JSON object，33/33 明確 EOS（末 token 在 receipt EOS IDs 中）；0 timeout、0 output cap、0 Markdown fence、0 不支持／未處理 alias、0 reference 當事件 alias、0 replay mismatch。EOS 是 token receipt 證據，不是看起來像完整 JSON 的推測。citation 檢查是 alias 與範圍核對，不是像素 grounding 正確性保證。

## 報告事件數與通過

| 解析事件數 | Attempts | Pass | Fail | Token range | EOS / cap / timeout |
|---|---|---|---|---|---|
| 0 | 20 | 15 | 5 | [174, 285] | 20 / 0 / 0 |
| 1 | 8 | 0 | 8 | [344, 371] | 8 / 0 / 0 |
| 2+ | 5 | 0 | 5 | [605, 633] | 5 / 0 / 0 |
| UNKNOWN | 0 | 0 | 0 | None | 0 / 0 / 0 |

結論：**SUPPORTED_DESCRIPTIVELY**。事件非空的 13 份全失敗；零事件 20 份中 15 pass / 5 fail。更多事件帶來更多 object/key/citation 及更多必填欄位，觀察到複雜度與失敗相關。可確認的直接原因是欄位約束違反；沒有確認「複雜度造成」違反。事件數與表示法、frame count、reference、視覺 token 都混雜。

通過回答全為 NO_CONFIRMED_EVENT；這是格式相容，不證明能偵測事件。gradient/checkerboard 合成 fixture 沒有本研究使用的人工物理 GT，不能把輸出事件數當真正事件數。

## 長度與結構

| 群組 | Token range | Token median | Raw character range |
|---|---|---|---|
| True | [225, 285] | 231 | [688, 787] |
| False | [174, 633] | 353.0 | [641, 1975] |

事件回答 344–633 tokens，零事件回答 174–285。最短失敗 174 tokens，比通過回答還短；最長回答 633/1024，未截斷。無證據以增加輸出 cap 作為優先修補。真實多事件仍可能超過 1024，該上限尚不具充分性保證。

複雜度定義：解析 event entries、distinct types、object/key/array element count、JSON depth、citation entries/aliases、missing required、populated optional、uncertainty 欄位與 timing alias fields。structural_complexity_score = object_count + key_count + array_element_count，是描述性計數而非經驗證難度指標。現在 optional_fields=0，missing_required=0；不能把空值稱為漏欄位。Malformed outputs 的 event_count 必須 UNKNOWN；本母體沒有 malformed case，不用 regex 猜事件數。

## 逐條件

| Condition | Strict pass | Source / consumed | Visual tokens | Reference | Generated tokens |
|---|---|---|---|---|---|
| MULTI_8_P200704 | 3/3 | 8 / 8 | 2016 | 0 | [231, 231] |
| STORY_8_P200704 | 3/3 | 8 / 8 | 240 | 0 | [229, 229] |
| MULTI_12_P200704 | 0/3 | 12 / 12 | 3024 | 0 | [605, 605] |
| STORY_12_P200704 | 0/3 | 12 / 12 | 238 | 0 | [174, 174] |
| MULTI_16_P200704 | 0/3 | 16 / 16 | 4032 | 0 | [362, 633] |
| STORY_16_P200704 | 2/3 | 16 / 16 | 238 | 0 | [285, 371] |
| VIDEO_SHORT8_P200704 | 3/3 | 8 / 8 | 1008 | 0 | [225, 225] |
| VIDEO_LONG118_P200704 | 3/3 | 118 / 14 | 1764 | 0 | [274, 274] |
| VIDEO_LONG118_P937664 | 1/3 | 118 / 14 | 8372 | 0 | [176, 273] |
| MULTI_8_REF1_P200704 | 0/3 | 8 / 8 | 2070 | 1 | [353, 359] |
| VIDEO_LONG118_REF1_P200704 | 0/3 | 118 / 14 | 1818 | 1 | [344, 352] |

Multi-image：3/12 pass；Storyboard：5/9；Video：7/12。共用一個 V3 task+schema hash 與 V2 system hash、greedy、1024 cap；frame/pixel/token/reference 因子不同，不能作為表示法的因果效果。

Multi8 NONE 是 0-event 3/3 pass，Multi8 REF1 是 1-event 0/3 pass；Long118 low-budget NONE 0-event 3/3 pass，REF1 1-event 0/3 pass。兩對 source pixel-digests 與非 reference 設定相同（詳 source metadata）；reference 額外 54 visual tokens、67 input tokens且更改 prompt framing。沒有 reference alias 當 event 引用、target_id 漏寫或未知 alias。REF1 輸出較長且有事件，但不能由 3 次重複斷言 reference 造成 JSON failure；也不能以失敗降低而推論 NONE 更準。

## 每個主要失敗

| Condition/iteration | Event count | Exact historical errors | Secondary diagnostic | EOS/cap | Raw source |
|---|---|---|---|---|---|
| MULTI_12_P200704/0 | 2 | /events/0/timing_uncertainty:'' should be non-empty; /events/1/timing_uncertainty:'' should be non-empty | /events/0/after_state:KNOWN_STATE_MISSING_SUPPORT ; /events/1/before_state:KNOWN_STATE_MISSING_SUPPORT | true/false | [iteration_0_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/MULTI_12_P200704/iteration_0_raw.txt>) |
| MULTI_12_P200704/1 | 2 | /events/0/timing_uncertainty:'' should be non-empty; /events/1/timing_uncertainty:'' should be non-empty | /events/0/after_state:KNOWN_STATE_MISSING_SUPPORT ; /events/1/before_state:KNOWN_STATE_MISSING_SUPPORT | true/false | [iteration_1_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/MULTI_12_P200704/iteration_1_raw.txt>) |
| MULTI_12_P200704/2 | 2 | /events/0/timing_uncertainty:'' should be non-empty; /events/1/timing_uncertainty:'' should be non-empty | /events/0/after_state:KNOWN_STATE_MISSING_SUPPORT ; /events/1/before_state:KNOWN_STATE_MISSING_SUPPORT | true/false | [iteration_2_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/MULTI_12_P200704/iteration_2_raw.txt>) |
| STORY_12_P200704/0 | 0 | /window_cited_frame_aliases:[] should be non-empty | none | true/false | [iteration_0_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/STORY_12_P200704/iteration_0_raw.txt>) |
| STORY_12_P200704/1 | 0 | /window_cited_frame_aliases:[] should be non-empty | none | true/false | [iteration_1_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/STORY_12_P200704/iteration_1_raw.txt>) |
| STORY_12_P200704/2 | 0 | /window_cited_frame_aliases:[] should be non-empty | none | true/false | [iteration_2_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/STORY_12_P200704/iteration_2_raw.txt>) |
| MULTI_16_P200704/0 | 1 | /events/0/timing_uncertainty:'' should be non-empty | /events/0/after_state:KNOWN_STATE_MISSING_SUPPORT ; /last_directly_supported_state:KNOWN_LAST_STATE_MISSING_SUPPORT | true/false | [iteration_0_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/MULTI_16_P200704/iteration_0_raw.txt>) |
| MULTI_16_P200704/1 | 2 | /events/0/timing_uncertainty:'' should be non-empty; /events/1/timing_uncertainty:'' should be non-empty | /events/0/after_state:KNOWN_STATE_MISSING_SUPPORT ; /events/1/before_state:KNOWN_STATE_MISSING_SUPPORT | true/false | [iteration_1_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/MULTI_16_P200704/iteration_1_raw.txt>) |
| MULTI_16_P200704/2 | 2 | /events/0/timing_uncertainty:'' should be non-empty; /events/1/timing_uncertainty:'' should be non-empty | /events/0/after_state:KNOWN_STATE_MISSING_SUPPORT ; /events/1/before_state:KNOWN_STATE_MISSING_SUPPORT | true/false | [iteration_2_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/MULTI_16_P200704/iteration_2_raw.txt>) |
| STORY_16_P200704/2 | 1 | /events/0/timing_uncertainty:'' should be non-empty | /events/0/after_state:KNOWN_STATE_MISSING_SUPPORT ; /last_directly_supported_state:KNOWN_LAST_STATE_MISSING_SUPPORT | true/false | [iteration_2_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/STORY_16_P200704/iteration_2_raw.txt>) |
| VIDEO_LONG118_P937664/1 | 0 | /window_cited_frame_aliases:[] should be non-empty | none | true/false | [iteration_1_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/VIDEO_LONG118_P937664/iteration_1_raw.txt>) |
| VIDEO_LONG118_P937664/2 | 0 | /window_cited_frame_aliases:[] should be non-empty | none | true/false | [iteration_2_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/VIDEO_LONG118_P937664/iteration_2_raw.txt>) |
| MULTI_8_REF1_P200704/0 | 1 | /events/0/timing_uncertainty:'' should be non-empty | /events/0/after_state:KNOWN_STATE_MISSING_SUPPORT | true/false | [iteration_0_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/MULTI_8_REF1_P200704/iteration_0_raw.txt>) |
| MULTI_8_REF1_P200704/1 | 1 | /events/0/timing_uncertainty:'' should be non-empty | /events/0/after_state:KNOWN_STATE_MISSING_SUPPORT | true/false | [iteration_1_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/MULTI_8_REF1_P200704/iteration_1_raw.txt>) |
| MULTI_8_REF1_P200704/2 | 1 | /events/0/timing_uncertainty:'' should be non-empty | /events/0/after_state:KNOWN_STATE_MISSING_SUPPORT | true/false | [iteration_2_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/MULTI_8_REF1_P200704/iteration_2_raw.txt>) |
| VIDEO_LONG118_REF1_P200704/0 | 1 | /events/0/timing_uncertainty:'' should be non-empty | /events/0/before_state:KNOWN_STATE_MISSING_SUPPORT ; /events/0/after_state:KNOWN_STATE_MISSING_SUPPORT ; /last_directly_supported_state:KNOWN_LAST_STATE_MISSING_SUPPORT | true/false | [iteration_0_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/VIDEO_LONG118_REF1_P200704/iteration_0_raw.txt>) |
| VIDEO_LONG118_REF1_P200704/1 | 1 | /events/0/timing_uncertainty:'' should be non-empty | none | true/false | [iteration_1_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/VIDEO_LONG118_REF1_P200704/iteration_1_raw.txt>) |
| VIDEO_LONG118_REF1_P200704/2 | 1 | /events/0/timing_uncertainty:'' should be non-empty | none | true/false | [iteration_2_raw.txt](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/runs/VIDEO_LONG118_REF1_P200704/iteration_2_raw.txt>) |

空 timing 的 minLength 和空 citations 的 minItems 是明確規則。known-state/null-support 也有明確現行 semantic guard。真正內部認知機制（模型是否將空字串理解成沒有不確定性）未證實；不將一種合理猜測寫成 root cause。NEXT：prospective prompt field clarification + 獨立 target/time 語意檢視，再經授權做新合成 regression。歷史15/33永不改寫。

## 早期歷史

早期33：12 pass、21 fail；15次空 timing、6次空 window citations，14次被遮住的known-state/null-support。CPU監控第一輪曾只監控launcher；該CPUpeak無效，但raw/生成/EOS/validator回條仍可核對。兩輪並非独立dataset，差異展示greedy+seed也不能保證穩定性。本次audit首版matcher把 adapter後加citation_allowed_aliases誤當transport原欄位，造成匹配報警；中間產物保存在diagnostic_initial，核對程式來源後排除僅該後加欄位，其他resource欄位、raw SHA、耗時全部精確匹配。最终66次無遺漏；未改來源回條。
