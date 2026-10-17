"""Offline annotation contract. Standard library only; never supplies human labels."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/findmind-gt-annotator'
STATES = ['ON_SURFACE', 'HELD_BY_PERSON', 'OTHER', 'UNKNOWN']
VISIBILITY = ['VISIBLE', 'PARTIALLY_OCCLUDED', 'NOT_VISIBLE', 'UNCERTAIN']
CERTAINTY = ['CONFIRMED', 'UNCERTAIN', 'INSUFFICIENT']
IDENTITY = ['CERTAIN', 'UNCERTAIN', 'UNKNOWN']
EVENTS = ['PICKUP', 'PLACEMENT', 'CONTACT_ONLY', 'CAMERA_MOTION_ONLY', 'OCCLUSION_INSUFFICIENT_EVIDENCE', 'OTHER']
REVIEW = ['NOT_STARTED', 'IN_PROGRESS', 'PARTIALLY_REVIEWED', 'COMPLETE_WITH_LIMITATIONS', 'EXHAUSTIVELY_REVIEWED']
ATTESTATIONS = ['entire_timeline_reviewed', 'all_pickup_placement_annotated', 'all_uncertainty_recorded', 'identity_not_guessed', 'no_unobservable_gap', 'target_association_resolved']

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode('utf8')).hexdigest()

def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()

def load_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('Non-finite JSON: ' + s)))

def annotation_schema():
    text = lambda n=2048: {'type': 'string', 'maxLength': n}
    nonempty = lambda n=160: {'type': 'string', 'minLength': 1, 'maxLength': n, 'pattern': r'\S'}
    number = {'type': 'number', 'minimum': 0}
    enum = lambda values: {'type': 'string', 'enum': values}
    array = lambda item, maximum=20000: {'type': 'array', 'items': item, 'maxItems': maximum}
    obj = lambda fields: {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}
    ref = lambda name: {'$ref': '#/definitions/' + name}
    boolean = {'type': 'boolean'}
    date = {'type': 'string', 'minLength': 20, 'maxLength': 40, 'pattern': r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|\+00:00)$'}
    sha = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
    definitions = {
        'interval': obj({'interval_id': nonempty(), 'start_s': number, 'end_s': number, 'notes': text(6000)}),
        'uncertainty': obj({'uncertainty_id': nonempty(), 'start_s': number, 'end_s': number, 'reason': nonempty(6000), 'could_conceal_event': boolean, 'identity_uncertain': boolean}),
        'event': obj({'event_id': nonempty(), 'type': enum(EVENTS), 'object_category': nonempty(), 'local_instance_id': nonempty(),
                      'start_s': number, 'end_s': number, 'before_state': enum(STATES), 'after_state': enum(STATES),
                      'before_visibility': enum(VISIBILITY), 'after_visibility': enum(VISIBILITY),
                      'before_evidence_times_s': array(number, 100), 'after_evidence_times_s': array(number, 100),
                      'target_identity_certainty': enum(IDENTITY), 'evidence_certainty': enum(CERTAINTY),
                      'visibility_limitations': text(6000), 'notes': text(6000), 'updated_at': date}),
        'state': obj({'state_id': nonempty(), 'object_category': nonempty(), 'local_instance_id': nonempty(),
                      'source_time_s': number, 'source_frame_index': {'type': ['integer', 'null'], 'minimum': 0},
                      'nearest_source_frame_index': {'type': ['integer', 'null'], 'minimum': 0},
                      'timing_precision': {'const': 'HTML5_TIMESTAMP_APPROXIMATE'}, 'physical_state': enum(STATES),
                      'visibility': enum(VISIBILITY), 'evidence_certainty': enum(CERTAINTY),
                      'target_identity_certainty': enum(IDENTITY), 'notes': text(6000), 'updated_at': date}),
        'attestations': obj({name: boolean for name in ATTESTATIONS}),
    }
    definitions['video'] = obj({'video_id': nonempty(), 'source_sha256': sha, 'source_duration_s': number,
        'assigned': boolean, 'review_status': enum(REVIEW), 'reviewed_intervals': array(ref('interval'), 5000),
        'events': array(ref('event'), 5000), 'states': array(ref('state')), 'uncertain_intervals': array(ref('uncertainty'), 5000),
        'coverage_attestations': ref('attestations'), 'event_list_exhaustiveness': enum(['EXHAUSTIVE_ATTESTED', 'NOT_ATTESTED', 'UNKNOWN']), 'notes': text(10000)})
    schema = obj({'schema_version': {'const': '1.0'}, 'dataset_id': nonempty(), 'dataset_version': nonempty(),
        'dataset_manifest_sha256': sha, 'reviewer_id': nonempty(64), 'session_id': nonempty(), 'assignment': text(),
        'created_at': date, 'updated_at': date, 'exported_at': date, 'export_kind': enum(['BACKUP', 'FINAL']),
        'videos': {'type': 'array', 'items': ref('video'), 'minItems': 9, 'maxItems': 9}})
    schema.update({'$schema': 'http://json-schema.org/draft-07/schema#', 'title': 'FindMind offline human annotation v1.0', 'definitions': definitions})
    return schema

def structural_errors(value, schema=None):
    """The small shared schema subset also implemented by contract.js."""
    import re
    schema = schema or annotation_schema()
    errors = []
    def visit(x, rule, path):
        if '$ref' in rule:
            rule = schema['definitions'][rule['$ref'].split('/')[-1]]
        types = rule.get('type', [])
        types = [types] if isinstance(types, str) else types
        def is_type(t):
            return {'object': isinstance(x, dict), 'array': isinstance(x, list), 'string': isinstance(x, str),
                    'boolean': isinstance(x, bool), 'null': x is None,
                    'number': isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x),
                    'integer': isinstance(x, (int,float)) and not isinstance(x, bool) and math.isfinite(x) and x == int(x)}.get(t, False)
        if types and not any(is_type(t) for t in types):
            errors.append(path + ': wrong type'); return
        if 'const' in rule and x != rule['const']: errors.append(path + ': unexpected constant')
        if 'enum' in rule and x not in rule['enum']: errors.append(path + ': unexpected value')
        if isinstance(x, dict):
            for key in rule.get('required', []):
                if key not in x: errors.append(path + '/' + key + ': required')
            for key, item in x.items():
                if key not in rule.get('properties', {}):
                    if rule.get('additionalProperties') is False: errors.append(path + '/' + key + ': unexpected field')
                else: visit(item, rule['properties'][key], path + '/' + key)
        if isinstance(x, list):
            if not rule.get('minItems', 0) <= len(x) <= rule.get('maxItems', float('inf')): errors.append(path + ': array size')
            for i, item in enumerate(x): visit(item, rule.get('items', {}), path + '/' + str(i))
        if isinstance(x, str):
            if not rule.get('minLength', 0) <= len(x) <= rule.get('maxLength', float('inf')): errors.append(path + ': string size')
            if 'pattern' in rule and not re.search(rule['pattern'], x): errors.append(path + ': pattern')
        if isinstance(x, (int, float)) and not isinstance(x, bool) and x < rule.get('minimum', -math.inf): errors.append(path + ': below minimum')
    visit(value, schema, '$')
    return errors

def covers_full(intervals, duration):
    end = 0.0
    for item in sorted(intervals, key=lambda x: x['start_s']):
        if item['start_s'] > end + 1e-6: return False
        end = max(end, item['end_s'])
    return end >= duration - 1e-6

def exhaustiveness(video):
    if video['review_status'] == 'NOT_STARTED': return 'UNKNOWN'
    full = video['review_status'] == 'EXHAUSTIVELY_REVIEWED' and all(video['coverage_attestations'].values()) and covers_full(video['reviewed_intervals'], video['source_duration_s'])
    hidden = any(u['could_conceal_event'] or u['identity_uncertain'] for u in video['uncertain_intervals'])
    unresolved = any(e['type'] in ('PICKUP', 'PLACEMENT') and (e['evidence_certainty'] != 'CONFIRMED' or e['target_identity_certainty'] != 'CERTAIN' or e['local_instance_id'].strip().upper() == 'UNKNOWN') for e in video['events'])
    return 'EXHAUSTIVE_ATTESTED' if full and not hidden and not unresolved else 'NOT_ATTESTED'

def validate_bundle(bundle, manifest):
    errors = structural_errors(bundle)
    if errors: return errors
    for name in ('dataset_id', 'dataset_version', 'dataset_manifest_sha256'):
        if bundle[name] != manifest[name]: errors.append('Dataset mismatch: ' + name)
    expected = {v['video_id']: v for v in manifest['videos']}
    seen_videos, seen_ids = set(), set()
    for v in bundle['videos']:
        vid = v['video_id']
        if vid in seen_videos: errors.append('Duplicate video: ' + vid)
        seen_videos.add(vid)
        if vid not in expected: errors.append('Unknown video: ' + vid); continue
        meta, duration = expected[vid], expected[vid]['source_duration_s']
        if v['source_sha256'] != meta['source_sha256'] or abs(v['source_duration_s'] - duration) > 1e-8: errors.append(vid + ': source identity/duration mismatch')
        def time(t):
            if not 0 <= t <= duration + 1e-8: errors.append(vid + ': time outside source duration')
        for key, id_key in [('events','event_id'), ('states','state_id'), ('reviewed_intervals','interval_id'), ('uncertain_intervals','uncertainty_id')]:
            for item in v[key]:
                if item[id_key] in seen_ids: errors.append('Duplicate annotation ID: ' + item[id_key])
                seen_ids.add(item[id_key])
                if key == 'states':
                    time(item['source_time_s'])
                    if item['source_frame_index'] is not None: errors.append(vid + ': HTML5 source frame index is not verified; must be null')
                    near = item['nearest_source_frame_index']
                    if near is not None and not 0 <= near < meta['frame_count']: errors.append(vid + ': invalid nearest frame')
                    if item['evidence_certainty'] == 'CONFIRMED' and item['physical_state'] in ('ON_SURFACE','HELD_BY_PERSON') and item['visibility'] in ('NOT_VISIBLE','UNCERTAIN'): errors.append(vid + ': invisible state cannot have confirmed visible support')
                else:
                    time(item['start_s']); time(item['end_s'])
                    if item['start_s'] > item['end_s']: errors.append(vid + ': reversed interval')
                if key == 'events':
                    bf, af = item['before_evidence_times_s'], item['after_evidence_times_s']
                    for t in bf + af: time(t)
                    if bf and af and max(bf) > min(af): errors.append(vid + ': reversed evidence chronology')
                    if item['type'] in ('PICKUP','PLACEMENT') and item['evidence_certainty'] == 'CONFIRMED':
                        pair = ('ON_SURFACE','HELD_BY_PERSON') if item['type'] == 'PICKUP' else ('HELD_BY_PERSON','ON_SURFACE')
                        if (item['before_state'],item['after_state']) != pair or not bf or not af: errors.append(vid + ': confirmed event needs correct states and before/after evidence')
                        if item['before_visibility'] in ('NOT_VISIBLE','UNCERTAIN') or item['after_visibility'] in ('NOT_VISIBLE','UNCERTAIN'): errors.append(vid + ': confirmed event needs visible evidence')
        if v['review_status'] == 'EXHAUSTIVELY_REVIEWED':
            if not covers_full(v['reviewed_intervals'], duration) or not all(v['coverage_attestations'][k] for k in ATTESTATIONS[:4]): errors.append(vid + ': full review requires complete intervals and four attestations')
        if v['event_list_exhaustiveness'] != exhaustiveness(v): errors.append(vid + ': inconsistent event-list exhaustiveness')
    if seen_videos != set(expected): errors.append('Must preserve exactly the nine video records')
    return errors

def submission_fingerprint(bundle):
    return digest({k: v for k, v in bundle.items() if k not in ('exported_at', 'export_kind')})
