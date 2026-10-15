# 最小修補選項（提案，未實作）

優先：PROMPT_CHANGE_PROPOSED，維持Prediction V1、V2 JSON system與runtime。另行獨立target/time語意審閱，不為歷史pass rate改schema。

| Group | Evidence | Root-cause confidence | Interpretation | Minimal repair | Schema / prompt / decoding | Risks | Required approval | Limited regression |
|---|---|---|---|---|---|---|---|---|
| 空timing_uncertainty | 13次、18event fields | 規則違反已證實；內在生成機制未知 | 非空free text，exact timing亦必填 | PROMPT_CHANGE_PROPOSED：說明精確時可寫無額外可觀察不確定性，不捏造uncertainty | 否 / 提案 / 否 | 可能誘導confidence措辭、改event count | 批准單因子prompt候選與離線preflight | 凍結合成inputs，baseline/candidate雙臂，原strict parser |
| 已知state卻null支持 | 11次secondary | 已由既有guard規則證實 | known requires alias；unknown requires null | 同一prompt說明保守state證據規則 | 否 / 提案 / 否 | 可能偏向UNKNOWN；不可強制known state | 與上項同一prompt intervention | before/after/last nullability CPU tests及原樣保存GPUraw |
| 空window citations | 5次 | minItems違反已證實 | 所有outcomes都需引用，引用不保證連續可評估 | 同一prompt说明引用可用支持/不足證據，不補假alias | 否 / 提案 / 否 | 虛構引用可通過格式，仍須grounding review | 同上 | no-event/uncertain contract CPU tests；GPU不得強制答案 |
| Target association / end visibility | 無此primary直接fail證据；政策有空隙 | SCHEMA_SEMANTIC_REVIEW_REQUIRED | NONE和opaque target无物理辨識保證 | 獨立ontology review，先以現INSUFFICIENT_EVIDENCE表达 | 只有獨立論證必要才提新schema / 待批准 / 否 | 影響scientific task definition | 人工批准語意；另任務，不能與格式放寬混在一起 | ambiguous-target、末端未見 CPU fixtures |
| Syntax / fences / truncation | primary 0/33 | 目前無直接需要 | NO_CHANGE_REQUIRED | decoding作後續備選，不優先 | 否 / 否 / 目前否 | constrained decoding不能保证semantic/citation正确，新增engine差異 | 未來若needed另批DECODING_CHANGE_PROPOSED | syntax only新版本，保留semantic validator |
| Alias scope | primary unsupported 0/33 | 無直接根因 | NO_CHANGE_REQUIRED，維持processor allowlist | 只在promptclarification重申已處理alias，無alias修補器 | 否 / 可隨同fieldclarification / 否 | 列表valid不等於精確grounding | 同prompt批准；不得改raw | supplied-but-unprocessed、reference alias拒絕CPUfixture |
| Output/time cap | 33EOS、max633/1024、zero timeout | INSUFFICIENT_EVIDENCE為調大cap的依據 | NO_CHANGE_REQUIRED for existing configuration | 保留1024提案，後續多事件需另檢capacity | 否 / 否 / 否 | 真實多事件仍可能超cap，timeout上限非保證 | 未來若需要RUNTIME_BUDGET_CHANGE_PROPOSED另批 | 另固定schema complexity bounds，不adaptive retry |

不提供修補patch，不新增full-schema答案example。全schema example可能把事件數與outcome向單一模板偏移；目前所有pass都是零事件，避免用confirmed或no-event例子造成答案偏置。候選prompt只寫規則與條件语意，確切文字需要下一任務審核、hash和批准。

下一授權任務名稱：`PREPARE_QWEN_NF4_PROMPT_CLARIFICATION_AND_MATCHED8_CPU_PREFLIGHT`。它應只產生版本化候選prompt、NONE語意提案、matched8 CPU輸入/processor計畫和receipt，不執行GPU、freeze或real pilot。待候選定稿，另授權 `RUN_QWEN_NF4_MINIMAL_SYNTHETIC_REGRESSION`。不是本audit授權。
