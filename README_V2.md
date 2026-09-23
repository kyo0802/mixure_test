# V2：事件驅動的語意時間記憶

低成本 YOLO／tracking 持續提出候選事件；只對選定事件做多影格 VLM 分析，再把固定 track ID 的語意與關係整合成時間記憶。這是 RGB／影像座標原型，不是真實 3D、物件永久性或長期 ReID 系統。

實際結果、人工影格檢查、V1 比較及 20 項驗收見 [V2_VALIDATION.md](V2_VALIDATION.md)。機器可讀稽核見 [docs/v2_artifact_audit.json](docs/v2_artifact_audit.json)。`confirmed` 表示通過程式 schema／信心門檻的模型解讀，**不代表人工真值已確認**；錯誤與 unknown 都需要保留。

## 本機輸入及輸出

本次輸入為 `test1.mp4`、`test2.mp4`，分別以 task1／task2 命名輸出目錄。

| 目錄 | 用途 |
| --- | --- |
| `outputs_v2/task1`、`outputs_v2/task2` | 實際 GPU VLM + V2 |
| `outputs_v2_events/task1`、`outputs_v2_events/task2` | disabled／event-only 對照 |
| `outputs_v1_comparison/task1`、`outputs_v1_comparison/task2` | 此機重建的 V1 對照 |
| `outputs/task1`、`outputs/task2` | 歷史目錄，沒有搬入本機，也沒有覆寫 |

V1 原始程式及測試保留。`docs/v1_preservation_manifest.json` 是歷史清單；其中 `graph_visualizer.py` 的既存差異與缺少的歷史輸出，和本次修改分開記錄。

## 安裝及執行

Python 3.12。Windows RTX 5070 Ti 已驗證 CUDA 12.8 PyTorch。GPU 額外依賴固定官方 Windows CPython 3.12 wheel；其他平台請依 PyTorch 官方指示安裝適用的 CUDA runtime。

```powershell
uv sync --extra vlm --extra gpu --extra quantized
uv run --extra vlm --extra gpu --extra quantized pytest -q
```

若預設 PyPI 下載很慢，可於 sync 加 `--index-url https://pypi.tuna.tsinghua.edu.cn/simple`；lockfile 保留來源及 hashes。`gpu` 及 `quantized` 是選用依賴，不會自動啟用 VLM。GPU 執行時保留相同 extras，避免 uv 改回一般 PyTorch 環境。

下載固定版本的模型（一次即可；不會上傳影片）：

```powershell
uv run --extra vlm --extra gpu --extra quantized hf download Qwen/Qwen2.5-VL-7B-Instruct --revision cc594898137f460bfe9f0759e9844b3ce807cfb5 --local-dir .models/Qwen2.5-VL-7B-Instruct
```

正式 V2 GPU 設定使用 7B NF4、BF16 compute、逐 track grounding；3B 診斷設定仍在 `configs/v2_gpu.yaml`。原 `configs/v2.yaml` 維持 disabled，也保留 SmolVLM local 與 HTTP backend 介面。

```powershell
uv run --extra vlm --extra gpu --extra quantized python scripts/run_video_v2.py test1.mp4 --config configs/v2_gpu_7b.yaml --output outputs_v2/task1
uv run --extra vlm --extra gpu --extra quantized python scripts/run_video_v2.py test2.mp4 --config configs/v2_gpu_7b.yaml --output outputs_v2/task2

uv run --extra vlm --extra gpu --extra quantized python scripts/run_video_v2.py test1.mp4 --events-only --output outputs_v2_events/task1
uv run --extra vlm --extra gpu --extra quantized python scripts/run_video_v2.py test2.mp4 --events-only --output outputs_v2_events/task2
```

`run_all_v2.py` 可接明確影片路徑：

```powershell
uv run --extra vlm --extra gpu --extra quantized python scripts/run_all_v2.py test1.mp4 test2.mp4 --config configs/v2_gpu_7b.yaml
```

此批次指令預設使用影片 stem（`outputs_v2/test1`、`test2`）；上方單片指令才使用本次報告的 task1／task2 路徑。未給影片參數時仍保留舊 `task1.mp4`／`task2.mp4` 預設。

## 流程與資料契約

