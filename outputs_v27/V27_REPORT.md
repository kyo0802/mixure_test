# V2.7 — Target-Centric Temporal Spatial Memory Graph

完成日期：2026-09-27（Asia/Taipei）  
範圍：`mixure_test_SAM`；重播 test3–test9 的既有可信資料。  
結論：**記憶、雙視圖與可解釋搜尋原型完成；最終放置位置的恢復仍受可信觀測與 physical evidence 不足限制。**

## 進度與成果摘要

|工作|結果|
|---|---|
|可信身分資料接入、observation / memory 隔離|完成|
|Relevant anchor、relation candidate / episode、事件快照|完成|
|Temporal / lifetime / lifecycle / search 圖|七支影片全部完成，PNG + Mermaid|
|Graph-rule search planner|完成，保留來源、時間與 uncertainty|
|回歸測試|27 passed，最後驗證耗時 0.26 秒|
|預測凍結|174 個輸出檔案，加上 inference / rendering 原始碼雜湊|
|上游檔案檢查|91 個實際使用的輸入檔案雜湊一致|
|凍結後 narrative 評估|七支影片全部完成|

4/7 影片具有 LAST_TRUSTED anchor，另 2/7 只能回傳較舊 context，1/7 沒有穩定空間線索。6/7 能產生可解釋的搜尋候選，**不是 6/7 找回成功或定位正確**。七片皆未形成 verified physical episode。沒有重新執行影片模型推論；本版測量的是既有觀測上的 memory replay。

本次新增 V2.7 模組、腳本、測試與輸出；沒有修改 YOLO、SAM2.1、Re-ID、Identity Guard 或 V2.6 決策規則，沒有進行 SAM 實驗。既有 V2.6 / V2.6.2 結論維持原狀；工作沒有寫入兄弟資料夾 `mixure_test`。

## 1. Memory Graph 到底存什麼？

存 `phone_01` 的可信出現、消失、重新確認事件，以及與少數有用 anchor 的 relation episodes。Episode 包含開始／最後支持影格與時間、狀態、支持影格、evidence、來源與 snapshot IDs。Entity ID 沿用上游 persistent entity；track ID 只作 provenance，沒有額外跨 track 合併。

同一個 episode/event store 衍生 temporal、lifetime 與 search 視圖。`observations.json` 是觀測稽核層；未確認 candidate 可留在此層，但不因此變成 `phone_01`。

## 2. 為什麼沒有把所有 scene objects 放進 graph？

每片上游有 81–110 個 entity，本版 lifetime graph 只有 1–2 個實體節點（含 target）。Anchor 必須具有可信身分、與 target 的相關觀測及時間支持，並屬於可定位的支撐物／地標類型，或具有獨立 physical assertion。一般無關椅子等不會僅因出現在畫面就納入。

七片共用設定：至少 3 個不同影格、支持跨度至少 0.35 秒、相鄰支持間隔至多 0.65 秒；image-near 的 bbox 間距門檻為影像對角線的 0.12；最多 3 個目前 anchor。同一影格的 raw / track 重複觀測不增加時間支持。這些規則未依個別影片 narrative 調整。

## 3. Temporal Memory Graph 如何產生？

依時間順序重播可信觀測，合併連續 relation 支持。只有 target 出現／消失／重新確認、重要 relation 開始／結束、anchor 改變或有明確 evidence 的互動事件才建立快照，不逐影格製造 graph。

快照是當時 store 的獨立拷貝，後續 episode 延長不改寫舊快照。失去連續可信 context 支持時，context episode 結束但歷史保留。沒有 evidence 時不虛構 PICKED_UP、MOVED_TO 或 PUTDOWN。

## 4. phone_01 Lifetime Memory Graph 如何產生？

`build_object_memory("phone_01")` 從同一 store 取出該 target 的 entities、episodes、events、lifecycle 與 last trusted memory。不是另跑一套關係推論；已 ENDED / STALE 的 episode 仍在歷史中。`object_memory_phone_01.json` 與 `phone_01_lifetime.json` 是相同資料的輸出別名，評估已檢查一致。

圖上以時間與狀態區分各 episode；同一 anchor 不因關係有多個歷史區段而變成不同實體。

