from __future__ import annotations
import io
import json
import os
from pathlib import Path
import pytest
from PIL import Image
from memory_graph.pass_t.phase2b.common import Phase2BBlocked, digest, read_json
from memory_graph.pass_t.phase2b.config import unresolved_template
from memory_graph.pass_t.phase2b.local_vlm.catalog import SPECS, runtime_error
from memory_graph.pass_t.phase2b.local_vlm.transport import LocalModelAdapter, validate_endpoint, NoRedirect, request_json
from memory_graph.pass_t.phase2b.local_vlm.runtime import validate_local_snapshot, load_runtime
from memory_graph.pass_t.phase2b.mocks import mock_payload
from memory_graph.pass_t.phase2b.backends import MockBackend, real_backend
from memory_graph.pass_t.phase2b.predictions import parse_raw, validate_prediction

def setup(key="qwen_awq"):
    spec = SPECS[key]; config = unresolved_template()
    config.update(backend=spec.backend, model=spec.model, revision=spec.revision, execution_location="LOCAL")
    config["generation"] = {"temperature": 0, "sampling": False, "seed": 1, "max_output_tokens": 1024}
    deployment = {"endpoint": "http://127.0.0.1:8765", "quantization": spec.quantization,
                  "approved_representations": list(spec.documented), "max_images": 6,
                  "max_frames": 6, "max_input_pixels": 1_000_000}
    return config, deployment

def sample():
    image = Image.new("RGB", (64, 36), "white"); stream = io.BytesIO(); image.save(stream, format="PNG")
    blob = stream.getvalue(); payload = mock_payload(); payload["media"][0]["content_sha256"] = digest(blob)
    return payload, {"MEDIA_001": blob}

@pytest.mark.parametrize("url", ["https://127.0.0.1:8765", "http://example.com:8765", "http://localhost:8765", "http://127.0.0.1.evil:8765", "http://user:pass@127.0.0.1:8765", "http://127.0.0.1:8765/path", "http://127.0.0.1:8765?x=1"])
def test_non_numeric_loopback_endpoint_rejected(url):
    with pytest.raises(Phase2BBlocked): validate_endpoint(url)

def test_redirect_is_rejected():
    with pytest.raises(Phase2BBlocked): NoRedirect().redirect_request(None,None,302,"",{},"http://evil/")

def test_direct_transport_cannot_call_external_endpoint():
    with pytest.raises(Phase2BBlocked): request_json("http://example.com:80/generate",{},1)

def test_real_loopback_transport_with_mock_http_server():
    import threading
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            response=json.dumps({"echo":value}).encode()
            self.send_response(200);self.end_headers();self.wfile.write(response)
    server=HTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        response=request_json(f"http://127.0.0.1:{server.server_port}/generate",{"mock":True},2)
        assert response=={"echo":{"mock":True}}
    finally:
        server.shutdown();server.server_close();thread.join(2)

@pytest.mark.parametrize("key", list(SPECS))
def test_three_exact_model_adapters_construct_without_loading(key):
    config, deployment = setup(key)
    adapter = LocalModelAdapter(config, deployment)
    assert adapter.name == SPECS[key].backend

@pytest.mark.parametrize("field,value", [("model", "Qwen/Other"), ("revision", "main")])
def test_model_or_revision_substitution_rejected(field,value):
    config, deployment = setup(); config[field] = value
    with pytest.raises(Phase2BBlocked): LocalModelAdapter(config,deployment)

def test_quantization_substitution_rejected():
    config, deployment = setup(); deployment["quantization"] = "BF16"
    with pytest.raises(Phase2BBlocked): LocalModelAdapter(config,deployment)

def test_correct_request_and_no_source_paths():
    config, deployment = setup(); payload, media = sample()
    envelope = LocalModelAdapter(config,deployment).construct_request(payload,media)
    assert envelope["payload"] == payload and envelope["model"] == config["model"]
    assert "image_path" not in json.dumps(envelope) and "PT2A_" not in json.dumps(envelope)

@pytest.mark.parametrize("limit,value", [("max_images",0),("max_frames",1),("max_input_pixels",1)])
def test_oversized_input_rejected(limit,value):
    config, deployment = setup(); deployment[limit] = value; payload,media=sample()
    with pytest.raises(Phase2BBlocked): LocalModelAdapter(config,deployment).construct_request(payload,media)

def test_nemotron_multi_image_is_not_inferred_from_other_variant():
    config,deployment=setup("nemotron_nvfp4"); payload,media=sample()
    with pytest.raises(Phase2BBlocked,match="MODALITY_NOT_RUNTIME_APPROVED|MODALITY_NOT_DOCUMENTED"):
        LocalModelAdapter(config,deployment).construct_request(payload,media)

def test_video_not_substituted_with_image():
    config,deployment=setup(); deployment["approved_representations"]=["MULTI_IMAGE"]
    payload,media=sample(); payload["representation"]="REENCODED_AUTHORIZED_VIDEO"
    with pytest.raises(Phase2BBlocked): LocalModelAdapter(config,deployment).construct_request(payload,media)

