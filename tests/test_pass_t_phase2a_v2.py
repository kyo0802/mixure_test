"""Synthetic Stage B contracts/storage; never submit in production response directories."""
import copy
import json
from pathlib import Path
import pytest
from PIL import Image
from memory_graph.pass_t.phase2a_v2 import policy, projection, validation, storage, finalize


@pytest.fixture
def synthetic(tmp_path):
    out = tmp_path / 'SYNTHETIC_ONLY'
    out.mkdir()
    receipt = policy.verify_gate()
    policy.exclusive(out / 'stage_b/approval.json', policy.read(policy.OUT / 'stage_b/approval.json'), out)
    policy.exclusive(out / 'stage_b/protected_before.json', {}, out)
    id_ = 'PT2A_' + 'a' * 16
    frames = []
    for j in range(6):
        path = out / f'S{10+j:06d}.png'
        Image.new('RGB', (1280, 720), (j * 20, 0, 0)).save(path)
        frames.append({'frame_id': f'S{10+j:06d}', 'source_frame_index': 10+j,
                       'source_timestamp_s': 1 + j / 10, 'timestamp_provenance': 'NATIVE_PTS',
                       'image_path': str(path), 'sha256': policy.sha(path)})
    visual = {'frames': frames, 'references': [], 'width': 1280, 'height': 720,
              'coordinate_system_id': 'REVIEW_FRAME_PIXELS_V1', 'frame_to_source_transform': [[1, 0, 0], [0, 1, 0]]}
    item = {'annotation_item_id': id_, 'original_pack_ids': ['SYNTHETIC_ONLY'], 'source_video_identifier': 'synthetic',
            'source_video_sha256': 'b' * 64, 'window_start_s': 1., 'window_end_s': 1.6,
            'authorized_half_open_frames': [10, 16], 'selected_local_candidate_id': '7', 'stratum': 'HUMAN_SEEDED_DEV',
            'dev_eligible': True, 'seed_provenance_scope': 'HUMAN_VISUAL_LOCALIZATION_ONLY',
            'binding_causality_status': 'CAUSALITY_UNVERIFIED', 'overlap_group_id': 'SYNTHETIC_GROUP',
            'formal_eligible': False, 'observations': [{'candidate_id': '7', 'observation_id': 'raw:0@10',
                                                       'source_frame_index': 10, 'bbox': [1, 2, 30, 40]}],
            'visual': visual, 'authorized_visual_manifest_sha256': policy.object_sha(visual)}
    backend = {'phase1c_response_sha256': 'c' * 64, 'phase1c_reviewer_id': 'SYNTHETIC_REVIEWER'}
    ip = out / 'items' / id_ / 'item.json'
    digest = policy.exclusive(ip, item, out)
    backend_sha = policy.exclusive(out / 'private' / (id_ + '.json'), backend, out)
    entry = {'annotation_item_id': id_, 'item_path': ip.relative_to(out).as_posix(), 'item_sha256': digest,
             'stratum': item['stratum'], 'original_pack_ids': item['original_pack_ids'], 'backend_sha256': backend_sha,
             'source_video_identifier': 'synthetic', 'overlap_group_id': 'SYNTHETIC_GROUP'}
    manifest = {'items': [entry], 'repeat_subset': [id_], 'excluded': [], 'formal_eligible': 0}
    policy.exclusive(out / 'manifest.json', manifest, out)
    policy.exclusive(out / 'manifest.freeze.json', {'manifest_sha256': policy.sha(out / 'manifest.json')}, out)
    unknown = {'status': 'UNKNOWN', 'description': 'Synthetic fixture; not a real human answer.'}
    draft = {'reviewer_id': 'SYNTHETIC_REVIEWER', 'window_outcome': 'INSUFFICIENT_EVIDENCE', 'events': [],
             'unmodeled_observations': [], 'observation_coverage_frame_ids': [], 'coverage_citations': [],
             'coverage_assessment': 'UNKNOWN', 'last_confirmed_state': 'STATE_UNKNOWN',
             'last_confirmed_state_description': None, 'last_confirmed_frame_id': None, 'last_confirmed_timestamp': None,
             'last_confirmed_state_evidence': [], 'last_confirmed_location_description': None,
             'location_marker': None, 'location_evidence_frame_ids': [],
             'visibility_at_window_end': {'visibility': 'VISIBILITY_UNKNOWN', 'frame_id': 'S000015', 'source_timestamp_s': 1.5,
                                          'observed_reason': None, 'evidence': [], 'rationale': 'Synthetic unknown visibility.'},
             'unknown_or_unobserved_afterward': True, 'subsequent_location': 'UNKNOWN',
             'subsequent_location_description': None, 'subsequent_location_evidence_frame_ids': [], 'subsequent_location_evidence': [],
             'target_identification_event_dependence': 'NOT_DEPENDENT', 'target_identification_event_dependence_rationale': 'Synthetic independent localization.',
             'target_recognition_used_pre_window_reference': False, 'uncertainty': unknown, 'confidence': 'UNKNOWN',
             'human_rationale': 'Synthetic only; no event inferred from visibility loss.',
             'attestations': {key: key == 'human_attestation' for key in policy.frozen_schema()['$defs']['attestations']['properties']},
             'interaction_metadata': {'initial_overlay_mode': 'SELECTED_CANDIDATE_ONLY', 'references_opened': [],
                                      'overlay_toggles': [], 'metadata_is_advisory': True}}
    response = storage.attach_backend(draft, item, entry, backend, receipt, 1)
    return {'out': out, 'item': item, 'entry': entry, 'backend': backend, 'receipt': receipt, 'draft': draft, 'response': response}


