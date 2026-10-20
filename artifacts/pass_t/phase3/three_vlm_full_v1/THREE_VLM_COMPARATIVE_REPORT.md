# FindMind：test1–test9 三模型完整時間軸評估

更新：2026-10-17。狀態：**THREE_VLM_FULL_DATASET_INFERENCE_COMPLETE**。

## 1. 本次結論

共同資料集涵蓋九支來源影片的全部視覺時間軸：69 個既有條目＋145 個新增覆蓋視窗＝214 條目，去除相同輸入後 **184 個不同輸入**。三模型實際共同完成 **184／184**；Qwen／VideoLLaMA 共同完成 **184／184**。執行完成不代表預測正確。

**最終建議：No model yet suitable for direct graph updates（目前沒有模型適合直接寫入 Graph）。** 結構有效、生成事件文字、物件類別辨識與確認同一物理實體／轉移，是不同層次。新資料仍缺全影片人工事件與逐格 state GT，不能給正式整體模型排名。

兩個既有 known-PICKUP 窗中，Qwen 都未提手機 PICKUP；VideoLLaMA 只在 test7 提出，但引用與 state 不相容；Nemotron 兩窗都提出 raw-strict-valid 的手機 PICKUP，卻仍有 after citation 遮擋或過早的 grounding 問題。這是兩個已知個案的描述，不是 recall 或全體模型排名；以下影像分析由助理完成，沒有新增人類 GT 或完整性認證。

## 2. 資料集與完整時間覆蓋

九支來源檔案均與既有 development_inputs 的 SHA-256 相符，無完全相同來源檔案 hash；但不因此認定為九個獨立 recording sessions。時長以下採完整解碼的 native video PTS 至最後影格 presentation end，不是音軌或容器延伸時間。

| 影片 | 視覺時長（秒） | 原始影格數 | 既有窗 | 新增窗 | 不同輸入 | 時間範圍覆蓋 |
|---|---:|---:|---:|---:|---:|---|
| test1 | 32.248 | 967 | 9 | 13 | 16 | 完整 |
| test2 | 30.812 | 924 | 8 | 12 | 15 | 完整 |
| test3 | 38.973 | 1169 | 9 | 17 | 21 | 完整 |
| test4 | 38.973 | 1169 | 8 | 18 | 25 | 完整 |
| test5 | 37.233 | 1117 | 8 | 15 | 18 | 完整 |
| test6 | 33.115 | 993 | 6 | 14 | 17 | 完整 |
| test7 | 43.880 | 1316 | 7 | 20 | 25 | 完整 |
| test8 | 36.770 | 1103 | 9 | 16 | 23 | 完整 |
| test9 | 40.008 | 1200 | 5 | 20 | 24 | 完整 |

固定規則：每窗最多 8 張，依窗內 native PTS 均勻分位點，取最近且嚴格遞增的 source index、同距取較早影格；不足 8 張則全部不同影格、不重複 padding。既有與新增窗一律同規則。新增覆蓋採 4 秒窗、2 秒 stride，從首個 PTS 起算，僅在區間未被既有或先前 coverage grid 完整覆蓋時加入；短尾端截至影片末端。時長依既有約 1–6 秒、典型約 3.6 秒的窗設計選定，沒有使用 GT 或先前模型答案。

保留舊 start/end，依現有 producer/validator 的 closed indices 解讀；舊 Phase 2a 的 half-open authorized scope 另外保留，不能混同。52 個原本沒有 frames 的條目現在都已從來源影片補齊；沒有再排除 test6。所有輸入是原片解碼的乾淨 PNG。

214 條目中 30 個是相同 source evidence 的重複別名，模型每組只生成一次。另驗證 184 組中沒有額外完全相同的 ordered PNG sequence。重疊窗及其 identities 全部保存，不能當作 184 個獨立真實事件或獨立樣本。完整時間配置覆蓋不等於 8 張圖觀察了每一瞬間，也不構成 exhaustive human negative。

