# 原片視覺裁決與三模型比較報告

更新：2026-10-20。來源：`artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/`。

## 已完成與適用範圍

依你授權代為裁決，已檢視 test1–test9 原片的按時間排序影格，完成 34 組裁決。15 個可見物理轉換：8 個 PICKUP、7 個 PLACEMENT；13 個物理轉換不確定；另 6 組為接觸、鏡頭移動、遮擋描述。

**這是 AI 原片視覺複核，不是新增人工標註或人工完備性背書。** 全片概覽每秒一格，事件細節每 0.25 秒一格，部分邊界每 0.1 秒一格；沒有宣稱逐格連續播放。證據保留原片 SHA、native PTS、來源格號與接觸表。

原始兩位 JSON、主裁決 CSV、coverage CSV、模型輸出與歷史結果保持不變。新 final_gt.json 明確標記 AI_ADJUDICATED_REFERENCE_NOT_HUMAN_GT，不能冒充 HUMAN_REVIEWED 進入既有正式評分。

## 關鍵修正

- 手把手機移進箱子、籃球或玩偶後方，不能只憑手最後退出就確認放置；這些案例保留不確定。
- 多支影片開頭只見手機在畫面下緣、手接觸後離開，沒有充分手持前狀態，不硬標 PLACEMENT。
- test7 的 CONTACT_ONLY 原區間含真正拿起動作，縮至離桌前接觸片段。
- test8 的拿起候選在抓握後離開畫面，缺少清楚離桌畫面，保留不確定。
- test9 的 G031 是球的接觸、G034 是手機的鏡頭移動；依原始類別分開處理。
- 事件只主張可見局部轉換，不跨離鏡或長遮擋認定全程同一個物理實例。

## 逐組裁決與原片依據

時間為前／後證據影格，並非事件持續時間。UNCERTAIN 不是否認事件曾發生，也不是負例。每組原始 event_id、reviewer、confidence、evidence references 完整保留於 adjudication_decisions.json。

### G001 · test1 · PICKUP

- 原始：KUO PICKUP 2.234–2.978 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。手機首次出現在畫面時已被拿著；看不到由支撐面離開的過程。
- 原片證據：[2.268s / f68](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test1_detail_1/page_01.jpg)；[2.768s / f83](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test1_detail_1/page_01.jpg)

### G002 · test1 · PLACEMENT

- 原始：annotator_huang PLACEMENT 4.468–6.12 秒；KUO PLACEMENT 4.551–6.421 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。先看到手持手機下降至桌面，之後手離開且手機留在桌上。
- 原片證據：[3.768s / f113](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test1_detail_1/page_01.jpg)；[6.270s / f188](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test1_detail_1/page_02.jpg)

### G003 · test1 · PICKUP

- 原始：annotator_huang PICKUP 11.53–14.44 秒；KUO PICKUP 10.4–12.149 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。手機由桌面支撐變成手持離桌；兩人較寬的時間範圍改以可見前後狀態定位。
- 原片證據：[11.505s / f345](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test1_detail_2/page_01.jpg)；[11.772s / f353](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test1_detail_2/page_01.jpg)

### G004 · test1 · PLACEMENT

- 原始：KUO PLACEMENT 12.165–16.012 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。手機及手移至籃球後方；手退出並不能證明遮擋中的手機已鬆手放下。
- 原片證據：[13.507s / f405](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test1_detail_2/page_02.jpg)；[16.007s / f480](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test1_detail_2/page_03.jpg)

### G005 · test2 · PLACEMENT

- 原始：annotator_huang PLACEMENT 3.5–5.81 秒；KUO PLACEMENT 3.52–6.869 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。先手持接近桌面，之後手機獨立留在桌上，手已撤離。
- 原片證據：[3.005s / f90](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test2_overview/page_01.jpg)；[5.775s / f173](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test2_detail_1/page_01.jpg)

### G006 · test2 · PICKUP

- 原始：annotator_huang PICKUP 10.22–10.51 秒；KUO PICKUP 10.382–11.505 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。手機先在桌面，後傾斜並隨手抬起。
- 原片證據：[10.282s / f308](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test2_detail_2/page_01.jpg)；[10.782s / f323](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test2_detail_2/page_01.jpg)

### G007 · test2 · PLACEMENT

- 原始：annotator_huang PLACEMENT 19.41–22.63 秒；KUO PLACEMENT 18.011–24.51 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。手機移到玩偶後方後被遮擋，無可見釋放與支撐後狀態。
- 原片證據：[19.778s / f593](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test2_detail_3/page_01.jpg)；[24.502s / f735](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test2_detail_3/page_03.jpg)

### G008 · test3 · PLACEMENT

