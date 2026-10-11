"""Exclusive human saves and validation inventory. Earlier answers never enter GUI state."""
import os
from collections import Counter
from uuid import uuid4
from .policy import OUT, read, sha, exclusive, within, utc, verify_gate, preservation
from .projection import load_manifest, load_item, load_backend
from .validation import validate, evaluation_metadata


def inventory(out=OUT, verify_visual=True):
    receipt = verify_gate(out)
    manifest = load_manifest(out)
    entries = {e['annotation_item_id']: e for e in manifest['items']}
    parsed, malformed = [], []
    for path in sorted((out / 'responses').glob('*.json')):
        try:
            value = read(path)
            key = (value['annotation_item_id'], value['review_round'])
            if not isinstance(key[0], str) or type(key[1]) is not int:
                raise ValueError('Invalid response key')
            parsed.append((path, value, key))
        except (KeyError, ValueError, TypeError) as error:
            malformed.append({'path': path.relative_to(out).as_posix(), 'valid': False,
                              'errors': ['MALFORMED_RESPONSE: ' + str(error)]})
    counts = Counter(key for _, _, key in parsed)
    results, first = [], {}
    for path, value, key in sorted(parsed, key=lambda row: (row[2][1], str(row[0]))):
        digest = sha(path)
        if counts[key] != 1:
            result = {'valid': False, 'errors': ['DUPLICATE_ITEM_ROUND'], 'exclusions': [], 'warnings': []}
        elif key[0] not in entries:
            result = {'valid': False, 'errors': ['UNAUTHORIZED_OR_EXCLUDED_ITEM'], 'exclusions': ['ORIGINALLY_INELIGIBLE'], 'warnings': []}
        else:
            entry = entries[key[0]]
            item = load_item(entry, out, verify_visual)
            backend = load_backend(entry, out)
            result = validate(value, item, entry['item_sha256'], receipt, backend,
                              first.get(key[0]), manifest['repeat_subset'])
            if result['valid']:
                proof_path = within(out, 'validated/' + value['provenance']['submission_id'] + '.json')
                try:
                    proof = read(proof_path)
                    intact = (proof['response_sha256'] == digest and proof['response_path'] == path.relative_to(out).as_posix()
                              and proof['valid'] is True)
                except (OSError, ValueError, KeyError):
                    intact = False
                if not intact:
                    result['valid'] = False
                    result['errors'].append('IMMUTABLE_SUBMISSION_RECEIPT_MISSING_OR_MISMATCHED')
                    result['error_details'].append({'code': 'IMMUTABLE_SUBMISSION_RECEIPT', 'message': result['errors'][-1]})
            if result['valid'] and key[1] == 1:
                first[key[0]] = {'sha256': digest, 'timestamp': value['provenance']['automatic_timestamp_utc'],
                                'reviewer_id': value['reviewer_id']}
        row = {'path': path.relative_to(out).as_posix(), 'sha256': digest,
               'annotation_item_id': key[0], 'review_round': key[1], **result}
        if result['valid']:
            row['evaluation'] = evaluation_metadata(value, result)
        results.append(row)
    return manifest, results + malformed


def progress(out=OUT):
    manifest, results = inventory(out)
    first = {r['annotation_item_id'] for r in results if r.get('review_round') == 1 and r['valid']}
    repeats = {r['annotation_item_id'] for r in results if r.get('review_round') == 2 and r['valid']}
    return {'eligible_windows': len(manifest['items']), 'eligible_nonoverlap_groups': len({e['overlap_group_id'] for e in manifest['items']}),
            'eligible_source_video_files': len({e['source_video_identifier'] for e in manifest['items']}),
            'valid_round1': len(first), 'valid_round2': len(repeats), 'invalid_records': sum(not r['valid'] for r in results),
            'remaining': [e['annotation_item_id'] for e in manifest['items'] if e['annotation_item_id'] not in first],
            'completed_ids': sorted(first), 'repeat_subset': manifest['repeat_subset'],
            'completed_repeat_ids': sorted(repeats), 'formal_eligible': 0,
            'status': 'HUMAN_ANNOTATION_NOT_STARTED' if not results else
                      'HUMAN_ANNOTATION_VALIDATED_COMPLETE' if len(first) == len(manifest['items']) and all(r['valid'] for r in results)
                      else 'HUMAN_ANNOTATION_INCOMPLETE_OR_INVALID'}


