# Windows A / B — 最終完整性複核報告

狀態：PASS_T_PHASE2A_EXHAUSTIVENESS_REVIEW_COMPLETE_NON_EXHAUSTIVE

Reviewer：reviewer_0；人類明確聲明「不是原 ZIP 標註者」。本次是 INFORMED 複核，已見既有標籤與視覺支持記錄，不是 blind 或 independent review。

| 視窗 | 人類最後一格回答 | 結果 | 原事件／本 view 保留事件 | exhaustive_review_readiness | 品質放行 |
|---|---|---|---|---|---|
| A test5 W05，S000449 | NO | NON_EXHAUSTIVE_CONFIRMED | 1 / 1 PICKUP | false | 否 |
| B test7 W05，S000479 | NO | NON_EXHAUSTIVE_CONFIRMED | 1 / 1 PICKUP | false | 否 |

## 原規則與判定

兩窗皆 cannot meet V2 last-frame coverage requirement，因此依使用者指定流程跳過 Phase 1–2，只完成 Phase 3 的最小 sidecar 保存及匯出。

```python
    strict_coverage = (response['window_outcome'] == 'NO_CONFIRMED_EVENT' or
                       response.get('event_list_exhaustiveness') == 'EXHAUSTIVE_ATTESTED')
    if strict_coverage:
        need(response['coverage_assessment'] == 'THROUGHOUT_ASSESSABLE', 'Unobservable gap blocks exhaustive/negative claim')
        need(frames[0]['frame_id'] in coverage_ids and frames[-1]['frame_id'] in coverage_ids,
             'Coverage requires first and last authorized frames')
        need(any(len(frames) // 3 <= positions.get(fid, -1) < math.ceil(2 * len(frames) / 3)
                 for fid in coverage_ids), 'Coverage requires middle-third frame')
        need(all(c['target_association'] == 'SUPPORTED' for c in response['coverage_citations']),
             'Coverage target association unsupported')
        need(response['visibility_at_window_end']['visibility'] in ('VISIBLE', 'PARTIALLY_OCCLUDED'),
             'Coverage claims assessable visible target at end but end visibility contradicts it')
    elif response['window_outcome'] == 'CONFIRMED_EVENTS':
```

A 的 S000449 HELD_BY_PERSON 是人類已澄清的 inferred state, not directly observed，不算 COVERAGE 或 gap interval 支持。B 的最後一格也由人類確認沒有直接可見目標支持。不猜測遮擋後是否仍在手中；放入箱子不自動改標 PLACEMENT，也不合併 32/34。

## 保留用途與未宣告事項

兩個 PICKUP 仍保留為探索性正例；未来只可做既知正例的命中／有限 recall 測試，額外預測 UNEVALUATED。不能計算全窗 precision、FP、FN、recall 或 hallucination rate。

本次明確判定的影格是 A S000449、B S000479。先前 PICKUP 支持範圍記錄仍獨立保存；未聲稱此次全窗逐格看完。完整 gap ledger 未收集，未捏造間隔邊界。四項完整性聲明全為 null（未提供，不代填），未新增或挑戰事件標註，未新增任何 V2 response 或 exhaustive attestation。

四層分開：原 annotation validator 有效；PICKUP 已有人工視覺支持；完整清單不受支持；品質尚未放行。formal_eligible=0、CAUSALITY_UNVERIFIED。

原 V2 NOT_ATTESTED 與 full-window false 都未修改。Phase 2b 必須另外讀取 sidecar 的 exhaustive_review_readiness=false，不能將它誤認為被改寫的 V2 flag。test3 仍隔離且不在本次範圍。

## 下一步（繁體中文）

這兩窗的完整性複核已完成，不用再填 exhaustive 勾選表。若要建立可評估全窗的資料，請另行設計前瞻抽樣（含隨機負控制），安排獨立第二標註者、確認 recording-session independence，並預先註冊採樣與計分規則。不同人但看過答案的本次複核不能取代獨立標註。

設計教訓：本批視窗按 event expected 選取，且在目標離開可視範圍後才結束；未来應規劃在目標仍可觀察時結束的視窗，並避免用事件預期代替代表性抽樣。

## 驗證範圍

這是 Phase 0 NO 分支，不實作 Phase 1 schema/validator 或 Phase 2 GUI，故未執行其合成測試與整套回歸測試。已執行原 authority／匯入驗證、原檔逐位元組雜湊保存檢查、唯讀匯出、相同內容重複匯出檢查；結果見 preservation_and_export_checks.json。沒有模型推論、metrics、Graph write、commit 或 push。
