"""Standalone annotation handoff. No original project, models or server required."""
import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from memory_graph.pass_t.phase2a_v2.policy import OUT, read, sha, within, utc, preservation
from memory_graph.pass_t.phase2a_v2.projection import load_manifest, load_item
from memory_graph.pass_t.phase2a_v2.storage import inventory, progress


def check_release():
    receipt = read(ROOT / 'release_receipt.json')
    if receipt['schema_version'] != 'PASS_T_ANNOTATION_HANDOFF_V1':
        raise ValueError('UNKNOWN_HANDOFF_VERSION')
    errors = []
    for name, digest in receipt['files_sha256'].items():
        path = within(ROOT, name)
        if not path.is_file() or sha(path) != digest:
            errors.append(name)
    if errors:
        raise ValueError('HANDOFF_FILE_CHANGED_OR_MISSING: ' + str(errors[:10]))
    manifest = load_manifest()
    if sha(OUT / 'manifest.json') != receipt['source_manifest_sha256']:
        raise ValueError('HANDOFF_SOURCE_MANIFEST_MISMATCH')
    for entry in manifest['items']:
        load_item(entry)
    check = preservation()
    if check['errors']:
        raise ValueError('HANDOFF_PRESERVATION_FAILED: ' + str(check['errors'][:10]))
    status = progress()
    if status['invalid_records']:
        raise ValueError('INVALID_EXISTING_ANNOTATIONS; no files overwritten')
    return {**status, 'status': 'HANDOFF_INTEGRITY_OK', 'annotation_status': status['status'],
            'immutable_files': len(receipt['files_sha256']),
            'preservation_scope': receipt['preservation_scope']}


def export_return(*, partial=False, out=OUT, returns=None):
    """Copy only validated submissions and their receipts into a new ZIP."""
    manifest, rows = inventory(out)
    status = progress(out)
    if status['invalid_records'] or not rows:
        raise ValueError('NO_VALID_SUBMISSIONS_OR_INVALID_RECORDS')
    complete = status['valid_round1'] == len(manifest['items'])
    if not complete and not partial:
        raise ValueError('ANNOTATION_INCOMPLETE: finish all windows or explicitly use --partial')
    files = {}
    for row in rows:
        response = read(within(out, row['path']))
        proof = 'validated/' + response['provenance']['submission_id'] + '.json'
        for name in (row['path'], proof):
            files[name] = sha(within(out, name))
    payload = {'schema_version': 'PASS_T_ANNOTATION_RETURN_V1', 'created_at_utc': utc(),
               'release_receipt_sha256': sha(ROOT / 'release_receipt.json'),
               'source_manifest_sha256': sha(out / 'manifest.json'),
               'policy_md_sha256': manifest['policy_md_sha256'],
               'complete_round1': complete, 'progress': status, 'files_sha256': files,
               'reviewer_ids': sorted({read(within(out, row['path']))['reviewer_id'] for row in rows}),
               'formal_eligible': 0, 'binding_causality_status': 'CAUSALITY_UNVERIFIED',
               'note': 'Returned submissions require owner validation; no automatic import or GT promotion.'}
    returns = Path(returns) if returns is not None else ROOT / 'returns'
    returns.mkdir(parents=True, exist_ok=True)
    path = returns / ('pass_t_annotations_' + str(uuid4()) + '.zip')
    with ZipFile(path, 'x', compression=ZIP_DEFLATED) as archive:
        archive.writestr('return_manifest.json', json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
        archive.write(ROOT / 'release_receipt.json', 'release_receipt.json')
        archive.write(out / 'manifest.freeze.json', 'manifest.freeze.json')
        for name in sorted(files):
            archive.write(within(out, name), name)
    return {'path': str(path.resolve()), 'sha256': sha(path),
            'complete_round1': complete, 'submitted_windows': status['valid_round1']}


def main():
    parser = argparse.ArgumentParser(description='FindMind Pass T V2 human annotation handoff')
    parser.add_argument('command', choices=['check', 'gui', 'progress', 'return'])
    parser.add_argument('--round', type=int, choices=[1, 2], default=1)
    parser.add_argument('--partial', action='store_true', help='Explicitly export an incomplete return ZIP')
    args = parser.parse_args()
    try:
        result = check_release()
        if args.command == 'gui':
            from memory_graph.pass_t.phase2a_v2.viewer import launch
            launch(round_=args.round)
            return
        if args.command == 'return':
            result = export_return(partial=args.partial)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(error)}, ensure_ascii=False, indent=2))
        raise SystemExit(2) from None


if __name__ == '__main__':
    main()
