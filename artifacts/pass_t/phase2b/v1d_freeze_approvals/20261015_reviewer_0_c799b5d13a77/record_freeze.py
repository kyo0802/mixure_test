"""Record the human's hash-bound freeze-only approval. Never import execution."""
import sys
sys.dont_write_bytecode=True
import os,json,hashlib,datetime,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
os.environ['GIT_OPTIONAL_LOCKS']='0'
ALLOWED=[OUT,ROOT/'artifacts/pass_t/phase2b/v1d_protocols']
NAV=[ROOT/'WORKSPACE/Pass_T/LATEST_REPORT.md',ROOT/'WORKSPACE/Pass_T/LATEST_DECISIONS.md',ROOT/'WORKSPACE/Pass_T/README.md']
def guard(event,args):
    if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','PIL','cv2','tensorflow','huggingface_hub'}:
        raise RuntimeError('MODEL_PIXEL_IMPORT_PROHIBITED')
    if event.startswith('socket.'):raise RuntimeError('NETWORK_PROHIBITED')
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        p=Path(os.fsdecode(args[0])).resolve();mode,flags=args[1:3]
        writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
        if writing and not (any(p.is_relative_to(q) for q in ALLOWED) or p in NAV):raise RuntimeError('WRITE_OUTSIDE_FREEZE_SCOPE:'+str(p))
        low=str(p).lower().replace('\\','/')
        if not writing and (p.suffix.lower() in {'.png','.jpg','.jpeg','.mp4','.avi','.mov','.pt','.bin','.safetensors','.npy','.npz'} or '/.models/' in low or low.endswith('/external_dev_gt.json')):
            raise RuntimeError('MEDIA_MODEL_GT_READ_PROHIBITED')
