import base64
import json
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest
from PIL import Image

from memory_graph.v294_strata.api import StrataClient, StrataError, final_response, ordered_content, public_response
from memory_graph.reasoning.validator import DirectReasoningValidator


ANSWER = dict(event_type='STATIC', interaction_anchor='NONE', released='NO',
              target_visible_after='YES', final_relation='NONE', final_relation_anchor='NONE', confidence='HIGH')


def response(content=None, reasoning=None):
    return {'choices': [{'message': {'content': content, 'reasoning_content': reasoning}, 'finish_reason': 'stop'}]}


@pytest.mark.parametrize('url', ['http://0.0.0.0:8080', 'http://192.168.1.1:8080', 'https://example.com'])
def test_loopback_only(url):
    with pytest.raises(ValueError):
        StrataClient(url)


def test_health_requires_loaded_vision_context():
    c = StrataClient()
    c.request = lambda *args: dict(status='ok', loaded=True, images=True, max_context=32768)
    assert c.health()['loaded']
    for key, bad in [('loaded', False), ('images', False), ('max_context', 8192), ('status', 'error')]:
        c.request = lambda *args, key=key, bad=bad: {**dict(status='ok', loaded=True, images=True, max_context=32768), key: bad}
        with pytest.raises(StrataError):
            c.health()


def test_explicit_image_order_and_unicode_path(tmp_path):
    paths = [tmp_path/'三.png', tmp_path/'一.png', tmp_path/'二.png']
    for i, p in enumerate(paths):
        Image.new('RGB', (10, 12), (i*100, 0, 0)).save(p)
    content = ordered_content('Read chronologically', paths)
    assert content[0]['text'] == 'Read chronologically'
    for i, p in enumerate(paths):
        assert content[1+2*i]['text'].startswith(f'frame_{i+1}')
        assert base64.b64decode(content[2+2*i]['image_url']['url'].split(',')[1]) == p.read_bytes()


def test_missing_image_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        ordered_content('x', [tmp_path/'missing.png'])


def test_final_only_and_reasoning_redacted():
    result = final_response(response(json.dumps(ANSWER), 'DO NOT SAVE THIS PRIVATE THOUGHT'))
    assert result['answer'] == ANSWER
    assert result['reasoning_metadata']['present'] is True
    assert 'PRIVATE THOUGHT' not in json.dumps(result)
    assert 'reasoning_content' not in json.dumps(result)


def test_reasoning_cannot_supply_missing_final():
    with pytest.raises(StrataError):
        final_response(response(None, json.dumps(ANSWER)))


def test_embedded_thinking_cannot_leak_to_error_artifact():
    raw = response('<think>PRIVATE THOUGHT</think>'+json.dumps(ANSWER), 'SECOND PRIVATE THOUGHT')
    with pytest.raises(StrataError):
        final_response(raw)
    assert 'PRIVATE THOUGHT' not in json.dumps(public_response(raw))


def test_no_claims_added_by_prompt():
    from memory_graph.v294_strata.prompts import prompt
    event = {'markers': ['A'], 'actor_markers': ['A'], 'location_markers': [],
             'contexts': [{'marker': 'A', 'raw_label': 'person'}], 'frames': [{'phase': 'BEFORE'}, {'phase': 'AFTER'}]}
    text = prompt(event)
    assert 'confidence' in text and 'A=person' in text
    assert 'Nearest' not in text
    assert 'not necessarily final anchor' in text
    assert 'identity is not authorized' in text


@pytest.mark.parametrize('text', ['[]', '{broken', '{"event_type":"STATIC","event_type":"PICKED_UP"}', '{"confidence":NaN}'])
def test_malformed_final_rejected(text):
    with pytest.raises(StrataError):
        final_response(response(text))


def test_missing_semantic_fields_not_repaired():
    result = final_response(response('{"event_type":"STATIC"}'))
    validation = DirectReasoningValidator().validate({'pack_id': 'test', 'markers': []}, result['answer'])
    assert not validation['schema_valid']
    assert result['answer'] == {'event_type': 'STATIC'}


def test_canonical_seven_fields():
    result = final_response(response(json.dumps(ANSWER)))
    assert DirectReasoningValidator().validate({'pack_id': 'test', 'markers': []}, result['answer'])['valid']
    result['answer']['actor'] = 'NONE'
    assert not DirectReasoningValidator().validate({'pack_id': 'test', 'markers': []}, result['answer'])['schema_valid']