實際共有 1,411 個不同 source frames 被採樣，來源合計 9,958 格（約 14.17%）；「全時間軸覆蓋」是所有時段都有所屬評估視窗，不是逐格觀察或完整捕捉所有短暫轉移。

完整來源／邊界／重疊／去重／frame hash／PTS：[dataset.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/dataset.json)；逐原始影格時間：[timelines/](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/timelines)；凍結憑證：[dataset_freeze.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/dataset_freeze.json)。

![九影片完整時間範圍與實際採樣點](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/timeline_coverage.png)

## 3. 共同任務與實際部署

三模型使用同一份英文 observation-first task 與最小 schema：每物件逐 alias 的 ON_SURFACE／HELD_BY_PERSON／OTHER／UNKNOWN，之後可選 PICKUP／PLACEMENT。固定連續 aliases F0001–F0008，附原生 source PTS。沒有特定目標類別、預期答案、GT、舊模型結果或 tracker/identity metadata；Reference NONE。任務與 schema 在本輪生成前固定，沒有根據結果修改。

| 模型 | 固定 revision | 部署 | 有效視覺表示 |
|---|---|---|---|
| Qwen2.5-VL-7B-Instruct | `cc594898137f460bfe9f0759e9844b3ce807cfb5` | 原有 NF4／BF16 compute、SDPA、Windows 環境 | 8 張 chronological images；既有 200704 pixel budget，每張通常 588×336 |
| VideoLLaMA3-7B | `d5b763e368861e7f5096e7ff1b49f92fbccf8ae6` | 原官方實作、語言 NF4、視覺/projector BF16、SDPA、隔離 Transformers 4.46.3 | 8 張 chronological images；合計 4096 visual-token 上限，通常每張 420×224 |
| Nemotron Nano 12B v2 VL | `16853d6c682223e967d5622c99d0082cb994b771` | 官方 NVFP4-QAD、WSL2、vLLM 0.31.0、Torch 2.13 cu130 | 官方 video array 8 張、512×512、temporal patch 1、EVS pruning=0；GPU成功情況依下節實測 |

全部固定 greedy／seed 42／max output 1536 tokens／generation timeout 300 秒，無品質重試。seed 不是跨硬體逐 bit determinism 的保證。使用各模型官方 chat template；Nemotron video 使用官方 no-think 格式控制。模型循序執行，同一 GPU 不同時載入兩個重 VLM。

來源 PNG、索引、native PTS 與順序共用，但實際 tokenizer、影格尺寸、視覺 token/tiling、量化與 engine 不同。**這是 deployment-configuration comparison，不是完全相同內部 tensor 的純模型能力比較。** 不把各模型 token 數當成相同計算單位。

Nemotron 的 official video processor 實際輸出 [8,3,512,512]，不是將八張減成四張；GPU 生成完成數以下節 raw receipts 為準。官方 vLLM video timestamps 以 floor(1000/source_fps) 毫秒乘原始 index，會與 native PTS 漂移；原生時間完整另外提供，未把近似時間冒充 authoritative PTS，亦未宣稱 frame-level attention 已驗證。逐次 input receipt 保存實際有效表示。

Nemotron 官方變體與授權來源：[NVFP4-QAD 模型卡](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-NVFP4-QAD)、[官方 BF16／video 使用說明](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-BF16)。本次沒有用 BF16 塞入 16GB，也沒有換成較小模型。Windows 磁碟上的 WSL wheel cache rename 問題改用原生 uv 安裝相同 Linux wheels；保留 eager 模式，在 Ubuntu 安裝 g++ 15.2、python3.14-dev 與 ninja-build，供官方 CUDA/Triton launcher 使用。IPC socket 改放 Linux /tmp，持久 artifacts/cache 留在專案。Windows 兩個既有環境保持原樣。

## 4. 真實生成、合約與效率結果

