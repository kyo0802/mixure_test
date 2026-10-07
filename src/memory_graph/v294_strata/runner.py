"""Explicit V294 IO; immutable identity input and unchanged builder/renderer."""
import hashlib
import json
import time
from pathlib import Path

from .api import StrataClient
from .prompts import prompt, TEMPLATE
from .resources import ResourceMonitor
from memory_graph.reasoning.validator import DirectReasoningValidator

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'outputs/v294_qwen38'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def save(path, data):
    path = Path(path).resolve()
    if not path.is_relative_to(OUT.resolve()):
        raise ValueError('V294 results must stay under outputs/v294_qwen38')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf8')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def current_sources():
    for group, prefix, numbers in [('development', 'test', range(1, 10)), ('known_validation_regression', 'val_', range(1, 12))]:
        for n in numbers:
            name = prefix+str(n)
            source = ROOT/f'outputs/identity_rebuild/{group}/runs_final/{name}/authorized_rows.json'
            video = ROOT/f'{name}.mp4' if group == 'development' else ROOT/f'val_set/{name}.mp4'
            yield name, group, source, video


def prepare():
    # This is called only after standalone smoke checks pass.
    smoke = read(OUT/'smoke/gate.json')
    if not smoke.get('passed'):
        raise RuntimeError('Standalone Strata smoke gate must pass before FindMind integration')
    if (OUT/'event_windows/events.json').exists():
        raise FileExistsError('V294 event packs already frozen')
    import cv2
    from memory_graph.events.window_builder import WindowConfig, target_timeline, select_events, select_context, dense_frames
    from memory_graph.reasoning.pipeline import render_frame, contact_sheet
    cfg = WindowConfig(); events = []; diagnostics = []
    for video_id, group, source, video in current_sources():
        raw = read(source)
        video_hash = sha(video)
        if video_hash != read(source.parent/'metrics.json')['video_sha256']:
            raise ValueError('Video changed since the current identity ledger: ' + video_id)
        if any(r.get('source') != 'final_revocation_filtered_ledger' for r in raw):
            raise ValueError('Only current final authorized ledger inputs allowed')
        rows = target_timeline(raw, cfg)
        pool, selected, queues = select_events(rows, cfg)
        cap = cv2.VideoCapture(str(video))
        try:
            for i, e in enumerate(selected):
                contexts = select_context(rows, e, cfg)
                event = {**e, 'pack_id': f'{video_id}__W{i+1:02d}', 'video_id': video_id, 'group': group,
                         'target_id': 'phone_01', 'representation': 'DENSE_ORDERED_EVENT_FRAMES',
                         'contexts': contexts, 'markers': [c['marker'] for c in contexts],
                         'actor_markers': [c['marker'] for c in contexts if c['role'] == 'INTERACTION_ACTOR_CANDIDATE'],
                         'location_markers': [c['marker'] for c in contexts if c['role'] == 'LOCATION_ANCHOR_CANDIDATE'],
                         'physical_reasoning_eligible': e['category'] == 'PHYSICAL_INTERACTION_EVENT' and e['completeness'] == 'COMPLETE_EVENT_WINDOW',
                         'authorized_source': str(source), 'authorized_source_sha256': sha(source),
                         'video_path': str(video), 'video_sha256': video_hash, 'frames': []}
                paths = []
                if e['category'] == 'PHYSICAL_INTERACTION_EVENT':
                    for row in dense_frames(rows, e, cfg):
                        row = {**row, 'phase': 'BEFORE' if row['time'] < e['transition_time'] else 'DURING' if row['time'] <= e['transition_time']+.6 else 'AFTER'}
                        cap.set(cv2.CAP_PROP_POS_FRAMES, row['frame']); ok, image = cap.read()
                        if not ok:
                            raise OSError('Cannot decode ' + video_id)
                        path = OUT/f'event_windows/frames/{event["pack_id"]}/f{row["frame"]:06d}.png'
                        render_frame(image, row, event, contexts, path); paths.append(path)
                        event['frames'].append({'frame': row['frame'], 'time': row['time'], 'phase': row['phase'],
                                                'image_path': str(path), 'sha256': sha(path), 'dimensions': [800, 600],
                                                'target_marked': row['identity_authorized'], 'target_bbox': row['target_bbox'],
                                                'identity_authorization_provenance': row['target_authorization_provenance']})
                    contact_sheet(paths, OUT/f'event_windows/review_sheets/{event["pack_id"]}.png', event)
                events.append(event)
        finally:
            cap.release()
        diagnostics.append({'video_id': video_id, 'group': group, 'source_sha256': sha(source),
                            'selected_events': len(selected), 'candidate_events': len(pool), 'queues': queues})
    save(OUT/'event_windows/events.json', events)
    save(OUT/'event_windows/builder_freeze.json', {'config': cfg.to_dict(), 'diagnostics': diagnostics,
                                                 'builder_sha256': sha(ROOT/'src/memory_graph/events/window_builder.py'),
                                                 'selection_changed': False, 'renderer_changed': False})
    (OUT/'prompts').mkdir(exist_ok=True)
    (OUT/'prompts/prompt_v294_final.txt').write_text(TEMPLATE, encoding='utf8')
    save(OUT/'prompts/prompt_iterations.json', {'versions': [{'version': 1, 'description': 'Chronological state change, release evidence, conservative relations and identity boundaries',
                                                            'sha256': sha(OUT/'prompts/prompt_v294_final.txt')}], 'selected': 1})
    return {'physical': sum(e['category'] == 'PHYSICAL_INTERACTION_EVENT' for e in events),
            'eligible': sum(e['physical_reasoning_eligible'] for e in events), 'total': len(events)}


