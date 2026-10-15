# FindMind Pass T Phase2b — 輸出失敗稽核與pilot決策

2026-10-15。狀態：`PASS_T_PHASE2B_QWEN_NF4_OUTPUT_AUDIT_COMPLETE_AWAITING_USER_DECISIONS`。

## 回答九個問題

1. **18次為何失敗？** 13次event timing_uncertainty空字串、5次window引用空清單；全部先被schema擋。另11次既有known-state支持規則違反被early-return遮住，已獨立列出。
2. **事件多／結構複雜是否相關？** SUPPORTED_DESCRIPTIVELY：0事件20次中15pass；1事件8次全fail；2事件5次全fail。更多欄位與更多error機會可解釋觀察，但沒有因果證據；與frame/representation/reference混雜，非33獨立科學樣本。
3. **schema壞、格式、引用、截斷還是其他？** 33份strict JSON皆可解析，EOS皆有token證據、zero cap/timeout。直接是mandatory value錯誤；引用問題是清單空，不是不存在或未看過alias。11次semantic缺support。未發現導致這18次的schema自相矛盾或parse/instrumentation錯誤；完整replay一致。
4. **該改schema嗎？** 沒有以這批failure為依據的科學必要。非空文字可說無額外可觀察不確定性，引用規則可按任務解釋，無須為pass rate放寬。target/outcome/time語意仍需独立review；必要才另提versionedcontract。
5. **最小repair？** PROMPT_CHANGE_PROPOSED：以新task prompt明示非空uncertainty、每種outcome引用、known/unknown state與target ambiguity；保留V1schema/V2system/runtime。没有寫promptpatch，也沒有constraineddecoder或增加budget。
6. **三種8frame能同source嗎？** 現Multi/Storyboard六窗uniform8已核對一致，synthetic8三者source pixel digests一致，Video8原receipt確實消費indices0..7。DEV六窗matchedVideo8仍未建/verify，VIDEO_MATCHED_8_NOT_YET_VERIFIED；native→CFR時序、alias與2frame temporal merge必须单独核對。共同8frames≠共同pixel/tokenbudget。
7. **NONE可用嗎？** 可以作有限firstexploratory提案，6窗同政策，無refextra tokens；無target identity證明。association不明時INSUFFICIENT_EVIDENCE，而非強迫event或把identityambiguous當targetnotobservable。该語意仍待人工批准。
8. **Freeze缺什麼？** 候選prompt及另批regression、matchedDEVvideo receipts、targetNONE语意批准、point/interval/uncertain/nativePTS与一對一matching、finalsetting/retry/order/assets hashes、完整humanapproval。formaleligible仍0、causality未驗證。
9. **精確下一任務？** `PREPARE_QWEN_NF4_PROMPT_CLARIFICATION_AND_MATCHED8_CPU_PREFLIGHT`，需你另行授權。先做候選prompt與CPUpreflight，再以固定hash另批18callsyntheticregression；随后freeze審閱和realpilot各自授權。此audit不授權任何生成或freeze。

## 交付入口

- [逐次CSV（66列，primary/history分欄）](QWEN_NF4_STRUCTURED_OUTPUT_AUDIT.csv)
- [完整failure與18案來源](QWEN_NF4_STRUCTURED_OUTPUT_FAILURE_REPORT.md)
- [契約語意](QWEN_NF4_PREDICTION_CONTRACT_SEMANTICS_REVIEW.md)
- [最小修補矩陣](QWEN_NF4_STRUCTURED_OUTPUT_REMEDIATION_OPTIONS.md)
- [未執行syntheticregression設計](QWEN_NF4_MINIMAL_SYNTHETIC_REGRESSION_PLAN.md)
- [24項human決策、18run pilot草案](QWEN_NF4_FINAL_PILOT_DECISION_DRAFT.md)
- [Freeze未就緒](QWEN_NF4_FREEZE_READINESS_AUDIT.md)
- [保存／測試驗證](QWEN_NF4_OUTPUT_AUDIT_PRESERVATION_REPORT.md)

最後33 = 11warmup+22measured、15/33strictpass；較早33 = 12/33，只engineeringhistory。全部raw/token/resource與來源回條已核對，未把synthetic輸出當真實event accuracy。actualPhase2a pilot0，newmodelcalls0。

十八run提案：6clean DEV窗×Multi8/Storyboard8/MatchedVideo8×repeat1，UNIFORM8、NONE、200704pixelcap、1024output、greedyseed42、load120/gen300/request330秒、generationretry0，所有0/.2/.5sensitivity全報。這些是PROPOSED；不是已批准配置。request上限99分鐘未含load/prep/retry，無30分鐘承諾。

早期文件採不同階段名稱V1/V2/V3，這裡primary明確指20261014_owned_tree capacityround、V3共用taskcontract+V2formatting、PredictionV1。全部來源与摘要hash在source_authority.json；已核對finalcapacity receipt與schema源碼版本，不靠舊摘要推定結果。