1. **Perception**：YOLO11s、5 FPS 取樣、ByteTrack、固定整數 track ID，保存 bbox、時間、速度、鄰近物件及可見性。ID 只在單支影片內有效。
2. **事件**：持續出現、持續未偵測、距離改變、共同運動、鄰近關係改變；有限長度合併、cooldown、priority、每片預設最多 8 個事件。這些都是候選訊號，鏡頭移動也可能造成訊號。
3. **Grounding**：每個事件保存 before／during／after 和可見 ID；額外 crop sheet 協助檢查。GPU staged backend 對每個 supplied track 的可見裁切辨識一次，再用三張場景影格分析關係。最多 6 個 supplied tracks + 1 次關係分析／事件，因此事件預算不是單次模型呼叫預算。沒有把每個影片影格送給 VLM。
4. **Structured VLM**：每個 component 保留真實 prompt、原始回覆、影像來源及錯誤。track ID 不可變；Pydantic 驗證類別、信心、属性、關係 enum、phase、arity 和 event ID。無效 component 不修補成想要的答案；其他獨立有效 component 可保留，事件標為 partial。
5. **Scene graphs**：以一般 entity/entity 關係組圖，human/body-part → object 可表示 HOLDING 等互動。相位共現、方向、距離、重疊、包含與 actor 類別驗證不合理回覆；動態動作及持續性聲明至少需兩個不同影格。geometry 不能證實真實接觸、動作或 3D。
6. **Memory admission**：觀察次數、時間、平均信心、面積與事件參與門檻先過濾 noisy tracks。依固定 ID 聚合語意；互相衝突時保留 unknown，不會把同類椅子合併。保留稀疏支持時間、phase、事件來源及保守的 observed transitions。
7. **Visualization**：事件時間軸、事件圖、最終一般網路圖、完整 annotated video。Anchor 只保留為 metadata／邊框提示，不是組圖中心。圖像可能只顯示部分節點／edges，`.render.json` 明列顯示與省略數目，JSON 保存完整資料。

## 重要檔案

每次執行：`track_timelines.json`、`raw_event_proposals.json`、`merged_events.json`、`active_event_ids.json`、`vlm_schema.json`、`run_config.json`、`hardware.json`、`run_status.json`、`rejected_tracks.json`、`semantic_aggregation.json`、`entity_id_mapping.json`、`memory_graph.json/png`、`event_timeline.png`、`annotated_v2.mp4`。

每個 selected event：`event.json`、`keyframes.json`、`before.jpg`、`during.jpg`、`after.jpg`、`track_crops.jpg/json`、`vlm_input.json`、`prompt.txt`、`vlm_raw.json`、成功／partial 時的 `vlm_validated.json`、`scene_graph.json/png`。Staged 模式額外保存 `identity_<ID>_<phase>.jpg`；**實際使用的分階段 prompts 以 `vlm_raw.json.generation_trace` 為準**。`prompt.txt` 是通用 joint backend 的事件 prompt。

`vlm_raw.json.response` 在 staged 模式是獨立通過 schema 的 components 集合；原封不動的模型文字位於 `generation_trace[].response`。`component_errors` 列出被丟棄的 components；不能把 partial 稱為全成功。

VLM cache 包含影像內容、模型／revision、dtype／量化、套件版本、prompt／grounding 版本及 metadata。失敗回覆也保留 cache。改設定／prompt 會建立不同 cache；重跑相同輸入使用既有證據，不會重新生成語意。Perception cache 另含影片、模型權重、設定與 runtime versions。

## 檢查與限制

```powershell
uv run --extra vlm --extra gpu --extra quantized python scripts/inspect_memory_v2.py outputs_v2/task1/memory_graph.json
uv run --extra vlm --extra gpu --extra quantized python scripts/contact_sheet_v2.py outputs_v2/task1 outputs_v2/task2
uv run --extra vlm --extra gpu --extra quantized python scripts/audit_v2.py outputs_v2/task1 outputs_v2/task2 outputs_v2_events/task1 outputs_v2_events/task2
```

稽核驗證選擇預算、ID／crop 來源、有效 JSON、關係端點、時間區間、PNG/JPEG 及整支 MP4 可解碼性。它不會自動判定籃球／垃圾桶真值；見人工檢查報告。

track fragmentation、遮擋、錯誤／重疊框、鏡頭運動及 VLM hallucination 仍存在。`semantic_corrections` 是模型標籤不同於 YOLO 的紀錄，包含一般同義詞變更及錯誤修正候選，**不是正確率**。類別信心是模型自報，未校準。沒有 lost-object candidate ranking、尋物 UI、深度／SLAM、3D memory 或範圍外的後续功能。

官方參考：[Qwen2.5-VL](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)、[PyTorch 安裝](https://docs.pytorch.org/get-started/locally/)、[bitsandbytes CUDA／Windows 支援](https://huggingface.co/docs/bitsandbytes/main/en/installation)。
