"""Independent production validation with separate quality and exclusion axes."""
from collections import Counter
from jsonschema import Draft202012Validator
from ..phase2a_v2 import policy, validation
from .authority import compatible
from .security import digest, json_bytes, RESPONSE, PROOF, Blocked

RECONCILE = 'REVIEWER_IDENTITY_RECONCILIATION_REQUIRED'
VISUAL = 'MANUAL_VISUAL_REVIEW_REQUIRED'
EXPOSURE = 'EXPOSURE_ATTESTATION_REQUIRES_HUMAN_CLARIFICATION'


def audit(archive, authority, prior=()):
    compatible(archive, authority)
    entries = {e['annotation_item_id']: e for e in authority.manifest['items']}
    values = archive['values']
    responses = [(n, v) for n, v in values.items() if RESPONSE.fullmatch(n)]
    referenced_proofs = {'validated/' + str(v['provenance'].get('submission_id')) + '.json'
                         for _, v in responses if isinstance(v.get('provenance'), dict)}
    if any(PROOF.fullmatch(n) and n not in referenced_proofs for n in values):
        raise Blocked('UNREFERENCED_VALIDATION_RECEIPT')
    reviewer_ids = sorted({v.get('reviewer_id') for _, v in responses if isinstance(v.get('reviewer_id'), str)})
    # Multiple exact strings remain unresolved people, never fuzzy-matched or normalized.
    reconcile = len(reviewer_ids) > 1
    ids = Counter(str(v.get('provenance', {}).get('submission_id')) for _, v in responses if isinstance(v.get('provenance'), dict))
    keys = Counter((str(v.get('annotation_item_id')), str(v.get('review_round')), str(v.get('reviewer_id'))) for _, v in responses)
    records = []
    validated_first = {r['response_sha256']: r for r in prior if r['valid'] and r['review_round'] == 1}
    for name, response in sorted(responses, key=lambda row: (str(row[1].get('review_round')), row[0])):
        id_ = response.get('annotation_item_id')
        entry = entries.get(id_) if isinstance(id_, str) else None
        item = authority.items.get(id_) if entry else None
        schema_errors = [e.message for e in Draft202012Validator(policy.frozen_schema()).iter_errors(response)]
        schema_valid = not schema_errors
        own_errors = []
        raw_result = {'valid': False, 'errors': schema_errors or ['UNAUTHORIZED_PHASE1C_ITEM'],
                      'error_details': [], 'exclusions': [], 'warnings': []}
        prov = response.get('provenance', {})
        prov = prov if isinstance(prov, dict) else {}
        sid = prov.get('submission_id')
        round_ = response.get('review_round')
        reviewer = response.get('reviewer_id')
        link = validated_first.get(response.get('relabel_of')) if isinstance(response.get('relabel_of'), str) else None
        round1 = None
        if link:
            first = link['response']
            round1 = {'sha256': link['response_sha256'], 'timestamp': first['provenance']['automatic_timestamp_utc'],
                      'reviewer_id': first['reviewer_id']}
            if first['annotation_item_id'] != id_ or first['reviewer_id'] != reviewer:
                own_errors.append('ROUND2_REQUIRES_SAME_EXACT_REVIEWER_AND_ITEM')
        if schema_valid and item:
            raw_result = validation.validate(response, item, entry['item_sha256'], authority.receipt,
                                              authority.backends[id_], round1, authority.manifest['repeat_subset'])
        if name != f'responses/{id_}_r{round_}.json':
            own_errors.append('RESPONSE_MEMBER_ITEM_ROUND_MISMATCH')
        if ids[str(sid)] != 1 or keys[(str(id_), str(round_), str(reviewer))] != 1:
            own_errors.append('DUPLICATE_SUBMISSION')
        if any(r.get('submission_id') == sid for r in prior):
            own_errors.append('SUBMISSION_ID_REUSED_ACROSS_ARCHIVES')
        proof_name = 'validated/' + str(sid) + '.json'
        proof = values.get(proof_name)
        response_sha = digest(archive['members'][name])
        expected_proof = {'response_sha256': response_sha, 'response_path': name, **raw_result}
        if schema_valid:
            expected_proof['evaluation'] = validation.evaluation_metadata(response, raw_result)
        proof_valid = proof == expected_proof and raw_result['valid']
        if not proof_valid:
            own_errors.append('ORIGINAL_VALIDATION_RECEIPT_INVALID_OR_ALTERED')
        provenance_errors = [e for e in raw_result['errors'] if e.startswith(('Provenance', 'Reviewer', 'Item ID', 'Target/stratum'))]
        semantic_errors = [e for e in raw_result['errors'] if e not in provenance_errors]
        valid = bool(raw_result['valid'] and not own_errors)
        result = {**raw_result, 'valid': valid, 'errors': raw_result['errors'] + own_errors}
        evaluation = validation.evaluation_metadata(response, result) if schema_valid else {
            'full_window_event_evaluation_supported': False, 'primary_full_window_metrics_eligible': False,
            'supported_event_exploratory_use_allowed': False, 'unlisted_events_status': 'UNEVALUATED',
            'event_evaluation_exclusion_reasons': ['INVALID_RESPONSE'], 'formal_eligible': False,
            'binding_causality_status': 'CAUSALITY_UNVERIFIED'}
        outcome = response.get('window_outcome')
        if not valid: category = 'QUARANTINED_INVALID'
        elif result['exclusions']: category = 'QUARANTINED_EXCLUDED'
        elif outcome == 'NO_CONFIRMED_EVENT': category = 'ACCEPTED_STRICT_NEGATIVE'
        elif outcome in ('INSUFFICIENT_EVIDENCE', 'TARGET_NOT_OBSERVABLE'): category = 'ACCEPTED_UNCERTAIN'
        elif response.get('event_list_exhaustiveness') != 'EXHAUSTIVE_ATTESTED': category = 'ACCEPTED_EXPLORATORY_POSITIVE'
        else: category = 'ACCEPTED_CLEAN_DEV'
        flags = []
        if reconcile: flags.append(RECONCILE)
        if result['exclusions']: flags.append(EXPOSURE)
        if outcome == 'CONFIRMED_EVENTS': flags.append(VISUAL)
        if not valid: flags.append('INVALID_RESPONSE_REQUIRES_OWNER_REVIEW')
        frames = {f['frame_id']: f for f in item['visual']['frames']} if item else {}
        checklist = []
        if schema_valid and item:
            seen = set()
            for c in validation._all_citations(response):
                key = (c['frame_id'], c['role'], c.get('visual_description'))
                if key in seen: continue
                seen.add(key)
                if c['frame_id'] in frames:
                    checklist.append({**frames[c['frame_id']], 'role': c['role'],
                                      'annotation_description': c['visual_description'],
                                      'asserted_target_association': c['target_association'],
                                      'review_scope': 'AUTHORIZED_FRAME_ONLY; statement is not independently visually verified'})
        record_id = digest(json_bytes([archive['sha256'], sid, response_sha]))
        record = {'record_id': record_id, 'archive_sha256': archive['sha256'], 'original_member_path': name,
                  'response_sha256': response_sha, 'submission_id': sid, 'annotation_item_id': id_,
                  'reviewer_id': reviewer, 'review_round': round_, 'response': response,
                  'original_validation_receipt': proof, 'original_receipt_member': proof_name if proof else None,
                  'schema_valid': schema_valid, 'schema_errors': schema_errors,
                  'semantic_valid': not semantic_errors if schema_valid and item else None,
                  'provenance_valid': bool(entry and not provenance_errors and not own_errors),
                  'immutable_receipt_valid': proof_valid, 'valid': valid,
                  'production_validation': raw_result, 'independent_validation': result,
                  'category': category, 'human_review_flags': flags, 'human_review_pending': bool(flags),
                  'visual_correctness': 'NOT_INDEPENDENTLY_REVIEWED', 'evaluation': evaluation,
                  'quality_cleared_for_model_scoring': bool(evaluation['full_window_event_evaluation_supported'] and not flags),
                  'exploratory_positive_quality_cleared': bool(evaluation['supported_event_exploratory_use_allowed'] and not flags),
                  'source': {k: item[k] for k in ('original_pack_ids', 'source_video_identifier', 'source_video_sha256',
                            'overlap_group_id', 'selected_local_candidate_id', 'stratum', 'window_start_s', 'window_end_s',
                            'binding_causality_status', 'seed_provenance_scope')} if item else None,
                  'authorized_frame_checklist': checklist, 'formal_eligible': 0,
                  'review_relation': ('SAME_EXACT_ID_BLINDED_REPEAT' if valid else 'INVALID_REPEAT_LINKAGE')
                      if round_ == 2 else 'FIRST_ROUND_EXACT_REVIEWER_ID'}
        records.append(record)
        if valid and round_ == 1: validated_first[response_sha] = record
    return {'schema_version': 'PASS_T_EXTERNAL_AUDIT_V1', 'archive_sha256': archive['sha256'],
            'archive_integrity': 'VERIFIED', 'authority': authority.verification,
            'return_claims': values['return_manifest.json'], 'records': records,
            'summary': summarize(records), 'limits': limitations()}


