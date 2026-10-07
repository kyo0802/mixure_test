from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/v297_physical_identity'
PREV=ROOT/'outputs/v296_reid'
OLD=ROOT/'outputs/v295_reid'
def read(p,default=None):
    p=Path(p);return json.loads(p.read_text(encoding='utf-8-sig')) if p.is_file() else default
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,value):
    p=Path(p).resolve()
    if not p.is_relative_to(OUT.resolve()):raise ValueError('V297 output namespace only')
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
