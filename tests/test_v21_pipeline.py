import cv2
import numpy as np
from memory_graph.config_v2 import V2Config
from memory_graph.v21 import pipeline
from memory_graph import pipeline_v2
from memory_graph.v21.artifacts import read
from memory_graph.memory.memory_store import save_json
from v2_helpers import timelines


def test_identity_survives_zero_event_budget_and_v2_admission(tmp_path,monkeypatch):
    source=tmp_path/'synthetic.mp4'
    writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'mp4v'),10,(100,100))
    for _ in range(60):writer.write(np.zeros((100,100,3),np.uint8))
    writer.release()
    tracks,meta=timelines([[(10,20)]*2],['chair'],step=.2)
    def collect(source,path,config):
        save_json(path/'video_metadata.json',meta)
        save_json(path/'track_timelines.json',tracks)
        save_json(path/'detections.json',[])
        return meta,[],tracks
    monkeypatch.setattr(pipeline,'collect_tracks',collect)
    monkeypatch.setattr(pipeline_v2,'collect_tracks',collect)
    config=V2Config();config.events.max_vlm_events=0
    output=tmp_path/'v21'
    status=pipeline.run(source,config,output,events_only=True)
    assert status['persistent_entities']==1
    assert status['context_vlm']['attempted']==0
    assert read(output/'persistent_entities.json')[0]['semantic_class']=='unknown'
    assert read(output/'admission_failures.json')['v2_counterfactual_removed'][0]['track_id']==1
    assert read(output/'memory_graph.json')['relations']==[]
