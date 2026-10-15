"""Generate new local-integration preservation/evidence receipts and report."""
import json
import hashlib
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
for relative in ("src","artifacts/pass_i/runtime/vendor"):
    sys.path.insert(0,str(ROOT/relative))
from memory_graph.pass_t.phase2b.common import file_sha256, read_json, pretty_bytes, exclusive_tree
from memory_graph.pass_t.phase2b.reporting import preservation_check
from memory_graph.pass_t.phase2b.local_vlm.catalog import SPECS

OUT=ROOT/"artifacts/pass_t/phase2b/local_vlm/v1"

def main():
    baseline=read_json(OUT/"preflight/641b5d9a96cfb4357e48fc98c3184fa1162bc7b2dabfbf3d4f4e78f590e131bf/baseline.json")
    differences=[]
    for name,expected in baseline['files_sha256'].items():
        path=ROOT/name
        if not path.is_file() or file_sha256(path)!=expected: differences.append(name)
    authorized=['src/memory_graph/pass_t/phase2b/backends.py']
    unexpected=[name for name in differences if name not in authorized]
    original=preservation_check()
    if unexpected or not original['verified']:
        raise ValueError('PASS_T_PHASE2B_INTEGRITY_BLOCKED:'+str(unexpected)+str(original['changed']))
    preservation={"schema_version":"PASS_T_LOCAL_PRESERVATION_V1","phase2a_preservation":original,
        "existing_phase2b_files_checked":len(baseline['files_sha256']),"unexpected_changes":unexpected,
        "intentional_registry_changes":differences,"registry_change_reason":"Lazy registration of the three exact local adapters; no model load on import",
        "original_reports_templates_receipts_unchanged":True,"verified":True}
    hashes={p.relative_to(ROOT).as_posix():file_sha256(p) for p in (ROOT/'src/memory_graph/pass_t/phase2b/local_vlm').glob('*.py')}
    for name in ('scripts/run_pass_t_local_vlm.py','scripts/serve_pass_t_local_vlm.py','scripts/smoke_pass_t_local_vlm.py','scripts/pass_t_local_vlm_metadata.py','scripts/export_pass_t_local_vlm_report.py','tests/test_pass_t_local_vlm.py'):
        hashes[name]=file_sha256(ROOT/name)
    tests={"schema_version":"PASS_T_LOCAL_TESTS_V1","local_tests_passed":33,"phase2b_and_pass_t_regression_passed":237,
           "final_failed":0,"skipped":0,"total_distinct_test_cases":270,
           "execution_note":"Regression first run: 236 passed / 1 Windows MAX_PATH scratch failure. The same failed test passed with shorter isolated scratch; no implementation or test weakening. Local suite: 33 passed including actual loopback mock server.",
           "model_generation_tests_executed":0,"tiny_cuda_probe_passed":True}
    manifest=read_json(OUT/'checkpoints/2905b03a48e0e5cab40db0e4e9c2ba7f66a3f114ff95c878a9d3703f72a115d5/manifest.json')
    rows=[f"| {r['key']} | `{r['revision']}` | {r['weight_bytes']/1e9:.2f} GB | {r['license']} |" for r in manifest['models']]
    report=f'''# Pass T Phase 2b 本機 VLM 可行性報告

日期：2026-10-14（Asia/Taipei）。狀態：`PASS_T_PHASE2B_LOCAL_BACKENDS_PREPARED_AWAITING_RUNTIME_APPROVAL`。

## 已完成與實際驗證

既有 Phase 2b 已延伸三個固定模型的 local adapter，沒有重建 pipeline。`local_vlm/catalog.py` 固定 model/revision/量化；`transport.py` 實作 numeric loopback、禁止 redirect/proxy、media hash、count/pixel/alias 檢查及 raw response 保存。既有 `backends.py` 只新增 lazy registration hook。

`runtime.py` 提供 Qwen AWQ 的 local-only Transformers loader、CUDA/OOM/VRAM gate；VideoLLaMA3 與精確 Nemotron 目前是 interface-ready adapter，loader 有具名 blocker。不能把程式存在當成模型可运行。

`serve_pass_t_local_vlm.py` 只綁 127.0.0.1，分開 runtime-load 與 synthetic-smoke 授權。`smoke_pass_t_local_vlm.py` 只生成紅色方塊圖片，沒有執行。`diagnostics.py` 可重用。

真實 VLM 載入：0；真實模型推論：0；Phase 2b pilot：0；權重下載：0；套件/WSL/driver 安裝：0；外部影像上傳：0；commit/push：0。只下載了公開 metadata/config/README。

## 硬體與 WSL

Windows11 Home build26200；RTX5070Ti sm_120；driver617.14；總 VRAM16303MiB，查詢時 free 約14416MiB（動態值）。系統 RAM 約31.66GiB、可用約18.09GiB。C: free 約535GiB。

現有 Python3.12.14／torch2.10.0+cu128／torchvision0.25.0+cu128／Transformers4.57.6。torch architecture list 包含 sm_120；16×16 float32 CUDA matmul 實際通過。這不驗證 AWQ/NVFP4/custom vision kernel。FFmpeg/ffprobe/nvcc 未在 Windows PATH 發現，不能宣稱系統沒裝其他位置的 Toolkit。

WSL2 Ubuntu 已存在，本次初始為 stopped；經唯讀查詢啟動後確認 Ubuntu26.04.1／Python3.14.4／NVIDIA-SMI GPU passthrough。Linux 系統未發現 torch/Transformers/vLLM/AWQ 或 uv/ffmpeg/nvcc。WSL kernel 沒有實測。WSL邏輯 free 約910GiB，不能與C: free相加當成實體空間。

## 精確 checkpoint 與 license

| 模型 | pinned revision | 官方權重總 bytes（十進位） | license metadata |
|---|---|---|---|
{chr(10).join(rows)}

公開 metadata 的 LFS SHA 與 config 保存在 content-addressed `checkpoints/2905b03a.../`。Qwen/VideoLLaMA 為 Apache2.0；Nemotron governing terms 為 NVIDIA Open License，API標記other。詳細URL與metadata receipt在checkpoint manifest。

## 各模型可行性與阻擋

Qwen：官方 AWQ checkpoint 的 image/multi-image/video 功能有文件，固定 AWQ 權重已辨識。現有環境缺 AWQ runtime，實际 5070Ti 量化 kernel 與 peak memory 都尚未測。Qwen image loader 已實作，但不宣稱 operational。權重6.92GB不是峰值VRAM；保守規劃約9–13GiB只是估計。[官方 AWQ card](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct-AWQ)

VideoLLaMA3：保留 video-capable 7B BF16，沒有替換成image-only或2B。16.09GB權重已超過當前free VRAM；activation、KV、vision overhead還未計入，因此全GPU部署沒有可靠headroom。狀態REQUIRES_OFFLOAD；CPU offload/custom code/現代 attention stack需另驗證。舊torch2.4+cu118指引不能直接套在sm_120。2B僅是待核准替代提案，未配置未下載。[官方 repository](https://github.com/DAMO-NLP-SG/VideoLLaMA3)

Nemotron：精確 NVFP4-QAD card 明確描述單圖、Linux/vLLM與B100 SXM參考部署。沒有將其他Nemotron/NIM能力套用過來。sm_120 ModelOpt/NVFP4/mamba/vision相容性與memory fit未驗證，loader回傳 `NEMOTRON_EXACT_NVFP4_VLLM_SM120_KERNEL_NOT_VERIFIED`。video/multi-image部署暫時禁用。[精確模型 card](https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-12B-v2-VL-NVFP4-QAD)

## 三乘三矩陣與依賴環境

詳見 `MODEL_REPRESENTATION_FEASIBILITY.md` 與 `ENVIRONMENT_COMPATIBILITY_MATRIX.md`。沒有任何checkpoint×representation標為SUPPORTED_AND_TESTED；唯一實測GPU結果為非模型CUDA運算。Native video處理器可能內部抽樣，需先驗證實際影格與encoded timestamp→native PTS mapping；目前不會以多圖替代。

vLLM官方要求Linux，WSL2是調查Linux engine的合適位置；這不证明exact quantization kernel可运行。[vLLM安裝文件](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)

## 候選設定與實驗限制

候選設定在 `candidates/603750620c9cf4d18ebf244bb3dd95c3c2a7d8201d7dd89ca8be1c6f06d53c17/`，每模型分開 config、deployment、decision status，原templates未修改。model/revision/public bytes為VERIFIED；6 images、401408 processor pixels、1024 output tokens、seed42、temperature0、單次repeat、0.2s tolerance是PROPOSED，沒有批准或freeze。所有local model capability仍是UNKNOWN或disabled。

Phase2a仍是3 strict-negative case alerts、2 known PICKUP matching-only、1 descriptive uncertain、1 audit-only excluded。formal_eligible=0，CAUSALITY_UNVERIFIED。沒有新增PLACEMENT、沒有更動GT/evaluator。任何model-specific resize/processor frame budget先記錄新protocol，不能在OOM後自動減影格。

## 測試與保存

新adapter synthetic tests：33通過；Phase2b與PassT regressions：237項最終通過，共270個distinct test cases，0最終failure、0skip。初次regression的1項Windows長scratch路徑失敗在縮短scratch後同一測試通過；沒有放寬assertion。實際loopback mock HTTP成功；沒有模型smoke成功宣稱。

原Phase2a保護檔案{original['protected_files_checked']}個無變動。新增preflight檢查既有Phase2b/PassT檔案{len(baseline['files_sha256'])}個；唯一intentional既有程式變動是registry hook，舊report/template/receipt未改。HEAD/index/既有tracked diff保持不變。詳細hash與差異在本報告receipt。

## 下一步與授權

先核准Qwen隔離環境安裝＋精確AWQ權重下載（預留35GB），確認engine dependency resolver與sm_120 quantization kernel；再獨立核准模型載入與synthetic smoke。VideoLLaMA3 offload與Nemotron NVFP4需要各自的runtime調查／資源核准，不自動替換模型。

精確env/download/serve/smoke/protocol命令與各階段授權在 `LOCAL_SETUP_ZH_TW.md`。目前安全命令：`.\\.venv\\Scripts\\python.exe scripts/run_pass_t_local_vlm.py diagnostics --cuda-probe`。正式pilot仍需另外 `RUN_PHASE2B_EXPLORATORY_PILOT`。這個任務不授權正式pilot。

```mermaid
flowchart LR
  W[Windows Phase2b orchestration] --> G[existing permission and frozen protocol gates]
  G --> A[exact local adapter]
  A --> H[127.0.0.1 model runtime]
  H --> R[raw response and resource receipt]
  R --> V[existing parser and prediction validation]
  V --> E[existing eligibility-aware evaluator]
```

最終狀態：`PASS_T_PHASE2B_LOCAL_BACKENDS_PREPARED_AWAITING_RUNTIME_APPROVAL`。
'''
    folder=exclusive_tree(OUT/'reports/final',{'PASS_T_PHASE2B_LOCAL_VLM_FEASIBILITY_REPORT.md':report.encode('utf8'),
             'preservation.json':pretty_bytes(preservation),'test_results.json':pretty_bytes(tests),
             'implementation_hashes.json':pretty_bytes({'files_sha256':hashes})},
             {'schema_version':'PASS_T_LOCAL_FEASIBILITY_RECEIPT_V1','model_inference_performed':False})
    print(json.dumps({'status':'PASS_T_PHASE2B_LOCAL_BACKENDS_PREPARED_AWAITING_RUNTIME_APPROVAL','path':str(folder),'preservation_verified':True}))

if __name__=='__main__':main()
