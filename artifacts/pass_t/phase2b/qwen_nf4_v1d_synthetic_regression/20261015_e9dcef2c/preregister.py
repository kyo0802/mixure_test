"""Fix all engineering criteria and fingerprints before model loading."""
import support as s
import inputs as inp
import hashlib

def main():
    fixture=s.read(s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json');lock=s.read(s.OUT/'FIXTURE_LOCK_RECEIPT.json')
    author=s.read(s.OUT/'PROMPT_AUTHORING_RECEIPT.json');cpu=s.read(s.OUT/'CPU_CHECKS.json')
    assert cpu['count']==cpu['passed'] and not cpu['CUDA_initialized']
    assert s.sha(s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json')==lock['fixture_manifest_sha256']
    assert s.sha(inp.prompt_path())==author['V1D_sha256']
    assert lock['created_at_unix']<author['authored_at_unix']
    before=s.read(s.OUT/'BEFORE.json');allowed='src/memory_graph/pass_t/phase2b/local_vlm/video_array_bridge.py'
    for name,h in before['protected_files'].items():
        if name.replace('\\','/')!=allowed and s.sha(s.ROOT/name)!=h:raise RuntimeError('PROTECTED_SOURCE_CHANGED:'+name)
    assets=s.read(s.OUT/'model_assets.json')
    for name,h in assets['files_sha256'].items():assert s.sha(s.MODEL/name)==h,name
    v1c=s.REF/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt'
    assert s.sha(v1c)==author['V1C_sha256']=='3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722'
    review=f'''# V1D minimal prompt change review

V1C SHA `{author['V1C_sha256']}`；V1D SHA `{author['V1D_sha256']}`。
Only three adjacent additions: event timing evidence/resolution and non-duration brackets; required root `/uncertainty` evidence-supported window limitations; processor-consumed window citation scope and uncertain assessment. All original V1C bytes are retained and recovered by removing those additions. Added lines={author['added_lines']} (including blank), removed={author['removed_lines']}; UTF8 no BOM/LF unchanged. Full diff: V1C_TO_V1D_UNIFIED_DIFF.patch (zero context, exact entire diff).

Original ontology/output/state/target/general instructions/schema references remain byte-for-byte. No new enum/property, no full JSON example, fixture/scenario/position/timestamp or literal frame alias, no ready-to-copy response sentence. Global exact field `/uncertainty` was verified before authorship. Identity semantic clause NOT_APPROVED_NOT_ENABLED.

Fixture lock SHA `{s.sha(s.OUT/'FIXTURE_LOCK_RECEIPT.json')}` predates authoring receipt. All64 frames and eight scenarios were locked before candidate text; metadata leakage checks run on actual rendered conversations for all8 conditions, no scenario IDs/private intent/GT fields sent. Historical model outputs used for schema audit only, not copied into V1D. Pixel semantic content necessarily contains authored visual actions, not hidden metadata answers; the renderer's intent is not physical GT.

Exact tokenizer count: V1C {cpu['V1C_task_tokens']}, V1D {cpu['V1D_task_tokens']}; standalone task only, excludes system/schema/media-expanded tokens. Static compatibility: all original bytes preserved; Prediction V1/Validator/parser/system unchanged; all8 CPU representations accepted, CPU checks {cpu['passed']}/{cpu['count']}. This is not scientific evidence of prompt efficacy.

One bounded runtime compatibility repair: original bridge rejects V1D with V1C_HASH_CHANGED (BRIDGE_PIN_BLOCKER.json); BRIDGE_V1D_PIN_REPAIR.patch adds an explicit pinned synthetic V1D deployment hash and records that hash in receipts. V1C remains default, tested with new CPU imagery. NF4 shared generation unchanged. No GPU repair/retry planned; any subsequent material execution blocker ends INCOMPLETE. Pre-lock renderer check corrected a false colour-count blankness proxy without changing any existing pixel bytes (PRELOCK_RENDER_CHECK_NOTE.md).
'''
    s.save('V1D_PROMPT_CHANGE_REVIEW.md',review)
    order=[]
    for fid in fixture['execution_order_scenario_ids']:
        f=next(x for x in fixture['scenarios'] if x['scenario_id']==fid)
        order.append({'scenario_id':fid,'condition_id':f['condition_id'],'representation':f['representation']})
    criteria='''# V1D preregistered engineering criteria

One narrowly additive V1D synthetic candidate, NOT final DEV prompt approval or research Protocol Freeze. New8 scenarios/64frames prospectively locked before authorship. Original V1C/PredictionV1/parser/Validator/V2system/evaluator unchanged. No old or real imagery, old fixtures/warmup, historical-response answers, identity clause, target reference, downloads, remote inference, DEV/Pilot/Graph/commit/push.

Exactly8 planned serial conditions: Multi8 zero/one/multiple; Story8 zero/one/multiple; VideoArray8 zero/one. Fixed SHA ranked within modality then round-robin order in fixture manifest. Intent metadata private, never forces events. No separate warmup, optional repeat or output-quality retry. One local model instance; original Qwen2.5-VL7B revision cc594898137f460bfe9f0759e9844b3ce807cfb5, NF4double4bit/BF16/SDPA. Batch1,do_samplefalse,seed42,max_new_tokens1024,repeat1,generation_retry0. No temperature argument forced under greedy.

Inputs1280x720RGB,8frames; cap200704/min3136; Story3columns480x270+32aliasstrip,1440x906,global resize; VideoNDarray explicit flag only scheduled Video, do_sample_framesFalse, temporalpatch2/fourunits, second_per_grid_ts=2/fps; FPS reconstructed from private synthetic span, no native PTS header. FRAME_MATCHED_ONLY, not equal time/token/detail information or eight independent time positions. Only supplied processor-consumed F aliases, no citation policy change.

Safety load120s/generation300s/request330s/whole3200s, loadfreeGPU>=10GiB/RAM>=8GiB, generationfreeGPU>=2GiB, globalGPUused<=14.5GiB, owned process-treeRSS<=20GiB, systemavailableRAM>=2GiB. Supervisor nominal1s samples, owned tree not only Python launcher. Samples not continuous absolute peaks. Model assets verified before load. Raw/start/runtime/completion receipts kept, raw fsync before validation.

Hard stops: protected hash mismatch; real/old media access; changed prompt/schema/Validator/parser/system; invalid preregistration; wrong model/quantization/attention; unsupported input/config; unsafe memory/time; unrecoverable missing/corrupted raw receipt. Parse/strict failure or low evolving pass count alone never stop scheduled matrix. One pre-execution bridge pin compatibility repair already used and versioned; no further runtime repair or retry budget in this execution. Pre-generation infrastructure retry budget0 (allowed maximum, conservatively not used). Any technical blocker => preserve INCOMPLETE, never replace a completed invalid output.

Classification precedence: missing scheduled conditions => REGRESSION_INCOMPLETE; all8complete with any authoritative strict failure => REGRESSION_FAIL; all8strictvalid but <3 model-emitted event-bearing outputs => STRUCTURAL_PASS_COVERAGE_INSUFFICIENT; only all8strictvalid and >=3 actual event-bearing => REGRESSION_PASS. Event-bearing is >=1 actual event object, not intended fixture label. Required event timing_uncertainty/root /uncertainty/window citations violations must all be zero for PASS. No physical accuracy interpretation.

Post-run warnings, no automatic verdict override: (1) >=3 event entries but all normalized timing_uncertainty identical (casefold,collapse whitespace); (2) >=12 consecutive normalized word tokens shared between generated uncertainty and candidate instructions, computed longest contiguous word match; (3) intendedzero emits events; (4) intendedone/multiple emits none; (5) known-state shadow checks expose concerns masked by structural early-return; (6) unsupported temporal precision; (7) unsupported target continuity; (8) membership-valid but evidentially questionable citations. 6-8 require visual judgment: automated syntactic flags are screening only, mark UNREVIEWED/NOT_ESTABLISHED instead of pretending a final visual decision. All outputs may be no-event/abstention without forcing branch coverage. Empty/null/omitted field findings preserved, never repaired.

No V1E, fixture replacement/redraw/selection after lock, decoder deployment, extra conditions, VariantA/B rerun or DEV inference. Adaptive development disclosed: V1D authored after V1C failures, new fixture population; 2/12 vs present8 is not a controlled improvement estimate. All freeze/scientific citation/identity/NONE/time matching/final prompt decisions remain human gates.
'''
    s.save('V1D_PREREGISTERED_CRITERIA.md',criteria)
    source={p.relative_to(s.ROOT).as_posix():s.sha(p) for p in (s.ROOT/'src/memory_graph/pass_t/phase2b').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for p in s.OUT.glob('*.py'):source[p.relative_to(s.ROOT).as_posix()]=s.sha(p)
    for p in [v1c,s.REF/'prompt_candidate/v2_system_unchanged.txt',s.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt',s.OUT/'model_assets.json',s.OUT/'FIXTURE_LOCK_RECEIPT.json',s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json']:
        source[p.relative_to(s.ROOT).as_posix()]=s.sha(p)
    run={'task_id':'PASS_T_PHASE2B_QWEN_NF4_V1D_MINIMAL_REPAIR_AND_SYNTHETIC_REGRESSION','order':order,
      'prompt_sha256':s.sha(inp.prompt_path()),'V1C_sha256':s.sha(v1c),'criteria_sha256':s.sha(s.OUT/'V1D_PREREGISTERED_CRITERIA.md'),
      'fixture_lock_sha256':s.sha(s.OUT/'FIXTURE_LOCK_RECEIPT.json'),'fixture_manifest_sha256':lock['fixture_manifest_sha256'],
      'run_order_sha256':fixture['run_order_sha256'],'source_sha256':source,
      'media_sha256':fixture['media_assets_sha256'],'CPU_receipt_sha256':{p.relative_to(s.ROOT).as_posix():s.sha(p) for p in (s.OUT/'cpu').glob('*.json')},
      'model_assets':assets,'generation':{'max_output_tokens':1024,'sampling':False,'seed':42},
      'generation_effective_expected':{'max_new_tokens':1024,'do_sample':False,'max_time':300},
      'repeat':1,'batch_size':1,'generation_retry':0,'infrastructure_retry':0,'warmup_calls':0,'scheduled_calls':8,
      'coverage':{'actual_event_bearing_min':3},'timeouts_s':{'load':120,'generation':300,'request':330,'whole':3200},
      'resources':{'global_gpu_used_gib':14.5,'owned_tree_rss_gib':20,'load_free_gpu_gib':10,'load_free_ram_gib':8,'generation_free_gpu_gib':2,'system_ram_floor_gib':2,'sampling_nominal_s':1},
      'warning_rule':'exact rules in V1D_PREREGISTERED_CRITERIA.md, fixed before outputs',
      'repair':{'pre_execution_runtime_pin_extension':1,'GPU_recovery_remaining':0,'diff_sha256':s.sha(s.OUT/'BRIDGE_V1D_PIN_REPAIR.patch')},
      'processor':{'max_pixels':200704,'min_pixels':3136,'source_dimensions':[1280,720],'storyboard':[1440,906],
        'video_temporal_patch_size':2,'video_mode':'NATIVE_ARRAY_EXPERIMENTAL','nonvideo_mode':'NATIVE_VIDEO_ARRAY_DISABLED'},
      'identity_clause_enabled':False,'target_reference':'NONE','protocol_frozen':False,'real_DEV_allowed':False}
    s.save('V1D_PREREGISTERED_EXECUTION_MANIFEST.json',run)
    s.save('EXECUTION_LOCK_RECEIPT.json',{'manifest_sha256':s.sha(s.OUT/'V1D_PREREGISTERED_EXECUTION_MANIFEST.json'),
      'criteria_sha256':run['criteria_sha256'],'locked_at_unix':s.time.time(),'fixture_lock_unix':lock['created_at_unix'],
      'prompt_authored_unix':author['authored_at_unix'],'model_loads_before_lock':0,'model_generations_before_lock':0,
      'kind':'ENGINEERING_EXECUTION_PREREGISTRATION_NOT_PROTOCOL_FREEZE'})
    for p in [s.OUT/'V1D_PREREGISTERED_EXECUTION_MANIFEST.json',s.OUT/'V1D_PREREGISTERED_CRITERIA.md',s.OUT/'EXECUTION_LOCK_RECEIPT.json']:p.chmod(0o444)
    print('EXECUTION_LOCKED',s.sha(s.OUT/'V1D_PREREGISTERED_EXECUTION_MANIFEST.json'),flush=True)

if __name__=='__main__':main()