def limitations():
    return ['Hashes/attestations do not prove authorship or visual correctness.',
            'Event-expected selection; no prospectively sampled negative controls.',
            'Recording-session independence UNKNOWN; windows are not independent sessions.',
            'Only PICKUP/PLACEMENT ontology; causality unverified; formal eligibility zero.',
            'Non-exhaustive unlisted events UNEVALUATED; no model metrics computed.',
            'Future Phase2b needs human quality review and prospective scoring/sampling preregistration.']


def summarize(records):
    def count(key): return sum(bool(r.get(key)) for r in records)
    return {'submitted_responses': len(records), 'unique_item_ids': len({str(r['annotation_item_id']) for r in records}),
            'valid_first_round': sum(r['valid'] and r['review_round'] == 1 for r in records),
            'independently_valid': count('valid'), 'invalid': len(records)-count('valid'),
            'categories': dict(Counter(r['category'] for r in records)),
            'outcomes': dict(Counter(str(r['response'].get('window_outcome')) for r in records)),
            'event_types': dict(Counter(e['event_type'] for r in records if r['schema_valid'] for e in r['response']['events'])),
            'reviewer_ids': dict(Counter(str(r['reviewer_id']) for r in records)),
            'human_review_required': count('human_review_pending'),
            'quarantined': sum(r['category'].startswith('QUARANTINED') for r in records),
            'accepted_dev': sum(r['category'].startswith('ACCEPTED') for r in records),
            'strict_negative_windows': sum(r['category'] == 'ACCEPTED_STRICT_NEGATIVE' for r in records),
            'exhaustive_positive_windows': sum(r['valid'] and r['response'].get('event_list_exhaustiveness') == 'EXHAUSTIVE_ATTESTED' for r in records),
            'non_exhaustive_positive_windows': sum(r['valid'] and r['response'].get('event_list_exhaustiveness') in ('NOT_ATTESTED','UNKNOWN') for r in records),
            'full_window_dev_supported': sum(r['evaluation']['full_window_event_evaluation_supported'] for r in records),
            'primary_full_window_dev_eligible': sum(r['evaluation']['primary_full_window_metrics_eligible'] for r in records),
            'sensitivity_only_full_window': sum(r['evaluation']['full_window_event_evaluation_supported'] and not r['evaluation']['primary_full_window_metrics_eligible'] for r in records),
            'exploratory_positive_records': sum(r['evaluation']['supported_event_exploratory_use_allowed'] for r in records),
            'eligible_exploratory_positive_events': sum(len(r['response']['events']) for r in records if r['evaluation']['supported_event_exploratory_use_allowed']),
            'quality_cleared_for_model_scoring': count('quality_cleared_for_model_scoring'),
            'distinct_evidence_groups': len({r['source']['overlap_group_id'] for r in records if r['source']}),
            'distinct_source_files': len({r['source']['source_video_sha256'] for r in records if r['source']}),
            'recording_session_independence': 'UNKNOWN', 'formal_eligible': 0, 'binding_causality_status': 'CAUSALITY_UNVERIFIED',
            'model_metrics_computed': False}


