"""Before-policy V297 preservation snapshot. Never rewrites historical artifacts."""
from pathlib import Path
import hashlib,json,time
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/v297_physical_identity'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    target=OUT/'baseline/preservation_manifest.json'
    if target.exists():raise FileExistsError('Preservation already exists')
    files={}
    for folder in ['src','scripts','tests','configs','outputs/identity_rebuild','outputs/v295_reid','outputs/v296_reid','outputs/v294_qwen38','outputs/validation','outputs_v292']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:files[p.relative_to(ROOT).as_posix()]=sha(p)
    for name in ['README.md','CURRENT_PIPELINE.md','pyproject.toml','uv.lock','.models/yolo11s.pt']:
        p=ROOT/name
        if p.is_file():files[name]=sha(p)
    for p in (ROOT/'.models').rglob('sam2.1*.pt'):files[p.relative_to(ROOT).as_posix()]=sha(p)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'files':files,'created_unix':time.time(),'branch':'codex/V297','scope':'Safe source/results and V295/V296 preserved before V297 decision logic'},indent=2),encoding='utf8')
    previous=ROOT/'outputs/v296_reid'
    metrics={'safe':json.loads((previous/'baseline/baseline_metrics.json').read_text(encoding='utf8'))['safe'],
        'v295':json.loads((ROOT/'outputs/v295_reid/known_val_regression/summary.json').read_text(encoding='utf8')),
        'v296':json.loads((previous/'known_val_regression/safety_summary.json').read_text(encoding='utf8')),
        'v296_test8':json.loads((previous/'development/test8_recovery.json').read_text(encoding='utf8')),
        'normal_runner_sha256':sha(ROOT/'scripts/run_findmind.py')}
    (target.parent/'baseline_metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf8')
    print('Preserved',len(files),'files',flush=True)
if __name__=='__main__':main()
