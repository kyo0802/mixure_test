# 18-call regression前瞻草案

**DRAFT_NOT_APPROVED_NOT_EXECUTED**。任何實際執行仍需另行明確授權。沒有GPU call或model load。

Variant A：6鎖定evaluationfixtures×3表示法=18，repeatindex0；intended stratum不強制模型輸出。Video CPU均FRAME_MATCHED_ONLY，且native-array尚未接入原V3 transport，所以目前Video arm阻擋；需要明確接受frame-matched-only、時間/alias粒度，以及獨立review nativearray runtime route，不能把CPU通過當原runtime可直接執行。

Variant B：另列6×Multi/Storyboard=12calls，見regression_preregistration.json獨立order；不是自動fallback，須人工選定才能啟動。不能將12個有利結果與未核准Video合併充作18。

Warmup用獨立fixture `X_0009ab2fbef22158`，若啟用，每表示法一次=3額外calls，不評分，不用evaluationfixtures暖機。repeatability另2固定conditions×2extra同設定repeats=4calls，primary之後執行；condition由已公布order前兩項決定，不按event answers選。若選Variant B，需另固定其repeatconditions，不偷偷沿用不可用Video條件。若完整Variant A+warmup+repeat獲批准，明確總上限25calls（18+3+4），不是暗中把warmup算進18。僅批准18不自動授權額外7。

排序：sha256(QWEN_NF4_HOLDOUT_ORDER_REV2/opaque_fixture/representation/repeat_index)，固定無隨機抽樣；模型seed42與runorder無關。先公布order/hash，不能按輸出重排。

| Order | Opaque fixture | Representation | Order hash |
|---|---|---|---|
| 1 | X_1c1b2f1aa6ae3ac2 | MULTI_IMAGE_8 | 0fe0c0dc822d8d411e5bb16395fcbc323b9045bbe0a0c0eaa8f3270f5461eca8 |
| 2 | X_6a46f3734a47a8a3 | MULTI_IMAGE_8 | 20259bc5edfdfff8b32549d9a4ff60363135e839dcb5e6ab09b45f48465092e4 |
| 3 | X_abef8149c15bfb7e | VIDEO_MATCHED_8 | 3ccee316c6cd3d17c2f77cef968e10b82dd84cbea91d93262934b911400de112 |
| 4 | X_1de7663247196813 | VIDEO_MATCHED_8 | 4393878e7e9d9b7e903d51ba75e7453af17eff72a1b50fef9eda47dd371f1319 |
| 5 | X_1de7663247196813 | MULTI_IMAGE_8 | 4b646331a87ac97a398391f71c4c5514db45813211078bedd70bb1a44637bcf0 |
| 6 | X_9466c22b82dad731 | MULTI_IMAGE_8 | 4db7e016780cd1a208b9ea5ee297da293e289e2309c85d4ce174f07fa336d9d1 |
| 7 | X_9466c22b82dad731 | VIDEO_MATCHED_8 | 5f49e0960503772334308b8857f51dd57b1c31dabd42ff2b25faffcf19554458 |
| 8 | X_1c1b2f1aa6ae3ac2 | VIDEO_MATCHED_8 | 60aec26e6ff6881ced900bd4c0afda7cc6a2ea1bb36fb80856266aa8e98c5234 |
| 9 | X_1c1b2f1aa6ae3ac2 | STORYBOARD_8 | 64bf984bee4f68c3bbc72eaf5e2812088727e664238aa7b6e83a65c3f1f5669f |
| 10 | X_6a46f3734a47a8a3 | STORYBOARD_8 | 81770b7003b1415a779dfc91c2f02b470564f7bfe8b0285a8c6b3278aa2e8aab |
| 11 | X_685180893dee1e85 | VIDEO_MATCHED_8 | b246862abc4cb33b63e9fdbfef686fef5e97df0976dd3104b8bd5e91ad65fd77 |
| 12 | X_685180893dee1e85 | MULTI_IMAGE_8 | b97667b7e16ea59a8e1eea619e71e4a5ada7e157d1a1d80e5bc7cb85870a24e4 |
| 13 | X_1de7663247196813 | STORYBOARD_8 | cea1ad802048e22ce4916ab017a1755e34d5bf9c664864f9f48f6c29d7a330c7 |
| 14 | X_abef8149c15bfb7e | MULTI_IMAGE_8 | d377cd2a2c2d7346632a792ed86aa3c1db73826a32a09fac8425797551bfb947 |
| 15 | X_6a46f3734a47a8a3 | VIDEO_MATCHED_8 | d98c7c0fbf2268b579e903c1f7171a387bd3440fe7c5e0c039860883a860215d |
| 16 | X_9466c22b82dad731 | STORYBOARD_8 | e243b918e5d308c198252974fe013113beed85a594d8574984c45d48c39222ea |
| 17 | X_abef8149c15bfb7e | STORYBOARD_8 | f1c4806c343630034647493526519f1829a8de159d82c4f7a0aa743dce0defe6 |
| 18 | X_685180893dee1e85 | STORYBOARD_8 | f7faac9ac3c10a4dec55229736d43a1daa4b7f1bcb7c8a33cba1c738d0a6014a |

工程接受：所有18輸出均須通過完整authoritative strict parser、schema、semantic、citation。分階段報，不能用schema pass掩蓋known-state問題。每表示法6份中至少2份event-bearing且至少1份known-state support適用，合併至少6/18event-bearing；這是branchcoverage提案，不是eventtruth要求。報intendedstrata（private）、emittedcounts、event-bearing和zero-event各strictvalidity、abstention以及knownstate是否被測到。覆蓋不足→EVENT_BEARING_BRANCH_NOT_EXERCISED，不能說原缺陷解決。forcedbranch另決策，不能製造事件。

Verdicts：REGRESSION_PASS=全部valid且coverage達標；STRUCTURAL_PASS_COVERAGE_INSUFFICIENT=全部valid但coverage不足；REGRESSION_FAIL=任一已完成輸出strict/runtime失敗；REGRESSION_INCOMPLETE=必要calls缺少，另列已知failure，不隱藏未完成。Variant B為12call独立variant，其每rep2/6、knownstate1/6和pooled4/12 coverage須在選B時獨立批准；不得套用18call的pooled6而不說明。

凍結待批准的componentmanifest：model revision/localassetmanifest、NF4、V2system、V1Cprompt、PredictionV1、validator、runtime/backend、model-visiblepayloadcontract、fixturesmanifest、repconfig、processorconfig、alias/native/modeltime mapping、order、generation和retry policy，各別hash。當前component/hash見prompt_candidate/receipt、processor_source_inventory、regression_preregistration與DELIVERABLE_MANIFEST；未整合的native-array bridge與尚未批准的條款不能產生假的finalruntime hash。

負面結果原raw/resource/開始邊界/EOS/token/partialfailure均保留。generationretry0；infra最多1且generation未開始有證據，不能按結果重試。OOM不自動降pixel/frame、不換模型；timeout不依答案增deadline；invalidJSON/citation不修補、不當作no-event。fixedgreedy/seed不保證bitwise重複，repeat是工程重現性不是獨立session。

本任務只一個candidate；未來失敗保留並回humanreview，最多再一個另批、另版本candidate，沒有自動迭代。沒有full-schema答案examples。測試是engineering，不是event detection、precision/recall/F1/hallucination測量或泛化/顯著/因果證據。

Timing敏感度0/.2/.5全報、point/interval/uncertainstatusaware一對一matching在realDEV仍待獨立批准；syntheticstrata只是designerintention，這個regression不grade physicaleventtruth。
