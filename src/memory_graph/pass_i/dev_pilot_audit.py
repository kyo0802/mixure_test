"""Read-only DEV pilot comparison plus separate, human-selected disagreement flags."""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from .common import OUT, read, resolve

LABELS = ('SAME', 'DIFFERENT', 'AMBIGUOUS')
FLAGS = ('UNREVIEWED', 'MODEL_ERROR', 'EVIDENCE_INSUFFICIENT', 'DATA_ERROR')


def _pilot_rows(out: Path):
    manifest = read(out / 'manifests/dev_pilot_manifest.json')
    entries = manifest['items']
    if len(entries) != 40 or len({e['item_id'] for e in entries}) != 40:
        raise ValueError('Expected the fixed 40-item pilot manifest')
    db = out / 'annotations/dev_pilot/annotations/annotations.sqlite3'
    with sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True) as con:
        human = {item_id: json.loads(data) for item_id, data in con.execute('SELECT item_id,data FROM annotations')}
    rows = []
    for entry in entries:
        item_id = entry['item_id']
        if entry['split'] != 'dev':
            raise ValueError(f'Non-DEV item in pilot: {item_id}')
        draft = read(out / 'prelabels/dev_pilot' / f'{item_id}.json')
        if not draft.get('valid') or draft.get('item_id') != item_id:
            raise ValueError(f'Missing/invalid GPT draft: {item_id}')
        annotation = human.get(item_id)
        if annotation and annotation['status'] not in {'REVIEWED', 'EXCLUDED'}:
            raise ValueError(f'Invalid human status: {item_id}')
        rows.append({'item_id': item_id, 'entry': entry, 'gpt': draft['parsed'], 'human': annotation})
    return rows


def _image_metadata(out: Path, entry: dict):
    evidence = read(resolve(entry['evidence_package']['path']))
    result = {}
    for side in ('Q', 'R'):
        crops = []
        for image in evidence['images']:
            if image['side'] == side and image['kind'] == 'phone_crop':
                path = resolve(image['path'])
                with Image.open(path) as im:
                    dimensions = f'{im.width}×{im.height}'
                crops.append({'path': image['path'], 'dimensions': dimensions, 'image_id': image['image_id']})
        result[side] = crops
    return result


def audit(out: Path = OUT):
    out = Path(out)
    rows = _pilot_rows(out)
    reviewed = [r for r in rows if r['human'] and r['human']['status'] == 'REVIEWED']
    excluded = [r for r in rows if r['human'] and r['human']['status'] == 'EXCLUDED']
    unreviewed = [r for r in rows if r['human'] is None]
    matrix = Counter((r['gpt']['label'], r['human']['human_label']) for r in reviewed)
    disagreements = [r for r in reviewed if r['gpt']['label'] != r['human']['human_label']]
    for r in disagreements:
        r['images'] = _image_metadata(out, r['entry'])
    return {'rows': rows, 'reviewed': reviewed, 'excluded': excluded, 'unreviewed': unreviewed,
            'matrix': matrix, 'disagreements': disagreements}


def _flag_db(out: Path):
    return Path(out) / 'annotations/dev_pilot/disagreement_review.sqlite3'


def flags(out: Path = OUT):
    db = _flag_db(out)
    if not db.exists():
        return {}
    with sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True) as con:
        return {item_id: {'flag': flag, 'note': note, 'updated_utc': updated}
                for item_id, flag, note, updated in con.execute('SELECT item_id,flag,note,updated_utc FROM reviews')}


def save_flag(item_id: str, flag: str, note: str = '', out: Path = OUT):
    if flag not in FLAGS:
        raise ValueError('Invalid disagreement flag')
    a = audit(out)
    if item_id not in {r['item_id'] for r in a['disagreements']}:
        raise ValueError('Only reviewed DEV pilot label disagreements can be flagged')
    db = _flag_db(out)
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db, timeout=30) as con:
        con.execute('CREATE TABLE IF NOT EXISTS reviews (item_id TEXT PRIMARY KEY, flag TEXT NOT NULL, note TEXT NOT NULL, updated_utc TEXT NOT NULL)')
        con.execute('INSERT OR REPLACE INTO reviews VALUES (?,?,?,?)',
                    (item_id, flag, note.strip(), datetime.now(timezone.utc).isoformat()))
    return {'item_id': item_id, 'flag': flag, 'note': note.strip()}


def _pct(n: int, d: int):
    return f'{n / d * 100:.1f}%' if d else 'n/a'


