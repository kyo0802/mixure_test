# FindMind — Frozen Validation Handoff

狀態：**READY_TO_FREEZE_FOR_VALIDATION**。本檔是預先凍結規格；沒有讀取validation filenames、metadata、thumbnail或影格，沒有跑validation。

## Model / environment

Qwen/Qwen2.5-VL-7B-Instruct；revision`cc594898137f460bfe9f0759e9844b3ce807cfb5`；本地`.models/Qwen2.5-VL-7B-Instruct`；NF4 double/BF16；torch 2.10.0+cu128、transformers 4.57.6、bitsandbytes 0.50.2、SDPA cuDNN preferred/MATH fallback。原 checkpoint hash 證據見 `outputs/reference_qwen/checkpoint_verification.json`。Greedy/max_new_tokens 1400/timeout 120s/800px image，各 frame composite 800×600；不可在看 validation 後調分辨率/量化/frames。

## Prompt / contract

七欄：event_type、interaction_anchor、released、target_visible_after、final_relation、final_relation_anchor、confidence。No frame citation/geometry questions/examples。只在原cleanprompt增加actor/locationrole宣告。Exact current prompts在`qwen/requests.json`；template/schema的hash如下。不能把BEFORE/DURING/AFTERphase當actiontruth。

## Builder parameters

| 全域參數 | 值 |
|---|---:|
| `stable_pre_seconds` | 0.7 |
| `stable_post_seconds` | 1.0 |
| `min_seconds` | 2.0 |
| `preferred_seconds` | 3.5 |
| `max_seconds` | 6.0 |
| `max_observation_gap_seconds` | 0.4 |
| `motion_speed_image_diagonals_per_second` | 0.04 |
| `velocity_interval_seconds` | 0.2 |
| `smoothing_seconds` | 0.4 |
| `state_dwell_seconds` | 0.3 |
| `dense_frame_fps` | 5.0 |
| `physical_budget_per_video` | 4 |
| `lifecycle_budget_per_video` | 6 |
| `max_actor_candidates` | 2 |
| `max_location_candidates` | 3 |

Builder initialconfiguration只有一組，globalcorrections0。1個runtimeSDPA修正記於`cleanup/runtime_correction.json`，不更改windowboundaries。時基來自明確授權manifest，不硬編framecount。

## Identity / actor / location policy

Re-IDsimilarity .60、best-secondmargin .10；IdentityGuard、PersistentEntity、YOLO、SAM2.1、bank、trust/searchpolicy保持原hash。T只能是當frame授權observation，不追認untrustedphone、不用futureframes選phone_01。Actor只原person/hand/arm/carrier，其他detectorclasses做locationcandidate；無actor允許NONE。最多2actors/3locations；location誤分類/alias需原樣記錄，不能看validation後手動換正確anchor。

## Selection / completeness

物理/lifecyclequeues獨立budget4/6。對motion/stability/visibilitypattern deterministictrigger，後向/前向找stablePRE/POST；chain、gap、durationgate通過才COMPLETE。Physicalreasoning只送COMPLETE，INCOMPLETE保留診斷。NoGT/VLM選窗。Denseordered5fps+boundaries/trigger，絕不跨界補frame；沒有per-videotuning，不能強迫沒有trigger的影片生成動作窗口。

## Validator / memory policy

StrictwholeJSONparser、exact7fields/enums、suppliedmarkercheck、minimalconsistencyvalidator，無geometryreasoner。Validatorpass不等於真實物理正確。VLMidentitywrites0；現在memorymapping只offlineengineeringreview，realrelation+SUPPORTED+safe-material才能simulatepromotion，wrong/unsafe/invalidreject；沒有actualtrustedwrites。不得用validationreviewlabels作operationalidentityauthority。

## Evaluation plan / denominators

先freezeboundaries/selection/requests/responses/parsed/deterministicmetrics，再獨立視覺review；不要修改prediction。報selected/complete/incomplete、全片有無physicaltrigger、PRE/transition/POSTvisualcomplete、actor/locationavailability、revieweligible、可檢查lowering/release與confirmedrelease分開、uniqueepisode與pack數分開。沒有全片independentGT不可報recall。逐欄可決denominator，不可決單列；invalid/schemafail仍計入calleddenominator。ALL與eligible分層都報event/actor/release/visibility/relation/anchor、unsafephysical、safe-searchablememory、actualwritecount、runtimeglobalVRAM。評估taxonomy保持原14類。Developmentreview是執行代理，正式validation宜獨立humanreview，避免把這次review當GTfeed回模型。

## Reference and reproducibility

V293419frozenfiles、compactQwenreference73files、primary330files、same-runtimebaseline5files與sourcehash核對。完整releaseepisode目前只有2次development，事件type偏STATIC與selflocationcontext是既知限制；下一個科學步驟為固定architectureheld-out測量，不在此要求perfectaccuracy或繼續調development。

| 檔案 | SHA256 |
|---|---|
| `src/memory_graph/reasoning/baseline_contract.py` | `de1e79370aa83392dd45a4f4def9319c6b27e531fcfad14bc3dba4d89e614c66` |
| `src/memory_graph/reasoning/common.py` | `9c99792f783775feb2dd7851edcda7a65e2f9c1cbea7068e83c00fecf349d8f4` |
| `src/memory_graph/reasoning/contract.py` | `0d7f71e3a8f74c14b07240de98a1748cab73950249bb077ad089cc2b28127be6` |
| `src/memory_graph/reasoning/evaluation.py` | `807da048b2ad9d2c3a45613433993ce49ecbab63bf8164d2f7fad6c9b1721b23` |
| `src/memory_graph/reasoning/json_contract.py` | `0cc237a6d632b565a5ab85cbbb28eab0b2ebd265da20f2020217d7cbcfdc8936` |
| `src/memory_graph/reasoning/model.py` | `607246d1ecad483ee972b95a378019cdee8339eb6eae4ac8b0695e44575a17e7` |
| `src/memory_graph/reasoning/pipeline.py` | `2992e71a6e8660ad5e6076d15be3c8bac3d42fa6df684ec27bd5adfb511d1316` |
| `src/memory_graph/reasoning/validator.py` | `fd8dac2d54e1c0cae31528cd276f5e482630560ec392e3a1731c2a885a26e79a` |
| `src/memory_graph/reasoning/__init__.py` | `5ce49fff2f38b04c173e0b300388a283398112a02b147cab65b5677d13f86a14` |
| `src/memory_graph/events/window_builder.py` | `2de9411a4cde50039aca0e0e6e0f56232d568e571933fd80f37023897ba6bcda` |
| `src/memory_graph/events/development_sources.py` | `33176d723d49422e0d4bbc9411749fa9cba236865b9a8cf0716f2c62acdea030` |
| `scripts/run_current_pipeline.py` | `3bb147307fb08148d386166bdbde34fb807fa8290bdfd3b2eb91930b1d6f6e6e` |
| `scripts/run_development_eval.py` | `391cf6d50eb0ff5f8d9e8d25e13aa0feaff365ec499c87bd6d7b878c04b994cb` |
| `scripts/run_baseline_same_runtime.py` | `cef9ec4d7f652f1fdd6221603110c2975b39d4834805f4f1678248379f54a69b` |

Exactfinalartifact/reporthash見`final/final_integrity_manifest.json`與`final_integrity_verification.json`；相鄰`mixure_test`不作此pipeline工作區。
