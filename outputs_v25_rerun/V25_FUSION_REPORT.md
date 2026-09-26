# V2.5 全影片重新推論報告

日期：2026-09-25。範圍：目前 `test3.mp4`–`test9.mp4` 七支影片。所有新程式與產物位於 `mixure_test_SAM`，本次未修改 `mixure_test`。本報告取代舊版 `outputs_v25/V25_FUSION_REPORT.md` 的七片成果數字。

## 1. Research Question

重新從七支目前影片產生偵測與追蹤後，V2.5 的通用目標綁定、持續候選接納與凍結 Re-ID 能否維持正確實體身分，尤其是更新後的 test5？

## 2. Why V2.4.1 Failed to Generalize

舊版以固定後期影格與候選窗評估，會漏掉真正目標的後續偵測。前次 V2.5 更混用了更新後 test5 影片與更新前偵測快取。這次每支影片都從目前位元組重新產生 V2.1 偵測、追蹤與實體輸入，並逐片驗證影片 SHA-256。

## 3. Removed Task-Specific Assumptions

V2.5 推論沿用無特定 test3–test9 track ID、後期固定影格的通用程式。原版 `outputs_v25` 保留不動；本次用獨立的 `v25rerun` 複本與 `outputs_v25_rerun`，避免改寫已鎖定預測。唯一重跑期程式修正是 SAM 遮罩在候選 YOLO 裁切框內前景不足 32 像素時，記錄其不可作遮罩裁切並改用原 YOLO 框；模型與 Re-ID 門檻未變。

## 4. Generalized Target Binding

七片均完成自動綁定。人工抽樣複核為 7/7 對應目標；test5 綁定由舊混合輸入的 track 13／f12，改成新鮮偵測的 track 21／f96。新版影片中帶標籤的手持目標在 f96、f192、f288、f366 保持相同實體關聯。這是抽樣可見身分判讀，並非最終位置證明。

## 5. Continuous Candidate Admission

七片共 174 個候選假說（前次混合輸入為 178）。六個經人工確認、處於目標未觀測期且有 YOLO 目標框的後期樣本，六個都進入候選串流（6/6）；其中兩個在首次 MATCH 停止前被 Re-ID 評估。test5 的目標在 f96–f366 屬已關聯的可信觀察，不納入後期候選分母。

## 6. Multi-frame Candidate Hypotheses

候選保留多幀觀察、局部追蹤來源、最多四個外觀視角、SAM 支援、Re-ID 歷史與同幀共存記錄。test5 候選數由舊輸入的 22 降至新輸入的 18；後段人工檢視的候選多為桌面上的座機。候選仍有碎片化，174 不等於 174 個物理手機。

## 7. YOLO/SAM Evidence Routing

所有影片均重新跑 V2.1 YOLO 偵測／追蹤，使用 `--events-only` 產生 V2.5 所需的偵測、追蹤與實體檔；未執行與 V2.5 身分流程無關的 VLM 事件敘述。每片再執行完整剩餘影格的 SAM 2.1 目標傳播與候選短段支援。V2.3 可信遮罩 guard 保留。

## 8. Persistent Entity Fusion

`phone_01` 在短暫失去 YOLO 觀察時保留身分。新候選不因同一 YOLO track ID 就直接視作同一物理實體；只有凍結 Re-ID 給 MATCH 才寫入別名並觸發同身分 SAM。test7 顯示此 gate 仍可能錯誤合併座機。

## 9. Frozen Re-ID Integration

MobileNetV3 權重、裁切前處理、相似度 0.60、競爭 margin 0.10、原 `decide` 函式與信任條件均保留。改動只處理新增影片暴露的無效遮罩裁切，以無遮罩的同一 YOLO 候選框完成特徵擷取。七片預測在人工複核前鎖定；架構 SHA-256 `e23c0725bda9341d46a3e17b5c4c81420c24e11b98a13cdb7ff3fd91e0d5fa30`，預測 manifest SHA-256 `1575b31d58a9742a6d7062dfb021c718b9655dc9532be4cbd2f300265c5215c6`。manifest 同時保存七支目前影片、各自新 V2.1 輸入與 V2.5 預測雜湊。

## 10. Per-video Results

