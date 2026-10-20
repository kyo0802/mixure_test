"""Small CPU-only owner CSV workflow. Original annotations are never rewritten."""
import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
from findmind_gt_contract import (ROOT, TOOL, EVENTS, STATES, VISIBILITY, canonical,
                                 digest, file_sha, load_json, validate_bundle)
sys.path.insert(0, str(ROOT / 'src'))
from memory_graph.experiments.three_vlm_contract import interval_distance, merge_intervals

OUT = ROOT / 'artifacts/vlmtest/gt_consolidation_v1'
EXP = ROOT / 'artifacts/pass_t/phase3/three_vlm_full_v1'
PHYSICAL = ('PICKUP', 'PLACEMENT')
YES = ('YES', 'TRUE', '1')


def save(path, value):
    path = Path(path)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def csv_write(path, rows, fields=None):
    with Path(path).open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        w.writeheader()
        for row in rows:
            w.writerow({k: ('\u200b' + str(v) if str(v).startswith(('=', '+', '-', '@')) else v)
                        for k, v in row.items()})


def csv_read(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return [{k: v.removeprefix('\u200b') for k, v in r.items()} for r in csv.DictReader(f)]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def number(value):
    n = float(value)
    require(math.isfinite(n), 'Non-finite time')
    return n


def affirmative(value):
    return str(value).strip().upper() in YES


def category(value):
    return str(value).strip().casefold()


def iv(e):
    return [e['start_s'], e['end_s']]


def overlap(a, b):
    return min(a[1], b[1]) >= max(a[0], b[0])


def similarity(a, b):
    if a['video_id'] != b['video_id'] or category(a['event']['object_category']) != category(b['event']['object_category']):
        return None
    x, y = a['event'], b['event']
    if interval_distance(iv(x), iv(y)) > .5:
        return None
    intersection = max(0., min(x['end_s'], y['end_s']) - max(x['start_s'], y['start_s']))
    union = max(x['end_s'], y['end_s']) - min(x['start_s'], y['start_s'])
    return (2. if x['type'] == y['type'] else 0.) + intersection / max(union, 1e-9) - interval_distance(iv(x), iv(y))


def align(left, right):
    """Mutual unique best pairs only; never union overlapping event components."""
    edges = {(i, j): s for i, a in enumerate(left) for j, b in enumerate(right)
             if (s := similarity(a, b)) is not None}
    def best(scores):
        scores = sorted(scores, reverse=True)
        return scores[0][1] if scores and (len(scores) == 1 or scores[0][0] - scores[1][0] > .15) else None
    lb = {i: best([(s, j) for (ii, j), s in edges.items() if ii == i]) for i in range(len(left))}
    rb = {j: best([(s, i) for (i, jj), s in edges.items() if jj == j]) for j in range(len(right))}
    paired = [(i, j) for i, j in lb.items() if j is not None and rb[j] == i]
    used_l, used_r = {i for i, _ in paired}, {j for _, j in paired}
    groups = [[left[i], right[j]] for i, j in paired]
    groups += [[a] for i, a in enumerate(left) if i not in used_l]
    groups += [[b] for j, b in enumerate(right) if j not in used_r]
    return sorted(groups, key=lambda g: (int(g[0]['video_id'].removeprefix('test')), min(x['event']['start_s'] for x in g))), edges


def classify(group):
    flags = []
    es = [r['event'] for r in group]
    if len(es) == 1:
        flags.append('ONE_REVIEWER_ONLY')
    else:
        a, b = es
        if (a['type'] in PHYSICAL) != (b['type'] in PHYSICAL):
            flags.append('NON_EVENT_CONFLICT')
        elif a['type'] != b['type']:
            flags.append('EVENT_TYPE_DISAGREEMENT')
        if max(abs(a[k] - b[k]) for k in ('start_s', 'end_s')) > .5:
            flags.append('TIMING_DISAGREEMENT')
        if any(a[k] != b[k] for k in ('before_state', 'after_state')):
            flags.append('UNCERTAIN_EVIDENCE')
    # Differently named reviewer-local IDs alone are never an identity conflict.
    if any(e['target_identity_certainty'] != 'CERTAIN' or e['local_instance_id'].upper() == 'UNKNOWN' for e in es):
        flags.append('IDENTITY_DISAGREEMENT')
    if any(e['evidence_certainty'] != 'CONFIRMED' for e in es):
        flags.append('UNCERTAIN_EVIDENCE')
    priority = ['NON_EVENT_CONFLICT', 'EVENT_TYPE_DISAGREEMENT', 'ONE_REVIEWER_ONLY',
                'UNCERTAIN_EVIDENCE', 'IDENTITY_DISAGREEMENT', 'TIMING_DISAGREEMENT']
    flags = list(dict.fromkeys(flags))
    return next((p for p in priority if p in flags), 'AGREED_CANDIDATE'), flags


def cross_group_conflicts(rows, registry):
    """Highlight alternative explanations without merging overlapping real events."""
    for row in rows:
        flags = [f for f in row['all_flags'].split('|') if f]
        for other in row['related_groups'].split('|'):
            if not other: continue
            for a in registry[row['group_id']]:
                for b in registry[other]:
                    x, y = a['event'], b['event']
                    if a['reviewer_id'] == b['reviewer_id'] or category(x['object_category']) != category(y['object_category']) or not overlap(iv(x), iv(y)):
                        continue
                    if (x['type'] in PHYSICAL) != (y['type'] in PHYSICAL): flags.append('NON_EVENT_CONFLICT')
                    elif x['type'] != y['type']: flags.append('EVENT_TYPE_DISAGREEMENT')
        flags = list(dict.fromkeys(flags)); row['all_flags'] = '|'.join(flags)
        priority = ['NON_EVENT_CONFLICT', 'EVENT_TYPE_DISAGREEMENT', 'ONE_REVIEWER_ONLY', 'UNCERTAIN_EVIDENCE', 'IDENTITY_DISAGREEMENT', 'TIMING_DISAGREEMENT']
        row['classification'] = next((p for p in priority if p in flags), 'AGREED_CANDIDATE')
    return rows


def records(out):
    manifest = load_json(TOOL / 'manifest.json')
    require(digest({k: v for k, v in manifest.items() if k != 'dataset_manifest_sha256'}) == manifest['dataset_manifest_sha256'], 'Manifest digest mismatch')
    bundles = [load_json(out / 'originals' / f'{n}.json') for n in ('huang', 'kuo')]
    for b in bundles:
        require(not validate_bundle(b, manifest), str(validate_bundle(b, manifest)))
    lists = []
    for n, b in zip(('huang', 'kuo'), bundles):
        lists.append([{'ref': n + ':' + e['event_id'], 'reviewer_id': b['reviewer_id'], 'session_id': b['session_id'],
                       'submission_sha256': file_sha(out / 'originals' / f'{n}.json'), 'video_id': v['video_id'], 'event': e}
                      for v in b['videos'] for e in v['events']])
    return manifest, bundles, lists


def verify_timing(manifest, dataset):
    videos = {v['video_id']: v for v in manifest['videos']}
    checked = 0
    for w in dataset['windows']:
        v = videos[w['video_id']]
        require(w['source_video_sha256'] == v['source_sha256'], 'Window source identity mismatch')
        for f in w['frames']:
            index = f['source_frame_index']
            require(0 <= index < v['frame_count'], 'Source frame index out of range')
            native = v['frame_timeline'][index]
            require(native['index'] == index and abs(native['source_time_s'] - f['native_pts_s']) < 1e-9, 'Native PTS mismatch')
            checked += 1
    return checked


def prepare(out):
    require(not (out / 'adjudication.csv').exists(), 'Prepared collection exists; never overwrite owner edits')
    manifest, bundles, lists = records(out)
    dataset = load_json(EXP / 'dataset.json')
    timing_checked = verify_timing(manifest, dataset)
    ds = {v['video_id']: v for v in dataset['videos']}
    sources = {}
    for v in manifest['videos']:
        p = ROOT / v['original_filename']
        require(file_sha(p) == v['source_sha256'] == ds[v['video_id']]['sha256'], 'Original video identity mismatch: ' + v['video_id'])
        require(abs(v['source_duration_s'] - ds[v['video_id']]['duration_seconds']) < 1e-6, 'Duration mismatch')
        sources[str(p.relative_to(ROOT))] = file_sha(p)
    for n in ('huang', 'kuo'):
        p = out / 'originals' / f'{n}.json'
        sources[str(p.relative_to(ROOT))] = file_sha(p)
    for p in [TOOL / 'manifest.json', EXP / 'dataset.json', EXP / 'configuration.json', EXP / 'event_proposals.json', EXP / 'state_claims.json', EXP / 'model_results.json', EXP / 'dataset_freeze.json'] + list((EXP / 'timelines').glob('*.json')):
        sources[str(p.relative_to(ROOT))] = file_sha(p)
    models = load_json(EXP / 'model_results.json')
    counts = {}
    for name, result in models.items():
        counts[name] = 0
        for row in result['rows']:
            raw = ROOT / row['raw_path']; receipt = raw.with_name('receipt.json')
            require(file_sha(raw) == row['raw_sha256'] == load_json(receipt)['raw_sha256'], 'Raw receipt mismatch')
            require(row['status'] == 'COMPLETED', 'Incomplete original run')
            for p in (raw, receipt, raw.with_name('validation.json'), raw.with_name('input.json')):
                sources[str(p.relative_to(ROOT))] = file_sha(p)
            require(load_json(raw.with_name('validation.json')) == row['validation'], 'Historical validation mismatch')
            counts[name] += 1
    require(counts == {'qwen': 184, 'videollama': 184, 'nemotron': 184}, 'Expected 552 completed calls')
    groups, edges = align(*lists)
    rows, registry = [], {}
    for i, group in enumerate(groups, 1):
        gid = f'G{i:03d}'; klass, flags = classify(group); registry[gid] = group
        e = group[0]['event']; row = {'group_id': gid, 'video_id': group[0]['video_id'], 'classification': klass, 'all_flags': '|'.join(flags),
                                     'source_refs': '|'.join(r['ref'] for r in group), 'related_groups': ''}
        for n in ('huang', 'kuo'):
            rec = next((r for r in group if r['ref'].startswith(n + ':')), None)
            row[n + '_reviewer_id'] = rec['reviewer_id'] if rec else ''
            for k in ('event_id', 'type', 'object_category', 'local_instance_id', 'start_s', 'end_s', 'before_state', 'after_state',
                      'before_visibility', 'after_visibility', 'before_evidence_times_s', 'after_evidence_times_s',
                      'target_identity_certainty', 'evidence_certainty', 'visibility_limitations', 'notes'):
                value = rec['event'][k] if rec else ''
                row[n + '_' + k] = canonical(value) if isinstance(value, list) else value
        row.update(decision_id=gid, owner_decision='', owner_reviewer_id='', final_event_id=f"GT_{row['video_id']}_{gid}",
                   final_event_type=e['type'], final_object_category=e['object_category'], final_object_id='',
                   final_start_s=e['start_s'], final_end_s=e['end_s'], final_before_state=e['before_state'], final_after_state=e['after_state'],
                   final_before_visibility=e['before_visibility'], final_after_visibility=e['after_visibility'],
                   final_before_evidence_times_s=canonical(e['before_evidence_times_s']), final_after_evidence_times_s=canonical(e['after_evidence_times_s']),
                   same_real_event_confirmed='', physical_transition_confirmed='', identity_resolved='', decision_notes='')
        rows.append(row)
    for row in rows:
        related = [g for g, rs in registry.items() if g != row['group_id'] and any(similarity(a, b) is not None for a in registry[row['group_id']] for b in rs if a['reviewer_id'] != b['reviewer_id'])]
        row['related_groups'] = '|'.join(related)
    cross_group_conflicts(rows, registry)
    alignment_fields = list(rows[0])[:list(rows[0]).index('decision_id')]
    csv_write(out / 'gt_alignment.csv', [{k: r[k] for k in alignment_fields} for r in rows])
    csv_write(out / 'adjudication.csv', rows)
    coverage, states = [], []
    for vi, v in enumerate(manifest['videos']):
        vs = [next(x for x in b['videos'] if x['video_id'] == v['video_id']) for b in bundles]
        gaps = [g for vv in vs for g in vv['uncertain_intervals'] if g['could_conceal_event'] or g['identity_uncertain']]
        bounds = sorted({0., v['source_duration_s']} | {g[k] for g in gaps for k in ('start_s', 'end_s')})
        for j, (a, b) in enumerate(zip(bounds, bounds[1:]), 1):
            if b - a < 1e-6:
                continue
            active = [g for g in gaps if g['start_s'] < b and g['end_s'] > a]
            coverage.append({'scope_id': f"{v['video_id']}_S{j:02d}", 'video_id': v['video_id'], 'start_s': a, 'end_s': b,
                             'suggestion': 'REPORTED_GAP_REQUIRES_RESOLUTION' if active else 'NO_REPORTED_GAP_NOT_ATTESTED',
                             'huang_exhaustiveness': vs[0]['event_list_exhaustiveness'], 'kuo_exhaustiveness': vs[1]['event_list_exhaustiveness'],
                             'reported_gaps': canonical(active), 'owner_decision': '', 'owner_reviewer_id': '',
                             'object_category_scope': '', 'object_ids_scope': '', 'full_scope_reviewed': '', 'all_events_verified': '',
                             'event_visibility_sufficient': '', 'object_identity_resolved': '', 'known_gaps_resolved': '', 'decision_notes': ''})
        for b, vv in zip(bundles, vs):
            states += [{'video_id': v['video_id'], 'reviewer_id': b['reviewer_id'], 'session_id': b['session_id'], **s} for s in vv['states']]
    csv_write(out / 'coverage_adjudication.csv', coverage)
    save(out / 'original_state_evidence.json', states)
    save(out / 'alignment_registry.json', registry)
    save(out / 'preservation_manifest.json', sources)
    stats = {'reviewers': [b['reviewer_id'] for b in bundles], 'original_annotations': [len(x) for x in lists],
             'physical_annotations': [sum(r['event']['type'] in PHYSICAL for r in x) for x in lists],
             'non_event_annotations': [sum(r['event']['type'] not in PHYSICAL for r in x) for x in lists],
             'groups': len(groups), 'paired_groups': sum(len(g) == 2 for g in groups), 'classifications': dict(Counter(r['classification'] for r in rows)),
             'all_flags': dict(Counter(f for r in rows for f in r['all_flags'].split('|') if f)), 'coverage_rows': len(coverage),
             'automatic_exhaustive_eligible_videos': 0, 'model_calls_verified': counts, 'state_records': len(states),
             'alignment_policy': 'Mutual unique best; same video/category; overlap or <=0.5s gap; same type preferred; margin >0.15. No physical merge.',
             'timing_disagreement_boundary_seconds': .5, 'historical_files_verified': len(sources), 'native_frame_references_verified': timing_checked}
    save(out / 'prepare_summary.json', stats)
    (out / 'gt_disagreement_summary.md').write_text('# 兩位人工 GT 對齊摘要\n\n' +
        f"原始紀錄：{stats['original_annotations']}；物理事件標記：{stats['physical_annotations']}；非事件觀察：{stats['non_event_annotations']}。\n\n" +
        f"共 {len(groups)} 個待裁決群組，其中 {stats['paired_groups']} 組雙人對應候選；分類 {stats['classifications']}。附加旗標 {stats['all_flags']}。\n\n" +
        '分類不是裁決：UNKNOWN 身分列為 IDENTITY_DISAGREEMENT，意指尚未解決，不代表已證實不同實物；不同 local ID 名稱本身不算衝突。\n\n' +
        '兩人九片 event_list_exhaustiveness 全為 NOT_ATTESTED。完整觀看不能產生負例資格；原始聲明保持原值。coverage 表依已知遮擋邊界切開，只是待人工核准的區間，未報遮擋也不等於已證明可觀察。\n\n' +
        '對齊只用人工標註。相同類別、型別及重疊時間只構成候選；related_groups 請檢查是否其實不同實物或不同事件。每個群組最多各一位審閱者的紀錄，不做傳遞式合併。\n\n' +
        '所有 owner_decision 均空白，尚無 authoritative GT。請見 EDITING_GUIDE.md。\n', encoding='utf-8')
    return stats


def verify(out):
    hashes = load_json(out / 'preservation_manifest.json')
    changed = [p for p, sha in hashes.items() if not (ROOT / p).exists() or file_sha(ROOT / p) != sha]
    require(not changed, 'Preserved input changed: ' + str(changed[:8]))
    verify_timing(load_json(TOOL / 'manifest.json'), load_json(EXP / 'dataset.json'))


def finalize(out, destination):
    verify(out)
    manifest, bundles, original_lists = records(out)
    videos = {v['video_id']: v for v in manifest['videos']}
    registry = load_json(out / 'alignment_registry.json')
    refs = {r['ref']: r for rs in registry.values() for r in rs}
    require(refs == {r['ref']: r for rs in original_lists for r in rs}, 'Alignment registry differs from original submissions')
    rows = csv_read(out / 'adjudication.csv')
    require(any(r['owner_decision'].strip() for r in rows), 'No owner adjudication yet; do not generate final GT')
    used, decisions, unresolved, observations, events = [], set(), [], [], {}
    for row in rows:
        gid = row['group_id']; require(gid in registry, 'Unknown group: ' + gid)
        require(row['decision_id'] and row['decision_id'] not in decisions, 'Duplicate/empty decision_id')
        decisions.add(row['decision_id'])
        rs = row['source_refs'].split('|'); allowed = {r['ref'] for r in registry[gid]}
        require(rs and all(r in allowed for r in rs), 'Altered source refs outside original group')
        require(not set(rs).intersection(used), 'Source annotation used more than once; split refs explicitly')
        used += rs
        vid = registry[gid][0]['video_id']; require(row['video_id'] == vid, 'Video changed')
        dec = row['owner_decision'].strip().upper()
        require(dec in ('', 'ACCEPT', 'MODIFY', 'REJECT', 'UNCERTAIN'), 'Invalid owner_decision')
        if dec:
            require(row['owner_reviewer_id'].strip() and row['decision_notes'].strip(), 'Decision needs reviewer and notes: ' + gid)
        if dec in ('', 'UNCERTAIN'):
            unresolved.append({'group_id': gid, 'source_refs': rs, 'records': [refs[r] for r in rs], 'owner_record': row}); continue
        if dec == 'REJECT':
            observations.append({'decision': dec, 'source_refs': rs, 'source_records': [refs[r] for r in rs], 'owner_record': row, 'owner_reviewer_id': row['owner_reviewer_id'], 'notes': row['decision_notes']}); continue
        typ = row['final_event_type']; require(typ in EVENTS, 'Unknown final event type')
        a, b = number(row['final_start_s']), number(row['final_end_s'])
        require(0 <= a <= b <= videos[vid]['source_duration_s'], 'Final interval out of source bounds')
        if typ not in PHYSICAL:
            observations.append({'decision': dec, 'source_refs': rs, 'source_records': [refs[r] for r in rs], 'owner_record': row, 'type': typ, 'video_id': vid, 'time_interval': [a, b], 'notes': row['decision_notes']}); continue
        require(all(affirmative(row[k]) for k in ('physical_transition_confirmed', 'identity_resolved')), 'Physical transition / identity confirmation missing: ' + gid)
        require(len(rs) == 1 or affirmative(row['same_real_event_confirmed']), 'Paired annotations require same_real_event_confirmed: ' + gid)
        require(row['final_object_id'].strip() and row['final_object_id'].upper() != 'UNKNOWN', 'Final physical object ID required')
        expected = ('ON_SURFACE', 'HELD_BY_PERSON') if typ == 'PICKUP' else ('HELD_BY_PERSON', 'ON_SURFACE')
        require((row['final_before_state'], row['final_after_state']) == expected, 'Physical state transition unsupported')
        for k in ('final_before_visibility', 'final_after_visibility'):
            require(row[k] in ('VISIBLE', 'PARTIALLY_OCCLUDED'), 'Invisible evidence cannot confirm a transition')
        before, after = json.loads(row['final_before_evidence_times_s']), json.loads(row['final_after_evidence_times_s'])
        require(isinstance(before, list) and isinstance(after, list) and before and after, 'Before/after evidence required')
        before, after = list(map(number, before)), list(map(number, after))
        require(all(0 <= t <= videos[vid]['source_duration_s'] for t in before + after) and max(before) < min(after), 'Invalid evidence timing')
        require(min(before) <= b and max(after) >= a, 'Evidence does not bound the event interval')
        # ACCEPT keeps the prefilled first selected source fields; corrections use MODIFY.
        if dec == 'ACCEPT':
            source = refs[rs[0]]['event']
            require(typ == source['type'] and category(row['final_object_category']) == category(source['object_category']) and [a, b] == iv(source)
                    and list(expected) == [source['before_state'], source['after_state']]
                    and before == source['before_evidence_times_s'] and after == source['after_evidence_times_s']
                    and row['final_before_visibility'] == source['before_visibility'] and row['final_after_visibility'] == source['after_visibility'],
                    'Changed source fields require MODIFY: ' + gid)
        eid = row['final_event_id'].strip(); require(eid, 'Unique final_event_id required')
        event = {'final_event_id': eid, 'video_id': vid, 'video_sha256': videos[vid]['source_sha256'], 'type': typ,
                 'object_category': row['final_object_category'].strip(), 'reviewed_object_id': row['final_object_id'].strip(), 'time_interval': [a, b],
                 'before_state': expected[0], 'after_state': expected[1], 'before_visibility': row['final_before_visibility'], 'after_visibility': row['final_after_visibility'],
                 'before_evidence_times_s': before, 'after_evidence_times_s': after, 'review_status': 'HUMAN_REVIEWED'}
        require(event['object_category'], 'Empty final object category')
        if eid in events:
            require(affirmative(row['same_real_event_confirmed']) and events[eid]['same_real_event_confirmed'], 'Explicit cross-row merge confirmation required')
            require(all(events[eid][k] == val for k, val in event.items()), 'Same final_event_id has inconsistent events')
            events[eid]['provenance'].append(row); events[eid]['source_records'] += [refs[r] for r in rs]
        else:
            events[eid] = {**event, 'same_real_event_confirmed': affirmative(row['same_real_event_confirmed']), 'provenance': [row], 'source_records': [refs[r] for r in rs]}
    require(set(used) == set(refs), 'Missing original annotation decisions; use UNCERTAIN instead of deleting rows')
    coverage, pending_scopes = [], []
    scope_ids = set()
    for row in csv_read(out / 'coverage_adjudication.csv'):
        require(row['scope_id'] and row['scope_id'] not in scope_ids, 'Duplicate/empty scope_id'); scope_ids.add(row['scope_id'])
        vid = row['video_id']; require(vid in videos, 'Unknown scope video')
        a, b = number(row['start_s']), number(row['end_s'])
        require(0 <= a < b <= videos[vid]['source_duration_s'], 'Scope out of source bounds')
        dec = row['owner_decision'].strip().upper(); require(dec in ('', 'ACCEPT', 'MODIFY', 'REJECT', 'UNCERTAIN'), 'Invalid scope decision')
        if dec:
            require(row['owner_reviewer_id'].strip() and row['decision_notes'].strip(), 'Scope decision needs owner and notes')
        if dec not in ('ACCEPT', 'MODIFY'):
            pending_scopes.append(row); continue
        require(row['owner_reviewer_id'].strip() and row['decision_notes'].strip(), 'Scope owner / notes missing')
        require(all(affirmative(row[k]) for k in ('full_scope_reviewed', 'all_events_verified', 'event_visibility_sufficient', 'object_identity_resolved')), 'Scope exhaustive attestation missing')
        cats = {category(x) for x in row['object_category_scope'].split('|') if x.strip()}; ids = {x.strip() for x in row['object_ids_scope'].split('|') if x.strip()}
        require(cats and ids, 'Explicit category and object-ID scopes required; ALL is permitted only if explicitly reviewed')
        vs = [next(v for v in bnd['videos'] if v['video_id'] == vid) for bnd in bundles]
        gaps = [g for v in vs for g in v['uncertain_intervals'] if (g['could_conceal_event'] or g['identity_uncertain']) and g['start_s'] < b and g['end_s'] > a]
        require(not gaps or affirmative(row['known_gaps_resolved']), 'Known obscured/identity gap remains; narrow scope or explicitly resolve with notes')
        unknown = [u for u in unresolved if any(r['video_id'] == vid and ('all' in cats or category(r['event']['object_category']) in cats) and overlap(iv(r['event']), [a, b]) for r in u['records'])]
        require(not unknown, 'Unresolved annotation overlaps accepted scope; resolve row or narrow scope')
        coverage.append({'scope_id': row['scope_id'], 'video_id': vid, 'video_sha256': videos[vid]['source_sha256'], 'start_s': a, 'end_s': b,
                         'review_status': 'HUMAN_REVIEWED', 'reviewer_id': row['owner_reviewer_id'], 'coverage': 'EXHAUSTIVE_ATTESTED',
                         'entire_interval_reviewed': True, 'all_pickup_placement_annotated': True, 'no_unobservable_gap': True,
                         'target_association_resolved': True, 'ontology': 'PICKUP_PLACEMENT_ONLY', 'object_categories': sorted(cats),
                         'object_ids': sorted(ids), 'original_NOT_ATTESTED_preserved': True, 'owner_attestation': row})
    gt = {'schema_version': 'findmind_consolidated_gt_v1', 'dataset_manifest_sha256': manifest['dataset_manifest_sha256'],
          'truth': list(events.values()), 'coverage': coverage, 'unresolved': unresolved, 'non_event_and_rejected': observations,
          'original_state_evidence': load_json(out / 'original_state_evidence.json'), 'state_evidence_is_not_automatically_adjudicated': True,
          'adjudication_sha256': file_sha(out / 'adjudication.csv'), 'coverage_adjudication_sha256': file_sha(out / 'coverage_adjudication.csv'),
          'input_hashes': load_json(out / 'preservation_manifest.json')}
    destination.mkdir(parents=True, exist_ok=False)
    save(destination / 'final_gt.json', gt)
    save(destination / 'finalization_receipt.json', {'final_gt_sha256': file_sha(destination / 'final_gt.json'),
        'adjudication_sha256': gt['adjudication_sha256'], 'coverage_adjudication_sha256': gt['coverage_adjudication_sha256']})
    eligibility = {'accepted_scopes': coverage, 'pending_or_excluded_scopes': pending_scopes, 'unresolved_groups': len(unresolved),
                   'overall_full_dataset_f1_allowed': False, 'policy': 'Only explicitly accepted object/category/time scopes; unreviewed intervals never negatives.'}
    save(destination / 'gt_eligibility.json', eligibility)
    (destination / 'final_gt_summary.md').write_text(f"# 最終 GT\n\n人工接受事件 {len(events)}；可評分局部範圍 {len(coverage)}；未解群組 {len(unresolved)}。\n\n原始 NOT_ATTESTED 未改寫；本次 scope 是新的人工作證。未審閱時間／物件不算負例；正例即使未取得完整 coverage 仍保留，但不產生全片 precision/F1。\n", encoding='utf-8')
    return {'events': len(events), 'eligible_scopes': len(coverage), 'unresolved_groups': len(unresolved)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'finalize', 'verify'])
    parser.add_argument('--collection', type=Path, default=OUT)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare': result = prepare(args.collection)
    elif args.action == 'verify': verify(args.collection); result = {'preserved_inputs': 'PASS'}
    else:
        require(args.output is not None, '--output is required and must not exist')
        result = finalize(args.collection, args.output)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
