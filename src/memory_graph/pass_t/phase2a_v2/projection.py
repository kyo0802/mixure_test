"""Prepare neutral, verified, bounded visual evidence without earlier answers."""
import hashlib
import math
from pathlib import Path
from PIL import Image
from .policy import ROOT, OUT, read, sha, canonical, object_sha, exclusive, verify_gate, within, utc


def repeat_subset(ids):
    ordered = sorted(ids, key=lambda x: (hashlib.sha256(
        ('PASS_T_PHASE2A_REPEAT_V1|' + x).encode('utf-8')).hexdigest(), x))
    return ordered[:max(1, math.ceil(len(ids) / 4))] if ids else []


def neutral_observation(row):
    return {key: row[key] for key in
            ('candidate_id', 'observation_id', 'source_frame_index', 'bbox')}


def _verify_source(mapping, frames, refs, folder, generate=None):
    # Sequential decode is private. Only the bounded authorized frames are emitted.
    import av
    path = within(ROOT, mapping['source_video_path'])
    if sha(path) != mapping['source_video_hash']:
        raise ValueError('Source hash mismatch: ' + mapping['pack_id'])
    lo, hi = mapping['authorized_half_open_frames']
    start, end = mapping['window_start_s'], mapping['window_end_s']
    existing = {f['source_frame_index']: f for f in frames}
    reference_map = {r['source_frame_index']: r for r in refs}
    bounded = []
    checked_refs = set()
    with av.open(str(path)) as container:
        for index, frame in enumerate(container.decode(video=0)):
            if index >= hi:
                break
            if frame.pts is None:
                raise ValueError('Missing native PTS')
            time = float(frame.pts * frame.time_base)
            if index in reference_map:
                ref = reference_map[index]
                if not time < start or abs(time - ref['source_timestamp_s']) > 1e-6:
                    raise ValueError('Pre-window reference bound/PTS mismatch')
                rp = within(folder, ref['image_path'])
                if sha(rp) != ref['sha256']:
                    raise ValueError('Reference hash mismatch')
                left, top, right, bottom = ref['bbox']
                rect = (int(left), int(top), math.ceil(right), math.ceil(bottom))
                expected = frame.to_image().convert('RGB').crop(rect)
                with Image.open(rp) as actual:
                    if expected.size != actual.size or expected.tobytes() != actual.convert('RGB').tobytes():
                        raise ValueError('Reference/source pixel mismatch')
                checked_refs.add(index)
            if lo <= index < hi and start <= time < end:
                if frame.width != 1280 or frame.height != 720:
                    raise ValueError('Unexpected source geometry')
                if generate is not None:
                    fp = generate / 'frames' / f'S{index:06d}.png'
                    fp.parent.mkdir(parents=True, exist_ok=True)
                    if fp.exists():
                        raise ValueError('Asset already exists')
                    frame.to_image().convert('RGB').save(fp)
                    bounded.append({'frame_id': f'S{index:06d}', 'source_frame_index': index,
                                    'source_timestamp_s': time, 'timestamp_provenance': 'NATIVE_PTS',
                                    'image_path': fp.relative_to(ROOT).as_posix(), 'sha256': sha(fp)})
                else:
                    if index not in existing:
                        raise ValueError('Missing authorized full-rate frame')
                    row = existing[index]
                    fp = within(folder, row['image_path'])
                    if (row['frame_id'] != f'S{index:06d}' or row['timestamp_provenance'] != 'NATIVE_PTS'
                            or abs(row['source_timestamp_s'] - time) > 1e-6 or sha(fp) != row['sha256']):
                        raise ValueError('Frame ID/PTS/hash mismatch')
                    with Image.open(fp) as actual:
                        if actual.size != (1280, 720) or actual.convert('RGB').tobytes() != frame.to_image().convert('RGB').tobytes():
                            raise ValueError('Frame/source pixel mismatch')
                    bounded.append({**row, 'image_path': fp.relative_to(ROOT).as_posix()})
    if generate is None and len(bounded) != len(frames):
        raise ValueError('Out-of-window or duplicate frame')
    if len(checked_refs) != len(refs) or len(refs) > 3:
        raise ValueError('Unauthorized reference')
    if not bounded or any(b['source_frame_index'] != a['source_frame_index'] + 1
                          or b['source_timestamp_s'] <= a['source_timestamp_s']
                          for a, b in zip(bounded, bounded[1:])):
        raise ValueError('Native frame continuity/PTS failure')
    projected_refs = []
    for ref in refs:
        fp = within(folder, ref['image_path'])
        left, top, right, bottom = ref['bbox']
        projected_refs.append({k: ref[k] for k in
                               ('reference_id', 'source_frame_index', 'source_timestamp_s', 'sha256')})
        projected_refs[-1].update(image_path=fp.relative_to(ROOT).as_posix(),
                                  role='REFERENCE_PRE_WINDOW', citable=False,
                                  crop_to_source_transform=[[1, 0, int(left)], [0, 1, int(top)]])
    return bounded, projected_refs


