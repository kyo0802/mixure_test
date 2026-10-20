"""Pin official Nemotron deployment metadata and download its supported NVFP4 assets."""
import os,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/pass_t/phase3/three_vlm_full_v1';OUT.mkdir(parents=True,exist_ok=True)
os.environ['HF_HOME']=str(ROOT/'.runtime/nemotron/huggingface');os.environ['HF_HUB_DISABLE_XET']='1'
from huggingface_hub import HfApi,snapshot_download
model='nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-NVFP4-QAD';target=ROOT/'.models/Nemotron-Nano-12B-v2-VL-NVFP4-QAD'
receipt=OUT/'nemotron_download.json'
if not receipt.exists():
    info=HfApi().model_info(model,files_metadata=True)
    release=json.load(urllib.request.urlopen('https://pypi.org/pypi/vllm/json'))['info']['version']
    metadata={'repository':model,'revision':info.sha,'license':'nvidia-open-model-license','variant':'OFFICIAL_NVFP4_QAD_12B_VL','vllm_version':release,'files':[{'name':f.rfilename,'bytes':f.size} for f in info.siblings],'runtime':'LINUX_WSL2_VLLM_MODELOPT_FP4','video_policy':'8_EXACT_SOURCE_FRAMES_NO_PRUNING','weights_bf16_fallback':False}
    receipt.write_text(json.dumps(metadata,indent=2),encoding='utf8')
metadata=json.loads(receipt.read_text(encoding='utf8'))
print('PINNED',metadata['revision'],'vllm',metadata['vllm_version'],flush=True)
snapshot_download(model,revision=metadata['revision'],local_dir=target,allow_patterns=['*.json','*.py','*.md','*.safetensors','*.txt','*.model'],max_workers=3)
print('NEMOTRON_DOWNLOAD_COMPLETE',flush=True)
