# V2.9 — 放置證據復原與物理關係驗證報告

## 結論

**V2.9 尚未把任何真實放置片段轉成可確認的物理記憶。** 它完成了歷史 SAM2.1 mask 接線、自動事件視窗、短視窗密集重檢、限定候選的本機 VLM 呼叫與關係 gate；但 14 個物理候選中沒有一個通過全部證據門檻。最終為 **0 PROMOTED、5 CANDIDATE、9 UNCERTAIN、0 REJECTED**。這是證據不足的結果，沒有降低身分或物理門檻來取得提升。

預測先寫入 `outputs_v29/`，於 **2026-09-27 14:57:35 UTC** 建立 `prediction_manifest.json`，並在讀取敘事評估前驗證程式、263 個預測檔、影片／模型與 V2.8 manifest 雜湊。此後只新增本報告與 `evaluation_summary.json`。`outputs_v27/`、`outputs_v28/` 與 V2.6/V2.6.2 歷史資料沒有改寫；`mixure_test` 沒有改動。V2.7、V2.8 與新增 V2.9 測試共 **102 項通過**。

## 執行與量化結果

| 影片 | 可信歷史 mask | 自動事件峰值 | 密集影格／獲授權新影格 | 非人物錨點同現影格 | VLM 呼叫 | CANDIDATE／UNCERTAIN | 搜尋項目 V2.8→V2.9 |
|---|---:|---:|---:|---:|---:|---:|---:|
| test3 | 45 | f492 | 46／24 | 11 | 2 | 1／3 | 6→7 |
| test4 | 42 | f462 | 46／28 | 0 | 0 | 0／1 | 3→3 |
| test5 | 58 | f438 | 46／24 | 17 | 3 | 4／3 | 8→12 |
| test6 | 36 | f414 | 46／23 | 0 | 0 | 0／0 | 6→6 |
| test7 | 38 | f432 | 46／23 | 0 | 0 | 0／0 | 10→10 |
| test8 | 39 | f432 | 46／25 | 0 | 0 | 0／1 | 3→3 |
| test9 | 12 | f600 | 46／35 | 0 | 0 | 0／1 | 0→0 |
| **合計** | **270** | **7 個視窗** | **322／182** | **28** | **5** | **5／9** | **36→41** |

「獲授權新影格」是原本每 6 影格抽樣以外、由短視窗 SAM2.1 連續遮罩與短距離身分 gate 接受的影格。密集重檢只處理七個約 3 秒的事件視窗，沒有整片重跑；YOLO 與 SAM2.1 視窗推論合計約 92.6 秒，本機 VLM 生成約 18.3 秒。28 個非人物同現影格僅在 test3/test5，且錨點分別是椅子、椅子／筆電，**不是**敘事中的箱子。因此數量上有影格增益，不等於最終放置證據增益。

## 18 項問題的直接回答