def cite(index, role='STATE', association='SUPPORTED'):
    return {'frame_id': f'S{10+index:06d}', 'source_timestamp_s': 1+index/10, 'role': role,
            'kind': 'CANDIDATE_OBSERVATION_BACKED' if index == 0 else 'DIRECT_VISUAL_ONLY',
            'source_observation_ids': ['raw:0@10'] if index == 0 else [],
            'visual_description': 'Synthetic visible target at the center; no machine association.', 'target_association': association}


def event(item, type_='PICKUP', start=0, end=2, id_='EVT001', exact=False):
    return {'annotation_item_id': item['annotation_item_id'], 'event_id': id_, 'event_type': type_,
            'local_candidate_reference': '7', 'event_time': {'status': 'EXACT_OBSERVED_TRANSITION' if exact else 'BOUNDED_BY_BEFORE_AFTER_EVIDENCE',
               'start_frame_id': f'S{10+(start+1 if exact else start):06d}', 'end_frame_id': f'S{10+(start+1 if exact else end):06d}',
               'start_timestamp_s': 1+(start+1 if exact else start)/10, 'end_timestamp_s': 1+(start+1 if exact else end)/10},
            'evidence': [cite(start, 'BEFORE'), cite(end, 'AFTER')] + ([cite(start+1, 'TRANSITION')] if exact else []),
            'observed_actor_reference': None, 'before_state': None, 'after_state': None,
            'uncertainty': {'status': 'UNKNOWN', 'description': 'Synthetic event evidence.'}, 'confidence': 'UNKNOWN',
            'human_rationale': 'Synthetic physical transition support.', 'chronology_uncertainty': False,
            'provenance': {'annotation_origin': 'HUMAN', 'evidence_scope': 'AUTHORIZED_WINDOW_ONLY'}}


def confirmed(fixture, exhaust='NOT_ATTESTED', type_='PICKUP'):
    response = copy.deepcopy(fixture['response'])
    response.update(window_outcome='CONFIRMED_EVENTS', events=[event(fixture['item'], type_)], event_list_exhaustiveness=exhaust)
    if exhaust == 'EXHAUSTIVE_ATTESTED':
        coverage(response)
        response['event_list_exhaustiveness_attestation'] = {k: True for k in policy.frozen_schema()['$defs']['event_list_exhaustiveness_attestation']['required']}
    return response


def coverage(response):
    response['coverage_assessment'] = 'THROUGHOUT_ASSESSABLE'
    response['coverage_citations'] = [cite(i, 'COVERAGE') for i in (0, 2, 5)]
    response['observation_coverage_frame_ids'] = [c['frame_id'] for c in response['coverage_citations']]
    response['visibility_at_window_end'].update(visibility='VISIBLE', evidence=[cite(5)])


