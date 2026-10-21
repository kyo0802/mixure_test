# VLMtest

更新：2026-10-21。最新工作：**Phase 9.1 互動記憶圖譜＋Nemotron verification cache**。CPU 與瀏覽器驗收完成；GPU 啟動與整支影片加速仍待量測。

**[最新完整報告](LATEST_REPORT.md)** · [目前結論與下一步](LATEST_DECISIONS.md) · [回到工作區](../README.md)

## Phase 9.1：目前入口

- [完整實作／量測報告](../../artifacts/phase9_1/PHASE9_1_REPORT.md) · [圖譜畫面](../../artifacts/phase9_1/MEMORY_GRAPH.png) · [精確影格證據](../../artifacts/phase9_1/GRAPH_EVIDENCE.png)
- [開啟 FindMind](http://127.0.0.1:8514/) → 選取記憶 → Memory Graph。也可從找物結果按「在記憶圖譜中查看」。
- 實際 WSL CPU 驗證：full SHA 63.723 s → cached metadata 0.324 s；不是整支影片加速或 warm inference 數字。
- 149 tests 通過。兩支 session 的 17 份歷史 Graph／來源／raw SHA 不變；只有新增的展示檢查留下 confirm／undo 記錄。[版本保存範圍](VERSION_STATUS.md) · [Phase 9.1 發佈說明](../../artifacts/phase9_1/README.md)。

## 歷史：Phase 9

- **[開啟 FindMind](http://127.0.0.1:8514/)** · [啟動與兩分鐘展示指南](../../artifacts/phase9/DEMO_GUIDE.md)
- [正式中文報告](../../artifacts/phase9/PHASE9_REPORT.md) · [找物交接畫面](../../artifacts/phase9/SEARCH_HANDOFF.png) · [檢查完成畫面](../../artifacts/phase9/DEPARTURE_COMPLETE.png)
- [15 項離開提醒測試](../../artifacts/phase9/departure_tests.log) · [15 項 Demo 回歸](../../artifacts/phase9/phase8_regression.log) · [71 項原有測試](../../artifacts/phase9/phase4_to_7_tests.log)

可從首頁啟動離開檢查，直接找手機、看證據、返回逐件確認、完成並開始新檢查。手動確認與影像記憶分開；瀏覽器驗收紀錄有展示標籤。101 tests 通過；0 VERIFIED 位置。[版本保存範圍](VERSION_STATUS.md) · [專案啟動與環境說明](../../README.md)。本機展示紀錄與完整 session 不上傳，其他電腦需另備環境與資料。下方歷史進度保留各階段當時的狀態。

## 歷史：Phase 8

- **[開啟本機 FindMind](http://127.0.0.1:8514/)** · [操作與啟動命令](../../artifacts/phase8/README.md)
- [正式中文報告](../../artifacts/phase8/PHASE8_REPORT.md) · [實際瀏覽器畫面](../../artifacts/phase8/FINDMIND_DEMO.png)
- [15 項 Demo 測試](../../artifacts/phase8/demo_tests.log) · [71 項 Phase 4–7 測試](../../artifacts/phase8/phase4_to_7_tests.log)

錄製結果搜尋不載 GPU 模型；真實 test8 的 3 筆底層手機紀錄顯示為 2 組時間／區域證據，保留候選與未知。新影片 UI 使用原 Phase 7 CLI，本次以工作 mocks 驗證提交與去重，未重跑 GPU。0 VERIFIED；未 commit／push。

## 歷史：Phase 7

- [操作說明：一個指令處理新影片、重查既有 session](../../artifacts/phase7/README.md)
- [正式中文報告](../../artifacts/phase7/PHASE7_REPORT.md) · [71 項測試及 hashes](../../artifacts/phase7/VERIFICATION.md)
- [test8 實際 session 搜尋結果](../../artifacts/findmind_sessions/video_932b70d6ece1c5b31493_20261020T223911Z_3e1a9e/search_result.json) · [手機候選畫面](../../artifacts/findmind_sessions/video_932b70d6ece1c5b31493_20261020T223911Z_3e1a9e/evidence/f00000414_annotated.jpg)

實際 CV 208 張、Nemotron 4 次、Qwen 6 次、SAM 8 prompts，全程約 12 分鐘。3 筆手機位置候選、0 VERIFIED；Nemotron strict 1／4，不等於事件已確認。用既有 test8 新推論做整合驗證，不宣稱未見資料泛化。未 commit／push。

## 歷史：Phase 6

- [正式中文報告](../../artifacts/phase6/PHASE6_REPORT.md) · [逐格視覺複核](../../artifacts/phase6/VISUAL_REVIEW.md)
- [最終執行紀錄](../../artifacts/phase6/pixel_demo/run_receipt.json) · [收尾 hashes／查詢修補](../../artifacts/phase6/CLOSEOUT_VERIFICATION.md)
- [test5 證據](../../artifacts/phase6/pixel_demo/test5/evidence_sheet.jpg) · [test8 同格比較](../../artifacts/phase6/pixel_demo/test8/f000300_comparison.jpg) · [test9 失敗限制](../../artifacts/phase6/pixel_demo/test9/evidence_sheet.jpg)
- [62 項 CPU 測試](../../artifacts/phase6/CPU_TEST_RESULTS.md)

21 張最終影格、19 筆輸出契約有效，6 張漏框確實補回。共 42 次針對性感知呼叫（含 21 次座標診斷）。所有新定位皆未獲 persistent identity，VERIFIED 位置仍 0。未 commit／push。

## 歷史：Phase 5

- [最新中文報告與使用指令](LATEST_REPORT.md)
- [正式九片執行結果與 hashes](../../artifacts/phase5/demo/run_receipt.json)
- [test2 手機位置查詢](../../artifacts/phase5/demo/test2/search_result.json) · [原片證據](../../artifacts/phase5/demo/test2/evidence_03.jpg)
- [44 項 CPU 測試](../../artifacts/phase5/CPU_TEST_RESULTS.md)

6／9 影片回傳 POSSIBLE_LOCATIONS，test5／8／9 為 UNKNOWN；88 筆手機候選位置觀察，0 VERIFIED。位置可查詢、可追溯，但不能宣稱目標手機確實仍在候選區域。沒有新模型推論；本次尚未 commit／push。

## 歷史：Phase 4

- [目前版本進度與 GitHub 保存範圍](VERSION_STATUS.md)

- **[Phase 4 中文整合報告](../../artifacts/phase4/PHASE4_INTEGRATION_REPORT.md)**：實作、限制、架構與重播指令。
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
