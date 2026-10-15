"""External DEV operations; deliberately cannot write canonical responses."""
import argparse
import json
from pathlib import Path
from uuid import uuid4
from ..phase2a_v2 import policy
from .authority import load_authority
from .security import Blocked, json_bytes, parse_archive
from .audit import audit, dataset_view
from .store import import_archive, inventory, verify_import, finalize
from .reporting import markdown
from .resolutions import current_dataset_view


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['audit', 'import', 'verify', 'status', 'pending', 'finalize', 'stats'])
    parser.add_argument('--zip', type=Path)
    parser.add_argument('--sha256')
    args = parser.parse_args(argv)
    root = policy.OUT / 'external_returns'
    diagnostic = policy.OUT / 'external_return_audits' / ('operation_' + uuid4().hex)
    try:
        if args.operation in ('audit', 'import', 'verify'):
            if not args.zip or not args.sha256: raise Blocked('EXPLICIT_ZIP_AND_SHA256_REQUIRED')
            archive = parse_archive(args.zip, args.sha256)
        authority = load_authority()
        if args.operation == 'audit':
            prior = [r for a in inventory(root, authority).values() if a['archive_sha256'] != args.sha256 for r in a['records']]
            result = audit(archive, authority, prior)
        elif args.operation == 'import':
            result = import_archive(args.zip, args.sha256, root, authority)
            result['export'] = finalize(root, authority)
            result['completion_status'] = 'PASS_T_PHASE2A_EXTERNAL_RETURN_IMPORTED_DEV_WITH_REVIEW_FLAGS'
        elif args.operation == 'verify':
            result = {'status': 'VERIFIED', 'audit': verify_import(root, args.sha256, authority),
                      'export': finalize(root, authority)}
        elif args.operation == 'finalize': result = finalize(root, authority)
        else:
            imports = inventory(root, authority)
            data = current_dataset_view([r for key in sorted(imports) for r in imports[key]['records']], policy.ROOT)
            result = {'imports': sorted(imports), 'summary': data['summary']}
            if args.operation == 'pending':
                result['pending'] = [{k: r[k] for k in ('annotation_item_id', 'reviewer_id', 'human_review_flags',
                    'authorized_frame_checklist')} for r in data['records'] if r['human_review_pending']]
        diagnostic.mkdir(parents=True, exist_ok=False)
        with (diagnostic / 'result.json').open('xb') as stream: stream.write(json_bytes(result))
        report = result.get('audit', result if 'records' in result else None)
        if report:
            with (diagnostic / 'audit.md').open('x', encoding='utf-8') as stream:
                stream.write(markdown(report, result.get('completion_status')))
        display = {k: v for k, v in result.items() if k not in ('audit', 'records', 'pending')}
        if 'audit' in result: display['summary'] = result['audit']['summary']
        print(json.dumps({'diagnostic': str(diagnostic), **display}, ensure_ascii=True, indent=2))
        return 0
    except (Blocked, OSError, ValueError, KeyError) as error:
        diagnostic.mkdir(parents=True, exist_ok=False)
        result = {'status': 'PASS_T_PHASE2A_EXTERNAL_RETURN_IMPORT_BLOCKED', 'reason': str(error),
                  'operation': args.operation, 'source': str(args.zip), 'expected_sha256': args.sha256}
        with (diagnostic / 'BLOCKED.json').open('xb') as stream: stream.write(json_bytes(result))
        print(json.dumps({**result, 'diagnostic': str(diagnostic)}, ensure_ascii=True))
        return 2


if __name__ == '__main__': raise SystemExit(main())
