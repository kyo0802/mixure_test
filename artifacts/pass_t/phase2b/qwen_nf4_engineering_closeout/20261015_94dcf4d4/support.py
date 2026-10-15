"""Synthetic-only scoped file access, exclusive receipts and pinned authority."""
import os, sys
sys.dont_write_bytecode=True
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import json,hashlib,socket,subprocess,time,traceback
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
assert ROOT.name=='mixure_test_SAM'
REF=ROOT/'artifacts/pass_t/phase2b/prompt_clarification_matched8_preflight/qwen_nf4/20261015_rev2_4f1c8d251b1e'
MODEL=ROOT/'.models/Qwen2.5-VL-7B-Instruct'
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor'),str(ROOT/'outputs/current_development/video_event_experiment/.deps')]
DENIED=[]
PIXEL_READS=set()
WEIGHT_LOAD_ALLOWED=False
ALLOWED_REFERENCE_FIXTURE_IDS=set()
CPU_DIAGNOSTIC=False

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(name,value):
    p=(OUT/name).resolve()
    if not p.is_relative_to(OUT):raise RuntimeError('OUTPUT_OUTSIDE_AUTHORIZED_NAMESPACE')
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(value.encode('utf8') if isinstance(value,str) else canon(value))
    return sha(p)
def deny(event,*a,**kw):
    DENIED.append(event);raise RuntimeError('SYNTHETIC_ONLY_FORBIDDEN:'+event)
socket.create_connection=lambda *a,**k:deny('network_connect')
socket.socket.connect=lambda *a,**k:deny('network_connect')
socket.socket.bind=lambda *a,**k:deny('server_bind')

def access_guard(event,args):
    if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
        p=Path(os.fsdecode(args[0])).resolve()
        if p.suffix.lower() in {'.png','.jpg','.jpeg','.mp4','.avi','.mov','.webp'}:
            allowed=p.is_relative_to(REF/'model_visible/fixtures') or p.is_relative_to(OUT/'inputs') or any(
                p.is_relative_to(REF/'model_visible/matched8_native_array'/fid) for fid in ALLOWED_REFERENCE_FIXTURE_IDS)
            if not allowed:deny('REAL_OR_UNAUTHORIZED_VISUAL_MEDIA:'+str(p))
            PIXEL_READS.add(str(p))
        if p.suffix.lower() in {'.safetensors','.pt','.pth','.bin'} and not p.is_relative_to(MODEL):
            deny('UNAUTHORIZED_MODEL_BINARY:'+str(p))
        if CPU_DIAGNOSTIC and p.suffix.lower() in {'.safetensors','.pt','.pth','.bin'}:
            deny('CPU_MODEL_BINARY_OPEN')
sys.addaudithook(access_guard)

def git():
    def cmd(*a):return subprocess.check_output(['git',*a],cwd=ROOT,stderr=subprocess.PIPE)
    return {'head':cmd('rev-parse','HEAD').decode().strip(),'index_sha256':sha(ROOT/'.git/index'),
      'tracked_diff_sha256':hashlib.sha256(cmd('diff','--binary')).hexdigest(),
      'staged_diff_sha256':hashlib.sha256(cmd('diff','--cached','--binary')).hexdigest(),
      'tracked_status_sha256':hashlib.sha256(cmd('status','--porcelain','--untracked-files=no')).hexdigest(),
      'full_status_sha256':hashlib.sha256(cmd('status','--porcelain','--untracked-files=all')).hexdigest()}

def hardware():
    import psutil
    csv=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used,memory.free,utilization.gpu','--format=csv,noheader'],encoding='utf8').strip()
    return {'gpu_csv':csv,'ram_available_bytes':psutil.virtual_memory().available,'pid':os.getpid(),
      'rss_bytes':psutil.Process().memory_info().rss,'os_peak_wset_bytes':getattr(psutil.Process().memory_info(),'peak_wset',None)}

