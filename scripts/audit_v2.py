"""Audit real V2 artifacts; structural validity is not semantic ground truth."""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
from memory_graph.scene_graph.models import TemporalMemory, SceneGraph
from memory_graph.vlm.parser import parse_result


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def audit(output):
    output = Path(output)
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    status = read(output/'run_status.json')
    config = read(output/'run_config.json')
    metadata = read(output/'video_metadata.json')
    memory = TemporalMemory.model_validate(read(output/'memory_graph.json'))
    tracks = read(output/'track_timelines.json')
    selected = [e for e in read(output/'merged_events.json') if e['selected']]
    active = read(output/'active_event_ids.json')
    check(status['status'] == 'complete', 'pipeline incomplete')
    check(len(selected) <= config['events']['max_vlm_events'], 'event budget exceeded')
    check(set(active) == {e['event_id'] for e in selected}, 'active IDs disagree with selection')
    check(len(selected) == status['selected_events'], 'status selection count disagrees')
    track_ids = {t['track_id'] for t in tracks}
    ids = {e.track_id for e in memory.entities}
    check(len(ids) == len(memory.entities) and ids <= track_ids, 'memory IDs changed or duplicated')
    rejected = {t['track_id'] for t in read(output/'rejected_tracks.json')}
    check(not ids & rejected and ids | rejected == track_ids, 'admission partition incomplete')
    invalid = []
    for event in selected:
        directory = output/'events'/event['event_id']
        for name in ['before.jpg','during.jpg','after.jpg','event.json','keyframes.json',
                     'vlm_input.json','vlm_raw.json','scene_graph.json','scene_graph.png',
                     'prompt.txt','track_crops.jpg','track_crops.json']:
            check((directory/name).is_file(), f'{event["event_id"]}: missing {name}')
        frames = read(directory/'keyframes.json')
        check([f['phase'] for f in frames] == ['before','during','after'], 'phase names/order wrong')
        times = [f['timestamp'] for f in frames]
        check(times == sorted(times), f'{event["event_id"]}: phase timestamps inverted')
        supplied = set(frames[0]['supplied_track_ids'])
        check(supplied <= track_ids, 'supplied IDs absent from tracking')
        visible = set()
        for frame in frames:
            visible.update(frame['visible_track_ids'])
            check(set(frame['visible_track_ids']) <= supplied, 'visible ID not supplied')
            check(cv2.imread(str(directory/frame['image_path'])) is not None, 'unreadable event image')
        check(supplied == visible, 'supplied IDs have no visible grounding')
        crops = read(directory/'track_crops.json')['crops']
        check({crop['track_id'] for crop in crops} == supplied, 'crop reference IDs disagree')
        check(cv2.imread(str(directory/'track_crops.jpg')) is not None, 'unreadable crop reference')
        for crop in crops:
            frame = next((f for f in frames if f['frame_index'] == crop['source_frame_index']), None)
            check(frame is not None and crop['track_id'] in frame['visible_track_ids'], 'crop has no source observation')
        scene = SceneGraph.model_validate(read(directory/'scene_graph.json'))
        check({e.track_id for e in scene.entities} <= supplied, 'scene contains unsupplied ID')
        if scene.analysis_status in {'success','partial'}:
            result = parse_result(read(directory/'vlm_raw.json')['response'], supplied, event['event_id'])
            check((directory/'vlm_validated.json').is_file(), 'missing validated VLM result')
            if (directory/'vlm_validated.json').is_file():
                check(result.model_dump() == read(directory/'vlm_validated.json'), 'validated JSON differs from raw parse')
        else:
            invalid.append({'event_id':event['event_id'], 'status':scene.analysis_status})
            check(all(e.semantic_class == 'unknown' for e in scene.entities), 'semantics fabricated without VLM')
            check(all(not r.evidence.vlm for r in scene.relations), 'VLM relation fabricated')
    for relation in memory.relations:
        check(relation.subject_track_id in ids and
              (relation.object_track_id is None or relation.object_track_id in ids), 'dangling relation')
        check(bool(relation.observed_times) and all(relation.start_time <= t <= relation.end_time
              for t in relation.observed_times), 'invalid relation evidence interval')
        check(set(relation.event_ids) <= set(active), 'relation has unknown event provenance')
    for name in ['memory_graph.png', 'event_timeline.png']:
        check(cv2.imread(str(output/name)) is not None, f'unreadable {name}')
    cap = cv2.VideoCapture(str(output/'annotated_v2.mp4'))
    decoded = 0
    fps = cap.get(cv2.CAP_PROP_FPS)
    while cap.read()[0]:
        decoded += 1
    cap.release()
    check(decoded == metadata['frame_count'], 'annotated video is truncated')
    check(abs(fps-metadata['fps']) < .01, 'annotated video FPS changed')
    check(metadata['decoded_frame_count'] == metadata['frame_count'], 'source was not fully decoded')
    return {'output':str(output), 'structural_pass':not errors, 'errors':errors,
            'status':status, 'decoded_annotated_frames':decoded, 'event_analysis_statuses':invalid,
            'semantic_ground_truth_verified':False,
            'note':'Manual inspection is required; schema-valid VLM output can still be incorrect.'}


def preservation():
    historical, baseline = read('docs/v1_preservation_manifest.json'), read('docs/session_baseline_hashes.json')
    report = {'unchanged_this_session':[], 'changed_this_session':[], 'historical_mismatch':[], 'historical_missing':[]}
    for name, expected in historical.items():
        path = Path(name)
        if not path.is_file():
            report['historical_missing'].append(name)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            report['historical_mismatch'].append(name)
        prior = baseline.get(name.replace('\\','/'))
        if prior:
            report['unchanged_this_session' if actual == prior else 'changed_this_session'].append(name)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('outputs', nargs='+')
    parser.add_argument('--report', default='docs/v2_artifact_audit.json')
    args = parser.parse_args()
    report = {'runs':[audit(path) for path in args.outputs], 'v1_preservation':preservation()}
    Path(args.report).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    raise SystemExit(int(any(not r['structural_pass'] for r in report['runs']) or
                         bool(report['v1_preservation']['changed_this_session'])))
