from pathlib import Path
import json, hashlib
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/current_development'
MODEL_ID='Qwen/Qwen2.5-VL-7B-Instruct'
REVISION='cc594898137f460bfe9f0759e9844b3ce807cfb5'
MODEL_PATH=ROOT/'.models/Qwen2.5-VL-7B-Instruct'
def read(p,default=None):
    p=Path(p)
    return json.loads(p.read_text(encoding='utf8')) if p.is_file() else default
def sha256(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def canonical_hash(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def write(p,x):
    p=Path(p);p.resolve().relative_to(OUT.resolve())
    if (OUT/'final/artifact_manifest.json').exists() and p.parts[-2] not in {'evaluation','regression','final'} and p.suffix!='.md':raise RuntimeError('Frozen predictions')
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding='utf8')