def authorities():
    required={REF/'DELIVERABLE_MANIFEST.json':'26012be8f30b3c53c366c3e05131b58e76e09acc495a00c104826d70c63acafc',
      REF/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json':'149f8696e51fa91cf43147d761315672dc43594aebe41b58cea8ed78956346ee',
      REF/'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json':'7e03eec785712c351fec299f5b249af430a003d30f78387fd7e5f6152c90719b',
      REF/'QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt':'3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722',
      ROOT/'src/memory_graph/pass_t/phase2b/predictions.py':'c4b077374d50fc478c29d0009180d488c60a463fa8bffa183a179c5f736f1d37'}
    for p,h in required.items():
        if sha(p)!=h:raise RuntimeError('AUTHORITY_HASH_MISMATCH:'+str(p))
    lock=read(REF/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json')
    for n,h in lock['model_visible_frames_sha256'].items():
        if sha(REF/n)!=h:raise RuntimeError('SYNTHETIC_FRAME_LOCK_MISMATCH:'+n)
    manifest=read(REF/'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json')
    assert len(manifest['scenarios'])==7
    assert sum(s['intended_stratum']=='WARMUP' for s in manifest['scenarios'])==1
    ALLOWED_REFERENCE_FIXTURE_IDS.update(x['fixture_id'] for x in manifest['scenarios'])
    return manifest

def snapshot():
    authorities()
    files={}
    source=ROOT/'src/memory_graph/pass_t/phase2b'
    for p in source.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:files[p.relative_to(ROOT).as_posix()]=sha(p)
    for n,h in read(REF/'DELIVERABLE_MANIFEST.json')['files_sha256'].items():
        p=REF/n
        if p.suffix.lower() in {'.png','.jpg','.avi','.mp4'}:continue
        if sha(p)!=h:raise RuntimeError('PROTECTED_REFERENCE_CHANGED:'+n)
        files[p.relative_to(ROOT).as_posix()]=h
    for n,h in read(REF/'processor_source_inventory.json').items():
        assert sha(ROOT/n)==h
        files[n]=h
    p=ROOT/'src/memory_graph/pass_t/phase2b/local_vlm/nf4.py'
    save('historical_source/nf4.py',p.read_text(encoding='utf8'))
    # Preserve exact raw bytes separately, including original line endings.
    raw=OUT/'historical_source/nf4_original_bytes.dat'
    with raw.open('xb') as f:f.write(p.read_bytes())
    assets=ROOT/'artifacts/pass_t/phase2b/capacity_probe/qwen_nf4/v2_20261014_owned_tree/model_assets.json'
    save('model_assets.json',read(assets))
    save('BEFORE.json',{'git':git(),'files':files,'hardware':hardware(),'visual_read_allowlist':[str(REF/'model_visible/fixtures'),str(OUT/'inputs')],
      'original_runtime_sha256':sha(p),'original_runtime_bytes_sha256':sha(raw),'old_manifest_verified':True,
      'preservation_scope':'source, processor implementation, old non-image artifacts and locked synthetic imagery; no DEV image checksum reads'})
    print('SNAPSHOT_PASS',len(files),'protected non-DEV files',flush=True)

def cpu_guards():
    global CPU_DIAGNOSTIC
    CPU_DIAGNOSTIC=True
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    import torch
    torch.set_num_threads(4)
    if torch.cuda.is_initialized():raise RuntimeError('CUDA_INITIALIZED_BEFORE_CPU_CHECK')
    torch.cuda.init=lambda *a,**k:deny('CPU_CUDA_INIT')
    torch.cuda._lazy_init=lambda *a,**k:deny('CPU_CUDA_LAZY_INIT')
    torch.load=lambda *a,**k:deny('CPU_WEIGHT_LOAD')
    torch.jit.load=lambda *a,**k:deny('CPU_JIT_WEIGHT_LOAD')
    from transformers import PreTrainedModel
    from transformers.generation.utils import GenerationMixin
    PreTrainedModel.from_pretrained=classmethod(lambda *a,**k:deny('CPU_MODEL_FROM_PRETRAINED'))
    GenerationMixin.generate=lambda *a,**k:deny('CPU_GENERATION')
    return torch
