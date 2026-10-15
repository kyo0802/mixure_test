# Prediction V1 語意檢視

權威：[prediction_v1.json](<C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/contracts/prediction_v1.json>)；[predictions.py](<C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/predictions.py>)；[event_gt_annotation_schema_v2.json](<C:/Users/smile/Desktop/test2/mixure_test_SAM/artifacts/pass_t/phase2a/v2/contracts/event_gt_annotation_schema_v2.json>)。具體來源 hash 在 source_authority.json；這些不是本次新 schema。

| 欄位 | 現有約束 | 空/null/漏欄位 |
|---|---|---|
| events[i].timing_uncertainty | 每一個 event 必填、string、minLength=1，沒有 exact-time 例外 | 空字串invalid；null invalid type；漏寫required violation；明確寫無額外可觀察不確定性可合法，不必捏造不確定性 |
| timing.status | EXACT_SUPPLIED_FRAME / BOUNDED_SUPPLIED_FRAMES / TIMING_UNKNOWN oneOf，各有對應alias要求 | status是enum/const；不是timing_uncertainty文字欄的替代 |
| window_cited_frame_aliases | 每個window outcome都必填array，minItems=1，uniqueItems，Fdddd pattern | 空清單invalid，null invalid type，漏寫invalid；沒有abstention例外 |
| event.cited_frame_aliases | 每個event最少1alias | 只檢查存在/格式，不保證before-after兩種物理證據均充分 |
| supporting_frame_alias | schema允許string/null；validator已知state要求非null、unknown要求null | schema nullability與semantic guard為分層規則，沒有互相矛盾 |
| top uncertainty | 必填非空free text | 不限LOW等enum；可說association無法判斷 |

V1對四種結果都要求window引用：CONFIRMED_EVENTS支援事件、NO_CONFIRMED_EVENT支援觀察範圍、INSUFFICIENT_EVIDENCE引用可用但不足的視覺內容、TARGET_NOT_OBSERVABLE引用支持不可見的所提供內容。引用存在不是連續可評估性的證明。不存在可引用內容時应pre-generation input eligibility阻擋，不能捏造alias來通過。沒有科學理由只為把五份failure變pass而移除minItems。

無現行空欄位矛盾可證實；應先維持V1。科學語意仍須獨立確認：

- NO_CONFIRMED_EVENT與INSUFFICIENT_EVIDENCE的界線：前者需要該任務可評估而無確認事件，後者可因target association不足；現validator沒證明full-window assessability。
- NONE + TARGET_A是opaque名稱，不是物理定位。INSUFFICIENT_EVIDENCE配合uncertainty已可表達身分／局部關聯不足；TARGET_NOT_OBSERVABLE不能等同多手機中不知道哪支是target。
- event.target_association_uncertainty允許NONE/POSSIBLE/HIGH，validator未禁止HIGH搭CONFIRMED_EVENTS；未見本母體此缺陷，但其評估解讀需前瞻批准。evaluator僅NONE可known-event matching；不能強迫model填NONE。
- end_visibility是所供影格末端還是authorized window end？Long118只處理14張且可能沒看到最後一張，必须區分；未知尾段保持UNKNOWN。
- PICKUP/PLACEMENT目前validator沒有硬編before/after state型別轉換；UNKNOWN狀態可能合理，不能自行發明transition-state violation。
- `SCHEMA_SEMANTICS_AMBIGUOUS`用於上述政策待釐清，未歸責為這18份失敗的直接原因。沒有生成新版schema或validator。

引用分類：編碼clip内存在 ≠ processor有看見；只可引用processed aliases；static reference無event aliases，不可引用作事件。Timing/state aliases也受相同allowlist約束。診斷更檢查unsupported vs supplied-but-unconsumed；primary全零。timestamp correctness需private native PTS，raw只有alias無numeric timestamp，citation timestamp mismatch在本母體不可直接量測。

關於狀態／物理猜測：11份known-state無支持是現規則可直接確認的錯誤。某回答宣稱placement卻before_state UNKNOWN，在V1未被禁止，僅列advisory，不能自造fail。安全assertions=false只是聲明，不能證明沒有視覺推理越界。

修補層級：先版本化prompt清楚說明非空理由、每種outcome的引用、known/unknown state支持及NONE下target ambiguity。獨立ontology語意審閱若真的發現不可表達且必要的狀態，才另提schema V2+validator版本+舊新結果分離。本任務不更動任何現行契約。
