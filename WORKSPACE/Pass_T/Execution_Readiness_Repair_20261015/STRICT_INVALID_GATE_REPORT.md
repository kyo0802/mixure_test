# Strict-invalid Gate Report

## Implemented caller policy

Protected `predictions.parse_raw/validate_prediction`與Prediction V1 bytes未變。新增 `v1d_outputs.classify_output` 呼叫原始介面，不複製／放寬validator。

| Input / condition | Classification | Authoritative matching |
| --- | --- | --- |
| No raw output | ABSENT_PREDICTION；各stage NOT_ASSESSED | 不可進；不推NO_EVENT |
| Malformed/duplicate-key/nonfinite/nonobject/invalid UTF8 | INVALID_JSON；JSON/FULL FAIL | 不可進；不做JSON repair |
| Schema failure | STRICT_INVALID；SCHEMA FAIL；SEMANTIC/CITATION NOT_ASSESSED_DUE_TO_SCHEMA_FAILURE | 不可進；不把early-return空error list誤標PASS |
| Semantic / citation failure | SCHEMA PASS；分別記SEMANTIC/CITATION FAIL；FULL FAIL | 不可進；不發明citation |
| All original strict checks pass | VALID_*；FULL PASS | 仍需frozen source/provenance及GT用途資格 |
| Valid zero-event outcome | VALID_NO_CONFIRMED_EVENT | 與invalid/absent分開；不從格式推physical truth |
| Runtime receipt mismatch | Raw及原receipt保存；authoritative_prediction=None | 不可進；保留validation stage與receipt問題的區別 |


`record_call_result` 用exclusive+flush+fsync先保存raw，接著保存原receipt，再分類。strict-invalid不轉成NO_EVENT或自動FN；定性review固定另列UNREVIEWED/DESCRIPTIVE_ONLY，沒有生成新人工標籤或GT。

`evaluate_recorded_call` 驗frozen/auth/raw/receipt綁定與window用途，再經gated evaluation；不自行讀GT，只有私有caller傳入的核准record可用，且從不進model payload。兩nonexhaustive窗的額外events為UNEVALUATED，test8保持descriptive；三negative只報case-level alert，沒有FPR或正式accuracy/precision/recall/F1/hallucination/generalization。

Parent run summary將 NOT_EXECUTED_AFTER_STOP、ABSENT_PREDICTION_AFTER_START、INCOMPLETE_RECEIPT_RAW_PRESERVED、各invalid與有效NO_EVENT分開，並分stage報PASS/FAIL/NOT_ASSESSED計數，不能從分母悄悄排除失敗。

## Evidence

- 最終53/53 CPU tests通過。18call metadata mock故意1個schema-invalid、1個invalid JSON、16個合法software NO_EVENT，驗證固定18次、無retry、raw全保存及invalid排除。**16/18不是VLM結果、不是模型accuracy。**
- protected historical V1D仍strict1/8，6個event-bearing全部strict-invalid；原8raw/receipt/report hashes在140項保存檢查內皆未變。沒有retroactive reclassification。
- 原schema failure early-return本身未改；未評估stage仍明示，不另造權威validator。
