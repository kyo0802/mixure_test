# Phase 7：新影片端到端流程實作與實跑報告

更新：2026-10-21。**PHASE7_FRESH_VIDEO_PIPELINE_IMPLEMENTED_AND_INTEGRATION_VERIFIED**

來源：`artifacts/phase7/PHASE7_REPORT.md`。本次已完成單一 MP4 入口、實際 CV／Nemotron／定位推論、既有 TemporalMemory 儲存與重開查詢。這是可用的候選空間記憶流程；尚未解決可靠身分、物理接觸或目前位置保證。

## 怎麼使用

在 `C:\Users\smile\Desktop\test2\mixure_test_SAM` 執行：

```powershell
# 新影片：自動建立新 session、執行模型、保存 Graph、回傳查詢
.venv\Scripts\python.exe -X utf8 -B scripts/run_findmind_video.py --video "C:\Videos\new_video.mp4" --query "Where is my phone?"

# 已保存 session：不載模型、不重新推論
.venv\Scripts\python.exe -X utf8 -B scripts/run_findmind_video.py --session "artifacts/findmind_sessions/video_932b70d6ece1c5b31493_20261020T223911Z_3e1a9e" --query "Where is my phone?"
```

新影片不需要先製作 manifest 或模型輸出 bundle。原 MP4 不複製；每次 process 建立獨立 session。終端顯示前五個結果，完整結果在 `search_result.json`。Python API 為 `memory_graph.integration.fresh_video.search_session`。

可用 `--target-category` 明確指定感知類別；`--window-seconds` 預設 12、`--cv-fps` 預設 5、`--localization-budget` 預設最多 6 張。已有 session 的新查詢只搜尋已保存證據，不能補做尚未感知的物體。輸出多筆候選可能是同一物體不同時間／不同關係，不是多個已確認實例。

## 本次實際跑了什麼

執行命令：

```powershell
.venv\Scripts\python.exe -X utf8 -B scripts/run_findmind_video.py --video test8.mp4 --query "Where is my phone?"
```

**影片是既有 test8，這次由新 orchestrator 首次處理並全部重新推論；不是未見影片泛化測試，也未使用歷史 Nemotron 結果代替。** 未收到另外的新影片，因此依任務允許的整合測試方式驗證。

- 原片長 36.77 秒，1280×720，1,103 frames；來源 SHA：`932b70d6ece1c5b3149321bfd9d633d78da5c1961d88dbf1b06311b5eb9bdee4`。
- 使用原生 PTS／time_base，實際影格間隔有差異；沒有使用 frame／30 當時間。
- CV 採樣 208 張，包含各 VLM window 的原片影格。
- Nemotron：4 個不重疊時間視窗，每窗最多 8 張 distinct native-time uniform frames，本次皆 8 張。
- 定位：從「偵測到物體但沒有可信表面」與「目標缺偵測」兩群按時間選 6 張，沒有每格跑 Qwen。
- GPU 按 CV → Nemotron → Qwen → SAM 執行，各自 subprocess 結束後才進入下一階段。

| 階段 | 結果 | 實際 wall time |
|---|---|---:|
| 原片登錄、PTS 與 208 張影格抽取 | 完成 | 16.52 秒 |
| YOLO11s／ByteTrack | 208／208 張，1,654 筆觀察 | 26.56 秒 |
| Nemotron Nano 12B v2 VL NVFP4-QAD | 4／4 次 fresh video-array generation | 482.36 秒 |
| Qwen7 NF4 目標／表面定位 | 6／6 次；5 筆契約有效、1 筆無效 | 172.31 秒 |
| SAM2.1 small | 8 次 box prompt、8 mask 通過幾何條件 | 21.44 秒 |
| 全程含整合、儲存與證據輸出 | 完成 | **723.39 秒，約 12 分 3 秒** |

Nemotron 約 435.12 秒花在模型資產 hash、載入及初始化；四次 generation／處理約 35.88 秒。這不是即時系統。CV 有一次 NMS time-limit warning，不能保證每次偵測完整；漏檢不會轉成不存在證據。

## Graph 與搜尋

Session：
`artifacts/findmind_sessions/video_932b70d6ece1c5b31493_20261020T223911Z_3e1a9e/`

- 1,704 筆 observations：1,654 CV、44 Nemotron state claims、3 新定位、3 同源定位描述。
- 773 個 candidate entity records，**不是 773 個不同實體真值**；未追蹤成功的偵測會保留獨立候選。
- 163 個 frame-scoped regions，含 5 個新表面 proposals；534 筆全類別候選關係，不能當定位品質指標。
- 2 個 PICKUP 假說：1 UNCERTAIN（實例關聯／獨立狀態證據不足）、1 REJECTED（模型前後狀態矛盾）。
- **0 新授權 persistent identities、0 VERIFIED locations、0 production Graph writes。**

「Where is my phone?」回傳 **POSSIBLE_LOCATIONS，3 筆候選**：

