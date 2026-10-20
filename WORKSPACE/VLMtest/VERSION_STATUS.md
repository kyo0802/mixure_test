# FindMind 目前版本進度

更新：2026-10-20。分支：`codex/pass-i-current`。

本次版本保存 Phase 3 三模型實驗、GT 整理與 AI 視覺裁決，以及 Phase 4 recorded-output 整合。主要入口：[最新整合報告](LATEST_REPORT.md)。

## 已完成

- test1–test9 三模型各 184 次推論，共 552 次，結果與 raw 文字保留；沒有本次新推論。
- 兩位人工標註 53 筆紀錄對齊成 34 組；原片採樣影格 AI 裁決得到 15 個可見轉換（8 PICKUP、7 PLACEMENT）、13 個不確定物理轉換及 6 組其他觀察。
- 39 筆模型引用視覺複核與局部探索性比較完成；AI review 不等同人工 GT，不進 runtime 決策查表。
- Phase 4 已實作 Nemotron adapter、CV／IdentityGuard adapter、事件決策、既有 TemporalMemory 持久化與證據排序搜尋；新 raw result 可使用相同入口。
- 九片端到端 CPU 重播完成：184 份 Nemotron 回應、8,163 筆 CV 觀察；143 筆事件假說為 0 SUPPORTED、53 REJECTED、90 UNCERTAIN；九片手機搜尋皆 UNKNOWN，保留原始證據與原因。
- 本次提交前 55 個 focused CPU tests 通過：整合、GT consolidation、三模型契約、observation interface。測試紀錄：`artifacts/phase4/version_control_tests.txt`。

## 尚未具備

1. VLM 描述到 CV 實體的可靠區域／實例關聯。
2. 獨立確認 ON_SURFACE ↔ HELD_BY_PERSON 的 runtime 量測。
3. 可追溯的具名位置／spatial zone 量測。
4. 全體事件與負例完備範圍的裁決；目前不能報正式整體 precision／recall／F1。
5. 新影片自動推論服務與可信 production Memory Graph 更新；目前完成的是重用既有輸出的隔離整合。

目前仍在感知／事件與記憶整合實作階段，沒有宣稱 Shadow mode 或完整新影片找物已驗收。

## GitHub 保存內容與本機資料

提交程式、測試、設定、進度報告、三模型 raw 文字與必要結果／來源 metadata、裁決文字資料，以及正式 demo 的事件決策／搜尋結果／執行 receipt。

模型權重、環境、影格、影片、視覺比較圖與大型 demo Graph 留在本機。原始 evidence manifests 及 hash 可用於驗證，但 GitHub clone 本身不包含全部 replay 所需資產。真實資料重播需放回對應原片、影格及既有 CV／IdentityGuard 輸出；CPU real-artifact test 也需要該本機證據。安裝程式與依賴宣告不包含模型／環境本體。

工作目錄中既有大量歷史刪除及無關暫存未納入本次提交。GitHub 版本保留那些既有歷史檔案，不表示本機工作目錄已完全乾淨。

重播方式與 fresh-result bundle 格式見 [整合報告](LATEST_REPORT.md)。沒有修改 production memory。