def render_report(out: Path = OUT):
    out = Path(out)
    a = audit(out)
    reviewed, matrix, disagreements = a['reviewed'], a['matrix'], a['disagreements']
    saved = flags(out)
    ambiguous_n = sum(matrix['AMBIGUOUS', h] for h in LABELS)
    amb_same = matrix['AMBIGUOUS', 'SAME']
    amb_diff = matrix['AMBIGUOUS', 'DIFFERENT']
    false_same = [r for r in reviewed if r['gpt']['label'] == 'SAME' and r['human']['human_label'] == 'DIFFERENT']
    lines = [
        '# Pass I DEV Pilot — GPT vs Human Audit', '',
        f"Scope: fixed 40-item DEV pilot; {len(reviewed)} reviewed, {len(a['excluded'])} excluded, {len(a['unreviewed'])} unreviewed.",
        'Human labels are visual annotations; this audit does not establish physical identity ground truth.',
        'No frozen items or new model runs are included. The prompt is unchanged.', '',
        '## 3×3 label table', '',
        '| GPT \\ Human | SAME | DIFFERENT | AMBIGUOUS | Total |',
        '|---|---:|---:|---:|---:|',
    ]
    for g in LABELS:
        lines.append(f"| {g} | " + ' | '.join(str(matrix[g, h]) for h in LABELS) +
                     f" | {sum(matrix[g, h] for h in LABELS)} |")
    lines.append('| Total | ' + ' | '.join(str(sum(matrix[g, h] for g in LABELS)) for h in LABELS) + f' | {len(reviewed)} |')
    lines += ['', f"Agreement: {sum(matrix[x, x] for x in LABELS)}/{len(reviewed)} ({_pct(sum(matrix[x, x] for x in LABELS), len(reviewed))}).",
              f"Label disagreements: {len(disagreements)}/{len(reviewed)} ({_pct(len(disagreements), len(reviewed))}).", '',
              '## GPT AMBIGUOUS transitions', '',
              f'- GPT AMBIGUOUS → human SAME: **{amb_same}/{ambiguous_n} ({_pct(amb_same, ambiguous_n)})** of reviewed GPT AMBIGUOUS; {amb_same}/{len(reviewed)} ({_pct(amb_same, len(reviewed))}) of all reviewed.',
              f'- GPT AMBIGUOUS → human DIFFERENT: **{amb_diff}/{ambiguous_n} ({_pct(amb_diff, ambiguous_n)})** of reviewed GPT AMBIGUOUS; {amb_diff}/{len(reviewed)} ({_pct(amb_diff, len(reviewed))}) of all reviewed.', '',
              '## False SAME', '',
              f"Confirmed GPT SAME → human DIFFERENT: {len(false_same)} case(s). " + (', '.join(r['item_id'] for r in false_same) if false_same else 'None.'),
              'An AMBIGUOUS human label would be reported separately as an unsupported SAME, not a confirmed false SAME.', '',
              '## Challenge tag strata', '',
              'Both GPT and human challenge tags are shown separately. A pair with multiple tags appears in multiple rows; “untagged” means no tag was selected. These rows must not be summed.', '']
    for source, field in [('Human', 'human_challenge_tags'), ('GPT', 'challenge_tags')]:
        def tags_for(r):
            return r['human'].get(field, []) if source == 'Human' else r['gpt'].get(field, [])
        lines += [f'### {source} tags', '',
                  f'| {source} challenge tag | Reviewed | Agree | Disagree | GPT AMBIGUOUS → human SAME | GPT AMBIGUOUS → human DIFFERENT |',
                  '|---|---:|---:|---:|---:|---:|']
        tag_set = sorted({tag for r in reviewed for tag in tags_for(r)})
        if any(not tags_for(r) for r in reviewed):
            tag_set.insert(0, '(untagged)')
        for tag in tag_set:
            subset = [r for r in reviewed if (not tags_for(r) if tag == '(untagged)' else tag in tags_for(r))]
            agree = sum(r['gpt']['label'] == r['human']['human_label'] for r in subset)
            asame = sum(r['gpt']['label'] == 'AMBIGUOUS' and r['human']['human_label'] == 'SAME' for r in subset)
            adiff = sum(r['gpt']['label'] == 'AMBIGUOUS' and r['human']['human_label'] == 'DIFFERENT' for r in subset)
            lines.append(f'| {tag} | {len(subset)} | {agree} ({_pct(agree, len(subset))}) | {len(subset)-agree} ({_pct(len(subset)-agree, len(subset))}) | {asame} | {adiff} |')
        lines.append('')
    lines += ['', '## GPT AMBIGUOUS → human DIFFERENT item details', '']
    for r in reviewed:
        if r['gpt']['label'] != 'AMBIGUOUS' or r['human']['human_label'] != 'DIFFERENT':
            continue
        images = _image_metadata(out, r['entry'])
        lines += [f"### {r['item_id']}", '',
                  f"- GPT ambiguity cause: `{r['gpt']['ambiguity_cause']}`; human label: `DIFFERENT`; human challenge tags: `{', '.join(r['human'].get('human_challenge_tags', [])) or '(untagged)'}`.",
                  f"- Q/R phone crop counts: {len(images['Q'])}/{len(images['R'])}."]
        for side in ('Q', 'R'):
            for image in images[side]:
                lines.append(f"- {image['image_id']}: `{image['path']}` — {image['dimensions']} px.")
        lines.append('')
    lines += ['## Manual disagreement inspection', '',
              'The flags below are human review states. `UNREVIEWED` means no visual error attribution has been selected. Choose a flag in Streamlit → DEV pilot → Disagreement Review. Saving a flag does not change the human label or GPT draft.', '',
              '| Item | GPT | Human | Flag | Note |', '|---|---|---|---|---|']
    for r in disagreements:
        state = saved.get(r['item_id'], {'flag': 'UNREVIEWED', 'note': ''})
        lines.append(f"| {r['item_id']} | {r['gpt']['label']} | {r['human']['human_label']} | {state['flag']} | {state['note'].replace('|', '\\|')} |")
    if a['excluded']:
        lines += ['', '## Excluded from 3×3 table', '',
                  '| Item | GPT | Human status | Reason |', '|---|---|---|---|']
        for r in a['excluded']:
            lines.append(f"| {r['item_id']} | {r['gpt']['label']} | EXCLUDED | {r['human']['exclude_reason']} |")
    path = out / 'reports/PASS_I_DEV_PILOT_AUDIT.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path
