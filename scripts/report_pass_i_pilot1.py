"""Read-only Pilot 1 readiness report; no model calls or annotation edits."""
from collections import Counter
from pathlib import Path
import sqlite3
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from memory_graph.pass_i.common import OUT, read, read_lines, sha
from memory_graph.pass_i.pilot import PROMPT_FILE, verify_pilot
from memory_graph.pass_i.pilot1 import PILOT1_MANIFEST


def main():
    pilot0 = verify_pilot()
    manifest = read(PILOT1_MANIFEST)
    prompt_sha = sha(PROMPT_FILE)
    if prompt_sha != pilot0['prompt_sha256'] or prompt_sha != manifest['prompt_sha256']:
        raise ValueError('Prompt SHA mismatch; STOP')
    original = {p['item_id']: p for p in read_lines(OUT / 'manifests/pair_manifest.jsonl')}
    pilot0_combos = {frozenset((original[e['item_id']]['query_epoch_id'], original[e['item_id']]['reference_epoch_id']))
                     for e in pilot0['items']}
    overlaps = [p['item_id'] for p in manifest['items'] if p['item_id'] in original or
                frozenset((p['query_epoch_id'], p['reference_epoch_id'])) in pilot0_combos]
    if overlaps:
        raise ValueError('Pilot 0 overlap: ' + ', '.join(overlaps))
    drafts = {}
    prelabels = OUT / 'prelabels/dev_pilot_1'
    for entry in manifest['items']:
        path = prelabels / f"{entry['item_id']}.json"
        if path.exists():
            drafts[entry['item_id']] = read(path)
    valid = [d for d in drafts.values() if d.get('valid') and d.get('schema_valid')]
    invalid = [item_id for item_id, d in drafts.items() if not d.get('valid') or not d.get('schema_valid')]
    gpt = Counter(d['parsed']['label'] for d in valid)
    quality = Counter(p['pair_quality'] for p in manifest['items'])
    videos = Counter(p['video_id'] for p in manifest['items'])
    db = OUT / 'annotations/dev_pilot_1/annotations/annotations.sqlite3'
    humans = {}
    if db.exists():
        with sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True) as con:
            humans = {k: json.loads(v) for k, v in con.execute('SELECT item_id,data FROM annotations')}
    reviewed = [x for x in humans.values() if x['status'] == 'REVIEWED']
    excluded = [x for x in humans.values() if x['status'] == 'EXCLUDED']
    status = 'PASS_I_PILOT1_READY_FOR_HUMAN_REVIEW' if len(drafts) == 40 else 'PASS_I_PILOT1_PRELABELING'
    lines = ['# Pass I DEV Pilot 1 Report', '', f'Status: **{status}**', '',
             f"Pilot 1 manifest SHA-256: `{sha(PILOT1_MANIFEST)}`.",
             f"Prompt: `pass_i_visual_annotator_v1`; SHA-256: `{prompt_sha}` (matches Pilot 0).",
             'CASE_CHANGE_POLICY: `UNKNOWN`.',
             'DEV only. Pilot 0 item IDs and unordered Q/R epoch combinations are disjoint; Frozen items sent: 0.', '',
             '## Clean pool and selection', '',
             f"- Human QC reviewed epochs at selection: {manifest['qc_reviewed_epochs']}.",
             f"- Clean DEV pair pool excluding Pilot 0: {manifest['clean_dev_pair_pool_count']}.",
             f"- Pilot 1 pairs: {len(manifest['items'])}; PRIMARY_VALID {quality['PRIMARY_VALID']}; HARD_VALID {quality['HARD_VALID']}; blind-first {manifest['blind_first_count']}.",
             '- Session/video composition: ' + ', '.join(f'{v} {n}' for v, n in sorted(videos.items())) + '.', '',
             '## GPT-6.1 Sol pre-label', '',
             f'- Completed: {len(drafts)}/40.',
             f'- Schema-valid: {len(valid)}/40; invalid: {len(invalid)}' + (f" ({', '.join(invalid)})" if invalid else '') + '.',
             f"- Valid labels: SAME {gpt['SAME']}, DIFFERENT {gpt['DIFFERENT']}, AMBIGUOUS {gpt['AMBIGUOUS']}.",
             'Raw responses are saved separately before parsing. The model-visible package contains only item ID, case policy, and numbered Q/R crops.', '',
             '## Human identity review', '',
             f'- Reviewed: {len(reviewed)}; excluded: {len(excluded)}; pending: {40-len(humans)}.',
             'Open the Streamlit tool → Workflow: Identity Annotation → Dataset scope: DEV Pilot 1. Complete the six blind-first items before revealing their GPT pre-labels.',
             'The Pilot 1 GPT-vs-human table and Pilot 0 descriptive comparison are deferred until human Pilot 1 annotation is complete.', '']
    path = OUT / 'reports/PASS_I_DEV_PILOT_1_REPORT.md'
    path.write_text('\n'.join(lines), encoding='utf-8')
    print(path)


if __name__ == '__main__':
    main()
