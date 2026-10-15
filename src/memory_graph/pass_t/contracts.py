"""Strict schemas and semantic validation for local temporal observations."""
from copy import deepcopy
import math
import re

ACTIONS = ['PICK_UP', 'MOVE_WHILE_HELD', 'PLACE', 'RELEASE', 'HANDOFF']
TRANSITIONS = ACTIONS + ['FINAL_STATE']
ASSESSMENTS = ['CONFIRMED_NONE', 'INDETERMINATE', 'EVENTS_OBSERVED', 'PARTIALLY_OBSERVED']
REASONS = ['OCCLUDED', 'OUT_OF_VIEW', 'TOO_SMALL', 'SAMPLING_MISSED', 'MOTION_BLUR',
           'VIEW_MISMATCH', 'WINDOW_BOUNDARY', 'OTHER']
VISIBILITY = ['VISIBLE', 'OCCLUDED', 'OUT_OF_VIEW', 'UNKNOWN']
PREDICATES = ['ON', 'IN', 'NEAR', 'LEFT_OF', 'RIGHT_OF', 'BEHIND', 'HELD_BY', 'UNKNOWN']
SPATIAL = PREDICATES[:6]


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required, 'additionalProperties': False}


def enum(values):
    return {'enum': values}


def array(items, minimum=0):
    return {'type': 'array', 'items': items, 'minItems': minimum}


STRING = {'type': 'string', 'minLength': 1}
NULL_STRING = {'type': ['string', 'null'], 'minLength': 1}
NUMBER = {'type': 'number'}
REFS = {**array(STRING), 'uniqueItems': True}
INTERVAL = {'anyOf': [{'type': 'array', 'items': NUMBER, 'minItems': 2, 'maxItems': 2}, {'type': 'null'}]}
OBS = obj({'support_class': enum(['DIRECT', 'INFERABLE', 'UNSUPPORTED']),
           'unobservable_reason': enum(REASONS + [None])})
OBS_MAP = {'type': 'object', 'minProperties': 1,
           'patternProperties': {'^SM_[0-9a-f]{12}$': OBS}, 'additionalProperties': False}
RELATION = obj({'predicate': enum(PREDICATES), 'anchor_local_id': NULL_STRING,
                'anchor_label': NULL_STRING,
                'reference_frame': enum(['IMAGE_2D', 'PHYSICAL_SCENE', 'UNKNOWN']),
                'evidence_frame_ids': REFS})


def with_observability(properties):
    return {**properties, 'observable_in_full_window': {'type': 'boolean'},
            'sampled_observability': OBS_MAP, 'unobservable_reason': enum(REASONS + [None])}


STATE_FIELDS = {'confirmation_status': enum(['CONFIRMED', 'NEVER_CONFIRMED']),
                'confirmed_at_s': {'type': ['number', 'null']}, 'evidence_frame_ids': REFS,
                'holder_status': enum(['HELD_BY_PERSON', 'NOT_HELD', 'UNKNOWN']),
                'holder_local_id': NULL_STRING, 'relation': RELATION}
EVENT_FIELDS = {'action': enum(ACTIONS), 'actor_local_id': NULL_STRING,
                'receiver_local_id': NULL_STRING, 'target_local_id': STRING,
                'evidence_frame_ids': REFS, 'onset_interval_s': INTERVAL,
                'offset_interval_s': INTERVAL,
                'boundary_status': enum(['BRACKETED', 'ONE_SIDED', 'UNLOCALIZABLE']),
                'boundary_reason': NULL_STRING,
                'relation': {'anyOf': [RELATION, {'type': 'null'}]}}
COMMON = {'schema_version': enum(['v1']), 'target_local_id': STRING,
          'event_assessment': enum(ASSESSMENTS),
          'unresolved_transitions': {**array(enum(TRANSITIONS)), 'uniqueItems': True},
          'current_visibility_at_window_end': enum(VISIBILITY),
          'window_end_timestamp_s': NUMBER, 'visibility_evidence_frame_ids': REFS}

PREDICTION_SCHEMA = obj({**COMMON,
    'events': array(obj({**EVENT_FIELDS, 'support_class': enum(['DIRECT', 'INFERABLE', 'UNSUPPORTED'])})),
    'last_confirmed_state': obj(STATE_FIELDS)})
