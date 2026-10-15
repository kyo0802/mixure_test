# Pass T Phase 2b — Final Pilot Execution Readiness Repair

Task：`PASS_T_PHASE2B_QWEN_NF4_EXECUTION_READINESS_REPAIR`  
日期：2026-10-15；結論：**ENGINEERING_READY_FOR_HUMAN_FREEZE_REVIEW**。

Authoritative repair report：[本次修補報告](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/READINESS_REPAIR_REPORT.md)。WORKSPACE latest copy更新至同一內容。當前仍在Pass I/T平行標註＋實作；Phase2b尚未完成。

## 1. 完成事項

三個原始code blockers已處理；strict-invalid caller gating/reporting補齊。**53/53 CPU tests通過**，另完成真正CLI的metadata dry-run。只使用一個working tree，沒有平行修改agent。

| Blocker | Responsible interface | Repair | CPU verification | Remaining scope |
| --- | --- | --- | --- | --- |
| A / T01 | video_array_bridge.prepare_video_array + v1d_protocol.bridge_eligibility | 新增real_pilot_mode=FROZEN_V1D_PILOT_V1；驗frozen/21decision approval/獨立執行授權、V1D/V2/schema/runtime/bridge hashes及call/alias/PTS；保留synthetic原guard | 缺freeze、缺授權、hash/rep/alias/PTS/prompt/system/預算/洩漏遭改均拒絕；MOCK records在真正preprocessor之前拒絕 | 真實array/processor/GPU仍未執行；8source→4unit、FRAME_MATCHED_ONLY不變 |
| B / T02 | v1d_protocol + v1d_execution + explicit CLI | 獨立versioned draft/freeze/run介面；三格式in-process共18call；不走legacy prompt_path/HTTP/AVI fallback；21項仍PENDING | 真實metadata dry-run成功；18call軟體mock一個runtime factory；授權nonce lease與call claim防重播；預設CLI不執行 | 未建立human-approved frozen protocol；currentmedia與weights未驗證 |
| C / T04 | evaluation.match_known_events / CLOSED_INTERVAL_GAP_V1 | 版本化closed-interval gap；historical default LEGACY_OVERLAP_V0仍原行為 | 點內/端點/前後/overlap/touch/disjoint/zero-width；0/.2/.5邊界與一對一、unknown/缺時/關聯不確定測試通過 | 這是待核准candidate semantics，不是已核准科學決策 |
| Strict output / T03 | v1d_outputs + record_call_result/evaluate_recorded_call | 原raw durable/exclusive保存，5stage分開，schema early return標NOT_ASSESSED；invalid與缺結果不得進matching；定性另存 | invalid/schema/semantic/citation/absent/有效NO_EVENT分支；mock18call中2invalid仍保留並繼續；nonexhaustive額外預測UNEVALUATED | 不宣稱schema/temporal match證明physical correctness |
| Media / M01 | draft_protocol/validate_draft/load_envelope | pin來源metadata、全authorized-list SHA/boundary、Uniform8、8alias/nativePTS及sourcePNG/storyboard hashes；執行時先授權再開檔驗bytes | 現有文字metadata一致性核對；未授權loader在任何媒體開檔前拒絕；mock receipt綁protocol/auth/source | PENDING_AUTHORIZED_EXECUTION；本次沒有重新hash/read真實媒體或原始source video |


## 2. 執行設定與人類狀態

新draft完整保留原候選六窗：test1 W03/W05去重、test2 W01、test5 W01、test5 W05、test7 W05、test8 W07；test3 W07排除。三negative僅case-level alerts、兩known PICKUP非完整清單、test8 uncertain；沒有validated PLACEMENT positive。

同一GT-independent Uniform8、ReferenceNONE、MI8/SB8/NativeArray8共18call、immutable V1D/V2、C3 report-only temporal-unit disclosure、FRAME_MATCHED_ONLY八source/四units、greedy42/1024/repeat1、無generation-quality retry/新identity clause/Graph。0/.2/.5全報，closed-interval matcher另有明確版本。21項scientific/protocol決策全部仍PENDING。

CLI dry-run輸出：draft canonical SHA `c799b5d13a7721a02e88d25f9474081b6d5975bb2b6f71a72f61bf1ba7a00f02`、planned_calls=18、decisions_pending=21、model_initialized=false、calls_executed=0、protocol_frozen=false、media_integrity=PENDING_AUTHORIZED_EXECUTION。[可審閱草案](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/DRAFT_CONFIGURATION_CANDIDATE.json)。

## 3. 來源變更與不變項目

