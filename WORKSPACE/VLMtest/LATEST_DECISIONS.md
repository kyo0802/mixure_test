# VLMtest — 目前結論與下一步

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