def infer(event, dest, client=None, diagnostic=False):
    client = client or StrataClient()
    dest = Path(dest)
    if dest.exists():
        raise FileExistsError('Inference output already exists')
    images = [Path(f['image_path']) for f in event['frames']]
    if not images or any(sha(p) != f['sha256'] for p, f in zip(images, event['frames'])):
        raise ValueError('Missing or changed evidence images')
    if any(a['frame'] >= b['frame'] for a, b in zip(event['frames'], event['frames'][1:])):
        raise ValueError('Non-chronological event frames')
    client.health()
    started = time.monotonic(); response = None; error = None
    with ResourceMonitor() as monitor:
        try:
            response = client.complete(prompt(event), images)
        except Exception as exc:
            error = type(exc).__name__ + ': ' + str(exc)
    validation = DirectReasoningValidator().validate(event, response['answer'] if response else None)
    result = {'pack_id': event['pack_id'], 'video_id': event['video_id'], 'group': event['group'],
              'event_category': event['category'], 'completeness': event['completeness'],
              'diagnostic_only': diagnostic, 'physical_reasoning_eligible': event['physical_reasoning_eligible'],
              'event_sha256': hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest(),
              'request': {'images': [str(p) for p in images], 'image_sha256': [sha(p) for p in images], 'prompt': prompt(event)},
              'response': response, 'raw_response_if_invalid': client.last_public if error else None,
              'error': error, 'validation': validation, 'wall_seconds': time.monotonic()-started,
              'resources': monitor.summary(), 'operational_graph_writes': 0, 'identity_writes': 0, 'bank_writes': 0}
    try:
        result['server_timings'] = client.request('/v1/status').get('last_timings')
    except Exception:
        result['server_timings'] = None
    save(dest, result)
    return result


def run(first=False, include_incomplete=False):
    events = read(OUT/'event_windows/events.json')
    candidates = [e for e in events if e['frames'] and (e['physical_reasoning_eligible'] or include_incomplete)]
    if first:
        candidates = [e for e in candidates if e['video_id'] == 'test2' and e['physical_reasoning_eligible']][:1]
    else:
        gate = read(OUT/'smoke/findmind_pack_test.json')
        if gate['error'] or not gate['validation']['valid']:
            raise RuntimeError('First real FindMind pack must finish with a valid canonical result')
    for event in candidates:
        dest = OUT/'smoke/findmind_pack_test.json' if first else OUT/f'coder/runs/{event["pack_id"]}.json'
        if dest.exists():
            previous = read(dest)
            expected = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
            if previous['event_sha256'] != expected or previous['request']['prompt'] != prompt(event):
                raise ValueError('Existing result has different evidence or prompt; archive it before rerunning')
            continue
        if not first and event['pack_id'] == gate['pack_id']:
            # The first actual V294 call is part of the selected batch; do not run it twice.
            expected = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()
            if gate['event_sha256'] != expected or gate['request']['prompt'] != prompt(event):
                raise ValueError('First pack or prompt changed; do not reuse smoke result')
            save(dest, {**gate, 'from_first_smoke': True})
            continue
        result = infer(event, dest, diagnostic=not event['physical_reasoning_eligible'])
        print(event['pack_id'], result['error'] or result['response']['answer'], round(result['wall_seconds'], 2), flush=True)
        if result['error']:
            raise RuntimeError('Stop batch after runtime/API failure')
        if result['resources']['min_system_ram_available_bytes'] < 256*2**20:
            raise RuntimeError('Stop batch: severely depleted available RAM')
