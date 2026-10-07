"""Immutable preservation snapshot taken before V296 implementation."""
from pathlib import Path
import hashlib,json,time
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/v296_reid'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    target=OUT/'baseline/preservation_manifest.json'
    if target.exists():raise FileExistsError('Baseline already preserved')
    files={}
    for folder in ['src','scripts','tests','configs','outputs/identity_rebuild','outputs/v295_reid','outputs/v294_qwen38','outputs/validation','outputs_v292']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:files[p.relative_to(ROOT).as_posix()]=sha(p)
    for name in ['README.md','CURRENT_PIPELINE.md','pyproject.toml','uv.lock','.models/yolo11s.pt']:
        p=ROOT/name
        if p.is_file():files[name]=sha(p)
    for p in (ROOT/'.models').rglob('sam2.1*.pt'):files[p.relative_to(ROOT).as_posix()]=sha(p)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'files':files,'created_unix':time.time(),'branch':'codex/V296','scope':'Active sources plus protected safe/V295/V294/validation/raw development outputs'},indent=2),encoding='utf8')
    metrics={'safe':json.loads((ROOT/'outputs/v295_reid/baseline/safe_baseline.json').read_text(encoding='utf8')),
        'v295':json.loads((ROOT/'outputs/v295_reid/known_val_regression/summary.json').read_text(encoding='utf8')),
        'v295_test8':json.loads((ROOT/'outputs/v295_reid/development/test8_recovery.json').read_text(encoding='utf8')),
        'normal_runner_sha256':sha(ROOT/'scripts/run_findmind.py')}
    (target.parent/'baseline_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf8')
    print('Preserved',len(files),'files',flush=True)
if __name__=='__main__':main()