def check(fixture, value=None, **kwargs):
    return validation.validate(value or fixture['response'], fixture['item'], fixture['entry']['item_sha256'],
                               fixture['receipt'], fixture['backend'], **kwargs)


@pytest.mark.parametrize('outcome', ['INSUFFICIENT_EVIDENCE', 'TARGET_NOT_OBSERVABLE', 'NO_CONFIRMED_EVENT', 'CONFIRMED_EVENTS'])
def test_four_outcomes(synthetic, outcome):
    value = synthetic['response']; value['window_outcome'] = outcome
    if outcome == 'NO_CONFIRMED_EVENT': coverage(value)
    elif outcome == 'CONFIRMED_EVENTS': value = confirmed(synthetic)
    assert check(synthetic, value)['valid']


@pytest.mark.parametrize('type_', ['PICKUP', 'PLACEMENT'])
@pytest.mark.parametrize('exact', [False, True])
def test_event_types_and_temporal_modes(synthetic, type_, exact):
    value = confirmed(synthetic, type_=type_); value['events'] = [event(synthetic['item'], type_, exact=exact)]
    assert check(synthetic, value)['valid']


@pytest.mark.parametrize('field', policy.frozen_schema()['$defs']['event_list_exhaustiveness_attestation']['required'])
@pytest.mark.parametrize('action', ['missing', 'false'])
def test_each_exhaustiveness_statement(synthetic, field, action):
    value = confirmed(synthetic, 'EXHAUSTIVE_ATTESTED')
    if action == 'missing': del value['event_list_exhaustiveness_attestation'][field]
    else: value['event_list_exhaustiveness_attestation'][field] = False
    assert not check(synthetic, value)['valid']


@pytest.mark.parametrize('exhaust', ['EXHAUSTIVE_ATTESTED', 'NOT_ATTESTED', 'UNKNOWN'])
def test_all_completeness_values(synthetic, exhaust):
    value = confirmed(synthetic, exhaust)
    result = check(synthetic, value); assert result['valid']
    meta = validation.evaluation_metadata(value, result)
    assert meta['full_window_event_evaluation_supported'] == (exhaust == 'EXHAUSTIVE_ATTESTED')
    assert meta['formal_eligible'] is False
    if exhaust != 'EXHAUSTIVE_ATTESTED': assert meta['unlisted_events_status'] == 'UNEVALUATED'


@pytest.mark.parametrize('assessment', ['GAPS_OR_UNCERTAINTY', 'UNKNOWN'])
@pytest.mark.parametrize('negative', [False, True])
def test_hidden_event_gap_blocks_full_window_claim(synthetic, assessment, negative):
    value = confirmed(synthetic, 'EXHAUSTIVE_ATTESTED')
    if negative:
        value['window_outcome'] = 'NO_CONFIRMED_EVENT'; value['events'] = []
        del value['event_list_exhaustiveness']; del value['event_list_exhaustiveness_attestation']
    value['coverage_assessment'] = assessment
    assert not check(synthetic, value)['valid']


@pytest.mark.parametrize('index', [0, 1, 2])
def test_missing_start_middle_end_coverage(synthetic, index):
    value = confirmed(synthetic, 'EXHAUSTIVE_ATTESTED')
    del value['coverage_citations'][index]; del value['observation_coverage_frame_ids'][index]
    assert not check(synthetic, value)['valid']


def test_supported_timing_uncertainty_not_hidden_event_gap(synthetic):
    value = confirmed(synthetic, 'EXHAUSTIVE_ATTESTED')
    value['events'][0]['event_time']['status'] = 'TIMING_UNCERTAIN'
    value['events'][0]['uncertainty']['status'] = 'TIMING_UNCERTAIN'
    assert check(synthetic, value)['valid']


