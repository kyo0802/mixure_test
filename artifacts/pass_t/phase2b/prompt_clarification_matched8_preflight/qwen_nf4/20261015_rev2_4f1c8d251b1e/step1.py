import core
import re,importlib.metadata
from memory_graph.pass_t.phase2b.predictions import validate_prediction,schema

CLARIFICATION='''
Contract clarification for PASS_T_PHASE2B_PREDICTION_V1:

Timing: each reported event requires a nonempty timing_uncertainty string. This is a truthful textual explanation, not an extra enum or a numerical precision requirement. For EXACT_SUPPLIED_FRAME, use it only when the transition itself is directly visible; explain the limits of the observation, including when no additional timing uncertainty is observed. For BOUNDED_SUPPLIED_FRAMES, explain the gap or interval limitation using the supplied boundary aliases. For TIMING_UNKNOWN, explain why the transition time cannot be established. An empty string, null, or omitted timing_uncertainty does not satisfy the contract. Never invent a precise time to satisfy a field.

Window evidence: this schema requires at least one window_cited_frame_aliases entry for each of CONFIRMED_EVENTS, NO_CONFIRMED_EVENT, INSUFFICIENT_EVIDENCE, and TARGET_NOT_OBSERVABLE. Cite only aliases actually supplied for the visual media. Window citations identify evidence supporting the assessment or its limitations; they do not certify continuous assessability. A confirmed event also requires nonempty event-specific cited_frame_aliases. For uncertain or non-observable outcomes, cite the available evidence supporting those limitations; preserve uncertainty and do not fabricate a supporting observation. Never cite unprocessed frames from an encoded clip, private frame IDs, annotations, or static target-reference media as event evidence. If a required citation genuinely cannot be supported, acknowledge the evidentiary conflict truthfully rather than inventing an alias.

Physical-state evidence: ON_SURFACE, HELD_BY_PERSON, and OTHER_OBSERVED require a supplied supporting_frame_alias in before_state, after_state, and last_directly_supported_state. STATE_UNKNOWN requires supporting_frame_alias=null. Use STATE_UNKNOWN when a physical state has no directly supporting observation. Visibility alone does not establish that an object is held. Occlusion does not establish placement; disappearance does not establish pickup; leaving the view does not prove final location. Unsupported continuity stays uncertain. A change of observed state is not automatically a confirmed PICKUP or PLACEMENT.

Keep the existing fields, permitted values, safety assertions, and subsequent_state=UNKNOWN. Do not add fields. Report only transitions supported by the bounded supplied evidence; do not fabricate events to exercise a response branch. Return only the required JSON object without Markdown or additional prose.
'''

