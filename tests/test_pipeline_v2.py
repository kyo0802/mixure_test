"""Integration fixtures are synthetic and never used as actual video evidence."""
import json
import cv2
import numpy as np
import pytest
from memory_graph.config_v2 import V2Config
from memory_graph import pipeline_v2
from memory_graph.video.reader import VideoReader
from v2_helpers import timelines


@pytest.mark.parametrize('mode', ['disabled', 'success', 'invalid'])
def test_v2_complete_artifacts_and_failure_isolation(tmp_path, monkeypatch, mode):
    source = tmp_path/'synthetic.mp4'
    writer = cv2.VideoWriter(str(source), cv2.VideoWriter_fourcc(*'mp4v'), 10, (100,100))
    assert writer.isOpened()
    for _ in range(60):
        writer.write(np.zeros((100,100,3), dtype=np.uint8))
    writer.release()
    tracks, _ = timelines([[(10,20)]*12, [(50,20)]*12], ['chair','chair'], step=.2)
    reader = VideoReader(source)
    list(reader.frames(5))
    monkeypatch.setattr(pipeline_v2, 'collect_tracks', lambda *args: (reader.metadata, [], tracks))

    class Backend:
        identity = {'backend':'synthetic-test-only', 'revision':'1'}
        def analyze_event(self, images, supplied, event):
            assert len(images) == 4 and all(cv2.imread(str(p)) is not None for p in images)
            if mode == 'invalid':
                return 'invalid JSON'
            return {'event_id':event['event_id'], 'entities':[
                {'track_id':t['track_id'], 'semantic_class':'chair', 'confidence':.9}
                for t in supplied], 'relations':[]}

    output = tmp_path/'v2'
    config = V2Config()
    config.events.max_vlm_events = 2
    memory = pipeline_v2.run_video_v2(source, config, output,
        backend=None if mode == 'disabled' else Backend())
    status = json.loads((output/'run_status.json').read_text())
    assert status['status'] == 'complete' and status['selected_events'] == 2
    assert len(memory.entities) == 2 and len({e.track_id for e in memory.entities}) == 2
    assert all(e.semantic_class == ('chair' if mode == 'success' else 'unknown') for e in memory.entities)
    assert status['vlm_failed_events'] == (2 if mode == 'invalid' else 0)
    for event_id in json.loads((output/'active_event_ids.json').read_text()):
        for name in ['before.jpg','during.jpg','after.jpg','event.json','keyframes.json',
                     'vlm_input.json','vlm_raw.json','scene_graph.json','scene_graph.png']:
            assert (output/'events'/event_id/name).is_file()
    assert (output/'annotated_v2.mp4').stat().st_size > 0
    assert (output/'memory_graph.png').is_file()
