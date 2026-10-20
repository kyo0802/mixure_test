# 模型引用影格複核補充

2026-10-20；AI 原片裁決後，額外實際查看 39 組模型引用前／後影格，共 13 張比較圖。沒有再跑模型。

## 結果

| 模型 | 審閱候選 | 引用支持 | 引用不支持 | 不確定 | 去重後支持的正事件（所有候選） | Strict 支持的正事件 |
|---|---:|---:|---:|---:|---:|---:|
| qwen | 4 | 1 | 2 | 1 | 1 | 0 |
| videollama | 1 | 0 | 1 | 0 | 0 | 0 |
| nemotron | 34 | 12 | 13 | 9 | 9 | 7 |

對已視覺確認屬同一局部轉換的候選去重，再使用既有 maximum-cardinality one-to-one matcher；0、0.2、0.5 秒的結果相同。配對索引、代表候選 ID、參考事件 ID 均保留於 positive_only_ai_comparison.json。

**這是 15 個 AI 正事件參考中的探索性命中數，不是正式 recall／precision／F1。** 引用不支持不代表整段影片沒有該事件：例如前後都已拿著手機，事件可能較早發生，但選錯 BEFORE 引用。39 筆是依時間鄰近選出的子集，剩餘 128 筆沒有做模型引用視覺裁決，不當成正確或錯誤。

## 可確認的問題

- 多個候選把「已經持有」到「繼續持有」標成 PICKUP，或把桌面接觸誤當離桌；只看時間重疊會高估能力。
- 有些候選在原片附近確有事件，但引用結束太早、物件被擋住，無法支持輸出的 AFTER 狀態。
- Qwen 有引用支持的事件候選，但仍是原始 strict-invalid，不能因視覺合理就改成 strict-valid。
- Nemotron 在這個正事件候選子集提供最多可支持局部轉換；尚不能推論整體較準確，因未完整評估它的其他候選與誤報。
- Wrong-target 在這個子集未建立可證實的錯誤，不等於全體零錯誤。物理 state 一致性僅評估本次 39 筆事件引用的前後狀態，沒有審完 6,420 個 state claims。

## 逐筆依據

