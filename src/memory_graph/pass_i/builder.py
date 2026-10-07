"""Read-only V297 inventory and label-free Pass I evidence preparation."""
from __future__ import annotations

import hashlib
import itertools
import math
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .common import ROOT, OUT, read, write, jsonl, sha, ref, resolve, read_lines

DEFAULT_CONFIG = {
    'schema': 'findmind_pass_i_dataset_v1', 'seed': 297101,
    'dev_fraction': .3, 'CASE_CHANGE_POLICY': 'UNKNOWN',
    'max_pairs_per_recording': 120, 'max_clean_crops': 6,
    'max_context_images': 2, 'minimum_crop_spacing_seconds': .4,
    'near_duplicate_hamming': 2, 'long_gap_seconds': 2.,
    'session_overrides': {},
    'session_policy': 'recording-level fallback; explicit overrides and shared source evidence unioned',
    'source_sets': ['development', 'known_val_regression'],
}


def dhash(image):
    a = np.asarray(image.convert('L').resize((9, 8)), dtype=np.int16)
    return int.from_bytes(np.packbits(a[:, 1:] > a[:, :-1]).tobytes(), 'big')


def quality(path):
    with Image.open(path) as im:
        rgb = im.convert('RGB')
        a = np.asarray(rgb)
        return {'width': im.width, 'height': im.height, 'dhash': f'{dhash(rgb):016x}',
                'blur_laplacian_variance': float(cv2.Laplacian(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), cv2.CV_64F).var())}


