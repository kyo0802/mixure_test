# V2.8 — Target-Centered Local Spatial Memory + Evidence-Gated Physical Reasoning

完成日期：2026-09-27（Asia/Taipei）  
工作範圍：`mixure_test_SAM`，test3–test9 frozen observation replay。  
結論：**V2.8 已把多數 V2.7 的兩節點圖擴充為連通的 1–2 hop local subgraph；physical reasoner 能產生並保存未確認假說，但這批 frozen evidence 沒有任何 relation 足以 PROMOTE。**

## 執行摘要

|項目|結果|
|---|---|
|上游模型|未執行；YOLO、tracking、SAM、Re-ID、Identity Guard 全部 frozen|
|V2.7 保護|`outputs_v27` manifest 及其檔案驗證通過，沒有覆寫 V2.7|
|V2.8 graph|總 entity 13 → 34；Hop1 20、Hop2 7；disconnected node 0|
|Physical decisions|22 個 `CANDIDATE_NEAR`、2 個 rejected NEAR、23 個 rejected OCCLUDED_BY、23 個 rejected BEHIND|
|Promotions|0；obvious false promotion 0|
|Search|5 片有 candidate physical hypothesis、1 片只有 image context、1 片沒有 useful context|
|Safety|unauthorized update 0、IMAGE→physical leak 0、identity-driven false relation 0|
|測試|V2.7 27 項 + V2.8 32 項，共 59 passed|
|凍結|post-freeze 評估前凍結 208 個 inference／JSON／PNG／Mermaid artifacts|

`CANDIDATE_NEAR` 只代表「多幀 2D proximity 穩定且值得搜尋」，沒有深度證據，輸出文字一律標成 possible / unconfirmed。它不是正確位置或已確認的 physical NEAR。

## Stage A — Evidence Availability Audit

|影片|可信 sampled target frames|Primary segments|最長連續支持|可信 mask|placement transition pattern|狀態|
|---|---:|---:|---:|---|---|---|
|test3|23|4|1.60s|無|無|EVALUABLE_CONTEXT_ONLY|
|test4|15|2|1.00s|無|無|EVALUABLE_CONTEXT_ONLY|
|test5|31|4|1.80s|無|無|EVALUABLE_CONTEXT_ONLY|
|test6|32|3|6.60s|無|無|EVALUABLE_CONTEXT_ONLY|
|test7|23|8|3.40s|無|無|EVALUABLE_CONTEXT_ONLY|
|test8|39|3|7.40s|無|無|EVALUABLE_CONTEXT_ONLY|
|test9|3|0|0.00s|無|無|INSUFFICIENT_EVIDENCE|

「EVALUABLE_CONTEXT_ONLY」表示能評估穩定局部 proximity 並形成 candidate，沒有足以測試放置／遮擋 promotion 的 transition evidence。七片的 frozen trusted `phone_01` registry 都沒有 mask reference；repo 有通用 VLM adapter，但沒有 candidate-scoped、已快取且已驗證的 VLM 證據。依規格沒有下載或載入新大型模型，也沒有讓舊 full-scene VLM 結果代替本次窄關係驗證。

## 各片真實結果

下表是 lifetime graph 計數；每個重要 snapshot 仍限制最多 3 個 primary、每個 primary 最多 2 個 context。

|影片|V2.7 → V2.8 entities|Hop0 / Hop1 / Hop2|最後可信 local structure|Physical result|Search 類型|
|---|---:|---:|---|---|---|
|test3|2 → 5|1 / 3 / 1|phone → sports ball → microwave|4 NEAR candidate；8 BEHIND/OCCLUDED rejected|candidate hypothesis|
|test4|2 → 4|1 / 2 / 1|phone → microwave、sports ball → potted plant|1 NEAR candidate；5 rejected|candidate hypothesis|
|test5|2 → 8|1 / 4 / 3|phone → sports ball → microwave|4 NEAR candidate；8 rejected|candidate hypothesis|
|test6|2 → 5|1 / 3 / 1|phone → microwave、sports ball、chair|3 NEAR candidate；6 rejected|candidate hypothesis|
|test7|2 → 6|1 / 5 / 0|phone → microwave、兩個 chair|8 NEAR candidate；14 rejected|candidate hypothesis|
|test8|2 → 5|1 / 3 / 1|f804 後只有 phone；較早 ball/chair/microwave/plant 為 STALE|2 NEAR candidate，但皆屬舊 episode|image context only|
|test9|1 → 1|1 / 0 / 0|只有 phone|無 candidate|no useful context|

