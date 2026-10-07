"""Local Strata HTTP adapter. Final content alone is semantic evidence."""
import base64
import copy
import json
import mimetypes
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from memory_graph.reasoning.json_contract import parse_json


class StrataError(RuntimeError):
    pass


def ordered_content(prompt, images):
    content = [{'type': 'text', 'text': prompt}]
    for index, path in enumerate(images):
        path = Path(path)
        mime = mimetypes.guess_type(path.name)[0]
        if mime not in {'image/png', 'image/jpeg', 'image/webp'}:
            raise ValueError('Unsupported image type: ' + str(path))
        encoded = base64.b64encode(path.read_bytes()).decode('ascii')
        content.extend([{'type': 'text', 'text': f'frame_{index+1} (chronological image {index+1})'},
                        {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{encoded}'}}])
    return content


def public_response(response):
    """Keep final API data, but never persist private reasoning or token traces."""
    r = copy.deepcopy(response)
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()
                    if k not in {'reasoning_content', 'reasoning', 'thinking', 'reasoning_text', 'token_log', 'logprobs'}}
        if isinstance(value, list):
            return [clean(v) for v in value]
        if isinstance(value, str):
            # Also protect against a frontend regression which leaks a thinking block into final content.
            return re.sub(r'<think>.*?(?:</think>|$)', '[private reasoning removed]', value, flags=re.S)
        return value
    return clean(r)


def final_response(response, parse=True):
    try:
        choice = response['choices'][0]
        message = choice['message']
        content = message.get('content')
        reasoning = message.get('reasoning_content') or ''
    except (KeyError, IndexError, TypeError) as exc:
        raise StrataError('Invalid Chat Completions envelope') from exc
    if not isinstance(content, str) or not content.strip():
        raise StrataError('Missing final content; private reasoning cannot supply an answer')
    if '<think>' in content or '</think>' in content:
        raise StrataError('Private reasoning leaked into final content; rejected')
    if choice.get('finish_reason') != 'stop':
        raise StrataError('Incomplete generation: ' + str(choice.get('finish_reason')))
    try:
        answer = parse_json(content) if parse else None
    except (ValueError, TypeError) as exc:
        raise StrataError('Malformed final JSON: ' + str(exc)) from exc
    return {'answer': answer, 'final_content': content, 'raw_response': public_response(response),
            'reasoning_metadata': {'present': bool(reasoning), 'characters': len(reasoning)},
            'usage': response.get('usage', {}), 'finish_reason': choice.get('finish_reason')}


class StrataClient:
    def __init__(self, base_url='http://127.0.0.1:8080', model='qwen3.8-flash-next-coder', timeout=600, retries=1,
                 reasoning_budget_tokens=3072):
        url = urllib.parse.urlsplit(base_url)
        if url.scheme != 'http' or url.hostname != '127.0.0.1' or url.username or url.password or url.query or url.fragment:
            raise ValueError('V294 requires http://127.0.0.1 only')
        if url.path not in {'', '/'}:
            raise ValueError('Provide the server root URL, without /v1')
        if timeout <= 0 or retries not in (0, 1, 2):
            raise ValueError('Positive timeout and at most two retries required')
        self.base_url = base_url.rstrip('/')
        self.model, self.timeout, self.retries = model, timeout, retries
        if not isinstance(reasoning_budget_tokens, int) or isinstance(reasoning_budget_tokens, bool) or reasoning_budget_tokens < 0:
            raise ValueError('Reasoning budget must be a non-negative integer')
        self.reasoning_budget_tokens = reasoning_budget_tokens
        self.last_attempts = 0
        self.last_public = None

    def request(self, path, payload=None):
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('Absolute local API path required')
        data = None if payload is None else json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf8')
        req = urllib.request.Request(self.base_url+path, data=data, headers={'Content-Type': 'application/json; charset=utf-8'})
        for attempt in range(self.retries+1):
            self.last_attempts = attempt+1
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as result:
                    return json.loads(result.read().decode('utf8', errors='strict'))
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 502, 503) and attempt < self.retries:
                    time.sleep(.5*(attempt+1))
                    continue
                # Do not retain arbitrary error bodies which could contain private reasoning.
                raise StrataError(f'HTTP {exc.code}: {exc.reason}') from exc
            except TimeoutError as exc:
                # A timed-out POST may still run server-side: never blindly duplicate it.
                raise StrataError('Timeout waiting for Strata') from exc
            except (urllib.error.URLError, OSError, ValueError) as exc:
                raise StrataError(type(exc).__name__ + ': ' + str(exc)) from exc

    def health(self):
        data = self.request('/health')
        if (data.get('status') != 'ok' or not data.get('loaded') or not data.get('images')
                or data.get('max_context') != 32768):
            raise StrataError('Strata must be loaded with vision and exactly 32768 context')
        self.model = data.get('model') or self.model
        return data

    def complete(self, prompt, images=(), *, parse=True, effort='high', max_tokens=4096):
        self.last_public = None
        payload = {'model': self.model, 'messages': [{'role': 'user', 'content': ordered_content(prompt, images)}],
                   'reasoning_effort': effort, 'temperature': 0, 'top_p': 1, 'seed': 294,
                   'max_tokens': max_tokens, 'stream': False, 'reasoning_budget_tokens': self.reasoning_budget_tokens}
        started = time.monotonic()
        response = self.request('/v1/chat/completions', payload)
        self.last_public = public_response(response)
        result = final_response(response, parse=parse)
        result.update(latency_seconds=time.monotonic()-started, attempts=self.last_attempts,
                      image_count=len(images), request_parameters={k: v for k, v in payload.items() if k != 'messages'})
        return result
