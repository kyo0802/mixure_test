"""Snapshot the current safe state before any V295 implementation edits."""
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/v295_reid'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    dest = OUT/'baseline/preserved_state.json'
    if dest.exists():
        raise FileExistsError('V295 baseline is immutable')
    files = {}
    roots = ['src', 'scripts', 'configs', 'tests', 'outputs/identity_rebuild',
             'outputs/validation', 'outputs/v294_qwen38', 'outputs_v293']
    for rel in roots:
        for path in (ROOT/rel).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                files[path.relative_to(ROOT).as_posix()] = sha(path)
    for name in ['README.md', 'CURRENT_PIPELINE.md', 'pyproject.toml', 'uv.lock']:
        files[name] = sha(ROOT/name)
    dest.parent.mkdir(parents=True)
    dest.write_text(json.dumps({'files': files, 'frozen_unix': time.time(),
                               'scope': 'Current source and required protected historical outputs'}, indent=2), encoding='utf8')
    (dest.parent/'source_hashes.json').write_text(json.dumps({k:v for k,v in files.items()
                        if k.startswith(('src/', 'scripts/', 'configs/', 'tests/'))}, indent=2), encoding='utf8')
    identity = ROOT/'outputs/identity_rebuild'
    dev = json.loads((identity/'development/identity_metrics.json').read_text(encoding='utf8'))
    val = json.loads((identity/'known_validation_regression/val_1_to_11_identity_metrics.json').read_text(encoding='utf8'))
    baseline = {'development': dev, 'known_regression': val,
        'permanent_false_merges': json.loads((identity/'known_validation_regression/false_merge_comparison.json').read_text()),
        'val9_bank_contamination': json.loads((identity/'known_validation_regression/bank_contamination_comparison.json').read_text()),
        'test8_result': dev['videos']['test8'], 'calibration': json.loads((identity/'calibration/confirmation_policy.json').read_text()),
        'protected_files': len(files), 'branch': 'codex/V295'}
    (dest.parent/'safe_baseline.json').write_text(json.dumps(baseline, indent=2), encoding='utf8')
    print('Protected files:',len(files),'known-regression totals:',val['totals'],flush=True)

if __name__ == '__main__':
    main()