1. **可信 SAM2.1 mask 有到物理層嗎？** 有。七片共 326 筆歷史 RLE，V2.6 融合接受 322 筆；V2.9 另以同影格身分狀態、drift 與長間隔連續性把 270 筆授權為 `phone_01` 的形狀／可見度證據。mask 本身沒有授權身分。
2. **原本有 mask 還是必須新傳播？** 原本的 `sam_continuity_log.json` 已有 RLE，V2.6 registry 的 SAM observation 也有 `mask_ref`，但標示 `trusted=false`，V2.8 因而看不到可信 mask。歷史影格不用重跑 SAM；本次只為七個事件視窗做新的密集 SAM2.1 傳播。test9 的長 LOST 後 mask 即使曾被舊融合接受，也因沒有重新授權而隔離。
3. **自動找到多少視窗？** 七片各一個，合計七個；峰值見上表。偵測規則只看可信目標遺失及另一項動作／距離／遮擋線索，沒有使用敘事指定影格。
4. **視窗是否對準重要轉折？** 部分對準手機消失，卻沒有充分對準「最後放置」。test8 選 f432 的早期遺失，沒有涵蓋後續 f804 `CONFIRMED_MATCH`；test3/test5 選到箱子附近的動作，但箱子沒有成為已知錨點。
5. **密集檢查多找回多少目標證據？** 322 個新檢查影格中有 182 個獲授權目標遮罩影格，全部落在原 6 影格抽樣格點之外。其餘 SAM/YOLO 電話觀測保留為候選或未授權，不直接更新 `phone_01`。
6. **錨點同現增加多少？** test3 新有 11 個椅子同現影格、test5 新有 17 個椅子／筆電同現影格；其他影片沒有可信目標與已知非人物錨點的密集同現。不能把所有 3,504 個 YOLO 非電話框當作有用的物理錨點。
7. **哪些候選送 VLM？** 五組「事件＋錨點」：test3 椅子與人物；test5 椅子、筆電與人物。這五次呼叫覆蓋 8 個 eligible 關係候選，使用同視窗的 BEFORE／DURING／AFTER 裁切圖；其他候選沒有滿足身分、錨點、時間證據門檻。
8. **VLM 增加有用證據嗎？** 沒有。五次中四次可解析、一筆 JSON 解析失敗；可解析結果幾乎一律選 `BEHIND`，連人物錨點也如此，理由多是影格標籤或直接寫 `UNCERTAIN`。gate 將其判定為缺少具體獨立理由，**0 次**作為 promotion 支持。
9. **哪些關係 PROMOTED？** 沒有。
10. **哪些關係仍是 CANDIDATE？** test3：`phone_01 CANDIDATE_NEAR 椅子`。test5：`CANDIDATE_NEAR 椅子`、`CANDIDATE_NEAR 筆電`、`CANDIDATE_OCCLUDED_BY 筆電`、`CANDIDATE_BEHIND 筆電`。它們在記憶與搜尋圖仍明示未確認。
11. **哪些被 REJECTED？** 物理候選為 0；不夠證據者維持 `UNCERTAIN`，未把未知當成硬反證。mask 層有 56 筆未授權，包括 fusion 衝突、drift 或長 LOST 後缺少重新授權。
12. **為何無法提升？** test3/test5 的真實箱子沒有可靠 persistent anchor；其他視窗欠缺非人物錨點的可信同現；VLM 回答缺乏可核查的時間／形狀理由。靜態 2D 近距離、偵測漏失或單獨 mask 包含都不足以證明 ON／INSIDE／BEHIND。
13. **任何真實影片產生可確認的 ON／INSIDE／BEHIND／OCCLUDED_BY／HELD_BY 嗎？** 沒有。
14. **有明顯假提升嗎？** 沒有，因為 0 個提升。但 test5 的「筆電後方」候選與敘事箱子目標不一致，仍可能把搜尋注意力帶往錯誤錨點；它保留未確認標記。
15. **test9 空 graph 有改善嗎？** 沒有。雖然短視窗新增 35 個獲授權影格，但只有人物同現，沒有可供搜尋的 HomePad／瓶子／籃球錨點；搜尋項目仍 0。
16. **test9 第一個失敗點？** 最後可信歷史 mask 為 **f624**；密集視窗在 **f627** 首次同時沒有 YOLO 電話框與 SAM2.1 電話 mask，分類為 `DETECTION_FAILURE`。f606 曾有暫時融合衝突，f618 的原始 YOLO 又使身份重新授權；f627 是最後可信觀測後的第一個持續斷點。後段長 LOST 後的舊 SAM mask 不再自動沿用 `phone_01`。
17. **搜尋是否優於 V2.8？** 候選數 36→41，且 V2.8 排序規則原封不動。新增項都未確認，沒有提升的放置關係；test3 首位成為椅子 NEAR，test5 前列出現筆電 BEHIND。**不能宣稱實際找回能力提升**，test9 仍空。
18. **目前最大瓶頸？** 已從「沒有 mask 接線」轉成「最後互動時缺乏可信、語義正確的目標–錨點連續同現」。箱子等物件未被穩定綁定，test8 後期重新確認不觸發視窗，test9 則在重要後續錨點之前失去電話偵測／SAM 連續性；本機 VLM 的理由品質也不足以補救。

## 逐片定性複查

- **test3：** 箱子在視覺上可見，YOLO／registry 未把它綁成放置錨點；候選只到椅子，沒有容器進入證據。
- **test4：** 籃球遮擋／後方序列未形成可信籃球錨點；附近偵測曾標為 `frisbee`，只有薄弱人物互動候選。
- **test5：** 箱子放置仍不明確。密集影格有椅子／筆電同現，卻不能替代箱子關係；`BEHIND`／`OCCLUDED_BY` 筆電只保留為候選。
- **test6：** 事件視窗有手機 mask，沒有與獲授權手機同現的已知非人物錨點，微波爐／娃娃放置證據未補齊。
- **test7：** 娃娃沒有成為該視窗的已知錨點；provisional 電話沒有污染 `phone_01`。
- **test8：** f804 的既有 `CONFIRMED_MATCH` 沒被改寫；本次早期 f432 視窗無法產生後段新上下文，多電話候選也沒有強制合併。
- **test9：** f627 同時失去密集 YOLO／SAM 電話證據；後續長間隔遮罩被隔離，HomePad／瓶子／籃球都沒有與已授權手機同現。`test9_failure_timeline.json` 與 PNG 列出逐影格鏈條。

## 產物與限制

主要可檢查檔案：`mask_evidence_audit.json`、各片 `mask_evidence.json`、`placement_event_candidates.json`、`dense_windows/PE0001/`、`physical_relation_candidates.json`、`vlm_relation_verification.json`、`physical_relation_decisions.json`、更新的 memory／search JSON、圖表與 `prediction_manifest.json`。每個視窗有 BEFORE／DURING／AFTER contact sheet；每片有 physical relation explainer 與 V2.8 風格的 temporal／lifetime／local／search graph。

本實驗不聲稱完整模型準確率，也沒有再訓練偵測器、SAM、Re-ID 或改動 Identity Guard／V2.8 決策規則。**V2.9 到此停止。**