@pytest.mark.parametrize('outcome', ['NO_CONFIRMED_EVENT', 'INSUFFICIENT_EVIDENCE', 'TARGET_NOT_OBSERVABLE'])
@pytest.mark.parametrize('field', ['event_list_exhaustiveness', 'event_list_exhaustiveness_attestation'])
def test_other_outcomes_prohibit_completeness(synthetic, outcome, field):
    value = synthetic['response']; value['window_outcome'] = outcome
    if outcome == 'NO_CONFIRMED_EVENT': coverage(value)
    value[field] = 'UNKNOWN' if field == 'event_list_exhaustiveness' else {k: True for k in policy.frozen_schema()['$defs'][field]['required']}
    assert not check(synthetic, value)['valid']


@pytest.mark.parametrize('change', ['missing_before', 'missing_after', 'reversed', 'outside', 'midpoint', 'wrong_id', 'wrong_observation', 'direct_with_observation', 'direct_blank', 'ambiguous', 'nonfinite'])
def test_invalid_event_evidence(synthetic, change):
    value = confirmed(synthetic); e = value['events'][0]
    if change == 'missing_before': e['evidence'] = e['evidence'][1:]
    elif change == 'missing_after': e['evidence'] = e['evidence'][:1]
    elif change == 'reversed': e['evidence'] = [cite(2, 'BEFORE'), cite(0, 'AFTER')]
    elif change == 'outside': e['evidence'][1]['frame_id'] = 'S000016'
    elif change == 'midpoint': e['event_time']['start_timestamp_s'] = 1.05
    elif change == 'wrong_id': e['local_candidate_reference'] = '8'
    elif change == 'wrong_observation': e['evidence'][0]['source_observation_ids'] = ['raw:wrong']
    elif change == 'direct_with_observation': e['evidence'][0].update(kind='DIRECT_VISUAL_ONLY', source_observation_ids=[])
    elif change == 'direct_blank': e['evidence'][1]['visual_description'] = '   '
    elif change == 'ambiguous': e['evidence'][0]['target_association'] = 'AMBIGUOUS'
    elif change == 'nonfinite': e['event_time']['end_timestamp_s'] = float('nan')
    assert not check(synthetic, value)['valid']


def test_multiple_events_not_forced_alternation(synthetic):
    value = confirmed(synthetic)
    value['events'].append(event(synthetic['item'], 'PICKUP', 3, 5, 'EVT002'))
    assert check(synthetic, value)['valid']


@pytest.mark.parametrize('case', ['duplicate_id', 'duplicate_event', 'unsorted', 'overlap_unflagged', 'opposite_exact'])
def test_multiple_event_errors(synthetic, case):
    value = confirmed(synthetic)
    second = event(synthetic['item'], 'PLACEMENT', 3, 5, 'EVT002')
    if case == 'duplicate_id': second['event_id'] = 'EVT001'
    if case == 'duplicate_event': second = copy.deepcopy(value['events'][0]); second['event_id'] = 'EVT002'
    if case == 'overlap_unflagged': second = event(synthetic['item'], 'PLACEMENT', 1, 4, 'EVT002')
    if case == 'opposite_exact':
        value['events'][0] = event(synthetic['item'], exact=True)
        second = event(synthetic['item'], 'PLACEMENT', id_='EVT002', exact=True)
    value['events'].append(second)
    if case == 'unsorted': value['events'].reverse()
    assert not check(synthetic, value)['valid']


def test_overlapping_brackets_explicit_uncertainty(synthetic):
    value = confirmed(synthetic)
    value['events'].append(event(synthetic['item'], 'PLACEMENT', 1, 4, 'EVT002'))
    for e in value['events']: e['chronology_uncertainty'] = True
    assert check(synthetic, value)['valid']


@pytest.mark.parametrize('type_,side,state', [('PICKUP','before_state','HELD_BY_PERSON'), ('PICKUP','after_state','ON_SURFACE'), ('PLACEMENT','before_state','ON_SURFACE'), ('PLACEMENT','after_state','HELD_BY_PERSON')])
def test_contrary_known_states(synthetic, type_, side, state):
    value = confirmed(synthetic, type_=type_); j = 0 if side == 'before_state' else 2
    value['events'][0][side] = {'state': state, 'frame_id': f'S{10+j:06d}', 'source_timestamp_s': 1+j/10,
                               'description': None, 'evidence': [cite(j)]}
    assert not check(synthetic, value)['valid']


