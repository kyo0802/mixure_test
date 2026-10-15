"""Frozen policy gate and confined append-only file primitives."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / 'artifacts/pass_t/phase2a/v2'
CONTRACTS = OUT / 'contracts'
EXPECTED_RECEIPT = '3f221f9776378fbb27e2caba01b4d53f33c0c327bfbb564573df5d692b42976a'


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def object_sha(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON: ' + value)))


def utc():
    return datetime.now(timezone.utc).isoformat()


def within(base, path):
    base = Path(base).resolve()
    path = (base / path).resolve()
    if not path.is_relative_to(base):
        raise ValueError('Path outside authorized root')
    return path


def exclusive(path, value, base=OUT):
    path = within(base, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    return sha(path)


def verify_gate(out=OUT, contracts=CONTRACTS):
    receipt_path = contracts / 'EVENT_GT_POLICY_V2.freeze_receipt.json'
    if sha(receipt_path) != EXPECTED_RECEIPT:
        raise ValueError('BLOCKED_FROZEN_RECEIPT_CHANGED')
    receipt = read(receipt_path)
    for name, digest in receipt['files_sha256'].items():
        if sha(contracts / name) != digest:
            raise ValueError('BLOCKED_FROZEN_CONTRACT_CHANGED: ' + name)
    approval = read(out / 'stage_b/approval.json')
    if (approval.get('exact_human_message', '').strip() != receipt['approval_message_required']
            or approval.get('policy_md_sha256') != receipt['policy_md_sha256']
            or approval.get('freeze_receipt_sha256') != EXPECTED_RECEIPT
            or approval.get('source') != 'direct user message in this task'):
        raise ValueError('BLOCKED_APPROVAL_MISSING_OR_MISMATCHED')
    return receipt


def frozen_schema():
    return read(CONTRACTS / 'event_gt_annotation_schema_v2.json')


def preservation(out=OUT, root=ROOT):
    baseline = read(out / 'stage_b/protected_before.json')
    errors = [name for name, digest in baseline.items()
              if not (root / name).is_file() or sha(root / name) != digest]
    return {'verified': len(baseline) - len(errors), 'errors': errors}
