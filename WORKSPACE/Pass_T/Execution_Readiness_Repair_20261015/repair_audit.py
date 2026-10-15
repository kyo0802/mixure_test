"""Text/source-only snapshots, source diffs and preservation receipts."""
import sys
sys.dont_write_bytecode=True
import os,json,hashlib,subprocess,difflib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
os.environ['GIT_OPTIONAL_LOCKS']='0'
BASE='src/memory_graph/pass_t/phase2b/'
EDIT=[BASE+'local_vlm/video_array_bridge.py',BASE+'evaluation.py']
NEW=[BASE+'v1d_protocol.py',BASE+'v1d_outputs.py',BASE+'v1d_execution.py','scripts/run_pass_t_v1d_pilot.py','tests/test_pass_t_v1d_readiness.py']
PROTECTED=[BASE+'predictions.py',BASE+'contracts/prediction_v1.json',BASE+'local_vlm/nf4.py',BASE+'local_vlm/qwen_contract.py',BASE+'local_vlm/runtime.py',BASE+'local_vlm/transport.py',BASE+'protocol.py',BASE+'config.py',BASE+'inference.py']
V1D=ROOT/'artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c'
REVIEW=ROOT/'WORKSPACE/Pass_T/Final_Pilot_Protocol_Review_20261015'
DIAG=ROOT/'WORKSPACE/Pass_T/V1D_Contract_Diagnosis_20261015'
REF=ROOT/'artifacts/pass_t/phase2b/prompt_clarification_matched8_preflight/qwen_nf4/20261015_rev2_4f1c8d251b1e'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(n,v):(OUT/n).write_text(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def git(*args):return subprocess.run(['git',*args],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
def state():
    s=git('status','--porcelain=v1','--untracked-files=all');return {'head':git('rev-parse','HEAD').decode().strip(),'index_sha256':sha(ROOT/git('rev-parse','--git-path','index').decode().strip()),'staged_diff_sha256':hashlib.sha256(git('diff','--cached','--binary','--no-ext-diff')).hexdigest(),'worktree_diff_sha256':hashlib.sha256(git('diff','--binary','--no-ext-diff')).hexdigest(),'status_sha256':hashlib.sha256(s).hexdigest()}
if sys.argv[1]=='before':
    assert not (OUT/'BEFORE.json').exists()
    for rel in EDIT:
        dest=OUT/'before_source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/rel).read_bytes())
    protected={ROOT/x for x in PROTECTED}
    for directory in [REVIEW,DIAG,V1D]:
        protected.update(p for p in directory.rglob('*') if p.is_file() and p.suffix.lower() in {'.md','.json','.jsonl','.txt','.py','.patch','.csv'})
    protected.update([REF/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt',REF/'prompt_candidate/v2_system_unchanged.txt'])
    for x in NEW:assert not (ROOT/x).exists(),x
    put('BEFORE.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'edited_before_sha256':{x:sha(ROOT/x) for x in EDIT},'protected_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(protected)},'new_paths_expected':NEW,'git':state()})
    print(json.dumps({'baseline_recorded':True,'protected':len(protected),'edit_files':EDIT,'new_files':NEW}))
elif sys.argv[1]=='after':
    b=json.loads((OUT/'BEFORE.json').read_text(encoding='utf8'))
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor'),str(ROOT/'outputs/current_development/video_event_experiment/.deps')]
    from memory_graph.pass_t.phase2b.v1d_protocol import dry_run
    prepared=dry_run(ROOT)
    put('DRAFT_CONFIGURATION_CANDIDATE.json',prepared['draft'])
    put('CPU_DRY_RUN_RECEIPT.json',{k:v for k,v in prepared.items() if k!='draft'})
    changed=[];patch=[]
    for rel in EDIT+NEW:
        p=ROOT/rel;old=(OUT/'before_source'/rel).read_text(encoding='utf8') if rel in EDIT else ''
        new=p.read_text(encoding='utf8');patch.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+rel if rel in EDIT else '/dev/null',tofile='b/'+rel))
        changed.append({'path':rel,'before_sha256':b['edited_before_sha256'].get(rel),'after_sha256':sha(p),'kind':'modified' if rel in EDIT else 'added'})
    bad=[p for p,h in b['protected_sha256'].items() if sha(ROOT/p)!=h]
    put('EXACT_SOURCE_DIFF.patch',''.join(patch));put('SOURCE_CHANGE_MANIFEST.json',{'files':changed,'patch_sha256':sha(OUT/'EXACT_SOURCE_DIFF.patch'),'protected_files_checked':len(b['protected_sha256']),'protected_changes':bad,'git_before':b['git'],'git_after':state(),'no_commit_push':True})
    assert not bad,bad
    print(json.dumps({'protected_changes':bad,'source_changes':len(changed),'patch_sha256':sha(OUT/'EXACT_SOURCE_DIFF.patch')}))