GT_SCHEMA = obj({**COMMON, 'event_window_id': STRING, 'session_id': STRING,
    'window_start_s': NUMBER, 'window_end_s': NUMBER, 'target_valid': {'type': 'boolean'},
    'adequate_observable_coverage': {'type': 'boolean'},
    'reference_frames': array(obj({'frame_id': STRING, 'source_timestamp_s': NUMBER}), 1),
    'events': array(obj(with_observability(EVENT_FIELDS))),
    'last_confirmed_state': obj(with_observability(STATE_FIELDS)),
    'provenance': obj({'annotator_id': STRING, 'timestamp_utc': STRING, 'tool_version': STRING}),
    'adjudication': {'type': ['object', 'null']}})

FRAME_SCHEMA = obj({'frame_id': {'type': 'string', 'pattern': '^F[0-9]{3}$'},
    'source_frame_index': {'type': 'integer', 'minimum': 0},
    'source_timestamp_s': NUMBER, 'window_relative_timestamp_s': NUMBER,
    'image_path': {'type': 'string', 'pattern': '^frames/F[0-9]{3}\\.png$'},
    'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
    'timestamp_provenance': enum(['NATIVE_PTS', 'DERIVED_FPS']),
    'overlay_policy_id': enum(['OVERLAY_NEUTRAL_V1']), 'sampling_manifest_version': enum(['v1'])})
MANIFEST_SCHEMA = obj({'schema_version': enum(['v1']), 'sampling_manifest_id': STRING,
    'event_window_id': STRING, 'session_id': STRING, 'source_video_id': STRING,
    'source_video_hash': NULL_STRING, 'target_local_id': STRING,
    'window_start_s': NUMBER, 'window_end_s': NUMBER, 'target_fps': NUMBER,
    'frames': array(FRAME_SCHEMA, 1), 'sampling': obj({'grid_count': {'type': 'integer'},
    'selected_grid_indices': array({'type': 'integer'}), 'collision_grid_indices': array({'type': 'integer'}),
    'realized_density_fps': NUMBER})})
