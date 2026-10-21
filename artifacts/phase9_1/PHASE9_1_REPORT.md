# FindMind Phase 9.1 — 互動記憶圖譜與 Nemotron 啟動優化

更新：2026-10-21。狀態：**實作與 CPU／瀏覽器驗收完成；GPU 啟動與整支影片加速量測尚未執行。** 本報告的 authoritative source 是 `artifacts/phase9_1/PHASE9_1_REPORT.md`；WORKSPACE 為日常閱讀副本。本次未 commit／push。

## 1. 完成內容

- 現有 Streamlit 新增 **Memory Graph / 記憶圖譜**，直接讀取目前選取 session 的 persisted records。
- 可平移、縮放、點選節點／關係、突出直接相鄰紀錄；依類別、節點種類、原生時間、狀態與關係篩選。預設上限 100、最高 300 節點；顯示篩選與上限隱藏數。
- 搜尋結果可帶精確 observation／location／region IDs 進圖譜；從出門清單找物也走同一條路。找不到精確引用時明示 CATEGORY_FILTER_ONLY；沒有鑰匙證據就呈現空圖，沒有造新節點。
- Nemotron 使用具預期 SHA 的版本化資產 manifest 與原子 verification receipt，第一次完整驗證，後續可依相符 metadata 復用。strict／force 模式仍逐檔完整 SHA。
- Windows job wrapper、Phase 7 subprocess、Linux launcher、資產驗證、runtime imports、engine init、request preparation、generation、serialization 皆新增 CPU monotonic timing；原 prompt／video array／生成設定／raw outputs／strict validation 契約保留。

## 2. Nemotron：找到什麼瓶頸

實際路徑：Streamlit submit → 既有磁碟 GPU lease → `run_findmind_job.py` → `run_findmind_video.py` → Windows `run_worker` → WSL Ubuntu → Linux launcher → 同一個 vLLM engine 依序處理影片所有視窗 → 程序退出 → Qwen → SAM。

**原來就已每支影片載入一次、重用於所有視窗。沒有逐視窗重載。** 不同影片／程序之間沒有常駐模型。

| 邊界／操作 | 現有證據與量測 | 解讀 |
| --- | --- | --- |
| test8 Nemotron stage | 歷史 482.359 s | 包含 WSL 程序與退出成本 |
| test8 `load.json` | 歷史 435.121 s | 涵蓋 hashing、imports、配置與 engine 等，原始程式沒有逐項計時 |
| 權重反序列化 | 歷史 vLLM log 48.97 s | 模型載入的子項，不能相加兩次 |
| 模型載入 | 歷史 vLLM log 67.225 s，約 9.95 GiB | 包含上述權重步驟 |
| engine profile／KV／warmup | 歷史 vLLM log 8.77 s | 不是完整外層初始化時間 |
| test8 load 後至 receipt | 歷史約 36.002 s | 包括四視窗 preparation、generation、validation／serialization，不是純 token generation |
| test8 receipt 至 stage exit 差額 | 約 11.236 s | 不能只歸因於 WSL 或 shutdown |
| WSL 啟動、imports、獨立 CUDA init、其他 config | 歷史無法分別歸因 | 新增 instrumentation，待下次有授權的新影片執行記錄；未捏造數字 |
| 第二支既有影片 test2 | stage 519.031 s；load 490.045 s | 另一個歷史 aggregate，未重跑 |

原程式確實在每支影片重新讀取所有 `.json`／`.py`／`.safetensors`，只保存 hash，沒有與固定預期 digest 比對。這次把相同的 22 個資產 pinned 成 manifest，且對三個 weight digests 與已下載 Hugging Face revision metadata 交叉核對；小檔案 SHA 來源是既有完成 session 的本機量測，**不是出版社簽章**。

**沒有把整段 435 秒宣稱成 hashing。** 本次只直接證明並移除了重複 SHA 的成本；其餘細項仍待 instrumented GPU run。

## 3. 實際效能量測

本次在與正式 runtime 相同的 Ubuntu WSL／9P 模型路徑執行 CPU-only 驗證，沒有載入模型或初始化 CUDA：

