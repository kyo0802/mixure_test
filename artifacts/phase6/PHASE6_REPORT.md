# Phase 6：目標定位與表面感知實作報告

更新：2026-10-21。狀態：**已完成實作、有限真實影格執行與複核；桌面搜尋局部改善，微波爐頂面與可信實例位置仍未達成。**

## 主要結果

本次沿用 Phase 5 的 TemporalMemory／搜尋，新增 Qwen2.5-VL-7B NF4 影格定位與 SAM2.1 small 邊界細化。只處理 test1–test9 共 21 張選定原片影格；不是九片全時段重新辨識，也沒有重跑 552 次事件 benchmark。原 Nemotron 事件及無座標描述保留。

| 項目 | 同格 Phase 5 | Phase 6 |
|---|---:|---:|
| 一般 phone 偵測框 | 13 張／15 框 | 另外產生 14 個 smartphone、5 個 phone_like_unknown |
| 有手機候選區域的影片 | 4／9 | 9／9 |
| 手機候選位置觀察 | 6 | 22 |
| 新表面候選／有 SAM mask | — | 34／32 |
| 新具座標 VLM claim 的局部觀察關聯 | — | 12 |
| 歷史無座標 VLM 描述被解決 | — | 0 |
| 新授權 persistent identities | — | 0 |
| VERIFIED locations | 0 | 0 |

上述是程式計數，不是辨識準確率。22 筆含同一物體由既有 CV 與新定位產生的候選、不同區域關係，不能視為 22 個獨立正確位置。Phase 5 全影片原報告的 6／9 不適合直接比較這裡的同格 4／9。

### 開發者看圖複核（AI 視覺檢查，非人工 GT）

已看完九張 evidence sheets 的全部 21 張原片疊圖，另放大檢查 test2 f85、test3 f274、test5 f288、test8 f300、test9 f546 的 Phase 5／6 同格對照。逐格紀錄見 `artifacts/phase6/VISUAL_REVIEW.md`，不進 runtime 或 GT。

- 14 個 smartphone proposals 中，12 張能合理指向實際手機；test9 f546、f591 框偏移／只覆蓋部分手機。沒有用 IoU GT 判定精度。
- **6 張確實補回原本沒有 phone 框的手機**：test1 f360、test2 f85、test3 f274、test4 f400、test6 f205、test7 f419。test9 f591 不計入成功補回。
- test1 f240、test4 f1050 整筆輸出驗證失敗；test5 f234 的底邊部分手機未輸出，共 3 張仍漏掉可見手機。
- 15 張一般桌面場景有可用於粗略區域查詢的局部桌面遮罩；部分有缺洞、裁切或過寬。這是局部可用性檢查，**不是完整桌面分割通過率**，也不是接觸驗證。
- **微波爐頂面未可靠解決**：多張仍圈到整個機身／櫃體；test7 f954 雖靠近頂面，仍含前緣且標成 tabletop，未計為可靠 microwave_top。
- 5 個 unknown proposals 主要落在背景無線電話／底座；test6 f726 的極小框甚至偏到瓶子附近。沒有把它們當使用者的 smartphone。也未證明模型已能可靠區分 handset／desk_telephone／remote_control。
- test2 f102 模型把手握手機說成 SURFACE_ALIGNED，顯示物理狀態仍可能錯。狀態輸出屬模型假說，沒有升成可信支撐或事件。

### 搜尋有沒有真的改善？

**有局部改善。** test5 f288 與 test8 f300／f372 原有手機框卻沒有可用桌面關係，現在能回傳「該時間的桌面候選」並附框、遮罩與來源。test2 f85 等原本漏掉的手持物體也有影格定位，但只能表示靠近區域。

test9 從 UNKNOWN 變成有候選，然而目標框偏移，**不計為已證實的搜尋品質改善**。9／9 有結果亦不等於找到使用者的手機；所有 category-level 結果保留身分未確認與目前位置未知。

九片 `cup` 查詢皆 UNKNOWN：本次新感知只詢問 smartphone，其他物體入口及持久化已用 deterministic CPU fixture 驗證，尚未做新 cup 感知實驗。以具名 entity 搜尋時，未授權新框不會出現在其候選或附加定位結果。

## 執行與座標契約