def locate(value):
    value.update(last_confirmed_state='ON_SURFACE', last_confirmed_frame_id='S000013', last_confirmed_timestamp=1.3,
                 last_confirmed_state_evidence=[cite(3)], last_confirmed_location_description='Synthetic visible support', location_evidence_frame_ids=['S000013'])


@pytest.mark.parametrize('kind,coords,valid', [('POINT',[0,0],True), ('POINT',[1279,719],True), ('POINT',[1280,0],False), ('BBOX',[0,0,1280,720],True), ('BBOX',[50,0,20,20],False), ('BBOX',[0,0,20,721],False)])
def test_manual_marker_geometry(synthetic, kind, coords, valid):
    value = synthetic['response']; locate(value)
    value['location_marker'] = {'frame_id':'S000013','kind':kind,'coordinates':coords,'coordinate_system_id':'REVIEW_FRAME_PIXELS_V1','origin':'GUI_DRAWN'}
    assert check(synthetic, value)['valid'] == valid


@pytest.mark.parametrize('case', ['missing_state_support','wrong_marker_frame','other_missing_description','mixed_axis','not_observable_known_state','wrong_end_frame','visible_without_evidence','null_location_claim','subsequent_not_later'])
def test_state_visibility_and_location_errors(synthetic, case):
    value = synthetic['response']; locate(value)
    if case == 'missing_state_support': value['last_confirmed_state_evidence'] = []
    elif case == 'wrong_marker_frame': value['location_marker'] = {'frame_id':'S000014','kind':'POINT','coordinates':[1,1],'coordinate_system_id':'REVIEW_FRAME_PIXELS_V1','origin':'GUI_DRAWN'}
    elif case == 'other_missing_description': value['last_confirmed_state'] = 'OTHER_OBSERVED'
    elif case == 'mixed_axis': value['last_confirmed_state'] = 'VISIBLE'
    elif case == 'not_observable_known_state': value['window_outcome'] = 'TARGET_NOT_OBSERVABLE'
    elif case == 'wrong_end_frame': value['visibility_at_window_end']['frame_id'] = 'S000014'
    elif case == 'visible_without_evidence': value['visibility_at_window_end']['visibility'] = 'VISIBLE'
    elif case == 'null_location_claim': value['last_confirmed_frame_id'] = None
    elif case == 'subsequent_not_later': value.update(subsequent_location='OBSERVED_IN_WINDOW', subsequent_location_description='Synthetic', subsequent_location_evidence_frame_ids=['S000013'], subsequent_location_evidence=[cite(3)])
    assert not check(synthetic, value)['valid']


def test_unmodeled_observation_does_not_become_event(synthetic):
    value = synthetic['response']; value['unmodeled_observations'] = [{'observation_id':'UM001','description':'Synthetic sliding','evidence_frame_ids':['S000013'],'evidence':[cite(3)]}]
    assert check(synthetic, value)['valid']; assert value['events'] == []


@pytest.mark.parametrize('field', [k for k in policy.frozen_schema()['$defs']['attestations']['properties'] if k != 'human_attestation'])
def test_leakage_excludes_without_rewriting(synthetic, field):
    value = confirmed(synthetic, 'EXHAUSTIVE_ATTESTED'); value['attestations'][field] = True
    result = check(synthetic, value); assert result['valid']; assert field in result['exclusions']
    assert not validation.evaluation_metadata(value,result)['full_window_event_evaluation_supported']


@pytest.mark.parametrize('dependence', ['NOT_DEPENDENT','PARTIALLY_DEPENDENT','DEPENDENT','UNKNOWN'])
def test_dependence_primary_vs_sensitivity(synthetic, dependence):
    value = confirmed(synthetic,'EXHAUSTIVE_ATTESTED'); value['target_identification_event_dependence'] = dependence
    result = check(synthetic,value); assert result['valid']
    assert validation.evaluation_metadata(value,result)['primary_full_window_metrics_eligible'] == (dependence == 'NOT_DEPENDENT')


