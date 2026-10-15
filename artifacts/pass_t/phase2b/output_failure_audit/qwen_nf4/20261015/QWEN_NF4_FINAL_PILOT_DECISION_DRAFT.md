# 首次Qwen NF4 pilot決策草案

**PROPOSED_NOT_APPROVED_NOT_FROZEN；formal real pilot 0。**

| Decision | Verified evidence | Proposed choice | Alternatives | Remaining risk | Human approval |
|---|---|---|---|---|---|
| 01 Baseline | VERIFIED：歷史health/revision資產metadata | 原Qwen2.5-VL7B NF4 double/BF16/SDPA；revision cc594898137f460bfe9f0759e9844b3ce807cfb5 | 不換AWQ/3B | 只有local revision provenance；無官方獨立checksum | REQUIRES_APPROVAL |
| 02 Prompt/system | VERIFIED：V3 task/schema與V2system各1hash | 保留baseline，候選prompt另版本 | 原V3直接pilot | 13event全失敗 | REQUIRES_APPROVAL |
| 03 Repair | VERIFIED：13空timing、5空cite、11secondary | PROMPT_CHANGE_PROPOSED；V1schema維持 | 独立schema review若必要 | prompt改後branchcoverage未測 | REQUIRES_APPROVAL |
| 04 Frame count | VERIFIED：8frame各3/3pass | PROPOSED UNIFORM_8 | 12/16另sensitivity | passing均no-event，非準確度 | REQUIRES_APPROVAL |
| 05 Sampling | VERIFIED：existinguniform8 source inventory | round/endpoint/tie算法原樣 | fixedFPS另實驗 | coarse gap漏短事件 | REQUIRES_APPROVAL |
| 06 Video matched8 | VERIFIED synthetic8 indices0..7；DEV未建 | PROPOSED FFV1/AVI4fps8sourceframes | 維持UNRESOLVED，不替換fullclip | VIDEO_MATCHED_8_NOT_YET_VERIFIED | UNRESOLVED |
| 07 Storyboard | VERIFIED：3col/480×270+32 | PROPOSED 1440×906 canvas8frame | 其他layout另版 | 整張縮圖降低targetpixel | REQUIRES_APPROVAL |
| 08 Pixels | VERIFIED：200704有效上限 | PROPOSED common200704+actualgridreceipt | 高cap另pixelstudy | 不匹配各representation總token | REQUIRES_APPROVAL |
| 09 Reference | VERIFIED NONE已有offline六窗 | PROPOSED NONE commonprimary | 5-windowpaired另授權 | TARGET_A opaque≠localization | REQUIRES_APPROVAL |
| 10 Target ambiguity | VERIFIED I_E+uncertainty可表达 | PROPOSED unresolved target→INSUFFICIENT_EVIDENCE | 独立newschema若必要 | confirmed HIGH目前validator允許 | UNRESOLVED |
| 11 Fairness | VERIFIED 2016/240/1008tokens | matchedsource/time、部署條件描述比較 | 匹配token另protocol | 不能純representation因果聲稱 | REQUIRES_APPROVAL |
| 12 Output budget | VERIFIED max633/1024、无cap | PROPOSED 1024 | 另budgetstudy | 真實multi-event未驗證 | REQUIRES_APPROVAL |
| 13 Decoding | VERIFIED do_sample=false seed42 | PROPOSED greedy，inactive temperature/top-p | decoding另study | seed不保證determinism | REQUIRES_APPROVAL |
| 14 Repeat | VERIFIED repeatedsynthetic會變動 | PROPOSED 1 per DEV condition | 2repeat另stabilitystudy | 一次只表可能性 | REQUIRES_APPROVAL |
| 15 Deadlines | VERIFIED existingprobe generation300s | PROPOSED load120/gen300/request330 | 另budgetproposal | 18×330=99min不含load | REQUIRES_APPROVAL |
| 16 Retry | VERIFIED preservingfailedraw工具存在 | PROPOSED generation0、pre-generationinfra最多1 | 完全0infra retry | 開始判定/ownedPID證明須固定 | REQUIRES_APPROVAL |
| 17 Run order | VERIFIED deterministic proposed18list | PROPOSED SHA排序固定，不因結果改 | 另固定humanorder | modelsession順序可影響latency | REQUIRES_APPROVAL |
| 18 Tolerance | VERIFIED三敏感度已列草案 | PROPOSED全報0/.2/.5 | 獨立tasktolerance另提 | 沒有選最好或gap/2 | REQUIRES_APPROVAL |
| 19 GT time matching | VERIFIED status三種；現matcher有空隙 | PROPOSED status-aware最大一對一closedinterval | 保留UNRESOLVED直至CPU規則定稿 | Decimal/timebase、greedy與pointinside需修復審查 | UNRESOLVED |
| 20 Cohort | VERIFIED 6clean；test3excluded | PROPOSED固定6窗×3×1=18 | 不加test3 | DEVselected，session independence未知 | REQUIRES_APPROVAL |
| 21 Analysis | VERIFIED authority用途限制 | PROPOSEDknown-only/negativealerts/descriptive | 正式metrics禁止 | formaleligible0、CAUSALITY_UNVERIFIED | REQUIRES_APPROVAL |
| 22 Hashes | VERIFIEDhistoricalcapacity/authority | PROPOSEDfinalprompt/config/input/order全hash | 目前不freeze | finalcandidate與matchedvideoassets尚缺 | UNRESOLVED |
| 23 Regression | VERIFIED allreported-eventsfail | PROPOSED先候選preflight後18syntheticcalls | 無regression直接pilot風險高 | regression未批准/未執行 | REQUIRES_APPROVAL |
| 24 Freeze | VERIFIED humanapproval本task未給 | PROTOCOL_NOT_READY_TO_FREEZE | 補完後独立freeze任務 | 兩道human gate仍存在 | UNRESOLVED |

