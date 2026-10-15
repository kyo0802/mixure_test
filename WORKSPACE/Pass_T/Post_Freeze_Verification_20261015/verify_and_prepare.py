"""CPU/text-only freeze verification. Never freeze, authorize, open media or run."""
import sys
sys.dont_write_bytecode=True
import os,json,hashlib,re,ast,secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
NAV={ROOT/'WORKSPACE/Pass_T/LATEST_REPORT.md',ROOT/'WORKSPACE/Pass_T/LATEST_DECISIONS.md',ROOT/'WORKSPACE/Pass_T/README.md'}
def guard(event,args):
    if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','PIL','cv2','tensorflow','huggingface_hub'}:raise RuntimeError('MODEL_OR_PIXEL_IMPORT_DENIED')
    if event.startswith('socket.'):raise RuntimeError('NETWORK_DENIED')
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        p=Path(os.fsdecode(args[0])).resolve();mode,flags=args[1:3]
        writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
        if writing and not (p.is_relative_to(OUT) or p in NAV):raise RuntimeError('WRITE_OUTSIDE_VERIFICATION_SCOPE')
        low=str(p).lower().replace('\\','/')
        if not writing and (p.suffix.lower() in {'.png','.jpg','.jpeg','.mp4','.avi','.mov','.pt','.bin','.safetensors','.npy','.npz'} or '/.models/' in low or low.endswith('/external_dev_gt.json')):raise RuntimeError('MEDIA_WEIGHT_GT_READ_DENIED')
sys.addaudithook(guard)
from memory_graph.pass_t.phase2b.common import canonical_bytes,digest,file_sha256,read_json,pretty_bytes,Phase2BBlocked
from memory_graph.pass_t.phase2b.v1d_protocol import verify_frozen,authorize_execution,decision_digest,VERSION,V1D_SHA,V2_SHA,SCHEMA_SHA,MODEL,REVISION,MATCHER

