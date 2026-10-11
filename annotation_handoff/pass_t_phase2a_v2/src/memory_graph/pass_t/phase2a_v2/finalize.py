"""Descriptive DEV-only exports and optional human-specified sampling diagnostics."""
import os
from collections import Counter
from datetime import datetime
from uuid import uuid4
from .policy import OUT, read, exclusive, within, utc, preservation
from .projection import load_item
from .storage import inventory
from .validation import _all_citations


def sampling(response, item, strides=()):
    if any(type(k) is not int or k <= 0 for k in strides):
        raise ValueError('STRIDES_MUST_BE_EXPLICIT_POSITIVE_INTEGERS')
    if not strides:
        return {'status': 'SAMPLING_NOT_REQUESTED', 'events': []}
    if not response['events']:
        return {'status': 'NO_CONFIRMED_EVENTS', 'events': []}
    frames = item['visual']['frames']
    positions = {f['frame_id']: j for j, f in enumerate(frames)}
    rows = []
    for event in response['events']:
        spans = {}
        for role in ('BEFORE', 'AFTER'):
            js = [positions[c['frame_id']] for c in event['evidence'] if c['role'] == role]
            a, b = min(js), max(js)
            spans[role] = {'start_position': a, 'end_position': b,
                           'start_frame_id': frames[a]['frame_id'], 'end_frame_id': frames[b]['frame_id'],
                           'start_pts_s': frames[a]['source_timestamp_s'], 'end_pts_s': frames[b]['source_timestamp_s']}
        time = event['event_time']; a, b = positions[time['start_frame_id']], positions[time['end_frame_id']]
        for k in strides:
            good, bad = [], []
            per_offset = []
            for offset in range(k):
                hits = {role: any(j % k == offset for j in range(span['start_position'], span['end_position'] + 1))
                        for role, span in spans.items()}
                (good if all(hits.values()) else bad).append(offset)
                per_offset.append({'offset': offset, **hits})
            rows.append({'event_id': event['event_id'], 'stride_frames': k, 'successful_offsets': good,
                         'failed_offsets': bad, 'all_offset_success': not bad, 'per_offset': per_offset,
                         'evidence_spans': spans, 'bracket_width_frames': b - a,
                         'native_pts_duration_s': time['end_timestamp_s'] - time['start_timestamp_s'],
                         'bracket_shorter_than_stride': b - a < k})
    return {'status': 'DESCRIPTIVE_SAMPLING_DIAGNOSTIC', 'events': rows,
            'limitation': 'Span envelopes do not prove continuous informative evidence or VLM accuracy. No model inputs selected.'}


def accounting(entries):
    return {'windows': len(entries), 'nonoverlap_groups': len({e['overlap_group_id'] for e in entries}),
            'source_video_files': len({e['source_video_identifier'] for e in entries})}


