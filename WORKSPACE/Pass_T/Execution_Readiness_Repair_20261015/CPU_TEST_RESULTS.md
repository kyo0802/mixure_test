# CPU-only Test Results

**53 tests passed；0 failures；0 errors；0 skipped。** 最終時間6.725秒（unittest回條）。沒有full repository suite。

Repository working directory：`C:\Users\smile\Desktop\test2\mixure_test_SAM`。

```powershell
.\.venv\Scripts\python.exe -B tests\test_pass_t_v1d_readiness.py
.\.venv\Scripts\python.exe -B scripts\run_pass_t_v1d_pilot.py dry-run --output WORKSPACE\Pass_T\Execution_Readiness_Repair_20261015\DRAFT_CONFIGURATION_CANDIDATE.json
```

另執行獨立CPU介面檢查：`python -B -c "import runpy,sys; runpy.run_path('scripts/run_pass_t_v1d_pilot.py',run_name='cpu_import_check'); import memory_graph.pass_t.phase2b.v1d_execution; print([n for n in ('torch','transformers','PIL','cv2') if n in sys.modules])"`；結果 `[]`，CLI local dependency integration OK。這是import/配置檢查，不是額外模型call；沒有將其與53個unit tests相加。最終草案亦由相同dry_run函式更新並驗過source hashes，見CPU_DRY_RUN_RECEIPT.json。

實際測試stdout/stderr另存 [cpu_tests_final.log](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/cpu_tests_final.log)；structured result [CPU_TEST_RESULTS.json](C:/Users/smile/Desktop/test2/mixure_test_SAM/WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/CPU_TEST_RESULTS.json)。log SHA `61a0ef423a4209a214e747ef8421831c526512ba80e07e74fc7f4530a75f3952`；result SHA `f4466de3d9571d89d059631e0f644376a7bb81e406a0fdc439d18a55ad166cf4`。

| Coverage | Verified result |
| --- | --- |
| Freeze/auth | 缺frozen、缺獨立auth、expiry/budget/call inventory/nonce/改hash/缺21decisions拒絕；未造人類批准 |
| Configuration/security | 三rep/六窗/18call、Uniform8/NONE、V1D/V2/model/schema/runtime/bridge pin；legacy或identity clause等變動拒絕 |
| Bridge | CPU eligibility 8→4 units；欠context與MOCK都在heavy imports前拒絕；alias/PTS/task/system/leak/generation變動拒絕 |
| Matcher | closed points/intervals各分支、0/.2/.5邊界、decimal邊界、一對一、unknown/缺時/關聯不確定與legacy復現 |
| Strict output | absent/malformed/schema/semantic/citation/validNO_EVENT分開；invalid不match；raw不修補；nonexhaustive extra UNEVALUATED；uncertain不當negative |
| Mock integration | 1個software runtime factory、18次mock calls；故意2invalid仍繼續，無模型/媒體，receipts綁protocol/source且明示MOCK_METADATA_ONLY |
| Replay/stops | exclusive authorization lease拒重播；not-started/no-output/incomplete-raw分開；hardware門檻以deterministic numbers驗 |
| Preservation | 原V1D 1/8與6event-bearing全invalid回條保持；140個protected檔案SHA不變 |


測試audit hook封鎖模型/像素library import、媒體/權重/raw real GT reads及socket；未發生任何guard denial，model_modules_loaded=[]、actual_model_calls=0、freeze writer未呼叫。mock事件與時間只測程式契約，不是physical GT，也沒有生成visual fixtures。

先前42/46測試是同一有界修補的早期run，不與最終53相加。最後53包含CLI輸出格式與mock不得進真實模型的回歸檢查；沒有optional full-suite擴張。
