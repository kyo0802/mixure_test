"""QC-gated DEV Pilot 1 preparation; no inference or human labels are generated."""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from .adapter import build_request
from .builder import sampling
from .common import OUT, ROOT, read, read_lines, ref, resolve, sha, write, jsonl
from .evidence_qc import KEEP, QCStore, extend_queue
from .pilot import PROMPT_FILE, verify_pilot

SEED = 297104
PILOT1_MANIFEST = OUT / 'manifests/dev_pilot_1_manifest.json'


def _rank(value: str):
    return hashlib.sha256(f'{SEED}:{value}'.encode()).hexdigest()


def _pick_crops(epoch: dict, review: dict):
    observations = {r['observation_id']: r for r in epoch['source_observations']}
    kept = []
    for crop in epoch['clean_crops']:
        oid = crop['observation_id']
        state = review['crop_states'][oid]
        if state not in KEEP:
            continue
        original = observations[oid]
        path = resolve(original['raw_crop_path'])
        if not path.is_file() or sha(path) != original['raw_crop_sha256']:
            raise ValueError(f'Original crop changed: {epoch["epoch_id"]}/{oid}')
        if crop['sha256'] != original['raw_crop_sha256']:
            raise ValueError(f'Copied/raw crop mismatch: {epoch["epoch_id"]}/{oid}')
        kept.append({'observation_id': oid, 'path': original['raw_crop_path'],
                     'sha256': original['raw_crop_sha256'], 'source_frame': original['frame'],
                     'time': original['time'], 'dimensions': [crop['width'], crop['height']],
                     'qc_state': state, 'qc_timestamp': review['updated_utc'],
                     'qc_version': review['schema'], 'dhash': original['quality']['dhash'],
                     'blur_laplacian_variance': original['quality']['blur_laplacian_variance']})
    if not kept:
        raise ValueError(f'VALID epoch has no kept crop: {epoch["epoch_id"]}')
    # Rank useful evidence first, then add frame/appearance diversity. Never alter pixels.
    selected = []
    pool = kept.copy()
    while pool and len(selected) < 3:
        def rank(c):
            diversity = min(((int(c['dhash'], 16) ^ int(s['dhash'], 16)).bit_count() for s in selected), default=64)
            spacing = min((abs(c['time'] - s['time']) for s in selected), default=999)
            size = min(c['dimensions'])
            return (c['qc_state'] == 'KEEP_PRIMARY', min(diversity, 32), min(spacing, 10),
                    math.log1p(size), math.log1p(c['blur_laplacian_variance']), _rank(c['observation_id']))
        best = max(pool, key=rank)
        selected.append(best)
        pool.remove(best)
    return kept, sorted(selected, key=lambda c: (c['source_frame'], c['observation_id']))