| 模型 | 已完成 raw／184 | failed | 未執行 | raw JSON | raw schema | raw full strict | fence body full-valid（另列） |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen | 184 | 0 | 0 | 0（0.0%） | 0（0.0%） | 0（0.0%） | 157 |
| videollama | 184 | 0 | 0 | 147（79.9%） | 144（78.3%） | 83（45.1%） | 0 |
| nemotron | 184 | 0 | 0 | 166（90.2%） | 163（88.6%） | 108（58.7%） | 1 |

分母是已返回並保存 raw 的完成呼叫；未執行不冒充模型負例。token-cap／timeout 可留下 partial raw，會在下一表另列。每份 raw 立即保存，JSON/語法、schema、引用、semantic consistency 分開驗證；invalid 不變成 NO_EVENT。只允許獨立記錄單一完整外層 Markdown fence 提取，不修補 JSON、不補 uncertainty/events/citations、不提升 raw strict。fence-body 是 descriptive proposal view，不是 authoritative accepted structured output。

| 模型 | 逐窗總處理秒數 | median／p95 秒 | EOS／token-cap／timeout | Torch peak GiB | 全 GPU used peak MiB | 輸出 tokens median／max |
|---|---:|---|---|---|---|---|
| qwen | 2413.18 | 10.41／27.29 | 181／3／0 | 6.16 | 未量測 | 434.0／1536 |
| videollama | 1700.63 | 9.70／10.93 | 184／0／0 | 8.18 | 未量測 | 306.0／471 |
| nemotron | 1983.72 | 6.94／32.96 | 167／17／0 | 不可估計／未量測 | 14955 | 278.5／1536 |

逐窗處理時間包括 render/preprocess/generate/保存/validation，載入、下載、資料建置與等待其他模型另計；完整 load receipts 保存在每模型 run 目錄。p95 採 nearest-rank。Torch peak 是該模型 process allocator；Nemotron worker 的全 GPU used 另含 display/其他 process，兩種數字不可直接當成相同量測比較。

| 影片 | Qwen 完成／不同輸入 | VideoLLaMA 完成／不同輸入 | Nemotron 完成／不同輸入 |
|---|---:|---:|---:|
| test1 | 16／16 | 16／16 | 16／16 |
| test2 | 15／15 | 15／15 | 15／15 |
| test3 | 21／21 | 21／21 | 21／21 |
| test4 | 25／25 | 25／25 | 25／25 |
| test5 | 18／18 | 18／18 | 18／18 |
| test6 | 17／17 | 17／17 | 17／17 |
| test7 | 25／25 | 25／25 | 25／25 |
| test8 | 23／23 | 23／23 | 23／23 |
| test9 | 24／24 | 24／24 | 24／24 |

### 觀察與事件候選（不是正確率）

各模型可能只回部分影格的 state；漏列不等於 UNKNOWN，也不能由未列某格推定 processor 丟掉該格。以下 state entries 是描述性輸出量，並非不同實體數或 state accuracy。候選事件數包含跨重疊窗重複與 strict-invalid 的可解析假說，不是真實事件數；較多不等於較高 recall。

- **qwen**：物件描述次數 `{"basketball": 109, "phone": 85, "desk": 32, "box": 32, "chair": 30, "stuffed toy": 28, "microwave": 12, "stuffed animal": 7}`；state entries `{"ON_SURFACE": 2297, "UNKNOWN": 150, "HELD_BY_PERSON": 190, "PLACEMENT": 3}`；parsed/fence hypotheses 6，raw-strict hypotheses 0，類型 `{"PICKUP": 6}`。UNKNOWN 僅為模型自述，不當成錯誤標籤。
  狀態宣告 `{"NO_CONFIRMED_EVENT": 175, "EVENTS": 6}`；UNKNOWN 占可解析 state claims 5.68%；有引用的可解析輸出 181，全部 alias 存在 181，無引用 0。這是 membership，並非影像支持。輸入 token median／min／max：`{"count": 184, "median": 2900.0, "min": 2892, "max": 2900}`，不跨 tokenizer 比較計算量。
  Raw validation 錯誤類別（每窗每類最多計一次）：`{"JSON_SYNTAX": 184}`。fence-body 錯誤另列：`{"DUPLICATE_OBJECT_DESCRIPTION": 14, "SCHEMA": 5, "NONCHRONOLOGICAL_STATES": 4, "EVENT_STATE_CITATIONS_INCONSISTENT": 4}`。完整原始錯誤訊息保留在 model_results.json。
