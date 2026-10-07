import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from memory_graph.pass_i.common import OUT, read, read_lines, sha, write, jsonl
from memory_graph.pass_i.pilot import select_pilot, verify_pilot, extract_prompt, PROMPT_SOURCE, PROMPT_FILE, priority, parse_response
from memory_graph.pass_i.codex_transport import turn_input, CONFIG
from memory_graph.pass_i.annotations import AnnotationStore


def sample(item):
    return {'item_id': item['item_id'], 'label': 'AMBIGUOUS', 'ambiguity_cause': 'LOW_QUALITY',
            'challenge_tags': ['poor_image_quality'], 'evidence_for_same': [], 'evidence_for_different': [], 'confidence': 'high'}


def test_prompt_exact_and_pilot_deterministic_dev_only():
    manifest = verify_pilot()
    assert PROMPT_FILE.read_text(encoding='utf-8') == extract_prompt(PROMPT_SOURCE)
    pairs = read_lines(OUT / 'manifests/pair_manifest.jsonl')
    selected, blind = select_pilot(pairs)
    reversed_selected, reversed_blind = select_pilot(list(reversed(pairs)))
    assert [p['item_id'] for p in selected] == [p['item_id'] for p in reversed_selected]
    assert blind == reversed_blind
    assert len(selected) == 40 and len(blind) == 6
    assert all(p['split'] == 'dev' for p in selected)
    assert [p['item_id'] for p in selected] == [p['item_id'] for p in manifest['items']]


def test_actual_appserver_turn_serialization():
    manifest = verify_pilot()
    entry = manifest['items'][0]
    public = read(ROOT / entry['evidence_package']['path'])
    inputs = turn_input(public, PROMPT_FILE.read_text(encoding='utf-8'))
    text = json.dumps(inputs)
    for forbidden in ['time_gap', 'tracker', 'DINO', 'LightGlue', 'alias', 'creation_reason', 'sampling', 'physical_gt', 'IdentityGuard', 'candidate_epoch', str(ROOT)]:
        assert forbidden not in text
    assert sum(i['type'] == 'image' for i in inputs) == len(public['images'])
    assert all(i['url'].startswith('data:image/') for i in inputs if i['type'] == 'image')
    assert not CONFIG['features.shell_tool'] and not CONFIG['features.apps']


def test_review_priority_exact_formula():
    base = {'label': 'SAME', 'confidence': 'high', 'evidence_for_same': [{}], 'evidence_for_different': []}
    assert not priority(base)
    assert priority({**base, 'label': 'AMBIGUOUS'})
    assert priority({**base, 'confidence': 'medium'})
    assert priority({**base, 'confidence': 'low'})
    assert priority({**base, 'evidence_for_different': [{}]})


def test_malformed_json_not_repaired():
    entry = verify_pilot()['items'][0]
    public = read(ROOT / entry['evidence_package']['path'])
    p = sample(public)
    valid = parse_response(json.dumps(p), public)
    assert valid['json_valid'] and valid['schema_valid'] and valid['needs_human_review']
    fenced = parse_response('```json\n' + json.dumps(p) + '\n```', public)
    assert fenced['status'] == 'PRELABEL_PARSE_FAILED' and not fenced['json_valid']
    p['needs_human_review'] = True
    extra = parse_response(json.dumps(p), public)
    assert extra['json_valid'] and not extra['schema_valid']


def test_pilot_blind_first_reveal_gate_and_store_separation(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    manifest = verify_pilot()
    entry = next(p for p in manifest['items'] if p['blind_first'])
    pair = next(p for p in read_lines(OUT / 'manifests/pair_manifest.jsonl') if p['item_id'] == entry['item_id'])
    jsonl(tmp_path / 'manifests/pair_manifest.jsonl', [pair])
    write(tmp_path / 'manifests/dev_pilot_manifest.json', {**manifest, 'items': [entry]})
    AnnotationStore(tmp_path).export(1)
    pilot_store = AnnotationStore(tmp_path / 'annotations/dev_pilot', prelabels_out=tmp_path / 'prelabels/dev_pilot')
    public = read(ROOT / entry['evidence_package']['path'])
    draft = sample(public)
    pilot_store.save_prelabel(public, {'synthetic_fixture': True}, json.dumps(draft), draft)
    pilot_store.export(1)
    monkeypatch.setenv('FINDMIND_PASS_I_DATASET', str(tmp_path))
    app = AppTest.from_file(str(ROOT / 'scripts/pass_i_annotation_app.py'), default_timeout=30).run()
    assert not app.exception
    assert not any(b.label == 'Accept GPT' for b in app.button)
    assert not any(b.label == 'Reveal GPT prelabel' for b in app.button)
    next(x for x in app.selectbox if x.label == 'Required ambiguity cause').select('VIEW_MISMATCH')
    next(x for x in app.button if x.label == 'Save annotation').click().run()
    assert not app.exception
    assert pilot_store.all()[entry['item_id']]['human_blind_label'] == 'AMBIGUOUS'
    assert not any(b.label == 'Accept GPT' for b in app.button)
    next(x for x in app.button if x.label == 'Reveal GPT prelabel').click().run()
    assert not app.exception
    next(x for x in app.button if x.label == 'Accept GPT').click().run()
    assert not app.exception
    final = pilot_store.all()[entry['item_id']]
    assert final['accepted_gpt_prelabel']
    assert final['human_blind_ambiguity_cause'] == 'VIEW_MISMATCH'
    assert final['human_ambiguity_cause'] == 'LOW_QUALITY'
    assert AnnotationStore(tmp_path).all() == {}


def test_raw_persisted_before_parse_and_immutable(tmp_path, monkeypatch):
    import memory_graph.pass_i.pilot as mod
    entry = verify_pilot()['items'][0]
    item = read(ROOT / entry['evidence_package']['path'])
    monkeypatch.setattr(mod, 'PILOT_OUT', tmp_path)
    original_parser = mod.parse_response
    def checked_parser(text, public):
        assert (tmp_path / f"{public['item_id']}.raw.json").exists()
        return original_parser(text, public)
    monkeypatch.setattr(mod, 'parse_response', checked_parser)
    result = mod.record_response(item, {'synthetic_fixture': True}, 'bad json', {'wall_seconds': 0})
    assert result['status'] == 'PRELABEL_PARSE_FAILED'
    with pytest.raises(FileExistsError):
        mod.record_response(item, {}, '{}', {})
