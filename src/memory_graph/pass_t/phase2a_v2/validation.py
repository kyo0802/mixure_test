"""Deterministic frozen-schema and semantic checks; never infer visual truth."""
import math
from datetime import datetime
from uuid import UUID
from jsonschema import Draft202012Validator
from .policy import frozen_schema, object_sha


def error_details(errors):
    categories = [('SCHEMA', 'SCHEMA_CONTRACT'), ('timestamp', 'NATIVE_TIMESTAMP'),
                  ('frame', 'FRAME_MEMBERSHIP'), ('observation', 'OBSERVATION_MAPPING'),
                  ('Coverage', 'FULL_WINDOW_COVERAGE'), ('gap', 'FULL_WINDOW_ASSESSABILITY'),
                  ('Provenance', 'PROVENANCE_HASH'), ('Reviewer', 'REVIEWER_LINKAGE'),
                  ('Marker', 'MARKER_GEOMETRY'), ('POINT', 'MARKER_GEOMETRY'), ('BBOX', 'MARKER_GEOMETRY'),
                  ('STATE', 'STATE_SUPPORT'), ('state', 'STATE_SUPPORT'), ('Event', 'EVENT_CHRONOLOGY'),
                  ('BEFORE', 'EVENT_CHRONOLOGY'), ('transition', 'EVENT_CHRONOLOGY'),
                  ('Duplicate', 'DUPLICATE_ASSERTION'), ('round', 'REVIEW_ROUND_LINKAGE')]
    return [{'code': next((code for word, code in categories if word in message), 'SEMANTIC_CONTRACT'),
             'message': message} for message in errors]


def _all_citations(response):
    yield from response['coverage_citations']
    yield from response['last_confirmed_state_evidence']
    yield from response['subsequent_location_evidence']
    yield from response['visibility_at_window_end']['evidence']
    for event in response['events']:
        yield from event['evidence']
        for state in (event['before_state'], event['after_state']):
            if state:
                yield from state['evidence']
    for observation in response['unmodeled_observations']:
        yield from observation['evidence']


