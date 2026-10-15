# Qwen NF4 Engineering Closeout 報告

更新：2026-10-15。最新任務取代未完成 Track1，依新授權完成獨立 engineering closeout。未把中斷的 Track1當成成功結果。

## 1 結果

- Native Video Array engineering smoke：True；實際 smoke attempts=1；nonempty=True；strict-valid=True。
- Variant B：12/12 完成，完整 strict通過 2/12，結果 **REGRESSION_FAIL**。
- Event-bearing 9/12，event-bearing strict通過 0；known-state applicable 12/12；coverage足夠=True。
- CPU 89/89 unique checks；6個負面assertions覆核重跑，不另加unique count。7原有synthetic fixtures(6eval+1warmup)，5video tensors逐值一致，12個B原pixel/rendered一致。沒有讀real DEV影像。
- Warning：['STRICT_PASS_BELOW_10_OF_12', 'VIOLATION_IN_3_OR_MORE:EMPTY_TIMING_UNCERTAINTY', 'VIOLATION_IN_3_OR_MORE:SCHEMA_MINLENGTH']。

## 2 實作與 runtime 範圍

新增 `src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py`；只在 NF4 preprocess加明確 default-disabled分支。歷史AVI/image程式保持預設行為，原source bytes與diff封存。使用同一shared generate_common/structuredoutput，沒有第二loader/evaluator/schema、沒有server或HTTPtransport redesign。Bridge本次經同一實際NF4 runtime的本機in-process路徑執行；現行HTTPtransport不接收ndarray，不宣稱HTTP/nativearray也驗證過。B feature flag全OFF，一個model instance，無額外warmup/repeat/retry。

## 3 固定 authority 與執行前鎖定

Model Qwen/Qwen2.5-VL-7B-Instruct、revisioncc594898137f460bfe9f0759e9844b3ce807cfb5、NF4double4bit BF16 SDPA；本機權重逐檔核對既有assetmanifest，非新的upstream checksum attestation。

V1C SHA `3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722`，APPROVED_FOR_SYNTHETIC_REGRESSION_CANDIDATE_ONLY；identityclause NOT_APPROVED_NOT_ENABLED。Lock receipt SHA `149f8696e51fa91cf43147d761315672dc43594aebe41b58cea8ed78956346ee`，與content_id ecc283...及fixture manifest SHA7e03...是不同概念，未混用。

執行前 immutable [preregistered_criteria.md](preregistered_criteria.md)、[run_manifest.json](run_manifest.json)、[PREREGISTRATION_LOCK_RECEIPT.json](PREREGISTRATION_LOCK_RECEIPT.json)；root criteria path `docs/preregistered_criteria.md`。Manifest SHA `d59da5a0bcf9187842c5037574e588af710134d894fd5b7e088e56d484bfc256`。確切B原順序、source/model/assets/processor/fixture/format/schema/Validator hashes全部保留；無觀察答案後調參。

## 4 分階段 strict 與 violations

| 檢查 | 通過 / 12 | 解讀 |
|---|---|---|
| JSON syntax | 12 | 全部能由原strict parser讀取 |
| Prediction V1 schema | 2 | 10份有必填空字串或空清單 |
| Semantic predicates（獨立診斷） | 12 | 不可抵消schema failure |
| Citation membership（獨立診斷） | 12 | 不代表空window citation符合schema |
| 完整 authoritative strict | **2** | 本次regression判定依此門檻 |

None表示not-evaluable，非PASS。authoritative strict Validator unchanged；它的early-return不被改寫，stage影子診斷不另計分。

Violation distinct-attempt counts：{'EMPTY_TIMING_UNCERTAINTY': 9, 'SCHEMA_MINLENGTH': 6, 'EMPTY_WINDOW_CITATIONS': 1}。每個item原raw、started、runtime、completion/validation receipts在runs/；[VARIANT_B_ATTEMPTS.csv](VARIANT_B_ATTEMPTS.csv)、[VARIANT_B_ATTEMPTS.jsonl](VARIANT_B_ATTEMPTS.jsonl)有完整12列與失敗案例。

| 表示法 | 完成 | Strict pass | Event-bearing | Known-state適用 |
|---|---|---|---|---|
| Multi-image 8 | 6/6 | 0/6 | 5/6 | 6/6 |
| Storyboard 8 | 6/6 | 2/6 | 4/6 | 6/6 |

B coverage沿原Markdown每rep2/6event-bearing、1/6knownstate、pooled4/12；未誤套A6/18。原intendedstrata只是designer intention，不強制模型答案、不算physicalGTaccuracy。9份event-bearing全部未通過strict；2份通過都是zero-event。12份known-state support診斷有引用支持，不等於已驗證物理狀態為真。

## 5 時間與 citation

Video8 source→4units，FRAME_MATCHED_ONLY。Source/native、uniformframe、processorunit、staticmodeltime分開列於cpu/video_*.json。Installed get_rope_index先把second_per_grid轉range_tensor.int64再乘tokens_per_second2；前次浮點簡化proxy的限制已在 [TEMPORAL_MAPPING_LIMITATIONS.md](TEMPORAL_MAPPING_LIMITATIONS.md)揭露，舊報告不改。GPUforward/generation成功不證明逐frame attention或實際absolutepositionIDs；未instrument實際position_ids。

