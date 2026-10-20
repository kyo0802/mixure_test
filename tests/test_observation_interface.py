"""CPU contract checks using byte fixtures; no image fixtures or model inference."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from memory_graph.experiments.observation_interface import (
    AdapterValue, ObservationRequest, RawResponse, SourceFrame, execute_once)


class RecordingAdapter:
    def __init__(self,token_count=11,drop=False):
        self.loaded=0;self.generated=0;self.closed=0;self.tokens=token_count;self.drop=drop
    def load(self,settings):
        self.loaded+=1;return {"model":"CPU_TEST_DOUBLE_NOT_A_VLM"}
    def render(self,request):
        return AdapterValue("opaque test renderer",{"model_visible_text":request.task_instruction})
    def preprocess(self,frames,rendered,settings):
        aliases=[f.alias for f in frames]
        return AdapterValue(object(),{"consumed_aliases":aliases[:-1] if self.drop else aliases,"visual_tokens":self.tokens,"temporal_units":None})
    def generate(self,prepared,rendered,generation):
        self.generated+=1;return RawResponse('```json\nINVALID_TEST_TEXT\n```',{"real_inference":False})
    def resources(self):return {"gpu_used":False}
    def close(self):self.closed+=1


class ObservationInterfaceTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/".runtime"
        root.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=root);self.base=Path(self.tmp.name)
        source=self.base/"byte_fixture.bin";source.write_bytes(b"CPU provenance fixture, not a physical event")
        frame=SourceFrame("F0001",source,1,.1,hashlib.sha256(source.read_bytes()).hexdigest())
        self.request=ObservationRequest((frame,),"recorded_video_identity_only","system","task",{}, {"sampling":False},{"model":"test"},{})
    def tearDown(self):self.tmp.cleanup()
    def test_default_permission_and_hash_failure_precede_model_loading(self):
        adapter=RecordingAdapter()
        with self.assertRaises(PermissionError):execute_once(adapter,self.request,self.base/"out",lambda *_:{})
        self.request.frames[0].path.write_bytes(b"changed")
        with self.assertRaises(ValueError):execute_once(adapter,self.request,self.base/"out",lambda *_:{},allow_generation=True)
        self.assertEqual(adapter.loaded,0)
    def test_raw_survives_validator_error_and_no_same_directory_retry(self):
        adapter=RecordingAdapter();out=self.base/"run"
        def broken(*_):raise ValueError("intentional CPU validator failure")
        execute_once(adapter,self.request,out,broken,allow_generation=True)
        self.assertEqual((out/"raw.txt").read_text(), '```json\nINVALID_TEST_TEXT\n```')
        self.assertIn('VALIDATOR_ERROR',(out/"validation.json").read_text())
        with self.assertRaises(FileExistsError):execute_once(adapter,self.request,out,broken,allow_generation=True)
        self.assertEqual(adapter.generated,1)
        self.assertEqual(adapter.closed,1)
    def test_adapters_need_not_share_internal_visual_token_counts(self):
        for tokens in (11,97):
            adapter=RecordingAdapter(tokens)
            execute_once(adapter,self.request,self.base/str(tokens),lambda *_:{"test_only":True},allow_generation=True)
            self.assertEqual(adapter.generated,1)
    def test_silent_frame_loss_rejected_before_generation(self):
        adapter=RecordingAdapter(drop=True)
        with self.assertRaisesRegex(ValueError,'DROPPED'):
            execute_once(adapter,self.request,self.base/"bad",lambda *_:{},allow_generation=True)
        self.assertEqual(adapter.generated,0)
        self.assertEqual(adapter.closed,1)


if __name__=="__main__":unittest.main()
