"""Human-only DEV CandidateEpoch evidence quality control.

QC states never enter model-visible Pass I packages. No state is inferred from
image metrics, tracker IDs, or Pilot 0 outcomes.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .common import OUT, ROOT, read, read_lines, resolve, sha, write

CROP_STATES = ('KEEP_PRIMARY', 'KEEP_WEAK', 'DROP_WRONG_TARGET', 'DROP_NOT_PHONE',
               'DROP_TOO_CORRUPTED', 'DROP_DUPLICATE')
EPOCH_STATES = ('VALID', 'MIXED_IDENTITY', 'NO_USABLE_TARGET')
KEEP = {'KEEP_PRIMARY', 'KEEP_WEAK'}
QUEUE_PATH = OUT / 'evidence_qc/queue.json'
DB_PATH = OUT / 'evidence_qc/human_qc.sqlite3'
QC_VERSION = 'pass_i_evidence_qc_v1'


def _rank(seed: int, value: str):
    return hashlib.sha256(f'{seed}:{value}'.encode()).hexdigest()


def make_queue(out: Path = OUT, target: int = 120, seed: int = 297103):
    """Build once from metadata only; never use human identity labels or frozen rows."""
    out = Path(out)
    queue_path = out / 'evidence_qc/queue.json'
    inventory_path = out / 'manifests/candidate_epoch_inventory.jsonl'
    current_hash = sha(inventory_path)
    if queue_path.exists():
        existing = read(queue_path)
        if existing['inventory_sha256'] != current_hash:
            raise ValueError('CandidateEpoch inventory changed after QC queue freeze')
        return existing
    epochs = [e for e in read_lines(inventory_path) if e['split'] == 'dev']
    pairs = [p for p in read_lines(out / 'manifests/pair_manifest.jsonl') if p['split'] == 'dev']
    by_id = {e['epoch_id']: e for e in epochs}
    attributes = defaultdict(set)
    degree = Counter()
    for pair in pairs:
        for eid in (pair['query_epoch_id'], pair['reference_epoch_id']):
            if eid in by_id:
                degree[eid] += 1
                attributes[eid].update(pair['pair_generation']['sampling_attributes'])
    videos = defaultdict(list)
    for e in epochs:
        if e['clean_crops'] and degree[e['epoch_id']]:
            videos[e['video_id']].append(e)
    if not videos:
        raise ValueError('No eligible DEV CandidateEpochs')
    # Equal video coverage first; within each video rotate available evidence strata.
    quotas = {v: min(len(rows), target // len(videos)) for v, rows in videos.items()}
    remainder = target - sum(quotas.values())
    for v in sorted(videos, key=lambda x: _rank(seed, x)):
        if remainder and quotas[v] < len(videos[v]):
            quotas[v] += 1
            remainder -= 1
    categories = ('multi_crop', 'single_crop', 'small_crop', 'blurred_crop',
                  'same_object_candidate_pairs', 'different_object_candidate_pairs',
                  'near_identical_phone_pairs', 'long_gap_pairs', 'reappearance_cases', 'blur_low_quality_pairs')
    per_video = {}
    for video, rows in videos.items():
        def tags(e):
            crops = e['clean_crops']
            result = set(attributes[e['epoch_id']])
            result.add('multi_crop' if len(crops) > 1 else 'single_crop')
            if any(min(c['width'], c['height']) < 48 for c in crops):
                result.add('small_crop')
            selected = set(e['selected_observation_ids'])
            if any(o.get('quality', {}).get('blur_laplacian_variance', 999) < 30 for o in e['source_observations'] if o['observation_id'] in selected):
                result.add('blurred_crop')
            return result
        ordered = sorted(rows, key=lambda e: (-degree[e['epoch_id']], _rank(seed, e['epoch_id'])))
        chosen, seen = [], set()
        for category in categories:
            for e in ordered:
                if e['epoch_id'] not in seen and category in tags(e):
                    chosen.append(e); seen.add(e['epoch_id'])
                    break
            if len(chosen) >= quotas[video]:
                break
        for e in ordered:
            if len(chosen) >= quotas[video]:
                break
            if e['epoch_id'] not in seen:
                chosen.append(e); seen.add(e['epoch_id'])
        per_video[video] = chosen
    ordered_queue = []
    for i in range(max(map(len, per_video.values()))):
        for video in sorted(per_video, key=lambda x: _rank(seed, x)):
            if i < len(per_video[video]):
                ordered_queue.append(per_video[video][i])
    records = []
    for i, e in enumerate(ordered_queue, 1):
        records.append({'position': i, 'epoch_id': e['epoch_id'], 'session_id': e['session_id'],
                        'video_id': e['video_id'], 'split': 'dev',
                        'selected_crop_count': len(e['clean_crops']),
                        'crop_min_dimensions': [[c['width'], c['height']] for c in e['clean_crops']],
                        'pair_sampling_attributes': sorted(attributes[e['epoch_id']]),
                        'existing_dev_pair_degree': degree[e['epoch_id']]})
    manifest = {'schema': 'pass_i_evidence_qc_queue_v1', 'seed': seed, 'target': target,
                'selection_count': len(records), 'inventory_sha256': current_hash,
                'selection_rule': 'equal video coverage; rotate metadata-derived crop/pair strata; fill by DEV pair degree and seeded hash; no identity gold',
                'items': records}
    write(queue_path, manifest)
    return manifest


def extend_queue(out: Path = OUT, additional: int = 30):
    """Add deterministic unreviewed DEV epochs when clean-pair supply is insufficient."""
    out = Path(out)
    manifest = make_queue(out)
    chosen = {e['epoch_id'] for e in manifest['items']}
    remaining = [e for e in read_lines(out / 'manifests/candidate_epoch_inventory.jsonl')
                 if e['split'] == 'dev' and e['clean_crops'] and e['epoch_id'] not in chosen]
    if not remaining:
        return manifest
    remaining.sort(key=lambda e: _rank(manifest['seed'], e['epoch_id']))
    buckets = defaultdict(list)
    for e in remaining:
        buckets[e['video_id']].append(e)
    selected = []
    while len(selected) < additional and any(buckets.values()):
        for video in sorted(buckets, key=lambda x: _rank(manifest['seed'], x)):
            if buckets[video]:
                selected.append(buckets[video].pop(0))
                if len(selected) >= additional:
                    break
    for e in selected:
        manifest['items'].append({'position': len(manifest['items']) + 1,
                                  'epoch_id': e['epoch_id'], 'session_id': e['session_id'],
                                  'video_id': e['video_id'], 'split': 'dev',
                                  'selected_crop_count': len(e['clean_crops']),
                                  'crop_min_dimensions': [[c['width'], c['height']] for c in e['clean_crops']],
                                  'pair_sampling_attributes': [],
                                  'existing_dev_pair_degree': 0,
                                  'extension_reason': 'insufficient QC-valid fresh pairs'})
    manifest['selection_count'] = len(manifest['items'])
    manifest['extensions'] = manifest.get('extensions', []) + [{'added': len(selected), 'rule': 'seeded DEV-only round robin by video'}]
    write(out / 'evidence_qc/queue.json', manifest)
    return manifest


class QCStore:
    def __init__(self, out: Path = OUT):
        self.out = Path(out)
        self.queue = make_queue(self.out)
        self.db = self.out / 'evidence_qc/human_qc.sqlite3'
        self.db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db) as con:
            con.execute('CREATE TABLE IF NOT EXISTS epoch_reviews (epoch_id TEXT PRIMARY KEY, data TEXT NOT NULL)')

    def all(self):
        with sqlite3.connect(self.db) as con:
            return {k: json.loads(v) for k, v in con.execute('SELECT epoch_id,data FROM epoch_reviews')}

    def save(self, epoch_id: str, crop_states: dict[str, str], epoch_state: str, note: str = ''):
        allowed = {r['epoch_id'] for r in self.queue['items']}
        if epoch_id not in allowed:
            raise ValueError('Only queued DEV CandidateEpochs may be reviewed')
        inventory = {e['epoch_id']: e for e in read_lines(self.out / 'manifests/candidate_epoch_inventory.jsonl') if e['split'] == 'dev'}
        epoch = inventory[epoch_id]
        expected = {c['observation_id'] for c in epoch['clean_crops']}
        if set(crop_states) != expected or any(state not in CROP_STATES for state in crop_states.values()):
            raise ValueError('Exactly one valid QC state is required for each selected crop')
        if epoch_state not in EPOCH_STATES:
            raise ValueError('One valid CandidateEpoch QC state is required')
        kept = [oid for oid, state in crop_states.items() if state in KEEP]
        if epoch_state == 'VALID' and not kept:
            raise ValueError('VALID requires at least one verified target crop')
        if epoch_state == 'NO_USABLE_TARGET' and kept:
            raise ValueError('NO_USABLE_TARGET cannot have a kept crop')
        value = {'schema': QC_VERSION, 'epoch_id': epoch_id, 'split': 'dev',
                 'crop_states': crop_states, 'epoch_state': epoch_state, 'human_note': note.strip(),
                 'updated_utc': datetime.now(timezone.utc).isoformat(),
                 'inventory_sha256': self.queue['inventory_sha256']}
        with sqlite3.connect(self.db, timeout=30) as con:
            con.execute('INSERT OR REPLACE INTO epoch_reviews VALUES (?,?)', (epoch_id, json.dumps(value)))
        return value


def report(out: Path = OUT):
    out = Path(out)
    queue = make_queue(out)
    reviews = QCStore(out).all()
    queued = {r['epoch_id'] for r in queue['items']}
    reviewed = [r for eid, r in reviews.items() if eid in queued]
    inventory = {e['epoch_id']: e for e in read_lines(out / 'manifests/candidate_epoch_inventory.jsonl') if e['split'] == 'dev'}
    for entry in queue['items']:
        eid = entry['epoch_id']
        if eid not in reviews:
            continue
        epoch = inventory[eid]
        expected = {c['observation_id'] for c in epoch['clean_crops']}
        actual = reviews[eid]['crop_states']
        if set(actual) != expected or any(s not in CROP_STATES for s in actual.values()):
            raise ValueError(f'Incomplete/invalid crop QC: {eid}')
        state = reviews[eid]['epoch_state']
        if state not in EPOCH_STATES or reviews[eid].get('split') != 'dev':
            raise ValueError(f'Invalid epoch QC: {eid}')
        kept = sum(s in KEEP for s in actual.values())
        if state == 'VALID' and kept == 0 or state == 'NO_USABLE_TARGET' and kept:
            raise ValueError(f'Inconsistent epoch/crop QC: {eid}')
    crop_counts = Counter(state for r in reviewed for state in r['crop_states'].values())
    epoch_counts = Counter(r['epoch_state'] for r in reviewed)
    pairs = [p for p in read_lines(out / 'manifests/pair_manifest.jsonl') if p['split'] == 'dev']
    invalid = sum(any(reviews.get(eid, {}).get('epoch_state') in {'MIXED_IDENTITY', 'NO_USABLE_TARGET'}
                      for eid in (p['query_epoch_id'], p['reference_epoch_id'])) for p in pairs)
    clean = sum(all(reviews.get(eid, {}).get('epoch_state') == 'VALID'
                    for eid in (p['query_epoch_id'], p['reference_epoch_id'])) for p in pairs)
    from .pilot1 import clean_pool
    clean_epochs, fresh_pool = clean_pool(out)
    quality = Counter(p['pair_quality'] for p in fresh_pool)
    pilot1_file = out / 'manifests/dev_pilot_1_manifest.json'
    pilot1_ready = pilot1_file.exists() and all(
        (out / 'prelabels/dev_pilot_1' / f"{item['item_id']}.json").exists()
        for item in read(pilot1_file)['items'])
    status = ('PASS_I_PILOT1_READY_FOR_HUMAN_REVIEW' if pilot1_ready else
              'PASS_I_EVIDENCE_QC_COMPLETE' if len(reviewed) == len(queued) else
              'PASS_I_EVIDENCE_QC_WAITING_FOR_HUMAN')
    lines = ['# Pass I Evidence QC Report', '',
             f'Status: **{status}**', '',
             f"DEV CandidateEpochs queued: {len(queued)}; human-QC reviewed: {len(reviewed)}.",
             f"Source inventory SHA-256: `{queue['inventory_sha256']}`.",
             'Pilot 0 designation: `DEV_PILOT_0_DATA_QUALITY_DISCOVERY`. Its inputs, GPT responses, annotations, and audit are preserved separately. Frozen data is outside this queue.', '',
             '## Crop QC', '', '| State | Count |', '|---|---:|']
    for state in CROP_STATES:
        lines.append(f'| {state} | {crop_counts[state]} |')
    lines += ['', '## CandidateEpoch QC', '', '| State | Count |', '|---|---:|']
    for state in EPOCH_STATES:
        lines.append(f'| {state} | {epoch_counts[state]} |')
    n = len(reviewed)
    def fraction(value):
        return f'{value}/{n} ({100 * value / n:.1f}%)' if n else 'not estimable before human QC'
    wrong_crop_count = crop_counts['DROP_WRONG_TARGET']
    total_crops = sum(crop_counts.values())
    lines += ['', '## Observed quality rates among reviewed epochs', '',
              f"- Wrong-target crop incidence: {fraction(sum('DROP_WRONG_TARGET' in r['crop_states'].values() for r in reviewed))}.",
              f"- Confirmed wrong-target crops: {wrong_crop_count}/{total_crops} ({100 * wrong_crop_count / total_crops:.1f}%) of selected crops." if total_crops else '- Confirmed wrong-target crops: not estimable.',
              f"- Non-phone crop incidence: {fraction(sum('DROP_NOT_PHONE' in r['crop_states'].values() for r in reviewed))}.",
              f"- Mixed-identity epoch rate: {fraction(epoch_counts['MIXED_IDENTITY'])}.",
              f"- No-usable-target epoch rate: {fraction(epoch_counts['NO_USABLE_TARGET'])}.", '',
              'KEEP_WEAK is retained as legitimate target evidence. Blur, occlusion, difficult views, visual similarity, and identity ambiguity alone are not treated as upstream QC errors.', '',
              '## DEV pool readiness', '',
              f"- QC-valid CandidateEpochs currently available: {len(clean_epochs)}.",
              f"- Kept target crops in VALID epochs: {sum(len(e['kept_crops']) for e in clean_epochs.values())}; model-primary selections (1–3 per epoch): {sum(len(e['selected_model_crops']) for e in clean_epochs.values())}.",
              f'- Original DEV pairs with two reviewed VALID sides: {clean}.',
              f'- Original DEV pairs with at least one reviewed invalid side: {invalid}.',
              f"- Fresh QC-valid DEV pairs excluding Pilot 0: {len(fresh_pool)}.",
              f"- PRIMARY_VALID pairs: {quality['PRIMARY_VALID']}.",
              f"- HARD_VALID pairs: {quality['HARD_VALID']}.",
              f'- INVALID_PAIR original DEV pairs with known reviewed invalid side: {invalid}.',
              '- Pilot 1 selection and GPT inference: see independent Pilot 1 manifest/report.', '',
              '## Per-CandidateEpoch crop accounting', '',
              '“Original crops” counts selected evidence crops before QC; “source observations” includes unselected raw observations from the CandidateEpoch.', '',
              '| CandidateEpoch | Video | Epoch QC | Source observations | Original crops | Retained | Primary | Weak | Dropped |',
              '|---|---|---|---:|---:|---:|---:|---:|']
    for entry in queue['items']:
        eid = entry['epoch_id']
        epoch = inventory[eid]
        review = reviews.get(eid)
        states = list(review['crop_states'].values()) if review else []
        primary, weak = states.count('KEEP_PRIMARY'), states.count('KEEP_WEAK')
        dropped = sum(s.startswith('DROP_') for s in states)
        lines.append(f"| `{eid}` | {epoch['video_id']} | {review['epoch_state'] if review else 'UNREVIEWED'} | {len(epoch['source_observations'])} | {len(epoch['clean_crops'])} | {primary + weak} | {primary} | {weak} | {dropped} |")
    lines += ['', 'These are observed rates in the selected DEV QC queue, not estimates for all 690 CandidateEpochs. No human QC state was inferred automatically.']
    path = out / 'reports/PASS_I_EVIDENCE_QC_REPORT.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path