- **videollama**：物件描述次數 `{"basketball": 92, "phone": 53, "chair": 37, "person": 30, "Chili": 11, "box": 11, "hand": 9, "cell phone": 8}`；state entries `{"ON_SURFACE": 1532, "HELD_BY_PERSON": 247, "OTHER": 468, "PICKUP": 4, "PLACEMENT": 3}`；parsed/fence hypotheses 15，raw-strict hypotheses 2，類型 `{"PICKUP": 14, "PLACEMENT": 1}`。UNKNOWN 僅為模型自述，不當成錯誤標籤。
  狀態宣告 `{"EVENTS": 61, "NO_CONFIRMED_EVENT": 86}`；UNKNOWN 占可解析 state claims 0.00%；有引用的可解析輸出 147，全部 alias 存在 147，無引用 0。這是 membership，並非影像支持。輸入 token median／min／max：`{"count": 0, "median": null, "min": null, "max": null}`，不跨 tokenizer 比較計算量。
  Raw validation 錯誤類別（每窗每類最多計一次）：`{"STATUS_EVENTS_INCONSISTENT": 51, "JSON_SYNTAX": 37, "EVENT_STATE_CITATIONS_INCONSISTENT": 5, "DUPLICATE_OBJECT_DESCRIPTION": 4, "SCHEMA": 3, "EVENT_TEMPORAL_ORDER": 1, "EVENT_OBJECT_NOT_OBSERVED": 1}`。fence-body 錯誤另列：`{}`。完整原始錯誤訊息保留在 model_results.json。
- **nemotron**：物件描述次數 `{"basketball": 84, "phone": 68, "stuffed animal": 35, "box": 25, "microwave": 23, "cell phone": 21, "person": 18, "chair": 10}`；state entries `{"HELD_BY_PERSON": 232, "ON_SURFACE": 1193, "OTHER": 101}`；parsed/fence hypotheses 146，raw-strict hypotheses 58，類型 `{"PLACEMENT": 58, "PICKUP": 88}`。UNKNOWN 僅為模型自述，不當成錯誤標籤。
  狀態宣告 `{"EVENTS": 101, "NO_CONFIRMED_EVENT": 66}`；UNKNOWN 占可解析 state claims 0.00%；有引用的可解析輸出 167，全部 alias 存在 166，無引用 0。這是 membership，並非影像支持。輸入 token median／min／max：`{"count": 184, "median": 3112.0, "min": 3096, "max": 3112}`，不跨 tokenizer 比較計算量。
  Raw validation 錯誤類別（每窗每類最多計一次）：`{"EVENT_STATE_CITATIONS_INCONSISTENT": 47, "JSON_SYNTAX": 18, "STATUS_EVENTS_INCONSISTENT": 8, "EVENT_TEMPORAL_ORDER": 4, "SCHEMA": 3, "DUPLICATE_OBJECT_DESCRIPTION": 2, "UNSUPPLIED_ALIAS": 1}`。fence-body 錯誤另列：`{}`。完整原始錯誤訊息保留在 model_results.json。

