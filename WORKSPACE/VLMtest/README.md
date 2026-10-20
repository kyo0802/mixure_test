# VLMtest

更新：2026-10-20。最新工作：**Phase 4 Nemotron → 既有 Memory Graph → Object Search recorded integration 完成**。

**[最新完整報告](LATEST_REPORT.md)** · [目前結論與下一步](LATEST_DECISIONS.md) · [回到工作區](../README.md)

## Phase 4：目前入口

- [目前版本進度與 GitHub 保存範圍](VERSION_STATUS.md)

- **[最新中文整合報告](LATEST_REPORT.md)**：實作、限制、架構與重播指令。
- [九片端到端 Demo 摘要](../../artifacts/phase4/demo/DEMO.md)
- [真實執行與來源 hash](../../artifacts/phase4/demo/run_receipt.json)
- [test1 Graph](../../artifacts/phase4/demo/test1/memory_graph.json) · [事件決策](../../artifacts/phase4/demo/test1/event_decisions.json) · [手機搜尋](../../artifacts/phase4/demo/test1/search_result.json)
- [22 項 CPU 測試](../../artifacts/phase4/cpu_tests.txt)

184 份既有 Nemotron 回應、8,163 筆 CV 觀察已接入隔離 Graph。143 筆假說：0 SUPPORTED、53 REJECTED、90 UNCERTAIN。九片搜尋皆 UNKNOWN：尚缺可授權的 VLM-to-CV 實例關聯、獨立 physical-state 與具名 location 量測。沒有用 AI review verdict 當 runtime GT，沒有新推論或 production Graph 寫入。

## 歷史：原片 AI 裁決與局部模型比較

不需要填 CSV。依 owner 委託檢視原片採樣序列，保留 15 個可見轉換（8 拿起、7 放下），13 組物理事件不確定，另 6 組接觸／鏡頭移動／遮擋描述。原始人工標註不變，AI 裁決獨立存放，不冒充人工 GT。

- [中文逐組裁決與模型比較](../../artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/AI_VISUAL_ADJUDICATION_REPORT.md)：點選證據連結即可查看原片影格。
- [39 筆模型引用前後畫面複核](../../artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/MODEL_CITATION_REVIEW.md)
- [AI 正事件參考 JSON](../../artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/final_gt.json)
- [完整裁決與原始 event ID](../../artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/adjudication_decisions.json)
- [最後驗證與檔案清單](../../artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/final_review_receipt.json)

既有 552 次推論全部沿用。正事件子集去重後，引用支持：Qwen 1、VideoLLaMA3 0、Nemotron 9；strict-valid 支持：0、0、7。這不是正式 precision／recall／F1；沒有充分完備負例範圍，其餘 128 筆候選尚未視覺裁決。2,235 個保留檔案驗證通過，21 項 CPU 測試通過。

## 歷史：原始 owner CSV 工作流程

53 筆原始紀錄已對齊成 34 組；552 筆模型輸出 hash 已核對，21 項 CPU 測試通過。兩人全片皆 NOT_ATTESTED，尚無自動負例資格。

- **[主裁決 CSV：34 組](../../artifacts/vlmtest/gt_consolidation_v1/adjudication.csv)**
- **[局部 coverage 裁決：41 段](../../artifacts/vlmtest/gt_consolidation_v1/coverage_adjudication.csv)**
- [逐欄填寫說明與兩條後續指令](../../artifacts/vlmtest/gt_consolidation_v1/EDITING_GUIDE.md)
- [只讀兩人對齊](../../artifacts/vlmtest/gt_consolidation_v1/gt_alignment.csv)
- [既有模型假說獨立審閱表](../../artifacts/vlmtest/gt_consolidation_v1/prediction_review.csv)（人工 GT 裁決後才看；可只審欲評分區間）
- [格式統計與評估限制](../../artifacts/vlmtest/gt_consolidation_v1/evaluation_readiness/THREE_VLM_COMPARATIVE_REPORT.md)

以上為原先人工工作表，原件保留未覆寫；目前入口以最新中文報告為準。身分、時間、去重或 coverage 尚未審定的模型假說保留未評分。

## 既有人工標註工具

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