sys.addaudithook(guard)
from memory_graph.pass_t.phase2b.common import canonical_bytes,digest,file_sha256,read_json,pretty_bytes,Phase2BBlocked
from memory_graph.pass_t.phase2b.v1d_protocol import validate_draft,decision_digest,freeze_protocol,verify_frozen,authorize_execution
DRAFT_PATH=ROOT/'WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/DRAFT_CONFIGURATION_CANDIDATE.json'
draft=read_json(DRAFT_PATH)
expected='c799b5d13a7721a02e88d25f9474081b6d5975bb2b6f71a72f61bf1ba7a00f02'
assert digest(canonical_bytes(draft))==expected
validate_draft(draft,ROOT)
components_before={p:file_sha256(ROOT/p) for p in draft['components_sha256']}
historical=ROOT/'WORKSPACE/Pass_T/Execution_Readiness_Repair_20261015/DELIVERABLE_MANIFEST.json'
historical_before=file_sha256(historical)
approval={'confirmation':'APPROVE_PHASE2B_V1D_FREEZE '+expected+' NO_EXECUTION',
    'reviewer_id':'reviewer_0','execution_authorized':False,
    'decisions':[{'id':d['id'],'decision_sha256':decision_digest(d),'status':'APPROVED'} for d in draft['human_decisions']],
    'approval_source':'Explicit human chat confirmation bound to the full draft SHA, followed by explicit reviewer ID reply.',
    'scope':'FREEZE_ONLY_NO_EXECUTION','recorded_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
approval_path=OUT/'human_freeze_approval.json'
if approval_path.exists():
    old=read_json(approval_path)
    assert {k:v for k,v in old.items() if k!='recorded_at_utc'}=={k:v for k,v in approval.items() if k!='recorded_at_utc'}
    approval=old
else:
    with approval_path.open('xb') as f:f.write(pretty_bytes(approval))
destination=freeze_protocol(draft,approval,ROOT)
bundle=read_json(destination/'frozen_bundle.json');verify_frozen(bundle,ROOT)
receipt=read_json(destination/'completion_receipt.json')
assert receipt['files_sha256']['frozen_bundle.json']==file_sha256(destination/'frozen_bundle.json')
try:authorize_execution(bundle,None,root=ROOT)
except Phase2BBlocked as error:
    assert str(error)=='SEPARATE_EXECUTION_AUTHORIZATION_REQUIRED'
else:raise AssertionError('MISSING_EXECUTION_AUTHORIZATION_NOT_BLOCKED')
assert all(file_sha256(ROOT/p)==h for p,h in components_before.items())
assert file_sha256(historical)==historical_before
assert not any(m in sys.modules for m in ['torch','transformers','PIL','cv2'])
protocol_sha=bundle['freeze_receipt']['protocol_sha256']
report=f'''# Pass T Phase 2b — V1D Protocol Frozen

日期：2026-10-15（Asia/Taipei）。狀態：**PROTOCOL_FROZEN_NO_EXECUTION_AUTHORIZED**。

Reviewer：`reviewer_0`。人類已明確批准完整draft SHA，並另提供本次reviewer ID；記錄21項decision digests為APPROVED，批准範圍僅freeze，不包含推論。

## Authority

- Draft canonical SHA-256：`{expected}`。
- Frozen protocol SHA-256：`{protocol_sha}`。
- [Frozen bundle]({(destination/'frozen_bundle.json').as_posix()})，file SHA：`{file_sha256(destination/'frozen_bundle.json')}`。
- [Immutable completion receipt]({(destination/'completion_receipt.json').as_posix()})，file SHA：`{file_sha256(destination/'completion_receipt.json')}`。
- [Human freeze-only approval]({approval_path.as_posix()})，file SHA：`{file_sha256(approval_path)}`。
- [本次freeze報告原檔]({(OUT/'FREEZE_REPORT.md').as_posix()})。

## Frozen scope

六窗：test1 W03/W05去重、test2 W01、test5 W01、test5 W05、test7 W05、test8 W07；test3 W07排除。三表示MI8/SB8/NativeArray8，planned18calls；Uniform8/ReferenceNONE/V1D/V2/C3/FRAME_MATCHED_ONLY、greedy42/1024與CLOSED_INTERVAL_GAP_V1。完整配置以bundle為準。

原draft內21項PENDING文字是凍結時保留的提案快照；此次人類批准另存於protocol.human_approval.decisions，21項均APPROVED，不回寫或覆蓋歷史draft/review/repair報告。

## Verification and remaining boundary

- 核對目前draft與已批准SHA完全相同；透過既有freeze writer產生bundle/receipt，再以verify_frozen重驗。
- 核對當前所有draft component hashes及原repair deliverable manifest未變；未改runtime、matcher、prompt、schema、GT或歷史報告。
- 驗證沒有execution authorization時確實拒絕執行。沒有建立execution authorization、沒有呼叫execution runner。
- 此次只做文字/JSON/hash/freeze寫入；未載入模型、未初始化CUDA、未讀真實媒體或原GT、未生成VLM預測、未寫Memory Graph、未commit/push。
- 真實媒體完整性與GPU實際行為仍為PENDING_AUTHORIZED_EXECUTION。歷史V1D strict1/8與六個event-bearing全部invalid結果不變。

下一步只有在另收到綁定此frozen protocol SHA的execution authorization（含reviewer、nonce、到期UTC與18call inventory）並滿足原runtime環境gate後，才可考慮實際pilot。此次**沒有執行授權**，Phase2b尚未完成。
'''
report_path=OUT/'FREEZE_REPORT.md'
if report_path.exists():assert report_path.read_text(encoding='utf8')==report
else:
    with report_path.open('x',encoding='utf8') as f:f.write(report)
(ROOT/'WORKSPACE/Pass_T/LATEST_REPORT.md').write_text(report,encoding='utf8')
(ROOT/'WORKSPACE/Pass_T/LATEST_DECISIONS.md').write_text(f'''# 最新 Pass T 決策狀態

2026-10-15：reviewer_0已核准並完成V1D protocol freeze；21項decision digests均APPROVED。

Frozen protocol SHA：`{protocol_sha}`。

**目前沒有execution authorization，不得執行18call。** 媒體完整性仍PENDING_AUTHORIZED_EXECUTION；歷史V1D失敗結果不變。

[最新報告]({(ROOT/'WORKSPACE/Pass_T/LATEST_REPORT.md').as_posix()})；[完整frozen bundle]({(destination/'frozen_bundle.json').as_posix()})。
''',encoding='utf8')
nav=ROOT/'WORKSPACE/Pass_T/README.md';text=nav.read_text(encoding='utf8')
start=text.index('目前主要工作');end=text.index('\n\n',start)
text=text[:start]+'目前主要工作仍在 Pass I/T 平行標註＋實作。V1D protocol已由 reviewer_0 明確核准並凍結：**PROTOCOL_FROZEN_NO_EXECUTION_AUTHORIZED**。21項decision digests已批准；目前沒有執行授權、未載入模型、未跑真實18call、未寫Graph。媒體完整性仍為 PENDING_AUTHORIZED_EXECUTION。工程修補53/53 CPU tests通過；歷史V1D仍strict **1/8**、6個event-bearing全invalid，REGRESSION_FAIL未改寫。'+text[end:]
nav.write_text(text,encoding='utf8')
verification={'status':'PROTOCOL_FROZEN_NO_EXECUTION_AUTHORIZED','reviewer_id':'reviewer_0','draft_sha256':expected,
    'protocol_sha256':protocol_sha,'frozen_path':str(destination),'approval_file_sha256':file_sha256(approval_path),
    'bundle_file_sha256':file_sha256(destination/'frozen_bundle.json'),'completion_receipt_sha256':file_sha256(destination/'completion_receipt.json'),
    'all_component_hashes_unchanged':True,'historical_repair_manifest_unchanged':True,'approved_decisions':21,
    'execution_without_authorization_rejected':True,'execution_authorization_created':False,'model_modules_loaded':[],
    'actual_model_calls':0,'report_sha256':file_sha256(report_path)}
verify_path=OUT/'FREEZE_VERIFICATION.json'
if verify_path.exists():assert read_json(verify_path)==verification
else:
    with verify_path.open('xb') as f:f.write(pretty_bytes(verification))
print(json.dumps(verification,ensure_ascii=False))
