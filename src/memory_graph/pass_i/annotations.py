"""Human visual gold, immutable GPT drafts and physical GT are separate stores."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .common import OUT, read, write, jsonl

LABELS = {'SAME', 'DIFFERENT', 'AMBIGUOUS'}
CAUSES = {'NO_DISCRIMINATIVE_FEATURE', 'VIEW_MISMATCH', 'LOW_QUALITY', 'CONFLICTING_EVIDENCE'}
TAGS = ['distractor_present', 'near_identical_appearance', 'front_vs_back', 'large_viewpoint_change',
        'different_lighting', 'motion_blur', 'partial_occlusion', 'poor_image_quality', 'none']
EXCLUSIONS = ['wrong_crop', 'wrong_target', 'not_phone', 'mixed_identity', 'wrong_epoch',
              'missing_image', 'duplicate_pair', 'corrupt_image', 'other']


def validate_annotation(a):
    if not a.get('item_id'):
        raise ValueError('item_id is required')
    if a['status'] == 'EXCLUDED':
        if a.get('exclude_reason') not in EXCLUSIONS or a.get('human_label') is not None or a.get('human_ambiguity_cause') is not None or a.get('accepted_gpt_prelabel'):
            raise ValueError('Excluded item requires one valid reason and no identity label')
    elif a['status'] == 'REVIEWED':
        if a.get('human_label') not in LABELS or a.get('exclude_reason') is not None:
            raise ValueError('Reviewed item requires a label and no exclusion reason')
        cause = a.get('human_ambiguity_cause')
        if a['human_label'] == 'AMBIGUOUS':
            if not isinstance(cause, str) or cause not in CAUSES:
                raise ValueError('AMBIGUOUS requires exactly one valid cause')
        elif cause is not None:
            raise ValueError('Non-AMBIGUOUS cause must be null')
    else:
        raise ValueError('Invalid status')
    tags = a.get('human_challenge_tags', [])
    if not isinstance(tags, list) or any(t not in TAGS for t in tags) or len(set(tags)) != len(tags) or ('none' in tags and len(tags) > 1):
        raise ValueError('Invalid challenge tags; none must stand alone')
    return a


def validate_prelabel(p, item):
    if not isinstance(p, dict) or set(p) != {'item_id', 'label', 'ambiguity_cause', 'challenge_tags', 'evidence_for_same', 'evidence_for_different', 'confidence'}:
        raise ValueError('Invalid GPT annotation schema')
    if p['item_id'] != item['item_id'] or p['confidence'] not in {'high', 'medium', 'low'}:
        raise ValueError('Invalid item/confidence')
    validate_annotation({'item_id': p['item_id'], 'status': 'REVIEWED', 'human_label': p['label'],
        'human_ambiguity_cause': p['ambiguity_cause'], 'human_challenge_tags': p['challenge_tags'], 'exclude_reason': None})
    for field in ['evidence_for_same', 'evidence_for_different']:
        if not isinstance(p[field], list):
            raise ValueError('Evidence must be an array')
        for e in p[field]:
            if not isinstance(e, dict) or set(e) != {'feature', 'q_image', 'r_image'} or not isinstance(e['feature'], str) or not e['feature'].strip():
                raise ValueError('Invalid evidence entry')
            for side, key in [('Q', 'q_image'), ('R', 'r_image')]:
                nums = {i['number'] for i in item['images'] if i['side'] == side and i['kind'] == 'phone_crop'}
                if type(e[key]) is not int or e[key] not in nums:
                    raise ValueError('Evidence cites a missing phone crop')
    if p['label'] == 'SAME' and (not p['evidence_for_same'] or p['evidence_for_different']):
        raise ValueError('SAME requires matching evidence and no contradiction')
    if p['label'] == 'DIFFERENT' and not p['evidence_for_different']:
        raise ValueError('DIFFERENT requires contradictory evidence')
    if p['label'] == 'AMBIGUOUS' and p['evidence_for_same'] and p['evidence_for_different'] and p['ambiguity_cause'] != 'CONFLICTING_EVIDENCE':
        raise ValueError('Conflicting evidence requires CONFLICTING_EVIDENCE')
    return p


class AnnotationStore:
    def __init__(self, out=OUT, prelabels_out=None):
        self.out = Path(out)
        self.prelabels_out = Path(prelabels_out) if prelabels_out is not None else self.out / 'prelabels'
        (self.out / 'annotations').mkdir(parents=True, exist_ok=True)
        self.prelabels_out.mkdir(parents=True, exist_ok=True)
        self.db = self.out / 'annotations/annotations.sqlite3'
        with self.connect() as con:
            con.execute('CREATE TABLE IF NOT EXISTS annotations (item_id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS physical (item_id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, item_id TEXT, data TEXT NOT NULL)')

    def connect(self):
        return sqlite3.connect(self.db, timeout=30)

    def all(self, table='annotations'):
        if table not in {'annotations', 'physical'}:
            raise ValueError('Invalid table')
        with self.connect() as con:
            return {k: json.loads(v) for k, v in con.execute(f'SELECT item_id,data FROM {table} ORDER BY item_id')}

    def save(self, value, total=0):
        value = {**validate_annotation(value), 'updated_utc': datetime.now(timezone.utc).isoformat()}
        if value.get('accepted_gpt_prelabel'):
            raw = self.prelabel(value['item_id'])
            if not raw or not raw['valid']:
                raise ValueError('Cannot accept missing/invalid GPT prelabel')
            p = raw['parsed']
            if (value['human_label'], value['human_ambiguity_cause'], value['human_challenge_tags']) != (p['label'], p['ambiguity_cause'], p['challenge_tags']):
                raise ValueError('Accepted GPT fields must match the original draft')
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            previous = con.execute('SELECT data FROM annotations WHERE item_id=?', (value['item_id'],)).fetchone()
            # Keep the initial blind judgment even if a later review overwrites final fields.
            if previous:
                old = json.loads(previous[0])
                for k, v in old.items():
                    if k.startswith('human_blind_'):
                        value[k] = v
            con.execute('INSERT INTO history(item_id,data) VALUES(?,?)', (value['item_id'], json.dumps(value)))
            con.execute('INSERT OR REPLACE INTO annotations VALUES(?,?)', (value['item_id'], json.dumps(value)))
            self._export(con, total)
        return value

    def save_physical(self, item_id, identity, source, total=0):
        if identity not in {'SAME', 'DIFFERENT', 'UNKNOWN'} or not source.strip():
            raise ValueError('Physical GT requires a label and provenance')
        value = {'item_id': item_id, 'physical_identity': identity, 'physical_identity_source': source,
                 'physical_gt_reviewed': True, 'updated_utc': datetime.now(timezone.utc).isoformat()}
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            con.execute('INSERT OR REPLACE INTO physical VALUES(?,?)', (item_id, json.dumps(value)))
            self._export(con, total)
        return value

    def _export(self, con, total):
        annotations = [json.loads(x[0]) for x in con.execute('SELECT data FROM annotations ORDER BY item_id')]
        physical = [json.loads(x[0]) for x in con.execute('SELECT data FROM physical ORDER BY item_id')]
        jsonl(self.out / 'annotations/human_annotations.jsonl', annotations)
        excluded = [a for a in annotations if a['status'] == 'EXCLUDED']
        jsonl(self.out / 'annotations/excluded_items.jsonl', excluded)
        jsonl(self.out / 'annotations/physical_gt.jsonl', physical)
        write(self.out / 'annotations/annotation_progress.json', {'total_items': total,
            'reviewed': sum(a['status'] == 'REVIEWED' for a in annotations), 'excluded': len(excluded),
            'unreviewed': max(0, total - len(annotations)), 'physical_gt_reviewed': len(physical),
            'gpt_prelabels': sum(__import__('re').fullmatch(r'PI_\d{6}', p.stem) is not None for p in self.prelabels_out.glob('PI_*.json'))})

    def export(self, total=0):
        with self.connect() as con:
            con.execute('BEGIN IMMEDIATE')
            self._export(con, total)

    def gold(self):
        return [a for a in self.all().values() if a['status'] == 'REVIEWED']

    def has_prelabel(self, item_id):
        return (self.prelabels_out / f'{item_id}.json').exists()

    def prelabel(self, item_id):
        path = self.prelabels_out / f'{item_id}.json'
        return read(path) if path.exists() else None

    def save_prelabel(self, item, raw, text, parsed):
        try:
            validate_prelabel(parsed, item)
            valid, error = True, None
        except (ValueError, KeyError, TypeError) as exc:
            valid, error = False, str(exc)
        value = {'item_id': item['item_id'], 'raw_response': raw, 'raw_text': text, 'parsed': parsed,
                 'valid': valid, 'validation_error': error}
        path = self.prelabels_out / f"{item['item_id']}.json"
        # Exclusive create: never overwrite the original response.
        with path.open('x', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
        return value