| 影片 | 目標綁定 track／幀 | 候選數 | Re-ID | 人工複核重點 |
|---|---|---:|---|---|
| test3 | 39／228 | 23 | NO_SAFE_MATCH | 最終箱內位置無法直接目視證明 |
| test4 | 36／216 | 22 | NO_SAFE_MATCH | 後期目標 f1050 已進入 Re-ID，但外觀相似度 0.335，保持模糊 |
| test5（更新版） | 21／96 | 18 | NO_SAFE_MATCH | f96、192、288、366 的帶標籤手持目標維持 `phone_01`；後段座機未誤合併，最終位置未證明 |
| test6 | 31／204 | 22 | NO_SAFE_MATCH | 目標可見的 f630 缺少對應目標 YOLO 框 |
| test7 | 29／210 | 27 | MATCH `candidate_004` | **f636 座機錯合併**；真目標 f720／888 的後續候選未進 Re-ID |
| test8 | 29／204 | 24 | MATCH `candidate_009` | f804 正確找回原黑色手機；後續多手機延續尚未證明 |
| test9 | 53／546 | 38 | NO_SAFE_MATCH | 目標可見的 f810 缺少對應目標 YOLO 框 |

每片均有 `review.md`、`timeline.png`、推論 JSON 與輸入雜湊。test5 另有更新版影片的 `postfreeze_review_contact.png` 及 `postfreeze_overview.png`。

## 11. Test8 Multi-phone Stress Case

f804 的黑色目標 `candidate_009` 與先前座機候選一起評估：目標相似度 0.681，次高 0.422，margin 0.259，獲得正確 MATCH 並實際重啟 SAM。f888／918 的目標 `candidate_014` 與兩支座機 `candidate_018`、`candidate_020` 分別保留同幀共存。因 f804 已 MATCH，後面的三手機組合並未再聯合評分；完整後續身分延續尚未證明。

## 12. Detection Failure Analysis

人工複核的 test6 f630 與 test9 f810 目標可見，但沒有對應目標偵測框。test8 f810 也有目標 YOLO 漏檢，但 f804 已取得正確候選。這些情況不能算作候選接納或 Re-ID 失敗。未更換 YOLO 模型或信心門檻。

## 13. Candidate Admission Analysis

六個有目標框的後期目標抽樣中，6/6 進入候選流；真正被 Re-ID 評估的為 test4 f1050 與 test8 f804（2/6）。test7 真目標雖在 f720／888 進入候選，f636 的錯誤 MATCH 使後續評估提前停止。test8 的 f888／918 屬 MATCH 後的延續問題。此比率僅適用人工抽樣幀，無法推成全影片召回率。

## 14. Re-ID After Correct Admission

test4 正確候選 `candidate_018` 相似度 0.335，未達 0.60；test8 正確候選 `candidate_009` 達 0.681 且 margin 0.259，成功匹配。更新版 test5 無後期真目標候選的安全 MATCH，不能把後段座機的 AMBIGUOUS 判為目標 Re-ID 失敗。

## 15. Identity Safety / False Merge Analysis

test7 `candidate_004` 是不同的座機，f636 的相似度 0.611 略高於 0.60；沒有第二個合格候選，margin 為 null。原凍結 gate 錯誤 MATCH、建立 `phone_01` 別名，並實際觸發一次錯誤的 SAM 重新初始化。七片共兩次 MATCH：一次正確（test8）、一次錯誤（test7）。未依人工真值回調門檻或改寫預測。

## 16. Regression Results

完整測試 **122 通過、1 失敗**；新增的新鮮影片／凍結驗證測試 4/4 通過，原 V2.5 指定的 18 項測試亦通過。唯一失敗是舊 `test_v241_generalization.py` 要求目前 `test5.mp4` 的雜湊仍等於更新前的 `51a05f…`，但目前檔案是 `da637b…`。這是舊快照的輸入條件不再成立；本次新 V2.5 manifest 明確驗證並使用 `da637b…`。舊 V2.4.1 輸出與程式未改寫。

## 17. Remaining Limitations

首次 MATCH 即停止 Re-ID，讓 test7 的錯誤合併遮蔽後續真目標。SAM 重新初始化結果有實際產生，但其後續遮罩尚未重新經 V2.3 guard 寫回 registry。候選存在碎片化。test5 抽樣幀的身分延續良好，但最後放置位置沒有足夠直接影像證據。未建構空間記憶圖。

## 18. Result Classification

`MULTIPLE_UPSTREAM_FAILURES_REMAIN`：本次修正了 test5 資料一致性並驗證七片同源輸入；候選接納改善，但 test7 身分安全、test6／9 目標漏檢與 MATCH 後延續仍是不同的剩餘瓶頸。

## 19. Next Architecture Decision

`IMPROVE_FUSION_AGAIN`。下一版應先防止單一邊界相似度座機直接造成不可逆合併，並持續稽核 MATCH 後真目標與 SAM 遮罩在 registry 的延續。新策略需另行凍結並做全影片盲測；保留 test6／9 的偵測漏失作獨立問題追蹤。
