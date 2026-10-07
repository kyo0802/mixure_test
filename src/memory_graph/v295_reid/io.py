import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'outputs/v295_reid'

def read(path, default=None):
    p = Path(path)
    return json.loads(p.read_text(encoding='utf-8-sig')) if p.is_file() else default

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def save(path, value):
    p = Path(path).resolve()
    if not p.is_relative_to(OUT.resolve()):
        raise ValueError('V295 results must stay under outputs/v295_reid')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf8')

def sources(video_id):
    dev = video_id.startswith('test')
    source = ROOT/(f'outputs_v292/{video_id}' if dev else f'outputs/validation/runs/{video_id}/{video_id}')
    video = ROOT/(f'{video_id}.mp4' if dev else f'val_set/{video_id}.mp4')
    safe = ROOT/f'outputs/identity_rebuild/{"development" if dev else "known_validation_regression"}/runs_final/{video_id}'
    return source, video, safe