## 六窗用途

| Source | Item ID | Opaque ID | Native frames | Usage |
|---|---|---|---|---|
| test1 | PT2A_9d15d2a6b56b56d0 | W_5597d9b003977e053d70 | 107 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS |
| test5 | PT2A_fe0910d66f4c5614 | W_aef405003cc72cef0044 | 72 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS |
| test7 | PT2A_c58b4df88a2f6801 | W_b8a53fea6aa8b92dc94f | 107 | KNOWN_EVENT_MATCHING_ONLY |
| test8 | PT2A_5dbb180e8ff88762 | W_db55b29f820c2b3e3afb | 118 | DESCRIPTIVE_UNCERTAINTY_ONLY |
| test2 | PT2A_b35d807b28b92101 | W_ec4751640324779435e6 | 108 | STRICT_NEGATIVE_CASE_ALERT_ANALYSIS |
| test5 | PT2A_eb60192e6986cb4f | W_f1d4f821d33515975293 | 108 | KNOWN_EVENT_MATCHING_ONLY |

test1 W03/W05是同一窗已dedup、test2 W01、test5 W01只case-level false-event alerts；known-negative附加独立review仍不足，不可population FP率。test5 W05/test7 W05只人工已支持PICKUP conditional matching，額外event UNEVALUATED；test8 W07只uncertainty/abstention描述，不能binarytruth；test3 W07從inference/scoring排除。formal_benchmark_eligible=0，CAUSALITY_UNVERIFIED，沒有accuracy/precision/recall/F1/hallucination_rate/統計顯著或泛化宣稱。raw dataset須與sidecar合讀，不產生新GT。

## Sampling與表示法


UNIFORM_8使用現builders.uniform_positions：位置round(i*(N-1)/7)，Python ties-to-even，8個唯一位置、包含首末；不足8frame則阻擋，不dup補幀。不讀GT選frame，不改offset。所有source frame ids/native PTS/hashes/aliases在prospective_uniform8_inventory.json，現Multi/Storyboard六窗都同選8張。

VIDEO_MATCHED_8提案：把同一8張source畫面依序lossless FFV1/AVI編碼，4fps，encoded frame k時間k/4，8frames 0…1.75s；私有mapping保存每個k→original source frame index/native PTS/alias/hash。這是時間壓縮/非等距native時序再CFR編碼，不可把播放器秒數當source秒數。processor4fps官方sampling、實際observer必須取indices0…7，各2frame temporal grouping，grid temporal4；引用允許8個source aliases，exact citation只允許有直接可辨識證据，temporal merge不保证精確區分每張frame。native PTS可用於private evaluator，模型不得利用clip 0…1.75時長猜source timing。

既有VIDEO_SHORT8同source digests的技術實驗已證明這種4fps8frame模態可消費8個aliases；不是fullclip118frame=14consumer的替代。六個真實窗尚未有matched8建構/processor receipts，因此 `VIDEO_MATCHED_8_NOT_YET_VERIFIED`。現build_video會編所有source frames，不能只把fullclip條件改名字成matched8。後續需独立versionedbuilder/alias timestampmapping與CPUprocessor预flight；必要時新合成GPU確認，不在本次做。

