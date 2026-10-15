"""Post-run descriptive contract audit; no model or processor execution."""
import support as s
import json,hashlib,csv,io,re,difflib
from collections import Counter

def norm(text):return ' '.join(text.casefold().split())
def words(text):return re.findall(r'[a-z0-9_]+',text.casefold())
def overlap(a,b):
    aa,bb=words(a),words(b)
    match=difflib.SequenceMatcher(None,aa,bb,autojunk=False).find_longest_match(0,len(aa),0,len(bb))
    return {'consecutive_word_tokens':match.size,'shared_text':' '.join(aa[match.a:match.a+match.size])}
def table(headers,rows):return '| '+' | '.join(headers)+' |\n|'+'|'.join('---' for _ in headers)+'|\n'+''.join('| '+' | '.join(str(x).replace('|','/') for x in row)+' |\n' for row in rows)

def main():
    run=s.read(s.OUT/'V1D_PREREGISTERED_EXECUTION_MANIFEST.json');fixtures=s.read(s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json')
    source_before=s.read(s.OUT/'BEFORE.json');lock=s.read(s.OUT/'EXECUTION_LOCK_RECEIPT.json');author=s.read(s.OUT/'PROMPT_AUTHORING_RECEIPT.json')
    assert s.sha(s.OUT/'V1D_PREREGISTERED_EXECUTION_MANIFEST.json')==lock['manifest_sha256']
    assert s.sha(s.OUT/'V1D_PREREGISTERED_CRITERIA.md')==lock['criteria_sha256']
    for name,h in {**run['source_sha256'],**run['CPU_receipt_sha256']}.items():assert s.sha(s.ROOT/name)==h,name
    for name,h in run['media_sha256'].items():assert s.sha(s.OUT/name)==h,name
    for name,h in run['model_assets']['files_sha256'].items():assert s.sha(s.MODEL/name)==h,name
    prompt=(s.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt').read_text(encoding='utf8')
    rows=[];all_timing=[];warning_rows=[];failures=[];runtime_rows=[]
    for i,entry in enumerate(run['order'],1):
        aid=f'R{i:02d}_{entry["condition_id"]}';folder=s.OUT/'runs'/aid;f=next(x for x in fixtures['scenarios'] if x['scenario_id']==entry['scenario_id'])
        if not (folder/'completed.json').exists():
            rows.append({'attempt_id':aid,'condition_id':entry['condition_id'],'scenario_id':entry['scenario_id'],'representation':entry['representation'],
              'completed':False,'runtime_failure':s.read(folder/'failure.json') if (folder/'failure.json').exists() else None})
            continue
        record=s.read(folder/'completed.json');runtime=s.read(folder/'runtime_receipt.json');checks=record['validation']
        assert s.sha(folder/'raw_output.txt')==record['raw_response_sha256']
        assert s.sha(folder/'runtime_receipt.json')==record['runtime_receipt_sha256']
        assert record['scenario_id']==entry['scenario_id'] and record['representation']==entry['representation']
        assert record['prompt_sha256']==run['prompt_sha256']
        assert record['video_input_mode']==('NATIVE_ARRAY_EXPERIMENTAL' if entry['representation']=='NATIVE_VIDEO_ARRAY' else 'NATIVE_VIDEO_ARRAY_DISABLED')
        row={'attempt_id':aid,'condition_id':entry['condition_id'],'scenario_id':entry['scenario_id'],'representation':entry['representation'],
          'completed':True,'intended_event_count_private':f['intended_event_count_private'],'raw_path':str((folder/'raw_output.txt').relative_to(s.OUT)),
          'raw_sha256':record['raw_response_sha256'],'input_tokens':runtime['input_token_count'],'visual_tokens':runtime['grid_derived_visual_tokens'],
          'generated_tokens':runtime['generated_tokens'],'eos_observed':runtime['eos_observed'],'output_cap_reached':runtime['output_cap_reached'],
          'generation_deadline_reached':runtime['generation_deadline_reached'],'generation_seconds':runtime['runtime_seconds'],
          'end_to_end_seconds':record['end_to_end_seconds'],'peak_allocated_bytes':runtime['peak_inference_vram_bytes'],
          'peak_reserved_bytes':runtime['peak_reserved_bytes'],'CPU_RSS_bytes':record['hardware_after']['rss_bytes'],
          'CPU_os_peak_wset_bytes':record['hardware_after']['peak_wset_bytes'],'runtime_receipt':runtime,'validation':checks}
        rows.append(row);runtime_rows.append(runtime)
        timing=checks.get('timing_uncertainty_strings',[]);all_timing.extend(x for x in timing if isinstance(x,str))
        warnings=[]
        if f['intended_event_count_private']==0 and checks['event_bearing']:warnings.append('INTENDED_ZERO_EMITTED_EVENTS_DESCRIPTIVE_ONLY')
        if checks['JSON_SYNTAX_PASS'] and f['intended_event_count_private']>0 and not checks['event_bearing']:warnings.append('INTENDED_EVENT_SCENARIO_EMITTED_NONE_DESCRIPTIVE_ONLY')
        if not checks['JSON_SYNTAX_PASS']:warnings.append('EVENT_COUNT_NOT_EVALUABLE_DUE_TO_PARSE_FAILURE')
        concern=[p for p in checks.get('shadow_diagnostic_only',[]) if p['rule_id']=='KNOWN_STATE_SUPPORT' and p['status']=='VIOLATED']
        if concern:warnings.append('KNOWN_STATE_SUPPORT_CONCERN')
        texts=[x for x in timing if isinstance(x,str)]
        if isinstance(checks.get('global_uncertainty'),str):texts.append(checks['global_uncertainty'])
        overlaps=[overlap(x,prompt) for x in texts]
        if any(x['consecutive_word_tokens']>=12 for x in overlaps):warnings.append('LONG_VERBATIM_PROMPT_OVERLAP')
        if any(not norm(x) for x in texts):warnings.append('WHITESPACE_ONLY_UNCERTAINTY_TEXT')
        warning_rows.append({'attempt_id':aid,'automated_warnings':warnings,'uncertainty_prompt_overlap':overlaps,
          'known_state_concerns':concern,'temporal_precision':'UNREVIEWED_REQUIRES_VISUAL_JUDGMENT',
          'target_continuity':'UNREVIEWED_REQUIRES_VISUAL_JUDGMENT','citation_evidential_meaning':'UNREVIEWED_REQUIRES_VISUAL_JUDGMENT',
          'source_evidence_facts':{'distinct_source_RGB_hashes':len({frame['rgb_sha256'] for frame in f['frames']}),
            'all_eight_source_frames_identical':len({frame['rgb_sha256'] for frame in f['frames']})==1,
            'interpretation':'hash facts only; neither continuous motion nor physical-event truth is inferred'},
          'intent_not_ground_truth':True})
    completed=[r for r in rows if r['completed']];valid=sum(r['validation']['STRICT_FULL_PASS'] for r in completed)
    event_count=sum(r['validation']['event_bearing'] for r in completed)
    syntax=sum(r['validation']['JSON_SYNTAX_PASS'] for r in completed)
    verdict='REGRESSION_INCOMPLETE' if len(completed)<8 else 'REGRESSION_FAIL' if valid<8 else 'STRUCTURAL_PASS_COVERAGE_INSUFFICIENT' if event_count<3 else 'REGRESSION_PASS'
    same_timing=len(all_timing)>=3 and len({norm(x) for x in all_timing})==1
    targeted={'event_timing_entries':0,'global_uncertainty':0,'window_citations':0}
    targeted_attempts={k:0 for k in targeted}
    for r in completed:
        if isinstance(r['validation']['targeted_violations'],dict):
            for key,n in r['validation']['targeted_violations'].items():targeted[key]+=n;targeted_attempts[key]+=bool(n)
    categories=Counter(c for r in completed for c in set(r['validation']['categories']))
    summary={'classification':verdict,'scheduled':8,'completed':len(completed),'JSON_syntax_pass':syntax,'strict_full_pass':valid,
      'actual_event_bearing':event_count,'coverage_required':3,'coverage_sufficient':event_count>=3,
      'targeted_violation_entries':targeted,'targeted_violation_attempts':targeted_attempts,'categories_attempt_counts':dict(categories),
      'targeted_fields_not_evaluable_due_to_parse':sum(not isinstance(r['validation']['targeted_violations'],dict) for r in completed),
      'event_entries':len(all_timing),'all_event_timing_identical_normalized_warning':same_timing,
      'distinct_event_timing_normalized_strings':len({norm(x) for x in all_timing}),
      'visual_semantics_warning_review':'UNREVIEWED; no physical GT or final visual judgment inferred',
      'V1D_technically_acceptable_for_human_final_candidate_review':verdict=='REGRESSION_PASS',
      'final_DEV_prompt_approved':False,'Protocol_frozen':False,'real_Phase2a_inferences':0,'V1E':False}
    s.save('V1D_REGRESSION_SUMMARY.json',summary)
    s.save('V1D_REGRESSION_ATTEMPTS.jsonl',''.join(s.canonical(r).decode() for r in rows))
    columns=['attempt_id','condition_id','scenario_id','representation','completed','JSON_SYNTAX_PASS','SCHEMA_PASS','SEMANTIC_PASS','CITATION_PASS','STRICT_FULL_PASS','event_count',
      'timing_uncertainty_strings','global_uncertainty','window_citations','eos_observed','generated_tokens','generation_seconds','peak_allocated_bytes','peak_reserved_bytes','raw_path']
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore');writer.writeheader()
    for r in rows:
        flat={**r,**r.get('validation',{})}
        for key in ['timing_uncertainty_strings','window_citations']:
            if key in flat:flat[key]=json.dumps(flat[key],ensure_ascii=False)
        writer.writerow(flat)
    s.save('V1D_REGRESSION_ATTEMPTS.csv',stream.getvalue())
    s.save('V1D_WARNING_REVIEW.json',{'identical_event_timing_warning':same_timing,'per_attempt':warning_rows,
      'no_automatic_verdict_override':True,'no_accuracy_inference_from_intended_event_count':True})
    validation='# V1D structured validation / coverage\n\n**'+verdict+'**.\n\n'
    validation+=table(['Attempt','Representation','JSON','Schema','Semantic diagnostic','Citation diagnostic','Strict','Emitted events'],[
      [r['attempt_id'],r['representation'],*[r['validation'][k] for k in ['JSON_SYNTAX_PASS','SCHEMA_PASS','SEMANTIC_PASS','CITATION_PASS','STRICT_FULL_PASS']],r['validation']['event_count']] for r in completed])
    validation+=f'\nMandatory field violations (individual entries)={targeted}; affected attempts={targeted_attempts}; distinct category attempts={dict(categories)}. Target fields not evaluable due to parse failure={summary["targeted_fields_not_evaluable_due_to_parse"]}; not counted as field PASS. Actual event-bearing={event_count}/8, coverage threshold3; not physical-event recall.\n\n'
    for r in completed:
        c=r['validation']
        validation+=f"## {r['attempt_id']}\n\nRaw: [{r['raw_path']}]({r['raw_path']}). Strict={c['strict']}.\n\nEvent timing strings: `{json.dumps(c.get('timing_uncertainty_strings'),ensure_ascii=False)}`.\n\nRoot `/uncertainty`: `{json.dumps(c.get('global_uncertainty'),ensure_ascii=False)}`.\n\nWindow citations: {c.get('window_citations')}; nonempty={c.get('window_citations_nonempty')}; membership={c.get('window_citation_membership')}.\n\n"
    validation+=f'''## Warnings and interpretation

All-event identical normalized timing explanation warning={same_timing}; distinct normalized event timing texts={summary['distinct_event_timing_normalized_strings']}. Long overlap uses preregistered >=12 contiguous word tokens. Full per-attempt strings, overlap excerpts, intended/emitted disagreements and masked known-state findings in V1D_WARNING_REVIEW.json. Whitespace-only text screened separately from unchanged schema minLength.

Temporal precision, target continuity and evidential citation meaning require visual judgment and remain explicitly UNREVIEWED, not falsely declared absent or automatically scored from renderer intent. Stable/changed object renderings are not event GT. Semantic/citation shadow diagnostics do not override strict early-return. No invalid outputs repaired or replaced; no further calls/prompt tuning.
'''
    s.save('V1D_STRUCTURED_VALIDATION_REPORT.md',validation)
    supervisor=s.read(s.OUT/'SUPERVISOR_RECEIPT.json');load=s.read(s.OUT/'MODEL_LOADED.json') if (s.OUT/'MODEL_LOADED.json').exists() else None
    resources={'model_load_seconds':load['health']['model_load_seconds'] if load else None,'load_receipt':load,
      'peak_allocated_bytes':max((r['peak_allocated_bytes'] for r in completed),default=None),
      'peak_reserved_bytes':max((r['peak_reserved_bytes'] for r in completed),default=None),
      'global_GPU_observed_peak_MiB':supervisor['global_gpu_observed_peak_mib'],
      'owned_tree_CPU_RSS_observed_peak_bytes':supervisor['owned_cpu_rss_observed_peak_bytes'],
      'supervisor_wall_seconds':supervisor['wall_seconds'],'generation_seconds_total':sum(r['generation_seconds'] for r in completed),
      'owned_worker_exit':supervisor['exit_code'],'resource_stop_reason':supervisor['stop_reason']}
    s.save('V1D_RESOURCE_REPORT.json',resources)
    resource='# V1D resource measurements\n\n'+table(['Attempt','Input tokens','Visual tokens','Generated','EOS','Cap','Gen seconds','E2E seconds','Allocated GiB','Reserved GiB','CPU RSS GiB'],[
      [r['attempt_id'],r['input_tokens'],r['visual_tokens'],r['generated_tokens'],r['eos_observed'],r['output_cap_reached'],round(r['generation_seconds'],3),round(r['end_to_end_seconds'],3),round(r['peak_allocated_bytes']/2**30,3),round(r['peak_reserved_bytes']/2**30,3),round(r['CPU_RSS_bytes']/2**30,3)] for r in completed])
    resource+=f"\nModel load={resources['model_load_seconds']}s; total generation={resources['generation_seconds_total']}s; supervisor wall={resources['supervisor_wall_seconds']}s; global GPU observed peak={resources['global_GPU_observed_peak_MiB']}MiB; owned-tree CPU RSS observed peak={resources['owned_tree_CPU_RSS_observed_peak_bytes']/2**30}GiB.\n\nNo warmup; first-condition cold/startup effects retained, no steady-state benchmark claim. PyTorch allocated/reserved peaks differ from sampled global GPU memory. Supervisor covers complete owned process tree, nominal1s with variable NVIDIA-SMI overhead, not absolute continuous peaks. Effective kwargs are in each runtime receipt (greedy/1024/seed42/300s); inactive checkpoint temperature warning retained, no temperature argument forced.\n"
    s.save('V1D_RESOURCE_REPORT.md',resource)
    changed=[]
    for name,h in source_before['protected_files'].items():
        if s.sha(s.ROOT/name)!=h:changed.append({'path':name.replace('\\','/'),'before':h,'after':s.sha(s.ROOT/name)})
    assert all(c['path']=='src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py' for c in changed)
    after=s.git();assert all(after[k]==source_before['git'][k] for k in ['head','index_sha256','staged_diff_sha256'])
    starts=[s.read(p)['started_at_unix'] for p in (s.OUT/'runs').glob('*/started.json')]
    model_start=s.read(s.OUT/'MODEL_LOAD_STARTED.json')['started_at_unix'] if (s.OUT/'MODEL_LOAD_STARTED.json').exists() else None
    if model_start:
        assert lock['fixture_lock_unix']<author['authored_at_unix']<lock['locked_at_unix']<model_start
        if starts:assert model_start<min(starts)
    s.save('V1D_PRESERVATION.json',{'git_before':source_before['git'],'git_after_before_WORKSPACE_publication':after,
      'protected_baseline_count':len(source_before['protected_files']),'authorized_bridge_pin_extension_only':changed,
      'all_other_protected_files_unchanged':True,'all_model_assets_unchanged':True,'model_assets_count':len(run['model_assets']['files_sha256']),
      'V1C_schema_Validator_parser_system_unchanged':True,'execution_source_hashes_unchanged':True,'fixture_and_execution_hashes_unchanged':True,
      'strict_ordering_verified':True,'fixture_lock_unix':lock['fixture_lock_unix'],'prompt_authored_unix':author['authored_at_unix'],
      'execution_lock_unix':lock['locked_at_unix'],'model_load_started_unix':model_start,'generation_starts_unix':starts,
      'actual_completed_generations':len(completed),'actual_started_conditions':len(starts),'real_DEV_or_old_image_reads':0,
      'pixel_guard_scope':'Python open audit denies all images/videos/arrays outside new task media; path inventories kept; not a machine-wide/native library trace',
      'real_Phase2a_predictions':0,'actual_Phase2b_Pilot':False,'Graph_writes':0,'Protocol_freezes':0,'commit_push':0})
    s.save('V1D_SOURCE_PRESERVATION_REPORT.md',f'''# V1D source and experiment preservation

Baseline {len(source_before['protected_files'])} source/non-image old receipts verified. V1C/schema/Validator/parser/V2 system/evaluator unchanged; parser function hash in SCHEMA_AUDIT.json, full source hash pinned in execution manifest. Only authorized existing source repair is video_array_bridge.py explicit pinned synthetic V1D deployment option (V1C default preserved), exact diff in BRIDGE_V1D_PIN_REPAIR.patch, original source in bridge_before.txt. NF4 shared runtime/generation unchanged. Old capacity/preflight/Variant B reports and raw outputs remain unchanged.

15 local model assets checked before and after; no checkpoint/download/dependency change. New64frames/order locked before V1D authoring, both before execution criteria lock/model load/generation; timestamp and hashes in V1D_PRESERVATION.json. Fixture renderer/media never changed after lock; candidate never changed after creation. One candidate, no V1E, no old/new fixture substitution, no additional model conditions or warmup. Eight scheduled raw receipts or exact incomplete inventory retained.

Git HEAD/index/staged unchanged; worktree intentionally includes bounded bridge extension and new artifacts. Source diffs preserved; no reset/clean/commit/push. Real/old imagery blocked by Python audit guard; only new task/media path inventories. No real DEV preprocessing/inference, GT edit, actual Phase2b Pilot, MemoryGraph write or research Protocol Freeze. No continuous machine-wide/native file trace is claimed. Pre-lock colour-check and path-normalization corrections documented separately, without changing any locked assets or candidate.
''')
    decision=f'''# V1D Human Pilot Decision Package

Current engineering result: **{verdict}**, strict {valid}/8, actual event-bearing {event_count}/8. Candidate technically eligible for final-prompt human review={verdict=='REGRESSION_PASS'}; **not approved as final DEV prompt, no Protocol Freeze**.

| Decision | Evidence | Proposed / pending | Limitation | Human approval |
|---|---|---|---|---|
| Final task prompt | One V1D SHA {run['prompt_sha256']}; all original V1C retained | Review V1D as candidate only if engineering acceptable | New media and adaptive repair; not controlled V1C improvement | REQUIRED |
| Remaining output warnings | See structured validation and warning JSON | Review identical boilerplate/overlap/known-state/visual questions | Visual flags explicitly UNREVIEWED, not physical GT scoring | REQUIRED |
| Video citation | 8aliases/4units, actual scheduled native array | Choose C1 original aliases; C2 separately changed unit contract; or C3 aliases+report disclosure | Membership not proof of frame-specific attention; no change here | REQUIRED |
| Time representation | FRAME_MATCHED_ONLY, native synthetic time sidecar | Real native PTS authoritative; point/interval/uncertain matching and0/.2/.5s sensitivity | No native-time/equal-information/eight-position equivalence; brackets not durations | REQUIRED |
| Target policy | ReferenceNONE; original identity policy unchanged | Decide NONE use and separately unapproved identity clause | Unknown association not automatically TARGET_NOT_OBSERVABLE | REQUIRED |
| Pilot budget/config | Proposed Uniform8,cap200704,story1440x906,1024greedyseed42repeat1,retry0,120/300/330s | Pin final runtime/assets/prompt/system/schema/order | CPU/spatial/token budgets differ; final settings not frozen | REQUIRED |
| Real cohort | No real imagery accessed in this task | Proposed6DEV×3representations=18 only after approval |2nonexhaustiveknownPICKUP,3casealerts,1uncertain;test3excluded;noPLACEMENTpositive;formal_eligible0,CAUSALITY_UNVERIFIED | REQUIRED |
| Scientific interpretation | Synthetic contract compliance only | Descriptive engineering/exploratory reporting | No accuracy/recall/precision/F1/hallucination/generalization/statistical significance | REQUIRED |
| Final Protocol Freeze / actual Pilot | Neither performed | Separate explicit human approvals | Regression_PASS alone grants neither | SEPARATE GATES |

Stop after this regression. If not REGRESSION_PASS, do not automatically author V1E or add calls; human reviews the failure/coverage first. Even PASS leaves visual caution and scientific policy decisions outstanding.
'''
    s.save('V1D_HUMAN_PILOT_DECISION_PACKAGE.md',decision)
    main=f'''# Qwen NF4 V1D 八次 synthetic regression 報告

更新：2026-10-15。**{verdict}**；完整 strict **{valid}/8**；實際 event-bearing **{event_count}/8**（門檻3）。完成{len(completed)}/8，JSON syntax {syntax}/8。

## 1 唯一候選與欄位

全局欄位確定為根物件 **`/uncertainty`**，required/non-null/string/minLength1；歷史6份錯誤的raw、schema paths與Validator逐項核對。`/events/*/timing_uncertainty`每個event必填；`/window_cited_frame_aliases`四種outcome皆minItems1、無例外。沒有改schema／parser／Validator。

V1C SHA `{author['V1C_sha256']}`；V1D SHA **`{run['prompt_sha256']}`**。只增加三段說明（timing證據、root uncertainty、processor-consumed window citations），added{author['added_lines']}行含空白、removed{author['removed_lines']}；原V1C每個byte保留，UTF8/LF不變。Task tokens659→{s.read(s.OUT/'CPU_CHECKS.json')['V1D_task_tokens']}。沒有JSON答案例、scenario-specific alias/position/time、ready-to-copy uncertainty答案或新target policy。完整diff在 [V1C_TO_V1D_UNIFIED_DIFF.patch](V1C_TO_V1D_UNIFIED_DIFF.patch)，審查在 [V1D_PROMPT_CHANGE_REVIEW.md](V1D_PROMPT_CHANGE_REVIEW.md)。

## 2 新fixture與執行前鎖定

8全新獨立seed情境、64張1280x720 RGB sourceframes，Multi3/Story3/Video2，scenario intent只在private metadata，非物理GT。未讀舊／real影像，非從Phase2a事件時間設計。模型只收到PNG/ndarray和opaquealiases，沒有intent、source ID、GT或tracking資料。Fixture lock SHA **`{s.sha(s.OUT/'FIXTURE_LOCK_RECEIPT.json')}`**，早於V1D作者回條；fixed interleaving與allasset hashes見 [V1D_SYNTHETIC_FIXTURE_MANIFEST.json](V1D_SYNTHETIC_FIXTURE_MANIFEST.json)。

執行 manifest SHA **`{s.sha(s.OUT/'V1D_PREREGISTERED_EXECUTION_MANIFEST.json')}`**，criteria與manifest在model load／generation前鎖定；[EXECUTION_LOCK_RECEIPT.json](EXECUTION_LOCK_RECEIPT.json)／[V1D_PREREGISTERED_CRITERIA.md](V1D_PREREGISTERED_CRITERIA.md)。CPU64/64，無CUDA初始化。沒有warmup／repeat／quality retry，8條件固定順序，batch1，1024greedyseed42，generation300s，load120/request330s。

## 3 實測結果

{table(['條件','表示法','Strict','實際event數','秒'],[[r['condition_id'],r['representation'],r['validation']['STRICT_FULL_PASS'],r['validation']['event_count'],round(r['generation_seconds'],2)] for r in completed])}

三項targeted violations（entries）={targeted}；affected attempts={targeted_attempts}；所有其他違規={dict(categories)}。Coverage達標={event_count>=3}。完整uncertainty原字串／windowcitations／known-state shadow checks／raw links在 [V1D_STRUCTURED_VALIDATION_REPORT.md](V1D_STRUCTURED_VALIDATION_REPORT.md)，全8條件機讀 [V1D_REGRESSION_ATTEMPTS.jsonl](V1D_REGRESSION_ATTEMPTS.jsonl)／[CSV](V1D_REGRESSION_ATTEMPTS.csv)。未修補任何生成輸出，未用失敗JSON當no-event。

全部event timing explanation正規化後相同警告={same_timing}（{len(all_timing)}個event entries，{summary['distinct_event_timing_normalized_strings']}種）。長verbatim overlap門檻12連續詞，intended/emitted不一致、known-state掩蓋問題及視覺precision/continuity/citation限制見 [V1D_WARNING_REVIEW.json](V1D_WARNING_REVIEW.json)。需要visual judgment的項目保留UNREVIEWED，不推定全部無問題，不以renderer intent當accuracy GT，也不自動覆寫regression分類。

## 4 Runtime／資源與修正

既有Qwen2.5-VL7B原revision cc594898137f460bfe9f0759e9844b3ce807cfb5、NF4double4bit/BF16/SDPA，一個localmodel。Video只於2個指定條件啟用nativearray，其餘OFF；8frames→4units，仍FRAME_MATCHED_ONLY，沒有新citation syntax／完整nativePTS／8獨立時間位置／equal-information聲稱。

唯一runtime修正是Bridge的V1C-only pin擋住V1D，改成explicit pinned synthetic V1D設定，V1C預設保留；原failure [BRIDGE_PIN_BLOCKER.json](BRIDGE_PIN_BLOCKER.json)、exactsource diff [BRIDGE_V1D_PIN_REPAIR.patch](BRIDGE_V1D_PIN_REPAIR.patch)。Shared NF4 generation不變。GPU recovery0，未按答案改prompt／設定。Pre-lock technical checker與Windows path normalization說明另存，不改已鎖fixture。

Model load={resources['model_load_seconds']}秒；總generation={resources['generation_seconds_total']}秒；supervisorwall={resources['supervisor_wall_seconds']}秒。PyTorch allocatedpeak={resources['peak_allocated_bytes']/2**30 if resources['peak_allocated_bytes'] else None}GiB，reservedpeak={resources['peak_reserved_bytes']/2**30 if resources['peak_reserved_bytes'] else None}GiB；globalGPU觀測peak={resources['global_GPU_observed_peak_MiB']}MiB；ownedtreeCPU RSS觀測peak={resources['owned_tree_CPU_RSS_observed_peak_bytes']/2**30}GiB。Resource stop={resources['resource_stop_reason']}，workerexit={resources['owned_worker_exit']}。詳 [V1D_RESOURCE_REPORT.md](V1D_RESOURCE_REPORT.md)，allocator／samplingscope分開，不聲稱穩態benchmark。

## 5 保存與解讀

[V1D_SOURCE_PRESERVATION_REPORT.md](V1D_SOURCE_PRESERVATION_REPORT.md)／[V1D_PRESERVATION.json](V1D_PRESERVATION.json)：原V1C、schema、Validator、parser、V2、evaluator與舊報告／raw不變；15modelassets前後核對。唯一existing-source變更為預先記錄的bridgepinextension。GitHEAD/index/staged不變，worktree有授權新增與修改，未reset/clean。沒有realDEV或舊影像讀取／realPhase2a prediction／actualPhase2bPilot／GT修改／MemoryGraph／ProtocolFreeze／commit/push。

這是after-V1C-failures的adaptive development，新8fixturepopulation不能拿V1C2/12與本結果當受控改善，亦非物理事件accuracy／recall／precision／F1／hallucinationrate／泛化／統計可靠度。

## 6 下一個人工gate

V1D技術上可作finalPilot候選交人工審閱={verdict=='REGRESSION_PASS'}；**尚未批准為DEV finalprompt**。仍需citationC1/C2/C3、identityclause與referenceNONE、time matching／sensitivity、pixel/generation/retry/failure政策與finalcomponenthashes，再各別人工ProtocolFreeze及actualPilot授權。詳 [V1D_HUMAN_PILOT_DECISION_PACKAGE.md](V1D_HUMAN_PILOT_DECISION_PACKAGE.md)。

本次停止；不建立V1E、不加call、不改fixture／V1D、不跑DEV。Phase2b未宣告完成。
'''
    s.save('PASS_T_PHASE2B_QWEN_NF4_V1D_REGRESSION_REPORT.md',main)
    s.save('DELIVERABLE_MANIFEST.json',{'classification':verdict,'strict_success':valid,'event_bearing':event_count,
      'files_sha256':{p.relative_to(s.OUT).as_posix():s.sha(p) for p in s.OUT.rglob('*') if p.is_file()},
      'realDEV_calls':0,'ProtocolFreeze':False,'final_prompt_approval_inferred':False})
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