- 原始：annotator_huang PLACEMENT 6.07–7.19 秒；KUO PLACEMENT 4.865–7.716 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。手機由畫面下緣進入；已見平放受手接觸，缺乏可確認的手持前狀態。手撤離本身不是放置轉換。
- 原片證據：[3.905s / f117](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test3_boundary_3.5/page_01.jpg)；[6.275s / f188](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test3_detail_1/page_01.jpg)

### G009 · test3 · PICKUP

- 原始：annotator_huang PICKUP 13.53–15.03 秒；KUO PICKUP 14.729–15.183 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。手機由桌面支撐，經傾斜後明確被手拿起。
- 原片證據：[14.505s / f435](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test3_detail_2/page_01.jpg)；[15.005s / f450](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test3_detail_2/page_01.jpg)

### G010 · test3 · PLACEMENT

- 原始：KUO PLACEMENT 16.119–20.135 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。手機進入不透明箱內，手退出後仍看不到手機或釋放動作。
- 原片證據：[16.273s / f488](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test3_detail_2/page_01.jpg)；[20.280s / f608](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test3_detail_2/page_03.jpg)

### G011 · test4 · PLACEMENT

- 原始：annotator_huang PLACEMENT 6.6–8.74 秒；KUO PLACEMENT 3.425–8.368 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。手機由手持下降至桌面，手離開後手機仍留在桌面。
- 原片證據：[6.275s / f188](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test4_detail_1/page_01.jpg)；[8.278s / f248](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test4_detail_1/page_01.jpg)

### G012 · test4 · CAMERA_MOTION_ONLY

- 原始：KUO CAMERA_MOTION_ONLY 10.235–11.702 秒
- 裁決：**ACCEPT / DESCRIPTIVE_OBSERVATION**。採樣畫面中手機相對桌面保持不動，鏡頭改變；僅支持這段可見狀態描述。
- 原片證據：[10.015s / f300](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test4_detail_2/page_01.jpg)；[11.767s / f353](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test4_detail_2/page_01.jpg)

### G013 · test4 · PICKUP

- 原始：annotator_huang PICKUP 12.23–14.94 秒；KUO PICKUP 12.291–14.6 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。手機由桌面支撐變成手持離桌。
- 原片證據：[13.002s / f390](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test4_detail_3/page_01.jpg)；[13.503s / f405](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test4_detail_3/page_01.jpg)

### G014 · test4 · PLACEMENT

- 原始：KUO PLACEMENT 15.602–18.525 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。手機被籃球遮住；手退出後無可見手機支撐狀態，不確認放置。
- 原片證據：[15.773s / f473](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test4_detail_3/page_02.jpg)；[18.510s / f555](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test4_detail_3/page_03.jpg)

### G015 · test5 · PLACEMENT

- 原始：annotator_huang PLACEMENT 3.67–5.47 秒；KUO PLACEMENT 2.165–4.546 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。手機初次可見時位於畫面下緣，未看清由手持到桌面支撐的轉換。
- 原片證據：[2.200s / f66](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test5_boundary_1.5/page_01.jpg)；[4.267s / f128](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test5_detail_1/page_01.jpg)

### G016 · test5 · PICKUP

- 原始：annotator_huang PICKUP 12.39–13.21 秒；KUO PICKUP 12.783–13.886 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。桌面上的手機傾斜並被手抬離。
- 原片證據：[12.767s / f383](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test5_detail_2/page_01.jpg)；[13.267s / f398](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test5_detail_2/page_01.jpg)

### G017 · test5 · PLACEMENT

- 原始：KUO PLACEMENT 14.269–18.125 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。手機移入箱內後不可見；不能以空手退出推定放置完成。
- 原片證據：[14.500s / f435](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test5_detail_2/page_01.jpg)；[18.500s / f555](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test5_detail_2/page_03.jpg)

### G018 · test6 · PLACEMENT

- 原始：KUO PLACEMENT 5.954–7.278 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。首次清楚看見手機時已在下緣桌面受手接觸，缺少手持前狀態。
- 原片證據：[5.208s / f156](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test6_boundary_4/page_02.jpg)；[6.275s / f188](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test6_detail_1/page_01.jpg)

### G019 · test6 · PICKUP

- 原始：annotator_huang PICKUP 11.76–13.82 秒；KUO PICKUP 13.136–15.248 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。由桌面支撐變成手持離桌。
- 原片證據：[12.768s / f383](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test6_detail_2/page_01.jpg)；[13.270s / f398](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test6_detail_2/page_01.jpg)

### G020 · test6 · PLACEMENT

- 原始：annotator_huang PLACEMENT 23.02–25.44 秒；KUO PLACEMENT 23.058–25.88 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。手持手機下降至微波爐頂部右側；手離開後可見手機獨立平放。
- 原片證據：[23.500s / f705](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test6_detail_3/page_01.jpg)；[25.770s / f773](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test6_detail_3/page_01.jpg)

