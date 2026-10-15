"""Standard-library, source/metadata-only review publisher. Never imports runtime code."""
import sys
sys.dont_write_bytecode=True
import os, json, hashlib, subprocess, datetime, collections, re
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
os.environ['GIT_OPTIONAL_LOCKS']='0'
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
ACCESS=collections.Counter()
REFRESH=sys.argv[1:]==['refresh']

def audit(event,args):
    if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','PIL','cv2','tensorflow','huggingface_hub'}:
        raise RuntimeError('MODEL_OR_PIXEL_LIBRARY_IMPORT_PROHIBITED')
    if event.startswith('socket.'):raise RuntimeError('NETWORK_PROHIBITED')
    if event=='subprocess.Popen':
        argv=args[1]
        allowed=(isinstance(argv,(list,tuple)) and argv[0]=='git' and argv[1] in {'rev-parse','status','diff'}) or (isinstance(argv,str) and any(argv.startswith('git '+c+' ') for c in ['rev-parse','status','diff']))
        if not allowed:raise RuntimeError('ONLY_READONLY_GIT_ALLOWED')
    if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
    p=Path(os.fsdecode(args[0])).resolve();mode,flags=args[1:3]
    writing=(isinstance(mode,str) and any(x in mode for x in 'wax+')) or (isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
    if writing:
        if not p.is_relative_to(OUT):raise RuntimeError('WRITE_OUTSIDE_NEW_REVIEW_DIRECTORY')
        ACCESS['new_directory_writes']+=1
    else:
        low=str(p).lower().replace('\\','/')
        if p.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.mp4','.avi','.mov','.mkv','.npy','.npz','.safetensors','.bin','.pt','.pth'} or '/.models/' in low or low.endswith('/external_dev_gt.json') or '/val_set/' in low:
            raise RuntimeError('MEDIA_WEIGHT_OR_RAW_GT_READ_PROHIBITED: '+str(p))
        if p.is_relative_to(ROOT):ACCESS['project_text_metadata_reads']+=1
sys.addaudithook(audit)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(o):return json.dumps(o,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def digest(o):return hashlib.sha256(canonical(o)).hexdigest()
def jr(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):
    p=OUT/n
    own_generated={'PRESERVATION_BEFORE.json','REVIEW_EVIDENCE_AND_PROPOSED_CONFIGURATION.json','FINAL_PILOT_PROTOCOL_CANDIDATE.md','HUMAN_APPROVAL_CHECKLIST.md','PILOT_COHORT_AND_GT_LIMITATIONS.md','STRICT_INVALID_AND_QUALITATIVE_REVIEW_POLICY.md','EXECUTION_READINESS_REPORT.md','UNRESOLVED_DECISIONS.md','PRESERVATION_REPORT.json','FINAL_COMPONENT_HASH_MANIFEST.json'}
    assert not p.exists() or (REFRESH and n in own_generated), 'EXCLUSIVE_NEW_DELIVERABLE_REQUIRED: '+n
    p.write_text(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(v).replace('|','\\|').replace('\n',' ') for v in row)+' |\n' for row in rows)
def git(*args):
    p=subprocess.run(['git',*args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    return p.stdout,p.stderr
def git_state():
    status,warnings=git('status','--porcelain=v1','--untracked-files=all')
    rel=OUT.relative_to(ROOT).as_posix()
    existing='\n'.join(x for x in status.decode().splitlines() if rel not in x)
    idx=Path(git('rev-parse','--git-path','index')[0].decode().strip())
    if not idx.is_absolute():idx=ROOT/idx
    staged,sw=git('diff','--cached','--binary','--no-ext-diff')
    unstaged,uw=git('diff','--binary','--no-ext-diff')
    return {'head':git('rev-parse','HEAD')[0].decode().strip(),'index_sha256':sha(idx),
        'staged_diff_sha256':hashlib.sha256(staged).hexdigest(),'worktree_diff_sha256':hashlib.sha256(unstaged).hexdigest(),
        'existing_status_sha256':hashlib.sha256(existing.encode()).hexdigest(),'existing_status_lines':len(existing.splitlines()),
        'git_warnings_sha256':hashlib.sha256(warnings+sw+uw).hexdigest(),'warnings_present':bool(warnings+sw+uw),
        'excluded_authorized_new_directory':rel}

B='artifacts/pass_t/phase2b'
V1D=B+'/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c'
V1C=B+'/qwen_nf4_engineering_closeout/20261015_94dcf4d4'
REF=B+'/prompt_clarification_matched8_preflight/qwen_nf4/20261015_rev2_4f1c8d251b1e'
OLD=B+'/preflight/qwen_nf4_protocol_candidates/v1/candidate_003'
DIAG='WORKSPACE/Pass_T/V1D_Contract_Diagnosis_20261015'
CODE='src/memory_graph/pass_t/phase2b'
SOURCES={}
def source(key,path,role):
    p=ROOT/path
    assert p.is_file(),path
    SOURCES[key]={'path':path,'sha256':sha(p),'role':role,'evidence_scope':'existing text/metadata/source only'}
    return p

source('E01',B+'/readiness/eligibility.json','Canonical seven-record eligibility; six admitted, one excluded')
source('E02',B+'/readiness/GT_ELIGIBILITY_LIMITATIONS.md','Exploratory-only GT limitations')
source('E03','artifacts/pass_t/phase2a/v2/reports/current_status_20261013_48a92354/PHASE2A_CURRENT_REPORT.md','Phase2a completion and sidecar/negative quality caveats')
source('E04','artifacts/pass_t/phase2a/v2/readiness_checks/20261013_negative_review/NEGATIVE_READINESS_REPORT.md','Negative review provenance and limitations')
source('E05',OLD+'/pilot_preregistration_draft.json','Historical unapproved pilot configuration and order')
source('E06',OLD+'/QWEN_NF4_PROTOCOL_DECISION_SHEET.md','Historical unresolved decisions')
source('E07',OLD+'/private/candidate_manifests.json','Existing Uniform8 sample positions/IDs/PTS/recorded image hashes')
source('E08',OLD+'/private/timing.json','Native source timing metadata and authorized frame counts')
source('E09',OLD+'/private/actual_container_pts_metadata.json','Old reencoded container timing; not native-array proof')
source('E10',REF+'/QWEN_NF4_PILOT_DECISION_PACKAGE_V3.md','C1/C2/C3 temporal-unit citation and decision alternatives')
source('E11',REF+'/freeze_blockers.json','All historical 21-item unresolved/resolved statuses')
source('E12',V1D+'/PASS_T_PHASE2B_QWEN_NF4_V1D_REGRESSION_REPORT.md','V1D failed structured-output regression')
source('E13',V1D+'/V1D_HUMAN_PILOT_DECISION_PACKAGE.md','Prior V1D warning and approval gates')
source('E14',V1D+'/V1D_REGRESSION_SUMMARY.json','Existing eight-call result counts')
source('E15',V1D+'/V1D_PREREGISTERED_EXECUTION_MANIFEST.json','Synthetic generation, resource and timeout settings')
source('E16',V1D+'/QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt','Immutable proposed task prompt')
source('E17',REF+'/QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt','Immutable V1C comparison prompt')
source('E18',REF+'/prompt_candidate/v2_system_unchanged.txt','Immutable V2 system formatting')
source('E19',DIAG+'/diagnosis_report.md','D4 diagnosis, scoped limitations')
source('E20',DIAG+'/diagnosis_decision.json','No observed C1-C3 defect; not a pass or approval')
source('E21',DIAG+'/final_verification.json','Completed diagnosis preservation verification')
source('E22',CODE+'/contracts/prediction_v1.json','Prediction V1 nonempty schema')
source('E23',CODE+'/predictions.py','Authoritative strict parser and validation')
source('E24',CODE+'/local_vlm/nf4.py','Shared existing Qwen NF4 runtime')
source('E25',CODE+'/local_vlm/video_array_bridge.py','Native array route; synthetic-only V1D pin')
source('E26',CODE+'/local_vlm/qwen_contract.py','Task/schema/system serialization and generation controls')
source('E27',CODE+'/local_vlm/transport.py','Legacy HTTP transport modality and permission gates')
source('E28',CODE+'/protocol.py','Legacy freeze protocol and base prompt pin')
source('E29',CODE+'/inference.py','Legacy authorized pilot executor')
source('E30',CODE+'/evaluation.py','Existing event-local greedy one-to-one matcher')
source('E31',V1D+'/supervisor.py','Synthetic supervisor resource and wall-time checks')
source('E32',V1D+'/inputs.py','Synthetic-only deployment; not a real deployment')
source('E33',V1D+'/V1D_RESOURCE_REPORT.json','Observed synthetic resource limits, not new capacity run')
source('E34',V1C+'/PASS_T_PHASE2B_QWEN_NF4_ENGINEERING_CLOSEOUT_REPORT.md','V1C engineering closeout') if (ROOT/V1C/'PASS_T_PHASE2B_QWEN_NF4_ENGINEERING_CLOSEOUT_REPORT.md').exists() else None
source('E35',REF+'/QWEN_NF4_MATCHED_VIDEO8_CPU_PREFLIGHT_REPORT.md','Existing CPU matched-frame evidence')
source('E36',B+'/config/protocol_decisions.template.json','Historical decision field requirements')
source('E37',CODE+'/model_visible.py','Permitted model-visible payload contract')
source('E38',CODE+'/config.py','Existing model/generation config checks')

elig=jr(ROOT/SOURCES['E01']['path']); cm=jr(ROOT/SOURCES['E07']['path']);timings=jr(ROOT/SOURCES['E08']['path'])
opaque={x['private_item_id']:x['opaque_id'] for x in jr(ROOT/SOURCES['E05']['path'])['cohort']}
members=sorted([x for x in elig['records'] if x['pilot_scoring_permission']!='AUDIT_ONLY_NO_MODEL_RUN'],key=lambda x:(int(x['source_video_identifier'].removeprefix('test')),x['original_pack_ids'][0]))
assert len(members)==6
cohort=[];metadata_checks=[]
for e in members:
    item=e['annotation_item_id'];oid=opaque[item];key='INPUT-'+oid
    sp=source(key,OLD+'/private/'+oid+'/source.json','Existing authorized frame-list metadata; no image opened')
    src=jr(sp);frames=src['frames'];t=next(x for x in timings if x['item_id']==item)
    m=next(x for x in cm if x['item_id']==item and x['name']=='UNIFORM_8_MULTI_IMAGE')
    sb=next(x for x in cm if x['item_id']==item and x['name']=='UNIFORM_8_STORYBOARD')
    positions=[round(i*(len(frames)-1)/7) for i in range(8)]
    assert positions==m['sampling']['positions']==sb['sampling']['positions']
    selected=[frames[i] for i in positions]
    assert [x['frame_id'] for x in selected]==m['sampling']['native_frame_ids']==sb['sampling']['native_frame_ids']
    assert [x['source_timestamp_s'] for x in selected]==m['sampling']['native_pts_s']==sb['sampling']['native_pts_s']
    assert all(x['timestamp_provenance']=='NATIVE_PTS' for x in selected)
    assert len({x['frame_id'] for x in selected})==8
    assert all(b['source_timestamp_s']>a['source_timestamp_s'] for a,b in zip(selected,selected[1:]))
    aliases=[Path(s).stem for s in m['media_files']]
    assert len(aliases)==8 and all(re.fullmatch(r'F\d{4}',a) for a in aliases)
    assert m['reference_policy']=='TARGET_REFERENCE_NONE_CANDIDATE_ONLY' and m['reference_count']==0 and sb['reference_policy']=='TARGET_REFERENCE_NONE_CANDIDATE_ONLY' and sb['reference_count']==0
    # Preserve recorded frame hashes, but never reopen actual media bytes.
    mappings=[{'supplied_alias':a,'source_frame_id':s['frame_id'],'source_frame_index':s['source_frame_index'],'native_source_pts_s':s['source_timestamp_s'],'recorded_source_png_sha256':s['sha256']} for a,s in zip(aliases,selected)]
    fps=7/(selected[-1]['source_timestamp_s']-selected[0]['source_timestamp_s'])
    c={'item_id':item,'opaque_id':oid,'original_pack_ids':e['original_pack_ids'],'permission':e['pilot_scoring_permission'],
       'original_full_window_eligible':e['original_v2_full_window_eligible'],'formal_benchmark_permission':False,
       'independent_visual_review_status':e.get('independent_visual_review_status'),'visual_review_limitations':e.get('visual_review_limitations'),
       'final_exhaustiveness_status':e.get('final_exhaustiveness_status'),'supported_positive_event_ids':e.get('supported_positive_event_ids'),
       'source_frame_count':len(frames),'source_first_frame':frames[0]['frame_id'],'source_last_frame':frames[-1]['frame_id'],
       'reported_half_open_frames':t.get('half_open_frames'),'native_source_video_sha256_recorded':t['source_video_sha256'],
       'uniform8_positions':positions,'selected_mapping':mappings,
       'native_array_fps_derived_from_span':fps,'native_array_second_per_grid_ts_proposed':2/fps,
       'temporal_units':[{'unit':i,'supplied_aliases':aliases[2*i:2*i+2], 'native_source_pts_s':[s['source_timestamp_s'] for s in selected[2*i:2*i+2]]} for i in range(4)],
       'old_image_manifest_payload_sha256_not_V1D':m['payload_sha256'],'old_image_manifest_rendered_chat_sha256_not_V1D':m['rendered_chat_sha256'],
       'recorded_reference_policy':m['reference_policy'],
       'media_integrity_status':'EXISTING_METADATA_VERIFIED_NOT_CURRENT_MEDIA_BYTES_REHASHED',
       'real_V1D_rendered_prompt_sha256':None,'real_native_array_execution_receipt':None}
    cohort.append(c)
    metadata_checks.append({'item_id':item,'uniform_rule_reproduced':True,'MI_storyboard_same_selection':True,'native_PTS_list_matches_source_metadata':True,
                            'all8_unique_increasing':True,'reference_none':True,'existing_source_image_bytes_reverified':False,
                            'source_metadata_sha256':sha(sp),'sampling_manifest_sha256':SOURCES['E07']['sha256']})

# Authority inventory: preserve selected metadata and all relevant source files, not media/model files.
protected={ROOT/x['path'] for x in SOURCES.values()}
protected.update(p for p in (ROOT/CODE).rglob('*') if p.is_file() and p.suffix in {'.py','.json'})
for folder in [ROOT/V1D,ROOT/V1C,ROOT/DIAG]:
    protected.update(p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in {'.md','.json','.jsonl','.csv','.txt','.py','.patch','.xml'})
for n in ['AGENTS.md','WORKSPACE/Pass_T/LATEST_REPORT.md','WORKSPACE/Pass_T/LATEST_DECISIONS.md','WORKSPACE/Pass_T/README.md','WORKSPACE/Pass_T/RESULTS.csv']:
    if (ROOT/n).exists():protected.add(ROOT/n)
for run in (ROOT/V1D/'runs').iterdir():
    cp=jr(run/'completed.json')
    assert sha(run/'raw_output.txt')==cp['raw_response_sha256']
    assert sha(run/'runtime_receipt.json')==cp['runtime_receipt_sha256']
before={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(protected)}
git_before=git_state()
put('PRESERVATION_BEFORE.json',{'files_sha256':before,'git':git_before,'scope':'Existing text/source/metadata only; no media or weight bytes read'})

assert SOURCES['E16']['sha256']=='7008254e618dc8bacdbdeaae3cbf471220afb5efd6c80afc8b9ea5fb5c96b9b0'
assert SOURCES['E17']['sha256']=='3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722'
assert jr(ROOT/SOURCES['E20']['path'])['primary']=='D4_NO_DEFECT_FOUND'
schema=jr(ROOT/SOURCES['E22']['path']);assert schema['properties']['uncertainty']['minLength']==1

DECISIONS=[]
def dec(i,title,value,evidence,risk='Awaiting explicit human approval',status='PROPOSED_AWAITING_HUMAN_APPROVAL'):
    DECISIONS.append({'id':i,'decision':title,'proposed_value':value,'evidence':evidence,'remaining_limitation':risk,'human_approval_status':status})
dec('H01','Failed-regression risk acceptance','Use immutable V1D for exploratory hypotheses despite strict 1/8; six event-bearing outputs all invalid',['E12','E13','E14','E19'],'Explicit exception to prior decision package warning; D4 did not turn REGRESSION_FAIL into PASS')
dec('H02','Model/revision','Existing local Qwen2.5-VL-7B-Instruct NF4 double quantization, BF16, SDPA; revision cc594898137f460bfe9f0759e9844b3ce807cfb5',['E15','E24'],'Existing asset receipts only; weights not reopened and no model substitution')
dec('H03','Prompt/system/schema','Exact V1D + unchanged V2 + unchanged Prediction V1/parser/validator; no V1E',['E16','E18','E22','E23'],'Full 18 real-input serialized hashes not captured or newly built')
dec('H04','Representation choice','All three representations, 8 source frames each; 18 planned calls, no 12-call fallback',['E10','E13','E25'],'Native route not presently real-DEV capable; T01/T02')
dec('H05','Sampling','Uniform8 round(i*(N-1)/7), Python ties-to-even, include endpoints; same selection all representations',['E07','E08'],'Can miss brief transitions; no offset/GT-driven frame selection')
dec('H06','Target reference and ambiguity clause','NONE for all six windows; no new identity-ambiguity clause; existing prompt/outcomes unchanged',['E10','E13','E16','E37'],'Opaque TARGET_A can remain ambiguous; this protocol does not authorize global identity or an implicit new prompt instruction')
dec('H07','Citation C3','Retain supplied per-frame aliases; native 8 aliases / 4 temporal units disclosed in report only',['E10','E25'],'No unit-level validator replacement, invented alias, precision claim or claim model distinguishes both paired frames')
dec('H08','Native time contract','FRAME_MATCHED_ONLY; private native source PTS authoritative; fps=7/(last-first), seconds/unit=2/fps, do_sample_frames=False',['E25','E07','E08'],'Model time is not native PTS faithful; no extra timestamp text/header; actual position_ids not instrumented')
dec('H09','Pixel/layout budget','min_pixels=3136, max effective spatial pixels=200704; storyboard 3 columns, 480x270 tile +32 alias row, 1440x906 canvas',['E15','E24','E25','E26','E07'],'Equal selected source frames does not imply equal visual token budget or retained detail; real grids must be logged later')
dec('H10','Generation','Greedy do_sample=False; seed42; max_new_tokens=1024; repeat1; temperature/top_p/top_k inactive',['E15','E26'],'Seed is not cross-platform determinism; no stability study or extra warmup')
dec('H11','Timeouts','load120s, generation max_time300s, supervised request330s; whole pilot6060s from load-start (derived 120+18*330)',['E05','E15','E31'],'6060s is a new proposed whole-run bound, not the old 8-call synthetic whole3200s; no verified real supervisor yet')
dec('H12','Hardware gates','Before load free GPU>=10GiB/RAM>=8GiB; generation free GPU>=2GiB; stop global GPU>14.5GiB, owned-tree RSS>20GiB or available RAM<2GiB; 1s nominal polling',['E15','E24','E31'],'Historical synthetic enforcement/measurements only; transient peaks can occur between polls; current free resources not probed')
dec('H13','Failure/retry/continuation','No generation-quality retry or automatic repair; proposed transport pre-generation retry0; continue on strict-invalid JSON if healthy; stop on hardware breach/OOM/process failure/deadline, mark remaining NOT_EXECUTED',['E05','E13','E29','E31'],'Changes historical proposed transport retry1 to explicit conservative retry0; no calls hidden as warmups or replacements')
dec('H14','Time sensitivity and matching','All 0,0.2,0.5s equally reported; greedy one-to-one closed-interval gap=max(0,GT_start-PRED_end,PRED_start-GT_end), require_overlap=False, stable GT then prediction order; TIMING_UNKNOWN unmatched/unresolved',['E10','E30'],'0.2 is not privileged; existing E30 interior-point case disagrees with proposed closed-interval semantics (T04); no matcher repair here; no optimal-cardinality or invented midpoint/duration claims')
dec('H15','Cohort and GT permissions','Three negative units, two nonexhaustive known PICKUP units, one uncertain; test1 W03/W05 deduplicated; exclude test3 W07',['E01','E02','E03','E04'],'No validated PLACEMENT positive; independent negative quality review incomplete; causality/session independence unestablished')
dec('H16','Strict-invalid exclusion and qualitative retention','Every raw unchanged; full-strict valid only in structured matching; separate syntax/schema/semantic/citation/full status; invalid not NO_EVENT',['E22','E23','E29','E30'],'Validator early-return must remain; unassessed stages reported NOT_ASSESSED, not false PASS; T03')
dec('H17','Physical reasoning assessment','Qualitative manual support review separate from schema/GT matching; unsupported/uncertain/unreviewed remain distinct; no new adjudicated labels here',['E13','E19','E02'],'No physical correctness inferred solely from event claim, match or schema validity')
dec('H18','Reporting and metrics','Execution/contract counts, known-event case matching, negative case alerts, uncertain descriptive review, representation descriptions only',['E01','E02','E30'],'No accuracy/precision/recall/F1/FPR/hallucination rate/generalization/statistical superiority')
dec('H19','Run order/budget','18 deterministic prospective rows; sha256 UTF8 PASS_T_PILOT_ORDER_V1/opaque/representation/NONE/1; one repeat, no extra generations, local API budget USD0',['E05','E10'],'Order regenerated for final NONE/native-array labels, not reuse obsolete unresolved-reference order; no measured USD hardware cost')
dec('H20','Model-visible information and time disclosure','Neutral supplied aliases, authorized media, exact V1D/V2/schema only; private PTS/GT/eligibility/tracker and review metadata excluded',['E16','E18','E26','E37'],'No new model-visible time map; native time distortions disclosed privately/report-only')
dec('H21','Freeze vs execution approval','Separate explicit freeze-only authorization; later separately authorize exactly18 real calls after technical blockers resolved',['E28','E29','E13'],'This request approves preparation only; flags/env values/old synthetic approvals grant no real-run authorization')

TECH=[
 {'id':'T01','severity':'BLOCKING_REAL_NATIVE_V1D','source':'E25 lines74-79','fact':'V1D prompt pin requires synthetic_only=True; honest real DEV deployment must not impersonate synthetic data.',
  'needed':'Separately authorized future implementation review for a real-DEV V1D route, preserving the prompt/schema and approval boundary; no bypass/patch in this task.'},
 {'id':'T02','severity':'BLOCKING_AS_IS_FREEZE_AND_18_CALL_RUNNER','source':'E27 lines75-79, E28 lines17-18/92-99, E29; existing prepared deployments',
  'fact':'Legacy freezer pins templates/event_reasoning_prompt_v1.txt; transport/prepared configurations use MULTI_IMAGE/STORYBOARD/REENCODED_AUTHORIZED_VIDEO and synthetic allowlists, not the proposed complete V1D native-array protocol. No verified approved real V1D 18-call manifest/config exists.',
  'needed':'Future source/metadata-only integration authorization and newly reviewed component hashes before a supported freeze; do not label the present legacy path ready.'},
 {'id':'T03','severity':'UNVERIFIED_INTEGRATED_REPORTING_AND_GATING','source':'E23/E29/E30',
  'fact':'Strict validator early returns on schema errors; evaluator accepts a prediction object and has no built-in full-strict-status parameter. Existing primitives do not alone prove all18 calls are gated and all3 sensitivities/stages are reported.',
  'needed':'Before actual execution, verify a caller gates matching on full strict validity and reports unassessed stages without repair; no evaluator/schema changes authorized now.'},
 {'id':'M01','severity':'UNVERIFIED_CURRENT_MEDIA_INTEGRITY_AND_REAL_SERIALIZATION','source':'E07/E08 plus six INPUT metadata files',
  'fact':'Uniform8/native PTS/source IDs/recorded hashes verified against existing JSON; no source media bytes, actual video pixels, real native arrays or final18 V1D processor receipts were opened/created.',
  'needed':'Do not invent current media/payload hashes. Actual file integrity and real input receipts remain future authorized preflight/execution gates.'},
 {'id':'T04','severity':'BLOCKING_CLOSED_INTERVAL_MATCH_SEMANTICS','source':'E30 lines36-45',
  'fact':'For nonzero-width GT intervals and a predicted point strictly inside, overlap length is zero and E30 uses distance to an endpoint instead of zero interval gap. Thus current implementation can reject a contained point at tolerance0. No actual GT times were opened to determine which six-window cases would trigger it.',
  'needed':'Human must approve the intended closed-interval rule (H14), then separately authorize and verify minimal matcher integration/correction before scoring/freeze; do not silently use the current edge-case behavior or change evaluator in this task.'}
]
settings={'model':'Qwen/Qwen2.5-VL-7B-Instruct','revision':'cc594898137f460bfe9f0759e9844b3ce807cfb5','quantization':'NF4 double/BF16/SDPA',
 'task_prompt_sha256':SOURCES['E16']['sha256'],'system_sha256':SOURCES['E18']['sha256'],'prediction_schema_sha256':SOURCES['E22']['sha256'],
 'representations':['MULTI_IMAGE','STORYBOARD','NATIVE_VIDEO_ARRAY'],'frames_per_window':8,'sampling':'GT_INDEPENDENT_UNIFORM_8_ROUND_TIES_TO_EVEN_ENDPOINTS',
 'reference':'NONE','citation_policy':'C3_RETAIN_SUPPLIED_ALIASES_REPORT_ONLY_TEMPORAL_UNITS','native_video':'FRAME_MATCHED_ONLY',
 'source_time_authority':'NATIVE_SOURCE_PTS_PRIVATE','video_units':4,'native_fps_rule':'7/(PTS_last-PTS_first)', 'native_video_do_sample_frames':False,
 'max_pixels':200704,'min_pixels':3136,'storyboard':{'columns':3,'tile':[480,270],'label_row_height':32,'canvas':[1440,906]},
 'generation':{'do_sample':False,'seed':42,'max_new_tokens':1024,'repeat':1,'extra_warmup_calls':0},
 'timeouts_s':{'load':120,'generation':300,'request':330,'whole_proposed':6060},
 'hardware_gib':{'load_free_gpu_min':10,'load_free_ram_min':8,'generation_free_gpu_min':2,'global_gpu_used_stop_above':14.5,'owned_tree_rss_stop_above':20,'system_ram_stop_below':2},
 'retry':{'generation_quality':0,'transport_before_generation_proposed':0},'matching':{'sensitivities_s':[0,0.2,0.5],'bounded_interval_overlap_required':False,'algorithm_proposed':'greedy one-to-one closed-interval gap max(0,gs-pe,ps-ge); tie GT index then prediction index','current_source_discrepancy':'T04 interior predicted point inside bounded GT'},
 'strict_invalid_structured_matching':False,'automatic_repair':False,'new_identity_ambiguity_clause':False,'memory_graph_writes':False,
 'local_api_budget_limit_usd':0,'actual_calls_this_task':0,'planned_calls':18}
order=[]
for c in cohort:
    for rep in settings['representations']:
        key=f'PASS_T_PILOT_ORDER_V1/{c["opaque_id"]}/{rep}/NONE/1'
        order.append({'item_id':c['item_id'],'opaque_id':c['opaque_id'],'representation':rep,'repeat':1,'order_key_sha256':hashlib.sha256(key.encode()).hexdigest()})
order.sort(key=lambda x:x['order_key_sha256'])
for i,x in enumerate(order,1):x['proposed_call_index']=i
prior=jr(ROOT/SOURCES['E11']['path'])['items']
crosswalk={
 '1 collect-all replay':'Historical resolved; keep diagnostic non-gating. H16.',
 '2 Validator hash unchanged':'Preserved in E23, not weakened. H03/H16.',
 '3 known-state taxonomy':'Preserve schema/source; no new taxonomy. H03.',
 '4 prompt candidate approved':'H01/H03: propose V1D, not old V1C. PENDING.',
 '5 identity clause approved/rejected':'H06: do not add the optional clause. PENDING.',
 '6 fixtures locked before prompt':'Historical completed; no new fixtures. Not a new pilot gate.',
 '7 regression design approved':'Historical V1D completed; no new regression authorized. H01 accepts its limitation only if human approves.',
 '8 regression executed/reviewed':'Execution completed 8 calls; REGRESSION_FAIL remains. H01 risk acceptance PENDING.',
 '9 CPU preflight performed DEV/synthetic':'Historical metadata/CPU checks recorded; not new real V1D validation. M01.',
 '10 native/model-time mapping for approved use':'H08 FRAME_MATCHED_ONLY, native PTS only for authoritative matching. PENDING.',
 '11 runtime model-consumed alias policy/granularity':'H07 C3 retain aliases + report-only paired temporal-unit disclosure. PENDING; T01/T02.',
 '12 approved representation budgets':'H09 unchanged 200704/min3136/storyboard geometry. PENDING.',
 '13 point/interval/uncertain matching approved':'H14 closed-interval gap/no midpoint/unknown unresolved/one-to-one. PENDING; T04 current interior-point discrepancy.',
 '14 timing sensitivity approved':'H14 all 0/.2/.5 equally, no selected headline tolerance. PENDING.',
 '15 approved final model-visible prompt hashes':'H03 exact task/system/schema pinned; all18 real serialized hashes unavailable. T02/M01.',
 '16 generation settings approved':'H10/H11 greedy42/1024/repeat1/timeouts; PENDING.',
 '17 failure/retry approved':'H13/H16 no repair/no generation retry/transport0; PENDING.',
 '18 proposed run order fixed':'New final-label order is explicit 18 rows; H19 PENDING, not falsely old order unchanged.',
 '19 source cohort fixed':'E01 confirms same6; H15 PENDING exploratory permission/negative caveats.',
 '20 frame/fixture/sourceasset hashes verified':'Historical hashes retained; source media not rehashed. M01. No new fixture.',
 '21 explicit final protocol human approval':'H21 NOT_GRANTED; freeze/run separate.'}
assert set(prior)==set(crosswalk)
identity={'task':'PASS_T_PHASE2B_QWEN_NF4_FINAL_PROTOCOL_REVIEW','status':'HUMAN_REVIEW_CANDIDATE_NOT_APPROVED_NOT_FROZEN',
 'proposed_settings':settings,'cohort':cohort,'run_order':order,'decisions':DECISIONS,'technical_findings':TECH,'source_components':SOURCES,'prior_decisions':crosswalk}
package_sha=digest(identity);package_id=package_sha[:12]
approval=f'APPROVE_PHASE2B_QWEN_NF4_EXPLORATORY_PROTOCOL {package_id} FREEZE_ONLY NO_EXECUTION'
put('REVIEW_EVIDENCE_AND_PROPOSED_CONFIGURATION.json',{'candidate_semantic_sha256':package_sha,**identity,'metadata_checks':metadata_checks,'historical_blocker_statuses':prior})

def evidence_text(keys):return ', '.join('`'+x+'`' for x in keys)
cohort_table=table(['視窗（去重單位）','Item ID / opaque ID','用途','既有來源 frames / PTS span'],
 [[' / '.join(c['original_pack_ids']),c['item_id']+' / '+c['opaque_id'],c['permission'],f"{c['source_first_frame']}–{c['source_last_frame']} ({c['source_frame_count']} frames); {c['selected_mapping'][0]['native_source_pts_s']:.6f}–{c['selected_mapping'][-1]['native_source_pts_s']:.6f}s"] for c in cohort])
decision_table=table(['ID / decision','Proposed value','Evidence','Human approval','Limitation'],[[d['id']+' '+d['decision'],d['proposed_value'],evidence_text(d['evidence']),d['human_approval_status'],d['remaining_limitation']] for d in DECISIONS])
technical_table=table(['ID','Readiness finding','Evidence','Required follow-up'],[[t['id']+' '+t['severity'],t['fact'],t['source'],t['needed']] for t in TECH])
source_table=table(['Evidence','Existing source','SHA-256'],[[k,f"[{Path(v['path']).name}]({(ROOT/v['path']).as_posix()})",v['sha256']] for k,v in SOURCES.items()])
setting_table=table(['Component','Proposed value / exact source'],[
 ['Model','Existing Qwen2.5-VL-7B-Instruct NF4 double / BF16 / SDPA; revision '+settings['revision']+' (E15/E24)'],
 ['Task/system','Exact immutable V1D (E16), exact V2 system (E18), existing schema (E22); no new identity clause'],
 ['Representations','Multi-image8 / Storyboard8 / Native Video Array8; same Uniform8 source set; six windows × three =18 planned calls'],
 ['Sampling','round(i*(N-1)/7), i=0..7, Python ties-to-even over authorized ordered frame list; endpoints; no GT event positions'],
 ['Reference/citations','NONE; C3 retains supplied frame aliases; paired video units reported privately, no change to validator'],
 ['Native video','FRAME_MATCHED_ONLY, 8 source frames→4 units, no dropped frames/no padding, do_sample_frames=False; fps=7/source PTS span; native PTS remains private authority'],
 ['Pixels/storyboard','min3136/max200704 effective spatial pixels; tiles480×270 +32 label, 3columns, canvas1440×906; no new timestamp overlay'],
 ['Generation','do_sample=False; seed42; max_new_tokens1024; repeat1; warmup0; no quality retry'],
 ['Timeouts','load120 / gen300 / supervised request330 seconds; proposed whole6060 seconds (new bound, not old synthetic3200)'],
 ['Failure handling','Transport retry0 proposed; strict-invalid retained and continue if healthy; hard safety/process/deadline failures stop and preserve missing results'],
 ['Safety','load free GPU≥10GiB/RAM≥8GiB; generation freeGPU≥2GiB; stop usedGPU>14.5GiB, ownedRSS>20GiB, systemRAM<2GiB; nominal polling1s'],
 ['Matching','Full strict valid only; 0/.2/.5s all reported; proposed greedy one-to-one closed-interval gap=max(0,gs-pe,ps-ge), require_overlap=False; T04 prevents claiming current source fully implements this; unknown timing unmatchable, no invented midpoint'],
 ['Reporting','Four separate axes execution/contract/physical support/representation; no formal model metrics, no Memory Graph writes']])

put('FINAL_PILOT_PROTOCOL_CANDIDATE.md',f'''# Final Qwen NF4 Exploratory Pilot — 人工審查候選

Task: `PASS_T_PHASE2B_QWEN_NF4_FINAL_PROTOCOL_REVIEW`  
2026-10-15；Review ID **{package_id}**；candidate semantic SHA-256 `{package_sha}`。

**READY_FOR_HUMAN_REVIEW — NOT_APPROVED — NOT_FROZEN — EXECUTION_BLOCKED_AS_IS。** 這是可審閱的完整提案，不是已核准部署。既有 V1D strict 1/8 的失敗結果不變；D4 只排除可見的特定序列化/指令缺陷，未證明 physical reasoning 正確，也未解除任何人類 gate。

本次只讀既有文字、schema、metadata、manifest 和回條；未載入模型、CUDA、GPU、新 VLM generations，未讀／decode 真實 DEV 像素，未建立 fixtures、修改既有檔案/Phase2a GT、freeze、pilot、Memory Graph、commit/push。僅本 WORKSPACE 新目錄有新增文件；依 narrower scope 不更新既有 LATEST_REPORT/README。

## 1. 研究目的與四個獨立軸

主要目的：觀察 Qwen 在真實 FindMind 有限視窗是否提出有可見證據支持的 PICKUP/PLACEMENT 物理事件假說。

A. **Execution reliability**：計畫18、實際開始/完成/失敗/未執行數、OOM/timeout/EOS/cap、runtime/resource記錄。  
B. **Structured contract**：syntax/schema/semantic/citation/full strict 分開，分母明示。  
C. **Physical reasoning/support**：人工檢查可見狀態變化、target association、遮擋/缺口、cites 是否支持；不從 label claim 或 schema pass 推定 physical correctness。  
D. **Representation differences**：同六窗三表示的描述性對照；相同 source selection 不等於相同 token/detail/temporal precision，不宣稱 superiority。

VLM 負責事件假說；本次不重設 Event-to-Graph，未來 deterministic evidence normalization/Graph construction 不在此任務範圍。

## 2. Proposed configuration（所有值均待人工核准）

{setting_table}

三個 temporal sensitivities 都是固定 report 欄位；0.2s 不作唯一主結果、不依結果挑選 tolerance。native PTS 不用模型整數化時間或 sampling_gap/2 取代；before/after evidence brackets 也不自動等於物理事件 duration。

## 3. Exact six-window cohort

{cohort_table}

test1 W03/W05 是同一項，只跑一個單位；test3 W07 污染揭露維持排除。三 strict-negative 的原 attestation 不等於新增獨立全窗品質認證；兩 known PICKUP 不是 exhaustive positive；test8 不是 negative；沒有 validated PLACEMENT positive。詳 [cohort/GT 限制](PILOT_COHORT_AND_GT_LIMITATIONS.md)。

## 4. Strict-invalid preregistration

每個 raw output byte-for-byte 保存，不修文字、不補欄位、不發明引用、不放寬 parser/schema/validator。只有 full-strict valid 能進 authoritative structured matching。strict-invalid 不是 NO_EVENT，也不計為合法模型 abstention；只可另列 descriptive qualitative review。缺失/失敗/未執行保留原因及各階段狀態，不能從分母移除。詳 [strict-invalid 政策](STRICT_INVALID_AND_QUALITATIVE_REVIEW_POLICY.md)。

## 5. Prior evidence and risk

- V1C engineering closeout：既有12-call Variant B strict2/12、9個 event-bearing 均 invalid；不與後來新 fixtures 的 V1D 當作受控改善實驗。
- V1D：JSON8/8，full strict1/8，event-bearing6/8全部invalid；9個 timing_uncertainty 空、6個root uncertainty空、1個window citations空。既有原始回應/結果不變。
- D4_NO_DEFECT_FOUND：八次捕獲文字保留全部三段新增指令，無直接矛盾/空值範本；沒有 full historical token/pixel 值，故非底層路徑與模型能力的全面證明。
- 原 V1D 人工套件說不建議 freeze，candidate technically eligible=False；本新任務只授權提出探索性風險接受方案，**沒有把原 gate 改成 PASS**。H01 必須明確人工接受這個例外。

## 6. 現況與核准邊界

{technical_table}

目前 protocol **可供人工審查，但不能使用現有 legacy 路徑直接 freeze/執行**。特別不得將 real DEV 假標為 synthetic_only=True 來繞過 T01，不得退回 V1C、舊AVI或改少於18call作替代。T04另記目前matcher與候選closed-interval規則的不一致，不能先計分再決定解釋。

下一個人類核准字串：

`{approval}`

此字串表示對本候選值/風險的 freeze-only 明確授權要求，**本次未收到、未生效**；不代表 execution permission，也不授權本任務修改 source。即使未來收到，T01/T02/T04 的現有程式 gate/語義差異仍不能跳過；必須先另行授權所需整合、以更新後 component hashes 重新人工確認，才可使用支援的路徑 freeze。若任何候選內容或 component 改變，必須新的 review ID，不能沿用本次核准。這裡沒有提供可自動執行的 freeze 指令。

## 7. Proposed call order

排序 key=SHA256 UTF-8 `PASS_T_PILOT_ORDER_V1/{{opaque_id}}/{{representation}}/NONE/1`，升序；不依 GT/答案排序。舊 draft ref=UNRESOLVED/encoded-video 的 order 不直接沿用。

{table(['順序','opaque unit','representation'],[[x['proposed_call_index'],x['opaque_id'],x['representation']] for x in order])}

## 8. Exact component and evidence identities

[FINAL_COMPONENT_HASH_MANIFEST.json](FINAL_COMPONENT_HASH_MANIFEST.json) 列候選語義身分、全部 component SHA、文件 SHA、原8 raw/receipt SHA、六窗 metadata 和 proposed configuration。不是 freeze receipt。真實媒體 hash 只保留既有記錄，不假稱本次重新驗證；真實18個完整V1D序列化 hash 未建立。

{source_table}

Stop: human review only. Phase2b 尚未完成。
''')

put('HUMAN_APPROVAL_CHECKLIST.md',f'''# Human Approval Checklist — {package_id}

**全數 PROPOSED／未收到人工核准。** 使用者授權建立此套件，不等於逐項 protocol approval。舊 synthetic deployment.approved=True、環境變數或舊 policy approval 不是 real pilot 授權。

{decision_table}

## 逐項歷史 blocker 對照（21/21）

{table(['歷史項目','舊狀態（不改寫）','此候選的處理/人工狀態'],[[k,prior[k],crosswalk[k]] for k in sorted(prior,key=lambda x:int(x.split()[0]))])}

## 其他歷史決策是否遺漏

- E06 reference localization/symmetry → H06：NONE一致，不加入額外 reference ablation；沒有證明 target唯一。
- E06 encoded-video V2 parity → E18/E24/E25 的 native synthetic 路徑已用同V2，但 real-native仍 T01/T02。
- E06 max_pixels vs actual resized grids → H09；source有effective cap，real receipts未驗證。
- E06 tolerance justification → H14三點全報，不假稱經正式校準。
- E06 matched-shape capacity → V1D已有synthetic資源紀錄 E33；非real DEV capacity認證，H12/M01。
- E10 holdout/regression alternatives → 現有 regression 已完成；不重開fixtures/warmup/repeats或新推論。
- E13 warnings/time/reference/cohort/science/freeze → H01/H06–H08/H15/H17/H18/H21皆明列。
- Historical transport retry1 → 本候選明確提議0（H13）；whole3200s → pilot6060s新提案（H11），皆未核准。

## 人類下一個明確授權

`{approval}`

只限 freeze-only protocol approval；不包含18call執行、source改動或Graph。現在尚有 T01/T02/T04 與 M01/T03 readiness gates，不能由該句自動跨越。若需要修整合，另提明確授權後產生更新套件/新 hashes，再人工確認；本候選未處理技術 blocker，也未設 approved=true。
''')

sampling_sections=[]
for c in cohort:
    sampling_sections.append('### '+' / '.join(c['original_pack_ids'])+' — '+c['item_id']+'\n\n'+
       table(['alias','source frame','native PTS (s)','recorded source PNG SHA-256'],[[m['supplied_alias'],m['source_frame_id'],repr(m['native_source_pts_s']),m['recorded_source_png_sha256']] for m in c['selected_mapping']])+\
       f"\nUniform source positions: `{c['uniform8_positions']}`. Native-array nominal fps from source span: `{c['native_array_fps_derived_from_span']}`; seconds/unit: `{c['native_array_second_per_grid_ts_proposed']}`. These are source-code-derived candidate metadata, not a new processor receipt.\n\n"+
       table(['unit','supplied alias pair','authoritative native PTS pair'],[[u['unit'],', '.join(u['supplied_aliases']),str(u['native_source_pts_s'])] for u in c['temporal_units']]))
put('PILOT_COHORT_AND_GT_LIMITATIONS.md',f'''# Six-window Cohort and GT Limitations

Review {package_id}；proposal only。Authority：E01/E02/E03；既有 GT dataset digest 記錄為 `ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c`。本次讀 eligibility/報告/來源 metadata，未重讀或變更原 GT 內容。

{cohort_table}

## Eligibility boundaries

1. **三 strict negatives**：test1 W03/W05 去重、test2 W01、test5 W01。原 full-window negative attestation/行政 reviewer resolution 被保留；test1 新增視覺 spot check 只有7/107 frames，test2/test5 W01 無新增獨立全窗視覺複核。只報個案 event alerts，不報FPR/hallucination rate，且 valid claim 仍需人工判讀。
2. **兩 known PICKUP**：test5 W05、test7 W05，NOT_ATTESTED/non-exhaustive；僅已支持 PICKUP 可探索性一對一 matching。後段遮擋不能證明持續拿著或排除後續事件。未列出的預測為 UNEVALUATED，不自動算 FP。不能合併其他 candidate 身分或解除既有target-association/causality限制。
3. **一 uncertain**：test8 W07，INSUFFICIENT_EVIDENCE，只 descriptive/abstention 分析；不轉成 NO_EVENT、不當完整負例。
4. **Excluded**：test3 W07 (`PT2A_0bfb99c324769681`) 保留污染/暴露排除，沒有模型call；負責人對誤勾的澄清不是解隔離。
5. 沒有 validated PLACEMENT positive，也沒有 exhaustive positive。全部 formal_benchmark_permission=false；causality/status與session獨立性未證實。不能報 accuracy、precision、recall、F1、false-positive rate、hallucination rate、generalization或統計優越性。

## Source/time metadata verification scope

六窗皆在既有 `private/source.json` ordered list 上重現 Uniform8（round ties-to-even）；與 E07 的 multi-image/storyboard 兩份名單/PTS一致，8個不同 source frame、native PTS嚴格遞增。未看 GT event location 來取樣。這驗證的是**既有metadata一致性**，不是目前影片bytes或內容未變。

保留 source list 原始frame IDs/PTS，不從概略 half-open window boundary推導或補入未授權影格。test1/test7 的 first supplied frame可晚於概略左邊界一格；不自動補影格或改GT。native timestamp 不從nominal FPS或舊FFV1 AVI container PTS反推。

真實影片／PNG 完全未開啟；`recorded_source_png_sha256` 和 source-video SHA只沿用既有metadata，未fresh rehash。既有sampling manifest的 payload/chat hashes來自舊prompt，**不能**稱為本V1D最終18call hashes。若無法僅用metadata完成現行媒體校驗，維持 M01 UNVERIFIED，不能為此偷讀像素。舊REENCODED_AUTHORIZED_VIDEO mapping不是新native-array時間忠實性證據。

## Per-window selected frames and private temporal units

以下是 review/evaluation 私有mapping，不進模型prompt；不得把native PTS字串額外塞入V1D或加到storyboard。C3保留供應alias，report-only揭露每2影格一unit；不能把8alias誤稱8獨立video temporal units。

{chr(10).join(sampling_sections)}

完整metadata SHA和逐項核對見 FINAL_COMPONENT_HASH_MANIFEST.json 與 REVIEW_EVIDENCE_AND_PROPOSED_CONFIGURATION.json。
''')

put('STRICT_INVALID_AND_QUALITATIVE_REVIEW_POLICY.md',f'''# Strict-invalid and Qualitative Review Policy — prospective

Review {package_id}；**awaiting human approval**。不修改 parser/schema/validator/GT，不重寫既有結果。

## Non-negotiable storage and eligibility

1. 每次模型回傳raw bytes原樣保存（含invalid JSON/Markdown/缺欄），記SHA、call ID、runtime/processor receipt、耗時/錯誤；不得strip、補JSON、填空uncertainty、發明citation或重新生成。
2. 分開報 JSON_SYNTAX、SCHEMA、SEMANTIC、CITATION、FULL_STRICT。權威 validator E23 在 schema failure 會early return；因此後續stage未跑時是 NOT_ASSESSED_DUE_TO_SCHEMA_FAILURE，不是假PASS或自動FAIL。若用既有collect-all helper，只能另列非權威diagnostic，不替換strict結果。
3. **只有FULL_STRICT=PASS且必要來源/引用mapping可驗證**的結構化結果，才能進authoritative matching。validity是格式/合約資格，不是physical truth認證。
4. 任一strict-invalid不得進authoritative matching；不得轉成NO_EVENT、模型abstention、零事件成功或自動FN。該單位matching記UNAVAILABLE_STRICT_INVALID，known GT保持未評估；保留無法產生可用結構的原因。
5. timeout/OOM/無raw/未執行，分別MISSING_TIMEOUT、MISSING_RUNTIME_FAILURE、NOT_EXECUTED_AFTER_STOP等；記已計畫18、已開始、完成、可解析、strict-valid及各層分母。不得以只剩少數valid的分母產生正式模型metrics。
6. generation-quality retry=0、automatic text repair=0、field filling=0、validator weakening=0；proposed transport retry=0，避免隱藏重複生成。strict-invalid在硬體健康時繼續固定計畫剩餘call；硬體/程序/timeout停止則保留剩餘NOT_EXECUTED。

## Authoritative structured matching — only applicable units

- 三 strict negatives：full-strict valid下報case-level event alert與人工支持審查；不是母體FP率。invalid不當negative成功。
- 兩known PICKUP：只match既有supported_positive_event_ids及同event type；target_association_uncertainty必須NONE（現有matcher條件），這個模型欄位本身不證明身分已正確；實際association仍需定性檢視。未列出的predicted events全部UNEVALUATED，不自動FP。
- test8 uncertain：不作event-list matching或negatives，只描述outcome、abstention與hypotheses。
- 禁止test3 W07進模型或matching。
- 各0/0.2/0.5秒均報；source native PTS authoritative。EXACT_FRAME是point，BOUNDED是closed evidence bracket，不推duration/midpoint；TIMING_UNKNOWN不能產生定時match。
- 提議採 `require_overlap=False`、greedy one-to-one，同type、closed-interval gap=`max(0,GT_start-PRED_end,PRED_start-GT_end)` ≤ tolerance；按(distance,GT index,pred index)排序，GT/pred各用一次，duplicate不多算。不是optimal maximum-cardinality；點在GT區間內的距離應為0，區間相交/端點相接亦為0；這只是時間相容，不證明事件或duration。
- **T04未解**：E30既有公式用strictly positive overlap length判斷相交，對GT有寬度、pred是內部point時會改用到endpoint的非零距離，與上述closed-interval規則不一致。這是靜態source可見的邊界缺口，未用真實GT或新增fixtures執行測試；本次不修matcher、不假稱新規則已實作，也不能悄悄採錯誤legacy行為。必須在freeze/scoring前另獲授權處理並重審hash。
- 無validated PLACEMENT positive；PLACEMENT假說只有個案定性價值，不生造新GT。

## Separately labeled qualitative review

對**strict-valid與strict-invalid分開**看現有raw事件假說，原raw/strict狀態永久保留。invalid中的文字可人工描述，但不能自動修成權威prediction或納入GT matching。

每一review項應記：call/representation、原raw SHA與原文引用、original validation status、可辨識的claim（無法解讀則UNINTERPRETABLE）、cited supplied aliases、可見physical transition與target association的支持/反證/缺口。結論用 SUPPORTED / NOT_SUPPORTED_BY_SUPPLIED_EVIDENCE / INDETERMINATE / UNREVIEWED；列實際reviewer及引文。沒有人工看過就維持UNREVIEWED；本任務未做real-pixel review，沒有新增任何此類標註。

定性結論是人對證據支持度的描述，不是authoritative structured prediction、不回填schema、不覆寫Phase2a GT、不自動稱hallucination/FP。不要因無相符特徵、遮擋或uncertainty字串為空就直接裁定physical event錯誤。

## Required disclosure

V1D synthetic regression **8/8 JSON、1/8 full strict；6/8 event-bearing全strict-invalid；9 timing空、6root空、1window cites空**。預期real pilot可能多數結構不可用；這不能透過repair或只報valid子集隱藏。定性假說研究仍需人工明確接受H01風險，不代表structured baseline已達標。
''')

readiness_rows=[
 ['Implemented and verified (existing evidence)','V1D/V2/schema/parser hashes、D4、V1D8次raw/receipt；synthetic native8→4unit/generation/safety歷史紀錄','E12–E26/E31/E33；既有合成結果非real validation'],
 ['Implemented and verified (metadata only)','六窗資格3negative/2known/1uncertain；Uniform8索引/native PTS/MI-SB同選擇','E01/E07/E08與六source JSON；未讀媒體'],
 ['Implemented but not verified for real DEV','NF4 model/greedy primitive、processor cap、native-array tensor route、supervision primitives','有synthetic執行證據；沒有本V1D real18call部署或receipts'],
 ['Proposed awaiting human approval','H01–H21全部：科學風險、targetNONE、C3、FRAME_MATCHED_ONLY、budgets/retries/timeouts/tolerances/order','候選語義完整；無批准/無freeze'],
 ['Missing or blocked','T01 real-native V1D gate；T02 legacy freeze/transport/config mismatch；T04 closed-interval point-containment discrepancy','現有source明確限制；不可以synthetic flag繞過或靜默改計分'],
 ['Missing or blocked/unverified','T03整合strict gating/分層報告/3sensitivities；M01current media完整性/final serialized hashes','保持UNVERIFIED；不以推測補metadata，不在此任務修source']]
put('EXECUTION_READINESS_REPORT.md',f'''# Execution Readiness Report — {package_id}

**Human review package READY；as-is execution NOT_READY；protocol NOT_FROZEN；Phase2b NOT_COMPLETE。**

{table(['Readiness class','What is established/proposed','Evidence and boundary'],readiness_rows)}

## Concrete blockers and source reconciliation

{technical_table}

`video_array_bridge.py` 74–79 的 `EXPLICIT_PINNED_SYNTHETIC_V1D_CANDIDATE_REQUIRED` 是真正technical blocker，不是等待按鈕或GPU記憶體不足。現行 prepared deployments.synthetic_only=true並沒有授權real DEV。legacy `protocol.prompt_path()` 仍固定 `templates/event_reasoning_prompt_v1.txt`；不能拿舊prompt freeze receipt為V1D背書。bridge in-process array≠legacy HTTP encoded-media route。現有freeze函式亦要求READY_TO_FREEZE、無unresolved與real_run_ready capabilities；此候選不滿足，未呼叫它。

matching primitives有one-to-one，但E30不直接接full-strict gate；E23 schema fail後不跑所有後段語義；因此整合呼叫端必須另有可查證gating和NOT_ASSESSED表示。T04另指出GT bounded interval內部的predicted point會因zero-length overlap被算到endpoint距離，而非closed-interval gap0；不知真實GT是否會觸發，因本次不讀GT事件內容。不能把候選規則寫成程式已實作。現有單一tolerance scalar可分別呼叫三次於未來evaluation，但沒有驗證本real18call報告已串接三點。

## Scope-limited checks performed

- 語法/模型沒有新執行；只用stdlib分析既有source/JSON/回條。
- metadata重現六窗Uniform8並與MI/SB取樣名單/PTS比對；全部通過，nativePTS provenance NATIVE_PTS、唯一/遞增。未開影像/影片，未重算其bytes hash。
- 原八raw/receipt SHA與原completed回條對照相符。V1C/V1D報告保持既有不同fixture/不同版本的非受控比較限制。
- source/設定證據列於hash manifest；model權重只沿用metadata revision，未讀取模型binary或重新驗證資產。
- 本次沒有GPU可用容量探測，過往resource資料不能替代未來before-load/call safety gate。
- 全部相關existing files與Git HEAD/index/staged/worktree比較詳PRESERVATION_REPORT.json；所有新增寫入均只在本目錄。Git snapshot受既有permission/long-path warnings及normalized diff範圍限制，不是全機證明。

## Next authorization and stop

人類審閱完H01–H21後，候選的下一個freeze-only授權格式是：

`{approval}`

**現在不能由此直接freeze。** T01/T02/T04要先在另獲授權的整合工作中解決並更新component manifest；若有hash/config變動，本ID失效，需新ID再次確認。此字串不自動授權source修改、real媒體開啟或18call。這是把所需人類決策說清楚，不是對可執行性或核准的推定。

本任務到此STOP：無freeze receipt、無run permission、無model/CUDA、新generation或Memory Graph。
''')

put('UNRESOLVED_DECISIONS.md',f'''# Unresolved Decisions — {package_id}

**21項human decisions全部PENDING；候選可審閱，執行仍阻擋。** Source review能證明既有實作/失敗，不能替人核准。

## 優先級 P0：不得繞過

{technical_table}

T01/T02/T04為as-is實際blocker；T03為整合驗證缺口；M01為現行媒體/真實serialized input證據缺口。後兩者不能用本次不允許的像素讀取/processor實作補完。T04不宣稱這六窗必定已計錯，只指出目前公式不完整實作候選的point/closed-interval契約。沒有新增模型權重下載問題，也沒有假稱目前RAM/VRAM足夠。

## 優先級 P1：人類必須決定

{table(['ID','Decision','Proposed value','Human status'],[[d['id'],d['decision'],d['proposed_value'],d['human_approval_status']] for d in DECISIONS])}

尤其：H01明確接受strict1/8風險；H06不加identity clause；H07/C3與H08/FRAME_MATCHED_ONLY接受配對unit限制；H14批准三點全報及closed-interval gap規則並處理T04；H15接受負例品質與nonexhaustive GT限制；H13/H11批准transport0與6060s新上限；H21區分freeze和execute。沒有任何項目因本文件寫了proposed就視為approved。

## 最小後續步驟

1. 人類先審閱本套件、接受或修改H01–H21及技術缺口。
2. 如要解T01/T02/T04，另外授權有界的integration/source工作；本任務不執行也不提出patch，不改prompt/schema/validator/GT，不重啟prompt優化。
3. 更新後candidate及component hashes再次交人類；只有supported freeze gate可用、readiness缺口明示且明確核准才freeze。此候選的授權識別句：`{approval}`。任何內容/hash改變需新ID，不可機械沿用。
4. freeze完成仍需新的explicit permission才可啟動18call；本次不存在該permission。不得先改成12call或V1C/AVIfallback以規避review。

不重設Event-to-Graph；先完成Qwen exploratory baseline的現有路徑。當前任務只交付review package，不稱Phase2b完成。
''')

# Read-only preservation and deliverable integrity. No self-referential hash in manifest.
after={name:sha(ROOT/name) for name in before}
git_after=git_state();git_keys=['head','index_sha256','staged_diff_sha256','worktree_diff_sha256','existing_status_sha256','existing_status_lines']
git_same={k:git_before[k]==git_after[k] for k in git_keys}
changed=[k for k in before if before[k]!=after[k]]
assert not changed and all(git_same.values()),'PRESERVATION_MISMATCH'
put('PRESERVATION_REPORT.json',{'status':'PASS','existing_files_compared':len(before),'existing_changed_files':changed,'before_sha256':before,'after_sha256':after,
 'git_before':git_before,'git_after':git_after,'git_equal':git_same,'new_write_scope':str(OUT),
 'no_model_or_pixel_modules_imported':not any(m.split('.')[0] in {'torch','transformers','PIL','cv2','tensorflow','huggingface_hub'} for m in sys.modules),
 'no_model_CUDA_generation_media_GT_write_freeze_pilot_graph_commit_push':True,
 'available_scope':'Observed tools + restricted stdlib script; not a native or machine-wide action trace; inaccessible Git paths not verified; current media/weight bytes not read.'})

required=['FINAL_PILOT_PROTOCOL_CANDIDATE.md','HUMAN_APPROVAL_CHECKLIST.md','PILOT_COHORT_AND_GT_LIMITATIONS.md',
 'STRICT_INVALID_AND_QUALITATIVE_REVIEW_POLICY.md','EXECUTION_READINESS_REPORT.md','UNRESOLVED_DECISIONS.md']
assert len(order)==18 and len({(x['opaque_id'],x['representation']) for x in order})==18
assert len({c['item_id'] for c in cohort})==6 and all('test3__W07' not in c['original_pack_ids'] for c in cohort)
assert collections.Counter(c['permission'] for c in cohort)=={'STRICT_NEGATIVE_CASE_ALERT_ANALYSIS':3,'KNOWN_EVENT_MATCHING_ONLY':2,'DESCRIPTIVE_UNCERTAINTY_ONLY':1}
assert all(d['human_approval_status']=='PROPOSED_AWAITING_HUMAN_APPROVAL' for d in DECISIONS)
assert all((OUT/n).is_file() for n in required)
docs={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='FINAL_COMPONENT_HASH_MANIFEST.json'}
component_manifest={'schema_version':'PASS_T_PHASE2B_FINAL_PROTOCOL_REVIEW_MANIFEST_V1','task_id':identity['task'],
 'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'HUMAN_REVIEW_CANDIDATE_NOT_APPROVED_NOT_FROZEN',
 'candidate_semantic_sha256':package_sha,'candidate_review_id':package_id,'approval_required_not_received':approval,'approval_granted':False,
 'freeze_ready_as_is':False,'execution_ready_as_is':False,'protocol_frozen':False,'actual_calls':0,'planned_calls':18,
 'source_components':SOURCES,'proposed_settings':settings,'cohort':cohort,'proposed_run_order':order,
 'technical_findings':TECH,'human_decisions':DECISIONS,'prior_blocker_crosswalk':crosswalk,'metadata_verification':metadata_checks,
 'new_deliverables_sha256':docs,'manifest_self_hash':'Not embedded: compute external SHA256 over this file; no circular self-hash',
 'model_weight_status':'Existing model asset metadata/revision only; binaries not loaded/read/rehashed',
 'real_media_status':'Existing recorded frame/video hashes retained, not currently byte-verified; no real pixels read',
 'final_real_rendered_prompt_hashes':'UNAVAILABLE_NOT_BUILT; old prompt payload/chat hashes must not be reused as V1D',
 'scope_and_access_counts':dict(ACCESS),'preservation_pass':True}
put('FINAL_COMPONENT_HASH_MANIFEST.json',component_manifest)
print(json.dumps({'status':'FINAL_PROTOCOL_PACKAGE_READY_FOR_HUMAN_REVIEW_EXECUTION_BLOCKED','review_id':package_id,
 'candidate_semantic_sha256':package_sha,'approval_required':approval,'existing_files_preserved':len(before),
 'manifest_sha256':sha(OUT/'FINAL_COMPONENT_HASH_MANIFEST.json'),
 'required_files_sha256':{n:sha(OUT/n) for n in required},'preservation_pass':True,'technical_blockers':['T01','T02','T04'],'verification_gaps':['T03','M01']},ensure_ascii=False))
