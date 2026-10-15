# Target 身分歧義條款 — PENDING_APPROVAL / NON_EXECUTABLE

提案原文（沒有放入核心prompt）：

> Under TARGET_REFERENCE_NONE, if the supplied media cannot establish which physical instance is the intended local target, use INSUFFICIENT_EVIDENCE and explain the target-association limitation in uncertainty. Do not equate unresolved identity with TARGET_NOT_OBSERVABLE, and do not convert a generic scene transition into a target-specific event without evidence.

現Prediction V1允許INSUFFICIENT_EVIDENCE、empty events、STATE_UNKNOWN/null與非空uncertainty；獨立CPU字典透過未改validator接受：{'valid': True, 'structural_errors': [], 'citation_errors': [], 'semantic_errors': []}。這只是technical acceptance，不是humanapproval。

身份未確立、已確立目標不在可觀察視野、物理轉換證據不足是三種不同概念。現schema能以outcome+自由文字表达第一及第三，TARGET_NOT_OBSERVABLE不應被當作多實例ambiguity的別名。沒有加入target field或強制HIGH/LOW；CONFIRMED_EVENTS配HIGH目前validator接受但需要前瞻解讀，不能由此推定身份確認。

替代：拒絕NONE首次條件，另設授權的target-reference定位任務；或獨立ontology review證實現schema无法表达必要語意才另提版本化schema。本次不採用任一替代。

風險：opaque TARGET_A缺靜態target reference時可能無法唯一關聯；偏向abstention影響任務定義，並不代表事件推理好壞。需要human選擇批准或拒絕確切條款及NONE的有限科學意義。未批准前不可將本段串入regression executableprompt，不得啟用。
