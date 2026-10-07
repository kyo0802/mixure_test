"""Blind, six-item Pilot 1 adjudication with separate decisions and delayed comparison."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .common import OUT, ROOT, read, resolve, sha

ITEM_IDS = ('PI_100004', 'PI_100006', 'PI_100007', 'PI_100011', 'PI_100019', 'PI_100020')
LABELS = ('SAME', 'DIFFERENT', 'AMBIGUOUS')
REPORT_NAME = 'PASS_I_PILOT1_DISAGREEMENT_ADJUDICATION.md'


def cases(out: Path = OUT):
    """Return only model-visible Pilot 1 image packages; no labels or QC data."""
    out = Path(out)
    manifest = read(out / 'manifests/dev_pilot_1_manifest.json')
    by_id = {entry['item_id']: entry for entry in manifest['items']}
    if not set(ITEM_IDS) <= set(by_id):
        raise ValueError('One or more fixed adjudication items are absent from Pilot 1')
    result = {}
    for item_id in ITEM_IDS:
        entry = by_id[item_id]
        if entry['split'] != 'dev':
            raise ValueError('Adjudication is DEV-only')
        evidence_path = resolve(entry['evidence_package']['path'])
        if sha(evidence_path) != entry['evidence_package']['sha256']:
            raise ValueError(f'Pilot 1 evidence changed: {item_id}')
        public = read(evidence_path)
        if set(public) != {'item_id', 'CASE_CHANGE_POLICY', 'images'} or public['item_id'] != item_id:
            raise ValueError(f'Invalid model-visible evidence: {item_id}')
        images = public['images']
        if not images or any(image['kind'] != 'phone_crop' or image['side'] not in {'Q', 'R'} for image in images):
            raise ValueError(f'Unexpected image type in Pilot 1 item: {item_id}')
        for image in images:
            if sha(resolve(image['path'])) != image['sha256']:
                raise ValueError(f'Pilot 1 crop changed: {item_id}/{image["image_id"]}')
        if not any(image['side'] == 'Q' for image in images) or not any(image['side'] == 'R' for image in images):
            raise ValueError(f'Missing Q or R crops: {item_id}')
        result[item_id] = public
    return result


class AdjudicationStore:
    def __init__(self, out: Path = OUT):
        self.out = Path(out)
        self.db = self.out / 'adjudication/pilot1_disagreements.sqlite3'
        self.db.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.db, timeout=30)) as con:
            con.execute('CREATE TABLE IF NOT EXISTS decisions (item_id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, item_id TEXT NOT NULL, data TEXT NOT NULL)')
            con.commit()

    def all(self):
        with closing(sqlite3.connect(self.db, timeout=30)) as con:
            return {item_id: json.loads(data) for item_id, data in con.execute('SELECT item_id,data FROM decisions')}

    def save(self, item_id: str, label: str, q_numbers: list[int], r_numbers: list[int],
             visible_feature: str, instance_reason: str, evidence_rule_acknowledged: bool,
             public: dict):
        if item_id not in ITEM_IDS or public['item_id'] != item_id:
            raise ValueError('Only the six fixed Pilot 1 disagreement items are allowed')
        if label not in LABELS:
            raise ValueError('Choose SAME, DIFFERENT, or AMBIGUOUS')
        available = {side: {image['number'] for image in public['images'] if image['side'] == side}
                     for side in ('Q', 'R')}
        for side, numbers in (('Q', q_numbers), ('R', r_numbers)):
            if len(numbers) != len(set(numbers)) or any(type(n) is not int or n not in available[side] for n in numbers):
                raise ValueError(f'Invalid {side} image number citation')
        visible_feature = visible_feature.strip()
        instance_reason = instance_reason.strip()
        if label in {'SAME', 'DIFFERENT'}:
            if not q_numbers or not r_numbers:
                raise ValueError('A decisive decision requires exact Q and R image numbers')
            if len(visible_feature) < 8 or len(instance_reason) < 12:
                raise ValueError('Describe the visible physical feature and why it supports physical-instance identity')
            if not evidence_rule_acknowledged:
                raise ValueError('Confirm the positive instance-specific or incompatible-evidence rule')
        else:
            q_numbers, r_numbers = [], []
            visible_feature = ''
            evidence_rule_acknowledged = False
        value = {'schema': 'pass_i_pilot1_blind_adjudication_v1', 'item_id': item_id,
                 'adjudicated_label': label, 'q_image_numbers': sorted(q_numbers),
                 'r_image_numbers': sorted(r_numbers), 'visible_physical_feature': visible_feature,
                 'instance_identity_explanation': instance_reason,
                 'evidence_rule_acknowledged': evidence_rule_acknowledged,
                 'evidence_sha256': sha(resolve(next(e['evidence_package']['path'] for e in
                     read(self.out / 'manifests/dev_pilot_1_manifest.json')['items'] if e['item_id'] == item_id))),
                 'updated_utc': datetime.now(timezone.utc).isoformat()}
        with closing(sqlite3.connect(self.db, timeout=30)) as con:
            con.execute('BEGIN IMMEDIATE')
            con.execute('INSERT INTO history(item_id,data) VALUES(?,?)', (item_id, json.dumps(value)))
            con.execute('INSERT OR REPLACE INTO decisions VALUES(?,?)', (item_id, json.dumps(value)))
            con.commit()
        return value


def write_completed_report(out: Path = OUT):
    """Reveal original human labels only after all six blind decisions exist."""
    out = Path(out)
    decisions = AdjudicationStore(out).all()
    if set(decisions) != set(ITEM_IDS):
        return None
    original_db = out / 'annotations/dev_pilot_1/annotations/annotations.sqlite3'
    with closing(sqlite3.connect(f'file:{original_db.as_posix()}?mode=ro', uri=True)) as con:
        originals = {item_id: json.loads(data) for item_id, data in
                     con.execute('SELECT item_id,data FROM annotations WHERE item_id IN (?,?,?,?,?,?)', ITEM_IDS)}
    if set(originals) != set(ITEM_IDS):
        raise ValueError('Original Pilot 1 human annotations are incomplete')
    lines = ['# Pilot 1 — Blind Disagreement Adjudication', '',
             'Status: **PASS_I_PILOT1_DISAGREEMENT_ADJUDICATION_COMPLETE**', '',
             'Six fixed DEV Pilot 1 disagreement pairs were adjudicated from the unchanged model-visible Q/R crops. Original human labels were read only after all six separate decisions were saved. GPT labels, QC metadata, tracking information, and physical GT were not shown in the adjudication UI.', '',
             '| Item | Original human | Adjudicated | Q numbers | R numbers | Visible feature | Sustained or changed |',
             '|---|---|---|---|---|---|---|']
    for item_id in ITEM_IDS:
        decision = decisions[item_id]
        original = originals[item_id]['human_label']
        if originals[item_id]['status'] != 'REVIEWED' or original not in LABELS:
            raise ValueError(f'Original human label unavailable: {item_id}')
        label = decision['adjudicated_label']
        state = 'SUSTAINED' if label == original else 'CHANGED'
        feature = decision['visible_physical_feature'].replace('|', '\\|').replace('\n', ' ')
        lines.append(f"| {item_id} | {original} | {label} | {', '.join(map(str, decision['q_image_numbers'])) or '—'} | {', '.join(map(str, decision['r_image_numbers'])) or '—'} | {feature or '—'} | {state} |")
    lines += ['', 'The adjudicated labels are separate from and do not overwrite the original Pilot 1 annotations.', '']
    path = out / 'reports' / REPORT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines), encoding='utf-8')
    return path