def prepare(out=OUT):
    receipt = verify_gate(out)
    if (out / 'manifest.json').exists() or list((out / 'responses').glob('*.json')):
        raise ValueError('Preparation already frozen or responses exist; no regeneration')
    pt = ROOT / 'artifacts/pass_t'
    mappings = read(pt / 'manifests/window_target_mapping.json')['packs']
    outcomes = {x['pack_id']: x for x in read(pt / 'manifests/human_seed_outcomes_v1.json')['items']}
    review = {x['pack_id']: x for x in read(pt / 'human_seed_review/review_manifest.json')['items']}
    groups = {}
    for mapping in mappings:
        key = {'source_video_sha256': mapping['source_video_hash'],
               'window_start_s': mapping['window_start_s'], 'window_end_s': mapping['window_end_s'],
               'authorized_half_open_frames': mapping['authorized_half_open_frames']}
        id_ = 'PT2A_' + object_sha(key)[:16]
        if id_ in groups and groups[id_]['key'] != key:
            raise ValueError('Item hash collision')
        groups.setdefault(id_, {'key': key, 'mappings': []})['mappings'].append(mapping)
    entries, excluded = [], []
    for id_, group in sorted(groups.items()):
        mapping = group['mappings'][0]
        packs = [m['pack_id'] for m in group['mappings']]
        if any(m['overlap_group_id'] != mapping['overlap_group_id'] for m in group['mappings']):
            raise ValueError('Duplicate media overlap mismatch')
        original = outcomes.get(mapping['pack_id'])
        if original and not original['dev_eligible']:
            excluded.append({'annotation_item_id': id_, 'original_pack_ids': packs,
                             'stratum': 'EXCLUDED_OR_UNRESOLVED', 'dev_eligible': False,
                             'exclusion_reasons': original['ineligibility_reasons'],
                             'source_video_identifier': mapping['video_id'],
                             'overlap_group_id': mapping['overlap_group_id']})
            continue
        backend = {'phase1c_response_sha256': None, 'phase1c_reviewer_id': None}
        if original:
            info = review[mapping['pack_id']]
            ip = within(pt / 'human_seed_review', info['item_path'])
            if sha(ip) != info['item_sha256'] or not original['valid'] or not original['review_completed']:
                raise ValueError('Phase1c provenance invalid')
            raw = read(ip)
            # The raw outcome/response is discarded here; no previous rationale/citations reach the GUI.
            rp = within(pt, original['response_path'])
            if sha(rp) != original['response_sha256']:
                raise ValueError('Phase1c response hash mismatch')
            reviewer = read(rp)['primary_response']['annotator_id']
            selected = str(original['selected_local_candidate'])
            stratum = 'HUMAN_SEEDED_DEV'
            scope = 'HUMAN_VISUAL_LOCALIZATION_ONLY'
            frames, refs = _verify_source(mapping, raw['frames'], raw['references'], ip.parent)
            observations = [neutral_observation(o) for o in raw['observations']]
            backend.update(phase1c_response_sha256=original['response_sha256'],
                           phase1c_reviewer_id=reviewer, source_review_item_sha256=info['item_sha256'])
        else:
            if mapping['resolution_status'] != 'RESOLVED_UNIQUE' or mapping['method'] != 'EXPLICIT_SOURCE_TRACK_PROVENANCE_ONLY':
                raise ValueError('Unresolved source item')
            selected = str(mapping['resolved_local_track_id'])
            if any(str(m['resolved_local_track_id']) != selected for m in group['mappings']):
                raise ValueError('Deduplicated target mismatch')
            stratum = 'SOURCE_RESOLVED_DEV'
            scope = 'EXPLICIT_SOURCE_TRACK_PROVENANCE_ONLY'
            frames, refs = _verify_source(mapping, [], [], ROOT, generate=out / 'items' / id_)
            observations = [{'candidate_id': selected, 'observation_id': o['observation_id'],
                             'source_frame_index': o['frame_index'], 'bbox': o['bbox']}
                            for o in mapping['exact_observations']]
        indices = {f['source_frame_index'] for f in frames}
        observations = [o for o in observations if o['source_frame_index'] in indices and o['candidate_id'] is not None]
        visual = {'frames': frames, 'references': refs, 'width': 1280, 'height': 720,
                  'coordinate_system_id': 'REVIEW_FRAME_PIXELS_V1',
                  'frame_to_source_transform': [[1, 0, 0], [0, 1, 0]]}
        item = {'annotation_item_id': id_, 'original_pack_ids': packs,
                'source_video_identifier': mapping['video_id'], 'source_video_sha256': mapping['source_video_hash'],
                'window_start_s': mapping['window_start_s'], 'window_end_s': mapping['window_end_s'],
                'authorized_half_open_frames': mapping['authorized_half_open_frames'],
                'selected_local_candidate_id': selected, 'stratum': stratum, 'dev_eligible': True,
                'seed_provenance_scope': scope, 'binding_causality_status': 'CAUSALITY_UNVERIFIED',
                'overlap_group_id': mapping['overlap_group_id'], 'formal_eligible': False,
                'observations': observations, 'visual': visual,
                'authorized_visual_manifest_sha256': object_sha(visual)}
        path = out / 'items' / id_ / 'item.json'
        digest = exclusive(path, item, out)
        backend_sha = exclusive(out / 'private' / (id_ + '.json'), backend, out)
        entries.append({'annotation_item_id': id_, 'item_path': path.relative_to(out).as_posix(),
                        'item_sha256': digest, 'stratum': stratum,
                        'original_pack_ids': packs, 'source_video_identifier': mapping['video_id'],
                        'overlap_group_id': mapping['overlap_group_id'], 'backend_sha256': backend_sha})
    if len(entries) != 7 or len(excluded) != 1:
        raise ValueError('Unexpected eligibility inventory')
    manifest = {'schema_version': 'PASS_T_PHASE2A_REVIEW_MANIFEST_V2', 'created_at_utc': utc(),
                'policy_md_sha256': receipt['policy_md_sha256'], 'items': entries, 'excluded': excluded,
                'repeat_subset': repeat_subset([e['annotation_item_id'] for e in entries]),
                'repeat_seed': 'PASS_T_PHASE2A_REPEAT_V1|', 'recommended_delay_days': 7,
                'recording_session_independence': 'UNKNOWN', 'formal_eligible': 0,
                'preparation': 'Verified original pixels, hashes and native PTS; no event labeling',
                'source_resolved_reference_limitation': 'No inherited test1 full-rate reference assets; none fabricated'}
    exclusive(out / 'manifest.json', manifest, out)
    exclusive(out / 'manifest.freeze.json', {'manifest_sha256': sha(out / 'manifest.json'),
                                           'frozen_before_any_event_response': True, 'utc': utc()}, out)
    return manifest


def load_manifest(out=OUT):
    verify_gate(out)
    manifest = read(out / 'manifest.json')
    if sha(out / 'manifest.json') != read(out / 'manifest.freeze.json')['manifest_sha256']:
        raise ValueError('Manifest freeze mismatch')
    if manifest['repeat_subset'] != repeat_subset([e['annotation_item_id'] for e in manifest['items']]):
        raise ValueError('Repeat subset mismatch')
    return manifest


def load_item(entry, out=OUT, verify_visual=True):
    path = within(out, entry['item_path'])
    if sha(path) != entry['item_sha256']:
        raise ValueError('Review item hash mismatch')
    item = read(path)
    if object_sha(item['visual']) != item['authorized_visual_manifest_sha256']:
        raise ValueError('Visual authorization hash mismatch')
    if verify_visual:
        for row in item['visual']['frames'] + item['visual']['references']:
            if sha(within(ROOT, row['image_path'])) != row['sha256']:
                raise ValueError('Authorized visual asset changed')
    return item


def load_backend(entry, out=OUT):
    path = within(out, 'private/' + entry['annotation_item_id'] + '.json')
    if sha(path) != entry['backend_sha256']:
        raise ValueError('Backend provenance hash mismatch')
    return read(path)
