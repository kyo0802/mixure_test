"""Read preserved synthetic results and publish engineering closeout; never infer."""
import support as s
import csv,io,json,hashlib
from collections import Counter

def link(name):return f'[{name}]({name})'
def gib(value):return None if value is None else value/2**30

def main():
    manifest=s.read(s.OUT/'run_manifest.json');before=s.read(s.OUT/'BEFORE.json')
    supervisor=s.read(s.OUT/'SUPERVISOR_RECEIPT.json')
    smoke=s.read(s.OUT/'VIDEO_SMOKE_RESULT.json') if (s.OUT/'VIDEO_SMOKE_RESULT.json').exists() else {'engineering_pass':False,'attempts':len(list((s.OUT/'runs').glob('VIDEO_SMOKE*/started.json')))}
    rows=[];runtime_rows=[]
    for i,planned in enumerate(manifest['original_B_order'],1):
        attempt=f'B_{i:02d}';folder=s.OUT/'runs'/attempt
        if not (folder/'completed.json').exists():
            rows.append({'attempt_id':attempt,'fixture':planned['fixture_id'],'representation':planned['representation'],
              'completed':False,'status':'NOT_COMPLETED','failure':s.read(folder/'failure.json') if (folder/'failure.json').exists() else None})
            continue
        record=s.read(folder/'completed.json');runtime=s.read(folder/'runtime_receipt.json')
        assert s.sha(folder/'raw_output.txt')==record['raw_output_sha256']
        assert s.sha(folder/'runtime_receipt.json')==record['runtime_receipt_sha256']
        checks=record['validation']
        row={'attempt_id':attempt,'fixture':record['fixture'],'representation':record['representation'],'completed':True,
          'video_input_mode':record['video_input_mode'],'raw_path':str((folder/'raw_output.txt').relative_to(s.OUT)),
          'raw_sha256':record['raw_output_sha256'],'input_tokens':runtime['input_token_count'],'generated_tokens':runtime['generated_tokens'],
          'eos_observed':runtime['eos_observed'],'output_cap_reached':runtime['output_cap_reached'],
          'generation_deadline_reached':runtime['generation_deadline_reached'],'runtime_seconds':runtime['runtime_seconds'],
          'allocated_peak_bytes':runtime['peak_inference_vram_bytes'],'reserved_peak_bytes':runtime['peak_reserved_bytes'],
          'cpu_rss_bytes':record['hardware_after']['rss_bytes'],'cpu_os_peak_wset_bytes':record['hardware_after']['os_peak_wset_bytes'],**checks}
        rows.append(row);runtime_rows.append(runtime)
    completed=[r for r in rows if r['completed']];strict=sum(r['STRICT_FULL_PASS'] for r in completed)
    event_bearing=sum(r['event_bearing'] for r in completed)
    by_rep={rep:{'completed':sum(r['representation']==rep for r in completed),
      'strict_pass':sum(r['representation']==rep and r['STRICT_FULL_PASS'] for r in completed),
      'event_bearing':sum(r['representation']==rep and r['event_bearing'] for r in completed),
      'known_state_applicable':sum(r['representation']==rep and r['known_state_applicable'] for r in completed)} for rep in ['MULTI_IMAGE','STORYBOARD']}
    coverage_ok=event_bearing>=4 and all(r['event_bearing']>=2 and r['known_state_applicable']>=1 for r in by_rep.values())
    verdict='REGRESSION_INCOMPLETE' if len(completed)!=12 else 'REGRESSION_FAIL' if strict<12 else 'REGRESSION_PASS' if coverage_ok else 'STRUCTURAL_PASS_COVERAGE_INSUFFICIENT'
    violations=Counter(v for r in completed for v in set(r['violation_categories']))
    warnings=[]
    if strict<10:warnings.append('STRICT_PASS_BELOW_10_OF_12')
    warnings.extend('VIOLATION_IN_3_OR_MORE:'+v for v,n in violations.items() if n>=3)
    if event_bearing<4 or any(r['event_bearing']<2 for r in by_rep.values()):warnings.append('EVENT_BEARING_COVERAGE_INSUFFICIENT')
    if any(r['known_state_applicable']<1 for r in by_rep.values()):warnings.append('KNOWN_STATE_SUPPORT_COVERAGE_INSUFFICIENT')
    if completed and not event_bearing:warnings.append('ALL_OUTPUTS_ZERO_EVENT_OR_ABSTENTION')
    if any(not r['eos_observed'] or r['output_cap_reached'] or r['generation_deadline_reached'] for r in completed):warnings.append('EOS_TRUNCATION_OR_DEADLINE_WARNING')
    summary={'scheduled_B':12,'completed_B':len(completed),'strict_pass_B':strict,'strict_fail_B':len(completed)-strict,
      'event_bearing_attempts':event_bearing,'event_bearing_strict_pass':sum(r['event_bearing'] and r['STRICT_FULL_PASS'] for r in completed),
      'zero_event_responses':sum(r['event_count']==0 for r in completed),
      'abstention_responses':sum(r.get('window_outcome') in {'INSUFFICIENT_EVIDENCE','TARGET_NOT_OBSERVABLE'} for r in completed),
      'known_state_applicable_attempts':sum(r['known_state_applicable'] for r in completed),
      'known_state_supported_attempts':sum(r['known_state_supported'] is True for r in completed),
      'stage_counts':{stage:sum(r[stage] is True for r in completed) for stage in ['JSON_SYNTAX_PASS','SCHEMA_PASS','SEMANTIC_PASS','CITATION_PASS','STRICT_FULL_PASS']},
      'by_representation':by_rep,'coverage_sufficient':coverage_ok,'verdict':verdict,'violation_attempt_counts':dict(violations),
      'engineering_warnings':warnings,'smoke':smoke,'formal_accuracy_measured':False}
    s.save('VARIANT_B_SUMMARY.json',summary)
    s.save('VARIANT_B_ATTEMPTS.jsonl',''.join(s.canon(r).decode() for r in rows))
    columns=['attempt_id','fixture','representation','completed','JSON_SYNTAX_PASS','SCHEMA_PASS','SEMANTIC_PASS','CITATION_PASS','STRICT_FULL_PASS',
      'event_count','event_bearing','known_state_applicable','known_state_supported','input_tokens','generated_tokens','eos_observed',
      'output_cap_reached','runtime_seconds','allocated_peak_bytes','reserved_peak_bytes','cpu_rss_bytes','raw_path','raw_sha256','violation_categories']
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore');writer.writeheader()
    for row in rows:
        out=dict(row)
        if 'violation_categories' in out:out['violation_categories']=';'.join(out['violation_categories'])
        writer.writerow(out)
    s.save('VARIANT_B_ATTEMPTS.csv',stream.getvalue())
    resources={'model_load':s.read(s.OUT/'MODEL_LOADED.json') if (s.OUT/'MODEL_LOADED.json').exists() else None,
      'global_gpu_observed_peak_mib':supervisor['global_gpu_observed_peak_mib'],'owned_tree_cpu_rss_observed_peak_bytes':supervisor['owned_cpu_rss_observed_peak_bytes'],
      'B_runtime_seconds':[r['runtime_seconds'] for r in completed],
      'B_total_generation_seconds':sum(r['runtime_seconds'] for r in completed),
      'B_peak_allocated_bytes':max((r['allocated_peak_bytes'] for r in completed),default=None),
      'B_peak_reserved_bytes':max((r['reserved_peak_bytes'] for r in completed),default=None),
      'B_max_generated_tokens':max((r['generated_tokens'] for r in completed),default=None),
      'supervisor_wall_seconds':supervisor['wall_seconds'],'monitor_scope':supervisor['monitor_scope'],
      'smoke_runtime':s.read(s.OUT/'runs/VIDEO_SMOKE_001/runtime_receipt.json') if (s.OUT/'runs/VIDEO_SMOKE_001/runtime_receipt.json').exists() else None}
    s.save('RESOURCE_SUMMARY.json',resources)
    changed=[]
    for name,h in before['files'].items():
        current=s.sha(s.ROOT/name)
        if current!=h:changed.append({'path':name,'before':h,'after':current})
    allowed='src/memory_graph/pass_t/phase2b/local_vlm/nf4.py'
    if any(r['path']!=allowed for r in changed):raise RuntimeError('UNAUTHORIZED_PROTECTED_SOURCE_CHANGE')
    for name,h in {**manifest['source_hashes'],**manifest['input_hashes'],**manifest['CPU_preprocessing_receipt_hashes']}.items():
        if s.sha(s.ROOT/name)!=h:raise RuntimeError('LOCKED_EXECUTION_COMPONENT_CHANGED:'+name)
    s.authorities()
    after=s.git();git_unchanged_keys=['head','index_sha256','staged_diff_sha256']
    preservation={'protected_files_checked':len(before['files']),'permitted_runtime_changes':changed,'unauthorized_changes':[],
      'source_diff':'runtime_changes.diff','historical_bytes_hash':s.sha(s.OUT/'historical_source/nf4_original_bytes.dat'),
      'execution_source_hashes_unchanged':True,'locked_input_hashes_unchanged':True,
      'git_before':before['git'],'git_after':after,'head_index_staged_unchanged':all(before['git'][k]==after[k] for k in git_unchanged_keys),
      'tracked_worktree_changed_expected':'one authorized NF4 bridge activation branch, plus new files; unrelated pre-existing changes preserved',
      'no_real_DEV_visual_reads_evidence':'support.access_guard permits only locked synthetic fixture trees and derived copies; CPU and GPU pixel path inventories retained',
      'cpu_pixel_reads':s.read(s.OUT/'CPU_CHECKS.json')['pixel_paths_read'],
      'GPU_pixel_reads':s.read(s.OUT/'GPU_EXECUTION_COMPLETE.json')['pixel_paths_read'] if (s.OUT/'GPU_EXECUTION_COMPLETE.json').exists() else s.read(s.OUT/'GPU_FATAL_ERROR.json').get('pixel_paths_read'),
      'scope_limit':'No real DEV pixel files opened, including for checksumming. Other-process actions not continuously observed.',
      'real_Phase2a_generations':0,'GT_edits':0,'Graph_writes':0,'protocol_freezes':0,'commit_push':0}
    if not preservation['head_index_staged_unchanged']:raise RuntimeError('GIT_AUTHORITY_CHANGED')
    s.save('SOURCE_PRESERVATION.json',preservation)
    s.save('SOURCE_PRESERVATION.md',f'''# Source preservation

Checked {len(before['files'])} baseline source/processor/non-image historical artifacts, plus all execution-locked inputs and source hashes. Exactly {len(changed)} permitted old-source change: NF4 preprocessing opt-in branch. Historical original bytes preserved in historical_source/nf4_original_bytes.dat; exact diff in runtime_changes.diff. Bridge default NATIVE_VIDEO_ARRAY_DISABLED. Original parser/Validator/schema/V2 formatting/V1C/fixtures unchanged. Source checks exclude real DEV imagery to comply with this task; do not claim old 29,746 image checksum inventory was reread.

Git HEAD/index/staged unchanged={preservation['head_index_staged_unchanged']}; tracked worktree intentionally changed. No unrelated reset/clean. Complete before/after hashes in SOURCE_PRESERVATION.json. Pixel guards and CPU/GPU path inventories establish owned script's synthetic-only access; not a machine-wide claim. No real Phase2a inference/GT edit/Graph write/Protocol Freeze/commit/push. New authorized artifacts are additions.
''')
    s.save('VIDEO_CITATION_OPTIONS.md','''# Video citation decision options — not approved

Eight source aliases F0001..F0008 remain unchanged. U0={F0001,F0002}, U1={F0003,F0004}, U2={F0005,F0006}, U3={F0007,F0008}; U names are provenance labels, not permitted prediction aliases. Actual attention localisation to a single frame remains unverified.

| Option | Meaning | Prediction V1 / strict Validator | Evaluator and timing | Future prompt / approval |
|---|---|---|---|---|
| C1 | Cite original source F aliases; private unit mapping | Structurally compatible; membership does not prove exact-frame model attention | Existing mapping structurally usable; scientific exact-frame interpretation requires approval | No forced prompt change; approve provenance-only semantics and precision limits |
| C2 | Cite conceptual two-frame temporal units | Not compatible without separately approved contract/Validator change; not implemented | Need separately approved unit-to-time and event matching rules | New prompt/schema/evaluator review; no activation here |
| C3 | Keep F aliases, disclose paired unit/native span in report | Report-only sidecar can preserve schema/Validator | No automatic interval expansion or scoring change; span is provenance, not confidence interval | Recommend report-only C3, but not chosen/approved; any model-visible instruction/new field/matching change needs separate approval |

Smoke uses unchanged membership Validator. This engineering success does not select final citation semantics. FRAME_MATCHED_ONLY is same source/order, not native-time/token/spatial/citation equivalence.
''')
    s.save('TEMPORAL_MAPPING_LIMITATIONS.md','''# Native → processor → model timing

See cpu/video_<fixture>.json for all 8 rows per locked synthetic fixture. Separate quantities: source synthetic PTS, nominal i/fps, processor unit floor(i/2)*second_per_grid_ts, static model relative temporal contribution. Separate columns retain nominal reconstruction error, processor quantization from nominal, processor-vs-native and static proxy-vs-native error. No container was encoded. Native PTS is private; span determines reconstructed FPS, individual PTS never entered the model text.

Important correction to previous simplified static proxy: installed modeling_qwen2_5_vl.py first calls torch.as_tensor(second_per_grid_t,dtype=range_tensor.dtype), with range_tensor=int64, BEFORE multiplication and final.long(). Source-faithful static calculation uses that cast. For hypothetical seconds=.99, previous floating simplification gives [0,1,3,5], whereas installed-source relative contribution gives [0,0,0,0]. Old reports remain untouched; their float proxy is not an exact reproduction of this installed integer-cast path. Unit count4 also does not guarantee4 distinct temporal position IDs.

GPU smoke proves native Video tensor route and actual forward/generation complete, not independently observed absolute position_ids or per-frame attention. Actual model position_ids were not instrumented; scalar source proxy must not be promoted to a runtime measurement. Source code/config hashes are in execution manifest. No architectural patch to temporal grouping/position code.
''')
    decisions=[
      ('Three representations',f"B {strict}/{len(completed)} strict; Video smoke engineering={smoke.get('engineering_pass')}",'Multi8/Story8/VideoArray8 exploratory','Smoke is not Video regression or real event accuracy','YES'),
      ('Video frame/time','7synthetic CPU matches, warmup GPU route','FRAME_MATCHED_ONLY;8frames/4units','CFR/temporal quantization; not equal time/tokens/spatial information','YES'),
      ('Video citation','Existing F membership only','Choose C1/C2/C3; suggest report-only C3','Single F citation does not prove individual attention','YES'),
      ('Target Reference NONE','Synthetic inputs contain no reference','TARGET_REFERENCE_NONE','Does not uniquely establish target identity','YES'),
      ('Target identity ambiguity','Clause NOT_APPROVED_NOT_ENABLED','Keep separate decision','Unknown identity not auto TARGET_NOT_OBSERVABLE; clause not merged','YES'),
      ('Uniform8','Fixed existing synthetic source membership','GT-independent round ties-to-even, endpoints','Sparse transitions/observability limits','YES'),
      ('Pixel/layout','CPU original pixel parity','cap200704,min3136;story3cols480x270+32,1440x906','Global storyboard resize loses detail; budgets not equivalent','YES'),
      ('Generation','Actual shared parameters recorded','1024,greedy,seed42,repeat1','Seed/greedy not bitwise reproducibility guarantee','YES'),
      ('Timeouts','Supervisor and runtime receipts','load120/gen300/request330','Samples/deadline checks not continuous instruction-level timeout','YES'),
      ('Event timing','No real GT scoring in this run','native PTS; point/closed interval/uncertain separately;1-to-1;0/.2/.5s all report','Evidence brackets are not event duration; exact matching semantics still need approval','YES'),
      ('Retry','No B retry; authorized smoke allowance bounded','generation0;never output-based retry','Any future infra retry needs defined pre-generation boundary','YES'),
      ('Strict JSON failure',f'{dict(violations)}','Preserve raw; full strict gating unchanged','Syntax/schema alone not full validity; no repair','YES'),
      ('Six DEV eligibility','Read existing metadata policy only; no DEV pixels','2known nonexhaustive PICKUP,3case negatives,1uncertain;test3excluded','formal_eligible0; no confirmed PLACEMENT; CAUSALITY_UNVERIFIED','YES'),
      ('Interpretation','Synthetic engineering only','Descriptive exploratory pilot; no formal metrics','No precision/recall/F1/accuracy/population hallucination/generalization/significance','YES'),
      ('Final hashes',f"execution manifest {s.sha(s.OUT/'run_manifest.json')}",'Pin approved final runtime/task/schema/assets/order separately','V1C approved only for synthetic candidate; final DEV prompt not approved','YES'),
      ('Human protocol freeze submission',verdict,'Submit decision package after remaining choices','No automatic freeze; no DEV run authorization implied','YES_SEPARATE_FINAL_GATE')]
    package='# Qwen NF4 Final Pilot Decision Package\n\nPROPOSED_AWAITING_HUMAN_REVIEW; PROTOCOL_NOT_FROZEN.\n\n| Decision | Verified evidence | Proposed setting | Risk / limitation | User approval required |\n|---|---|---|---|---|\n'
    for row in decisions:package+='| '+' | '.join(row)+' |\n'
    package+='\nFirst pilot proposal: six DEV windows × three representations =18 calls, referenceNONE, uniform8,1024greedyseed42repeat1,retry0. **No DEV images or model calls occurred here.** Additional positives in nonexhaustive windows UNEVALUATED; strict-negative case-level alerts only; uncertain descriptive only. No formal metrics.\n\nNext required decisions: final citation option and time interpretation; identity ambiguity clause/NONE policy; budget/layout/generation/timeouts/retry/failure/matching rules; final DEV prompt and component fingerprints; explicit human protocol freeze approval; actual exploratory DEV run remains separate authorization. Synthetic outcome does not automatically pass these gates.\n'
    s.save('QWEN_NF4_FINAL_PILOT_DECISION_PACKAGE.md',package)
    cpu=s.read(s.OUT/'CPU_CHECKS.json')
    main=f'''# Qwen NF4 Engineering Closeout 報告

更新：2026-10-15。最新任務取代未完成 Track1，依新授權完成獨立 engineering closeout。未把中斷的 Track1當成成功結果。

## 1 結果

- Native Video Array engineering smoke：{smoke.get('engineering_pass')}；實際 smoke attempts={smoke.get('attempts')}；nonempty={smoke.get('nonempty_raw_output')}；strict-valid={smoke.get('strict_valid')}。
- Variant B：{len(completed)}/12 完成，完整 strict通過 {strict}/12，結果 **{verdict}**。
- Event-bearing {event_bearing}/12，event-bearing strict通過 {summary['event_bearing_strict_pass']}；known-state applicable {summary['known_state_applicable_attempts']}/12；coverage足夠={coverage_ok}。
- CPU {cpu['passed']}/{cpu['count']} unique checks；6個負面assertions覆核重跑，不另加unique count。7原有synthetic fixtures(6eval+1warmup)，5video tensors逐值一致，12個B原pixel/rendered一致。沒有讀real DEV影像。
- Warning：{warnings}。

## 2 實作與 runtime 範圍

新增 `src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py`；只在 NF4 preprocess加明確 default-disabled分支。歷史AVI/image程式保持預設行為，原source bytes與diff封存。使用同一shared generate_common/structuredoutput，沒有第二loader/evaluator/schema、沒有server或HTTPtransport redesign。Bridge本次經同一實際NF4 runtime的本機in-process路徑執行；現行HTTPtransport不接收ndarray，不宣稱HTTP/nativearray也驗證過。B feature flag全OFF，一個model instance，無額外warmup/repeat/retry。

## 3 固定 authority 與執行前鎖定

Model Qwen/Qwen2.5-VL-7B-Instruct、revisioncc594898137f460bfe9f0759e9844b3ce807cfb5、NF4double4bit BF16 SDPA；本機權重逐檔核對既有assetmanifest，非新的upstream checksum attestation。

V1C SHA `3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722`，APPROVED_FOR_SYNTHETIC_REGRESSION_CANDIDATE_ONLY；identityclause NOT_APPROVED_NOT_ENABLED。Lock receipt SHA `149f8696e51fa91cf43147d761315672dc43594aebe41b58cea8ed78956346ee`，與content_id ecc283...及fixture manifest SHA7e03...是不同概念，未混用。

執行前 immutable {link('preregistered_criteria.md')}、{link('run_manifest.json')}、{link('PREREGISTRATION_LOCK_RECEIPT.json')}；root criteria path `{manifest['criteria_path']}`。Manifest SHA `{s.sha(s.OUT/'run_manifest.json')}`。確切B原順序、source/model/assets/processor/fixture/format/schema/Validator hashes全部保留；無觀察答案後調參。

## 4 分階段 strict 與 violations

{summary['stage_counts']}。None表示not-evaluable，非PASS。authoritative strict Validator unchanged；它的early-return不被改寫，stage影子診斷不另計分。

Violation distinct-attempt counts：{dict(violations)}。每個item原raw、started、runtime、completion/validation receipts在runs/；{link('VARIANT_B_ATTEMPTS.csv')}、{link('VARIANT_B_ATTEMPTS.jsonl')}有完整12列與失敗案例。

Representation分層：{json.dumps(by_rep,ensure_ascii=False)}。B coverage沿原Markdown每rep2/6event-bearing、1/6knownstate、pooled4/12；未誤套A6/18。原intendedstrata只是designer intention，不強制模型答案、不算physicalGTaccuracy。

## 5 時間與 citation

Video8 source→4units，FRAME_MATCHED_ONLY。Source/native、uniformframe、processorunit、staticmodeltime分開列於cpu/video_*.json。Installed get_rope_index先把second_per_grid轉range_tensor.int64再乘tokens_per_second2；前次浮點簡化proxy的限制已在 {link('TEMPORAL_MAPPING_LIMITATIONS.md')}揭露，舊報告不改。GPUforward/generation成功不證明逐frame attention或實際absolutepositionIDs；未instrument實際position_ids。

{link('VIDEO_CITATION_OPTIONS.md')}保留C1原Falias、C2unitcitations設計、C3Falias加unitspan disclosure，尚未選定。Smoke沿原Validator membership；沒有修改predictioncitation syntax／評分。

## 6 資源與 latency

Model load：{resources['model_load']['health']['model_load_seconds'] if resources['model_load'] else None}秒。
Smoke generation：{resources['smoke_runtime']['runtime_seconds'] if resources['smoke_runtime'] else None}秒；allocatedpeak={gib(resources['smoke_runtime']['peak_inference_vram_bytes']) if resources['smoke_runtime'] else None}GiB，reservedpeak={gib(resources['smoke_runtime']['peak_reserved_bytes']) if resources['smoke_runtime'] else None}GiB。
B每次generationseconds={resources['B_runtime_seconds']}；合計{resources['B_total_generation_seconds']}秒，allocatedpeak={gib(resources['B_peak_allocated_bytes'])}GiB，reservedpeak={gib(resources['B_peak_reserved_bytes'])}GiB。
全程global GPU觀測peak={resources['global_gpu_observed_peak_mib']}MiB，ownedtreeRSS觀測peak={gib(resources['owned_tree_cpu_rss_observed_peak_bytes'])}GiB；supervisorwall={resources['supervisor_wall_seconds']}秒。觀測samples不是continuous/global精確peak；PyTorchallocatorpeak另列，不混為同一量。完整 {link('RESOURCE_SUMMARY.json')}、{link('SUPERVISOR_RECEIPT.json')}。

## 7 保存與限制

{link('SOURCE_PRESERVATION.md')}／{link('SOURCE_PRESERVATION.json')}／{link('runtime_changes.diff')}。169個baseline非DEV影像source/artifact、全lockedsyntheticpixels與executionmanifest核對；只有授權的NF4 branch改動，其餘protected unchanged。GitHEAD/index/staged保持原樣，worktree因授權變更而改動。沒有為hash驗證讀DEVimage。沒有realPhase2a inference、GT改動、Graphwrite、ProtocolFreeze、commit/push。

不能將15/33capacity與本12call當可比較improvement estimates：population/technicalconditions不同。沒有三表示法equal-information控制聲稱，未驗證real-world event accuracy。這次只有Video integration smoke，不是VariantA Video regression。

## 8 下一步

請閱讀 {link('QWEN_NF4_FINAL_PILOT_DECISION_PACKAGE.md')} 的16項決策。仍需finalDEVprompt/citation/identity/NONE/timing/budget/generation/retry/failure/hash選擇與人工protocolfreeze，實際DEVrun再獨立授權。Candidatefirstpilot18calls只提案，formal_eligible=0、CAUSALITY_UNVERIFIED，test3excluded，2nonexhaustiveknownPICKUP/3casealerts/1uncertain限制不變。

**本任務完成後停止。結果交給人工審閱，不自動改V1C、加call或啟動DEV。**
'''
    s.save('PASS_T_PHASE2B_QWEN_NF4_ENGINEERING_CLOSEOUT_REPORT.md',main)
    files={p.relative_to(s.OUT).as_posix():s.sha(p) for p in s.OUT.rglob('*') if p.is_file()}
    s.save('DELIVERABLE_MANIFEST.json',{'status':'QWEN_NF4_ENGINEERING_CLOSEOUT_COMPLETE_AWAITING_HUMAN_PROTOCOL_DECISIONS',
      'regression':verdict,'files_sha256':files,'new_GPU_smoke_calls':smoke.get('attempts'), 'new_Variant_B_calls':len(completed),
      'real_Phase2a_calls':0,'protocol_frozen':False,'no_commit_push':True})
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
