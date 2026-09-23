# V2.1 — Persistent identity and independent bottleneck evaluation

本次在既有 V2 上新增獨立擴充，保留 V1/V2 程式、模型與成果。研究目的是分辨 detector、local tracking、persistent association、admission、semantic/relation reasoning 的失敗。沒有實作 segmentation propagation、SAM 3、尋物 ranking、UI 或 3D memory。

完整實測與 SAM 決策見 [V21_VALIDATION.md](V21_VALIDATION.md)。GT 只放在 `evaluation/v21`，只能由 `scripts/evaluate_v21.py` 讀取。Inference CLI 沒有 GT 參數。

完整回歸測試：**65 passed**。569 個 V1/V2 baseline 檔案的 preservation audit 通過。必要歷史裁切最長邊限制384px，三張場景圖維持原本960px設定；沒有更換VLM。

## 流程

```text
video → unchanged YOLO/local tracker (verified cache allowed)
      → track quality and crop appearance
      → PersistentEntityResolver over ALL usable tracklets
      → unchanged V2 event proposal / selection / semantic VLM
      → extra persistent-context VLM on selected events
      → image-plane Observation Graph / physical candidates
      → conservatively promoted temporal Memory Graph
      → frozen prediction hashes

frozen predictions + evaluation-only manual/narrative GT
      → detection / tracking / association / admission / reasoning metrics
      → bottleneck assessment and controlled A/B proposal
```

Identity 在事件執行之前建立。事件候選器沿用 V2 local-track 訊號，事件上下文再映射到 persistent IDs；本次沒有把事件重要性改成身份 admission 條件。這是 offline video pipeline，外觀與 track quality 可使用完整 tracklet，並非宣稱即時 causal 系統。

## 執行

使用原本 `configs/v2_gpu_7b.yaml` 與已下載的 Qwen2.5-VL-7B-Instruct NF4/BF16，不更換模型。

```powershell
uv run --extra vlm --extra gpu --extra quantized pytest -q
uv run --extra vlm --extra gpu --extra quantized scripts/run_video_v21.py test1.mp4 --reuse-v2 outputs_v2/task1 --output outputs_v21/task1
uv run --extra vlm --extra gpu --extra quantized scripts/run_video_v21.py test2.mp4 --reuse-v2 outputs_v2/task2 --output outputs_v21/task2
uv run --extra vlm --extra gpu --extra quantized scripts/review_v21.py test1.mp4 outputs_v21/task1 --seconds 9 10 11.6 12 12.4 12.8 13.2 13.6 14 16 24
uv run --extra vlm --extra gpu --extra quantized scripts/review_v21.py test2.mp4 outputs_v21/task2 --seconds 3 4 5 6 9.6 10.2 10.4 17.6 18 18.4 18.6 18.8 19.2 19.6 19.8 20 20.4 22 26 28
uv run --extra vlm --extra gpu --extra quantized scripts/audit_v21.py outputs_v21/task1 outputs_v21/task2
uv run --extra vlm --extra gpu --extra quantized scripts/evaluate_v21.py outputs_v21/task1 evaluation/v21/task1_annotations.json
uv run --extra vlm --extra gpu --extra quantized scripts/evaluate_v21.py outputs_v21/task2 evaluation/v21/task2_annotations.json
```

省略 `--reuse-v2` 可重新執行 perception。`--events-only` 不載入 VLM，仍建立 identity 與幾何 observation。重跑 GPU 時，同輸入可命中內容雜湊 cache；context 的 cache 另含實際 prompts、image hashes 與 backend identity。此次沿用 V2 已有語意 cache，但新增 persistent-context 的 **16 次生成都是真實 GPU 推論**。

若環境已安裝完成而網路不可用，可用 `uv run --no-sync python ...`，或 Windows 的 `.\.venv\Scripts\python.exe ...` 執行同樣腳本，避免 uv 再查詢套件 metadata。此次最後測試使用後者，65項通過；不會為了重新執行下載模型。

輸出必須獨立於 V1/V2 目錄。`event_analysis/` 是本次重用 V2 runner 的中間產物，其中的舊 V2 memory 不是 V2.1 最終 memory；請看外層 `memory_graph.json`。

## 模組與契約

