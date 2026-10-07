from pathlib import Path
import pytest
from memory_graph.validation.common import ROOT, OUT, VideoRoot, read, write
from memory_graph.validation.upstream import ValidationContext
from memory_graph.events.window_builder import WindowConfig
from memory_graph.reasoning.common import read as read_json

def test_gt_sealed():
    if (OUT/'PREDICTION_FREEZE_COMPLETE.txt').exists():pytest.skip('Already legitimately unsealed')
    with pytest.raises(RuntimeError,match='sealed'):read(ROOT/'val_set/val_1.txt')

def test_video_routing_preserves_model_location():
    route=VideoRoot(str(ROOT))
    assert route/'val_11.mp4' == ROOT/'val_set/val_11.mp4'
    assert route/'.models/yolo11s.pt' == ROOT/'.models/yolo11s.pt'
    assert route/'test1.mp4' == ROOT/'test1.mp4'

def test_output_escape_rejected():
    with pytest.raises(ValueError):write(ROOT/'outputs/current_development/forbidden.json',{})

def test_frozen_builder_config():
    frozen=read_json(ROOT/'outputs/current_development/event_windows/config.json')
    assert WindowConfig().to_dict()==frozen['initial_global_config']

def test_route_context_restored():
    from memory_graph.v25rerun import adapter
    original=(adapter.ROOT,adapter.OUT,Path.cwd())
    with ValidationContext(OUT):
        assert adapter.ROOT/'val_1.mp4'==ROOT/'val_set/val_1.mp4'
        assert adapter.OUT==OUT.resolve()
    assert (adapter.ROOT,adapter.OUT,Path.cwd())==original
