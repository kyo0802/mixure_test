# 三模型人工 GT 評估進度

更新：2026-10-19。沿用既有 552 次生成，沒有新推論。

| 模型 | 已完成 | Raw JSON | Raw schema | Raw full-strict | 事件假說 | 其中 strict | 待審／不可用 |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen | 184 | 0 | 0 | 0 | 6 | 0 | 6 |
| videollama | 184 | 147 | 144 | 83 | 15 | 2 | 15 |
| nemotron | 184 | 166 | 163 | 108 | 146 | 58 | 146 |

人工 final GT：尚待裁決。PICKUP／PLACEMENT 的局部 precision、recall、F1 只會在核准 scope、模型物件身分與事件去重已解決時產生；詳見 evaluation.json。

目前未建立全資料集 exhaustive GT，所以 overall F1 保持 null。未審時間、未知身分、無法解析輸出不計為無事件或 TN。strict-invalid 假說只留在獨立 physical_candidates 分析，不能進 strict_valid 匹配。

物件名稱相同與 citation 時間重疊不能證明同一實物或同一事件。跨視窗去重依人工 reviewed_event_group，選字典序最早視窗作代表，不看 GT 選最佳時間。兩個真正事件即使區間重疊仍保留不同 group。

時間比較採既有 closed-interval distance 與 one-to-one maximum-cardinality，tolerance=0、0.2、0.5 秒。模型原生 before/after PTS 是引用界限，不是物理動作持續時間；只有人工確認該界限可定位轉變時才納入匹配。

Wrong-target 與物理 state 支持需人工驗證；JSON/schema/semantic 合格不等於物理正確。33 筆原始 state 暫作證據，未自動變成人工裁決 state GT。

先獨立完成 adjudication.csv 與 coverage_adjudication.csv，不用模型答案解決人工分歧。prediction_review.csv 為既有模型假說的獨立證據審閱表；可只處理欲評估的局部範圍，未審範圍透明保留 null。

## qwen / physical_candidates

可評分 scopes：0；被門檻阻擋：0。

## qwen / strict_valid

可評分 scopes：0；被門檻阻擋：0。

## videollama / physical_candidates

可評分 scopes：0；被門檻阻擋：0。

## videollama / strict_valid

可評分 scopes：0；被門檻阻擋：0。

## nemotron / physical_candidates

可評分 scopes：0；被門檻阻擋：0。

## nemotron / strict_valid

可評分 scopes：0；被門檻阻擋：0。