### G021 · test7 · PLACEMENT

- 原始：KUO PLACEMENT 4.66–6.197 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。初段手機位於畫面下緣；只能確認後來在桌上，無充分手持到支撐的可見轉換。
- 原片證據：[3.505s / f105](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test7_boundary_3/page_01.jpg)；[6.008s / f180](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test7_detail_1/page_01.jpg)

### G022 · test7 · PICKUP

- 原始：annotator_huang PICKUP 11.91–13.94 秒；KUO PICKUP 14.101–14.809 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。先在桌面，後被拿起。KUO 的起點晚於可見離桌轉換。
- 原片證據：[12.768s / f383](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test7_detail_2/page_01.jpg)；[13.270s / f398](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test7_detail_2/page_01.jpg)

### G023 · test7 · CONTACT_ONLY

- 原始：KUO CONTACT_ONLY 12.285–14.357 秒
- 裁決：**MODIFY / MODIFIED_DESCRIPTIVE_OBSERVATION**。原 CONTACT_ONLY 延伸至 14.357 秒，已涵蓋拿起；縮至離桌前接觸片段。13.270 秒已手持，不能整段當純接觸負例。
- 原片證據：[12.268s / f368](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test7_detail_2/page_01.jpg)；[12.768s / f383](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test7_detail_2/page_01.jpg)

### G024 · test7 · PLACEMENT

- 原始：annotator_huang PLACEMENT 25.89–32.44 秒；KUO PLACEMENT 23.665–28.405 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。約 31 秒前仍手持，後被玩偶遮住；原放置區間末端未提供可見釋放證據。
- 原片證據：[31.012s / f930](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test7_detail_3/page_03.jpg)；[35.268s / f1058](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test7_detail_3/page_04.jpg)

### G025 · test7 · OCCLUSION_INSUFFICIENT_EVIDENCE

- 原始：KUO OCCLUSION_INSUFFICIENT_EVIDENCE 31.504–36.788 秒
- 裁決：**ACCEPT / DESCRIPTIVE_OBSERVATION**。保留手機被玩偶遮擋、事件不可確認的紀錄；不是無事件證明。
- 原片證據：[31.512s / f945](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test7_detail_3/page_03.jpg)；[37.003s / f1110](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test7_overview/page_04.jpg)

### G026 · test8 · PLACEMENT

- 原始：KUO PLACEMENT 6.385–6.94 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。手機從畫面下緣出現時已接近桌面；無清楚手持前狀態，不由手離開推定放置。
- 原片證據：[5.808s / f174](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test8_boundary_4.5/page_02.jpg)；[6.777s / f203](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test8_detail_1/page_01.jpg)

### G027 · test8 · PICKUP

- 原始：annotator_huang PICKUP 14.34–16.55 秒；KUO PICKUP 13.835–16.014 秒
- 裁決：**UNCERTAIN / INSUFFICIENT_VISIBLE_TRANSITION**。抓握後鏡頭移動使手機離開畫面；未明確看見手機離開支撐面，後段再出現不能補證此瞬間。
- 原片證據：[14.270s / f428](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test8_boundary_14.25/page_01.jpg)；[14.772s / f443](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test8_boundary_14.25/page_01.jpg)

### G028 · test8 · PLACEMENT

- 原始：annotator_huang PLACEMENT 29.7–30.7 秒；KUO PLACEMENT 29.67–30.957 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。手持手機下降至窗邊平台，手撤離後手機仍留在支撐物上。
- 原片證據：[28.508s / f855](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test8_detail_3/page_01.jpg)；[30.512s / f915](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test8_detail_3/page_01.jpg)

### G029 · test9 · PLACEMENT

- 原始：KUO PLACEMENT 6.756–8.469 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。手持手機下降至球與箱子之間；後方可見手機邊緣平放，手已離開。部分遮擋但有後狀態。
- 原片證據：[6.777s / f203](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_1/page_01.jpg)；[8.780s / f263](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_1/page_01.jpg)

### G030 · test9 · OCCLUSION_INSUFFICIENT_EVIDENCE

- 原始：KUO OCCLUSION_INSUFFICIENT_EVIDENCE 10.365–11.423 秒
- 裁決：**ACCEPT / DESCRIPTIVE_OBSERVATION**。球遮住手機，保留不可判定紀錄；不自動當沒有拿起或放下。
- 原片證據：[10.282s / f308](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_1/page_02.jpg)；[11.500s / f345](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_1/page_02.jpg)

### G031 · test9 · CONTACT_ONLY

- 原始：KUO CONTACT_ONLY 17.473–18.393 秒
- 裁決：**ACCEPT / DESCRIPTIVE_OBSERVATION**。原標的是 Ball：手推動桌面上的球，球仍由桌面支撐；不是手機接觸事件。
- 原片證據：[17.508s / f525](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_2/page_01.jpg)；[18.277s / f548](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_2/page_01.jpg)