def test_missing_weights_named_blocker(tmp_path):
    with pytest.raises(Phase2BBlocked,match="LOCAL_PINNED_WEIGHTS_MISSING"):
        validate_local_snapshot(SPECS["qwen_awq"],tmp_path/"missing",{"models":[]})

def test_load_requires_authorization_before_importing_model(monkeypatch,tmp_path):
    config,deployment=setup(); monkeypatch.delenv("PASS_T_LOCAL_RUNTIME_APPROVAL",raising=False)
    with pytest.raises(Phase2BBlocked,match="MODEL_LOAD_REQUIRES_RUNTIME_APPROVAL"):
        load_runtime(config,deployment,tmp_path,{})

@pytest.mark.parametrize("key,reason", [("videollama3_7b","OFFLOAD"),("nemotron_nvfp4","SM120")])
def test_unverified_engines_explicitly_blocked(key,reason,monkeypatch,tmp_path):
    config,deployment=setup(key); deployment["approved"]=True
    monkeypatch.setenv("PASS_T_LOCAL_RUNTIME_APPROVAL","true")
    with pytest.raises(Phase2BBlocked,match=reason): load_runtime(config,deployment,tmp_path,{})

def test_no_authorization_no_inference_call(monkeypatch):
    config,deployment=setup(); payload,media=sample(); calls=[]
    monkeypatch.delenv("PASS_T_PHASE2B_REAL_RUN_PERMISSION",raising=False)
    adapter=LocalModelAdapter(config,deployment,exchange=lambda *args:calls.append(args))
    with pytest.raises(Phase2BBlocked): adapter.invoke(payload,media,1)
    assert calls==[]

def test_health_requires_actual_model_and_kernel():
    config,deployment=setup(); spec=SPECS["qwen_awq"]
    health={"model":spec.model,"revision":spec.revision,"quantization":spec.quantization,
            "model_loaded":False,"kernel_verified":False}
    with pytest.raises(Phase2BBlocked): LocalModelAdapter(config,deployment,exchange=lambda *args:health).capability_check()

def test_raw_output_and_receipt_preserved_without_repair(monkeypatch,tmp_path):
    config,deployment=setup(); spec=SPECS["qwen_awq"]; payload,media=sample()
    monkeypatch.setenv("PASS_T_PHASE2B_REAL_RUN_PERMISSION","true")
    monkeypatch.setattr("memory_graph.pass_t.phase2b.local_vlm.transport.repository_root",lambda:tmp_path)
    health={"model":spec.model,"revision":spec.revision,"quantization":spec.quantization,
            "model_loaded":True,"kernel_verified":True,"tested_representations":["MULTI_IMAGE"]}
    raw=MockBackend("no_event").invoke(payload,{},1).decode()
    response={**health,"raw_output":raw,"processed_frame_aliases":payload["media"][0]["supplied_frame_aliases"]}
    def exchange(url,body,timeout): return health if url.endswith("/health") else response
    adapter=LocalModelAdapter(config,deployment,exchange=exchange)
    assert adapter.invoke(payload,media,1)==raw.encode()
    assert validate_prediction(parse_raw(raw.encode()),payload["media"][0]["supplied_frame_aliases"])["valid"]
    read_root = Path("\\\\?\\" + str(tmp_path)) if os.name == "nt" else tmp_path
    assert list(read_root.rglob("raw_output.txt"))[0].read_bytes()==raw.encode()

def test_dropped_frames_rejected_and_raw_retained(monkeypatch,tmp_path):
    config,deployment=setup(); spec=SPECS["qwen_awq"];payload,media=sample()
    monkeypatch.setenv("PASS_T_PHASE2B_REAL_RUN_PERMISSION","true")
    monkeypatch.setattr("memory_graph.pass_t.phase2b.local_vlm.transport.repository_root",lambda:tmp_path)
    health={"model":spec.model,"revision":spec.revision,"quantization":spec.quantization,
            "model_loaded":True,"kernel_verified":True,"tested_representations":["MULTI_IMAGE"]}
    response={**health,"raw_output":"malformed remains raw","processed_frame_aliases":["F0001"]}
    adapter=LocalModelAdapter(config,deployment,exchange=lambda url,*args:health if url.endswith("/health") else response)
    with pytest.raises(Phase2BBlocked,match="PROCESSOR_DROPPED"):
        adapter.invoke(payload,media,1)
    read_root = Path("\\\\?\\" + str(tmp_path)) if os.name == "nt" else tmp_path
    assert list(read_root.rglob("raw_output.txt"))[0].read_text()=="malformed remains raw"

@pytest.mark.parametrize("message,expected", [("CUDA out of memory","CUDA_OOM_NO_AUTOMATIC_RESAMPLING"),("no kernel image is available","GPU_KERNEL_ARCHITECTURE_INCOMPATIBLE"),("AWQ unsupported","QUANTIZATION_ENGINE_INCOMPATIBLE")])
def test_errors_are_specific_and_never_change_config(message,expected):
    assert runtime_error(RuntimeError(message))==expected