## 5. Observation relation 如何與 physical memory 分離？

`IMAGE_LEFT_OF / RIGHT_OF / ABOVE / BELOW / NEAR / OVERLAP` 都只是影像幾何。穩定而有用的幾何線索可形成 **ANCHOR_CONTEXT**，其 evidence level 明確標成 `TRUSTED_IMAGE_CONTEXT`；這不是 physical NEAR、ON、INSIDE 或 BEHIND。

Physical promotion 另外要求因果有效、身分相符的 interaction / verified event / VLM assertion，含獨立物理支持、來源與至少 0.8 confidence，再經多影格支持。對應機制已用 synthetic fixtures 測試，但本次 56 個既有 event graphs 全是 `skipped_events_only`，沒有 verified physical evidence。因此真實重播的 physical episodes = **0**，未實際驗證 physical perception 的品質。

## 6. phone UNOBSERVED 後記憶如何保留？

依 frozen upstream 的 UNOBSERVED 事件更新 target 狀態；當時 ACTIVE episode 改為 LAST_TRUSTED，保留 last seen、最後可信 anchor、來源與歷史快照。這是「曾經可信的位置線索」，不聲稱手機現在仍在那裡。

先前 overlap 加上 anchor 仍可見最多形成 occluder candidate，不自動寫 OCCLUDED_BY。重新確認 target 時，舊 LAST_TRUSTED context 轉為 STALE；新位置必須重新累積支持。test8 因此不會把 f804 前的球類記憶冒充 f804 的目前 context。

## 7. PROVISIONAL / AMBIGUOUS 如何被阻止污染 memory？

只有原始 trusted history 與當下精確的 CONFIRMED_MATCH 授權可寫入 target memory。其他 identity 狀態留在 observation audit；未授權 candidate 不能開始、延長或結束 phone_01 的 episode。

不使用 registry 最終 alias map 追溯授權整條 candidate 軌跡；SAM 中標為 untrusted 的觀測仍未授權。test7 的 provisional f636 沒有更新 target；test8 只接受確定的 f804 CONFIRMED_MATCH，後續不明手機未獲授權。七片稽核的未授權 memory updates 均為 0。這證明授權邊界遵守，不等於證明上游所有 TRUSTED 身分都正確。

## 8. Search Candidate 怎麼從 graph 產生？

Target 為 UNOBSERVED 時，planner 讀 lifetime episodes 與 last trusted state。每個候選輸出 anchor、relation、rule priority、source episode、source snapshot、最後支持時間、reason、uncertainty 與 provenance。相同 anchor / relation 保留優先結果；HELD_BY 及 person anchor 不作 location candidate。

程式入口：`memory_graph.v27.search_planner.find(object_memory, "phone_01")`。本版為可獨立驗證的 replay 模組，沒有接入主原型的即時服務或 UI。

## 9. 為什麼不是舊版 weighted score？

排序是明確的規則階層：

1. LAST_TRUSTED physical location（如 ON / INSIDE / BEHIND / OCCLUDED_BY）。
2. LAST_TRUSTED anchor / context。
3. 最近一段已結束或已 stale 的穩定空間 context。
4. 更早的可信歷史。

同階層以最後支持時間排序，再以穩定 ID 打破平手。没有 T/M/I/O/E 權重加總。Anchor admission 可用幾何接近程度選取相關物件，但不將它當作搜尋 confidence 或 weighted ranking score。

## 10. test3–test9 各自最後得到什麼 memory？

所有影片的最終 target state 都是 UNOBSERVED。下表「最後可信 target」與「anchor 最後支持」是不同時間；不能混用。