def finalize(out=OUT, strides=()):
    if any(type(k) is not int or k <= 0 for k in strides):
        raise ValueError('STRIDES_MUST_BE_EXPLICIT_POSITIVE_INTEGERS')
    manifest, results = inventory(out)
    if any(not r['valid'] for r in results):
        raise ValueError('FINALIZE_BLOCKED_INVALID_OR_DUPLICATE_RECORDS')
    first = [r for r in results if r['review_round'] == 1]
    if not first:
        raise ValueError('FINALIZE_BLOCKED_NO_GENUINE_VALIDATED_HUMAN_RESPONSES')
    check = preservation(out)
    if check['errors']:
        raise ValueError('FINALIZE_BLOCKED_PROTECTED_ARTIFACT_CHANGED')
    entries = {e['annotation_item_id']: e for e in manifest['items']}
    dataset = []
    for result in first:
        entry = entries[result['annotation_item_id']]
        response = read(within(out, result['path']))
        item = load_item(entry, out)
        dataset.append({'annotation_item_id': result['annotation_item_id'],
                        'source_video_identifier': item['source_video_identifier'],
                        'source_video_sha256': item['source_video_sha256'],
                        'overlap_group_id': item['overlap_group_id'], 'stratum': item['stratum'],
                        'original_pack_ids': item['original_pack_ids'], 'selected_local_candidate_id': item['selected_local_candidate_id'],
                        'original_dev_eligible': item['dev_eligible'], 'validation_exclusions': result['exclusions'],
                        'window_start_s': item['window_start_s'], 'window_end_s': item['window_end_s'],
                        'response_sha256': result['sha256'], 'response': response, 'evaluation': result['evaluation'],
                        'sampling': sampling(response, item, strides)})
    repeat_results = []
    by_id = {d['annotation_item_id']: d for d in dataset}
    for result in results:
        if result['review_round'] == 2:
            value = read(within(out, result['path']))
            original = by_id[result['annotation_item_id']]['response']
            delay = (datetime.fromisoformat(value['provenance']['automatic_timestamp_utc'].replace('Z', '+00:00'))
                     - datetime.fromisoformat(original['provenance']['automatic_timestamp_utc'].replace('Z', '+00:00'))).total_seconds() / 86400
            repeat_results.append({'annotation_item_id': result['annotation_item_id'], 'response_sha256': result['sha256'],
                                   'delay_days': delay, 'shorter_than_recommended_delay': delay < 7,
                                   'same_reviewer': value['reviewer_id'] == original['reviewer_id'],
                                   'outcome_agreement': value['window_outcome'] == original['window_outcome'],
                                   'event_type_sequence_agreement': [e['event_type'] for e in value['events']] == [e['event_type'] for e in original['events']],
                                   'event_interval_exact_agreement': [e['event_time'] for e in value['events']] == [e['event_time'] for e in original['events']],
                                   'last_state_agreement': value['last_confirmed_state'] == original['last_confirmed_state'],
                                   'exhaustiveness_agreement': value.get('event_list_exhaustiveness') == original.get('event_list_exhaustiveness'),
                                   'limitation': 'Single-reviewer descriptive comparison only; no reliability claim'})
    responses = [d['response'] for d in dataset]
    def distribution(key):
        return dict(Counter(r.get(key, 'NOT_APPLICABLE') for r in responses))
    annotated_entries = [entries[d['annotation_item_id']] for d in dataset]
    strata = {}
    for d in dataset:
        key = d['stratum'] + '|' + d['response']['target_identification_event_dependence']
        strata.setdefault(key, []).append(entries[d['annotation_item_id']])
    summary = {'export_created_at_utc': utc(), 'status': 'DEV_GT_VALIDATED_COMPLETE' if len(first) == len(entries) else 'DEV_GT_PARTIAL',
               'submitted_round1_windows': len(first), 'valid_round1_windows': len(first), 'invalid_records': 0,
               'eligible_inventory': accounting(manifest['items']), 'annotated_inventory': accounting(annotated_entries),
               'remaining_annotation_ids': sorted(set(entries) - set(by_id)),
               'outcome_distribution': distribution('window_outcome'), 'exhaustiveness_distribution': distribution('event_list_exhaustiveness'),
               'confirmed_event_types': dict(Counter(e['event_type'] for r in responses for e in r['events'])),
               'citation_kinds': dict(Counter(c['kind'] for r in responses for c in _all_citations(r))),
               'unmodeled_observation_count': sum(len(r['unmodeled_observations']) for r in responses),
               'strata': {key: accounting(value) for key, value in strata.items()},
               'clean_original_DEV_eligible_submissions': sum(not d['validation_exclusions'] for d in dataset),
               'primary_target_localized_submissions': sum(not d['validation_exclusions'] and d['response']['target_identification_event_dependence'] == 'NOT_DEPENDENT' for d in dataset),
               'full_window_supported': sum(d['evaluation']['full_window_event_evaluation_supported'] for d in dataset),
               'primary_full_window_eligible': sum(d['evaluation']['primary_full_window_metrics_eligible'] for d in dataset),
               'exclusion_reasons': dict(Counter(reason for d in dataset for reason in d['evaluation']['event_evaluation_exclusion_reasons'])),
               'repeat_comparison': repeat_results, 'formal_eligible': 0, 'metrics_computed': False,
               'causality_status': 'CAUSALITY_UNVERIFIED', 'recording_session_independence': 'UNKNOWN',
               'sampling_strides_human_supplied': list(strides),
               'limits': ['Event-expected selection; no sampled negative controls; base-rate bias.',
                          'Same source windows are not independent recording sessions.',
                          'Only PICKUP/PLACEMENT ontology; unmodeled observations remain gaps.',
                          'Likely same person selected target and labeled events; self-declared dependence not independently verified.',
                          'No metric scoring/matching protocol frozen; non-exhaustive unlisted events UNEVALUATED.',
                          'Structural validation and hashes cannot prove human visual correctness/authorship.']}
    folder = out / 'exports' / ('export_' + str(uuid4()))
    export_hash = exclusive(folder / 'event_gt_dev.json', {'summary': summary, 'items': dataset}, out)
    exclusive(folder / 'export_receipt.json', {'event_gt_dev_sha256': export_hash, 'created_at_utc': utc()}, out)
    for path in folder.iterdir():
        os.chmod(path, 0o444)
    return {'export_path': str(folder / 'event_gt_dev.json'), 'sha256': export_hash, 'summary': summary}