| 原片位置 | 結果 | 解讀 |
|---|---|---|
| f414，13.803333 秒 | tabletop candidate／NEAR_REGION | 部分手機被手遮住；框能指向手機，但表面關係粗略 |
| f180，6.008333 秒 | 兩筆 tabletop candidate | CV 與新定位的同格證據；是兩筆觀察，不是兩支已確認手機 |

已直接看過 f180／f414 原片及疊圖：能看到手機，但 f180 在畫面底緣部分裁切、f414 有手遮擋，**不能憑投影確定放下／支撐或目前仍在那裡**。另看 f1020：模型框落在遠處人物手持物附近，定位粗糙且無表面，未成為桌面位置候選；未當作使用者同一支手機。

重開全新 Python process 查詢仍得到相同 3 筆候選；`torch/vllm/ultralytics/transformers` 均未載入。具名但未 enrolled 的身分查詢回 UNKNOWN／0 候選。Bottle 類別已由本次實際 YOLO 路徑產生觀察，重查回 83 筆候選關係；未人工確認這 83 筆的物理正確性。Keys／wallet 的參數入口可用，但尚未測試其真實感知效果，不宣稱已可靠支援。

## 契約與品質要分開看

Nemotron 執行 4／4 成功，但完整 strict-valid **1／4**：

- window_0001：status 與 event list 不一致。
- window_0002：完整契約有效；其 PICKUP 仍因無獨立身分／狀態證據而 UNCERTAIN。
- window_0003：重複物體描述及事件狀態引用矛盾。
- window_0004：raw JSON 不合法；外層 fence 的非權威描述依既有 adapter 政策另存。

保留原始文字、input video array hash、frame aliases、native PTS、processor shape、模型 revision／資產 hashes、generation metadata 及 schema／semantic／citation 結果。Invalid 不變成 NO_EVENT，也不會得到可信事件／位置。

Nemotron 使用原本已測試的 **官方 video array transport**，不是偷偷改成多張 image。其內部時間位置仍由 FPS 近似產生；**明文 native PTS 對照才是權威來源**，VFR 並不表示模型內部時間編碼已完全等價。Qwen／SAM 的 surface semantics 仍可能把微波爐機身當頂面；本次沒有重新研究或宣稱修好。

## 檔案入口

```text
artifacts/findmind_sessions/<session_id>/
  source_manifest.json       原片 SHA、完整 native timeline、samples、windows
  cv/                        YOLO／track observations、空授權 ledger、receipt
  vlm/                       Nemotron raw／input／validation／runtime
  localization/              選格原因、Qwen raw、座標、SAM masks
  observations.json
  event_decisions.json
  memory_graph.json          既有 TemporalMemory 格式
  search_result.json
  evidence/source/           未加標註原片 PNG
  evidence/*_annotated.jpg   候選框、區域與限制
  run_receipt.json
```

沒有重做 Graph schema。新增 `fresh_video.py`（CPU orchestration/API）、`fresh_workers.py`（重用 CV／Phase 6）、`nemotron_video.py`（參數化既有部署），加上公開單一 CLI 與內部 Linux worker。模型、提示契約、IdentityGuard、Phase 4–6 決策沿用；空身分授權 ledger 明確代表新影片尚無實例 enrollment。

單一 perception worker 失敗時會記錄階段錯誤並保留其他成功證據，建立可查詢的部分 Graph；timeout 後不繼續載入下一個 GPU 模型。原片／影格完整性錯誤仍會拒絕組裝，以免把錯誤來源寫成有效證據。程序被外部強制中止後尚未完成的 session 不保證可自動恢復；目前 query 模式只接受已保存 Graph／receipt 的 session。

## 驗證與限制

- **71／71 focused CPU tests 通過**（Phase 4–6 的 62 項＋Phase 7 的 9 項），含 VFR／不重疊 window、局部追蹤不授權身分、invalid 不代表無事件、空／失敗證據仍可保存，以及 GPU-free query／hash guard。
- 208 個 source image hashes 全數符合；3,273 個歷史保護檔與 Phase 6 的 21 份 raw 未變。
- 本次未訓練、未跑三模型比較、未讀 GT 判斷、未改歷史 benchmark、未寫 production memory、未 commit／push。
- 實跑後修補了證據輸出選格：所有 localization frames 必定有疊圖，不被全類別摘要抽樣擠掉；另補 query 的 strict-valid 診斷與預先檢查 budget。僅 CPU 重畫／查詢，未重做任何推論或 Graph；原始 run receipt 保留當時程式 hash，收尾 hash 見 `artifacts/phase7/VERIFICATION.md`。

剩餘主要工作：新影片／新場景更多實測、表面與小物體定位品質、跨視角實例身分、速度／載入成本、可恢復的長任務及最終 Agent UI。本次已達成「一支 MP4 → 真實推論 → 隔離 Graph → 保存後可查詢」的整合目標。