BUNDLE_FRAME = obj({'frame_id': {'type': 'string', 'pattern': '^F[0-9]{3}$'},
    'image_path': {'type': 'string', 'pattern': '^frames/F[0-9]{3}\\.png$'},
    'timestamp_s': NUMBER, 'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}})
BUNDLE_SCHEMA = obj({'bundle_id': {'type': 'string', 'pattern': '^B_[0-9a-f]{12}$'},
    'representation_type': enum(['A', 'B', 'C']), 'schema_version': enum(['v1']),
    'sampling_manifest_id': {'type': 'string', 'pattern': '^SM_[0-9a-f]{12}$'},
    'frames': array(BUNDLE_FRAME, 1), 'target_id': enum(['T1']),
    'person_ids': {**array({'type': 'string', 'pattern': '^P[1-9][0-9]*$'}), 'uniqueItems': True},
    'allowed_anchor_ids': {**array({'type': 'string', 'pattern': '^A[1-9][0-9]*$'}), 'uniqueItems': True},
    'overlay_policy_id': enum(['OVERLAY_NEUTRAL_V1']),
    'prompt_id': enum(['pass_t_event_annotator_v1']),
    'prompt_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
    'media_path': {'enum': ['media/input.mkv', 'media/input.mp4', 'media/grid.png', None]},
    'tile_mapping': array(obj({'frame_id': STRING, 'row': {'type': 'integer', 'minimum': 0},
                              'column': {'type': 'integer', 'minimum': 0}, 'timestamp_s': NUMBER}))})


def schema_errors(value, schema):
    from jsonschema import Draft202012Validator
    return [f'{list(e.absolute_path)}: {e.message}' for e in Draft202012Validator(schema).iter_errors(value)]


def validate_prediction(value, bundle, start, end, human=False):
    errors = schema_errors(value, GT_SCHEMA if human else PREDICTION_SCHEMA)
    if errors:
        return errors
    if not start < end:
        return ['invalid authorization bounds']
    def forbidden_fields(x):
        if isinstance(x,dict):
            for key,v in x.items():
                if re.search(r'global.*alias|identity.*merge|graph.*write|trusted.*graph|physical.*identity',key,re.I):
                    errors.append('forbidden identity/graph authority field')
                forbidden_fields(v)
        elif isinstance(x,list):
            for v in x:forbidden_fields(v)
        elif isinstance(x,float) and not math.isfinite(x):errors.append('non-finite numeric field')
    forbidden_fields(value)
    frame_times = ({x['frame_id']: x['source_timestamp_s'] for x in value['reference_frames']}
                   if human else {x['frame_id']: x['timestamp_s'] for x in bundle['frames']})
    persons = set(bundle['person_ids']); anchors = set(bundle['allowed_anchor_ids'])
    if any(not start <= t < end for t in frame_times.values()):
        errors.append('reference outside authorized half-open window')
    if value['target_local_id'] != bundle['target_id']:
        errors.append('target outside allowed set')
    if abs(value['window_end_timestamp_s'] - end) > .001:
        errors.append('window-end timestamp mismatch')
    events = value['events']; assessment = value['event_assessment']; unresolved = value['unresolved_transitions']
    if bool(events) != (assessment in {'EVENTS_OBSERVED', 'PARTIALLY_OBSERVED'}):
        errors.append('event list / assessment mismatch')
    if bool(unresolved) != (assessment in {'INDETERMINATE', 'PARTIALLY_OBSERVED'}):
        errors.append('unresolved transitions / assessment mismatch')

    def refs(xs, required=False):
        if required and not xs:
            errors.append('assertion without evidence')
        if not set(xs) <= set(frame_times):
            errors.append('invalid evidence frame reference')

    def person(x, required=False):
        if required and x in {None, 'UNKNOWN'}:
            errors.append('required actor unavailable')
        if x not in persons | {None, 'UNKNOWN'}:
            errors.append('person outside allowed set')

    def relation(x, required=False):
        if x is None:
            if required: errors.append('relation missing')
            return
        a=x['anchor_local_id']; pred=x['predicate']; refs(x['evidence_frame_ids'], pred!='UNKNOWN')
        allowed = persons if pred=='HELD_BY' else anchors
        if a is not None and a not in allowed: errors.append('anchor outside allowed set')
        if pred in SPATIAL and a is None and not x['anchor_label']:
            errors.append('spatial relation requires observed anchor or short descriptive anchor')
        if x['anchor_label'] and len(x['anchor_label'])>120:
            errors.append('anchor description too long')
        if pred=='UNKNOWN' and (a is not None or x['anchor_label'] is not None or x['reference_frame']!='UNKNOWN'):
            errors.append('UNKNOWN relation has definite fields')

    def observability(x):
        for sm,o in x['sampled_observability'].items():
            if o['unobservable_reason']=='SAMPLING_MISSED' and (
                not x['observable_in_full_window'] or o['support_class']=='DIRECT'):
                errors.append('invalid SAMPLING_MISSED semantics')
            if o['support_class']=='DIRECT' and (not x['observable_in_full_window'] or o['unobservable_reason'] is not None):
                errors.append('DIRECT observability inconsistent')
            if o['support_class']=='UNSUPPORTED' and o['unobservable_reason'] is None:
                errors.append('UNSUPPORTED requires limitation reason')
        if bundle['sampling_manifest_id'] not in x['sampled_observability']:
            errors.append('missing manifest-specific observability')

    refs(value['visibility_evidence_frame_ids'], value['current_visibility_at_window_end']!='UNKNOWN')
    state=value['last_confirmed_state']; refs(state['evidence_frame_ids'],state['confirmation_status']=='CONFIRMED')
    relation(state['relation']); h=state['holder_status']; hid=state['holder_local_id']; person(hid)
    if state['confirmation_status']=='NEVER_CONFIRMED':
        if state['confirmed_at_s'] is not None or state['evidence_frame_ids'] or h!='UNKNOWN' or hid is not None or state['relation']!={'predicate':'UNKNOWN','anchor_local_id':None,'anchor_label':None,'reference_frame':'UNKNOWN','evidence_frame_ids':[]}:
            errors.append('NEVER_CONFIRMED requires all state fields empty/UNKNOWN')
    elif state['confirmed_at_s'] is None or not start <= state['confirmed_at_s'] < end:
        errors.append('confirmed state time outside window')
    elif any(frame_times.get(f,math.inf)>state['confirmed_at_s']+.001 for f in state['evidence_frame_ids']+state['relation']['evidence_frame_ids']):
        errors.append('last confirmed state relies on later evidence')
    if h=='HELD_BY_PERSON' and (hid not in persons or state['relation']['predicate']!='HELD_BY' or state['relation']['anchor_local_id']!=hid):
        errors.append('held status / holder / relation contradiction')
    if h=='NOT_HELD' and (hid is not None or state['relation']['predicate']=='HELD_BY'):
        errors.append('NOT_HELD contradiction')
    if h=='UNKNOWN' and (hid is not None or state['relation']['predicate']=='HELD_BY'):
        errors.append('UNKNOWN holder cannot assert holding')
    if human:
        if value['window_start_s']!=start or value['window_end_s']!=end:
            errors.append('GT authorization bounds mismatch')
        if not value['target_valid']: errors.append('invalid local target: exclude window')
        if assessment=='CONFIRMED_NONE' and not value['adequate_observable_coverage']:
            errors.append('CONFIRMED_NONE requires adequate coverage; review as INDETERMINATE')
        observability(state)
    previous=None
    for e in events:
        if e['target_local_id']!=bundle['target_id']: errors.append('event target outside allowed set')
        refs(e['evidence_frame_ids'],True);person(e['actor_local_id']); person(e['receiver_local_id'])
        if e['action']=='HANDOFF':
            person(e['actor_local_id'],True);person(e['receiver_local_id'],True)
            if e['actor_local_id']==e['receiver_local_id']: errors.append('HANDOFF actors must differ')
        elif e['receiver_local_id'] is not None: errors.append('receiver only allowed on HANDOFF')
        on=e['onset_interval_s']; off=e['offset_interval_s']; status=e['boundary_status']
        for interval in [on,off]:
            if interval and (interval[0]>interval[1] or interval[0]<start or interval[1]>end):
                errors.append('invalid temporal bracket')
        if status=='BRACKETED' and (on is None or off is None or e['boundary_reason'] is not None): errors.append('BRACKETED needs both bounds')
        if status=='ONE_SIDED' and ((on is None)==(off is None) or not e['boundary_reason']): errors.append('ONE_SIDED needs one bound and reason')
        if status=='UNLOCALIZABLE' and (on is not None or off is not None or not e['boundary_reason']): errors.append('UNLOCALIZABLE requires null bounds/reason')
        if on and off and (on[0]>off[0] or on[1]>off[1]): errors.append('onset after offset')
        if on and previous is not None and on[0]<previous: errors.append('events not chronologically ordered')
        if on: previous=on[0]
        relation(e['relation'],e['action']=='PLACE')
        if e['action']=='PLACE' and e['relation'] and e['relation']['predicate'] not in {'ON','IN'}:
            errors.append('PLACE requires supported destination ON/IN, not proximity')
        if human: observability(e)
        elif e['support_class']=='UNSUPPORTED': errors.append('unsupported action cannot be asserted')
    compatible={frozenset(x) for x in [('PICK_UP','MOVE_WHILE_HELD'),('HANDOFF','MOVE_WHILE_HELD'),('PLACE','RELEASE')]}
    for i,a in enumerate(events):
        for b in events[i+1:]:
            if a['onset_interval_s'] and a['offset_interval_s'] and b['onset_interval_s'] and b['offset_interval_s']:
                # Reject definite overlaps, not merely overlapping uncertainty brackets.
                if max(a['onset_interval_s'][1],b['onset_interval_s'][1]) < min(a['offset_interval_s'][0],b['offset_interval_s'][0]) and frozenset([a['action'],b['action']]) not in compatible:
                    errors.append('physically incompatible event overlap')
    return errors


def directly_observable(record, manifest_id):
    return record['sampled_observability'][manifest_id]['support_class']=='DIRECT'


def unknown_state():
    return {'confirmation_status':'NEVER_CONFIRMED','confirmed_at_s':None,'evidence_frame_ids':[],
            'holder_status':'UNKNOWN','holder_local_id':None,
            'relation':{'predicate':'UNKNOWN','anchor_local_id':None,'anchor_label':None,
                        'reference_frame':'UNKNOWN','evidence_frame_ids':[]}}


def baseline(bundle, end, abstain=True):
    return {'schema_version':'v1','target_local_id':bundle['target_id'],
            'event_assessment':'INDETERMINATE' if abstain else 'CONFIRMED_NONE','events':[],
            'unresolved_transitions':deepcopy(TRANSITIONS) if abstain else [],
            'last_confirmed_state':unknown_state(),'current_visibility_at_window_end':'UNKNOWN',
            'window_end_timestamp_s':end,'visibility_evidence_frame_ids':[]}
