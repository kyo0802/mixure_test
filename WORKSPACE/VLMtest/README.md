# VLMtest

更新：2026-10-18。最新工作：**離線人工 GT 標註工具完成**。

**[最新完整報告](LATEST_REPORT.md)** · [目前結論與下一步](LATEST_DECISIONS.md) · [回到工作區](../README.md)

## 人工標註工具

| 找什麼 | 入口 |
|---|---|
| 開始正式人工標註 | [離線工具 index.html](../../tools/findmind-gt-annotator/index.html) |
| 發給其他人的完整套件 | [下載 ZIP](../../dist/findmind-gt-annotator.zip)（完整解壓後開啟） |
| 給外部審閱者的 README | [GitHub 獨立標註分支](https://github.com/kyo0802/mixure_test/tree/codex/offline-gt-annotator)（Code → Download ZIP） |
| 審閱者操作與準則 | [瀏覽器指南](../../tools/findmind-gt-annotator/guide.html) |
| 主持人收件、衝突與裁決 | [Owner guide](../../docs/FINDMIND_GT_OWNER_GUIDE.md) |
| 本次權威報告與驗證 | [工具產物](../../artifacts/vlmtest/gt_tool) |

工具內含 test1–test9 完整原片，不需環境或伺服器。45 項自動測試通過；負責人已回報實機播放、標註、匯出再匯入成功。下一步為正式獨立人工標註及明確裁決，尚未建立全片正式 GT。

## 歷史：三模型共同資料集結果

test1–test9 三模型共同資料集推論完成。Qwen、VideoLLaMA3、Nemotron 各 184／184，合計 552 次；零視窗推論失敗、零品質重試。69 個舊窗加 145 個覆蓋窗共 214 條目，去重後 184 組八影格輸入，包含 test6。時間範圍覆蓋九片全長，實際採樣 1,411／9,958 格，並非逐格觀察。

Raw full-strict：Qwen 0／184（另外 157 份 fence-body full-valid）、VideoLLaMA3 83／184、Nemotron 108／184。這是格式／一致性數字，不是物理正確率。**目前沒有模型適合直接更新 Graph**；下一步先完成人工事件、state、身分與 coverage 審閱。

| 找什麼 | 入口 |
|---|---|
| 歷史三模型比較報告 | [原始完整報告](../../artifacts/pass_t/phase3/three_vlm_full_v1/THREE_VLM_COMPARATIVE_REPORT.md) |
| 原影片、184 張 contact sheets、完整 PNG | [舊檢視頁（不能提交標註）](../../artifacts/pass_t/phase3/three_vlm_full_v1/human_review/INDEX.html) |
| 歷史人工審閱輸入與模板 | [歷史資料夾](../../artifacts/pass_t/phase3/three_vlm_full_v1/human_review) |
| 三模型 raw、validation、receipts | [原始輸出](../../artifacts/pass_t/phase3/three_vlm_full_v1/runs) |
| 九影片時間覆蓋圖 | [直接開啟](../../artifacts/pass_t/phase3/three_vlm_full_v1/timeline_coverage.png) |
| 權威報告、凍結設定與完整性檢查 | [實驗資料夾](../../artifacts/pass_t/phase3/three_vlm_full_v1) |
| 歷史 VideoLLaMA3：16 組輸入 | [歷史實驗](../../artifacts/pass_t/phase3/videollama3_full_v1) |
| 歷史 Qwen A/B/C 消融 | [歷史實驗](../../artifacts/pass_t/phase3/observation_ablation_v1) |

底層歷史 artifacts 保留原路徑。日常閱讀與後續 VLM 測試報告使用本資料夾的固定入口。