| 操作 | 量測 | 結果 |
| --- | --- | --- |
| 強制完整 SHA 驗證 | **63.722993 s** | 22 fresh files，0 cached |
| 下一次 metadata receipt 驗證 | **0.324058 s** | 0 fresh files，22 cached |
| test8 Graph 首次解析＋驗證＋投影 | **0.198814 s** | 3,911 視覺節點、5,511 record edges |
| 同一程序再次讀取 Graph | **0.113355 s** | 每次仍核對 Graph／manifest hashes；CPU cache 復用解析投影 |

完整驗證是 fresh cryptographic verification，**不保證 OS 檔案 page cache 為冷**。第二列是 metadata cache validation，不是暖模型推論時間。沒有重算模型 SHA 來驗證前一份 SHA；第二次確實沒有再次讀取模型 bytes 計算 digest。

本次沒有新 GPU generation，沒有新的 optimized cold engine／warm generation／新影片總耗時／peak VRAM 量測。不能把上述 63.4 秒差額直接換算成整支影片節省量。

原始量測：[完整 SHA](verification_full.json) · [快取驗證](verification_cached.json) · [Graph CPU](GRAPH_CPU_MEASUREMENT.json)。

程式與 pinned manifest 的前後 SHA：[Source change manifest](SOURCE_CHANGE_MANIFEST.json)。資產 manifest SHA-256：`5821fa4f56f63980d5cea0c9244cdc16b4dbe285b53bbef60d9f5f3c29ee04b3`。

## 4. 驗證 receipt 與信任邊界

資產 manifest：`config/findmind_nemotron_assets.json`；policy `nemotron_asset_sha256_v1`。本機 receipt：`.runtime/nemotron/verification/assets_v1.json`。

- repository、revision、manifest bytes SHA、policy、algorithm、canonical model／file location、size、mtime_ns、ctime_ns、inode、device、預期／實測 digest、UTC 驗證時間與 outcome 都參與驗證。
- 缺少／損壞 receipt、版本／manifest／metadata 不符會完整重驗；檔案集合改變、size／SHA 不符直接失敗。已知 SHA mismatch 會寫 FAILED tombstone，不能沿用舊成功 receipt。
- 每檔 hash 前後及 receipt 提交前都檢查 metadata。receipt 用獨立 temporary file＋flush/fsync＋atomic replace 寫入。
- `FINDMIND_NEMOTRON_VERIFICATION=strict` 或 `FINDMIND_NEMOTRON_FORCE_VERIFY=1` 可強制重驗；Windows → WSL 明確傳遞這兩個 allowlisted 參數。
- receipt 是**可信本機儲存環境下的 metadata 信任政策**。它不等同每次 fresh SHA，也不抵抗可竄改 cache、檔案並還原 metadata 的本機攻擊者。需要每次 cryptographic validation 時使用 strict。
- canonical path／OS file identity 不同會失去 cache 命中；請以 WSL 執行驗證命令，以符合實際 runtime。

## 5. 為何沒有新常駐 worker

選擇 **optimized cold start＋既有單影片多視窗重用**。歷史日誌顯示權重約 9.95 GiB，另有約 2 GiB KV cache／activation；16 GiB RTX 5070 Ti 還需要給 Qwen、YOLO、SAM。既有 lifecycle 已依序交接 GPU，沒有證據支持跨工作常駐能安全降低整體耗時。

因此沒有新 server、外部 inference endpoint、第二個 GPU lock 或假 persistent 模式。原先背景工作 lease、timeout 後保留 lock、不盲目 retry、partial-session 規則均保留。Graph-only 查詢仍不載模型。

## 6. 真實 Graph schema 與唯讀映射

來源是 `TemporalMemory(schema_version=2.0)`，`SemanticEntity` 及 metadata records；不是每個事實都已存成獨立 graph node。adapter 僅建立 presentation projection，不回寫 Graph。

