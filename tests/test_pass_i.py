import copy
import json
import os
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from memory_graph.pass_i.common import OUT, read, read_lines, sha, write, jsonl
from memory_graph.pass_i.adapter import build_request, prelabel
from memory_graph.pass_i.annotations import AnnotationStore, validate_annotation, validate_prelabel
from memory_graph.pass_i.builder import validate_dataset, select_crops, DEFAULT_CONFIG, number_images, protected_snapshot


@pytest.fixture
def item(tmp_path):
    images = []
    for side in ['Q', 'R']:
        for kind, name in [('phone_crop', '1'), ('context', 'C1')]:
            p = tmp_path / f'{side}_{name}.png'
            Image.new('RGB', (32, 40), 'gray').save(p)
            images.append({'image_id': f'{side}-{name}', 'side': side, 'kind': kind, 'number': 1,
                           'path': str(p), 'sha256': sha(p)})
    return {'item_id': 'PI_000001', 'CASE_CHANGE_POLICY': 'UNKNOWN', 'images': images}


def annotation(**changes):
    return {'item_id': 'PI_000001', 'status': 'REVIEWED', 'human_label': 'AMBIGUOUS',
        'human_ambiguity_cause': 'NO_DISCRIMINATIVE_FEATURE', 'human_challenge_tags': [],
        'accepted_gpt_prelabel': False, 'exclude_reason': None, **changes}


def draft(item):
    return {'item_id': item['item_id'], 'label': 'AMBIGUOUS', 'ambiguity_cause': 'NO_DISCRIMINATIVE_FEATURE',
            'challenge_tags': [], 'evidence_for_same': [], 'evidence_for_different': [], 'confidence': 'high'}


def test_real_dataset_sessions_images_hashes_numbering_protection():
    result = validate_dataset()
    assert result['failed'] == 0, result['errors']
    assert result['protected_files_verified'] > 0


def test_no_session_or_source_overlap():
    inv = read_lines(OUT / 'manifests/candidate_epoch_inventory.jsonl')
    split = read(OUT / 'manifests/session_split.json')
    assert split['frozen_before_inference'] and not split['gpt_outputs_observed']
    sessions = {s: {e['session_id'] for e in inv if e['split'] == s} for s in ['dev', 'frozen']}
    frames = {s: {r['raw_image_sha256'] for e in inv if e['split'] == s for r in e['source_observations']} for s in ['dev', 'frozen']}
    assert not sessions['dev'] & sessions['frozen']
    assert not frames['dev'] & frames['frozen']
    recordings = {r['video_id']: r for r in split['recordings']}
    for reason in split['grouping_evidence']:
        assert recordings[reason['a']]['split'] == recordings[reason['b']]['split']
        assert recordings[reason['a']]['session_id'] == recordings[reason['b']]['session_id']


def test_actual_serialized_request_excludes_metadata(item):
    request = build_request(item, 'Separately supplied test prompt')
    serialized = json.dumps(request)
    forbidden = ['time_gap_seconds', 'tracker', 'DINO', 'LightGlue', 'retrieval', 'creation_reason',
                 'alias', 'IdentityGuard', 'physical_identity', 'pair_generation', 'sampling',
                 'candidate_epoch_id', 'crop_sha256', 'sha256', 'frame', 'timestamp']
    assert all(k not in serialized for k in forbidden)
    assert str(ROOT) not in serialized
    assert [c['text'] for c in request['input'][1]['content'] if c['type'] == 'input_text'][1:] == ['[Q-1]', '[Q-C1]', '[R-1]', '[R-C1]']
    assert sum(c['type'] == 'input_image' for c in request['input'][1]['content']) == 4
    for key in forbidden:
        contaminated = {**item, key: 'secret'}
        with pytest.raises(ValueError):
            build_request(contaminated, 'External prompt')
    contaminated = copy.deepcopy(item)
    contaminated['images'][0]['retrieval_rank'] = 1
    with pytest.raises(ValueError):
        build_request(contaminated, 'External prompt')