Lifetime 的 Hop1 數可超過 3，因為它保存不同時間的歷史；單一 snapshot 沒有超過 3 個 primary。Raw detector label 和 semantic role 分開保存，表中名稱不代表人工確認過的物件語意。

## Post-freeze test3–test9 對照

- **test3：** 沒有 box entity 或 container-entry transition，所以沒有建立 INSIDE。新圖增加 chair、sports ball 與 microwave context，但沒有取得敘述中的最終 box placement。
- **test4：** 有 sports ball primary anchor，另有 potted plant Hop2 幫助定位；NEAR 只到 candidate。BEHIND 缺少 overlap 增加、visibility loss 與持續未觀測的完整 pattern，因此拒絕。
- **test5：** 沒有看到 box placement transition。因 final placement 不完整，INSIDE 沒有被生成或推進，正確保持 uncertainty；最後只保留 ball→microwave context。
- **test6：** microwave 已進 final primary anchors，local graph 比 V2.7 豐富；沒有穩定 doll node，也沒有實際 ON／INSIDE／BEHIND placement evidence。
- **test7：** provisional identity 仍是 observation-only，沒有把 doll 寫入 `phone_01` memory。較多舊 anchors 反映歷史 context，不代表找到了 doll placement。
- **test8：** f804 的唯一 `CONFIRMED_MATCH` 更新最後可信時間，但一個影格不足以形成新 segment。其他電話不會污染 `phone_01`；f804 前的 local graph 保留在 lifetime，但轉為 STALE，final local graph 只有 phone。
- **test9：** 只有 3 個可信 sampled target frames，沒有穩定 target-anchor segment，因此 basketball、HomePad、bottle 都沒有進 graph。主要卡在 identity/co-visibility evidence，不是 physical gate 將一個完整 pattern 擋掉。

以上是凍結後的定性比較，不是完整 trajectory ground truth accuracy。執行者在 inference 前已看過附件敘述，因此 manifest 沒有宣稱人工盲測；V2.8 inference source 本身不讀 evaluation、GT 或各影片敘述。

## V28_REPORT 必答問題

### 1. 是否解決 V2.7 graph 太 sparse？

**大致解決 graph 結構問題，但未解決最終放置 evidence。** test3–8 都從 V2.7 的 2 個 lifetime entities 擴充到 4–8 個；test3、4、5、6、8 形成 Hop2。test9 因 evidence 不足仍只有 target。總 entity 從 13 增為 34，且 0 個 disconnected node。

### 2. 每片 Hop0/Hop1/Hop2 有多少？

依序為：test3 `1/3/1`、test4 `1/2/1`、test5 `1/4/3`、test6 `1/3/1`、test7 `1/5/0`、test8 `1/3/1`、test9 `1/0/0`。這是 lifetime 去重 entity 計數。

### 3. 新 node 是否真的對搜尋有用？

它們都有 `phone → primary` 或 `phone → primary → context` 的可追路徑，能用來定位 anchor；例如 test4 的 sports ball→potted plant、test5 的 sports ball→microwave。對 narrative 的實際用途則不一致：test4、test6 有部分吻合，test3/5 缺 box，test7 缺 doll，test8 新確認後沒有 context。

### 4. 是否 graph 過度膨脹？

沒有回到 80–110 nodes 的 full scene graph。Lifetime 最大為 test5 的 8 個 entity；snapshot 使用 1 target、最多 3 primary、每 primary 最多 2 context。所有 graph connected，規則可檢出的 irrelevant/disconnected branch 為 0。這不能保證 detector 語意標籤都正確。

### 5. 哪些 physical relations 產生 candidate？

只有 **NEAR，共 22 個**。它要求多幀 proximity 與時間穩定，但深度未知，因此全部標成 CANDIDATE。

### 6. 哪些被 PROMOTED？

