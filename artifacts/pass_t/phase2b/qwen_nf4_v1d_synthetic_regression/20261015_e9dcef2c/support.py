"""V1D synthetic-only access guard and exclusive engineering receipts."""
import os,sys
sys.dont_write_bytecode=True
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
from pathlib import Path
import json,hashlib,socket,subprocess,time
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
assert ROOT.name=='mixure_test_SAM'
PRIOR=ROOT/'artifacts/pass_t/phase2b/qwen_nf4_engineering_closeout/20261015_94dcf4d4'
REF=ROOT/'artifacts/pass_t/phase2b/prompt_clarification_matched8_preflight/qwen_nf4/20261015_rev2_4f1c8d251b1e'
MODEL=ROOT/'.models/Qwen2.5-VL-7B-Instruct'
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor'),str(ROOT/'outputs/current_development/video_event_experiment/.deps')]
DENIED=[];PIXEL_READS=set();CPU_MODE=False
def canonical(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(name,v):
    p=(OUT/name).resolve()
    if not p.is_relative_to(OUT):raise RuntimeError('OUTPUT_SCOPE_VIOLATION')
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(v.encode('utf8') if isinstance(v,str) else canonical(v))
    return sha(p)
def deny(reason):
    DENIED.append(reason);raise RuntimeError('V1D_GUARD:'+reason)
def guard(event,args):
    if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
        p=Path(os.fsdecode(args[0])).resolve()
        if p.suffix.lower() in {'.png','.jpg','.jpeg','.mp4','.avi','.mov','.webp','.bmp','.tif','.tiff','.npy','.npz'}:
            if not p.is_relative_to(OUT/'media'):deny('REAL_OR_OLD_VISUAL_MEDIA_FORBIDDEN:'+str(p))
            PIXEL_READS.add(str(p))
        if p.suffix.lower() in {'.safetensors','.pt','.pth','.bin'}:
            if CPU_MODE or not p.is_relative_to(MODEL):deny('MODEL_BINARY_FORBIDDEN_IN_THIS_SCOPE:'+str(p))
sys.addaudithook(guard)
socket.create_connection=lambda *a,**k:deny('NETWORK_CONNECT')
socket.socket.connect=lambda *a,**k:deny('NETWORK_CONNECT')
socket.socket.bind=lambda *a,**k:deny('SERVER_STARTUP')
def git():
    def g(*a):return subprocess.check_output(['git',*a],cwd=ROOT,stderr=subprocess.PIPE)
    return {'head':g('rev-parse','HEAD').decode().strip(),'index_sha256':sha(ROOT/'.git/index'),
      'tracked_diff_sha256':hashlib.sha256(g('diff','--binary')).hexdigest(),
      'staged_diff_sha256':hashlib.sha256(g('diff','--cached','--binary')).hexdigest(),
      'tracked_status_sha256':hashlib.sha256(g('status','--porcelain','--untracked-files=no')).hexdigest(),
      'full_status_sha256':hashlib.sha256(g('status','--porcelain','--untracked-files=all')).hexdigest()}
def hardware():
    import psutil
    csv=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.used,memory.free,utilization.gpu','--format=csv,noheader'],encoding='utf8').strip()
    mi=psutil.Process().memory_info()
    return {'gpu_csv':csv,'ram_available_bytes':psutil.virtual_memory().available,'pid':os.getpid(),'rss_bytes':mi.rss,'peak_wset_bytes':getattr(mi,'peak_wset',None)}
def cpu_guards():
    global CPU_MODE
    CPU_MODE=True;os.environ['CUDA_VISIBLE_DEVICES']='-1'
    import torch
    torch.set_num_threads(4)
    if torch.cuda.is_initialized():deny('CPU_CUDA_ALREADY_INITIALIZED')
    torch.cuda.init=lambda *a,**k:deny('CPU_CUDA_INIT')
    torch.cuda._lazy_init=lambda *a,**k:deny('CPU_CUDA_INIT')
    torch.load=lambda *a,**k:deny('CPU_WEIGHT_LOAD')
    torch.jit.load=lambda *a,**k:deny('CPU_WEIGHT_LOAD')
    from transformers import PreTrainedModel
    from transformers.generation.utils import GenerationMixin
    PreTrainedModel.from_pretrained=classmethod(lambda *a,**k:deny('CPU_MODEL_FROM_PRETRAINED'))
    GenerationMixin.generate=lambda *a,**k:deny('CPU_GENERATION')
    return torch