def test_adapter_inactive_does_not_call_client(item, tmp_path):
    class ForbiddenClient:
        @property
        def responses(self):
            pytest.fail('Model call attempted')
    with pytest.raises(PermissionError):
        prelabel(ForbiddenClient(), item, 'External prompt', AnnotationStore(tmp_path))


@pytest.mark.parametrize('changes', [
    {'human_ambiguity_cause': None}, {'human_ambiguity_cause': ['LOW_QUALITY', 'VIEW_MISMATCH']},
    {'human_label': 'SAME'}, {'human_challenge_tags': ['none', 'motion_blur']},
    {'human_challenge_tags': ['invented']},
    {'status': 'EXCLUDED', 'exclude_reason': 'wrong_crop'},
    {'status': 'EXCLUDED', 'human_label': None, 'human_ambiguity_cause': None, 'exclude_reason': None},
])
def test_invalid_annotations_rejected(changes):
    with pytest.raises((ValueError, TypeError)):
        validate_annotation(annotation(**changes))


@pytest.mark.parametrize('label', ['SAME', 'DIFFERENT'])
def test_nonambiguous_null_cause(label):
    validate_annotation(annotation(human_label=label, human_ambiguity_cause=None))


def test_exclusion_not_gold_and_restart(tmp_path):
    store = AnnotationStore(tmp_path)
    store.save(annotation(), 2)
    store.save(annotation(item_id='PI_000002', status='EXCLUDED', human_label=None,
                          human_ambiguity_cause=None, exclude_reason='wrong_crop'), 2)
    resumed = AnnotationStore(tmp_path)
    assert len(resumed.all()) == 2
    assert [a['item_id'] for a in resumed.gold()] == ['PI_000001']
    assert read(tmp_path / 'annotations/annotation_progress.json')['excluded'] == 1
    assert len(read_lines(tmp_path / 'annotations/excluded_items.jsonl')) == 1
    resumed.save(annotation(human_ambiguity_cause='LOW_QUALITY'), 2)
    assert AnnotationStore(tmp_path).all()['PI_000001']['human_ambiguity_cause'] == 'LOW_QUALITY'


def test_separate_prelabel_human_blind_and_physical(item, tmp_path):
    store = AnnotationStore(tmp_path)
    p = draft(item)
    store.save_prelabel(item, {'mock': 'test fixture only'}, json.dumps(p), p)
    raw_file = tmp_path / 'prelabels/PI_000001.json'
    before = raw_file.read_bytes()
    store.save(annotation(human_blind_label='AMBIGUOUS', human_blind_ambiguity_cause='LOW_QUALITY', human_blind_challenge_tags=[]))
    store.save(annotation(accepted_gpt_prelabel=True))
    store.save_physical('PI_000001', 'UNKNOWN', 'Synthetic test fixture')
    assert raw_file.read_bytes() == before
    assert store.all()['PI_000001']['human_blind_ambiguity_cause'] == 'LOW_QUALITY'
    assert 'physical_identity' not in store.all()['PI_000001']
    assert store.all('physical')['PI_000001']['physical_identity'] == 'UNKNOWN'
    with pytest.raises(FileExistsError):
        store.save_prelabel(item, {}, '', p)


def test_invalid_crop_evidence_indices(item):
    p = draft(item)
    p.update(label='SAME', ambiguity_cause=None, evidence_for_same=[{'feature': 'Test fixture mark', 'q_image': 2, 'r_image': 1}])
    with pytest.raises(ValueError):
        validate_prelabel(p, item)
    p['evidence_for_same'][0]['q_image'] = 1
    validate_prelabel(p, item)


def test_numbering_and_hash_tampering(item):
    wrong = copy.deepcopy(item)
    wrong['images'][0]['image_id'] = 'Q-2'
    with pytest.raises(ValueError):
        build_request(wrong, 'Prompt')
    wrong = copy.deepcopy(item)
    wrong['images'][0]['sha256'] = '0' * 64
    with pytest.raises(ValueError):
        build_request(wrong, 'Prompt')


