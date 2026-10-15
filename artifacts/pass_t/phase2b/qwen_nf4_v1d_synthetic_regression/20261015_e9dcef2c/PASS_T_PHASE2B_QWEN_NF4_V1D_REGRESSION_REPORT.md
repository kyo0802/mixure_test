# Qwen NF4 V1D 八次 synthetic regression 報告

更新：2026-10-15。**REGRESSION_FAIL**；完整 strict **1/8**；實際 event-bearing **6/8**（門檻3）。完成8/8，JSON syntax 8/8。

## 1 唯一候選與欄位

全局欄位確定為根物件 **`/uncertainty`**，required/non-null/string/minLength1；歷史6份錯誤的raw、schema paths與Validator逐項核對。`/events/*/timing_uncertainty`每個event必填；`/window_cited_frame_aliases`四種outcome皆minItems1、無例外。沒有改schema／parser／Validator。

V1C SHA `3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722`；V1D SHA **`7008254e618dc8bacdbdeaae3cbf471220afb5efd6c80afc8b9ea5fb5c96b9b0`**。只增加三段說明（timing證據、root uncertainty、processor-consumed window citations），added4行含空白、removed0；原V1C每個byte保留，UTF8/LF不變。Task tokens659→871。沒有JSON答案例、scenario-specific alias/position/time、ready-to-copy uncertainty答案或新target policy。完整diff在 [V1C_TO_V1D_UNIFIED_DIFF.patch](V1C_TO_V1D_UNIFIED_DIFF.patch)，審查在 [V1D_PROMPT_CHANGE_REVIEW.md](V1D_PROMPT_CHANGE_REVIEW.md)。

## 2 新fixture與執行前鎖定

8全新獨立seed情境、64張1280x720 RGB sourceframes，Multi3/Story3/Video2，scenario intent只在private metadata，非物理GT。未讀舊／real影像，非從Phase2a事件時間設計。模型只收到PNG/ndarray和opaquealiases，沒有intent、source ID、GT或tracking資料。Fixture lock SHA **`2e2f3e3afdcf2ae4244fdef12801db6c6bcf5457324f53b4a0108a02c5a2784f`**，早於V1D作者回條；fixed interleaving與allasset hashes見 [V1D_SYNTHETIC_FIXTURE_MANIFEST.json](V1D_SYNTHETIC_FIXTURE_MANIFEST.json)。

執行 manifest SHA **`f4a91abc2c43a8c8247c784a7b6d861aeba6e453e17381e79d75515101673c60`**，criteria與manifest在model load／generation前鎖定；[EXECUTION_LOCK_RECEIPT.json](EXECUTION_LOCK_RECEIPT.json)／[V1D_PREREGISTERED_CRITERIA.md](V1D_PREREGISTERED_CRITERIA.md)。CPU64/64，無CUDA初始化。沒有warmup／repeat／quality retry，8條件固定順序，batch1，1024greedyseed42，generation300s，load120/request330s。

## 3 實測結果

| 條件 | 表示法 | Strict | 實際event數 | 秒 |
|---|---|---|---|---|
| C01 | MULTI_IMAGE | False | 0 | 61.15 |
| C06 | STORYBOARD | False | 2 | 155.54 |
| C08 | NATIVE_VIDEO_ARRAY | False | 1 | 98.64 |
| C03 | MULTI_IMAGE | False | 1 | 50.39 |
| C04 | STORYBOARD | False | 2 | 12.37 |
| C07 | NATIVE_VIDEO_ARRAY | True | 0 | 5.65 |
| C02 | MULTI_IMAGE | False | 1 | 8.52 |
| C05 | STORYBOARD | False | 2 | 12.41 |


三項targeted violations（entries）={'event_timing_entries': 9, 'global_uncertainty': 6, 'window_citations': 1}；affected attempts={'event_timing_entries': 6, 'global_uncertainty': 6, 'window_citations': 1}；所有其他違規={'EMPTY_WINDOW_CITATIONS': 1, 'EMPTY_TIMING_UNCERTAINTY': 6, 'SCHEMA_MINLENGTH': 6}。Coverage達標=True。完整uncertainty原字串／windowcitations／known-state shadow checks／raw links在 [V1D_STRUCTURED_VALIDATION_REPORT.md](V1D_STRUCTURED_VALIDATION_REPORT.md)，全8條件機讀 [V1D_REGRESSION_ATTEMPTS.jsonl](V1D_REGRESSION_ATTEMPTS.jsonl)／[CSV](V1D_REGRESSION_ATTEMPTS.csv)。未修補任何生成輸出，未用失敗JSON當no-event。

全部event timing explanation正規化後相同警告=True（9個event entries，1種）。長verbatim overlap門檻12連續詞，intended/emitted不一致、known-state掩蓋問題及視覺precision/continuity/citation限制見 [V1D_WARNING_REVIEW.json](V1D_WARNING_REVIEW.json)。需要visual judgment的項目保留UNREVIEWED，不推定全部無問題，不以renderer intent當accuracy GT，也不自動覆寫regression分類。

## 4 Runtime／資源與修正