def round_linkage(item_id, out=OUT):
    manifest, results = inventory(out)
    if item_id not in manifest['repeat_subset']:
        raise ValueError('NOT_IN_REPEAT_SUBSET')
    matching = [r for r in results if r.get('annotation_item_id') == item_id and r.get('review_round') == 1]
    if len(matching) != 1 or not matching[0]['valid']:
        raise ValueError('NO_UNIQUE_VALID_ROUND1')
    # Only backend linkage, time and reviewer metadata are returned; no answers.
    row = matching[0]
    value = read(within(out, row['path']))
    return {'sha256': row['sha256'], 'timestamp': value['provenance']['automatic_timestamp_utc'],
            'reviewer_id': value['reviewer_id']}


def attach_backend(draft, item, entry, backend, receipt, round_, linkage=None):
    reserved = {'schema_version', 'annotation_item_id', 'review_round', 'relabel_of',
                'target_reference', 'same_reviewer_as_phase1c', 'provenance'}
    if reserved.intersection(draft):
        raise ValueError('BACKEND_FIELDS_NOT_ALLOWED_IN_DRAFT; importing or migrating responses is not supported')
    value = dict(draft)
    value.update(schema_version='PASS_T_EVENT_GT_V2', annotation_item_id=item['annotation_item_id'],
                 target_reference={'selected_local_candidate_id': item['selected_local_candidate_id'], 'stratum': item['stratum']},
                 review_round=round_, relabel_of=linkage['sha256'] if linkage else None,
                 same_reviewer_as_phase1c=None if backend['phase1c_reviewer_id'] is None
                 else value.get('reviewer_id') == backend['phase1c_reviewer_id'])
    value['provenance'] = {
        'submitted_via': 'human_event_gt_review_viewer', 'automatic_timestamp_utc': utc(),
        'timestamp_recorded_automatically': True, 'submission_id': str(uuid4()),
        'policy_md_sha256': receipt['policy_md_sha256'], 'policy_json_sha256': receipt['policy_json_sha256'],
        'schema_sha256': receipt['schema_sha256'], 'review_item_sha256': entry['item_sha256'],
        'source_video_sha256': item['source_video_sha256'],
        'authorized_visual_manifest_sha256': item['authorized_visual_manifest_sha256'],
        'phase1c_response_sha256': backend['phase1c_response_sha256'], 'seed_provenance_scope': item['seed_provenance_scope'],
        'original_pack_ids': item['original_pack_ids'], 'binding_causality_status': 'CAUSALITY_UNVERIFIED'}
    return value


def submit(draft, entry, round_=1, out=OUT):
    receipt = verify_gate(out)
    manifest, existing = inventory(out)
    if any(not r['valid'] for r in existing):
        raise ValueError('INVALID_EXISTING_RECORDS_REQUIRE_REVIEW; nothing overwritten')
    if entry not in manifest['items']:
        raise ValueError('UNAUTHORIZED_ITEM')
    id_ = entry['annotation_item_id']
    if any(r.get('annotation_item_id') == id_ and r.get('review_round') == round_ for r in existing):
        raise ValueError('DUPLICATE_ITEM_ROUND')
    item = load_item(entry, out)
    backend = load_backend(entry, out)
    linkage = round_linkage(id_, out) if round_ == 2 else None
    value = attach_backend(draft, item, entry, backend, receipt, round_, linkage)
    result = validate(value, item, entry['item_sha256'], receipt, backend, linkage, manifest['repeat_subset'])
    if not result['valid']:
        raise ValueError('\n'.join(result['errors']))
    check = preservation(out)
    if check['errors']:
        raise ValueError('PROTECTED_PRESERVATION_FAILED: ' + str(check['errors'][:10]))
    path = out / 'responses' / (id_ + f'_r{round_}.json')
    digest = exclusive(path, value, out)
    os.chmod(path, 0o444)
    exclusive(out / 'validated' / (value['provenance']['submission_id'] + '.json'),
              {'response_sha256': digest, 'response_path': path.relative_to(out).as_posix(),
               **result, 'evaluation': evaluation_metadata(value, result)}, out)
    return {'path': str(path), 'sha256': digest, 'warnings': result['warnings']}
