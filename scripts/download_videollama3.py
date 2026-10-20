"""User-authorized pinned official weights and code download; no model inference."""
from pathlib import Path
import os,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
os.environ['HF_HUB_DISABLE_XET']='1'
os.environ['HF_HUB_OFFLINE']='0'
os.environ['HF_HOME']=str(ROOT/'.runtime/videollama3/huggingface')
from huggingface_hub import HfApi,snapshot_download
MODEL='DAMO-NLP-SG/VideoLLaMA3-7B'
out=ROOT/'.models/VideoLLaMA3-7B';out.mkdir(parents=True,exist_ok=True)
receipt=out/'download_provenance.json'
if receipt.exists():
    data=json.loads(receipt.read_text(encoding='utf8'));revision=data['revision']
else:
    info=HfApi().model_info(MODEL,files_metadata=True);revision=info.sha
    data={'repository':MODEL,'revision':revision,'license':getattr(info.card_data,'license',None),'files':[{'name':s.rfilename,'bytes':s.size} for s in info.siblings]}
    receipt.write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps({'repository':MODEL,'revision':revision,'destination':str(out)}),flush=True)
snapshot_download(MODEL,revision=revision,local_dir=out,max_workers=3,allow_patterns=['*.json','*.py','*.safetensors','*.txt','*.model','*.md','LICENSE*'])
print('DOWNLOAD_COMPLETE',flush=True)