def test_original_exclusion_not_overridden(synthetic):
    value = confirmed(synthetic,'EXHAUSTIVE_ATTESTED'); synthetic['item']['dev_eligible'] = False
    result = check(synthetic,value); assert 'ORIGINALLY_INELIGIBLE' in result['exclusions']
    assert not validation.evaluation_metadata(value,result)['full_window_event_evaluation_supported']


@pytest.mark.parametrize('field', ['policy_md_sha256','policy_json_sha256','schema_sha256','review_item_sha256','source_video_sha256','authorized_visual_manifest_sha256','phase1c_response_sha256'])
def test_provenance_hash_mismatch(synthetic, field):
    value = synthetic['response']; value['provenance'][field] = 'f'*64
    assert not check(synthetic,value)['valid']


@pytest.mark.parametrize('value', ['2026-02-30T12:00:00+00:00','2026-10-12T12:00:00+08:00'])
def test_utc_calendar_checked(synthetic, value):
    synthetic['response']['provenance']['automatic_timestamp_utc'] = value
    assert not check(synthetic)['valid']


def test_immutable_save_duplicate_and_progress(synthetic):
    result = storage.submit(synthetic['draft'],synthetic['entry'],out=synthetic['out'])
    before = Path(result['path']).read_bytes()
    assert storage.progress(synthetic['out'])['valid_round1'] == 1
    with pytest.raises(ValueError,match='DUPLICATE'): storage.submit(synthetic['draft'],synthetic['entry'],out=synthetic['out'])
    assert Path(result['path']).read_bytes() == before
    assert 'events' not in storage.progress(synthetic['out'])


def test_duplicate_files_are_both_invalid(synthetic):
    result = storage.submit(synthetic['draft'],synthetic['entry'],out=synthetic['out'])
    policy.exclusive(synthetic['out']/'responses/duplicate.json',policy.read(result['path']),synthetic['out'])
    _, rows = storage.inventory(synthetic['out']); assert len(rows)==2; assert all(not r['valid'] for r in rows)


def test_blind_repeat_linkage_and_delay(synthetic):
    storage.submit(synthetic['draft'],synthetic['entry'],out=synthetic['out'])
    linkage = storage.round_linkage(synthetic['item']['annotation_item_id'],synthetic['out'])
    assert set(linkage)=={'sha256','timestamp','reviewer_id'}
    result = storage.submit(synthetic['draft'],synthetic['entry'],2,synthetic['out'])
    assert 'REPEAT_DELAY_SHORTER_THAN_7_DAYS' in result['warnings']
    assert policy.read(result['path'])['relabel_of']==linkage['sha256']


def test_repeat_cannot_precede_first(synthetic):
    with pytest.raises(ValueError,match='ROUND1'): storage.round_linkage(synthetic['item']['annotation_item_id'],synthetic['out'])


def test_finalize_empty_is_blocked(synthetic):
    with pytest.raises(ValueError,match='NO_GENUINE'): finalize.finalize(synthetic['out'])
    assert not (synthetic['out']/'exports').exists()


def test_finalize_real_storage_path_synthetic_only(synthetic):
    response = confirmed(synthetic,'UNKNOWN')
    draft = {k:v for k,v in response.items() if k not in ['schema_version','annotation_item_id','review_round','relabel_of','target_reference','same_reviewer_as_phase1c','provenance']}
    storage.submit(draft,synthetic['entry'],out=synthetic['out'])
    result = finalize.finalize(synthetic['out'],[2,3]); exported=policy.read(result['export_path'])
    assert result['summary']['annotated_inventory']=={'windows':1,'nonoverlap_groups':1,'source_video_files':1}
    assert exported['items'][0]['evaluation']['unlisted_events_status']=='UNEVALUATED'
    assert result['summary']['formal_eligible']==0; assert result['summary']['metrics_computed'] is False
    assert len(exported['items'][0]['sampling']['events'])==2


@pytest.mark.parametrize('strides', [[0],[-1],[1.5],[True]])
def test_invalid_strides(synthetic,strides):
    with pytest.raises(ValueError): finalize.sampling(confirmed(synthetic),synthetic['item'],strides)


