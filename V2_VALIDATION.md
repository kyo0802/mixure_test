# V2 actual validation — 2026-09-23

## 結論

V2 架構、兩支影片處理、真實 GPU VLM、結構驗證、時間記憶及輸出稽核已完成。完整測試 **50 passed**。這是可運作並可檢查的研究框架，不能宣稱模型語意全部正確，或已可靠辨識事件中的實際動作。

使用 RTX 5070 Ti、Qwen2.5-VL-7B-Instruct、NF4 4-bit／BF16 compute。每個選中事件對最多六個 track 的多相位裁切進行辨識，再分析三張完整場景影格的關係。真正模型生成次數為 56／55；最後一次輸出更新使用原始回覆 cache，故 run_status 的新生成次數為零。原始實測狀態保留於 docs/v2_task1_inference_run.json、docs/v2_task2_inference_run.json；最終關係以加強幾何驗證後的輸出為準。

| 實際結果 | test1.mp4 → task1 | test2.mp4 → task2 |
|---|---:|---:|
| 完整解碼影格 | 967 | 924 |
| sampled frames | 162 | 155 |
| 固定數字 track IDs | 77 | 96 |
| raw signals / merged events / selected | 124 / 45 / 8 | 138 / 53 / 8 |
| 可用事件（其中 partial） | 8（1） | 8（1） |
| 被排除的無效 VLM components | 1 | 1 |
| admitted labeled / unknown entities | 22 / 22 | 19 / 23 |
| admission 排除 tracks | 33 | 54 |
| VLM / geometry-only relation intervals | 4 / 86 | 2 / 78 |
| interactions / transitions | 0 / 0 | 0 / 0 |

Partial 不是完全成功：有效的獨立辨識結果保留，無效 component 原文及錯誤保存但不入圖。Labeled／confirmed 是程式狀態，不是人工確認正確；track 數也不是實際物件數。

## 與先前暫停摘要核對

V2 模組與 disabled 預設存在。已修正 event budget 重複選擇時的 stale selected 標記，加入零預算與重複選擇測試。原始 35 passed／1 failed 並未在修正前重新量測，不能當成本次測試紀錄。

歷史 outputs/task1、outputs/task2 不在移入的目錄，不能核對原始 50 merged events 或圖片。此次 task1 為 45 merged events，不能硬湊成 50。原始 V1 manifest 中 31 個現存檔案均與本次開始時一致；graph_visualizer.py 與舊 manifest 有一項既存差異，並非本次改動。V1 重跑在 outputs_v1_comparison，沒有覆寫歷史路徑。

## 二十項驗收

| # | 要求 | 實測／驗證與限制 |
|---|---|---|
| 1 | V1 保留 | 本次 31 個既有 V1 檔案 hash 不變；歷史缺檔與既存差異另列稽核。 |
| 2 | 兩片可處理 | V1、V2 event-only、V2 local VLM 均完成；V2 全片解碼通過。 |
| 3 | temporal tracks | 77／96 numeric IDs，觀察時間、bbox、信心與 detector class 保留。 |
| 4 | 選擇有意義事件 | 45／53 merged 中各選 8；人工見物件進出、靠近、手與物件共現。鏡頭移動與重複窗口仍造成噪音，未測 event precision。 |
| 5 | before/during/after | 16 個 selected events 全部具備三相位影格與來源 metadata。 |
| 6 | 可見 ID grounding | 場景 bbox ID、crop atlas、各 ID 多相位裁切與實際輸入 provenance 均保存。 |
| 7 | structured validated | Pydantic、固定 supplied IDs、原始 generation trace、partial/error 狀態；沒有自動修補成期望答案。 |
| 8 | 改類別不改 ID | task1 ID23 cup→basketball 人工確認；仍有錯誤 correction，見下表。 |
| 9 | unknown | 實際 22／23 admitted unknown，event-only 全 unknown。 |
| 10 | 真實多椅分離 | task1 ID58／60、task2 ID88／90 是不同椅子且保持獨立；不合併相同語意類別。 |
| 11 | noise admission | 33／54 tracks 被門檻排除，測試確認單影格高 VLM 信心不能繞過；仍不能移除所有錯框。 |
| 12 | 一般 entity 關係 | 有向 entity/entity 圖，語意與 2D geometry 分開；共 4／2 個通過驗證的 VLM relation intervals。 |
| 13 | 人物物件互動可表示 | schema／validator 支援 person、hand 等 actor 與 HOLDING 等；實片沒有通過的 interaction，不能聲稱動作辨識成功。 |
| 14 | 非 anchor panels | 一般 entity network；anchor 只保留 metadata／邊框，不作中心分組。 |
| 15 | 保留時間 | phase、start/end、observed_times、event provenance 保留；transition 必須有有效 VLM 支持。實片 transition 為 0。 |
| 16 | geometry/tracking check | 共現、至少兩影格的持續／動作證據、actor、方向／距離等檢查；拒絕 11／5 個 VLM relation claims。Geometry 不能證實語意或接觸。 |
| 17 | 圖可檢查 | timelines、16 event graphs、2 memory graphs、contact sheets、完整 annotated videos；大圖有顯示上限，render.json 明列省略項，完整 JSON 保留。 |
| 18 | 不宣称真 3D | 文件及圖明確為 2D evidence；沒有 depth／SLAM／3D memory。 |
| 19 | 無尋物 ranking/UI | 未實作，也未擴張範圍。 |
| 20 | 檢查實際兩片 | 檢視全部選中窗口的前中後影格、兩個時間軸、代表性 ID crops、事件／memory graphs；影片全解碼並抽查 annotated frames。 |

