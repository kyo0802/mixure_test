import json
import pytest
from memory_graph.pass_t.phase2b.common import Phase2BBlocked, canonical_bytes,digest
from memory_graph.pass_t.phase2b.local_vlm.catalog import SPECS
from memory_graph.pass_t.phase2b.local_vlm.nf4 import verify_assets,QwenNF4Runtime
from memory_graph.pass_t.phase2b.local_vlm.transport import LocalModelAdapter
from memory_graph.pass_t.phase2b.mocks import mock_payload

def minimal_snapshot(path):
    path.mkdir()
    values={'config.json':{'model_type':'qwen2_5_vl'},'model.safetensors.index.json':{'weight_map':{'tensor':'missing.safetensors'}},
        'download_provenance.json':{'repository':'Qwen/Qwen2.5-VL-7B-Instruct','revision':SPECS['qwen_nf4'].revision}}
    for name in ('preprocessor_config.json','tokenizer.json','tokenizer_config.json','chat_template.json'):values[name]={}
    for name,value in values.items():(path/name).write_text(json.dumps(value),encoding='utf8')

def test_nf4_and_awq_are_distinct():
    nf4=SPECS['qwen_nf4'];awq=SPECS['qwen_awq']
    assert nf4.model!=awq.model and nf4.revision!=awq.revision and nf4.quantization!=awq.quantization

def test_nf4_missing_processor_rejected(tmp_path):
    minimal_snapshot(tmp_path/'m');(tmp_path/'m/tokenizer.json').unlink()
    with pytest.raises(Phase2BBlocked,match='MISSING_PROCESSOR'):verify_assets(tmp_path/'m')

def test_nf4_missing_shard_rejected(tmp_path):
    minimal_snapshot(tmp_path/'m')
    with pytest.raises(Phase2BBlocked,match='MISSING_OR_UNSAFE_WEIGHT_SHARD'):verify_assets(tmp_path/'m')

def test_awq_checkpoint_not_loaded_as_nf4(tmp_path):
    minimal_snapshot(tmp_path/'m');(tmp_path/'m/config.json').write_text(json.dumps({'model_type':'qwen2_5_vl','quantization_config':{'quant_method':'awq'}}))
    with pytest.raises(Phase2BBlocked,match='NOT_AWQ'):verify_assets(tmp_path/'m')

def test_nf4_load_guard_precedes_gpu_work(monkeypatch,tmp_path):
    monkeypatch.delenv('PASS_T_LOCAL_RUNTIME_APPROVAL',raising=False)
    with pytest.raises(Phase2BBlocked,match='MODEL_LOAD_REQUIRES'):QwenNF4Runtime(SPECS['qwen_nf4'],{},tmp_path,{})

def test_synthetic_permission_does_not_authorize_unknown_payload(monkeypatch):
    spec=SPECS['qwen_nf4'];config={'backend':spec.backend,'model':spec.model,'revision':spec.revision,'execution_location':'LOCAL'}
    deployment={'endpoint':'http://127.0.0.1:8770','quantization':spec.quantization,'synthetic_only':True,
        'synthetic_payload_sha256_allowlist':[digest(b'authorized other fixture')]}
    monkeypatch.setenv('PASS_T_LOCAL_SYNTHETIC_APPROVAL','true');monkeypatch.delenv('PASS_T_PHASE2B_REAL_RUN_PERMISSION',raising=False)
    adapter=LocalModelAdapter(config,deployment,exchange=lambda *args:pytest.fail('Unexpected request'))
    with pytest.raises(Phase2BBlocked,match='LOCAL_INFERENCE_AUTHORIZATION_REQUIRED'):adapter.invoke(mock_payload(),{},1)