**nemotron 已排除的啟動錯誤**：`ZMQError`：ipc path "/mnt/c/Users/smile/Desktop/test2/mixure_test_SAM/.runtime/nemotron/cache/TMPDIR/27847a41-21f9-49d5-b10a-655cc30fa0cd" is longer than 107 characters (sizeof(sockaddr_un.sun_path)). zmq.IPC_PATH_MAX_LEN constant can be used to check addr length (if it is defined). (addr='ipc:///mnt/c/Users/smile/Desktop/test2/mixure_test_SAM/.runtime/nemotron/cache/TMPDIR/27847a41-21f9-49d5-b10a-655cc30fa0cd')。完整 trace：[runs/nemotron/load_failure_01.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/runs/nemotron/load_failure_01.json)。這些失敗發生於生成前，不是品質重試。

**nemotron 已排除的啟動錯誤**：`RuntimeError`：Engine core initialization failed. See root cause above. Failed core proc(s): {}。完整 trace：[runs/nemotron/load_failure_02.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/runs/nemotron/load_failure_02.json)。這些失敗發生於生成前，不是品質重試。

完整逐模型／逐窗／parser 分層、資源、object/state summaries：[model_results.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/model_results.json)。來源相同的交集清單：[matched_inputs.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/matched_inputs.json)。候選事件與 source-time evidence brackets：[event_proposals.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/event_proposals.json)；括號不是物理事件持續時間，也不自動視為 true event interval。

## 5. GT 適用範圍與一致評估

既有人工來源保留：3 個 local-target strict-negative units（test1 W03/W05 去重、test2 W01、test5 W01）、2 個非完整 PICKUP 正例（test5/test7 W05）、1 個證據不足窗；test3 W07 繼續隔離。另讀既有五份 human-adjudicated model-call review，僅用其可支持的 physical-event/context 範圍，不把舊模型預測當 GT 或新模型答案。

**沒有新的人類 GT、沒有全九影片 exhaustive annotation、沒有正式 PLACEMENT positive。** 舊 GT formal_eligible=0，且主要只針對一個 local target；不能拿來評估通用 task 的所有物件與全影片負事件。舊 half-open GT 與本次 closed 端點也不同，部分最後一格超出原 GT 授權範圍，已逐筆列出。

| 指標 | 本次可報內容 |
|---|---|
| Object recognition recall／class confusion／wrong-target rate | 新逐物件人類標籤與 instance mapping 尚缺；不可估計，不能把 category 相同當同一 PersistentEntity |
| State accuracy／per-state confusion／unsupported-state frequency | 缺 reviewed frame-object-state/support GT；不可估計。模型 UNKNOWN/各 state 頻次另列，不把 unknown/unreviewed 算錯 |
| PICKUP precision／recall／F1 | 沒有本通用任務的 exhaustive eligible truth 與 reviewed identity/proposal groups；不可估計。known-positive cases 只作探索性描述 |
| PLACEMENT recall／F1 | 沒有 eligible positive，不可估計，不報 0 |
| Before/after/object/transition citation support | alias membership 與 consistency 可自動驗證；實際影像支持需人工，未審閱不判為成功 |
| JSON/schema/citation membership/truncation/efficiency | 可對實際完成 calls 報告，與 physical correctness 分開 |

同一 evaluator 對三模型一致處理。temporal matching 明定 0／0.2／0.5 秒（primary 0.2），閉區間距離 max(c−b,a−d,0)，one-to-one maximum-cardinality；需相同已人工確認 object ID/type/source video。無時間或身分則不匹配。精確 input duplicates 已去除；跨重疊窗的真實同一事件必須由人賦予同一 reviewed_event_group，不能只靠相似描述／重疊 bracket 把不同事件併成一件。未審閱 proposals 不入 authoritative matching，不重複數同一 human event。

所有 GT 來源 hashes、逐舊窗 eligibility／超出範圍 indices、sidecar 與不可估計原因：[gt_evaluation.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/gt_evaluation.json)。非完整窗的未列事件一律 UNEVALUATED，絕不自動算 FP。