| 視覺元素 | 實際資料來源 | 語意 |
| --- | --- | --- |
| Candidate | observations 的精確 `object_instance_candidate` 值與 observation IDs | 本機候選／追蹤引用；不因相同類別合併，不是個人物品或實體計數 |
| Identity | 同時有 `authorized_entity_id` 與 `identity_authorization` 的 observation | 只顯示已保存的身分授權；不據此發明 verified location |
| Observation | `/metadata/observations/i` | observation_id、source frame、source time、bbox、provider／provenance |
| Region | `/metadata/scene_regions/i` | frame-scoped candidate surface／detector extent；不是永久房間或場景 ID |
| SpatialEvidence | `/metadata/location_observations/i`；舊格式 fallback 指向實際 candidate／trusted history index | 原始位置／投影紀錄；CANDIDATE、UNKNOWN 等不轉為已確認事實 |
| Event | `/events/i` | 原來 PICKUP／PLACEMENT hypothesis、decision、before／after refs；不是已發生動作 |
| Edges | 原 `/metadata/graph_edges/i` | 使用原本 OBSERVED_BY、HAS_LOCATION_EVIDENCE、NEAR_REGION、POSSIBLY_ON_SURFACE 等 predicate |
| 引用連線 | `object_observation_id`、authorization、supporting／conflicting IDs | 明示 reference-only，不是新增的物理關係 |

每個 node ID 都含 session、node kind、原始 record ID，每個 node／edge 有 source JSON pointer。原本 frame anchor edges 以 PTS／frame 資訊顯示，不生成大量時間節點。沒有由幾何距離另外推導視覺連線，沒有 SAME_ENTITY 捷徑。

Cache key 是已驗證的 session＋Graph SHA；每次先驗證來源。切換 session 或 Graph bytes 改變就清除 selection、filters 與 evidence keys。元件只接收 bounded presentation payload，不把整個 Graph 或模型載進瀏覽器。

## 7. test8 的展示意義

真實 test8 有 **3 筆手機 candidate-location records、2 組時間／區域搜尋證據、0 VERIFIED**：

- f414：13.803333 秒，NEAR_REGION 桌面候選。
- f180：6.008333 秒，兩筆不同來源／引用的候選位置紀錄。
- 另有原始 UNKNOWN 關係紀錄可供展開；它們不會變成額外的已確認手機。
- 事件是 1 UNCERTAIN、1 REJECTED。搜尋 neighborhood 預設只顯示直接相關紀錄；取消 checkbox 可展開類別全部紀錄與事件。

預設搜尋 neighborhood 顯示 15 個 presentation nodes（其中包含原始 UNKNOWN 引用），不是 15 個物體。完整 phone 類別視圖是 44 nodes。原搜尋排序、三筆 candidate／兩組顯示與不確定性均保留。

## 8. 瀏覽器實際驗收

已在本機 8514 真實 UI 操作：

1. 選取 test8 → 繁體中文手機查詢 → POSSIBLE_LOCATIONS → View in Memory Graph，EXACT_RECORD_IDS。
2. 點 SVG observation node → 詳情更新為原 observation；平移、縮放、相鄰 highlighting 實際工作。
3. 點 NEAR_REGION edge → CANDIDATE 及原始 edge pointer；選區域節點可看原片 f414／13.803333 秒。另一筆關係對應 f180／6.008333 秒。
4. 回 Find Item 保留 session；鑰匙查詢 UNKNOWN → CATEGORY_FILTER_ONLY → 空圖，沒有造 keys node。
5. 建立新的 DEMO_PRESENTATION 檢查 `6165516472c14163ba30fec4cea21af7` → 手機 Find → Search → Graph → 返回清單。查看記憶後仍有 3 件待確認；明確確認手機才變 2 件，撤銷後回 3 件。
6. 切到原本已完成的 test2 session → Graph 變成該影片 14 個 phone nodes，證據變為 f534／17.808333 秒，沒有沿用 test8 IDs 或 f414 影像。新 session 不是硬編碼特例。

截圖：[互動圖譜](MEMORY_GRAPH.png) · [來源影格與 PTS](GRAPH_EVIDENCE.png)。窄側欄截圖可見平移與部分畫布；在完整瀏覽器開同一個本機網址可使用更大空間。

本次只新增一份展示檢查並記錄 confirm／undo，不作實際攜帶證明。舊檢查未改寫；新檢查留下三件待確認。

## 9. 測試與保存驗證

