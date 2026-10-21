# VLMtest — 目前結論與下一步

更新：2026-10-21。**Phase 9.1 互動 Memory Graph 與 Nemotron 驗證快取完成。**

- 選擇 optimized cold start，維持既有單影片／多視窗 model reuse；16 GiB GPU 採順序模型 ownership，不新增常駐服務。
- 22 個模型資產採 pinned SHA manifest。Full verification 63.723 s；metadata cache 0.324 s。嚴格／force 模式保留，cache 不是 fresh crypto 等價替代。
- 原 435 s aggregate 仍不能全歸因為 hashing；新 instrumentation 接入，但 optimized GPU cold／warm 與整體新影片耗時未量測。
- Graph 是已保存紀錄的唯讀投影；可選取節點／關係、看精確來源影格、依時間與狀態篩選，支援搜尋與出門找物交接。
- test8 仍為三筆位置候選、兩組時間／區域證據、0 VERIFIED；keys 無證據就空圖，session 切換清除舊 selection。
- 149 tests 與實際瀏覽器流程通過。17 份歷史 session 檔案 SHA 保留；新增一份獨立展示檢查並確認後撤銷。程式／報告納入 Phase 9.1 版本，個人狀態不發佈；[版本保存範圍](VERSION_STATUS.md)。
- [最新報告](LATEST_REPORT.md) · [開啟 FindMind](http://127.0.0.1:8514/)。

## 歷史：Phase 9 結論

Phase 9 離開提醒＋Object Search 已整合完成。

- 首頁／離開檢查／找物同一應用，必帶設定與檢查快照保存於獨立 JSON。
- 只有明確確認／撤銷按鈕改打包狀態；影像、PICKUP 假說或漏偵測不會自動判定已帶妥／忘帶。
- 101 tests 通過；真實瀏覽器完整流程、重設、歷史與服務重啟驗證完成，未重跑 GPU。
- 目前保留一份完成的展示紀錄及一份新的三件未確認檢查。展示確認不作實際攜帶證明；Graph 仍 0 VERIFIED。
- [最新報告](LATEST_REPORT.md) · [展示指南](../../artifacts/phase9/DEMO_GUIDE.md) · [開啟應用](http://127.0.0.1:8514/) · [版本保存範圍](VERSION_STATUS.md)。本機個人清單與完整推論 session 不納入 GitHub。下方為各階段當時的歷史結論。

## 歷史：Phase 8 結論

更新：2026-10-21。**Phase 8 本機互動 Demo 已完成並開啟 8514。**

- 錄製記憶可立即中英文搜尋、看同格證據與時間線；新影片可透過明確提交啟動原 Phase 7 背景工作。
- 15 Demo tests＋71 prior tests 通過；實際瀏覽器驗證完成。未重新推論；候選與可信狀態未放寬。
- 現有 test8 仍是 2 組時間／區域證據、0 VERIFIED；不能聲稱可靠追蹤使用者特定物品或目前位置。
- [最新報告](LATEST_REPORT.md) · [開啟 Demo](http://127.0.0.1:8514/) · [使用說明](../../artifacts/phase8/README.md)。未 commit／push。

## 歷史：Phase 7 結論

更新：2026-10-21。**Phase 7 新影片端到端已可執行與保存後查詢。**

- 單一入口 `scripts/run_findmind_video.py`：new MP4 → native PTS → fresh CV／Nemotron／target-surface → isolated Graph → query。
- test8 fresh inference 723.39 秒，3 筆 phone candidates，0 VERIFIED；模型執行全完成，Nemotron strict-valid 1／4。
- 71 focused CPU tests；獨立新 process 查詢不載 torch／vLLM／Ultralytics／Transformers。
- 現在可帶新影片試用，仍須明示候選與目前位置未知。優先改善載入時間、表面／小物體定位及身分；未做 Agent UI 或 production memory。
- [最新報告](LATEST_REPORT.md) · [使用方式](../../artifacts/phase7/README.md)。本機變更未 commit／push。

## 歷史：Phase 6 結論

更新：2026-10-21。**Phase 6 感知與候選搜尋整合完成；產品可信位置尚未達成。**

- 21 張最終真實影格、19 筆契約有效；6 張 CV 漏框獲合理手機定位，2 張定位偏移，3 張仍漏掉。
- test5／test8 有實際桌面查詢改善；微波爐頂面仍常含機身。更多候選不等於更準確。
- 62 CPU tests，18 個保存查詢重載一致，歷史受保護檔案不變。
- 下一步優先處理可靠頂面、小物體定位與接觸證據；身分與目前位置仍不可由類別或投影代替。
- [最新完整報告](LATEST_REPORT.md) · [正式 Phase 6 報告](../../artifacts/phase6/PHASE6_REPORT.md)。未 commit／push。

## 歷史：Phase 5 結論

更新：2026-10-20。**PHASE5_CANDIDATE_SPATIAL_MEMORY_IMPLEMENTED**。

- [最新報告](LATEST_REPORT.md)：Scene Spatial Registry、逐影格幾何、VLM-to-CV 候選、位置歷史、既有 Graph 搜尋與九片實跑完成。
- 6／9 片有候選位置、3 片 UNKNOWN；1,043 區域觀察、88 手機候選位置、17 筆有既有 CV 身分授權的候選；VERIFIED 位置仍為 0。
- 目前是可查詢的候選空間記憶，尚不是可靠的目前位置或目標 smartphone 身分判定。
- 44 CPU tests 通過，九片 Graph 重載／查詢一致；Phase 4 事件仍 0／53／90。
- 優先補：同格 surface／小物體定位、實例分辨、獨立接觸證據、跨視角區域對應。
- 只寫 Phase 5 隔離 Graph；沒有新推論、GT 查表、production writes 或本次 commit／push。

## 歷史：Phase 4 結論

更新：2026-10-20。**PHASE4_RECORDED_INTEGRATION_COMPLETE**。

- [最新報告](LATEST_REPORT.md)：已實作 adapter、獨立證據 decision、既有 TemporalMemory 持久化與證據排序搜尋。
- 九片、184 回應、8,163 CV 觀察；143 假說為 0 SUPPORTED／53 REJECTED／90 UNCERTAIN。110 筆 CV 觀察保留經核對的歷史身分關聯，不傳遞給未綁定 VLM 類別。
- 九片手機搜尋 UNKNOWN，沒有支援具名位置；缺口是 runtime 實例 grounding、獨立 physical-state 及 spatial-zone 量測。程式可接新 raw result，不依賴歷史 window ID。
- 22 CPU tests 通過；九片 Graph 重新載入搜尋一致；1,643 執行輸入及 2,235 歷史保護檔案 hash 驗證通過。
- 只寫 `artifacts/phase4/` 隔離 Graph；無新推論、無 GT／review 查表、無 production memory 更新、無 commit／push。

## 歷史：AI 原片裁決

- [歷史中文裁決](../../artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/AI_VISUAL_ADJUDICATION_REPORT.md)包含 34 組原片裁決與證據連結。15 個可見轉換（8 拿起、7 放下）、13 個不確定物理轉換、6 組其他觀察。
- 額外查看 39 筆模型引用：13 支持、16 不支持、10 不確定。去重正事件支持數 Qwen 1、VideoLLaMA3 0、Nemotron 9；strict-valid 支持數 0、0、7。
- 這是 AI 視覺複核，原始人工 JSON／CSV 不變，不冒充 HUMAN_REVIEWED；沒有完整負例資格，正式 precision／recall／F1 不可報告。其餘 128 筆候選未視覺裁決。
- 既有 552 次推論沿用；2,235 個保留檔案 SHA 驗證通過，21 項 CPU 測試通過。未 commit／push，未更新 Graph。

## 歷史：2026-10-19 原始人工裁決工作表

- huang 19 筆、KUO 34 筆原始紀錄已驗證，對齊成 34 組（19 雙人候選／15 單人紀錄）。原始 33 筆 state 作為證據保留。
- [填主裁決表](../../artifacts/vlmtest/gt_consolidation_v1/adjudication.csv)與[局部 coverage](../../artifacts/vlmtest/gt_consolidation_v1/coverage_adjudication.csv)；[操作說明](../../artifacts/vlmtest/gt_consolidation_v1/EDITING_GUIDE.md)。優先 G003/G004、G022/G023、G024/G025。
- 兩位九片全為 NOT_ATTESTED，不能自動當完整負例。局部 scopes 可獨立核准；未解事件與遮擋不當成無事件。
- 552 次原始生成沿用；raw full-strict Qwen 0、VideoLLaMA3 83、Nemotron 108／184。167 筆假說不能憑名稱或重疊時間自動完成實物關聯及去重。
- 21 項 CPU 測試通過。等待實際人工決策；之後直接執行 final GT 及評估指令。未跑模型、未寫 Graph、未 commit／push。

## 歷史：離線工具交付

更新：2026-10-18。**OFFLINE_GT_ANNOTATION_TOOL_READY**。

- [離線標註工具](../../tools/findmind-gt-annotator/index.html)與[獨立 ZIP](../../dist/findmind-gt-annotator.zip)已完成，內含九支原片；審閱者不需安裝環境。使用者已回報播放、標註與匯出再匯入成功。
- 45 項自動測試通過；實機回報與 DOM doubles 分開記錄。HTML5 PTS 導航不宣稱 frame-accurate；完整人工驗收表仍可由各審閱者核對。
- **下一步：建立正式獨立 session 完成人工事件、state、身分與 coverage 標註，匯出 JSON，經主持人收件及明確裁決。** 測試提交不得混入 GT。未完整覆蓋不能當負例，爭議不自動投票。
- 未執行新模型推論、未計正式模型正確率、未寫 Graph。工具實作階段未 commit／push；後續依使用者明確要求提供開發分支推送及獨立標註分支，README 內含審閱者下載與交件步驟。

[最新工具報告](LATEST_REPORT.md) · [主持人收件說明](../../docs/FINDMIND_GT_OWNER_GUIDE.md)

## 歷史：test1–test9 三模型共同資料集評估

更新：2026-10-18；推論與完整性彙整於 2026-10-17 完成，本次接續完成發布入口。**THREE_VLM_FULL_DATASET_INFERENCE_COMPLETE**。

- 九支原片全部納入，包含 test6；69 個舊窗的 52 個缺少設定已補齊。新增 145 個時間覆蓋窗，214 條目去重為 184 個唯一輸入，三模型各生成一次，共 552 次；零視窗執行失敗、零品質重試。完整時間配置覆蓋不等於逐格觀看。
- Qwen raw JSON 0／184、raw full-strict 0／184；157 份獨立 fence-body full-valid。VideoLLaMA3 raw JSON 147／184、full-strict 83／184。Nemotron raw JSON 166／184、full-strict 108／184；17 份達 token cap。無效輸出保留原文，不改成無事件、不進 authoritative matching。
- Nemotron 官方 NVFP4-QAD 已在 RTX 5070 Ti 16GB／WSL2 實際跑完 184 組八影格 video array；兩次啟動錯誤在生成前修復，紀錄保留。Qwen／VideoLLaMA 為八張 chronological images；共同來源相同，內部表示不同，因此是部署設定比較。
- 既有 test5/test7 PICKUP 只作個案描述。Nemotron 兩窗都有手機假說，但 after 引用仍有遮擋／過早問題；Qwen 兩窗未提手機事件，VideoLLaMA 的 test7 假說 semantic-invalid。不能用事件數、alias 存在或 schema 有效推定物理正確。
- **決策：No model yet suitable for direct graph updates。** 不選整體勝者、不啟動 hybrid、不更新 Graph。舊 GT 不足以支持這個通用物件任務的全片正式 precision／recall／F1／state accuracy；不可估計者保留 null，不把未審閱當負例。
- **唯一建議下一步：完成同一資料集的事件、state、身分與 coverage 人工審閱，再用現有輸出重算 eligible metrics。** 人工套件未預填模型答案為 GT；目前未啟動新推論、訓練或整合階段。

[歷史完整報告](../../artifacts/pass_t/phase3/three_vlm_full_v1/THREE_VLM_COMPARATIVE_REPORT.md)；[舊 contact sheet 檢視頁（不是標註工具）](../../artifacts/pass_t/phase3/three_vlm_full_v1/human_review/INDEX.html)；[全部原始輸出](../../artifacts/pass_t/phase3/three_vlm_full_v1/runs)；[保存與輸入驗證](../../artifacts/pass_t/phase3/three_vlm_full_v1/verification.json)。沒有 commit／push。
