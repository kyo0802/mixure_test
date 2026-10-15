# FindMind Pass T Phase2b Revision2 完成報告

2026-10-15。**PASS_T_PHASE2B_QWEN_NF4_PROMPT_MATCHED8_PREFLIGHT_COMPLETE_AWAITING_USER_APPROVAL**。

## 1–3 Strict與完整shadow

33/33 strictreplay一致，原15/33pass不變，G2–G5全部PASS。13attempt/18欄位emptytiming、5attempt/5emptywindowlists，11attempt/20maskedknownstatesupport。knownstate breakdown：after_state11、before_state6、laststate3。分NA/NE/SAT/VIOL與原errorfirst順序保留；沒有自造HIGHconfirmedfail。完整JSONL、frequencies、影子dependency修正confirmation均有hash和receipt。

## 4–6 Fixture與prompt

6eval（0/1/2intended各2）+1warmup，56新CPUscene影格，先lock再prompt。鎖回條SHA=149f8696e51fa91cf43147d761315672dc43594aebe41b58cea8ed78956346ee，manifest與所有pixels鎖定，promptreceipt直接引用lockhash與Step0B，非僅時間戳。沒有舊capacityimages、realPhase2apixels或舊raw作syntheticinputs；作者仍知場景概念，不声稱概念blind。脚本意圖不等於modelrecognizedevents。

唯一候選：[QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt](QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt)，SHA `3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722`，3549bytes、exacttask-onlytokens=659（Qwen2TokenizerFast/transformers4.57.6，無system/schema/media expansion）。只新增A非空時間解释、B各outcome引用、Cknown/unknownstate證據規則；V1schema/V2system/V3runtime不改；沒有答案examples。D身分條款只在[TARGET_IDENTITY_AMBIGUITY_CLAUSE_PENDING_APPROVAL.md](TARGET_IDENTITY_AMBIGUITY_CLAUSE_PENDING_APPROVAL.md)，core不含、未批准、未啟用。

## 7–9 Matched8與時間限制

| Case | Kind | Outcome | Max nominal Δs | Max processor-unit Δs | Max static-model-position proxy Δs |
|---|---|---|---|---|---|
| test1 | DEV | FRAME_MATCHED_ONLY | 0.01499999999999968 | 0.5150000190734856 | 0.5349999999999993 |
| test5 | DEV | FRAME_MATCHED_ONLY | 0.014285714285714013 | 0.3476190090179436 | 0.6999999999999993 |
| test7 | DEV | FRAME_MATCHED_ONLY | 0.014761904761904088 | 0.5147619597117092 | 0.5383333333333322 |
| test8 | DEV | FRAME_MATCHED_ONLY | 0.013809523809521274 | 0.5683333333333351 | 0.8900000000000006 |
| test2 | DEV | FRAME_MATCHED_ONLY | 0.014523809523809827 | 0.5161904446283971 | 0.5716666666666663 |
| test5 | DEV | FRAME_MATCHED_ONLY | 0.014285714285714235 | 0.5142857154210407 | 0.5666666666666664 |
| X_9466c22b82dad731 | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | 0.0 | 0.5 | 0.5 |
| X_1de7663247196813 | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | 0.0 | 0.5 | 0.5 |
| X_685180893dee1e85 | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | 0.0 | 0.5 | 0.5 |
| X_1c1b2f1aa6ae3ac2 | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | 0.0 | 0.5 | 0.5 |
| X_abef8149c15bfb7e | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | 0.0 | 0.5 | 0.5 |
| X_6a46f3734a47a8a3 | SYNTHETIC_EVAL | FRAME_MATCHED_ONLY | 0.0 | 0.5 | 0.5 |
| X_0009ab2fbef22158 | WARMUP | FRAME_MATCHED_ONLY | 0.0 | 0.5 | 0.5 |