def clean_pool(out: Path = OUT):
    out = Path(out)
    store = QCStore(out)
    reviews = store.all()
    allowed = {e['epoch_id'] for e in store.queue['items']}
    inventory = {e['epoch_id']: e for e in read_lines(out / 'manifests/candidate_epoch_inventory.jsonl') if e['split'] == 'dev'}
    valid = {}
    for eid, review in sorted(reviews.items()):
        if eid not in allowed or review['epoch_state'] != 'VALID':
            continue
        epoch = inventory[eid]
        kept, selected = _pick_crops(epoch, review)
        valid[eid] = {'epoch_id': eid, 'session_id': epoch['session_id'], 'video_id': epoch['video_id'],
                      'split': 'dev', 'epoch_qc_state': 'VALID', 'qc_timestamp': review['updated_utc'],
                      'qc_version': review['schema'], 'kept_crops': kept,
                      'selected_model_crops': selected,
                      'has_primary': any(c['qc_state'] == 'KEEP_PRIMARY' for c in kept)}
    pilot0 = verify_pilot()
    original_pairs = {p['item_id']: p for p in read_lines(out / 'manifests/pair_manifest.jsonl') if p['split'] == 'dev'}
    excluded_combos = {frozenset((original_pairs[e['item_id']]['query_epoch_id'],
                                  original_pairs[e['item_id']]['reference_epoch_id'])) for e in pilot0['items']}
    by_video = defaultdict(list)
    for eid, clean in valid.items():
        by_video[clean['video_id']].append(eid)
    pool = []
    config = read(out / 'config.json')
    for video, ids in sorted(by_video.items()):
        for qid, rid in itertools.combinations(sorted(ids), 2):
            if frozenset((qid, rid)) in excluded_combos:
                continue
            q, r = valid[qid], valid[rid]
            q_orig, r_orig = inventory[qid], inventory[rid]
            if q['session_id'] != r['session_id']:
                continue
            filtered = []
            for original, clean in ((q_orig, q), (r_orig, r)):
                c = dict(original)
                selected = {x['observation_id'] for x in clean['selected_model_crops']}
                c['source_observations'] = [o for o in original['source_observations'] if o['observation_id'] in selected]
                c['selected_observation_ids'] = sorted(selected)
                filtered.append(c)
            attributes = sampling(filtered[0], filtered[1], config)['sampling_attributes']
            pool.append({'query_epoch_id': qid, 'reference_epoch_id': rid,
                         'video_id': video, 'session_id': q['session_id'], 'split': 'dev',
                         'pair_quality': 'PRIMARY_VALID' if q['has_primary'] and r['has_primary'] else 'HARD_VALID',
                         'sampling_attributes': attributes})
    return valid, pool


def write_private_source_trace(out: Path = OUT):
    """Record source provenance beside cleaned evidence, never in GPT input."""
    out = Path(out)
    valid, _ = clean_pool(out)
    inventory = {e['epoch_id']: e for e in read_lines(out / 'manifests/candidate_epoch_inventory.jsonl') if e['split'] == 'dev'}
    rows = []
    for eid, clean in sorted(valid.items()):
        original = inventory[eid]
        by_oid = {o['observation_id']: o for o in original['source_observations']}
        kept = []
        for crop in clean['kept_crops']:
            source = by_oid[crop['observation_id']]
            kept.append({'observation_id': crop['observation_id'], 'original_crop_path': crop['path'],
                         'original_crop_sha256': crop['sha256'], 'source_frame': source['frame'],
                         'source_frame_sha256': source['raw_image_sha256'], 'source_bbox': source['bbox'],
                         'source_local_track_id': source['local_track_id'],
                         'qc_state': crop['qc_state'], 'qc_timestamp': crop['qc_timestamp'],
                         'qc_version': crop['qc_version']})
        rows.append({'epoch_id': eid, 'video_id': clean['video_id'], 'session_id': clean['session_id'],
                     'split': 'dev', 'epoch_qc_state': 'VALID', 'kept_source_crops': kept})
    path = out / 'pilot1/clean_epoch_source_trace.jsonl'
    jsonl(path, rows)
    return path


