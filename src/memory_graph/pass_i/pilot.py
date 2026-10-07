"""Fixed DEV pilot selection and raw-first parsing; no benchmark gold construction."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from .common import ROOT, OUT, read, write, read_lines, sha, ref, jsonl
from .adapter import build_request
from .annotations import validate_prelabel, AnnotationStore

PROMPT_SOURCE = Path(r'C:\Users\smile\.codex\attachments\04123513-f88b-4385-9d3e-024b2292227a\貼上的文字.txt')
PILOT_MANIFEST = OUT / 'manifests/dev_pilot_manifest.json'
PROMPT_FILE = OUT / 'prompts/pass_i_prelabel_prompt.txt'
PILOT_OUT = OUT / 'prelabels/dev_pilot'
PILOT_ANNOTATIONS = OUT / 'annotations/dev_pilot'
SCHEMA_VERSION = 'pass_i_visual_identity_v1'
MODEL = 'gpt-6.1-sol'
SEED = 297102


def extract_prompt(source):
    text = Path(source).read_text(encoding='utf-8')
    start = '## BEGIN PASS I VISUAL ANNOTATOR SYSTEM PROMPT'
    end = '## END PASS I VISUAL ANNOTATOR SYSTEM PROMPT'
    # Boundary newlines are framing, not prompt content. Never modify internal bytes.
    return text.split(start, 1)[1].split(end, 1)[0].strip('\r\n')


def priority(p):
    return p['label'] == 'AMBIGUOUS' or p['confidence'] != 'high' or bool(p['evidence_for_same'] and p['evidence_for_different'])


def select_pilot(pairs, count=40, seed=SEED):
    dev = [p for p in pairs if p['split'] == 'dev']
    if len(dev) < count:
        raise ValueError('Insufficient existing DEV pairs')
    rank = lambda p: hashlib.sha256(f"{seed}:{p['item_id']}".encode()).hexdigest()
    dev.sort(key=rank)
    strata = sorted({c for p in dev for c in p['pair_generation']['sampling_attributes']})
    videos = sorted({p['video_id'] for p in dev})
    queues = [[p for p in dev if c in p['pair_generation']['sampling_attributes']] for c in strata]
    queues += [[p for p in dev if p['video_id'] == v] for v in videos]
    queues += [[p for p in dev if len(p['images']) >= 10], [p for p in dev if len(p['images']) < 10], dev]
    chosen, seen = [], set()
    positions = [0] * len(queues)
    while len(chosen) < count:
        for i, queue in enumerate(queues):
            while positions[i] < len(queue) and queue[positions[i]]['item_id'] in seen:
                positions[i] += 1
            if positions[i] < len(queue):
                p = queue[positions[i]]
                seen.add(p['item_id']); chosen.append(p)
                if len(chosen) == count:
                    break
    chosen.sort(key=lambda p: p['item_id'])
    blind = {p['item_id'] for p in sorted(chosen, key=lambda p: hashlib.sha256(f"{seed}:blind:{p['item_id']}".encode()).hexdigest())[:round(count * .15)]}
    return chosen, blind


def schema():
    evidence = {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
        'properties': {'feature': {'type': 'string', 'minLength': 1}, 'q_image': {'type': 'integer', 'minimum': 1}, 'r_image': {'type': 'integer', 'minimum': 1}},
        'required': ['feature', 'q_image', 'r_image']}}
    return {'type': 'object', 'additionalProperties': False, 'properties': {
        'item_id': {'type': 'string', 'pattern': '^PI_[0-9]{6}$'},
        'label': {'enum': ['SAME', 'DIFFERENT', 'AMBIGUOUS']},
        'ambiguity_cause': {'enum': ['NO_DISCRIMINATIVE_FEATURE', 'VIEW_MISMATCH', 'LOW_QUALITY', 'CONFLICTING_EVIDENCE', None]},
        'challenge_tags': {'type': 'array', 'uniqueItems': True, 'items': {'enum': ['distractor_present', 'near_identical_appearance', 'front_vs_back', 'large_viewpoint_change', 'different_lighting', 'motion_blur', 'partial_occlusion', 'poor_image_quality', 'none']}},
        'evidence_for_same': evidence, 'evidence_for_different': evidence,
        'confidence': {'enum': ['high', 'medium', 'low']}},
        'required': ['item_id', 'label', 'ambiguity_cause', 'challenge_tags', 'evidence_for_same', 'evidence_for_different', 'confidence']}


def prepare():
    from .builder import validate_dataset
    checks = validate_dataset()
    write(OUT / 'reports/dev_pilot_stage_a.json', checks)
    if checks['failed']:
        raise ValueError(checks['errors'])
    if PILOT_MANIFEST.exists():
        verify_pilot()
        return read(PILOT_MANIFEST)
    for p in [PROMPT_FILE.parent, PILOT_OUT, PILOT_ANNOTATIONS, OUT / 'runtime/pilot_empty_workspace']:
        p.mkdir(parents=True, exist_ok=True)
    exact = extract_prompt(PROMPT_SOURCE)
    PROMPT_FILE.write_text(exact, encoding='utf-8')
    write(PROMPT_FILE.parent / 'output_schema.json', schema())
    write(PROMPT_FILE.parent / 'prompt_manifest.json', {
        'prompt_version': 'pass_i_visual_annotator_v1', 'prompt_sha256': sha(PROMPT_FILE),
        'output_schema_version': SCHEMA_VERSION, 'output_schema_sha256': sha(PROMPT_FILE.parent / 'output_schema.json'),
        'CASE_CHANGE_POLICY': 'UNKNOWN', 'model_name': MODEL, 'model_revision': None,
        'revision_note': 'No snapshot/revision exposed by local model catalog.',
        'source_attachment_sha256': sha(PROMPT_SOURCE), 'prompt_extraction': 'exact text between user markers, framing newlines removed',
        'transport': 'Codex app-server; ChatGPT-authenticated; exact baseInstructions and fresh ephemeral thread per item',
        'official_model_documentation': 'https://developers.openai.com/api/docs/models/gpt-6.1-sol'})
    pairs = read_lines(OUT / 'manifests/pair_manifest.jsonl')
    chosen, blind = select_pilot(pairs)
    entries = [{'item_id': p['item_id'], 'split': 'dev', 'blind_first': p['item_id'] in blind,
                'evidence_package': p['evidence_package'], 'sampling_attributes': p['pair_generation']['sampling_attributes'],
                'video_id': p['video_id']} for p in chosen]
    manifest = {'schema': 'pass_i_dev_pilot_v1', 'seed': SEED, 'selection_count': len(entries),
        'selection_rule': 'seeded round-robin available DEV sampling attributes, recordings and evidence counts; independent of GPT correctness',
        'blind_first_fraction': .15, 'blind_first_count': len(blind),
        'CASE_CHANGE_POLICY': 'UNKNOWN', 'prompt_sha256': sha(PROMPT_FILE),
        'dataset_pair_manifest': ref(OUT / 'manifests/pair_manifest.jsonl'),
        'dataset_split_manifest': ref(OUT / 'manifests/session_split.json'), 'items': entries,
        'frozen_items_allowed': False}
    write(PILOT_MANIFEST, manifest)
    write(OUT / 'manifests/dev_pilot_hashes.json', {str(p.relative_to(ROOT).as_posix()): sha(p) for p in
        [PILOT_MANIFEST, PROMPT_FILE, PROMPT_FILE.parent / 'prompt_manifest.json', PROMPT_FILE.parent / 'output_schema.json']})
    # Separate pilot annotation store. No human annotation or GPT draft is created here.
    pilot_store = AnnotationStore(PILOT_ANNOTATIONS, prelabels_out=PILOT_OUT)
    pilot_store.export(len(entries))
    jsonl(PILOT_OUT / 'dev_pilot_raw_responses.jsonl', [])
    jsonl(PILOT_OUT / 'dev_pilot_prelabels.jsonl', [])
    return manifest


def verify_pilot():
    hashes = read(OUT / 'manifests/dev_pilot_hashes.json')
    for path, h in hashes.items():
        if sha(ROOT / path) != h:
            raise ValueError('Frozen prompt/pilot drift: ' + path)
    manifest = read(PILOT_MANIFEST)
    for refdata in [manifest['dataset_pair_manifest'], manifest['dataset_split_manifest']]:
        if sha(ROOT / refdata['path']) != refdata['sha256']:
            raise ValueError('Dataset/split changed')
    pairs = {p['item_id']: p for p in read_lines(OUT / 'manifests/pair_manifest.jsonl')}
    for p in manifest['items']:
        if p['split'] != 'dev' or pairs[p['item_id']]['split'] != 'dev':
            raise ValueError('Frozen item in pilot')
        if sha(ROOT / p['evidence_package']['path']) != p['evidence_package']['sha256']:
            raise ValueError('Evidence drift')
    return manifest


def public_item(entry):
    if entry['split'] != 'dev':
        raise ValueError('Only DEV pilot inputs are permitted')
    item = read(ROOT / entry['evidence_package']['path'])
    if item['item_id'] != entry['item_id']:
        raise ValueError('Wrong evidence item')
    build_request(item, PROMPT_FILE.read_text(encoding='utf-8'))
    return item


def parse_response(text, item):
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        return {'item_id': item['item_id'], 'status': 'PRELABEL_PARSE_FAILED', 'json_valid': False,
                'schema_valid': False, 'error': str(exc), 'parsed': None, 'needs_human_review': True}
    try:
        validate_prelabel(parsed, item)
        if parsed['item_id'] != item['item_id']:
            raise ValueError('Item mismatch')
    except (ValueError, KeyError, TypeError) as exc:
        return {'item_id': item['item_id'], 'status': 'PRELABEL_PARSE_FAILED', 'json_valid': True,
                'schema_valid': False, 'error': str(exc), 'parsed': parsed, 'needs_human_review': True}
    return {'item_id': item['item_id'], 'status': 'PRELABELED', 'json_valid': True, 'schema_valid': True,
            'error': None, 'parsed': parsed, 'needs_human_review': priority(parsed)}


def record_response(item, raw, text, runtime):
    rawpath = PILOT_OUT / f"{item['item_id']}.raw.json"
    with rawpath.open('x', encoding='utf-8') as f:
        json.dump({'item_id': item['item_id'], 'raw_response': raw, 'raw_text': text, 'runtime': runtime}, f, ensure_ascii=False, indent=2)
        f.flush()
        __import__('os').fsync(f.fileno())
    # Raw disk persistence is complete before any annotation JSON is parsed.
    raw_record = {'item_id': item['item_id'], 'raw_response': raw, 'raw_text': text, 'runtime': runtime}
    with (PILOT_OUT / 'dev_pilot_raw_responses.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(raw_record, ensure_ascii=False) + '\n')
    result = parse_response(text, item)
    value = {**result, 'valid': result['schema_valid'], 'raw_response_path': str(rawpath.relative_to(ROOT)),
             'raw_response_sha256': sha(rawpath), 'raw_text': text, 'validation_error': result['error']}
    write(PILOT_OUT / f"{item['item_id']}.json", value)
    with (PILOT_OUT / 'dev_pilot_prelabels.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')
    return result
