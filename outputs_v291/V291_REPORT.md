# V2.9.1 執行報告

## 執行範圍與凍結

- 工作目錄：`mixure_test_SAM`。沒有在兄弟目錄 `mixure_test` 寫入檔案。
- test1.mp4 / test2.mp4（對應 task1 / task2）從原始影片執行目前 pipeline；test3–test9 重用有效的凍結 V2.8/V2.9 證據，只重跑必要的 V2.9.1 階段。
- 預測在人工註記評估前已凍結；清單包含 1,567 個預測產物、9 個原始碼檔、12 個輸入雜湊。人工評估檔與本報告不在預測凍結清單內。
- V2.7、V2.8、V2.9 凍結檢查通過；本工作沒有覆寫歷史輸出。
- 凍結 UTC：`2026-09-27T16:55:05.448478+00:00`。

## task1 / task2 原始影片端到端結果

| 影片 | Pipeline | YOLO detections | Trusted SAM masks | Persistent entities | V2.9.1 events | Physical candidates | Search results |
|---|---|---:|---:|---:|---|---:|---:|
| task1 / test1.mp4 | 完成，原片重跑 | 1,125 | 50 | 75 | LOSS_EVENT 1 | 7 | 18 |
| task2 / test2.mp4 | 完成，原片重跑 | 1,511 | 76 | 94 | RECONFIRM_EVENT 3 | 29 | 27 |

### task1 評註比對

以人工檢視的 10 個可見框、class-agnostic IoU ≥ 0.30 評估：8/10 有匹配框；匹配框中 6/8 類別正確。原手機 8 個可見樣本有 6 個匹配，匹配的 6 個都標成 `cell phone`。初始 target binding 使用 local track 17，人工檢視確認它是早期原手機；track 17 在 f270/f300/f348 有框級軌跡對應，之後幾個高 IoU 偵測沒有持續的同一 local-track 指派。手機在 f420 進入 LOSS_EVENT；40 個 rediscovery 候選都維持 AMBIGUOUS，沒有錯誤合併。

籃球與垃圾桶在各自人工框上都有高 IoU 偵測，但兩者都被分成 `cup`。`cup` 標籤出現在 phone_01 記憶與搜尋候選，因此語意污染仍存在；它們沒有升格成已確認物理關係。籃球區域只保留為未確認視覺上下文，沒有 phone–basketball 放置關係獲得物理證據支持。後續 desk phone（track 70 / entity_0057）與 phone_01 保持分離；兩張椅子（track 58、60）也落在不同 fusion entities。

### task2 評註比對

以人工檢視的 22 個可見框評估：15/22 有匹配框；匹配框中 14/15 類別正確。原手機樣本有 11/17 匹配，匹配的 11 個均為 `cell phone`。初始綁定從 track 22 開始；人工註記確認 track 22 與 43 是同一支手機的短間隔片段，但本次 fusion 保留為 entity_0019 與 entity_0031，Identity Guard 沒有授權合併，66 個 rediscovery 候選皆為 AMBIGUOUS。這是目前短間隔 Re-ID 的未解缺口。

後續兩支 desk phone 的框都匹配且類別正確，track 78 / entity_0061 與 track 80 / entity_0063 維持不同實體；track 81 延續左側 handset 的 entity_0061。teddy bear 與 microwave 出現在 phone_01 搜尋上下文（teddy bear 排名最高），但全數仍是候選上下文；29 個物理候選、13 個 uncertain，沒有物理關係升格。

人工樣本是稀疏、非隨機診斷資料，不代表全影片 accuracy；完整表格與逐項數據見 `evaluation_summary.json` 及各影片的 `evaluation.json`。

## 錨點與多事件

9 支影片共有 110 個既有 persistent-anchor 參照、118 個 event-local anchors、356 個 target-anchor 共視影格。Role assignments：LANDMARK 194、OCCLUDER 90、INTERACTION_AGENT 21、UNKNOWN_LANDMARK 9、SUPPORT 4（多重角色會重複計數）。event-local anchors 保留事件範圍，沒有自動升格為全域 PersistentEntity。

- test3：30 個 event-local anchors；包含 microwave、sports ball、frisbee 等既有類別候選，偵測到 OCCLUSION → RECONFIRM → SECOND_LOSS。未見新 container/doll 身分被安全恢復。
- test4：33 個 event-local anchors，含 sports ball；偵測到 OCCLUSION、POSSIBLE_PUTDOWN、LOSS。
- test5：27 個 event-local anchors，含 dining table；偵測到 OCCLUSION、RECONFIRM、SECOND_LOSS。
- test6：12 個 event-local anchors，含 microwave；未恢復 doll 身分。
- test7：12 個 event-local anchors；有 1 個 PROVISIONAL 與 194 個 AMBIGUOUS rediscovery 候選，PROVISIONAL 沒有污染記憶。
- test8：從凍結 identity timeline 偵測到 f804 的 RECONFIRM_EVENT，沒有將 f432 的早期 loss 當成唯一事件。該窗口沒有 target-anchor 共視，空間關係仍未建立。
- test9：保留兩個 RECONFIRM_EVENT（f786、f1038）與 SECOND_LOSS（f1062），沒有硬編碼 frame。具體候選結果見下節。

## Rediscovery、VLM 與物理關係

- Rediscovery 共 629 個候選：CONFIRMED 1（test8）、PROVISIONAL 1（test7）、AMBIGUOUS 627、REJECTED 0。安全身份規則未被放寬，也沒有把未確認候選回寫到 LOST 區間。
- Observable-fact VLM 共 30 次呼叫，30 次輸出皆可解析，抽取 300 個可觀察事實，0 個 unusable；API 沒有要求 VLM 直接選物理關係。
- 物理輸出有 173 個 CANDIDATE、53 個 UNCERTAIN、0 個 PROMOTED。沒有不安全的物理升格。Search 有 158 個 candidate physical locations、41 個 anchor-context-only locations；test9 是唯一 no-context 影片。

### test9 確切阻塞點

在 93 個 post-loss 候選中，Identity Guard 全部判為 AMBIGUOUS（CONFIRMED 0、PROVISIONAL 0）。長 gap 後沒有可信 SAM/V2.6 identity confirmation，target-anchor 共視為 0，因此無法形成新的 phone_01 local graph；search context 也為 0。這是上游身份證據不足，不是 rediscovery API/runtime 失敗。

## 測試與剩餘阻塞

- V2.9.1 focused tests：22 passed。
- 全測試：293 passed、3 failed、1 skipped。3 個失敗是既有 V2.4.1/V2.5 frozen-artifact hash 測試，建立 V2.9.1 輸出前已重現；沒有修改那些歷史輸出。V2.7/V2.8/V2.9 freeze verification 通過。
- 主要剩餘問題：task1 的 cup 語意污染、task2 手機 track 22/43 短 gap 未安全合併，以及 test9 長 gap 缺乏可信身份/SAM 證據。故目前結論為部分修正完成，仍有上游身份證據缺口。

## 輸出位置

`outputs_v291/`；主報告為 `V291_REPORT.md`，凍結後評估為 `evaluation_summary.json`。test9 rediscovery 時間線為 `test9/rediscovery_timeline.json` 與 `test9/rediscovery_timeline.png`。

V291_PARTIAL_FIXES_WITH_REMAINING_UPSTREAM_GAPS