| File | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| [src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py) | 5cfebb8d93294585cc62531258fba79f2d5abc2cb57e0f1ba1e108664288ed4e | 75ba3f8fc63b13b869eb684ba3c7dc1ab9061c68efc2bee19dc5ab4f72802cef |
| [src/memory_graph/pass_t/phase2b/evaluation.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/evaluation.py) | 4d69a83f361579b0e22a00075b3e1e9a5255daec416c9a5937240f22c7f19826 | 975c8706f11d0c8f05184cc2025bdd3f04ce2439eceb0a5970f0f91b227d33bb |
| [src/memory_graph/pass_t/phase2b/v1d_protocol.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/v1d_protocol.py) | NEW FILE | ae41eb4debc944247f8339f45e0922a2228a5f55ce8331ddea962c76f3cff8e1 |
| [src/memory_graph/pass_t/phase2b/v1d_outputs.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/v1d_outputs.py) | NEW FILE | e746203c7f92cbcb4aa9e2af6a302325cdc8c8293bfc83a93b5317d73a2cb1f3 |
| [src/memory_graph/pass_t/phase2b/v1d_execution.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/src/memory_graph/pass_t/phase2b/v1d_execution.py) | NEW FILE | 958f5d3d44803716290d218182fe02a8e1ff0070614c0e751b9d8b544e063ccf |
| [scripts/run_pass_t_v1d_pilot.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/scripts/run_pass_t_v1d_pilot.py) | NEW FILE | 2edcb6beb927e3b6756c0cdaedd360bf46031cca4f385076a7146e691fe8dc35 |
| [tests/test_pass_t_v1d_readiness.py](C:/Users/smile/Desktop/test2/mixure_test_SAM/tests/test_pass_t_v1d_readiness.py) | NEW FILE | bbed483e3efe7eafca05919e908bbc1b565eec73fe62e98446bc97a56b0838e0 |


[完整逐行 source diff](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/EXACT_SOURCE_DIFF.patch) SHA：`180200fd88004d0e5b20d13f6494645eb31bc62a5ddd75e05f15dced923f3061`。[SOURCE_CHANGE_MANIFEST.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/SOURCE_CHANGE_MANIFEST.json) 保存before/after SHA和Git狀態；before source文字在本目錄before_source。新增report/helper與WORKSPACE導航屬文件出版，不是runtime source改動。

**未修改** V1C/V1D、V2 system、Prediction V1/schema/strict Parser/Validator、shared NF4 loader/generate、legacy transport/protocol/config/inference或任何historical regression/review。140個protected text/source/receipt檔案SHA全相同；Git HEAD/index/staged diff不變，既有工作樹變更未重設。原GT未讀寫；本次未重算其內容hash，不把範圍外檔案宣稱為已逐byte驗證。

## 4. 測試與驗證證據

[CPU_TEST_RESULTS.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/CPU_TEST_RESULTS.md)、[最終測試log](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/cpu_tests_final.log)、[結果JSON](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/CPU_TEST_RESULTS.json)。

53tests/0fail/0error/0skip；no model modules loaded、no audit denials、actual model calls0。18call軟體mock是對控制流程的測試（故意schema-invalid1、invalidJSON1、其餘mockNO_EVENT16），不是模型表現或新VLM預測。沒有產生任何視覺fixture。

## 5. 尚未驗證且必須保留的邊界

- 真實PNG/storyboard/current media hashes、pixel decode/native array、actual processor grids/positions、模型權重/currentGPU resources、CUDA實際數值/安全timeout/真正18call均未執行。media mechanism已實作，現況仍 **PENDING_AUTHORIZED_EXECUTION**。
- native PTS來自pin住的既有source metadata；不宣稱本次重讀原video或重新驗original source-video SHA。8aliases不能解釋成8個獨立temporal positions；actual forward positions仍未instrumented。
- 新observer記錄CPU tensors/input IDs/rendered文本，尚無real DEV receipt可供驗證；相關功能只有mock/既有source契約證據。
- 凍結與執行授權記錄是可追溯的人類來源宣告，不是人類作者的密碼學簽章。沒有人類approval就不得建立真正freeze；MOCK資料不能載入模型。
- Python/file/import guard與相關SHA只覆蓋本次工具/程式；不是全機native-access trace。Git inventory受既有permission/long-path及normalized diff限制，保留範圍據實標示。

## 6. 科學結果未改

歷史 V1D regression仍 **REGRESSION_FAIL，strict1/8，6event-bearing全部strict-invalid**。D4僅表示沒有找到特定可見序列化缺陷。工程修補沒有改善或重新測量模型accuracy/precision/recall/F1/FPR/hallucination/generalization；這些正式指標仍不可宣稱。

VLM仍負責physical event hypotheses；deterministic software只做validation、temporal resolution和未來Graph更新。本次未重設Event-to-Graph，也沒有Graph寫入。

## 7. 下一個人類決策與停止

[REMAINING_HUMAN_APPROVALS.md](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/REMAINING_HUMAN_APPROVALS.md) 列21項及decision digests。下一個freeze-only confirmation是：

`APPROVE_PHASE2B_V1D_FREEZE c799b5d13a7721a02e88d25f9474081b6d5975bb2b6f71a72f61bf1ba7a00f02 NO_EXECUTION`

另需reviewer及21項逐項approval記錄；本次未收到或自批。freeze後仍須獨立execution authorization才能18call。到此停止：**未freeze、未載入模型、未初始化CUDA、未讀真實媒體、未新推論、未commit/push**。沒有自動新增後續工程階段。
