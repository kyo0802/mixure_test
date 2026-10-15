"""Exclusive, archive-addressed imports; recomputation detects derived-record tampering."""
from pathlib import Path
import os
import stat
from .security import Blocked, HEX, digest, json_bytes, strict_json, safe_path, parse_archive
from .audit import audit, dataset_view


def checked_root(root):
    root = Path(root).absolute()
    for part in (root, *root.parents):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise Blocked('LINK_IN_STORE_ROOT')
    # SHA-addressed records can exceed legacy MAX_PATH on this Windows host.
    if os.name == 'nt' and not str(root).startswith('\\\\?\\'):
        return Path('\\\\?\\' + str(root))
    return root


def payloads(archive, result, raw_zip):
    data = {'source_metadata/archive.zip': raw_zip, 'reports/audit.json': json_bytes(result),
            'exports/external_dev_gt_v1.json': json_bytes(dataset_view(result['records']))}
    for name, raw in archive['members'].items():
        if name.startswith('responses/'): dest = 'original_responses/' + name.split('/')[1]
        elif name.startswith('validated/'): dest = 'original_receipts/' + name.split('/')[1]
        else: dest = 'source_metadata/' + name
        data[dest] = raw
    for record in result['records']:
        name = record['record_id'] + '.json'
        data['independent_validation/' + name] = json_bytes(record)
        bucket = 'quarantine/' if record['category'].startswith('QUARANTINED') else 'accepted_dev/'
        data[bucket + name] = json_bytes({'record_id': record['record_id'], 'category': record['category'],
                                        'response_sha256': record['response_sha256']})
        data['evaluation_metadata/' + name] = json_bytes(record['evaluation'])
        if record['human_review_pending']:
            data['human_review_queue/' + name] = json_bytes({k: record[k] for k in (
                'record_id', 'annotation_item_id', 'reviewer_id', 'source', 'category', 'human_review_flags',
                'authorized_frame_checklist', 'evaluation', 'quality_cleared_for_model_scoring')})
    return data


def create_files(folder, data, receipt):
    checked_root(folder)
    if folder.exists(): raise Blocked('OUTPUT_ALREADY_EXISTS_OR_PARTIAL')
    folder.mkdir(parents=True, exist_ok=False)
    for name, raw in {**data, 'completion_receipt.json': json_bytes(receipt)}.items():
        path = safe_path(folder, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream: stream.write(raw)
        path.chmod(stat.S_IREAD)


def verify_files(folder, expected, receipt):
    checked_root(folder)
    actual = set()
    for path in folder.rglob('*'):
        safe_path(folder, path.relative_to(folder).as_posix())
        if path.is_file(): actual.add(path.relative_to(folder).as_posix())
    if actual != set(expected) | {'completion_receipt.json'}:
        raise Blocked('IMPORTED_FILE_SET_CONFLICT_OR_PARTIAL')
    if receipt.get('files_sha256') != {n: digest(b) for n, b in sorted(expected.items())}:
        raise Blocked('DERIVED_RECORD_RECEIPT_CONFLICT')
    for name, raw in expected.items():
        path = safe_path(folder, name)
        if path.read_bytes() != raw: raise Blocked('IMPORTED_BYTES_CONFLICT: ' + name)
        if path.stat().st_mode & stat.S_IWRITE: raise Blocked('IMPORT_NOT_READ_ONLY: ' + name)


def verify_import(root, sha, authority, cache=None, visiting=None):
    root = checked_root(root)
    if not HEX.fullmatch(sha): raise Blocked('INVALID_IMPORT_KEY')
    cache = {} if cache is None else cache
    visiting = set() if visiting is None else visiting
    if sha in cache: return cache[sha]
    if sha in visiting: raise Blocked('CYCLIC_IMPORT_DEPENDENCY')
    visiting.add(sha)
    folder = safe_path(root, sha)
    completion = safe_path(folder, 'completion_receipt.json')
    if not completion.is_file(): raise Blocked('PARTIAL_IMPORT_NO_COMPLETION_RECEIPT')
    receipt = strict_json(completion.read_bytes())
    if (receipt.get('schema_version') != 'PASS_T_EXTERNAL_IMPORT_V1' or receipt.get('archive_sha256') != sha
            or not isinstance(receipt.get('dependencies'), list)):
        raise Blocked('INVALID_IMPORT_RECEIPT')
    dependencies = receipt['dependencies']
    if any(not isinstance(d, str) or not HEX.fullmatch(d) for d in dependencies) or len(set(dependencies)) != len(dependencies):
        raise Blocked('INVALID_IMPORT_DEPENDENCIES')
    prior = []
    for dep in dependencies: prior.extend(verify_import(root, dep, authority, cache, visiting)['records'])
    source = safe_path(folder, 'source_metadata/archive.zip')
    archive = parse_archive(source, sha)
    result = audit(archive, authority, prior)
    expected = payloads(archive, result, source.read_bytes())
    verify_files(folder, expected, receipt)
    visiting.remove(sha)
    cache[sha] = result
    return result


def inventory(root, authority):
    root = checked_root(root)
    cache = {}
    if root.exists():
        for folder in sorted(root.iterdir()):
            if folder.name == 'datasets': continue
            if not HEX.fullmatch(folder.name) or not folder.is_dir(): raise Blocked('UNEXPECTED_STORE_ENTRY')
            verify_import(root, folder.name, authority, cache)
    return cache


def import_archive(source, sha, root, authority):
    archive = parse_archive(source, sha)
    existing = inventory(root, authority)
    if sha in existing:
        return {'status': 'ALREADY_IMPORTED', 'archive_sha256': sha, 'audit': existing[sha]}
    prior = [r for key in sorted(existing) for r in existing[key]['records']]
    result = audit(archive, authority, prior)
    raw = Path(source).read_bytes()
    if digest(raw) != sha: raise Blocked('SOURCE_CHANGED_DURING_IMPORT')
    data = payloads(archive, result, raw)
    receipt = {'schema_version': 'PASS_T_EXTERNAL_IMPORT_V1', 'archive_sha256': sha,
               'dependencies': sorted(existing), 'files_sha256': {n: digest(b) for n, b in sorted(data.items())}}
    create_files(checked_root(root) / sha, data, receipt)
    verify_import(root, sha, authority)
    return {'status': 'IMPORTED', 'archive_sha256': sha, 'audit': result}


def finalize(root, authority):
    from ..phase2a_v2 import policy
    from .resolutions import current_dataset_view
    imports = inventory(root, authority)
    if not imports: raise Blocked('NO_VERIFIED_IMPORTS')
    repository_root = policy.ROOT if checked_root(root) == checked_root(policy.OUT / 'external_returns') else None
    dataset = current_dataset_view([r for key in sorted(imports) for r in imports[key]['records']], repository_root)
    raw = json_bytes(dataset)
    version = digest(raw)
    folder = checked_root(root) / 'datasets' / version
    data = {'external_dev_gt.json': raw}
    receipt = {'schema_version': 'PASS_T_EXTERNAL_DATASET_RECEIPT_V1', 'imports': sorted(imports),
               'dataset_sha256': version, 'files_sha256': {n: digest(b) for n, b in data.items()}}
    if folder.exists():
        stored = strict_json(safe_path(folder, 'completion_receipt.json').read_bytes())
        if stored != receipt: raise Blocked('DATASET_RECEIPT_CONFLICT')
        verify_files(folder, data, stored)
    else: create_files(folder, data, receipt)
    return {'path': str(folder / 'external_dev_gt.json'), 'sha256': version, 'summary': dataset['summary']}
