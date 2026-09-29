# V2.9.3 事件證據恢復與配對物理推論報告

結論：**V293_EVIDENCE_PIPELINE_VALID**

## 1. V2.9.2 的 54 筆失敗原因

- DENSE_MASK_ARTIFACT_LOST：6 筆。
- WINDOW_HAS_NO_TRUSTED_TARGET：44 筆。
- TRUSTED_REINIT_SEED_OMITTED：4 筆。

次要原因可以重疊：DURING 查詢錨點缺失 23 筆、AFTER 錨點缺失 26 筆。所有請求均有唯一主要原因與逐 phase 診斷。

根因包括 dense RLE 路徑讀錯後覆寫為空、reinitialized masks 漏接，以及事件視窗本來沒有可信目標。V292 frozen artifacts 保持原樣。

## 2. 修改範圍

- 建立獨立 OBSERVATION_AUTHORIZED：使用既有可信 seed、因果時間順序、既有 0.4 秒短延續限制與 drift/conflict 檢查。不能更新身份、alias、MATCHED、appearance bank。
- 保存 raw dense masks，再產生 observation 授權紀錄；接收 baseline 已授權的 SAM restart seed。
- 每個 target × anchor × event 自動選擇 1 個 BEFORE、1–3 個 DURING、1–2 個 AFTER。依實際幾何／可見性變化排序，固定每事件最多兩個查詢。
- AFTER 可使用 TARGET_NOT_OBSERVED_WITH_ANCHOR_VISIBLE，但需連續 anchor-visible view、無場景切換診斷、無 SAM/phone candidate，且延續先前有效目標證據。未觀測不等於物理不存在。
- AFTER 使用同一可見狀態；未觀測需要兩個連續視圖、在既有 0.4 秒短延續限制內開始，且前一目標 bbox 不可被影像邊界截斷，避免將移出鏡頭當成有效遮擋證據。
- 場景診斷採固定 luma difference >0.35 且 histogram correlation <0.2；這是新增的保守影像診斷，未改身份或物理 gate 閾值。它不能排除所有局部遮擋。
- VLM 使用原 Qwen2.5-VL-3B，僅回報 observable facts；輸出上限改為 768 tokens，容納完整 frame arrays 與 grounding schema。
- 開發時發現複製 prompt 描述範例會通過初版檢查；已加入拒絕檢查與 regression test。修正使用新 prompt，最終結果只保留通過現行契約重驗的回答。
- 圖組複核發現 VLM 將紫框中的人／手描述成附近籃球；加入一般類別／同義詞相容性檢查，無法對應 raw anchor hypothesis 的回答標為 grounding-invalid。保留 detector 語義不確定性，不把描述當成 GT 重新命名錨點。
- 使用原 V2.9 候選特徵與 physical gate；只有通過 grounding 的事實能送入 gate。V2.8 graph/search 和 identity outputs 均不被本版本寫入。

## 3. Evidence funnel：before / after

| 階段 | V2.9.2 | V2.9.3 |
|---|---:|---:|
| Pair requests | 54 | 54 |
| Eligible | 0 | 11 |
| VLM calls | 0 | 11 |
| Schema valid | 0 | 11 |
| Grounding valid | 0 | 5 |
| Physical gate relation calls | 0 | 15 |

V293 在同一事件的既有 anchor pool 內重新排序查詢錨點，因此這是相同查詢預算的流程比較，不是固定同一組 anchor 的模型 accuracy 比較。

| Video | Requests | Eligible | VLM | Grounded | Gate | P/C/U/R | 無物理輸出時的首個失敗階段 |
|---|---:|---:|---:|---:|---:|---|---|
| test1 | 6 | 2 | 2 | 0 | 0 | 0/0/0/0 | vlm_grounding |
| test2 | 6 | 4 | 4 | 1 | 3 | 0/0/1/2 | 已有 gate 輸出 |
| test3 | 6 | 0 | 0 | 0 | 0 | 0/0/0/0 | evidence_eligibility |
| test4 | 6 | 0 | 0 | 0 | 0 | 0/0/0/0 | evidence_eligibility |
| test5 | 6 | 0 | 0 | 0 | 0 | 0/0/0/0 | evidence_eligibility |
| test6 | 6 | 0 | 0 | 0 | 0 | 0/0/0/0 | evidence_eligibility |
| test7 | 6 | 0 | 0 | 0 | 0 | 0/0/0/0 | evidence_eligibility |
| test8 | 6 | 5 | 5 | 4 | 12 | 0/1/5/6 | 已有 gate 輸出 |
| test9 | 6 | 0 | 0 | 0 | 0 | 0/0/0/0 | evidence_eligibility |