def protected_snapshot(root=ROOT):
    # Include complete V297 outputs and V2101 artifacts, not just policy files.
    folders = ['src/memory_graph/v297_physical_identity', 'src/memory_graph/v296_reid',
               'src/memory_graph/identity', 'src/memory_graph/events',
               'src/memory_graph/reasoning', 'src/memory_graph/v2101_deploy',
               'outputs/v297_physical_identity', 'artifacts/v2.10.1']
    result = {}
    for folder in folders:
        for p in sorted((root / folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                result[p.relative_to(root).as_posix()] = sha(p)
    for p in sorted((root / 'scripts').glob('*v297*.py')):
        result[p.relative_to(root).as_posix()] = sha(p)
    return result


class Union:
    def __init__(self, ids):
        self.p = {x: x for x in ids}

    def find(self, x):
        if self.p[x] != x:
            self.p[x] = self.find(self.p[x])
        return self.p[x]

    def join(self, a, b):
        a, b = self.find(a), self.find(b)
        self.p[max(a, b)] = min(a, b)


def select_crops(rows, cfg):
    # Prefer quality first; subsequent choices add temporal and visual diversity.
    pool = [r for r in rows if r.get('available')]
    selected = []
    while pool and len(selected) < cfg['max_clean_crops']:
        eligible = [r for r in pool if all(
            r['raw_crop_sha256'] != s['raw_crop_sha256'] and
            abs(r['time'] - s['time']) >= cfg['minimum_crop_spacing_seconds'] and
            (int(r['quality']['dhash'], 16) ^ int(s['quality']['dhash'], 16)).bit_count() > cfg['near_duplicate_hamming']
            for s in selected)]
        if not eligible:
            break
        def rank(r):
            q = r['quality']
            clarity = math.log1p(q['blur_laplacian_variance']) + math.log1p(min(q['width'], q['height']))
            spacing = min((abs(r['time'] - s['time']) for s in selected), default=0)
            novelty = min(((int(q['dhash'], 16) ^ int(s['quality']['dhash'], 16)).bit_count() for s in selected), default=0)
            return (clarity if not selected else min(spacing, 10) + novelty / 8 + clarity / 4, -r['frame'], r['observation_id'])
        best = max(eligible, key=rank)
        selected.append(best)
        pool.remove(best)
    return sorted(selected, key=lambda r: (r['frame'], r['observation_id']))


def inventory(root, cfg):
    base = root / 'outputs/v297_physical_identity'
    epochs, recordings, issues = [], {}, []
    file_hashes = {}
    def digest(path):
        path = Path(path)
        if path not in file_hashes:
            file_hashes[path] = sha(path)
        return file_hashes[path]
    for source_set in cfg['source_sets']:
        for ep in sorted((base / source_set / 'runs').glob('*/candidate_epochs.json')):
            vid = ep.parent.name
            mp = ep.parent / 'metadata.json'
            sp = base / 'inputs' / vid / 'source.json'
            metadata, source = read(mp), read(sp)
            video = root / (f'{vid}.mp4' if vid.startswith('test') else f'val_set/{vid}.mp4')
            if not video.is_file() or digest(video) != source['video_sha256']:
                raise ValueError('Missing or changed source video: ' + vid)
            recordings[vid] = {'video_id': vid, 'video_path': video.relative_to(root).as_posix(),
                'video_sha256': source['video_sha256'], 'source_set': source_set,
                'explicit_session_id': source.get('session_id') or source.get('recording_session_id') or cfg['session_overrides'].get(vid),
                'source_manifest': ref(sp, root), 'frame_signatures': {}, 'crop_signatures': [], 'preview_frames': []}
            for original in read(ep)['epochs']:
                observations = []
                for oid in original['observation_ids']:
                    r = metadata.get(oid)
                    if r is None:
                        raise ValueError('Missing epoch observation: ' + oid)
                    if r['candidate_epoch_id'] != original['candidate_epoch_id']:
                        raise ValueError('Observation epoch mismatch')
                    entry = {k: r[k] for k in ['observation_id', 'frame', 'time', 'bbox', 'label', 'local_track_id',
                             'raw_crop_path', 'raw_crop_sha256', 'raw_image_sha256']}
                    raw = resolve(r['raw_crop_path'], root)
                    reason = None
                    if r.get('annotation_overlays') is not False or r.get('raw_source_verified') is not True:
                        reason = 'UNVERIFIED_OR_OVERLAID'
                    elif r.get('source_video_sha256') != source['video_sha256']:
                        reason = 'SOURCE_VIDEO_MISMATCH'
                    elif not raw.is_file():
                        reason = 'MISSING_CROP'
                    elif digest(raw) != r['raw_crop_sha256']:
                        reason = 'CROP_HASH_MISMATCH'
                    else:
                        try:
                            entry['quality'] = quality(raw)
                            expected = r['canonical_metadata']['crop_dimensions']
                            if [entry['quality']['width'], entry['quality']['height']] != expected:
                                reason = 'CROP_DIMENSION_MISMATCH'
                        except (OSError, ValueError):
                            reason = 'CORRUPT_CROP'
                    entry['available'] = reason is None
                    if reason:
                        issues.append({'video_id': vid, 'observation_id': oid, 'reason': reason})
                    entry['raw_crop_path'] = raw.relative_to(root).as_posix()
                    observations.append(entry)
                    recordings[vid]['crop_signatures'].append(r['raw_crop_sha256'])
                    recordings[vid]['frame_signatures'][str(r['frame'])] = r['raw_image_sha256']
                observations.sort(key=lambda x: (x['frame'], x['observation_id']))
                if not observations:
                    issues.append({'epoch_id': original['candidate_epoch_id'], 'reason': 'EMPTY_EPOCH'})
                    continue
                chosen = select_crops(observations, cfg)
                first, last = observations[0], observations[-1]
                epochs.append({'epoch_id': original['candidate_epoch_id'], 'video_id': vid,
                    'start_frame': first['frame'], 'end_frame': last['frame'],
                    'start_time': first['time'], 'end_time': last['time'],
                    'end_time_semantics': 'last observed time, not builder discontinuity time',
                    'candidate_class': sorted({r['label'] for r in observations}),
                    'source_observations': observations,
                    'source_paths': [ref(ep, root), ref(mp, root), ref(sp, root)],
                    'hidden_provenance': {'serialized_epoch': original},
                    'selected_observation_ids': [r['observation_id'] for r in chosen],
                    'clean_crops': [], 'context_images': []})
                recordings[vid]['preview_frames'].extend(r['frame'] for r in chosen)
    if not epochs:
        raise ValueError('No canonical V297 epochs found')
    return epochs, recordings, issues


def split_recordings(recordings, cfg, root):
    union = Union(recordings)
    reasons = []
    exact = {}
    for vid, r in recordings.items():
        keys = [('video', r['video_sha256'])] + [('frame', h) for h in r['frame_signatures'].values()] + [('crop', h) for h in r['crop_signatures']]
        if r['explicit_session_id']:
            keys.append(('explicit_session', r['explicit_session_id']))
        for key in keys:
            if key in exact and exact[key] != vid:
                union.join(vid, exact[key])
                reasons.append({'a': vid, 'b': exact[key], 'basis': key[0]})
            else:
                exact[key] = vid
    # Inspect only original source pixels, never identity outputs or model predictions.
    previews = []
    for vid, r in recordings.items():
        cap = cv2.VideoCapture(str(root / r['video_path']))
        try:
            for frame in sorted(set(r['preview_frames'])):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
                ok, bgr = cap.read()
                if not ok:
                    raise OSError(f'Cannot decode {vid} frame {frame}')
                rgb = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                thumb = np.asarray(rgb.resize((16, 16)), dtype=np.int16)
                dh = dhash(rgb)
                for other, old_frame, old_dh, old_thumb in previews:
                    if other != vid and (dh ^ old_dh).bit_count() <= cfg['near_duplicate_hamming'] and np.mean(np.abs(thumb - old_thumb)) <= 8:
                        union.join(vid, other)
                        reasons.append({'a': vid, 'b': other, 'basis': 'near_duplicate_original_frame', 'frames': [frame, old_frame]})
                previews.append((vid, frame, dh, thumb))
        finally:
            cap.release()
    groups = defaultdict(list)
    for vid in sorted(recordings):
        groups[union.find(vid)].append(vid)
    ordered = sorted(groups.values(), key=lambda g: hashlib.sha256((str(cfg['seed']) + ':' + '|'.join(g)).encode()).hexdigest())
    ndev = max(1, min(len(ordered) - 1, round(len(ordered) * cfg['dev_fraction']))) if len(ordered) > 1 else 1
    sessions = []
    for i, videos in enumerate(ordered):
        sid = 'recording_group:' + hashlib.sha256('|'.join(videos).encode()).hexdigest()[:16]
        split = 'dev' if i < ndev else 'frozen'
        sessions.append({'session_id': sid, 'split': split, 'video_ids': videos,
                         'basis': 'explicit session / recording bytes / shared-frame union',
                         'cross_recording_session_metadata_available': all(recordings[v]['explicit_session_id'] for v in videos)})
        for v in videos:
            recordings[v].update(session_id=sid, split=split)
    return {'schema': 'pass_i_session_split_v1', 'seed': cfg['seed'], 'dev_fraction': cfg['dev_fraction'],
            'CASE_CHANGE_POLICY': cfg['CASE_CHANGE_POLICY'], 'sessions': sessions,
            'recordings': list(recordings.values()), 'grouping_evidence': reasons,
            'near_duplicate_audit': {'original_frames_checked': len(previews), 'hamming_max': cfg['near_duplicate_hamming'], 'mean_rgb_difference_max': 8},
            'frozen_before_inference': True, 'gpt_outputs_observed': False}


def packages(epochs, recordings, cfg, root, out):
    for e in epochs:
        e.update(session_id=recordings[e['video_id']]['session_id'], split=recordings[e['video_id']]['split'])
        token = hashlib.sha256(e['epoch_id'].encode()).hexdigest()[:20]
        directory = out / 'items/evidence' / token
        directory.mkdir(parents=True, exist_ok=True)
        selected = [r for r in e['source_observations'] if r['observation_id'] in e['selected_observation_ids']]
        for n, r in enumerate(selected, 1):
            p = directory / f'crop_{n:02d}.png'
            shutil.copyfile(root / r['raw_crop_path'], p)
            e['clean_crops'].append({**ref(p, root), 'observation_id': r['observation_id'], 'frame': r['frame'], 'time': r['time'],
                                   'width': r['quality']['width'], 'height': r['quality']['height'], 'upscaled': False})
        context_rows = selected[:1] + (selected[-1:] if len(selected) > 1 else [])
        cap = cv2.VideoCapture(str(root / recordings[e['video_id']]['video_path']))
        try:
            for n, r in enumerate(context_rows[:cfg['max_context_images']], 1):
                cap.set(cv2.CAP_PROP_POS_FRAMES, r['frame'])
                ok, img = cap.read()
                if not ok or hashlib.sha256(img.tobytes()).hexdigest() != r['raw_image_sha256']:
                    raise ValueError('Original context frame does not match stored pixels')
                p = directory / f'context_{n:02d}.jpg'
                Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(p, quality=95)
                e['context_images'].append({**ref(p, root), 'frame': r['frame'], 'time': r['time'],
                    'source_frame_sha256': r['raw_image_sha256'], 'annotation_overlays': False})
        finally:
            cap.release()


def sampling(a, b, cfg):
    ar, br = a['source_observations'], b['source_observations']
    la, lb = {r['local_track_id'] for r in ar}, {r['local_track_id'] for r in br}
    gap = max(0., b['start_time'] - a['end_time'], a['start_time'] - b['end_time'])
    tags = []
    if la & lb:
        tags.append('same_object_candidate_pairs')
    if {r['frame'] for r in ar} & {r['frame'] for r in br}:
        tags.append('different_object_candidate_pairs')
    if gap >= cfg['long_gap_seconds']:
        tags.append('long_gap_pairs')
        if la & lb:
            tags.append('reappearance_cases')
    aa = [r for r in ar if r['observation_id'] in a['selected_observation_ids']]
    bb = [r for r in br if r['observation_id'] in b['selected_observation_ids']]
    if any((int(x['quality']['dhash'], 16) ^ int(y['quality']['dhash'], 16)).bit_count() <= 6
           for x in aa for y in bb):
        tags.append('near_identical_phone_pairs')
    if any(r['quality']['blur_laplacian_variance'] < 30 or min(r['quality']['width'], r['quality']['height']) < 32 for r in aa + bb):
        tags.append('blur_low_quality_pairs')
    return {'sampling_attributes': tags, 'time_gap_seconds': gap,
        'rule': 'same-video unordered epoch combinations; shared local ID/coexistence/image-hash/quality proxies; NOT identity labels',
        'category_semantics': 'sampling hypotheses only; appearance proxy does not establish model/instance equality'}


def number_images(q, r):
    images = []
    for side, e in [('Q', q), ('R', r)]:
        for kind, key in [('phone_crop', 'clean_crops'), ('context', 'context_images')]:
            for n, p in enumerate(e[key], 1):
                images.append({'image_id': f'{side}-' + ('C' if kind == 'context' else '') + str(n),
                    'side': side, 'kind': kind, 'number': n, 'path': p['path'], 'sha256': p['sha256']})
    return images


def build_pairs(epochs, cfg, root, out):
    byvideo = defaultdict(list)
    for e in epochs:
        if e['clean_crops']:
            byvideo[e['video_id']].append(e)
    pairs, possible_counts = [], Counter()
    for video, es in sorted(byvideo.items()):
        pool = []
        for a, b in itertools.combinations(sorted(es, key=lambda e: (e['start_frame'], e['epoch_id'])), 2):
            gen = sampling(a, b, cfg)
            possible_counts.update(gen['sampling_attributes'])
            h = hashlib.sha256((str(cfg['seed']) + a['epoch_id'] + '|' + b['epoch_id']).encode()).hexdigest()
            pool.append((a, b, gen, h))
        # Deterministic round-robin across supported sampling strata, then hash fill.
        pool.sort(key=lambda x: x[3])
        categories = sorted({c for _, _, g, _ in pool for c in g['sampling_attributes']})
        queues = [[x for x in pool if c in x[2]['sampling_attributes']] for c in categories] + [pool]
        chosen, seen = [], set()
        cursors = [0] * len(queues)
        while len(chosen) < cfg['max_pairs_per_recording']:
            progress = False
            for i, queue in enumerate(queues):
                while cursors[i] < len(queue) and queue[cursors[i]][3] in seen:
                    cursors[i] += 1
                if cursors[i] < len(queue):
                    x = queue[cursors[i]]
                    chosen.append(x); seen.add(x[3]); progress = True
                    if len(chosen) >= cfg['max_pairs_per_recording']:
                        break
            if not progress:
                break
        for q, r, gen, _ in chosen:
            pairs.append({'query_epoch_id': q['epoch_id'], 'reference_epoch_id': r['epoch_id'],
                'session_id': q['session_id'], 'video_id': video, 'split': q['split'],
                'CASE_CHANGE_POLICY': cfg['CASE_CHANGE_POLICY'], 'pair_generation': gen,
                'images': number_images(q, r), 'gold_label': None})
    pairs.sort(key=lambda p: (p['video_id'], p['query_epoch_id'], p['reference_epoch_id']))
    for n, p in enumerate(pairs, 1):
        p['item_id'] = f'PI_{n:06d}'
        # Visible package contains no epoch/tracker/time/identity/sampling fields.
        public = {k: p[k] for k in ['item_id', 'CASE_CHANGE_POLICY', 'images']}
        file = out / 'items' / p['item_id'] / 'evidence.json'
        write(file, public)
        p['evidence_package'] = ref(file, root)
    return pairs, possible_counts


def validate_dataset(root=ROOT, out=OUT):
    errors, checks = [], 0
    def check(value, message):
        nonlocal checks
        checks += 1
        if not value:
            errors.append(message)
    inv = read_lines(out / 'manifests/candidate_epoch_inventory.jsonl')
    pairs = read_lines(out / 'manifests/pair_manifest.jsonl')
    split = read(out / 'manifests/session_split.json')
    epochs = {e['epoch_id']: e for e in inv}
    ss = {s['session_id']: s['split'] for s in split['sessions']}
    video_splits, source_splits, crop_splits = {}, {}, {}
    for e in inv:
        check(ss.get(e['session_id']) == e['split'], 'epoch session leakage')
        for key, container in [(e['video_id'], video_splits)]:
            check(container.setdefault(key, e['split']) == e['split'], 'video leakage')
        for r in e['source_observations']:
            h = r['raw_image_sha256']
            check(source_splits.setdefault(h, e['split']) == e['split'], 'source-frame overlap')
        for p in e['clean_crops']:
            check(crop_splits.setdefault(p['sha256'], e['split']) == e['split'], 'identical crop overlap')
    seen_files = {}
    from .adapter import build_request
    for n, p in enumerate(pairs, 1):
        check(p['item_id'] == f'PI_{n:06d}', 'item numbering')
        q, r = epochs[p['query_epoch_id']], epochs[p['reference_epoch_id']]
        check(q['session_id'] == r['session_id'] == p['session_id'], 'pair session leakage')
        check(q['split'] == r['split'] == p['split'], 'pair split leakage')
        check(p['images'] == number_images(q, r), 'Q/R numbering mismatch')
        for f in p['images'] + [p['evidence_package']]:
            file = root / f['path']
            if file not in seen_files:
                seen_files[file] = file.is_file() and sha(file) == f['sha256']
            check(seen_files[file], 'missing image/hash: ' + f['path'])
        public = read(root / p['evidence_package']['path'])
        check(set(public) == {'item_id', 'CASE_CHANGE_POLICY', 'images'}, 'public metadata leakage')
        # Serialize an actual request on every item; no client and no inference.
        build_request(public, 'Test-only externally supplied annotation instruction.', root)
    hashes = read(out / 'manifests/manifest_hashes.json')
    for path, h in hashes.items():
        check(sha(root / path) == h, 'manifest hash mismatch: ' + path)
    baseline = read(out / 'manifests/protected_before.json')
    current = protected_snapshot(root)
    check(current == baseline, 'protected V297/V2101 files changed')
    return {'passed': checks - len(errors), 'failed': len(errors), 'errors': errors,
            'protected_files_verified': len(baseline), 'unique_evidence_files_verified': len(seen_files)}


def build(root=ROOT, out=OUT, cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    if cfg['CASE_CHANGE_POLICY'] not in {'UNKNOWN', 'NO_CASE_CHANGES'}:
        raise ValueError('Invalid CASE_CHANGE_POLICY')
    if cfg['CASE_CHANGE_POLICY'] == 'NO_CASE_CHANGES' and not cfg.get('case_policy_verified_metadata'):
        raise ValueError('NO_CASE_CHANGES requires explicit verified experiment metadata')
    if (out / 'manifests/session_split.json').exists():
        raise FileExistsError('Dataset already frozen; validate or build a separate version')
    for name in ['manifests', 'items', 'prelabels', 'annotations', 'reports']:
        (out / name).mkdir(parents=True, exist_ok=True)
    write(out / 'config.json', cfg)
    write(out / 'manifests/protected_before.json', protected_snapshot(root))
    print('Discovering verified CandidateEpoch evidence...', flush=True)
    epochs, recordings, issues = inventory(root, cfg)
    print(f'Found {len(recordings)} recordings / {len(epochs)} epochs; checking shared source frames...', flush=True)
    split = split_recordings(recordings, cfg, root)
    write(out / 'manifests/session_split.json', split)
    print('Exporting original-resolution evidence...', flush=True)
    packages(epochs, recordings, cfg, root, out)
    pairs, possible = build_pairs(epochs, cfg, root, out)
    jsonl(out / 'manifests/candidate_epoch_inventory.jsonl', epochs)
    jsonl(out / 'manifests/pair_manifest.jsonl', pairs)
    write(out / 'reports/input_issues.json', issues)
    selected = Counter(c for p in pairs for c in p['pair_generation']['sampling_attributes'])
    categories = ['same_object_candidate_pairs', 'different_object_candidate_pairs', 'near_identical_phone_pairs',
        'front_vs_back_pairs', 'large_viewpoint_change_pairs', 'blur_low_quality_pairs',
        'partially_occluded_pairs', 'long_gap_pairs', 'reappearance_cases']
    summary = {'sessions': len(split['sessions']), 'recordings': len(recordings), 'epochs': len(epochs), 'pairs': len(pairs),
        'CASE_CHANGE_POLICY': cfg['CASE_CHANGE_POLICY'], 'gpt_called': False, 'human_labels': 0,
        'evidence': {'epochs_with_crops': sum(bool(e['clean_crops']) for e in epochs),
                     'clean_crops': sum(len(e['clean_crops']) for e in epochs),
                     'context_images': sum(len(e['context_images']) for e in epochs),
                     'crop_count_distribution': dict(Counter(len(e['clean_crops']) for e in epochs))},
        'splits': {s: {'sessions': sum(x['split'] == s for x in split['sessions']),
                      'recordings': sum(x['split'] == s for x in recordings.values()),
                      'epochs': sum(e['split'] == s for e in epochs), 'pairs': sum(p['split'] == s for p in pairs)} for s in ['dev', 'frozen']},
        'sampling_coverage': {c: {'available': possible[c], 'selected': selected[c],
            'basis': 'unsupported without human viewpoint/occlusion inspection' if c in ['front_vs_back_pairs', 'large_viewpoint_change_pairs', 'partially_occluded_pairs'] else 'metadata/image proxy, never gold'} for c in categories},
        'limitations': ['No explicit cross-video session metadata: recording-level fallback, shared-source checks and configurable overrides.',
                       'Known val regression videos are previously used material, not a new held-out system evaluation.',
                       'Near-duplicate source-frame audit covers all selected evidence frames; exact frame hashes cover all inventoried observations.',
                       'No visual identity labels or model predictions generated.']}
    write(out / 'reports/build_summary.json', summary)
    files = [out / 'config.json'] + list((out / 'manifests').glob('*.json*'))
    write(out / 'manifests/manifest_hashes.json', {p.relative_to(root).as_posix(): sha(p) for p in files if p.name != 'manifest_hashes.json'})
    from .annotations import AnnotationStore
    AnnotationStore(out).export(len(pairs))
    print(f'Prepared {len(pairs)} pairs; validating...', flush=True)
    result = validate_dataset(root, out)
    write(out / 'reports/dataset_validation.json', result)
    if result['failed']:
        raise ValueError(result['errors'])
    return summary, result