def validate(response, item, item_sha, receipt, backend, round1=None, repeat_ids=()):
    errors = [f'SCHEMA {"/".join(map(str, error.absolute_path))}: {error.message}'
              for error in Draft202012Validator(frozen_schema()).iter_errors(response)]
    if errors:
        return {'valid': False, 'errors': errors, 'error_details': error_details(errors), 'exclusions': [], 'warnings': []}
    warnings = []
    def need(condition, reason):
        if not condition:
            errors.append(reason)
    def finite(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    def nonblank(value):
        return isinstance(value, str) and bool(value.strip())
    frames = item['visual']['frames']
    table = {f['frame_id']: f for f in frames}
    positions = {f['frame_id']: i for i, f in enumerate(frames)}
    selected = item['selected_local_candidate_id']
    obs = {}
    for row in item['observations']:
        if row['candidate_id'] == selected:
            obs.setdefault(row['source_frame_index'], set()).add(row['observation_id'])
    def frame_time(fid, time, context):
        if fid not in table:
            need(False, context + ': unauthorized frame (references never citable)')
            return False
        row = table[fid]
        lo, hi = item['authorized_half_open_frames']
        need(lo <= row['source_frame_index'] < hi
             and item['window_start_s'] <= row['source_timestamp_s'] < item['window_end_s'],
             context + ': half-open bounds')
        need(finite(time) and abs(time - row['source_timestamp_s']) <= 1e-6,
             context + ': native timestamp mismatch/nonfinite')
        return True
    def citation(cite, context):
        if not frame_time(cite['frame_id'], cite['source_timestamp_s'], context):
            return
        available = obs.get(table[cite['frame_id']]['source_frame_index'], set())
        ids = set(cite['source_observation_ids'])
        if cite['kind'] == 'CANDIDATE_OBSERVATION_BACKED':
            need(bool(ids) and ids <= available, context + ': wrong selected observation')
        else:
            need(not available and not ids and nonblank(cite['visual_description']),
                 context + ': DIRECT requires no selected observation and visible what/where description')
    def supported_at(cites, fid, role='STATE'):
        return any(c['frame_id'] == fid and c['role'] == role and c['target_association'] == 'SUPPORTED' for c in cites)
    def state_record(state, context):
        if state is None:
            return
        if state['frame_id'] is not None:
            frame_time(state['frame_id'], state['source_timestamp_s'], context)
            need(supported_at(state['evidence'], state['frame_id']), context + ': missing supported STATE at asserted frame')
        if state['state'] == 'OTHER_OBSERVED':
            need(nonblank(state['description']), context + ': OTHER description')
    def exact_utc(value, context):
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            need(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, context + ': not UTC')
            return parsed
        except (ValueError, TypeError):
            need(False, context + ': invalid UTC date')
            return None
    # Reject blank human declarations even when JSON Schema minLength passes whitespace.
    for field in ('reviewer_id', 'human_rationale', 'target_identification_event_dependence_rationale'):
        need(nonblank(response[field]), field + ': blank')
    need(nonblank(response['uncertainty']['description']), 'Uncertainty description blank')
    need(response['annotation_item_id'] == item['annotation_item_id'], 'Item ID mismatch')
    need(response['target_reference'] == {'selected_local_candidate_id': selected, 'stratum': item['stratum']},
         'Target/stratum mismatch')
    provenance = response['provenance']
    for field, expected in {
        'policy_md_sha256': receipt['policy_md_sha256'], 'policy_json_sha256': receipt['policy_json_sha256'],
        'schema_sha256': receipt['schema_sha256'], 'review_item_sha256': item_sha,
        'source_video_sha256': item['source_video_sha256'],
        'authorized_visual_manifest_sha256': item['authorized_visual_manifest_sha256'],
        'phase1c_response_sha256': backend['phase1c_response_sha256'],
        'seed_provenance_scope': item['seed_provenance_scope'], 'original_pack_ids': item['original_pack_ids'],
        'binding_causality_status': item['binding_causality_status']}.items():
        need(provenance[field] == expected, 'Provenance mismatch: ' + field)
    saved_time = exact_utc(provenance['automatic_timestamp_utc'], 'Submission')
    try:
        need(str(UUID(provenance['submission_id'])) == provenance['submission_id'].lower(), 'Invalid UUID')
    except ValueError:
        need(False, 'Invalid UUID')
    same = None if backend['phase1c_reviewer_id'] is None else response['reviewer_id'] == backend['phase1c_reviewer_id']
    need(response['same_reviewer_as_phase1c'] is same, 'Reviewer linkage mismatch')
    if response['review_round'] == 2:
        need(item['annotation_item_id'] in repeat_ids, 'Not in frozen repeat subset')
        need(round1 is not None and response['relabel_of'] == round1['sha256'], 'Invalid round-1 linkage')
        if round1:
            first_time = exact_utc(round1['timestamp'], 'Round 1')
            if saved_time and first_time:
                need(saved_time >= first_time, 'Round 2 predates round 1')
                if (saved_time - first_time).total_seconds() < 7 * 86400:
                    warnings.append('REPEAT_DELAY_SHORTER_THAN_7_DAYS')
    metadata = response['interaction_metadata']
    reference_ids = {r['reference_id'] for r in item['visual']['references']}
    need(set(metadata['references_opened']) <= reference_ids, 'Unapproved reference opened')
    for toggle in metadata['overlay_toggles']:
        exact_utc(toggle['timestamp_utc'], 'Overlay log')
    citations = list(_all_citations(response))
    for index, cite in enumerate(citations):
        citation(cite, f'Citation {index}')
    # Duplicate citations within each evidence array are prohibited; reuse across separate assertions is allowed.
    def unique(cites, context):
        try:
            keys = [object_sha(c) for c in cites]
        except ValueError:
            need(False, context + ': nonfinite evidence value')
            return
        need(len(keys) == len(set(keys)), context + ': duplicate citations')
    for label in ('coverage_citations', 'last_confirmed_state_evidence', 'subsequent_location_evidence'):
        unique(response[label], label)
    coverage_ids = response['observation_coverage_frame_ids']
    need(set(coverage_ids) == {c['frame_id'] for c in response['coverage_citations']}, 'Coverage IDs/citations mismatch')
    strict_coverage = (response['window_outcome'] == 'NO_CONFIRMED_EVENT' or
                       response.get('event_list_exhaustiveness') == 'EXHAUSTIVE_ATTESTED')
    if strict_coverage:
        need(response['coverage_assessment'] == 'THROUGHOUT_ASSESSABLE', 'Unobservable gap blocks exhaustive/negative claim')
        need(frames[0]['frame_id'] in coverage_ids and frames[-1]['frame_id'] in coverage_ids,
             'Coverage requires first and last authorized frames')
        need(any(len(frames) // 3 <= positions.get(fid, -1) < math.ceil(2 * len(frames) / 3)
                 for fid in coverage_ids), 'Coverage requires middle-third frame')
        need(all(c['target_association'] == 'SUPPORTED' for c in response['coverage_citations']),
             'Coverage target association unsupported')
        need(response['visibility_at_window_end']['visibility'] in ('VISIBLE', 'PARTIALLY_OCCLUDED'),
             'Coverage claims assessable visible target at end but end visibility contradicts it')
    elif response['window_outcome'] == 'CONFIRMED_EVENTS':
        need(response['uncertainty']['status'] != 'NO_ADDITIONAL_UNCERTAINTY', 'Non-exhaustive list needs explicit uncertainty')
    event_ids, event_keys = [], []
    for event in response['events']:
        event_ids.append(event['event_id'])
        need(event['annotation_item_id'] == item['annotation_item_id']
             and event['local_candidate_reference'] == selected, 'Event target mismatch')
        need(nonblank(event['human_rationale']) and nonblank(event['uncertainty']['description']), 'Event rationale/uncertainty blank')
        unique(event['evidence'], event['event_id'])
        time = event['event_time']
        sf, ef = time['start_frame_id'], time['end_frame_id']
        start, end = time['start_timestamp_s'], time['end_timestamp_s']
        frame_time(sf, start, 'Event start'); frame_time(ef, end, 'Event end')
        event_keys.append((start, end, event['event_id']))
        before = [c['source_timestamp_s'] for c in event['evidence'] if c['role'] == 'BEFORE']
        after = [c['source_timestamp_s'] for c in event['evidence'] if c['role'] == 'AFTER']
        latest_before, earliest_after = max(before), min(after)
        need(latest_before < earliest_after, 'BEFORE/AFTER must be strictly ordered')
        if time['status'] == 'EXACT_OBSERVED_TRANSITION':
            need(sf == ef and start == end and latest_before < start < earliest_after,
                 'Exact transition needs equal frame/time and strict before/after')
            need(any(c['role'] == 'TRANSITION' and c['frame_id'] == sf and abs(c['source_timestamp_s'] - start) <= 1e-6
                     for c in event['evidence']), 'Exact transition missing cited transition')
        else:
            need(start == latest_before and end == earliest_after and start < end,
                 'Bounded/uncertain endpoints must be latest BEFORE and earliest AFTER')
            need(any(c['role'] == 'BEFORE' and c['frame_id'] == sf for c in event['evidence'])
                 and any(c['role'] == 'AFTER' and c['frame_id'] == ef for c in event['evidence']), 'Bracket endpoint frame mismatch')
            if time['status'] == 'TIMING_UNCERTAIN':
                need(event['uncertainty']['status'] == 'TIMING_UNCERTAIN', 'Timing status needs explicit timing uncertainty')
        for cite in event['evidence']:
            if cite['role'] == 'TRANSITION':
                need(start <= cite['source_timestamp_s'] <= end, 'Transition outside bracket')
        state_record(event['before_state'], 'Before state'); state_record(event['after_state'], 'After state')
        for state, before_flag in ((event['before_state'], True), (event['after_state'], False)):
            if state and state['frame_id'] is not None:
                need(state['source_timestamp_s'] <= latest_before if before_flag else state['source_timestamp_s'] >= earliest_after,
                     'Before/after STATE chronology mismatch')
                forbidden = ('HELD_BY_PERSON' if before_flag else 'ON_SURFACE') if event['event_type'] == 'PICKUP' else ('ON_SURFACE' if before_flag else 'HELD_BY_PERSON')
                need(state['state'] != forbidden, 'Contrary physical state for transition')
    need(len(event_ids) == len(set(event_ids)), 'Duplicate event IDs')
    need(event_keys == sorted(event_keys), 'Events not in chronological order')
    signatures = [(e['event_type'], e['event_time']['start_frame_id'], e['event_time']['end_frame_id']) for e in response['events']]
    need(len(signatures) == len(set(signatures)), 'Duplicate physical event')
    for i, first in enumerate(response['events']):
        a = first['event_time']
        for second in response['events'][i + 1:]:
            b = second['event_time']
            exact_a, exact_b = a['status'] == 'EXACT_OBSERVED_TRANSITION', b['status'] == 'EXACT_OBSERVED_TRANSITION'
            if exact_a and exact_b and a['start_timestamp_s'] == b['start_timestamp_s']:
                need(first['event_type'] == second['event_type'], 'Opposite exact events at same instant')
            elif (max(a['start_timestamp_s'], b['start_timestamp_s']) < min(a['end_timestamp_s'], b['end_timestamp_s'])
                  or exact_a and b['start_timestamp_s'] < a['start_timestamp_s'] < b['end_timestamp_s']
                  or exact_b and a['start_timestamp_s'] < b['start_timestamp_s'] < a['end_timestamp_s']):
                need(first['chronology_uncertainty'] and second['chronology_uncertainty'], 'Overlapping brackets require chronology uncertainty')
                warnings.append('OVERLAPPING_UNCERTAIN_EVENT_BRACKETS')
    last = response['last_confirmed_frame_id']
    if last is not None:
        frame_time(last, response['last_confirmed_timestamp'], 'Last confirmation')
        need(supported_at(response['last_confirmed_state_evidence'], last), 'Last confirmation needs supported same-frame STATE')
    for event in response['events']:
        for state in (event['before_state'], event['after_state']):
            if state and state['state'] != 'STATE_UNKNOWN':
                need(last is not None and response['last_confirmed_timestamp'] is not None
                     and state['source_timestamp_s'] <= response['last_confirmed_timestamp'],
                     'Later directly supported known state contradicts the last-confirmed assertion')
    if response['last_confirmed_state'] == 'OTHER_OBSERVED':
        need(nonblank(response['last_confirmed_state_description']), 'Last OTHER description missing')
    for fid in response['location_evidence_frame_ids']:
        need(fid in table and supported_at(response['last_confirmed_state_evidence'], fid), 'Location evidence unsupported')
    if response['last_confirmed_location_description'] or response['location_marker']:
        need(last in response['location_evidence_frame_ids'], 'Location missing last-confirmed frame')
    marker = response['location_marker']
    if marker:
        need(marker['frame_id'] == last, 'Marker frame differs from last confirmation')
        coords = marker['coordinates']; width, height = item['visual']['width'], item['visual']['height']
        need(all(finite(v) for v in coords), 'Marker nonfinite')
        if marker['kind'] == 'POINT':
            need(0 <= coords[0] < width and 0 <= coords[1] < height, 'POINT out of bounds')
        else:
            x1, y1, x2, y2 = coords
            need(0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height, 'BBOX geometry invalid')
    visibility = response['visibility_at_window_end']
    need(visibility['frame_id'] == frames[-1]['frame_id'], 'Visibility assessment must use last authorized native frame')
    frame_time(visibility['frame_id'], visibility['source_timestamp_s'], 'End visibility')
    if visibility['visibility'] in ('VISIBLE', 'PARTIALLY_OCCLUDED'):
        need(any(c['frame_id'] == frames[-1]['frame_id'] and c['target_association'] == 'SUPPORTED'
                 for c in visibility['evidence']), 'Visible end needs supported same-frame evidence')
    elif visibility['visibility'] == 'NOT_VISIBLE':
        need(any(c['frame_id'] == frames[-1]['frame_id'] for c in visibility['evidence']), 'Not-visible end missing assessment citation')
        if visibility['observed_reason'] != 'REASON_UNKNOWN':
            need(any(c['source_timestamp_s'] <= visibility['source_timestamp_s'] and c['target_association'] == 'SUPPORTED'
                     and nonblank(c['visual_description']) for c in visibility['evidence']), 'Positive exit/occlusion reason requires direct written visual evidence')
    if response['window_outcome'] == 'TARGET_NOT_OBSERVABLE':
        need(not any(c['target_association'] == 'SUPPORTED' for c in citations), 'Supported visible target contradicts TARGET_NOT_OBSERVABLE')
        need(last is None and response['last_confirmed_state'] == 'STATE_UNKNOWN', 'Not-observable target cannot have confirmed state')
    if response['subsequent_location'] == 'OBSERVED_IN_WINDOW':
        need(last is not None, 'Subsequent location requires prior confirmation')
        ids = response['subsequent_location_evidence_frame_ids']
        need(set(ids) == {c['frame_id'] for c in response['subsequent_location_evidence']}, 'Subsequent IDs/evidence mismatch')
        for cite in response['subsequent_location_evidence']:
            need(cite['target_association'] == 'SUPPORTED' and last is not None
                 and cite['source_timestamp_s'] > response['last_confirmed_timestamp'], 'Subsequent location must be directly supported strictly later')
    unmodeled_ids = []
    for entry in response['unmodeled_observations']:
        unmodeled_ids.append(entry['observation_id'])
        need(set(entry['evidence_frame_ids']) == {c['frame_id'] for c in entry['evidence']}, 'Unmodeled IDs/evidence mismatch')
        need(nonblank(entry['description']), 'Unmodeled description blank')
    need(len(unmodeled_ids) == len(set(unmodeled_ids)), 'Duplicate unmodeled IDs')
    exclusions = [key for key, value in response['attestations'].items() if key != 'human_attestation' and value]
    if not item['dev_eligible']:
        exclusions.append('ORIGINALLY_INELIGIBLE')
    return {'valid': not errors, 'errors': errors, 'error_details': error_details(errors),
            'exclusions': exclusions, 'warnings': sorted(set(warnings))}


def evaluation_metadata(response, result):
    confirmed = response['window_outcome'] == 'CONFIRMED_EVENTS'
    value = response.get('event_list_exhaustiveness')
    basis = ('STRICT_NO_CONFIRMED_EVENT' if response['window_outcome'] == 'NO_CONFIRMED_EVENT' else
             'EXHAUSTIVE_ATTESTED' if confirmed and value == 'EXHAUSTIVE_ATTESTED' else
             'NON_EXHAUSTIVE' if confirmed and value == 'NOT_ATTESTED' else
             'UNKNOWN' if confirmed else 'NOT_APPLICABLE')
    reasons = list(result['exclusions'])
    if not result['valid']:
        reasons.append('INVALID_RESPONSE')
    if basis not in ('STRICT_NO_CONFIRMED_EVENT', 'EXHAUSTIVE_ATTESTED'):
        reasons.append('FULL_WINDOW_COMPLETENESS_UNSUPPORTED')
    supported = not reasons
    primary = supported and response['target_identification_event_dependence'] == 'NOT_DEPENDENT'
    if response['target_identification_event_dependence'] != 'NOT_DEPENDENT':
        reasons.append('DEPENDENCE_SENSITIVITY_ONLY')
    data = {'completeness_basis': basis, 'full_window_event_evaluation_supported': supported,
            'primary_full_window_metrics_eligible': primary, 'event_evaluation_exclusion_reasons': reasons,
            'supported_event_exploratory_use_allowed': confirmed and result['valid'] and not result['exclusions'],
            'unlisted_events_status': 'UNEVALUATED' if basis in ('NON_EXHAUSTIVE', 'UNKNOWN', 'NOT_APPLICABLE') else 'FUTURE_SCORING_TBD',
            'formal_eligible': False, 'binding_causality_status': 'CAUSALITY_UNVERIFIED'}
    if confirmed:
        data['event_list_exhaustiveness'] = value
    return data
