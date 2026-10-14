"""Read-only inventory/verification for the 2026-10-14 local organization."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NAMES = {
    'outputs_v1_comparison': 'baseline_comparison',
    'outputs_v2': 'initial_vlm',
    'outputs_v2_events': 'initial_events',
    'outputs_v21': 'candidate_admission',
    'outputs_v22': 'sam_temporal',
    'outputs_v23': 'entity_fusion',
    'outputs_v24': 'appearance_reidentification',
    'outputs_v25_rerun': 'target_binding',
    'outputs_v26': 'safe_identity_fusion',
    'outputs_v27': 'temporal_spatial_memory',
    'outputs_v28': 'target_local_memory',
    'outputs_v29': 'anchor_reasoning',
    'outputs_v291': 'anchor_recovery',
    'outputs_v292': 'canonical_pipeline_sources',
    'outputs_v293': 'pair_event_reasoning',
}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def git_state():
    return subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT).decode('utf-8')

def snapshot():
    rows, blocked, fingerprints = [], [], {}
    candidates = [(name, 'archive/experiments/' + target) for name, target in NAMES.items()]
    candidates += [(p.name, 'archive/test_runs/' + p.name.lstrip('.')) for p in sorted(ROOT.iterdir())
                   if p.is_dir() and (p.name.startswith(('.identity', '.v294', '.v295')) or p.name == '.extqa')]
    for old, new in candidates:
        path = ROOT / old
        errors, files = [], []
        for d, ds, fs in os.walk(path, onerror=lambda e: errors.append(str(e)), followlinks=False):
            for name in fs:
                p = Path(d) / name
                try:
                    files.append((p.relative_to(ROOT).as_posix(), p.stat().st_size, sha(p)))
                except OSError as e:
                    errors.append(str(e))
        if errors:
            blocked.append({'path': old, 'reason': 'access denied; left in place', 'errors': errors})
            continue
        fingerprints.update({p: {'size': size, 'sha256': digest} for p, size, digest in files})
        rows.append({'old': old, 'new': new, 'files': len(files), 'bytes': sum(x[1] for x in files)})
    # Current source, configuration and user-facing records remain in place.
    # Do not traverse model/runtime caches or read the Frozen evidence split.
    for group in ['src', 'scripts', 'configs', 'tests']:
        for p in (ROOT / group).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                fingerprints[p.relative_to(ROOT).as_posix()] = {'size': p.stat().st_size, 'sha256': sha(p)}
    for p in ROOT.glob('*.md'):
        fingerprints[p.name] = {'size': p.stat().st_size, 'sha256': sha(p)}
    for group in ['artifacts/pass_i/reports', 'artifacts/pass_t/reports', 'artifacts/pass_t/phase2a/v2/contracts']:
        for p in (ROOT / group).rglob('*'):
            if p.is_file():
                fingerprints[p.relative_to(ROOT).as_posix()] = {'size': p.stat().st_size, 'sha256': sha(p)}
    record = {'root': str(ROOT), 'moves': rows, 'blocked': blocked, 'files': fingerprints,
              'git_tracked_status': git_state()}
    with (HERE / 'before.json').open('x', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    print(json.dumps({'planned_moves': len(rows), 'relocation_files': sum(x['files'] for x in rows),
                      'relocation_bytes': sum(x['bytes'] for x in rows), 'protected_files': len(fingerprints),
                      'blocked_directories': len(blocked)}))

def verify():
    record = json.loads((HERE / 'before.json').read_text(encoding='utf-8'))
    failures = []
    for name, expected in record['files'].items():
        p = ROOT / name
        if not p.is_file() or p.stat().st_size != expected['size'] or sha(p) != expected['sha256']:
            failures.append(name)
    links = []
    for row in record['moves']:
        old, new = ROOT / row['old'], ROOT / row['new']
        ok = old.exists() and new.exists() and os.path.samefile(old, new)
        links.append({'old': row['old'], 'new': row['new'], 'same_directory': ok})
    result = {'checked_files': len(record['files']), 'changed_or_missing': failures,
              'git_tracked_status_unchanged': git_state() == record['git_tracked_status'],
              'compatibility': links}
    (HERE / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'compatibility'}))
    if failures or not result['git_tracked_status_unchanged'] or not all(x['same_directory'] for x in links):
        raise SystemExit(1)

if __name__ == '__main__':
    {'snapshot': snapshot, 'verify': verify}[sys.argv[1]]()