六DEV+六eval+warmup全部FRAME_MATCHED_ONLY。八個sourceRGBdigest/order/lineage/Uniform8與前receipt位置一致；原生VideoarraypublicAPI有video_grid_thw，沒有影像列表冒充Video，也没有forward。無container，所以encodedtime=null；nativePTSprivate，Video時間以fps作uniform重建。actual2frame/patch→4時間位置，相對native每frame偏差超0.1proposal；nominal8frameCFR可能很接近native，但不可忽略actualtemporalunit量化。reason詞CFR_TIME_DISTORTION在此指uniform reconstruction/temporalunits的偏差，並非宣稱有containerCFR。影像/storyboardORDER_ONLY，原生時序沒提供；無time-information/pixel/tokenparity聲稱。

8sourcealiases可通過membership，但模型是否逐frame辨識尚未證明；RUNTIME_CONSUMPTION_NOT_VERIFIED。原V3runtime走AVI，nativearrayroute尚未整合，是另個工程決策。不能把本CPUpreflight接成GPUrun。詳細sourceIDs/nativePTS/digests、tiletransforms、observer/grid/tensorhash、perframe rawdeviation見[Matched8 CPU report](QWEN_NF4_MATCHED_VIDEO8_CPU_PREFLIGHT_REPORT.md)及private_mappings。

補充[model temporal-position audit](MODEL_VISIBLE_TEMPORAL_POSITION_AUDIT.md)為Step2必要合讀：實際config tokens_per_second=2，get_rope_index再.long()，表中另列staticmodelpositionproxy；它不同於processorgrid秒數，也不是呼叫model得出的runtime證據。

## 10 Regression草案

[18-call preregistration](QWEN_NF4_18_CALL_SYNTHETIC_REGRESSION_PREREGISTRATION.md)：6fixture×3rep，固定hash交錯，Video arm未批准而阻擋；VariantB獨立12call，不自動fallback。獨立warmup最多3與2condition×2repeat=4均另計且需另批。每rep>=2/6event-bearing、>=1knownstate適用，pooled>=6/18；所有strictvalid+coverage才REGRESSION_PASS，否則STRUCTURAL_PASS_COVERAGE_INSUFFICIENT/FAIL/INCOMPLETE，不能强迫事件以填coverage。Generationretry0，infra最多1僅開始前；一candidate失敗停止，最多一個另批revision，未執行。

## 11–12 Tests／保存

60 uniqueCPUchecks＋3個modelposition計算檢查全部PASS；29746既有檔案hash全不變，Git HEAD/index/worktree不變。所有script設CUDA_VISIBLE_DEVICES=-1、HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1，網路/權重/model-pretrained/generation/CUDAinit failclosed，scriptAST沒有非processorfrompretrained/generate/serverlaunchcall。GPU/processbeforeafter與CPUcuda_initialized紀錄保留；對外部程序沒有連續trace，不聲稱hash能证明全機否定。new_model_calls0、GPUinference0、realPhase2a prediction0、protocolfreeze0、Graphwrite0、commit/push0。

## 13–14 剩餘gate／下個授權

PROTOCOL_NOT_READY_TO_FREEZE。21gate見[Pilot decision package](QWEN_NF4_PILOT_DECISION_PACKAGE_V3.md)：核心prompt、identityclause、NONE語意、Videoframeonly與alias精度、nativearrayruntimebridge、budget/generation/retry/時間matching/敏感度、regression與最終protocol仍需human決策。knownPICKUPonly、negativecasealerts、test8descriptive、test3excluded、formal0與CAUSALITY_UNVERIFIED保留。

下一步需要你的**明確選擇與授權**：批准或拒絕V1C及独立identityclause；選18callVariantA（先另行runtimebridge審查及FRAME_MATCHED_ONLY批准），或獨立12callVariantB；明示warmup/4extra-repeat是否授權，再授權該版本的有限syntheticregression。未決前不執行任何calls。Regression結果審阅後的protocolfreeze和RUN_PHASE2B_EXPLORATORY_PILOT仍各自獨立授權。

本次成功條件是CPUdiagnostic、先鎖fixtures、單一candidate与诚實preflight；沒有宣稱事件偵測改善或GPU成功。所有stepreceipts和檔案hash列在DELIVERABLE_MANIFEST.json，這是工程交付manifest而非humanapprovedprotocolfreeze。