def run():
    core.authorities();lock=core.read(core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json')
    for name,h in lock['model_visible_frames_sha256'].items():assert core.sha(core.OUT/name)==h
    assert core.sha(core.OUT/'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json')==lock['fixture_manifest_sha256']
    cap=core.ROOT/'artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree'
    f=core.read(cap/'fixtures/MULTI_8_P200704/fixture.json');previous=f['payload']['instructions'];system=f['deployment']['response_format_system']
    prompt=previous+CLARIFICATION
    private=core.read(core.OUT/'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json')
    literals=[]
    for s in private['scenarios']:
        literals.extend([s['fixture_id'],s['script'],str(s['seed']),s['intended_stratum']])
    # Whole literals: the generic ontology word "lifted" is not the private
    # scene identifier "lift". Substring matching would create a false alarm.
    overlaps=[v for v in literals if re.search(r'\b'+re.escape(v)+r'\b',prompt)]
    assert not overlaps
    assert 'TARGET_REFERENCE_NONE' not in prompt and 'identity cannot be' not in prompt
    exact_clause='''Under TARGET_REFERENCE_NONE, if the supplied media cannot establish which physical instance is the intended local target, use INSUFFICIENT_EVIDENCE and explain the target-association limitation in uncertainty. Do not equate unresolved identity with TARGET_NOT_OBSERVABLE, and do not convert a generic scene transition into a target-specific event without evidence.'''
    core.save('QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt',prompt)
    # This is a private CPU schema fixture, not a model answer or GT example.
    value={'schema_version':schema()['$id'],'target_id':'TARGET_A','window_outcome':'INSUFFICIENT_EVIDENCE',
      'window_cited_frame_aliases':['F0001'],'events':[],'last_directly_supported_state':{'state':'STATE_UNKNOWN','supporting_frame_alias':None},
      'end_visibility':'UNKNOWN','subsequent_state':'UNKNOWN','rationale':'Target association cannot be established from available media',
      'uncertainty':'Local target identity unresolved','safety_assertions':{'global_identity_claimed':False,
      'state_persisted_across_unobserved_interval':False,'container_or_handover_auto_classified':False}}
    result=validate_prediction(value,['F0001']);assert result['valid']
    core.save('conditional_clauses/identity_acceptance_cpu_fixture.json',{'fixture':value,'validation':result,'not_model_output':True})
    core.save('TARGET_IDENTITY_AMBIGUITY_CLAUSE_PENDING_APPROVAL.md',f'''# Target 身分歧義條款 — PENDING_APPROVAL / NON_EXECUTABLE

提案原文（沒有放入核心prompt）：

> {exact_clause}

現Prediction V1允許INSUFFICIENT_EVIDENCE、empty events、STATE_UNKNOWN/null與非空uncertainty；獨立CPU字典透過未改validator接受：{result}。這只是technical acceptance，不是humanapproval。

身份未確立、已確立目標不在可觀察視野、物理轉換證據不足是三種不同概念。現schema能以outcome+自由文字表达第一及第三，TARGET_NOT_OBSERVABLE不應被當作多實例ambiguity的別名。沒有加入target field或強制HIGH/LOW；CONFIRMED_EVENTS配HIGH目前validator接受但需要前瞻解讀，不能由此推定身份確認。

替代：拒絕NONE首次條件，另設授權的target-reference定位任務；或獨立ontology review證實現schema无法表达必要語意才另提版本化schema。本次不採用任一替代。

風險：opaque TARGET_A缺靜態target reference時可能無法唯一關聯；偏向abstention影響任務定義，並不代表事件推理好壞。需要human選擇批准或拒絕確切條款及NONE的有限科學意義。未批准前不可將本段串入regression executableprompt，不得啟用。
''')
    tokenizer_status={}
    try:
        processor,torch=core.load_processor();tok=processor.tokenizer
        tokenizer_status={'status':'EXACT','token_count':len(tok.encode(prompt,add_special_tokens=False)),
            'scope':'standalone task prompt, excludes system/schema/media/template expansion','tokenizer_class':type(tok).__name__,
            'transformers_version':importlib.metadata.version('transformers'),'torch_version':torch.__version__,'cuda_initialized':torch.cuda.is_initialized()}
    except (OSError,ImportError) as e:
        tokenizer_status={'status':'PROCESSOR_BEHAVIOR_UNVERIFIABLE','token_count':None,'reason':str(e)}
    candidate={'candidate_name':'QWEN_NF4_EVENT_REASONING_PROMPT_V1C','candidate_approved':False,
      'prompt_sha256':core.sha(core.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt'),'file_size':len(prompt.encode()),
      'previous_task_prompt_sha256':core.byte_sha(previous.encode()),'v2_system_sha256':core.byte_sha(system.encode()),
      'prediction_v1_schema_sha256':core.sha(core.ROOT/'src/memory_graph/pass_t/phase2b/contracts/prediction_v1.json'),
      'v3_construction_sha256':core.sha(core.ROOT/'src/memory_graph/pass_t/phase2b/local_vlm/qwen_contract.py'),
      'fixture_lock_receipt_sha256':core.sha(core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json'),
      'step0b_receipt_sha256':core.sha(core.OUT/'STEP_RECEIPT_0B.json'),
      'tokenizer':tokenizer_status,'identity_clause_in_core':False,'fixture_literal_overlaps':overlaps,
      'leakage_categories_checked':['scenario IDs','script/scene identifiers','intended event-count labels','seeds','numeric source timestamps','rendered text (no scene text)','private object identifiers','palette colors and positions (not included in prompt)'],
      'allowed_generic_overlaps':['PICKUP','PLACEMENT','field names','enum values','supported physical-state terminology'],
      'changes':['nonempty timing explanation without invented precision','outcome-specific citations per existing V1','known/unknown state support and conservative continuity'],
      'unchanged':['schema','strict validator','V2 system','V3 runtime','model/revision/NF4','generation parameters'],
      'remaining_ambiguities':['citation requirement vs genuinely unsupported evidence: do not invent','target identity clause pending human approval','video alias temporal granularity']}
    core.save('prompt_candidate/receipt.json',candidate)
    core.save('prompt_candidate/v2_system_unchanged.txt',system)
    core.save('PROMPT_CLARIFICATION_TRACEABILITY.md',f'''# V1C prompt追溯 — 尚未批准

| Step0 category | 原contract | 新clarification | 證據 | 風險 |
|---|---|---|---|---|
| 空timing，13attempt/18欄位 | 每event string minLength1 | exact/bounded/unknown的非空誠實文字，不能造精確時間 | schema與diagnostics/frequencies.json | 可能改uncertainty措辭，尚未測效能 |
| 空window cite，5attempt | 所有四種outcome都minItems1 | 依outcome引用支持或不足的實際影格，不造alias | 原schema/validator | 引用valid不代表grounding或continuousassessability |
| known-state無support，11attempt/20欄位 | known requires alias，unknown requires null | before/after/last均遵循；看得見不等於held | shadow原碼規則+JSONL | 可能增加UNKNOWN，不證明提升事件辨識 |

原task完整保留，只追加抽象規則；沒有full-schema示例、fixture-specific例子或答案。pending identity clause完全獨立。沒有新增mandatoryfields、enum、timestamps；沒有強迫exacttime、事件數、隱藏狀態或持續性。

候選SHA `{candidate['prompt_sha256']}`；原taskSHA `{candidate['previous_task_prompt_sha256']}`；V2systemSHA `{candidate['v2_system_sha256']}`。token count={tokenizer_status}。只計task本體，不能當實際expandedinputtokens。

鎖回條hash `{candidate['fixture_lock_receipt_sha256']}` 被prompt receipt引用；lock自身指向immutablemanifest/影格hash且記錄prompt absent，Step0B完成後才寫candidate。時間戳只是補充。作者知道fixtures概念，這不證明概念盲測。

保留規則：Prediction V1、parser/validator、V2formatting、V3construction/runtime、greedy等全部不改。尚未釐清target-NONE的科學解讀、Video可辨alias粒度與citation/abstention真正衝突；均交human，不以修schema提高舊pass率。
''')
    core.receipt(1,[core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json',core.OUT/'STEP_RECEIPT_0B.json',core.ROOT/'src/memory_graph/pass_t/phase2b/contracts/prediction_v1.json'],
      [core.OUT/n for n in ['QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt','TARGET_IDENTITY_AMBIGUITY_CLAUSE_PENDING_APPROVAL.md','PROMPT_CLARIFICATION_TRACEABILITY.md','prompt_candidate/receipt.json']],
      prompt_sha256=candidate['prompt_sha256'],holdout_lock_receipt_sha256=candidate['fixture_lock_receipt_sha256'])
    print({'prompt_sha256':candidate['prompt_sha256'],'tokenizer':tokenizer_status,'pending_clause_in_core':False})
if __name__=='__main__':run()