### G032 · test9 · PICKUP

- 原始：annotator_huang PICKUP 20.04–20.45 秒；KUO PICKUP 19.604–20.781 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。手機原在桌面，之後明確手持離桌。
- 原片證據：[20.012s / f600](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_2/page_02.jpg)；[20.280s / f608](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_2/page_02.jpg)

### G033 · test9 · PLACEMENT

- 原始：annotator_huang PLACEMENT 29.06–30.65 秒；KUO PLACEMENT 26.978–31.013 秒
- 裁決：**MODIFY / VISUALLY_SUPPORTED_TRANSITION**。手持手機下降到微波爐頂；手撤離後可見白色圓柱後的黑色手機邊緣，後續角度也顯示手機平放。
- 原片證據：[27.773s / f833](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_3/page_01.jpg)；[30.512s / f915](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_3/page_02.jpg)

### G034 · test9 · CAMERA_MOTION_ONLY

- 原始：KUO CAMERA_MOTION_ONLY 33.663–35.715 秒
- 裁決：**MODIFY / MODIFIED_DESCRIPTIVE_OBSERVATION**。原標的是 Phone：可見段手機留在微波爐頂、鏡頭移動；縮至仍可辨認手機的段落，後來移出畫面的部分不視為可評負例。
- 原片證據：[33.782s / f1013](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_4/page_01.jpg)；[35.000s / f1050](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/evidence/test9_detail_4/page_01.jpg)

## 552 次既有推論：格式與事件候選比較

| 模型 | 完成 | 原始 JSON 合法 | Schema 合法 | Strict 合法 | 事件候選 | Strict 事件候選 |
|---|---:|---:|---:|---:|---:|---:|
| qwen | 184 | 0 | 0 | 0 | 6 | 0 |
| videollama | 184 | 147 | 144 | 83 | 15 | 2 |
| nemotron | 184 | 166 | 163 | 108 | 146 | 58 |

Strict-invalid 仍然保留，不等於 NO_EVENT。Qwen 外層 code fence 中的內容可以描述性查看，不能回寫成原始 strict-valid。候選多不代表更準確；沒有因此宣布 Nemotron 勝出。

### 時間鄰近的候選檢索（不是 TP、recall 或實體匹配）

只查同片、同事件類型、文字包含 phone 的候選。以既有 interval_distance 在 0／0.2／0.5 秒找前後證據 bracket 的距離；以下是有任何候選接近的不同參考事件數，同一事件多窗命中只計一個參考 ID。沒有用此規則合併模型事件。

| 模型 | 所有候選：0 / .2 / .5 秒 | Strict 候選：0 / .2 / .5 秒 |
|---|---|---|
| qwen | 3 / 4 / 4 | 0 / 0 / 0 |
| videollama | 1 / 1 / 1 | 0 / 0 / 0 |
| nemotron | 14 / 14 / 14 | 11 / 11 / 11 |

**此表不驗證模型引用影格足以支持事件、不確認目標實例、不證明時間定位正確。** 詳細 proposal ID 與 bracket 留在 temporal_proximity_review.json；它不進入 authoritative 一對一匹配。

## 尚不能報出的分數與原因

- 兩位原始 event_list_exhaustiveness=NOT_ATTESTED 完整保留；採樣複核不足以新增無遮擋且完整的負例範圍。
- 正式 PICKUP／PLACEMENT precision、recall、F1 與整體 F1 均為 unavailable，沒有把未知區間算 FP/TN。
- Wrong-target 與物理 state consistency 尚無逐模型引用影格／實例裁決，因此不填零或推估數字。
- 去重與正式一對一匹配仍要求已確認同一事件／物件；本次不以重疊時間或 phone 字串替代這個要求。
- 15 個可見正事件可用於探索性對照，13 個未確認事件保留日後檢查；沒有因局部不確定刪掉全片的可見證據。

## 交付與狀態

已完成 34 組 AI 裁決、可見正事件參考、證據索引、既有模型格式比較與時間候選檢索。正式實體事件評分未完成，原因是完備範圍與模型引用／實例資格不足，並非要求你再讀 CSV。

可直接閱讀本報告逐組中文判斷並點選原片影格。若要下一步完成正式比較，需對照模型實際引用影格完成物理支持及同一事件裁決，且只在明確完備的局部範圍計算負例相關分數；本次未自行製造這些資格。

狀態：AI_VISUAL_ADJUDICATION_COMPLETE_WITH_UNCERTAINTY；FORMAL_EVENT_METRICS_NOT_ELIGIBLE。未新增模型推論、未更新 Graph、未 commit/push。
