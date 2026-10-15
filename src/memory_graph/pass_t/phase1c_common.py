"""Shared offline utilities; explicit UTF-8 and new-artifact write boundaries."""
import ast
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'artifacts/pass_t'
COUNTERS = {'model_inference_calls':0,'local_model_reruns':0,'graph_write_attempts':0,
            'builder_changes':0,'frozen_schema_changes':0}


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def write(path,value,exclusive=False):
    path=Path(path).resolve()
    if not path.is_relative_to(OUT.resolve()):
        raise ValueError('Writes must stay under artifacts/pass_t')
    protected=read(OUT/'manifests/phase1c_protected_before.json')
    if path.relative_to(ROOT).as_posix() in protected:
        raise ValueError('Refusing to overwrite protected pre-existing artifact')
    path.parent.mkdir(parents=True,exist_ok=True)
    content=value if isinstance(value,str) else json.dumps(value,indent=2,ensure_ascii=False)+'\n'
    with path.open('x' if exclusive else 'w',encoding='utf-8') as f:
        f.write(content)


def safety_scan(paths):
    """Scan new modules/tests for external inference/network imports and loaders."""
    prohibited={'torch','transformers','ultralytics','sam2','sam3','openai','anthropic','requests',
                'httpx','socket','urllib','http','aiohttp','huggingface_hub','timm'}
    loader_calls={'from_pretrained','predict','generate','load_model','run_video','run_video_v2','run_v21'}
    errors=[];scanned=[]
    for path in paths:
        path=Path(path);tree=ast.parse(path.read_text(encoding='utf-8'));scanned.append(str(path.relative_to(ROOT)))
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[x.name for x in node.names] if isinstance(node,ast.Import) else [node.module or '']
                for name in names:
                    if name.split('.')[0] in prohibited:
                        errors.append(f'{path.name}:{node.lineno} prohibited import {name}')
            if isinstance(node,ast.Call):
                call=node.func.attr if isinstance(node.func,ast.Attribute) else node.func.id if isinstance(node.func,ast.Name) else ''
                if call in loader_calls:errors.append(f'{path.name}:{node.lineno} prohibited call {call}')
                if call in {'read_text','write_text'} or (call=='open' and
                    not any(isinstance(k.value,ast.Constant) and isinstance(k.value.value,str) and 'b' in k.value.value
                            for k in node.keywords if k.arg=='mode') and
                    not any(isinstance(a,ast.Constant) and isinstance(a.value,str) and 'b' in a.value for a in node.args)):
                    # Image.open is binary image decoding, not textual file IO.
                    if isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='Image':
                        continue
                    if call=='open' and isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='av':
                        continue
                    if not any(k.arg=='encoding' and isinstance(k.value,ast.Constant) and k.value.value=='utf-8' for k in node.keywords):
                        errors.append(f'{path.name}:{node.lineno} text IO missing explicit UTF-8')
    return {'status':'PASS' if not errors else 'FAIL','files_scanned':scanned,'errors':errors,
            'runtime_counters':dict(COUNTERS),'network_imports_allowed':False}
