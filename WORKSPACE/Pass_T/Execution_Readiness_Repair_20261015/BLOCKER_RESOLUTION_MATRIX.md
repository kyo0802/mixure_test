# Blocker Resolution Matrix

Task `PASS_T_PHASE2B_QWEN_NF4_EXECUTION_READINESS_REPAIR`；2026-10-15。**ENGINEERING_READY_FOR_HUMAN_FREEZE_REVIEW**。

| Blocker | Responsible interface | Repair | CPU verification | Remaining scope |
| --- | --- | --- | --- | --- |
| A / T01 | video_array_bridge.prepare_video_array + v1d_protocol.bridge_eligibility | 新增real_pilot_mode=FROZEN_V1D_PILOT_V1；驗frozen/21decision approval/獨立執行授權、V1D/V2/schema/runtime/bridge hashes及call/alias/PTS；保留synthetic原guard | 缺freeze、缺授權、hash/rep/alias/PTS/prompt/system/預算/洩漏遭改均拒絕；MOCK records在真正preprocessor之前拒絕 | 真實array/processor/GPU仍未執行；8source→4unit、FRAME_MATCHED_ONLY不變 |
| B / T02 | v1d_protocol + v1d_execution + explicit CLI | 獨立versioned draft/freeze/run介面；三格式in-process共18call；不走legacy prompt_path/HTTP/AVI fallback；21項仍PENDING | 真實metadata dry-run成功；18call軟體mock一個runtime factory；授權nonce lease與call claim防重播；預設CLI不執行 | 未建立human-approved frozen protocol；currentmedia與weights未驗證 |
| C / T04 | evaluation.match_known_events / CLOSED_INTERVAL_GAP_V1 | 版本化closed-interval gap；historical default LEGACY_OVERLAP_V0仍原行為 | 點內/端點/前後/overlap/touch/disjoint/zero-width；0/.2/.5邊界與一對一、unknown/缺時/關聯不確定測試通過 | 這是待核准candidate semantics，不是已核准科學決策 |
| Strict output / T03 | v1d_outputs + record_call_result/evaluate_recorded_call | 原raw durable/exclusive保存，5stage分開，schema early return標NOT_ASSESSED；invalid與缺結果不得進matching；定性另存 | invalid/schema/semantic/citation/absent/有效NO_EVENT分支；mock18call中2invalid仍保留並繼續；nonexhaustive額外預測UNEVALUATED | 不宣稱schema/temporal match證明physical correctness |
| Media / M01 | draft_protocol/validate_draft/load_envelope | pin來源metadata、全authorized-list SHA/boundary、Uniform8、8alias/nativePTS及sourcePNG/storyboard hashes；執行時先授權再開檔驗bytes | 現有文字metadata一致性核對；未授權loader在任何媒體開檔前拒絕；mock receipt綁protocol/auth/source | PENDING_AUTHORIZED_EXECUTION；本次沒有重新hash/read真實媒體或原始source video |


工程完成不等於protocol approval、freeze、real execution或科學驗證。歷史review package未修改。新source manifest和draft取代舊候選的runtime hash適用性；舊核准識別句不可機械沿用。