|影片|重播影格|實體／快照／episode|最後可信 target 秒|搜尋 #1 的 anchor 與支持區段|狀態／規則|
|---|---:|---|---:|---|---|
|test3|196|2 / 5 / 2|15.60|sports ball `entity_0051`，13.20–14.80 秒|LAST_TRUSTED / 2|
|test4|196|2 / 3 / 1|15.40|sports ball `entity_0041`，14.40–14.80 秒|LAST_TRUSTED / 2|
|test5|187|2 / 3 / 1|13.80|sports ball `entity_0043`，11.00–12.80 秒|LAST_TRUSTED / 2|
|test6|167|2 / 3 / 1|13.41|sports ball `entity_0029`，6.80–13.01 秒|LAST_TRUSTED / 2|
|test7|221|2 / 6 / 2|14.00|sports ball，10.60–13.20 秒|ENDED / 3|
|test8|185|2 / 5 / 1|26.80（f804）|sports ball `entity_0028`，6.80–14.20 秒|STALE / 3|
|test9|201|1 / 2 / 0|20.60|無穩定 anchor|無候選|

上述 relation 全是 ANCHOR_CONTEXT，非 physical relation。test3 另保留 11.00–11.60 秒的已結束球類 episode；test7 另保留 7.00–7.60 秒的已結束 episode。搜尋會去除相同 anchor / relation 的重複項，但 lifetime 歷史不刪除。

### 凍結後 narrative 對照

|影片|定性判讀|
|---|---|
|test3|沒有形成 box 最終放置 context；球類線索不能當作盒內位置。|
|test4|球類 anchor 與 basketball 敘述部分一致，可作搜尋起點；未確認 BEHIND 或盲區物理位置。|
|test5|沒有形成 box context；放置觀測不完整時不補出 INSIDE。|
|test6|沒有形成 microwave / doll 最終 context；只有先前球類線索。|
|test7|只有舊 context，provisional 不足以授權玩偶附近的新記憶。|
|test8|f804 更新 last seen；單一確認影格沒有足夠時間支持建立新 anchor，後續干擾手機不污染 target。|
|test9|没有穩定 context，不能從 narrative 補入 basketball occlusion、HomePad 或 bottle 關係。|

這是定性對照，沒有標註完整 ground truth trajectory 或計算模型 accuracy。原始 spec 的 narrative 已對執行者可見，故不宣稱人工盲測；manifest 明列 `operator_exposed_to_user_narrative=true`。Inference code 不讀 narrative，評估腳本只在凍結後執行。

## 11. 哪些影片成功產生有用 last trusted context？

test3、4、5、6 成功保留最後可信的 image anchor context；其中 test4 的球類 anchor 與 narrative 有部分語意對應，較適合作為後續搜尋起點。其餘三片雖有可信歷史線索，沒有證明對應最後放置位置；不能把「有 context」視為任務完成。

## 12. 哪些影片只能得到 uncertainty？

所有影片的 current physical location 都仍不確定。test7、8 只能提供较舊搜尋 fallback；test9 沒有可用 stable anchor。test3、5、6 對使用者描述的最後放置區域也無法給出可靠定位。

## 13. 哪些錯誤來自 upstream，而不是 graph？

上游限制包括：缺少 verified physical evidence、可信 target 在最終放置動作前中斷、SAM 傳播未獲 trusted 授權、重現候選仍 ambiguous / provisional，以及 anchor 身分可能分裂。V2.7 不能自行修補這些資訊。

Graph 本身也有限制：類別與時間支持的 admission 規則偏保守，可能漏掉短暫但有價值的 anchor；2D context 不含世界座標，anchor 可能移動；沒有新的 anchor 跨 track 合併或 3D 校正。未納入物件不應全部歸咎於 detector。Physical assertion adapter 與真實視覺 evidence 的端到端接入尚未完成，本版主要驗證安全的 store / promotion 邊界。

## 14. Graph 是否 sparse / readable？

每片 lifetime graph 1–2 個實體、0–2 個 relation episodes；temporal graph 2–6 個事件快照。PNG 與 Mermaid 都採 entity → relation node → entity，目標與 LAST_TRUSTED 突出、ENDED / STALE 降低顯著度；timeline 以分開 mini graphs 顯示時間演化。已檢視代表性的搜尋、lifetime、timeline、lifecycle 圖並修正文字裁切。

這些實驗證明目前小型圖可讀，尚未驗證大量長期歷史的視覺擴充性。

## 15. 下一步值得加入更強 physical relation reasoning 嗎？