def test_selection_does_not_pad_adjacent_or_duplicate_frames():
    rows = [{'observation_id': str(i), 'frame': i, 'time': i * .1, 'available': True,
             'raw_crop_sha256': str(i), 'quality': {'dhash': '1', 'width': 20, 'height': 20, 'blur_laplacian_variance': 5}} for i in range(10)]
    assert len(select_crops(rows, DEFAULT_CONFIG)) == 1


def test_streamlit_blind_save_exclude_resume_review_and_physical(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    # Two real evidence packages copied by manifest reference; annotations use test-only storage.
    pairs = read_lines(OUT / 'manifests/pair_manifest.jsonl')
    pairs = [p for p in pairs if p['split'] == 'dev'][:2]
    jsonl(tmp_path / 'manifests/pair_manifest.jsonl', pairs)
    (tmp_path / 'manifests/session_split.json').write_bytes((OUT / 'manifests/session_split.json').read_bytes())
    (tmp_path / 'manifests/candidate_epoch_inventory.jsonl').write_bytes((OUT / 'manifests/candidate_epoch_inventory.jsonl').read_bytes())
    store = AnnotationStore(tmp_path)
    store.export(2)
    monkeypatch.setenv('FINDMIND_PASS_I_DATASET', str(tmp_path))
    app = AppTest.from_file(str(ROOT / 'scripts/pass_i_annotation_app.py'), default_timeout=30).run()
    assert not app.exception
    assert not any('GPT prelabel ·' in x.value for x in app.subheader)
    next(x for x in app.selectbox if x.label == 'Required ambiguity cause').select('LOW_QUALITY')
    next(x for x in app.button if x.label == 'Save annotation').click().run()
    assert not app.exception
    assert store.all()[pairs[0]['item_id']]['human_label'] == 'AMBIGUOUS'
    next(x for x in app.button if x.label == 'Next').click().run()
    next(x for x in app.radio if x.label == 'Human decision').set_value('EXCLUDE ITEM').run()
    next(x for x in app.selectbox if x.label == 'Required exclusion reason').select('wrong_crop')
    next(x for x in app.button if x.label == 'Save annotation').click().run()
    assert not app.exception
    assert store.all()[pairs[1]['item_id']]['status'] == 'EXCLUDED'
    restart = AppTest.from_file(str(ROOT / 'scripts/pass_i_annotation_app.py'), default_timeout=30).run()
    assert not restart.exception
    # Model response is a synthetic fixture only, never a dataset prelabel.
    public = read(ROOT / pairs[0]['evidence_package']['path'])
    p = draft(public)
    store.save_prelabel(public, {'synthetic_test_fixture': True}, json.dumps(p), p)
    next(x for x in restart.radio if x.label == 'Mode').set_value('Review').run()
    assert not restart.exception
    next(x for x in restart.button if x.label == 'Accept GPT').click().run()
    assert store.all()[pairs[0]['item_id']]['accepted_gpt_prelabel']
    next(x for x in restart.radio if x.label == 'Mode').set_value('Physical Identity Review').run()
    assert not restart.exception
    restart.text_area[0].set_value('Synthetic physical provenance')
    next(x for x in restart.button if x.label == 'Save physical GT').click().run()
    assert not restart.exception
    assert store.all('physical')[pairs[0]['item_id']]['physical_gt_reviewed']
    next(x for x in restart.radio if x.label == 'Mode').set_value('Blind').run()
    next(x for x in restart.selectbox if x.label == 'Filter').select('Excluded').run()
    assert next(x for x in restart.selectbox if x.label == 'Item').value == pairs[1]['item_id']
    next(x for x in restart.selectbox if x.label == 'Filter').select('Unreviewed').run()
    assert not restart.exception
    assert any('No items match' in x.value for x in restart.info)
