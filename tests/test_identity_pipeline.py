"""Real IO adapter checks using tiny deterministic perception fixtures."""
import json
from pathlib import Path
import numpy as np
import cv2
import pytest
from memory_graph.identity import pipeline

class Embed:
    def vector(self,image,box):return (1.,0.)

def test_replay_only_raw_evidence_not_legacy_identity(tmp_path,monkeypatch):
    monkeypatch.setattr(pipeline,'OUT',tmp_path)
    source=tmp_path/'source';(source/'perception').mkdir(parents=True)
    video=tmp_path/'small.mp4';writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'mp4v'),5,(32,32))
    for _ in range(7):writer.write(np.full((32,32,3),120,np.uint8))
    writer.release()
    frames=[{'frame_index':i,'timestamp':i/5} for i in range(7)]
    rows=[{**f,'bbox':[4,4,20,25],'confidence':.9,'class_name':'cell phone'} for f in frames]
    (source/'video_metadata.json').write_text(json.dumps({'fps':5,'width':32,'height':32,'sampled_frames':frames}))
    (source/'perception/tracks.json').write_text(json.dumps([{'track_id':7,'detector_class':'cell phone','observations':rows}]))
    (source/'perception/yolo_detections.json').write_text(json.dumps(rows))
    (source/'identity').mkdir();(source/'identity/entity_registry.json').write_text('INVALID MALICIOUS OLD AUTHORITY')
    metrics=pipeline.replay(source,video,tmp_path/'new',embedder=Embed())
    assert metrics['initial_binding'] and metrics['authorized_observations']==5
    assert metrics['unauthorized_matched']==0
    assert (tmp_path/'new/identity.json').exists()

def test_output_cannot_escape_identity_tree():
    with pytest.raises(ValueError):pipeline.safe_output(pipeline.ROOT/'outputs/validation')
    with pytest.raises(ValueError):pipeline.safe_output(pipeline.ROOT.parent/'mixure_test')

def test_active_identity_has_no_legacy_authority_imports():
    import ast
    forbidden={'memory_graph.v23.fusion','memory_graph.v24.reid','memory_graph.v25rerun.fusion',
        'memory_graph.v25rerun.reid','memory_graph.v26.pipeline','memory_graph.v292.pipeline',
        'memory_graph.validation.upstream','memory_graph.events.development_sources'}
    for path in Path(pipeline.__file__).parent.glob('*.py'):
        tree=ast.parse(path.read_text(encoding='utf8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):assert node.module not in forbidden

def test_synthetic_policy_is_not_production():
    from memory_graph.identity.contracts import Policy
    assert not Policy().automatic_confirmation_enabled