### 舊負例與不確定範圍的描述性警報

以下只列新輸入是否產生候選，不計 FP：原 GT 僅針對 local phone target，且邊界可能比本次少最後一格。前三個 unit 是舊負例，test8 W07 則是證據不足，不能作正例或負例。沒有候選也不證明負例正確。test1 W03/W05 是同一負例單位，只列 canonical input。

| 舊 GT unit | 模型 | 新輸入狀態宣告 | raw/fence 候選事件 | raw full strict |
|---|---|---|---|---|
| test1__W03 → test1__W02 | qwen | NO_CONFIRMED_EVENT | 無可解析事件候選 | False |
| test1__W03 → test1__W02 | videollama | EVENTS | 無可解析事件候選 | False |
| test1__W03 → test1__W02 | nemotron | NO_CONFIRMED_EVENT | 無可解析事件候選 | True |
| test2__W01 → test2__W01 | qwen | NO_CONFIRMED_EVENT | 無可解析事件候選 | False |
| test2__W01 → test2__W01 | videollama | NO_CONFIRMED_EVENT | 無可解析事件候選 | True |
| test2__W01 → test2__W01 | nemotron | NO_CONFIRMED_EVENT | 無可解析事件候選 | True |
| test5__W01 → test5__W01 | qwen | NO_CONFIRMED_EVENT | 無可解析事件候選 | False |
| test5__W01 → test5__W01 | videollama | NO_CONFIRMED_EVENT | 無可解析事件候選 | True |
| test5__W01 → test5__W01 | nemotron | NO_CONFIRMED_EVENT | 無可解析事件候選 | True |
| test8__W07 → test8__W07 | qwen | NO_CONFIRMED_EVENT | 無可解析事件候選 | False |
| test8__W07 → test8__W07 | videollama | NO_CONFIRMED_EVENT | 無可解析事件候選 | True |
| test8__W07 → test8__W07 | nemotron | NO_CONFIRMED_EVENT | 無可解析事件候選 | True |

## 6. 物理證據與錯誤分析

以下是助理對實際選取影格及模型原文的 retrospective analysis，不是新的 human adjudication；案例選取包含既有 known positives 與實際格式／引用失敗，不代表隨機抽樣全體。

### test5__W05

本次選取 S342/357/373/388/404/419/435/450。F0001–F0004 手機在桌面，F0005/S404 與 F0006/S419 可見手持；F0007–F0008 不能可靠直接確認手機是否仍被握持。既有人工支持 PICKUP，但事件清單非完整，最後新採樣 S450 亦超出舊 half-open GT。

Qwen：phone F0005 寫 ON_SURFACE，與可見手持不符；F0006 正確描述 HELD，但 F0007/F0008 繼續確定 HELD 缺直接可見支持。仍回 NO_CONFIRMED_EVENT、events=[]，沒有提出已知手機拿起假說；原文帶 fence，不能當 raw-strict valid。VideoLLaMA：這次辨識到 phone，但 F0005 仍寫 ON_SURFACE，F0006–F0008 改為 OTHER，沒有捕捉可見的手持狀態；status=EVENTS 卻 events=[]，因此 semantic-invalid，不能把狀態字串 EVENTS 當成已產生 PICKUP。Nemotron：raw full-strict valid，提出 phone PICKUP，before F0001/ON_SURFACE、after F0008/HELD_BY_PERSON。這與既有已知事件類型相符，但沒有引用真正可見手持的 F0005/F0006，反而用手機被盒子遮擋且超出舊 GT scope 的 F0008；該格不能直接確認持握。因此僅能說它找到合理事件假說，不能說完成具物理支持的 grounding 或正式時間匹配。

### test7__W05

本次選取 S372/387/403/418/434/449/465/480。F0001/F0002 手機在桌面，F0003/S403、F0004/S418 可見手持；F0005 起沒有足夠直接手機可見支持。後段鏡頭移開，也無法從這些畫面直接確認籃球桌面狀態。既有人工支持 PICKUP，清單非完整。