## 4. Physical gate 結果

- OCCLUDED_BY：{'REJECTED': 4, 'UNCERTAIN': 1}
- BEHIND：{'REJECTED': 4, 'UNCERTAIN': 1}
- NEAR：{'UNCERTAIN': 4, 'CANDIDATE': 1}

開發中曾有一筆 HELD_BY PROMOTED，但圖組檢查發現 VLM 把 queried person/hand 描述成鄰近籃球；最終 grounding 契約已拒絕該回答，此筆不列入最終物理決策。

P/C/U/R 分別是 PROMOTED / CANDIDATE / UNCERTAIN / REJECTED。零 PROMOTED 可以是合理結果，本次沒有降低任何門檻。

## 5. Regression 與凍結

- 未授權 MATCHED：0。
- test2 track22/43 fusion：True。
- test7 identity/memory/search frozen hashes 維持：True。
- test8 forward loop：True；真實 confirmation frames：[804]。
- test9 unresolved：True。
- 身份閾值 0.6 / margin 0.1；protected policy source hashes unchanged：True。
- prediction freeze 後驗證：True，419 個檔案。
- 專項測試：V293 33 項、V292 66 項通過；完整套件 390 通過、3 失敗、1 跳過。
- 三項失敗均為執行前既有 V241/V25 歷史輸出雜湊不符，詳見 test_results.json；本次未改寫歷史輸出。

## 6. 選擇性 dense 重算

重算 6 個 bounded intervals。未重跑九支完整 YOLO/SAM。每側最多擴展 1.5 秒，日誌記錄 interval、seed、raw hash、原模型／config hash 與實際 canonical dense 參數（YOLO conf .15，imgsz 960，最高 15 fps）。
證據準備共 103.25 秒；最終保留 VLM 回答的推論時間合計 179.12 秒（不含捨棄的開發嘗試）。
同一 V293 開發執行中，若 prompt 與逐張輸入圖片 SHA256 完全相同，重用該次實際模型回答，重新執行 grounding / gate；輸入改變則重新推論。最終漏斗的 VLM calls 是具有實際模型呼叫來源的 pair 數。

## 7. 剩餘失敗原因與下一步

- NO_TARGET_BEFORE：42
- PAIR_NEVER_COVISIBLE：1

全體請求仍以缺少授權目標觀測為最大覆蓋限制；已有證據的 11 個配對中，6 個 grounding-invalid，顯示 VLM 配對辨識是目前可直接量測的下游瓶頸。

優先改善 pair-specific VLM grounding（區分查詢錨點與鄰近物件、處理 AFTER 可見性矛盾），使用已凍結開發證據評估；另行審核事件選取與可信觀測覆蓋，再處理正常 Identity Guard 的長間隔恢復。

## 8. 實際限制

- Grounding valid 表示 schema、查詢身份、時間引用與觀測狀態一致，不代表已經過獨立人工正確性標註。
- Anchor 描述相容性檢查是保守文字檢查，不是獨立視覺驗證器；偵測類別錯誤或同義詞不足可能造成 false rejection。
- 短時間場景診斷及 anchor bbox 可觀測性不能證明完全沒有鏡頭移動或局部遮擋。
- 繼承 V292 可信身份來源的限制；觀測授權不會修正上游誤認，也不會建立新身份。
- 未使用新錄製的 validation videos、GT 位置、新模型、訓練或 UI。

## 9. 代表圖組與重播入口

- 有效配對：review_sheets/test8_pair0/contact_sheet.jpg。
- 錨點描述錯誤並被拒絕：review_sheets/test2_grounding_rejected/contact_sheet.jpg。
- 移出鏡頭後不採用未觀測證據：review_sheets/test8_pair4/contact_sheet.jpg。
- 無證據案例：test1/debug_unavailable/ 下的 contact_sheet.jpg。
- scripts/run_v293.py verify 可驗證本次凍結檔案；prepare/reselect/replay 在凍結後會拒絕改寫。

V293_EVIDENCE_PIPELINE_VALID