**沒有。** ON、INSIDE、HELD_BY 沒有符合語意角色及 transition 的穩定 episode；23 個 OCCLUDED_BY 與 23 個 BEHIND 嘗試都因 pattern 缺失被拒絕。

### 7. 每個 promotion 的 evidence 是什麼？

本次沒有 promotion，因此沒有可列的 promotion evidence。Schema 與合成測試證明 gate 可接受：HELD_BY 需同步運動和獨立 interaction、ON 需 support-compatible 穩定放置、INSIDE 需 entry+containment 和 mask／獨立／VLM 支持、BEHIND/OCCLUDED_BY 需 relation-specific visibility sequence。這只證明程式能力，不是七片真實成效。

### 8. 有沒有明顯 false physical promotion？

0。原因是沒有任何 promotion，而不是 reasoner 已在真實 positive case 上達到 100% precision。Candidate NEAR 仍可能是投影巧合，輸出沒有把它當 confirmed。

### 9. 哪些 relation 因 evidence 不夠被拒絕？

OCCLUDED_BY 23、BEHIND 23、NEAR 2。主要缺少 overlap/visibility 變化、消失後時序連續性、mask area trend與額外 semantic/VLM 支持。ON、INSIDE、HELD_BY 沒有足夠 compatible episode，未生成可評估 candidate。

### 10. Physical reasoning 最大瓶頸？

第一是 **final placement 時段的 trusted target-anchor co-visibility**；其次是 detector/identity 造成關鍵 box、doll、HomePad、bottle 沒有穩定綁到 target 周圍。第三是 frozen trusted target 沒有 mask reference，無法量測真實可見面積。VLM 缺失會限制語意確認，但更強 VLM 無法補回沒有共視或未授權的 target trajectory。Relation gate 目前不是首要瓶頸。

### 11. Search 是否從「anchor 附近」進步到「裡／後／上」？

**尚未。** Planner 已能優先使用 promoted INSIDE/BEHIND/ON，合成測試也通過；真實七片沒有 promotion，所以 test3–7 最高只到 possible NEAR，test8/9 更弱。進步在 local anchor structure 與 uncertainty 表達，沒有進步成確認的物理放置。

### 12. 哪些影片仍 fallback 到 image context？

test8 只有 stale image context；test9 沒有 context。test3–7 雖由 candidate NEAR 排在 image context 前面，本質仍是未確認的 2D temporal proximity，不能當作 physical location。

### 13. test7/test8 identity safety 是否保持？

保持。所有未授權 observation 更新數為 0。test7 provisional 沒有寫入 target memory；test8 只接受 f804 的單一 CONFIRMED_MATCH，未追溯授權其他手機或後續 candidate history。

### 14. Temporal graph 是否更像 local memory？

是。它以 target state、primary/context 變更和 physical candidate 事件建立 2–7 個 stage，不逐 frame 畫圖；每個 stage 可同時顯示多個 primary、Hop2 context 與 candidate 狀態。可讀圖使用 entity→relation node→entity，ACTIVE／LAST_TRUSTED／STALE 與 CANDIDATE 分開標示。

### 15. Lifetime graph 是否清楚呈現 spatial history？

比 V2.7 完整：它保留 ENDED／STALE episodes、1–2 hop anchors、candidate physical relations 與最後可信 local graph。test8 特別清楚呈現 f804 重新確認後，舊 ball/chair/microwave context 只能留在 STALE history。較長 lifetime 若繼續增加 episode，仍需要分頁或時間篩選，這版只驗證目前規模。

### 16. 下一步需要更強 VLM，還是 upstream evidence？

先補 **upstream causal evidence**。應優先保存 final placement 前中後的 trusted target mask、anchor 共視與授權連續性，再對已形成的少數 candidate 做窄 VLM verification。現在直接換更強 VLM，大多數缺失案例仍沒有可靠 target/anchor window 可供判斷。

## 最終能力判斷

目前 FindMind 已完成這條鏈的保守版本：

```text
phone disappears
→ retrieve last trusted spatial memory
→ inspect connected nearby anchor structure
→ generate a physical hypothesis when a temporal pattern exists
→ promote only with relation-specific evidence
→ produce a prioritized and uncertainty-aware search plan
```