def prepare_pilot1(out: Path = OUT, minimum_reviews: int = 100):
    out = Path(out)
    if PILOT1_MANIFEST.exists():
        return read(PILOT1_MANIFEST)
    store = QCStore(out)
    reviewed = len(store.all())
    if reviewed < minimum_reviews:
        raise ValueError(f'Human Evidence QC checkpoint: {reviewed}/{minimum_reviews} reviewed epochs')
    pilot0 = verify_pilot()
    if sha(PROMPT_FILE) != pilot0['prompt_sha256']:
        raise ValueError('Pilot 0 prompt hash mismatch; STOP before Pilot 1')
    valid, pool = clean_pool(out)
    if len(pool) < 40:
        if reviewed == len(store.queue['items']):
            extended = extend_queue(out)
            raise ValueError(f'Only {len(pool)} clean fresh DEV pairs; QC queue extended to {extended["selection_count"]}, complete new human QC')
        raise ValueError(f'Only {len(pool)} clean fresh DEV pairs; complete additional human QC')
    by_quality = {quality: [p for p in pool if p['pair_quality'] == quality]
                  for quality in ('PRIMARY_VALID', 'HARD_VALID')}
    # Prefer 30 primary + 10 hard when supported; never invent a quality stratum.
    primary_target = min(30, len(by_quality['PRIMARY_VALID']))
    hard_target = min(40 - primary_target, len(by_quality['HARD_VALID']))
    primary_target = min(40 - hard_target, len(by_quality['PRIMARY_VALID']))
    if primary_target + hard_target < 40:
        hard_target = min(40 - primary_target, len(by_quality['HARD_VALID']))
    selected = []
    video_counts, tag_counts = Counter(), Counter()
    for quality, target in (('PRIMARY_VALID', primary_target), ('HARD_VALID', hard_target)):
        remaining = by_quality[quality].copy()
        for _ in range(target):
            def balance(p):
                tags = p['sampling_attributes']
                tag_load = sum(tag_counts[tag] for tag in tags) / len(tags) if tags else 1 + sum(tag_counts.values())
                return (video_counts[p['video_id']], tag_load,
                        _rank(p['query_epoch_id'] + '|' + p['reference_epoch_id']))
            best = min(remaining, key=balance)
            remaining.remove(best)
            selected.append(best)
            video_counts[best['video_id']] += 1
            tag_counts.update(best['sampling_attributes'])
    if len(selected) != 40:
        raise ValueError('Insufficient fresh QC-valid pairs after quality balancing')
    selected.sort(key=lambda p: (p['video_id'], _rank(p['query_epoch_id'] + '|' + p['reference_epoch_id'])))
    pair_dir = out / 'pilot1'
    for eid, clean in valid.items():
        token = hashlib.sha256(eid.encode()).hexdigest()[:20]
        path = pair_dir / 'clean_epochs' / token / 'evidence.json'
        write(path, {'schema': 'pass_i_qc_clean_epoch_evidence_v1',
                     'images': [{'number': n, 'path': crop['path'], 'sha256': crop['sha256']}
                                for n, crop in enumerate(clean['kept_crops'], 1)]})
        clean['rebuilt_evidence_package'] = ref(path)
    entries = []
    for i, pair in enumerate(selected, 1):
        item_id = f'PI_{100000 + i:06d}'
        images = []
        for side, eid in (('Q', pair['query_epoch_id']), ('R', pair['reference_epoch_id'])):
            for n, crop in enumerate(valid[eid]['selected_model_crops'], 1):
                images.append({'image_id': f'{side}-{n}', 'side': side, 'kind': 'phone_crop',
                               'number': n, 'path': crop['path'], 'sha256': crop['sha256']})
        public = {'item_id': item_id, 'CASE_CHANGE_POLICY': 'UNKNOWN', 'images': images}
        build_request(public, PROMPT_FILE.read_text(encoding='utf-8'))
        evidence_path = pair_dir / 'items' / item_id / 'evidence.json'
        write(evidence_path, public)
        entries.append({**pair, 'item_id': item_id, 'evidence_package': ref(evidence_path),
                        'blind_first': False})
    blind = {p['item_id'] for p in sorted(entries, key=lambda p: _rank('blind:' + p['item_id']))[:6]}
    for entry in entries:
        entry['blind_first'] = entry['item_id'] in blind
    jsonl(pair_dir / 'clean_epochs.jsonl', valid.values())
    jsonl(pair_dir / 'clean_dev_pair_pool.jsonl', pool)
    write_private_source_trace(out)
    manifest = {'schema': 'pass_i_dev_pilot_1_v1', 'selection_count': 40, 'seed': SEED,
                'prompt_sha256': sha(PROMPT_FILE), 'CASE_CHANGE_POLICY': 'UNKNOWN',
                'qc_queue_sha256': sha(out / 'evidence_qc/queue.json'),
                'qc_reviewed_epochs': reviewed, 'clean_dev_pair_pool_count': len(pool),
                'blind_first_count': 6, 'items': entries,
                'pilot0_pair_exclusion_count': len(pilot0['items']), 'frozen_items_allowed': False}
    write(PILOT1_MANIFEST, manifest)
    write(out / 'manifests/dev_pilot_1_hashes.json', {'manifest_sha256': sha(PILOT1_MANIFEST),
                                                      'prompt_sha256': sha(PROMPT_FILE)})
    return manifest
