from __future__ import annotations
import importlib.metadata as md
import json
from pathlib import Path
import platform
import torch
import transformers

snapshot = Path('/home/smile07159/findmind-v2101/hf-home/hub/models--DAMO-NLP-SG--VideoLLaMA3-7B/snapshots/d5b763e368861e7f5096e7ff1b49f92fbccf8ae6')
config = json.loads((snapshot / 'config.json').read_text())
files = sorted(p.name for p in snapshot.iterdir() if p.is_file())
versions = {}
for name in ('flash-attn','accelerate','bitsandbytes','torchvision','decord','opencv-python','safetensors','huggingface-hub'):
    try: versions[name] = md.version(name)
    except md.PackageNotFoundError: versions[name] = None
result = {
 'python': platform.python_version(), 'torch':torch.__version__, 'torch_cuda':torch.version.cuda,
 'cuda_available':torch.cuda.is_available(), 'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
 'gpu_compute_capability':list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None,
 'transformers':transformers.__version__, 'packages':versions, 'model_snapshot':str(snapshot),
 'files':files, 'architectures':config.get('architectures'),'auto_map':config.get('auto_map'),
 'model_type':config.get('model_type'), 'torch_dtype':config.get('torch_dtype'),
}
for name in ('modeling_videollama3.py','configuration_videollama3.py','processing_videollama3.py'):
    p=snapshot/name
    if p.is_file():
        lines=p.read_text(errors='replace').splitlines()
        result[name+'_first_lines']=lines[:100]
print(json.dumps(result,indent=2,ensure_ascii=False))