Storyboard提案沿既有3col、480×270tile+32label，8frame canvas1440×906；processor cap200704針對整張montage，target實際縮小，低cap曾為240visualtokens。Multi8每張336×588=197568pixels，2016visualtokens；Video8同spatialcap、4temporalgrids=1008tokens。frame/timecoverage可matched，visual information/target pixels/patchcompression不matched；不可把差異全歸表示法。937664 video是另pixel sensitivity，Uniform12/16是另density sensitivity，均不加入primary18runs。


## Target NONE

NONE是可提案的commonprimary，18run無staticref、無refextra tokens/額外資產授權問題。它沒有建立目标身分。若未能將動作唯一關聯到指定target，INSUFFICIENT_EVIDENCE + explicit uncertainty，不把generic scene event變target event；不可把TARGET_NOT_OBSERVABLE和identity ambiguous混用。現schema有可用表达，因此没有必然schema-change blocker，但语意humanapproval仍UNRESOLVED。五窗referencepaired另研究且另授權；不包含於primary。

## 時間判定


時間規則為prospective decision，未改現行evaluation.py：GT schema status有EXACT_OBSERVED_TRANSITION、BOUNDED_BY_BEFORE_AFTER_EVIDENCE、TIMING_UNCERTAIN，均有start/endframe+native timestamp，但status決定可用性，不能單看數值是否相等。

- 精確GT：必須確保對應source frame/timebase一致，優先source PTS tick+time_base有理數比較；僅有JSON數字時Decimal(str(number)) exact來源表示，不新加float epsilon。0s是無額外容許量，不把十進位近似說成sensor exact；缺少timebase/frame對照須標UNRESOLVED。prediction點與GT點的絕對差；prediction bounded interval內含GT點僅叫interval-compatible，單獨報interval寬度，不等於exact localization。
- bounded GT：確認event_time是人工存的bounded欄位，不能拿整個BEFORE/AFTER evidence envelope自行扩大。兩interval最短距離 max(0, max(start)-min(end))，與所有0/.2/.5 threshold分別比較。point在bounded interval内也距離0（現require_overlap分支會拒絕這情況，需獨立review）；報交集/寬度/點或區間類型，不能稱精確時間正確。
- TIMING_UNCERTAIN GT或TIMING_UNKNOWN prediction：時間matching UNDEFINED，event-type可独立描述；不能把不確定GT時間包當真值。
- 每窗event_type且target_association_uncertainty=NONE且citation valid才列time-compatible邊；一對一最大匹配，先最大cardinality，再最小總distance，再按GT/pred ID決定tie。當前greedy matcher未證明max-cardinality，下一獨立CPU regression需測反例；本次不實作或計分。
- 0.0/0.2/0.5全報，無primary最佳threshold選取。0.2僅sensitivity，0.5較寬鬆；不以UNIFORM_8 gap/2增容。分開報event-type、GT時間compatibility、prediction uncertainty、citation validity、target association、sampling gap。no exact timing保証。


## 執行設定／預算提案

6×3×1=18generations（不是18獨立event samples）。max_new_tokens1024，do_sample=false，seed42不保證determinisim；load120s、gen300s、request330s。18request上限99分鐘，若六模型session各load120上限再12分鐘；pre-generation infra retry最多一，若每session重載再多最多12分鐘。額外CPUprep、kill/unload和資源不足等待未包含，未設其gate不可宣稱globaldeadline。未批准任何retry。

歷史generation4.14–175.04s（含warmup），measured上至87.28s，長輸出與硬體排程均不穩。可供預留約2–3小時工程時段（假設有限prep、既有環境穩定、至多六次pre-generationreload），不是runtime保證或由DEV量測得出的range，超時仍按原gate結束。不得保證30分鐘。cap1024沒有真實multi-event充分性證明；更長不能由本18failure推得有用。

失敗規則：OOM preserve receipt→runtime failure，不自動減frame/pixel或換精度；timeout preservepartialraw並標stage，不依答案增deadline；invalidJSON/schema/citation保持原字串，strictfailure不是no-event，no-qualityretry；target ambiguity允許abstain。generation開始後0retry；infraretry最多1仅token生成前有可查證start boundary。實驗repeat=1與重試分別列。每次保存attempt，不因favorable結果改runorder。

Hash要求：exact model asset metadata/manifests、prompt/system/schema/validator/adapter source、generation與resource設定、cohort/eligibility/sidecar、每個selectedsource frame+mapping、renderedinput/processedalias/grid、native與encodedtimeline、final18order；目前只有歷史版本與prospective order，候選prompt與matchedDEVassets尚無finalhash。

Gate1：completeprotocol review後另授權freeze task；Gate2：有效freeze receipt後另授權RUN_PHASE2B_EXPLORATORY_PILOT。此task不通過任一gate。