| 模組 | 責任 |
|---|---|
| `v21/contracts.py` | identity 設定、persistent entity、NONE/UNCERTAIN/SUPPORTED VLM schema |
| `v21/quality.py` | duration、observation count、gaps、bbox center jumps、motion change、semantic/appearance consistency |
| `v21/resolver.py` | 多線索 gated MATCH／AMBIGUOUS／NEW_ENTITY；候選分數與 veto 全部保留 |
| `v21/context.py` | 三相位完整圖、ID 映射與最後確認 crop；無當前 observation 就不補 bbox |
| `v21/graphs.py` | 語意聚合與 image-plane／physical candidate／promotion 分離 |
| `v21/pipeline.py` | 不讀 GT 的獨立 orchestrator；先 identity，再事件與語意 |
| `evaluation_v21/evaluator.py` | 只讀凍結 predictions 與人工 GT，分層評估、時間軸及瓶頸診斷 |

Resolver 的 identity IDs 是 `entity_0001` 等無語意名稱，絕不使用 GT 的 smartphone_01 等名稱。短 gap、外觀、位置、motion、area ratio 必須共同通過；同時可見的 tracks 不合併，ambiguous 不強制合併。Context／semantic compatibility 分量保留，其中 context 目前只供診斷；3D、mask、camera compensation 與 interaction continuity hooks 為 null，沒有假裝已實作。

每個 entity 保存 local tracks、association history、last confirmed time/bbox、逐取樣 visibility history、uncertainty。未觀測超過門檻可標 LOST，意思是 tracking 證據失聯，**不是物理物件消失或尋物結論**。UNOBSERVED／LOST 的 current_bbox 必須為 null。

BEFORE 可見、後續漏偵測的 supplied track 必須保留 historical crop；除此之外，最近四秒內最後確認的未觀測 track 每事件最多補入兩個。必要 before-visible context 不受額外預算排擠。長時間 detector/tracker 缺失仍可能超出窗口；不是所有歷史身份都能送入 VLM，未被選中的仍保存在 memory。此限制是實測瓶頸之一，不能宣稱已恢復 task2 手機全程。

## Observation 與物理記憶

2D 方位／距離一律 `IMAGE_*`／`reference_frame=image_plane`，`physical_confidence=null`。有效 VLM 回覆可能只形成 CANDIDATE。Promotion 要求多個不同事件支持、至少兩個實際共同可見影格、足夠信心，以及既有 geometry validator 的獨立支持。候選時間與來源保留；過時支持標 STALE。沒有觀察不能自動 ENDED，也不會自動斷言 OCCLUDED／OUT_OF_VIEW。

這個門檻刻意保守，本次兩片 promoted physical relations 都為 0；觀察圖仍有 90／82 個關係。零錯誤 promotion 不代表高 physical-relation recall。

## 輸出

兩片均有規格要求的 track_quality_report、persistent_entities、track_entity_associations、ambiguous_associations、admission_failures、observation_graph、memory_graph、error_analysis、bottleneck_assessment JSON；tracking_diagnostic_timeline、memory_graph_overview、observation_graph_debug PNG；每個 tracklet/entity 的 contact sheet 與 JSON；gt_review 原圖、detections 疊圖、annotation template、手機診斷時間軸；validation_report.md。

另存 `identity_rejected_tracks.json`、`persistent_entities_pre_semantics.json`、`relation_candidates.json`、`prediction_manifest.json`。`event_analysis/events/*/persistent_context_vlm.json` 包含真實 prompt／原文／backend／影像 hashes；`persistent_context_input.json` 標示歷史 crop 與每相位 visibility。這些是模型解讀，不能當真值。

## 評估界線

人工框標註是助理逐張檢視的稀疏、非隨機診斷樣本，沒有密集逐幀人工專家標註。採 class-agnostic IoU≥0.3 計 detection，再獨立看 class、local track 及 persistent mapping。遮擋、出畫及不確定影格不進 recall 分母。沒有從敘事推造 exact intervals，沒有對未標註時段內插。圖片可能同時有桌機與手機，必須依各自 bbox 評估。

短 track 被 V2 admission 排除是 counterfactual 診斷，不自動等同所有排除都不合理。重要物件的 admission 損失只在有人工 mapping 時判定。全片 purity、exact ID-switch count、全片 recall 未具足夠 GT，報 `NOT MEASURABLE FROM CURRENT GT`。