| # | 候選 | 裁決 | 原片引用判斷 |
|---:|---|---|---|
| 1 | [qwen:test1__C0004:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_01.jpg) | SUPPORTED | 前格手機由桌面支撐，後格手持離桌。 |
| 2 | [qwen:test4__C0005:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_01.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 引用前格手機已手持，後格仍手持；缺少桌面前狀態。 |
| 3 | [qwen:test6__W02:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_01.jpg) | UNCERTAIN | 後格正在傾斜，接觸面模糊；引用尚不足以確認離桌。 |
| 4 | [qwen:test7__C0005:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_02.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前後皆已手持。 |
| 5 | [videollama:test7__W05:1](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_02.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前後皆為桌面抓握，後格尚未呈現明確離桌。 |
| 6 | [nemotron:test1__W01:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_02.jpg) | SUPPORTED | 前格手機在手中下降，後格平放桌面且手仍接觸；支持支撐狀態變化，不主張此時完全鬆手。 |
| 7 | [nemotron:test1__C0004:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_03.jpg) | SUPPORTED | 桌面手機變成手持，與原片同一局部拿起相符。 |
| 8 | [nemotron:test1__C0005:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_03.jpg) | SUPPORTED | 桌面手機變成手持；與 #7 同一局部拿起，不能重算事件。 |
| 9 | [nemotron:test1__C0006:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_03.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前後皆已手持。 |
| 10 | [nemotron:test2__W02:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_04.jpg) | UNCERTAIN | 後格抓握桌面手機，支撐是否解除不清楚。 |
| 11 | [nemotron:test2__C0001:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_04.jpg) | UNCERTAIN | 後格手機位於影像下緣，支撐後狀態不充分。 |
| 12 | [nemotron:test2__C0002:1](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_04.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前後手機都在桌面受手接觸，缺手持前狀態。 |
| 13 | [nemotron:test2__C0005:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_05.jpg) | UNCERTAIN | 後格傾斜抓握，但無充分可見離桌狀態。 |
| 14 | [nemotron:test3__W01:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_05.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 後格仍桌面接觸；時間早於可見拿起。 |
| 15 | [nemotron:test3__W03:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_05.jpg) | SUPPORTED | 前格手機在桌面，後格右上邊緣可見手持手機。 |
| 16 | [nemotron:test3__W04:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_06.jpg) | SUPPORTED | 前格桌面，後格手機明確抬離；與 #15 同一局部拿起。 |
| 17 | [nemotron:test3__C0007:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_06.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 後格仍平放桌面被接觸。 |
| 18 | [nemotron:test4__W01:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_06.jpg) | UNCERTAIN | 後格僅傾斜，是否仍由桌面支撐不明。 |
| 19 | [nemotron:test4__W02:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_07.jpg) | SUPPORTED | 前格桌面，後格手機已明確手持離桌。 |
| 20 | [nemotron:test4__W03:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_07.jpg) | UNCERTAIN | 前格手機已開始抬起／傾斜，支撐前狀態不能確定。 |
| 21 | [nemotron:test4__W07:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_07.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前格已手持，後格被球遮擋，不支持引用中的拿起轉換。 |
| 22 | [nemotron:test4__C0001:1](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_08.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前後皆手持，未呈現放下。 |
| 23 | [nemotron:test4__C0002:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_08.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前後皆已在桌面，手由接觸變成退出，不提供手持前狀態。 |
| 24 | [nemotron:test4__C0003:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_08.jpg) | SUPPORTED | 由明確手持變成桌面平放、手仍接觸；支持支撐轉換，不主張已完全鬆手。 |
| 25 | [nemotron:test4__C0005:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_09.jpg) | SUPPORTED | 桌面手機變為手持，與 #19 同一局部拿起。 |
| 26 | [nemotron:test4__C0007:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_09.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前格已手持，後格被球遮擋；缺拿起前狀態。 |
| 27 | [nemotron:test5__W05:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_09.jpg) | UNCERTAIN | 後格手機在箱子後／內不可見，不能由手臂姿勢確認持握後狀態。 |
| 28 | [nemotron:test5__C0006:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_10.jpg) | SUPPORTED | 前格桌面手機，後格明確手持離桌。 |
| 29 | [nemotron:test6__W02:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_10.jpg) | UNCERTAIN | 後格傾斜且模糊，無充分離桌證據。 |
| 30 | [nemotron:test6__W04:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_10.jpg) | SUPPORTED | 前格桌面，後格明確手持。 |
| 31 | [nemotron:test6__C0006:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_11.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前後皆桌面抓握。 |
| 32 | [nemotron:test6__C0010:1](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_11.jpg) | UNCERTAIN | 後格手機被手遮擋於頂面邊緣，引用無充分可辨認的支撐後狀態。 |
| 33 | [nemotron:test7__W05:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_11.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前後皆桌面抓握，尚未明確離桌。 |
| 34 | [nemotron:test7__C0005:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_12.jpg) | SUPPORTED | 桌面手機變成手持。 |
| 35 | [nemotron:test8__C0013:1](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_12.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前後皆為平台上的手機受手接觸，未呈現手持到支撐轉換。 |
| 36 | [nemotron:test9__W01:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_12.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前後手機皆在桌面，後格只是手接觸。 |
| 37 | [nemotron:test9__C0009:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_13.jpg) | NOT_SUPPORTED_BY_CITED_STATES | 前後手機皆在桌面，後格只是手接觸。 |
| 38 | [nemotron:test9__C0010:0](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_13.jpg) | SUPPORTED | 由桌面手機變成手持，明確可見離桌。 |
| 39 | [nemotron:test9__C0013:1](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/model_citations/page_13.jpg) | UNCERTAIN | 前後手機都受到手與白色裝置遮擋，無充分手持前／支撐後狀態。 |

## 驗證

既有 GT consolidation CPU 測試 21／21 通過；2,235 個保留檔案 SHA 驗證通過。無新模型推論、無 GT 原檔覆寫、無 Graph 更新、無 commit／push。

本次完成：原始 34 組 AI 裁決與 39 筆模型引用複核、合資格的局部正事件探索性對照。全體正式模型評分仍因完備範圍、剩餘模型引用與身分資格不足而不輸出分數。