**值得做小規模、有 evidence gate 的驗證。** 現在缺乏足以回答「盒內／物件後方／支撐面上」的證據；只有更漂亮的 graph 不會解決定位。不過應先確認放置區段是否有 trusted target + anchor 共現，再評估短片段 interaction / physical reasoning，否則更強 reasoning 仍無法安全綁定 phone_01。

這是下一版建議，沒有在本版啟動。V2.7 已停止於凍結輸出、評估與本報告。

## 交付檔案與閱讀順序

所有路徑以 `mixure_test_SAM` 為根目錄：

- `src/memory_graph/v27/`：models、observation、relevance、promotion、temporal store、planner、adapter、visualization。
- `scripts/run_v27.py`、`render_v27_graphs.py`、`evaluate_v27.py`。
- `tests/test_v27_memory.py`：27 項案例，包括未確認身分不污染、image geometry 不升為 physical、消失保留、episode 合併、歷史不刪、排序、HELD_BY 排除、未來 evidence 拒絕、同影格去重及真實 test7/test8 授權。
- `outputs_v27/summary.json`：凍結的重播摘要；`evaluation_summary.json`：凍結後評估。
- `outputs_v27/prediction_manifest.json`：輸出與原始碼 SHA-256。
- 每片 `observations.json`、`relation_episodes.json`、`temporal_memory.json`、`object_memory_phone_01.json`、`phone_01_lifetime.json`、`search_candidates.json`、`search_plan.txt`、`evaluation.json`。
- 每片 `graphs/temporal/`：各快照 PNG / MMD；`graphs/`：timeline、lifetime memory、search graph、lifecycle PNG / MMD。

|影片|搜尋結果|Temporal timeline|Lifetime graph|Search graph|
|---|---|---|---|---|
|test3|[plan](test3/search_plan.txt)|[PNG](test3/graphs/temporal_memory_timeline.png)|[PNG](test3/graphs/phone_01_lifetime_memory.png)|[PNG](test3/graphs/phone_01_search_graph.png)|
|test4|[plan](test4/search_plan.txt)|[PNG](test4/graphs/temporal_memory_timeline.png)|[PNG](test4/graphs/phone_01_lifetime_memory.png)|[PNG](test4/graphs/phone_01_search_graph.png)|
|test5|[plan](test5/search_plan.txt)|[PNG](test5/graphs/temporal_memory_timeline.png)|[PNG](test5/graphs/phone_01_lifetime_memory.png)|[PNG](test5/graphs/phone_01_search_graph.png)|
|test6|[plan](test6/search_plan.txt)|[PNG](test6/graphs/temporal_memory_timeline.png)|[PNG](test6/graphs/phone_01_lifetime_memory.png)|[PNG](test6/graphs/phone_01_search_graph.png)|
|test7|[plan](test7/search_plan.txt)|[PNG](test7/graphs/temporal_memory_timeline.png)|[PNG](test7/graphs/phone_01_lifetime_memory.png)|[PNG](test7/graphs/phone_01_search_graph.png)|
|test8|[plan](test8/search_plan.txt)|[PNG](test8/graphs/temporal_memory_timeline.png)|[PNG](test8/graphs/phone_01_lifetime_memory.png)|[PNG](test8/graphs/phone_01_search_graph.png)|
|test9|[plan](test9/search_plan.txt)|[PNG](test9/graphs/temporal_memory_timeline.png)|[PNG](test9/graphs/phone_01_lifetime_memory.png)|[PNG](test9/graphs/phone_01_search_graph.png)|

### 驗證與重現

在 SAM workspace 執行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_v27_memory.py -q
.\.venv\Scripts\python.exe scripts\evaluate_v27.py
```

評估先驗證凍結輸出與原始碼，再確認 91 個已使用上游檔案的 SHA-256，最後寫獨立 evaluation 檔；不覆寫凍結預測。第一次產生順序是 run → render → freeze → evaluate；目前 run / render 已拒絕覆寫凍結結果。若未來做新實驗，應使用新版本輸出。

封存時間：2026-09-27 02:30:56（Asia/Taipei）。SHA-256 驗證範圍為 manifest 所列的輸出、程式碼與實際使用的上游輸入，並非所有歷史資料夾的完整稽核。