def test_sampling_all_offsets_and_envelopes(synthetic):
    value=confirmed(synthetic); value['events'][0]['evidence']=[cite(0,'BEFORE'),cite(1,'BEFORE'),cite(2,'AFTER'),cite(3,'AFTER')]
    diagnostic=finalize.sampling(value,synthetic['item'],[2])['events'][0]
    assert diagnostic['all_offset_success']; assert diagnostic['successful_offsets']==[0,1]
    assert finalize.sampling(value,synthetic['item'])['status']=='SAMPLING_NOT_REQUESTED'
    assert finalize.sampling(synthetic['response'],synthetic['item'],[2])['status']=='NO_CONFIRMED_EVENTS'


@pytest.mark.parametrize('message',['','APPROVE_PHASE2A_POLICY_V1 c90f527eb01e','APPROVE_PHASE2A_POLICY_V2 000000000000','APPROVE_PHASE2A_POLICY_V2 c90f527eb01e extra'])
def test_approval_gate_rejects_missing_wrong_stale(synthetic,message):
    path=synthetic['out']/'stage_b/approval.json'
    data=policy.read(path); data['exact_human_message']=message
    path.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(ValueError,match='APPROVAL'): policy.verify_gate(synthetic['out'])


def test_frozen_contracts_and_production_inventory_readonly():
    assert policy.verify_gate()['policy_md_sha256'].startswith('c90f527eb01e')
    manifest=projection.load_manifest(); assert len(manifest['items'])==7; assert len(manifest['repeat_subset'])==2
    assert manifest['excluded'][0]['original_pack_ids']==['test8__W06']
    items=[projection.load_item(e) for e in manifest['items']]
    assert sum(len(i['visual']['frames']) for i in items)==728
    source=[i for i in items if i['stratum']=='SOURCE_RESOLVED_DEV'][0]
    assert len(source['visual']['frames'])==107; assert source['original_pack_ids']==['test1__W03','test1__W05']
    assert len({e['overlap_group_id'] for e in manifest['items']})==7
    assert len({e['source_video_identifier'] for e in manifest['items']})==6


def test_no_disallowed_import_or_operation():
    import ast
    for path in (policy.ROOT/'src/memory_graph/pass_t/phase2a_v2').glob('*.py'):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[n.name for n in node.names]+[getattr(node,'module','') or '']
                assert not any(any(bad in name for bad in ('phase1c_viewer','phase1c_responses','torch','transformers','requests','openai')) for name in names)
    assert not list((policy.OUT/'responses').glob('*.json'))


def test_safe_paths_and_exclusive_creation(synthetic):
    with pytest.raises(ValueError): policy.within(synthetic['out'],'../escape.json')
    path=synthetic['out']/'one.json'; policy.exclusive(path,{},synthetic['out'])
    with pytest.raises(FileExistsError): policy.exclusive(path,{},synthetic['out'])


def test_saved_response_tampering_is_detected(synthetic):
    import os
    result=storage.submit(synthetic['draft'],synthetic['entry'],out=synthetic['out'])
    path=Path(result['path']); value=policy.read(path); value['human_rationale']='Modified synthetic answer.'
    os.chmod(path,0o666); path.write_text(json.dumps(value),encoding='utf-8')
    _, rows=storage.inventory(synthetic['out'])
    assert not rows[0]['valid']; assert 'IMMUTABLE_SUBMISSION' in rows[0]['errors'][-1]
    with pytest.raises(ValueError,match='INVALID'): finalize.finalize(synthetic['out'])


def test_missing_immutable_receipt_is_reported(synthetic):
    result=storage.submit(synthetic['draft'],synthetic['entry'],out=synthetic['out'])
    proof=synthetic['out']/'validated'/(policy.read(result['path'])['provenance']['submission_id']+'.json')
    proof.unlink()
    _, rows=storage.inventory(synthetic['out'])
    assert not rows[0]['valid']


def test_later_known_state_cannot_be_ignored(synthetic):
    value=confirmed(synthetic)
    value['events'][0]['after_state']={'state':'HELD_BY_PERSON','frame_id':'S000012','source_timestamp_s':1.2,
                                      'description':None,'evidence':[cite(2)]}
    assert not check(synthetic,value)['valid']
    locate(value)
    assert check(synthetic,value)['valid']


