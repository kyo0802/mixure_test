"""Standalone Strata gate, before any FindMind event-pack execution."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.v294_strata.api import StrataClient
from memory_graph.v294_strata.resources import ResourceMonitor
from memory_graph.v294_strata.runner import OUT, save


def main():
    from PIL import Image, ImageDraw, ImageFont
    client = StrataClient(timeout=900)
    health = client.health()
    save(OUT/'smoke/health.json', {'health': health, 'models': client.request('/v1/models'),
                                  'status': client.request('/v1/status')})
    def call(name, text, images=(), effort='high', max_tokens=4096):
        print('Standalone:', name, flush=True)
        with ResourceMonitor() as monitor:
            result = client.complete(text, images, effort=effort, max_tokens=max_tokens)
        result['resources'] = monitor.summary()
        result['server_timings'] = client.request('/v1/status').get('last_timings')
        save(OUT/f'smoke/{name}.json', result)
        return result

    text = call('text_test', 'Return exactly this JSON: {"ok":true,"unicode":"測試"}.', effort='none', max_tokens=128)
    assert text['answer'] == {'ok': True, 'unicode': '測試'}, 'Text/UTF-8 smoke failed'
    folder = OUT/'smoke/images'; folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for n, color in enumerate(['RED', 'GREEN', 'BLUE']):
        # Filenames deliberately do not sort into temporal order.
        path = folder/["第三.png", "第一.png", "第二.png"][n]
        image = Image.new('RGB', (512, 384), {'RED': '#ef2828', 'GREEN': '#20ce50', 'BLUE': '#305aef'}[color])
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 56)
        draw.text((45, 140), f'{n+1} {color}', fill='white', font=font)
        image.save(path); paths.append(path)
    single = call('image_test', 'Read the visible number and color word. Return only JSON {"number": integer, "color": "color word"}.', paths[:1])
    assert single['answer'] == {'number': 1, 'color': 'RED'}, 'Single-image recognition failed'
    multi = call('multi_image_test', 'Read each separate image in its supplied order. Return only JSON with keys "numbers" and "colors", each an array in the image order.', paths)
    assert list(map(str, multi['answer'].get('numbers', []))) == ['1', '2', '3'], 'Multi-image number order failed'
    assert [str(c).upper() for c in multi['answer'].get('colors', [])] == ['RED', 'GREEN', 'BLUE'], 'Multi-image color order failed'
    assert multi['reasoning_metadata']['present'], 'High effort produced no separate reasoning evidence'
    # Near-full context probe. Counting uses the official Anthropic endpoint, without generation.
    padding = 'ordinary neutral words in this context. '*3600
    instruction = '\nAt the end return only JSON {"context_check":"V294_END"}. '
    count = client.request('/v1/messages/count_tokens', {'model': client.model, 'max_tokens': 512,
                           'messages': [{'role': 'user', 'content': padding+instruction}]})
    token_count = count['input_tokens']
    if not 24000 <= token_count <= 30000:
        repetitions = int(3600*27500/token_count)
        padding = 'ordinary neutral words in this context. '*repetitions
        count = client.request('/v1/messages/count_tokens', {'model': client.model, 'max_tokens': 512,
                               'messages': [{'role': 'user', 'content': padding+instruction}]})
    assert 24000 <= count['input_tokens'] <= 30000, 'Near-32K probe token budget outside expected range'
    context = call('context_32k_test', padding+instruction, effort='high', max_tokens=4096)
    assert context['answer'] == {'context_check': 'V294_END'}, 'Long-context final answer failed'
    context['counted_prompt_tokens'] = count['input_tokens']
    save(OUT/'smoke/context_32k_test.json', context)
    save(OUT/'smoke/gate.json', {'passed': True, 'unix': time.time(), 'health': True, 'models': True,
                               'text': True, 'single_image': True, 'ordered_multi_image': True, 'high_reasoning': True,
                               'context_configured': 32768, 'near_full_context_prompt_tokens': count['input_tokens'],
                               'utf8': True, 'all_completed_without_oom': True})
    print('Standalone smoke gate passed.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        save(OUT/'smoke/gate.json', {'passed': False, 'error': type(exc).__name__+': '+str(exc)})
        raise
