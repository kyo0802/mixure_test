"""CPU preparation guards and exclusive namespace operations."""
import os,sys
sys.dont_write_bytecode=True
for key,value in {'CUDA_VISIBLE_DEVICES':'-1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}.items():os.environ[key]=value
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[5]
assert ROOT.name=='mixure_test_SAM'
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor'),str(ROOT/'outputs/current_development/video_event_experiment/.deps')]
import json,hashlib,subprocess,socket
from datetime import datetime,timezone

GUARD_EVENTS=[]
def denied(*args,**kwargs):
    GUARD_EVENTS.append('forbidden_call_blocked');raise RuntimeError('CPU_PREFLIGHT_MODEL_NETWORK_OR_CUDA_FORBIDDEN')
socket.create_connection=denied
socket.socket.connect=denied

def open_guard(event,args):
    if event=='open' and args and isinstance(args[0],(str,bytes,Path)):
        name=os.fsdecode(args[0]).lower()
        if name.endswith(('.safetensors','.pt','.pth','.bin')):
            raise PermissionError('CPU_PREFLIGHT_WEIGHT_BINARY_OPEN_FORBIDDEN')
sys.addaudithook(open_guard)

def processor_guards():
    import torch
    torch.set_num_threads(4)
    assert not torch.cuda.is_initialized()
    torch.cuda.init=denied;torch.cuda._lazy_init=denied
    torch.load=denied;torch.jit.load=denied
    from transformers import PreTrainedModel
    from transformers.generation.utils import GenerationMixin
    setattr(PreTrainedModel,'from_pretrained',classmethod(denied))
    setattr(GenerationMixin,'generate',denied)
    return torch

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def byte_sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def save(name,value):
    p=OUT/name
    assert p.resolve().is_relative_to(OUT)
    data=value.encode() if isinstance(value,str) else canon(value)
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(data)
    return sha(p)
def receipt(step,inputs,outputs,status='COMPLETE',**extra):
    return save(f'STEP_RECEIPT_{step}.json',{'step':str(step),'status':status,'timestamp':datetime.now(timezone.utc).isoformat(),
        'inputs':{rel(p):sha(p) for p in inputs},'outputs':{str(p.relative_to(OUT)):sha(p) for p in outputs},
        'environment':{k:os.environ[k] for k in ['CUDA_VISIBLE_DEVICES','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE']},
        'new_model_calls':0,**extra})
def authorities():
    before=read(OUT/'PREFLIGHT_BEFORE.json')
    required={'src/memory_graph/pass_t/phase2b/predictions.py':'c4b077374d50fc478c29d0009180d488c60a463fa8bffa183a179c5f736f1d37',
      'src/memory_graph/pass_t/phase2b/contracts/prediction_v1.json':'f8b0dfb6c62301baabff5e1adfddf14dc6be9381aa84c884fc70f5318abcedc3',
      'artifacts/pass_t/phase2a/v2/external_returns/datasets/ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c/external_dev_gt.json':'ad1af02ab2d086b5070e8611cc4f7053abc030f83680fa27f50c5ab5da6b3a6c',
      'artifacts/pass_t/phase2a/v2/exhaustive_reviews/adjudicated_7e28b9edf80a8e4da88caa66/adjudicated_dev_view.json':'fa0133e4e49e54bdbac2ba59420d29b504e8bf219fa8179b57cd1b35261a005c',
      'artifacts/pass_t/phase2a/v2/contracts/EVENT_GT_ANNOTATION_POLICY_V2.md':'c90f527eb01e3b320138961570c5647670536d3611feae3c4b7a1d10e33fdac4'}
    for n,h in required.items():
        if sha(ROOT/n)!=h or before['files'][n]!=h:raise RuntimeError('INTEGRITY_BLOCKED:'+n)
    return required
def load_processor():
    torch=processor_guards()
    from transformers import AutoProcessor
    p=AutoProcessor.from_pretrained(ROOT/'.models/Qwen2.5-VL-7B-Instruct',local_files_only=True,trust_remote_code=False,max_pixels=200704)
    for obj in [p.image_processor,p.video_processor]:
        obj.size={'shortest_edge':3136,'longest_edge':200704};obj.min_pixels=3136;obj.max_pixels=200704
    assert not torch.cuda.is_initialized()
    return p,torch

def git():
    def g(*args):return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.PIPE)
    return {'head':g('rev-parse','HEAD').decode().strip(),'index_sha256':sha(ROOT/'.git/index'),
      'tracked_diff_sha256':byte_sha(g('diff','--binary')),'staged_diff_sha256':byte_sha(g('diff','--cached','--binary')),
      'tracked_status_sha256':byte_sha(g('status','--porcelain','--untracked-files=no'))}
