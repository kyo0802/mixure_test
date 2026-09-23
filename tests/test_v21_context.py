import json
from types import SimpleNamespace as S
import cv2
import numpy as np
from memory_graph.v21.context import build_context
from memory_graph.v21.contracts import IdentityConfig


def test_before_visible_identity_survives_zero_supplemental_budget(tmp_path):
    video=tmp_path/'clip.mp4'
    writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'mp4v'),5,(64,64))
    for _ in range(10):writer.write(np.zeros((64,64,3),np.uint8))
    writer.release()
    frames=[{'phase':p,'frame_index':i,'timestamp':i/5,'visible_track_ids':[1] if i==0 else [],
             'supplied_track_ids':[1]} for p,i in [('before',0),('during',3),('after',6)]]
    (tmp_path/'keyframes.json').write_text(json.dumps(frames))
    obs=S(frame_index=0,timestamp=0,bbox=(2,2,20,20),confidence=.9)
    context,images=build_context(tmp_path,[S(track_id=1,observations=[obs])],{1:'entity_1'},video,
                                IdentityConfig(max_missing_context=0))
    assert len(images)==1 and context['historical_references'][0]['required_before_visible_context']
    assert context['historical_references'][0]['phase_visibility']['after']=='UNOBSERVED'
    assert context['historical_references'][0]['current_bbox_when_unobserved'] is None