- 首次 normalized 0–1000 實驗：21 次呼叫、9 筆可解析／12 筆無效；視覺上仍有座標尺度疑慮，保留在 `artifacts/phase6/demo`，不作最終表現依據。
- 最終明確像素座標版：同樣 21 張、21 次呼叫、19 筆契約通過／2 筆失敗。模型輸入固定 1008 × 560，驗證 processor grid 後映回原始尺寸；不裁切超界座標、不把首次結果重新解釋成 pixels。
- 本任務 **Qwen 總計 42 次針對性感知 generation**。最終 Qwen generation 合計 381.48 秒，peak allocated 6,333,474,304 bytes（約 5.90 GiB），不含載入／解碼／SAM。
- 最終 SAM 60 次 box prompt、57 個 mask 通過幾何接受條件；3.734 秒、peak allocated 約 0.592 GiB。32 是去重後表面遮罩數，57 含物體與未去重表面。reserved 計數可能保留前一模型快取高水位，不代表 SAM 活躍配置。
- SAM mask 受模型 proposal 限制，不是獨立語義或接觸證據；只在該原片影格有效，沒有跨鏡頭沿用幾何。

## 實作與安全邊界

`target_surface.py`：型別、座標／來源檢查、局部關聯、Graph 整合與查詢。
`perception_runtime.py`：重用既有 NF4 loader、保存原始回應、SAM refinement。
`spatial.py`：可選 pixel-mask 幾何關係；舊 polygon 路徑保留。
`pipeline.py`：Phase 6 搜尋分派。
`run_phase6_demo.py`：單一示範／查詢入口。
`test_phase6_perception.py`：18 項 Phase 6 保護測試。

所有新 surface 都是 UNVERIFIED_SURFACE_CANDIDATE，`usable_surface=False`；局部「看起來有用」的開發者檢查沒有回灌成 verified。新 VLM claim 與其派生定位是同源證據，不算兩個獨立模型交叉確認。歷史授權只留在既有觀察，不移轉到新框。未被 positively 分類為 smartphone 的舊 phone 在派生查詢中保持 unknown；因此 test1 f240 等會失去一般手機候選入口，原始觀察及 Phase 5 Graph 保留。可信歷史在同格評估範圍內保留，不以候選覆寫。

新模組接受 arbitrary video ID、來源 frame／PTS、既有 observations 與可選 reference image；reference 僅輔助外觀，不能授權身分。沒有 GT 查表、訓練、production Graph 寫入、commit 或 push。

## 使用方式與檔案

從 `C:\Users\smile\Desktop\test2\mixure_test_SAM`：

```powershell
# 已完成結果：只查詢，不載模型
.venv\Scripts\python.exe -X utf8 -B scripts/run_phase6_demo.py --memory artifacts/phase6/pixel_demo/test8/memory_graph.json --query "Where is my phone?"
.venv\Scripts\python.exe -X utf8 -B scripts/run_phase6_demo.py --memory artifacts/phase6/pixel_demo/test8/memory_graph.json --query cup

# 如日後明確需要重新感知，使用新的 output；會執行模型
.venv\Scripts\python.exe -X utf8 -B scripts/run_phase6_demo.py --output artifacts/phase6/new_demo
```

- 最終原始輸出、來源 manifest、isolated Graph、搜尋、遮罩、同格圖：`artifacts/phase6/pixel_demo/`。
- 每影片 `evidence_sheet.jpg`，單格 `fNNNNNN_comparison.jpg` 左 Phase 5／右 Phase 6。
- 來源及程式 hashes：`pixel_demo/run_receipt.json`；收尾查詢修補與驗證：`CLOSEOUT_VERIFICATION.md`。
- 符合使用者固定入口：`WORKSPACE/VLMtest/LATEST_REPORT.md`。

## 驗證與未完成項目

62／62 focused CPU tests 通過；九片 Graph 重載後 phone／cup 共 18 查詢與保存結果一致。3,273 個歷史受保護檔案 SHA 未變，21 份最終 raw output SHA 未變，事件決策保持原 Phase 4 狀態。詳見 `CPU_TEST_RESULTS.md`。

接下來仍須改善：微波爐等物體的真實頂面定位、小型／部分遮擋手機的框精度、held 與接觸判斷、參考實例與跨時間身分、跨視角 surface 對應。完整新影片上傳到查詢流程尚未實作。

**Phase 6 的局部感知與搜尋整合已可執行；不宣稱可靠找物產品完成，也不宣稱所有 surface localization 目標達標。**