def test_truncated_generation_rejected():
    r = response(json.dumps(ANSWER))
    r['choices'][0]['finish_reason'] = 'length'
    with pytest.raises(StrataError):
        final_response(r)


def test_timeout_no_duplicate_inference(monkeypatch):
    calls = []
    def fail(*args, **kwargs):
        calls.append(kwargs)
        raise TimeoutError('test timeout')
    monkeypatch.setattr('urllib.request.urlopen', fail)
    with pytest.raises(StrataError, match='Timeout'):
        StrataClient(timeout=0.1).request('/v1/chat/completions', {'messages': []})
    assert len(calls) == 1
    assert calls[0]['timeout'] == .1


def test_transient_retry_is_bounded(monkeypatch):
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise urllib.error.HTTPError('http://127.0.0.1', 503, 'busy', {}, None)
    monkeypatch.setattr('urllib.request.urlopen', fail)
    monkeypatch.setattr('time.sleep', lambda _: None)
    with pytest.raises(StrataError):
        StrataClient(retries=1).request('/health')
    assert len(calls) == 2


def test_api_sets_high_low_randomness_and_order(monkeypatch, tmp_path):
    image = tmp_path/'f1.png'
    Image.new('RGB', (10, 10)).save(image)
    client = StrataClient()
    captured = []
    client.request = lambda path, payload: captured.append((path, payload)) or response(json.dumps(ANSWER))
    result = client.complete('x', [image])
    assert result['answer'] == ANSWER
    req = captured[0][1]
    assert req['reasoning_effort'] == 'high'
    assert req['reasoning_budget_tokens'] == 3072
    assert req['max_tokens'] == 4096 and req['temperature'] == 0 and req['seed'] == 294
    assert len(req['messages'][0]['content']) == 3


def test_normal_pipeline_does_not_import_strata():
    code = "import sys; from memory_graph.identity import pipeline; assert not any(x.startswith('memory_graph.v294_strata') for x in sys.modules)"
    run = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr


def test_v294_output_guard_rejects_external_path(tmp_path):
    from memory_graph.v294_strata.runner import save
    forbidden = tmp_path/'not_v294.json'
    with pytest.raises(ValueError, match='V294 results'):
        save(forbidden, {'x': 1})
    assert not forbidden.exists()


def test_health_binds_actual_loaded_model():
    client = StrataClient()
    client.request = lambda _: dict(status='ok', loaded=True, images=True, max_context=32768, model='actual-coder-iq1_m')
    client.health()
    assert client.model == 'actual-coder-iq1_m'


def test_changed_video_cannot_reuse_identity_ledger(monkeypatch, tmp_path):
    from memory_graph.v294_strata import runner
    monkeypatch.setattr(runner, 'OUT', tmp_path)
    source = tmp_path/'authorized_rows.json'
    monkeypatch.setattr(runner, 'current_sources', lambda: [('test', 'development', source, tmp_path/'video.mp4')])
    def fake_read(path):
        if Path(path).name == 'gate.json':
            return {'passed': True}
        if Path(path).name == 'metrics.json':
            return {'video_sha256': 'old-video'}
        return []
    monkeypatch.setattr(runner, 'read', fake_read)
    monkeypatch.setattr(runner, 'sha', lambda _: 'changed-video')
    with pytest.raises(ValueError, match='Video changed'):
        runner.prepare()


@pytest.mark.parametrize('budget', [-1, True, 1.5])
def test_invalid_reasoning_budget_rejected(budget):
    with pytest.raises(ValueError):
        StrataClient(reasoning_budget_tokens=budget)


def test_changed_prompt_cannot_reuse_completed_event(monkeypatch, tmp_path):
    from memory_graph.v294_strata import runner
    monkeypatch.setattr(runner, 'OUT', tmp_path)
    event = {'video_id': 'test2', 'pack_id': 'test2__W04', 'frames': [1], 'physical_reasoning_eligible': True}
    dest = tmp_path/'smoke/findmind_pack_test.json'
    dest.parent.mkdir()
    dest.write_text('{}')
    monkeypatch.setattr(runner, 'read', lambda p: [event] if Path(p).name == 'events.json' else
                        {'event_sha256': 'old-evidence', 'request': {'prompt': 'old-prompt'}})
    monkeypatch.setattr(runner, 'prompt', lambda _: 'new-prompt')
    with pytest.raises(ValueError, match='different evidence or prompt'):
        runner.run(first=True)
