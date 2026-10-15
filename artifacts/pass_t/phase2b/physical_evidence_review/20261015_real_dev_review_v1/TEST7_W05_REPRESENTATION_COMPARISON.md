# TEST7_W05 Representation Comparison

[開啟離線比較頁](TEST7_W05_REPRESENTATION_COMPARISON.html)

| Call | Representation | Outcome | Exact model rationale | Timing | Contract |
|---|---|---|---|---|---|
| 2 | MULTI_IMAGE | NO_CONFIRMED_EVENT | No event claim | — | STRICT_VALID_NO_CONFIRMED_EVENT_COMPARATOR |
| 4 | STORYBOARD | CONFIRMED_EVENTS | The ball is picked up from the surface in frame F0001. | {'frame_alias': 'F0001', 'status': 'EXACT_SUPPLIED_FRAME'} | STRICT_INVALID_DESCRIPTIVE_ONLY |
| 8 | NATIVE_VIDEO_ARRAY | CONFIRMED_EVENTS | The object is picked up from the table. | {'frame_alias': 'F0001', 'status': 'EXACT_SUPPLIED_FRAME'} | STRICT_INVALID_DESCRIPTIVE_ONLY |

只比較既有表示的輸出；不宣稱哪個較好。名詞不代表 verified identity。五個事件假說皆 invalid；格式與物理證據分開。

Call 2 strict-valid NO_CONFIRMED_EVENT 為 disagreement comparator，不是自動 false negative，也不是第六個 event-bearing hypothesis。