@pytest.mark.parametrize('visibility',['NOT_VISIBLE','VISIBILITY_UNKNOWN'])
def test_exhaustive_coverage_cannot_contradict_end_visibility(synthetic,visibility):
    value=confirmed(synthetic,'EXHAUSTIVE_ATTESTED')
    value['visibility_at_window_end'].update(visibility=visibility,observed_reason='REASON_UNKNOWN' if visibility=='NOT_VISIBLE' else None)
    assert not check(synthetic,value)['valid']


def test_other_candidate_observations_do_not_extend_selected_track(synthetic):
    synthetic['item']['observations'].append({'candidate_id':'34','observation_id':'raw:other@11','source_frame_index':11,'bbox':[2,3,20,30]})
    value=confirmed(synthetic)
    value['events'][0]['evidence'].append(cite(1,'TRANSITION'))
    assert check(synthetic,value)['valid']
    value['events'][0]['evidence'][-1].update(kind='CANDIDATE_OBSERVATION_BACKED',source_observation_ids=['raw:other@11'])
    assert not check(synthetic,value)['valid']


def test_no_event_from_visibility_loss(synthetic):
    value=synthetic['response']
    value['visibility_at_window_end'].update(visibility='NOT_VISIBLE',observed_reason='REASON_UNKNOWN',evidence=[cite(5,association='NOT_VISIBLE')])
    assert check(synthetic,value)['valid']; assert value['events']==[]


def test_reference_frames_not_citable(synthetic):
    value=confirmed(synthetic)
    value['events'][0]['evidence'][0]['frame_id']='R000010'
    assert not check(synthetic,value)['valid']


def test_non_exhaustive_requires_uncertainty(synthetic):
    value=confirmed(synthetic); value['uncertainty']['status']='NO_ADDITIONAL_UNCERTAINTY'
    assert not check(synthetic,value)['valid']


def test_human_attestation_false_is_not_a_submission(synthetic):
    synthetic['draft']['attestations']['human_attestation']=False
    with pytest.raises(ValueError,match='SCHEMA'): storage.submit(synthetic['draft'],synthetic['entry'],out=synthetic['out'])
    assert not list((synthetic['out']/'responses').glob('*.json'))


def test_broken_source_hash_linkage_does_not_pass(synthetic):
    item=synthetic['out']/synthetic['entry']['item_path']; item.write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='hash'): projection.load_item(synthetic['entry'],synthetic['out'])


def test_v1_cannot_be_silently_migrated(synthetic):
    synthetic['response']['schema_version']='PASS_T_EVENT_GT_V1'
    assert not check(synthetic)['valid']


def test_nonfinite_citation_returns_error_not_exception(synthetic):
    value=confirmed(synthetic); value['events'][0]['evidence'][0]['source_timestamp_s']=float('nan')
    result=check(synthetic,value)
    assert not result['valid']; assert result['error_details']


def test_unknown_state_can_have_direct_supported_location(synthetic):
    value=synthetic['response']; locate(value); value['last_confirmed_state']='STATE_UNKNOWN'
    assert check(synthetic,value)['valid']


@pytest.mark.parametrize('change',['receipt','schema'])
def test_copied_frozen_contract_bytes_cannot_change(synthetic,change):
    import shutil
    contracts=synthetic['out']/'copied_contracts'; shutil.copytree(policy.CONTRACTS,contracts)
    path=contracts/('EVENT_GT_POLICY_V2.freeze_receipt.json' if change=='receipt' else 'event_gt_annotation_schema_v2.json')
    with path.open('a',encoding='utf-8') as stream: stream.write(' ')
    with pytest.raises(ValueError,match='FROZEN'): policy.verify_gate(synthetic['out'],contracts)


@pytest.mark.parametrize('version',['PASS_T_EVENT_GT_V1','PASS_T_EVENT_GT_V2'])
def test_raw_responses_cannot_be_reimported_or_migrated(synthetic,version):
    synthetic['response']['schema_version']=version
    with pytest.raises(ValueError,match='BACKEND_FIELDS'): storage.submit(synthetic['response'],synthetic['entry'],out=synthetic['out'])
    assert not list((synthetic['out']/'responses').glob('*.json'))