| 執行集合 | 結果 |
| --- | --- |
| `test_phase9_1*.py` | 32 passed |
| `test_findmind_*.py` | 46 passed（含 Demo、departure 與既有離線 GT 工具測試） |
| `test_phase[4-7]_*.py` | 71 passed |
| 合計 | **149 passed** |
| Python source AST、component JavaScript syntax | 通過 |
| 新程序 Graph imports | torch／vLLM／Ultralytics／Transformers 均未載入 |

覆蓋首次／快取／force／strict／metadata 與 revision 失效、corrupt receipt、known mismatch、asset set、缺少 worker不重試、WSL 參數傳遞、原 prompt與 generation AST 不變、來源 ID／pointer、類別／時間／狀態篩選、node cap、search handoff、session isolation、真實 overlay、缺少／越界證據與 GPU-free imports。

第一次舊 Demo 回歸有 3 項失敗：測試把最新 test2 session 誤當成原本唯一的 test8。已只修改測試的 fixture 選擇，沒有改產品排序、threshold 或預期結果；最終重跑通過。初次失敗 log 保留。

兩支 session 的 Graph、manifest、receipt、search_result、event_decisions 與 7 份 raw outputs，共 **17 個歷史檔案 SHA 全部相同**。第 18 個受檢檔案是清單狀態，因上述新增展示檢查而預期改變。GT、Frozen assets 與模型輸出未改寫。[保存驗證](PRESERVATION_CHECK.json)。

測試原文：[focused](focused_tests_final.log) · [Demo／清單](demo_regression_final.log) · [Phase 4–7](phase4_7_regression.log)。

## 10. 本機命令

啟動現有 FindMind（不自行載入模型）：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\start_findmind_demo.ps1
```

開啟 http://127.0.0.1:8514/，選影片記憶，再選 Memory Graph。新 MP4 → 原 Phase 7 → persisted session → Search → Graph 路徑保留；本次沒有為 UI 重跑影片。

CPU-only 資產驗證（WSL，匹配正式 runtime 的 path／file identity）：

```powershell
wsl -d Ubuntu --exec /mnt/c/Users/smile/Desktop/test2/mixure_test_SAM/.runtime/nemotron/venv_linux/bin/python -B /mnt/c/Users/smile/Desktop/test2/mixure_test_SAM/scripts/verify_findmind_nemotron.py
# 每檔完整 SHA：同一命令加 --mode strict 或 --force
```

實際新影片流程預設 `cached`。需要嚴格重驗時，在啟動 CLI／Streamlit 前設定：

```powershell
$env:FINDMIND_NEMOTRON_VERIFICATION = 'strict'
# 或只強制這次 full verification
$env:FINDMIND_NEMOTRON_FORCE_VERIFY = '1'
```

恢復快取：設定 verification 為 `cached`，force 為 `0`。沒有 persistent runtime switch，因為本次未實作跨影片常駐模型。

## 11. 限制與下一步

- 優化後 engine cold start、first／warm generation、WSL startup、shutdown、總新影片耗時與 peak VRAM **待量測**；instrumentation 已接入。下一次實際新影片工作即可產生詳細 trace，不需要另建實驗框架。
- 沒有常駐 worker；Qwen／SAM 的載入成本未優化，端到端仍可能昂貴。
- 此次以 mocks 測新的 worker integration／guards，以真實已保存 session 測圖譜；未跑新的整支 GPU pipeline，不宣稱該整條路徑已重新驗收效能。
- 圖譜仍是 RGB、frame-scoped、稀疏觀察；沒有連續存在／物理接觸／目前位置保證。原身分、事件驗證及 ranking policy 未變。
- 未定位全部三維場景；圖譜只投影實際 records，未解析的 anchor／endpoint 計數保留。節點上限 300，較大資料需類別／時間切片；所有原紀錄仍在 authoritative Graph。
- 本機 metadata cache 是明示的信任取捨，需要嚴格模式時每次完整驗證。新環境也仍需原本模型／WSL／依賴與 session，不提供自動下載。

下一個實際步驟是由操作者在合適時機處理一段新影片，檢查 `nemotron_process_timing.jsonl`、`vlm/timing.jsonl`、`vlm/asset_verification.json` 與既有 vLLM log；分開報告 verification、imports、engine、generation 與整體耗時。此報告沒有自動建立其他工程階段或啟動模型。