[VIDEO_CITATION_OPTIONS.md](VIDEO_CITATION_OPTIONS.md)保留C1原Falias、C2unitcitations設計、C3Falias加unitspan disclosure，尚未選定。Smoke沿原Validator membership；沒有修改predictioncitation syntax／評分。

## 6 資源與 latency

Model load：26.621696699992754秒。
Smoke generation：73.50221240000974秒；allocatedpeak=6.123626232147217GiB，reservedpeak=6.85546875GiB。
B每次generationseconds=[152.4841854999977, 17.514077799991355, 14.778159899986349, 4.690676500002155, 168.20804539999517, 12.646636600009515, 8.35362019999593, 5.489783800003352, 15.907787999996799, 5.434093299991218, 12.405298099998618, 12.401915499998722]；合計430.3142805999669秒，allocatedpeak=6.277605056762695GiB，reservedpeak=6.865234375GiB。
全程global GPU觀測peak=8543.0MiB，ownedtreeRSS觀測peak=4.604450225830078GiB；supervisorwall=554.0469999999914秒。觀測samples不是continuous/global精確peak；PyTorchallocatorpeak另列，不混為同一量。完整 [RESOURCE_SUMMARY.json](RESOURCE_SUMMARY.json)、[SUPERVISOR_RECEIPT.json](SUPERVISOR_RECEIPT.json)。

## 7 保存與限制

[SOURCE_PRESERVATION.md](SOURCE_PRESERVATION.md)／[SOURCE_PRESERVATION.json](SOURCE_PRESERVATION.json)／[runtime_changes.diff](runtime_changes.diff)。169個baseline非DEV影像source/artifact、全lockedsyntheticpixels與executionmanifest核對；只有授權的NF4 branch改動，其餘protected unchanged。GitHEAD/index/staged保持原樣，worktree因授權變更而改動。沒有為hash驗證讀DEVimage。沒有realPhase2a inference、GT改動、Graphwrite、ProtocolFreeze、commit/push。

不能將15/33capacity與本12call當可比較improvement estimates：population/technicalconditions不同。沒有三表示法equal-information控制聲稱，未驗證real-world event accuracy。這次只有Video integration smoke，不是VariantA Video regression。

## 8 下一步

**本次工程執行完成，但 regression 未通過，不建議目前凍結第一個 Pilot protocol。** 首先人工審閱 strict failures，決定後續如何處理 contract；本任務不修改 prompt、Validator 或再開實驗。

補充警告：9份輸出共17個 event timing_uncertainty 空字串；6份全局 uncertainty 空字串；1份 window_cited_frame_aliases 空清單。另列 temporal-uncertainty 與 window-citation evidence 警告。CITATION_PASS=12 是獨立 membership 診斷，不表示那份空 window citation 滿足 schema 或提供足夠窗口證據；SEMANTIC_PASS=12 也不能覆蓋10份 schema 失敗。所有12份有EOS，沒有output cap/deadline截斷。

前兩個對應表示法的首次 latency 較大（Multi152.48秒、Storyboard168.21秒），其餘B4.69–17.51秒。本次沒有額外warmup；不把首次／後續時間混為穩態benchmark。保留checkpoint inactive temperature警告（實際greedy kwargs未傳temperature）及bitsandbytes alignment慢速kernel警告，沒有因此改設定。

### 本次 source SHA-256

| Component | SHA-256 |
|---|---|
| Video Array Bridge | `318febec583338626203d15f64fac55190e4a8133e0120b5dbea23d6d148db6f` |
| 原始 NF4 runtime（raw bytes保存） | `366a6d80b511c6e1a59ff79a45f38ac5c81b1a8ad6a5c3f06118bf9754580881` |
| 啟用分支後 NF4 runtime | `fc15d9012a3a992e4dcb9e66a3b458b242c319b1efe5f4d30dae19b81364547b` |
| Strict Validator（未變） | `c4b077374d50fc478c29d0009180d488c60a463fa8bffa183a179c5f736f1d37` |
| Prediction V1（未變） | `f8b0dfb6c62301baabff5e1adfddf14dc6be9381aa84c884fc70f5318abcedc3` |
| V2 system formatting（未變） | `9b76b7e320dfb677a1cb8566c16dff15785759bc4915375123bc12dd118fd08e` |
| 執行前固定 criteria | `cdb995920b4e4a080c2c2d9beeb02e24f4592ae8de249dae57758b421618d906` |

完整 model assets、原始 runtime、source/config/fixture/criteria/order hash 與執行前鎖定時間見 run_manifest／PREREGISTRATION_LOCK_RECEIPT。補充的 post-run receipts 驗證模型權重、GT metadata 的執行後保存，以及 criteria lock 早於 model load／第一個generation；沒有為此讀 DEV 影像。

請閱讀 [QWEN_NF4_FINAL_PILOT_DECISION_PACKAGE.md](QWEN_NF4_FINAL_PILOT_DECISION_PACKAGE.md) 的16項決策。仍需finalDEVprompt/citation/identity/NONE/timing/budget/generation/retry/failure/hash選擇與人工protocolfreeze，實際DEVrun再獨立授權。Candidatefirstpilot18calls只提案，formal_eligible=0、CAUSALITY_UNVERIFIED，test3excluded，2nonexhaustiveknownPICKUP/3casealerts/1uncertain限制不變。

**本任務完成後停止。結果交給人工審閱，不自動改V1C、加call或啟動DEV。**