def dataset_view(records):
    """Cross-archive comparisons add flags to exports, never mutate imported records."""
    import copy
    records = copy.deepcopy(records)
    grouped = {}
    for r in records: grouped.setdefault(str(r['annotation_item_id']), []).append(r)
    comparisons = []
    for id_, group in grouped.items():
        first = [r for r in group if r['valid'] and r['review_round'] == 1]
        fingerprints = {digest(json_bytes({k: r['response'].get(k) for k in (
            'window_outcome','events','last_confirmed_state','last_confirmed_frame_id',
            'visibility_at_window_end','event_list_exhaustiveness')})) for r in first}
        if len(first) > 1:
            disagree = len(fingerprints) > 1
            comparisons.append({'annotation_item_id': id_, 'records': [r['record_id'] for r in first],
                                'exact_reviewer_ids': sorted({r['reviewer_id'] for r in first}),
                                'structured_answers_differ': disagree, 'independent_persons_verified': False,
                                'comparison_scope': 'Exact structured answers, including descriptions; not a reliability statistic.'})
            for r in first:
                r['human_review_flags'] = sorted(set(r['human_review_flags'] + [RECONCILE] + (['ADJUDICATION_PENDING'] if disagree else [])))
                r['human_review_pending'] = True
                r['quality_cleared_for_model_scoring'] = False
                r['exploratory_positive_quality_cleared'] = False
    return {'schema_version': 'PASS_T_EXTERNAL_DEV_GT_V1', 'records': records, 'summary': summarize(records),
            'views': {'full_window_dev_evidence': [r['record_id'] for r in records if r['evaluation']['full_window_event_evaluation_supported']],
                      'exploratory_supported_positives': [r['record_id'] for r in records if r['evaluation']['supported_event_exploratory_use_allowed']],
                      'uncertain_outcomes': [r['record_id'] for r in records if r['category'] == 'ACCEPTED_UNCERTAIN'],
                      'quarantined': [r['record_id'] for r in records if r['category'].startswith('QUARANTINED')],
                      'pending_manual_review': [r['record_id'] for r in records if r['human_review_pending']]},
            'reviewer_comparisons': comparisons, 'formal_eligible': 0, 'limits': limitations()}