Qwen：phone 與 basketball 都整段 F0001–F0008 寫 ON_SURFACE。手機在 F0003/F0004 的 state 錯誤，後段不可見物件的確定 ON_SURFACE 缺直接支持；回 NO_CONFIRMED_EVENT，漏掉已知手機拿起。VideoLLaMA：提出 basketball 與 cell phone 各一個 PICKUP，卻都引用 F0001→F0002；球在這兩格仍在桌面，沒有該球 pickup 的可見支持；手機在這兩格尚在桌面，模型已寫 HELD_BY_PERSON，真正可見手持的 F0003/F0004 又寫 OTHER。事件 citations 與它自己的 state 序列也不相容，strict semantic-invalid。Nemotron：raw full-strict valid，提出 phone PICKUP F0001→F0002；F0003/F0004 的 HELD 與可見手持相符，但 F0002/S387 尚未有確證拿起的支撐轉移，模型過早宣告 HELD，之後 F0005–F0008 又將不可直接看見的手機持續寫 HELD，且把後段不可見的球確定寫 ON_SURFACE。事件類型合理不等於時間或 after citation 正確；不能算已完成 grounded known-positive match。三模型都仍需要獨立 state/visibility/citation review。

### test1__W02 (canonical input for W03/W05)

本次選取 S156/171/187/202/218/233/249/264。F0001–F0003 有手接觸桌上的手機；單憑接觸不能確證拿起。F0004/S202 明確可見手機在桌面且沒有手持，之後仍在桌面。舊 test1 W03/W05 負例共用本 canonical input；新末格 S264 在舊 half-open scope 之外，不因此擴張負例 GT。

Qwen：可解析 fence-body 將手機全程寫 ON_SURFACE，沒有事件，這些可見狀態與採樣圖沒有上述矛盾，但 raw 仍因 fence 無效。VideoLLaMA：F0001/F0002 寫 HELD_BY_PERSON，手接觸本身不足支持；status=EVENTS 卻 events=[]，semantic-invalid。Nemotron：raw full-strict valid 且 NO_CONFIRMED_EVENT，然而將手機 F0001–F0004 寫 HELD_BY_PERSON，尤其 F0004 已沒有手持，與可見畫面不符。這是 schema/consistency 有效仍可含錯誤物理 state 的具體例子；不是新增 human GT 或可外推的錯誤率。

### test9__C0007

本次選取 S420/437/454/471/488/505/522/539。視點隨鏡頭改變；F0006 有手接觸球，後段球的完整支撐關係不易由樣本確證。盒子在 F0007/F0008 仍可見位於桌面，沒有手持盒子之支持。沒有本視窗的人類事件 GT，因此不將全部事件判成陰性。

VideoLLaMA：同時提出 basketball 與 box 的 PICKUP，after 引用 F0007/F0008；但自身 box state 在兩格仍寫 ON_SURFACE，事件與 state 不相容，strict-invalid，且這些影像也未支持盒子被拿起。鏡頭造成的畫面位置改變不能作為 pickup 證據；不能據此推定模型內部錯誤原因。對籃球保留不確定，不因這組稀疏樣本直接排除實際拿起。Qwen：沒有事件，球全段 ON_SURFACE；後兩格的支撐判斷需要人工確認，不能把其無事件當真實負例。Nemotron：raw full-strict valid，僅提出 basketball PICKUP F0001→F0008，沒有盒子事件；後格球僅部分可見，仍須人工完整影片確認支撐轉移，不能從 raw-valid 直接建立 positive GT。cell phone 在 F0007/F0008 的類別描述也沒有建立跨窗物理身分。