def put(n,value):
    p=OUT/n
    with p.open('x',encoding='utf8') as f:f.write(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n')

expected='c799b5d13a7721a02e88d25f9474081b6d5975bb2b6f71a72f61bf1ba7a00f02'
protocol_root=ROOT/'artifacts/pass_t/phase2b/v1d_protocols'
candidates=[]
for directory in sorted(protocol_root.iterdir()) if protocol_root.exists() else []:
    if (directory/'frozen_bundle.json').is_file():
        value=read_json(directory/'frozen_bundle.json')
        if value.get('freeze_receipt',{}).get('draft_sha256')==expected:candidates.append(directory)
assert len(candidates)==1, 'EXACTLY_ONE_AUTHORITATIVE_FREEZE_REQUIRED'
folder=candidates[0];bundle=read_json(folder/'frozen_bundle.json');receipt=read_json(folder/'completion_receipt.json')
draft=verify_frozen(bundle,ROOT);approval=bundle['protocol']['human_approval']
assert digest(canonical_bytes(draft))==expected
saved_draft=ROOT/'WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/DRAFT_CONFIGURATION_CANDIDATE.json'
assert read_json(saved_draft)==draft
assert receipt['files_sha256']=={'frozen_bundle.json':file_sha256(folder/'frozen_bundle.json')}
base_receipt={k:v for k,v in receipt.items() if k not in {'files_sha256','content_id'}}
assert digest(canonical_bytes({'files_sha256':receipt['files_sha256'],'receipt':base_receipt}))==folder.name==receipt['content_id']
assert all(receipt[k]==v for k,v in bundle['freeze_receipt'].items())
approval_folder=ROOT/'artifacts/pass_t/phase2b/v1d_freeze_approvals/20261015_reviewer_0_c799b5d13a77'
approval_file=approval_folder/'human_freeze_approval.json'
assert read_json(approval_file)==approval
assert approval['reviewer_id']=='reviewer_0' and approval['execution_authorized'] is False
assert approval['confirmation']=='APPROVE_PHASE2B_V1D_FREEZE '+expected+' NO_EXECUTION'
decisions=[]
assert len(approval['decisions'])==len(draft['human_decisions'])==21
for proposed,approved in zip(draft['human_decisions'],approval['decisions']):
    assert approved=={'id':proposed['id'],'decision_sha256':decision_digest(proposed),'status':'APPROVED'}
    decisions.append({**approved,'effective_human_reviewer':approval['reviewer_id'],'reviewer_record_scope':'The single human approval record explicitly covers the entire 21-decision list'})
assert [d['id'] for d in decisions]==[f'H{i:02d}' for i in range(1,22)]
calls=draft['run_order'];settings=draft['settings']
assert len(calls)==18 and [c['proposed_call_index'] for c in calls]==list(range(1,19))
assert len({(c['opaque_id'],c['representation']) for c in calls})==18 and len(draft['windows'])==6
assert {c['representation'] for c in calls}=={'MULTI_IMAGE','STORYBOARD','NATIVE_VIDEO_ARRAY'}
assert settings['task_prompt_sha256']==V1D_SHA and settings['system_sha256']==V2_SHA and settings['prediction_schema_sha256']==SCHEMA_SHA
assert settings['model']==MODEL and settings['revision']==REVISION and draft['matcher_policy']==MATCHER
assert settings['planned_calls']==18 and settings['reference']=='NONE' and settings['frames_per_window']==8
protected={ROOT/p:h for p,h in draft['components_sha256'].items()}
for path in [folder/'frozen_bundle.json',folder/'completion_receipt.json',approval_file,saved_draft,approval_folder/'FREEZE_VERIFICATION.json']:
    protected[path]=file_sha256(path)
assert all(file_sha256(p)==h for p,h in protected.items())

# Inspect only supported authoritative execution roots; never interpret CPU mocks
# in repair reports as real execution authorizations or actual model calls.
execution_roots=[]
for rel in ['artifacts/pass_t/phase2b/v1d_pilot_runs','artifacts/pass_t/phase2b/runs']:
    p=ROOT/rel
    entries=sorted(x.name for x in p.iterdir()) if p.exists() else []
    execution_roots.append({'path':rel,'exists':p.exists(),'entries':entries})
assert all(not r['entries'] for r in execution_roots), 'EXECUTION_RECORDS_REQUIRE_FURTHER_RECONCILIATION'
rejected={}
for name,b,a in [('missing_frozen_manifest',None,None),('missing_execution_authorization',bundle,None)]:
    try:authorize_execution(b,a,root=ROOT)
    except (Phase2BBlocked,KeyError,TypeError) as error:rejected[name]=str(error)
    else:raise AssertionError('GUARD_DID_NOT_REJECT:'+name)
assert rejected['missing_execution_authorization']=='SEPARATE_EXECUTION_AUTHORIZATION_REQUIRED'

source=ROOT/'src/memory_graph/pass_t/phase2b/v1d_execution.py'
text=source.read_text(encoding='utf8');lines=text.splitlines();tree=ast.parse(text)
guard_evidence=[]
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name in {'load_envelope','_worker','_runtime_factory','execute_authorized'}:
        guard_evidence.append({'function':node.name,'file':str(source),'sha256':file_sha256(source),'line_start':node.lineno,'line_end':node.end_lineno,
            'exact_source':'\n'.join(lines[node.lineno-1:node.end_lineno])})

proto_sha=bundle['freeze_receipt']['protocol_sha256']
confirmation='EXECUTE_PHASE2B_V1D '+proto_sha+' 18_CALLS'
# This is an ungranted proposal: confirmation/reviewer remain null. The actual
# validator will reject it. A random nonce and an expiry proposal grant nothing.
nonce=secrets.token_hex(16)
expiry='2026-10-16T07:54:51+00:00'
proposal={'status':'PROPOSED_NOT_AUTHORIZED','approval_received':False,'confirmation_required':confirmation,
    'authorization_fields':{'schema_version':VERSION+'_EXECUTION_AUTHORIZATION','confirmation':None,
      'protocol_sha256':proto_sha,'max_calls':18,'reviewer_id':None,'nonce':nonce,
      'expires_at_utc':expiry,'call_ids':list(range(1,19))},
    'expiry_taipei':'2026-10-16 15:54:51 +08:00','human_action_required':'Explicitly approve execution scope, supply execution reviewer ID, and accept/update nonce and expiry before creating the separate APPROVED file.'}
try:authorize_execution(bundle,proposal['authorization_fields'],root=ROOT)
except Phase2BBlocked as error:rejected['unapproved_proposal']=str(error)
else:raise AssertionError('PROPOSAL_MUST_NOT_AUTHORIZE_EXECUTION')
approved_path=OUT/'execution_authorization.APPROVED.json'
assert not approved_path.exists()
put('EXECUTION_AUTHORIZATION_PROPOSAL.json',proposal)
command=f'''# PREPARED ONLY — NOT EXECUTED. Requires a separately human-authorized file.
Set-Location -LiteralPath '{ROOT}'
if (-not (Test-Path -LiteralPath '{approved_path}')) {{ throw 'Separate approved execution authorization is missing.' }}
$env:PASS_T_LOCAL_RUNTIME_APPROVAL = '1'
$env:PASS_T_PHASE2B_REAL_RUN_PERMISSION = '1'
& '{ROOT / '.venv/Scripts/python.exe'}' -B '{ROOT / 'scripts/run_pass_t_v1d_pilot.py'}' run --frozen '{folder / 'frozen_bundle.json'}' --execution-authorization '{approved_path}'
'''
put('PREPARED_EXECUTION_COMMAND.ps1.txt',command)
result={'status':'FREEZE_VERIFIED_READY_FOR_EXECUTION_AUTHORIZATION','verified_utc_reference':'2026-10-15 07:54:51 UTC',
 'frozen_directory':str(folder),'draft_canonical_sha256':expected,'protocol_canonical_sha256':proto_sha,
 'bundle_file_sha256':file_sha256(folder/'frozen_bundle.json'),'completion_receipt_sha256':file_sha256(folder/'completion_receipt.json'),
 'approval_file_sha256':file_sha256(approval_file),'approved_decisions':decisions,'component_hashes_verified':draft['components_sha256'],
 'calls':calls,'execution_root_inventory':execution_roots,'no_execution_authorization_found_in_authoritative_roots':True,
 'execution_records_for_this_pilot_found':False,'guard_rejections':rejected,'guard_source_evidence':guard_evidence,
 'actual_model_calls_this_task':0,'model_modules_loaded':[],'protocol_freeze_called_this_task':False,
 'approved_execution_file_created':False,'media_integrity':'PENDING_AUTHORIZED_EXECUTION',
 'scope_limitations':'No machine-wide access/process audit; absence of records covers the supported Phase2b execution roots, not arbitrary external/manual executions. Existing CPU mock records are not real approvals or inference.'}
put('POST_FREEZE_VERIFICATION.json',result)
report=f'''# Phase 2b — Post-freeze Verification and Execution Preparation

Task：PASS_T_PHASE2B_V1D_POST_FREEZE_VERIFICATION；2026-10-15。

**FREEZE_VERIFIED_READY_FOR_EXECUTION_AUTHORIZATION**

## Freeze verified from files, not assumed from chat

- Source draft canonical SHA-256：`{expected}`，與當前draft完全相同。
- **Frozen protocol canonical SHA-256：`{proto_sha}`**。
- Frozen bundle file SHA-256：`{file_sha256(folder/'frozen_bundle.json')}`。
- Completion receipt file SHA-256：`{file_sha256(folder/'completion_receipt.json')}`。
- [Authoritative frozen bundle]({(folder/'frozen_bundle.json').as_posix()})。
- [Authoritative completion receipt]({(folder/'completion_receipt.json').as_posix()})。
- [Human freeze approval]({approval_file.as_posix()})。

核實content-addressed目錄ID、completion receipt檔案清單與SHA、bundle內protocol/draft/approval digests、當前所有component hashes和verify_frozen。21/21 decisions均APPROVED且digest相符，human reviewer=reviewer_0；reviewer是覆蓋整份21項清單的approval record來源，而非虛構逐項不同reviewer。原draft保留PENDING歷史快照，實際人類批准在protocol.human_approval.decisions，兩者不混淆。

## Pinned configuration

恰好六窗×三表示=18call，call IDs依序1–18，18個(window,representation)組合無重複。六窗為test1 W03/W05去重、test2 W01、test5 W01、test5 W05、test7 W05、test8 W07；test3 W07排除。V1D/V2/Prediction V1/strict validator/NF4 runtime/Bridge/三格式/Uniform8/ReferenceNONE/C3/FRAME_MATCHED_ONLY/closed-interval matcher與cohort均由原freeze manifest及當前component hashes核實，沒有變更。

## Execution has not been authorized

freeze approval明確execution_authorized=false。支持的V1D pilot與legacy Phase2b run roots均不存在任何run/authorization-use紀錄；本task也沒有啟動模型或建立execution authorization。檢查不把repair資料夾中的MOCK_METADATA_ONLY當作真實執行。

「未執行」的可查證範圍是此pilot支持的repository路徑、回條與目前操作；不是保證外部/手動/任意其他路徑從未執行模型的全機證明。真實媒體完整性、currentGPU與real inference仍PENDING_AUTHORIZED_EXECUTION。

## Guards verified

缺frozen manifest與缺獨立execution authorization皆被既有authorize_execution拒絕；本次proposal也被拒絕（confirmation=null）。靜態source核對新版execute_authorized及worker在spawn/資源檢查/model factory前做授權檢查，load_envelope在任何source PNG read之前檢查frozen/auth。runtime另保留外部兩個環境permission flags，不能以flags取代授權。此敘述限受支持entry path，不宣稱任意私下呼叫底層loader皆不可繞過。

## Exact next human action

本次**只準備、尚未授權**的確認句：

`{confirmation}`

如要執行，請另明確授權上述18call、提供execution reviewer ID，並接受或更新下列提議：

- nonce（32位lowercase hex）：`{nonce}`。
- expires_at_utc：`{expiry}`（台北2026-10-16 15:54:51）。過期必須重新明確確認有效期限，不能自行延長。
- call_ids：`[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18]`；max_calls=18。
- schema_version：`{VERSION}_EXECUTION_AUTHORIZATION`。

[完整未核准proposal]({(OUT/'EXECUTION_AUTHORIZATION_PROPOSAL.json').as_posix()}) 內confirmation/reviewer皆null，approval_received=false，無法執行。freeze reviewer_0不自動當成新的execution reviewer。人類授權後才能另建 `execution_authorization.APPROVED.json`；此task沒有建立它。

## Prepared command — NOT EXECUTED

```powershell
{command}```

[命令文字檔]({(OUT/'PREPARED_EXECUTION_COMMAND.ps1.txt').as_posix()}) 只供閱讀/後續確認。沒有執行命令或設定任何permission環境變數。輸出/授權nonce使用紀錄仍由既有runner按授權hash產生並防重播。

## Preservation and stop

未修改任何prompt/schema/validator/Bridge/matcher/runtime/GT/frozen artifact；所有本次protected component與freeze檔案前後SHA相同。只新增此驗證/準備目錄及更新WORKSPACE導航報告。沒有GPU/CUDA、model load、新model calls、真實媒體讀取、Memory Graph、commit/push，也沒有再呼叫freeze。詳細hash、21項approved digests、guard source行號見[驗證JSON]({(OUT/'POST_FREEZE_VERIFICATION.json').as_posix()})。

STOP BEFORE REAL EXECUTION。Phase2b尚未完成。
'''
assert all(file_sha256(p)==h for p,h in protected.items())
assert not any(m in sys.modules for m in ['torch','transformers','PIL','cv2'])
put('POST_FREEZE_VERIFICATION_REPORT.md',report)
(ROOT/'WORKSPACE/Pass_T/LATEST_REPORT.md').write_text(report,encoding='utf8')
(ROOT/'WORKSPACE/Pass_T/LATEST_DECISIONS.md').write_text(f'''# Pass T — 待獨立執行授權

2026-10-15：freeze已由檔案/receipt/hash重新驗證，21項核准者reviewer_0。**目前未有execution authorization，不執行。**

Frozen protocol SHA：`{proto_sha}`。

下一個人類確認句：`{confirmation}`，另需execution reviewer、nonce、expiry及18call inventory。本次nonce/expiry只是待核准提案，沒有自批。

[最新報告]({(ROOT/'WORKSPACE/Pass_T/LATEST_REPORT.md').as_posix()})；[未核准proposal]({(OUT/'EXECUTION_AUTHORIZATION_PROPOSAL.json').as_posix()})。
''',encoding='utf8')
nav=ROOT/'WORKSPACE/Pass_T/README.md';s=nav.read_text(encoding='utf8');start=s.index('目前主要工作');end=s.index('\n\n',start)
s=s[:start]+'目前主要工作仍在 Pass I/T 平行標註＋實作。V1D protocol已重新核實freeze/21項approval與component hashes：**FREEZE_VERIFIED_READY_FOR_EXECUTION_AUTHORIZATION**。目前沒有獨立execution authorization或支持的pilot run紀錄；只準備下一步授權格式與命令，未開真實媒體、未載入模型、未跑18call、未寫Graph。'+s[end:]
nav.write_text(s,encoding='utf8')
put('DELIVERABLE_HASHES.json',{p.name:file_sha256(p) for p in OUT.iterdir() if p.is_file()})
print(json.dumps({'status':result['status'],'protocol_sha256':proto_sha,'bundle_file_sha256':result['bundle_file_sha256'],
    'approved_decisions':21,'component_count':len(draft['components_sha256']),'execution_roots':execution_roots,
    'confirmation_required':confirmation,'proposed_nonce':nonce,'proposed_expiry_utc':expiry,
    'authorization_granted':False,'model_calls':0,'report':str(OUT/'POST_FREEZE_VERIFICATION_REPORT.md')},ensure_ascii=False))
