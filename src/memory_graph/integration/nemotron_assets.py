"""Local metadata-bound verification cache. No GPU imports or model loading.

Cached validation assumes trusted local storage and metadata. It is NOT fresh
cryptographic validation and does not resist an attacker rewriting the cache or
restoring all file metadata. Strict/force modes always hash every asset.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid
from datetime import datetime, timezone

POLICY = 'nemotron_asset_sha256_v1'
TRADEOFF = 'LOCAL_TRUSTED_METADATA_CACHE_NOT_FRESH_CRYPTOGRAPHIC_REVALIDATION'


def valid_timestamp(value):
    try:return isinstance(value,str) and datetime.fromisoformat(value).tzinfo is not None
    except ValueError:return False


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def atomic(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf8') as f:
            json.dump(value, f, indent=2); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists(): temp.unlink()


def metadata(path):
    s = path.stat()
    return dict(canonical_path=str(path.resolve()), size=s.st_size,
        mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns, inode=s.st_ino, device=s.st_dev)


def verify_assets(model, manifest, receipt_path, *, mode='cached', force=False):
    if mode not in {'cached', 'strict'}: raise ValueError('UNKNOWN_ASSET_VERIFICATION_MODE')
    start = time.monotonic(); model = Path(model).resolve(strict=True)
    raw = Path(manifest).read_bytes(); spec = json.loads(raw)
    if spec.get('policy_version') != POLICY or not spec.get('repository') or not spec.get('revision'):
        raise ValueError('INVALID_ASSET_MANIFEST')
    assets = spec.get('assets')
    if not isinstance(assets, list) or not assets: raise ValueError('EMPTY_ASSET_MANIFEST')
    names = [a['name'] for a in assets]
    if len(set(names)) != len(names): raise ValueError('DUPLICATE_ASSET')
    actual = {p.name for p in model.iterdir() if p.is_file() and p.suffix in {'.json', '.py', '.safetensors'}}
    if actual != set(names): raise ValueError('MODEL_ASSET_SET_CHANGED')
    identity = dict(policy_version=POLICY, repository=spec['repository'], revision=spec['revision'],
        manifest_sha256=hashlib.sha256(raw).hexdigest(), hash_algorithm='sha256', model_location=str(model))
    try:
        cached = json.loads(Path(receipt_path).read_text(encoding='utf8'))
    except (OSError, ValueError): cached = {}
    reusable = (isinstance(cached, dict) and all(cached.get(k) == v for k, v in identity.items())
        and cached.get('outcome') == 'VERIFIED' and isinstance(cached.get('files'), dict)
        and set(cached['files']) == set(names) and valid_timestamp(cached.get('verified_utc')))
    rows = {}; fresh = []; hits = []; elapsed = {}
    for a in assets:
        name = a['name']
        if Path(name).name != name or '/' in name or '\\' in name or not re.fullmatch(r'[a-f0-9]{64}', a['sha256']):
            raise ValueError('INVALID_ASSET_IDENTITY')
        path = (model / name).resolve(strict=True)
        if path.parent != model or not path.is_file(): raise ValueError('ASSET_OUTSIDE_CANONICAL_MODEL')
        before = metadata(path)
        if before['size'] != a['size']: raise ValueError('ASSET_SIZE_MISMATCH:' + name)
        old = cached['files'].get(name, {}) if reusable else {}
        hit = (mode == 'cached' and not force and isinstance(old, dict)
            and old.get('metadata') == before and old.get('sha256') == a['sha256']
            and old.get('expected_sha256') == a['sha256'] and old.get('outcome') == 'VERIFIED'
            and valid_timestamp(old.get('verified_utc')))
        tick = time.monotonic()
        if hit:
            value = old['sha256']; hits.append(name)
        else:
            value = digest(path); fresh.append(name)
            if value != a['sha256']:
                # Tombstone prevents an old successful receipt surviving a known mismatch.
                atomic(receipt_path, dict(**identity, outcome='FAILED', failed_asset=name))
                raise ValueError('ASSET_SHA256_MISMATCH:' + name)
        if metadata(path) != before: raise ValueError('ASSET_CHANGED_DURING_VERIFICATION:' + name)
        elapsed[name] = time.monotonic() - tick
        rows[name] = dict(metadata=before, sha256=value, expected_sha256=a['sha256'], outcome='VERIFIED',
            verified_utc=old['verified_utc'] if hit else datetime.now(timezone.utc).isoformat())
    for name,row in rows.items():
        if metadata(model/name)!=row['metadata']:raise ValueError('ASSET_CHANGED_BEFORE_RECEIPT:'+name)
    verified = dict(**identity, outcome='VERIFIED', verified_utc=datetime.now(timezone.utc).isoformat(), files=rows,
        trust_policy=TRADEOFF)
    atomic(receipt_path, verified)
    return dict(**identity, outcome='VERIFIED', validation_kind='FRESH_SHA256' if not hits else 'CACHED_METADATA' if not fresh else 'MIXED',
        fresh_files=fresh, cached_files=hits, file_seconds=elapsed, elapsed_s=time.monotonic()-start,
        asset_hashes={n:r['sha256'] for n,r in rows.items()}, trust_policy=TRADEOFF, forced=force, mode=mode)


def verify_existing(root, *, mode=None, force=False):
    root = Path(root)
    manifest=root/'config/findmind_nemotron_assets.json'
    spec=json.loads(manifest.read_text(encoding='utf8'))
    if (spec.get('repository'),spec.get('revision')) != (
            'nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-NVFP4-QAD','16853d6c682223e967d5622c99d0082cb994b771'):
        raise ValueError('PINNED_MODEL_REVISION_MISMATCH')
    return verify_assets(root/'.models/Nemotron-Nano-12B-v2-VL-NVFP4-QAD',
        manifest, root/'.runtime/nemotron/verification/assets_v1.json',
        mode=mode or os.environ.get('FINDMIND_NEMOTRON_VERIFICATION', 'cached'),
        force=force or os.environ.get('FINDMIND_NEMOTRON_FORCE_VERIFY') == '1')
