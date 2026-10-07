"""Whitelisted GPT request adapter. No SDK import or network call at import/build time."""
from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

from .common import ROOT, resolve, sha

ALLOWED_ITEM = {'item_id', 'CASE_CHANGE_POLICY', 'images'}
ALLOWED_IMAGE = {'image_id', 'side', 'kind', 'number', 'path', 'sha256'}


def build_request(item, system_prompt, root=ROOT):
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError('A separately supplied system prompt is required')
    if set(item) != ALLOWED_ITEM:
        raise ValueError('Only public evidence-package fields are accepted')
    if item['CASE_CHANGE_POLICY'] not in {'NO_CASE_CHANGES', 'UNKNOWN'}:
        raise ValueError('Invalid case policy')
    if not isinstance(item['item_id'], str) or not __import__('re').fullmatch(r'PI_\d{6}', item['item_id']):
        raise ValueError('Invalid item ID')
    content = [{'type': 'input_text', 'text': f"item_id: {item['item_id']}\nCASE_CHANGE_POLICY = {item['CASE_CHANGE_POLICY']}"}]
    counts = {}
    for image in item['images']:
        if set(image) != ALLOWED_IMAGE:
            raise ValueError('Forbidden image metadata')
        side, kind = image['side'], image['kind']
        if side not in {'Q', 'R'} or kind not in {'phone_crop', 'context'}:
            raise ValueError('Invalid image type')
        key = (side, kind)
        counts[key] = counts.get(key, 0) + 1
        label = f'{side}-' + ('C' if kind == 'context' else '') + str(counts[key])
        if image['number'] != counts[key] or image['image_id'] != label:
            raise ValueError('Image numbering mismatch')
        p = resolve(image['path'], root)
        if not p.is_file() or sha(p) != image['sha256']:
            raise ValueError('Missing or changed image')
        mime = mimetypes.guess_type(p.name)[0]
        if mime not in {'image/png', 'image/jpeg', 'image/webp'}:
            raise ValueError('Unsupported image format')
        content.extend([{'type': 'input_text', 'text': f'[{label}]'},
            {'type': 'input_image', 'image_url': f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode(), 'detail': 'high'}])
    if not counts.get(('Q', 'phone_crop')) or not counts.get(('R', 'phone_crop')):
        raise ValueError('Both epochs require phone crops')
    # Filenames, epoch IDs, chronology and hidden provenance never leave this boundary.
    request = {'model': 'gpt-6.1-sol', 'input': [
        {'role': 'system', 'content': [{'type': 'input_text', 'text': system_prompt}]},
        {'role': 'user', 'content': content}]}
    json.dumps(request)  # Ensure actual request is serializable.
    return request


def prelabel(client, item, system_prompt, store, *, enabled=False, root=ROOT):
    if not enabled:
        raise PermissionError('GPT adapter is inactive; separate pilot authorization is required')
    if store.has_prelabel(item['item_id']):
        raise FileExistsError('Raw prelabel already exists; never overwrite')
    request = build_request(item, system_prompt, root)
    response = client.responses.create(**request)
    raw = response.model_dump(mode='json')
    text = response.output_text
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    # Preserve even invalid responses for human review; validation is separate.
    store.save_prelabel(item, raw, text, parsed)
    return parsed