其他未逐格審閱的 state／target claims 保持 UNREVIEWED；不能因狀態描述合理或 schema 有效就標 correct。camera-motion-only 不能證明 manipulation；遮擋後的確定 HELD／ON_SURFACE、把類別當 instance、前後不匹配與不存在的 aliases 都需分開檢查。沒有對未審閱全體臆造錯誤率。

## 7. 人工審閱套件與交付入口

直接開啟 **[九影片人工審閱頁](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/human_review/INDEX.html)**：184 張 actual-frame contact sheets，source-video links，可另開完整 PNG；沒有預填模型答案。

- `events.csv`：video/type/object/time interval/support source frames/identity certainty/coverage review/reviewer。
- `states.csv`：1,411 個不同 source frames 的空白列；按物件填 state/visibility/support certainty/review status，同格多物件可新增列。
- `coverage.csv`：9 個 full-video review scopes，預設 UNREVIEWED；需完整區間、人類 exhaustive attestation、無可藏事件的缺口及 target association resolved，才可建立 exhaustive negative。
- `object_mapping.csv`／`proposal_review.csv`：人工辨認 model object、物理實體、事件群與 before/after/identity/transition support。
這是可編輯檔案與靜態頁面，不是新標註 web application。新填答案必須另行驗證，不能自動覆寫歷史 GT。

程式／原始資料：[三模型 runs/](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/runs)；[configuration.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/configuration.json)；[prompt.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/prompt.json)；[schema.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/schema.json)；[execution_components.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/execution_components.json)；[execution_integration_revisions.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/execution_integration_revisions.json)；[verification.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/verification.json)。

## 8. 保存、限制與下一步

保存檢查：8525 個既有檔案，變動 0；凍結資料／frames 變動 0；原片變動 0；552 份完成輸入 receipts 的 frames／共同 task／schema／表示檢查失敗 0；未記錄的 execution-component 變動 0。相容性修正另存 before/after 與真實錯誤證據；沒有改 prompt/schema/source selection 或根據輸出品質調整。8 個 CPU contract checks 通過，無視覺 fixtures、無品質重試。

CPU 檢查：`.venv/Scripts/python.exe -X utf8 -B -m unittest discover -s tests -p test_three_vlm_contract.py -v`；結果 [cpu_tests_final.log](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/cpu_tests_final.log)。這些只驗證採樣／parser／matcher／GT eligibility contracts，不是模型品質測試。

沒有改歷史 Qwen／VideoLLaMA／V297／GT／人工 review；沒有訓練、Graph 更新、commit 或 push。資料是開發用錄影，已被專案反覆使用，不能宣稱 held-out generalization。

**下一步：先在這個共同資料集完成事件／state／coverage 的人工審閱，再在相同 outputs 上重算 eligible metrics；不先換 prompt 或追加生成。** VLM 保持 physical-event hypothesis producer，deterministic software 負責 evidence/identity/temporal validation；本次沒有重新設計 Event-to-Graph。

### 重現用 SHA-256

| 固定輸入／組件清單 | SHA-256 |
|---|---|
| [dataset_freeze.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/dataset_freeze.json) | `dffa0aa2ee2e993639fabe052adb46270149df553b57595c24df38a55d25cf3a` |
| [configuration.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/configuration.json) | `0f9620451f69316caa876c6165a233aaca20d1d72e26e6d0dd1b42f2876787f5` |
| [prompt.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/prompt.json) | `c18cb7b49342dade429292647c2dd71834d8d972f5326fe2eb1ba5bb36b04b9a` |
| [schema.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/schema.json) | `7bf285da94efe46125736b37e46bafb6512c98eab11eb6958c3aaea219e804f3` |
| [execution_components.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/execution_components.json) | `16addc89728835b14c4501bdb1112dc35efb032ecd0e4b58aeab067024526414` |
| [execution_integration_revisions.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase3/three_vlm_full_v1/execution_integration_revisions.json) | `01b4bfb7e250b16ebab6eb26882b9a315ffe5c2a1b553840089ef12a5e41d9f3` |