既有Qwen2.5-VL7B原revision cc594898137f460bfe9f0759e9844b3ce807cfb5、NF4double4bit/BF16/SDPA，一個localmodel。Video只於2個指定條件啟用nativearray，其餘OFF；8frames→4units，仍FRAME_MATCHED_ONLY，沒有新citation syntax／完整nativePTS／8獨立時間位置／equal-information聲稱。

唯一runtime修正是Bridge的V1C-only pin擋住V1D，改成explicit pinned synthetic V1D設定，V1C預設保留；原failure [BRIDGE_PIN_BLOCKER.json](BRIDGE_PIN_BLOCKER.json)、exactsource diff [BRIDGE_V1D_PIN_REPAIR.patch](BRIDGE_V1D_PIN_REPAIR.patch)。Shared NF4 generation不變。GPU recovery0，未按答案改prompt／設定。Pre-lock technical checker與Windows path normalization說明另存，不改已鎖fixture。

Model load=23.780862699999943秒；總generation=404.66026130000023秒；supervisorwall=450.6099999999999秒。PyTorch allocatedpeak=6.316991329193115GiB，reservedpeak=6.865234375GiB；globalGPU觀測peak=8444.0MiB；ownedtreeCPU RSS觀測peak=4.4870147705078125GiB。Resource stop=None，workerexit=0。詳 [V1D_RESOURCE_REPORT.md](V1D_RESOURCE_REPORT.md)，allocator／samplingscope分開，不聲稱穩態benchmark。

## 5 保存與解讀

Guard補充：[GUARD_EVENT_DISCLOSURE.md](GUARD_EVENT_DISCLOSURE.md)。Worker記錄1次被阻擋的socket.bind（通用標籤SERVER_STARTUP），不是已啟動VLM server的證據；未記錄caller stack，來源／目的不作推測。沒有old/real-media或network-connect denial，73個讀取路徑均為本次新media（部分只做hash）。8次local生成正常完成，不改guard或增加推論。Finalization原先「所有denial皆為0」的過度假設已修正，保留此事件並揭露，非忽略。

[V1D_SOURCE_PRESERVATION_REPORT.md](V1D_SOURCE_PRESERVATION_REPORT.md)／[V1D_PRESERVATION.json](V1D_PRESERVATION.json)：原V1C、schema、Validator、parser、V2、evaluator與舊報告／raw不變；15modelassets前後核對。唯一existing-source變更為預先記錄的bridgepinextension。GitHEAD/index/staged不變，worktree有授權新增與修改，未reset/clean。沒有realDEV或舊影像讀取／realPhase2a prediction／actualPhase2bPilot／GT修改／MemoryGraph／ProtocolFreeze／commit/push。

這是after-V1C-failures的adaptive development，新8fixturepopulation不能拿V1C2/12與本結果當受控改善，亦非物理事件accuracy／recall／precision／F1／hallucinationrate／泛化／統計可靠度。

## 6 下一個人工gate

**目前不建議進入 final Pilot protocol freeze。** 六份event-bearing輸出都未通過strict；唯一通過的是native Video零事件條件。9個event timing_uncertainty全部是空字串，因此「normalized相同」警告與既有必填失敗同源，不代表有意義的說明文字。全局uncertainty同樣仍有6份空字串，不能宣稱已解決。

特別注意R05_C04：renderer intendedzero，八張source RGB hashes相同，model卻產生2個events。這是已記錄的intended/emitted差異與可追溯的像素事實，值得人工檢視transition／citation證據；不是經人工physicalGT adjudication的false-positive統計。其他需要visual judgment的警告保留UNREVIEWED，沒有假稱全部通過。

| 重要component | SHA-256 |
|---|---|
| 原Bridge（已保存） | `318febec583338626203d15f64fac55190e4a8133e0120b5dbea23d6d148db6f` |
| V1D explicit pin Bridge | `5cfebb8d93294585cc62531258fba79f2d5abc2cb57e0f1ba1e108664288ed4e` |
| Shared NF4 runtime（未變） | `fc15d9012a3a992e4dcb9e66a3b458b242c319b1efe5f4d30dae19b81364547b` |
| Validator＋parser來源（未變） | `c4b077374d50fc478c29d0009180d488c60a463fa8bffa183a179c5f736f1d37` |
| Prediction V1（未變） | `f8b0dfb6c62301baabff5e1adfddf14dc6be9381aa84c884fc70f5318abcedc3` |
| V2 formatting（未變） | `9b76b7e320dfb677a1cb8566c16dff15785759bc4915375123bc12dd118fd08e` |

V1D技術上可作finalPilot候選交人工審閱=False；**尚未批准為DEV finalprompt**。仍需citationC1/C2/C3、identityclause與referenceNONE、time matching／sensitivity、pixel/generation/retry/failure政策與finalcomponenthashes，再各別人工ProtocolFreeze及actualPilot授權。詳 [V1D_HUMAN_PILOT_DECISION_PACKAGE.md](V1D_HUMAN_PILOT_DECISION_PACKAGE.md)。

本次停止；不建立V1E、不加call、不改fixture／V1D、不跑DEV。Phase2b未宣告完成。