## 人工物件檢查

以下是選定片段的人工檢查，不是完整標註資料集或正確率評估。

| 片段 | 畫面證據 | 結果 |
|---|---|---|
| task1 evt011，7.0s，ID23 | 前景橘色籃球，YOLO cup | VLM basketball，正確；ID23 不變。 |
| task1 evt011，ID25 | 背景綠色垃圾桶，小而模糊 | VLM cup；**trash can correction 未成功**。 |
| task1 evt011，ID28 | 椅子被前景籃球遮擋，crop 大部分是球 | VLM basketball 是錯誤歸屬；不應算另一顆球。 |
| task1 evt034，19.81s，ID58／60 | 藍色辦公椅與白色塑膠椅 | office chair／chair，兩個真實物件維持不同 ID。ID61 不列入已確認椅子。 |
| task1 evt040，25.41s | 桌面電話、玩偶、微波爐 | 電話70／71辨識合理；69保留 unknown；關係回覆 JSON 無效而排除。 |
| task2 evt006，2.60s，ID17 | 橘色籃球，YOLO sports ball | VLM basketball，正確。 |
| task2 evt006，ID4 | 白椅及其上深色物件 | VLM flip-flop 錯誤，不能當有效修正。 |
| task2 evt038，19.81s | 手靠近／接觸微波爐上的玩偶 | 未得到有效 interaction；不能聲稱 HOLDING／PICKING_UP。 |
| task2 evt053，28.61s，ID88／90 | 左前景與右牆旁兩張白椅 | 各自 chair，維持不同 ID；96可能是後續 fragmentation，不宣稱第三張真椅。 |

額外檢查 task1 evt016 的寬框包含多個物件、evt019 的 track40 隨時間漂移；語意衝突可退回 unknown，但 numeric track continuity 不等同物理 ReID。實際球被不同 track 重複標記、person→chair／basketball 等錯誤仍存在。事件候選含鏡頭運動影響；task1 部分同時間但不同 tracks 的窗口重複。沒有為這兩支影片硬編碼正確標籤。

## 可重現證據

- [使用與執行指令](README_V2.md)
- [V1/V2 統計比較](docs/v2_comparison.md) 與 [完整 hashes/runtime JSON](docs/v2_comparison.json)
- [四組 V2 artifact audit](docs/v2_artifact_audit.json)；[V1 comparison audit](docs/v1_comparison_audit.json)
- [task1 memory graph](outputs_v2/task1/memory_graph.png)、[task2 memory graph](outputs_v2/task2/memory_graph.png)
- [task1 timeline](outputs_v2/task1/event_timeline.png)、[task2 timeline](outputs_v2/task2/event_timeline.png)
- [task1 contact sheet 1](outputs_v2/task1/event_contact_sheet_01.jpg)、[2](outputs_v2/task1/event_contact_sheet_02.jpg)
- [task2 contact sheet 1](outputs_v2/task2/event_contact_sheet_01.jpg)、[2](outputs_v2/task2/event_contact_sheet_02.jpg)
- [task1 annotated video](outputs_v2/task1/annotated_v2.mp4)、[task2 annotated video](outputs_v2/task2/annotated_v2.mp4)

測試指令：`uv run --extra vlm --extra gpu --extra quantized pytest -q`。GPU 量化套件只在明確選擇的設定啟用，預設 VLM 仍 disabled。3B／FP16 失敗、detector prompt bias 與模型調整的實驗紀錄在 docs；不計入最終成功次數。

架構驗證完成，但可靠垃圾桶修正、實際互動辨識與 VLM-confirmed temporal transitions 尚未被此實驗證明。這些限制已保留在成果中，沒有虛構補齊。
