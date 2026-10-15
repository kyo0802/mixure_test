# Collect-all 非計分診斷

主要母體33次，11 warmup/22 measured，strict原判定15/33。重播一致33/33；G1–G5={'G1': True, 'G2': True, 'G3': True, 'G4': True, 'G5': True}。

影子module不接入scoring。現validator只有完整函式、未暴露獨立semantic predicates，因此只讀匯入原schema/parser/validator，另依原碼逐條reimplement shadow；G2/G3核對該做法而不改validator。所有原raw SHA由capacity完成回條驗證。

Affected attempts：{'KNOWN_STATE_SUPPORT': 11, 'EMPTY_TIMING_UNCERTAINTY': 13, 'EMPTY_WINDOW_CITATIONS': 5}；individual predicate violations：{'EMPTY_TIMING_UNCERTAINTY': 18, 'KNOWN_STATE_SUPPORT': 20, 'EMPTY_WINDOW_CITATIONS': 5}。不可將兩種數量相加。被early return遮住的known-state缺支持：11份、20個欄位。包括event before/after與last state，完整JSON path、既有error文字、state/alias證據在JSONL；不只猜HELD狀態。零事件的event-specific checks是NOT_APPLICABLE；wrongtype/missingalias prerequisites用NOT_EVALUABLE。

13空timing/5空windowlist/11masked與前audit核對，G4=True。精確數量及condition/event-count tables在diagnostics/frequencies.json；解釋模型內在機制仍是推測。沒有schema relax、raw修補或重新評分。target HIGH/POSSIBLE/confirmed政策並非現validator規則，標NOT_APPLICABLE待語意審查。
