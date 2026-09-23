"""Compare actual artifacts without equating model label changes with accuracy."""
import json
from pathlib import Path
from memory_graph.perception.track_manager import sha256


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


if __name__ == '__main__':
    rows = []
    for name,source in [('task1','test1.mp4'),('task2','test2.mp4')]:
        v1 = Path('outputs_v1_comparison')/name
        v2 = Path('outputs_v2')/name
        event_only = Path('outputs_v2_events')/name
        status = read(v2/'run_status.json')
        memory = read(v2/'memory_graph.json')
        event_ids = read(v2/'active_event_ids.json')
        raw = [read(v2/'events'/eid/'vlm_raw.json') for eid in event_ids]
        metadata = read(v2/'video_metadata.json')
        rows.append({'video':source,'source_sha256':sha256(source),
            'duration_seconds':metadata['duration'],'sampled_frames':len(metadata['sampled_frames']),
            'v1':read(v1/'run_status.json'),'v1_detections':len(read(v1/'detections.json')),
            'v2':status,'event_only':read(event_only/'run_status.json'),
            'vlm_backend':memory['metadata']['vlm_backend'],
            'hardware':memory['metadata']['hardware'],
            'recorded_model_generations':sum(len(r.get('generation_trace',[])) or 1 for r in raw),
            'geometry_rejected_relations':sum(len(read(v2/'events'/eid/'scene_graph.json')['rejected_relations']) for eid in event_ids),
            'selected_frame_indices':sorted({f['frame_index'] for eid in event_ids for f in read(v2/'events'/eid/'keyframes.json')}),
            'interpretation':'Label differences include synonyms and errors; these counts are not semantic accuracy.'})
    report = {'videos':rows,'detector_weights_sha256':sha256('yolo11s.pt')}
    Path('docs/v2_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    measurements = [
        ('Decoded frames',lambda r:r['v2']['decoded_frames']),
        ('Sampled frames',lambda r:r['sampled_frames']),
        ('V1 tracks',lambda r:r['v1']['tracks']),
        ('V1 anchors',lambda r:r['v1']['anchors']),
        ('V1 stable relation intervals',lambda r:r['v1']['stable_relations']),
        ('V2 tracks',lambda r:r['v2']['raw_track_ids']),
        ('V2 raw signals / merged / selected',lambda r:f"{r['v2']['raw_event_signals']} / {r['v2']['merged_events']} / {r['v2']['selected_events']}"),
        ('VLM valid / partial / failed events',lambda r:f"{r['v2']['vlm_analyzed_events']} / {r['v2']['vlm_partial_events']} / {r['v2']['vlm_failed_events']}"),
        ('Recorded model generations',lambda r:r['recorded_model_generations']),
        ('VLM component failures',lambda r:r['v2']['vlm_component_failures']),
        ('Admitted VLM labels / unknown',lambda r:f"{r['v2']['confirmed_semantic_entities']} / {r['v2']['unknown_entities']}"),
        ('Rejected tracks',lambda r:r['v2']['rejected_tracks']),
        ('VLM / geometry-only relation intervals',lambda r:f"{r['v2']['semantic_relations']} / {r['v2']['geometry_only_relations']}"),
        ('Rejected VLM relation claims',lambda r:r['geometry_rejected_relations']),
        ('Interaction relation intervals',lambda r:r['v2']['interaction_relations']),
        ('Observed relation transitions',lambda r:r['v2']['transitions']),
        ('Unique selected full-scene frames',lambda r:len(r['selected_frame_indices']))]
    text = '# Actual V1 / V2 measurements\n\n| Measurement | test1.mp4 | test2.mp4 |\n| --- | ---: | ---: |\n'
    for label,value in measurements:
        text += f'| {label} | {value(rows[0])} | {value(rows[1])} |\n'
    text += '\nPartial events are included in valid events: independently validated components survive, with failed components excluded. '
    text += 'Relation counts include sparse intervals and are not precision/recall or physical object counts. '
    text += 'V1 is a regenerated local baseline; original historical outputs were not present.\n'
    Path('docs/v2_comparison.md').write_text(text,encoding='utf-8')
    print(text)