本批資料實際走到「candidate hypothesis」或「image context」；沒有走到 confirmed physical placement。最大 blocker 是 placement 時段 upstream evidence 不完整，而不是 graph store、search priority 或 threshold 太保守。

## 交付內容

- `src/memory_graph/v28/`：roles、geometry、local subgraph、physical reasoner、memory、search、pipeline、visualization。
- `scripts/run_v28.py`、`render_v28_graphs.py`、`evaluate_v28.py`。
- `tests/test_v28_memory.py`：32 個 V2.8 cases；V2.7 27 cases 保留。
- `outputs_v28/evidence_availability.json` 與 `evidence_availability_summary.json`。
- `outputs_v28/summary.json`、`prediction_manifest.json`、`evaluation_summary.json`。
- 每片包含規格要求的 observation、local graph、anchor、physical decision、episode、temporal/lifetime、search、evaluation JSON/text。
- 每片包含 individual temporal stage、timeline、lifetime、search、final local subgraph 的 PNG 與 Mermaid。

|影片|搜尋結果|Timeline|Lifetime|Final local graph|Search graph|
|---|---|---|---|---|---|
|test3|[plan](test3/search_plan.txt)|[PNG](test3/graphs/temporal_memory_timeline.png)|[PNG](test3/graphs/phone_01_lifetime_memory.png)|[PNG](test3/graphs/phone_01_local_subgraph_final.png)|[PNG](test3/graphs/phone_01_search_graph.png)|
|test4|[plan](test4/search_plan.txt)|[PNG](test4/graphs/temporal_memory_timeline.png)|[PNG](test4/graphs/phone_01_lifetime_memory.png)|[PNG](test4/graphs/phone_01_local_subgraph_final.png)|[PNG](test4/graphs/phone_01_search_graph.png)|
|test5|[plan](test5/search_plan.txt)|[PNG](test5/graphs/temporal_memory_timeline.png)|[PNG](test5/graphs/phone_01_lifetime_memory.png)|[PNG](test5/graphs/phone_01_local_subgraph_final.png)|[PNG](test5/graphs/phone_01_search_graph.png)|
|test6|[plan](test6/search_plan.txt)|[PNG](test6/graphs/temporal_memory_timeline.png)|[PNG](test6/graphs/phone_01_lifetime_memory.png)|[PNG](test6/graphs/phone_01_local_subgraph_final.png)|[PNG](test6/graphs/phone_01_search_graph.png)|
|test7|[plan](test7/search_plan.txt)|[PNG](test7/graphs/temporal_memory_timeline.png)|[PNG](test7/graphs/phone_01_lifetime_memory.png)|[PNG](test7/graphs/phone_01_local_subgraph_final.png)|[PNG](test7/graphs/phone_01_search_graph.png)|
|test8|[plan](test8/search_plan.txt)|[PNG](test8/graphs/temporal_memory_timeline.png)|[PNG](test8/graphs/phone_01_lifetime_memory.png)|[PNG](test8/graphs/phone_01_local_subgraph_final.png)|[PNG](test8/graphs/phone_01_search_graph.png)|
|test9|[plan](test9/search_plan.txt)|[PNG](test9/graphs/temporal_memory_timeline.png)|[PNG](test9/graphs/phone_01_lifetime_memory.png)|[PNG](test9/graphs/phone_01_local_subgraph_final.png)|[PNG](test9/graphs/phone_01_search_graph.png)|

## 重現與限制

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_v27_memory.py tests\test_v28_memory.py -q
.\.venv\Scripts\python.exe scripts\evaluate_v28.py
```

第一次生成順序為 run → render → freeze → evaluate。目前 prediction manifest 已存在，run/render 拒絕覆寫；後續不同 threshold 或 evidence 實驗應使用新版本資料夾。`V28_REPORT.md` 與 `evaluation*.json` 是 post-freeze 產物，不在 prediction hash 中；evaluator 每次先後都驗證 frozen predictions/source 與 V2.7 manifest。

依 STOP RULE，本版在完成 audit、local graph、reasoner、memory、search、visualization、tests、freeze、evaluation 與報告後停止，沒有開始 V2.9、SAM/Re-ID/VLM 新實驗、SLAM、3D、GNN 或訓練。
