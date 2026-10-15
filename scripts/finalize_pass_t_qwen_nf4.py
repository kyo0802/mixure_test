"""Preserve actual smoke evidence and prepare an unfrozen NF4 proposal/report."""
import json,sys,subprocess
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
for relative in ('src','artifacts/pass_i/runtime/vendor'):sys.path.insert(0,str(ROOT/relative))
from memory_graph.pass_t.phase2b.common import read_json,file_sha256,pretty_bytes,exclusive_tree
from memory_graph.pass_t.phase2b.reporting import preservation_check

OUT=ROOT/'artifacts/pass_t/phase2b/local_runtime/qwen_nf4'
V1='d6a3483296bee8e68e72d3de8635b87ac1d23512db28c3bb206adab48bd65c5c'
V2='8705118349b877ca45cf01bdade1810a0a82efbd7723167c55eea40cc6b718b0'
AUDIT='3dcbc1f0a680104e0beb27366691f9e68b5b88a4e8df354c67da0ff3c2a6cf57'
PREP='02c46a89902a6bbb0b576fab616d503ff801137086d5a45bf0c9fd9a028cafc8'

def main():
    import os,psutil,xml.etree.ElementTree as ET
    def long(path):return Path('\\\\?\\'+str(path.resolve())) if os.name=='nt' else path
    out=long(OUT)
    assets=read_json(out/'asset_audits'/AUDIT/'assets.json');historical=read_json(out/'asset_audits'/AUDIT/'historical_hashes.json')
    weight_changes=[name for name,expected in assets['files_sha256'].items() if file_sha256(Path(assets['path'])/name)!=expected]
    history_changes=[name for name,expected in historical.items() if file_sha256(ROOT/name)!=expected]
    protected=preservation_check()
    if weight_changes or history_changes or not protected['verified']:raise ValueError('PASS_T_PHASE2B_QWEN_NF4_INTEGRITY_BLOCKED')
    a=read_json(out/'smoke_results'/V1/'summary.json');b=read_json(out/'smoke_results'/V2/'summary.json')
    structured=b['records'][0]
    success=bool(b['health'] and structured['transport_generation_passed'] and (structured.get('validation') or {}).get('valid') and b['owned_runtime_exited'])
    status='PASS_T_PHASE2B_QWEN_NF4_REAL_SMOKE_PASSED_AWAITING_PROTOCOL_APPROVAL' if success else 'PASS_T_PHASE2B_QWEN_NF4_PARTIAL_SMOKE_WITH_BLOCKERS'
    preservation={'phase2a':protected,'model_files_checked':len(assets['files_sha256']),'model_bytes_unchanged':not weight_changes,
        'historical_files_checked':len(historical),'historical_bytes_unchanged':not history_changes,
        'weights_authoritative_upstream_checksums':'NOT_AVAILABLE_LOCALLY; revision supported by local download provenance and historical config',
        'no_graph_write':True,'no_actual_phase2a_inference':True,'no_commit_push':True}
    config=read_json(out/'prepared'/PREP/'config.json');config['complete']=False
    deployment=read_json(out/'prepared'/PREP/'deployment.json')
    deployment['approved']=False
    runtime_identity={'baseline_id':b['baseline_id'],'local_checkpoint_path':assets['path'],
        'revision_evidence':assets['revision_evidence'],'asset_audit_id':AUDIT,
        'effective_runtime':b['health']['effective_runtime'],'smoke_configuration':str(out/'prepared'/PREP),
        'smoke_only':True,'real_pilot_permission':False,'formatting_system_v2':deployment['response_format_system'],
        'actual_input_budgets':{'single_image':[224,224],'multi_image_count':3,'storyboard':[672,248],
                               'synthetic_video_frames':8,'synthetic_video_fps':4}}
    for rep,cap in config['capabilities'].items():
        cap.update(status='LOCALLY_VERIFIED',evidence=f'Actual synthetic generation and processor receipts V1 {V1}; single-image strict registry/parser receipt V2 {V2}. Scientific pilot and larger input budgets not tested.')
    proposals={'status':'PROPOSED_NOT_APPROVED_NOT_FROZEN','baseline_id':b['baseline_id'],
        'pilot_windows':['test1 W03/W05 deduplicated','test2 W01','test5 W01','test5 W05','test7 W05','test8 W07 descriptive only'],
        'excluded':'test3 W07','reference_policy':'NONE (target-localization limitations require review)',
        'uniform_image_count':3,'storyboard_same_selection':True,'processor_max_pixels':200704,
        'generation':{'max_output_tokens':512,'temperature':0,'sampling':False,'seed':42,'timeout_seconds':180},
        'repeat_count':1,'event_time_tolerance_s':0.2,'run_order':['MULTI_IMAGE','STORYBOARD','VIDEO only after approving actual processor frame budget'],
        'gpu_budget':'12GiB process budget proposed, >=2GiB free before inference, batch1, no CPU offload',
        'native_video':'8-frame/4fps synthetic proven only; real authorized-window processor FPS and sample count remain UNRESOLVED',
        'event_matching':'known supported PICKUP only; extra predictions UNEVALUATED; negatives case-alert only; uncertainty descriptive',
        'formatting_system_v2':'Proposed adapter formatting layer; event prompt bytes unchanged, user must approve for first pilot',
        'formal_eligible':0,'binding_causality_status':'CAUSALITY_UNVERIFIED'}
    tests={}
    for name in ('local_and_nf4','regression'):
        root=ET.parse(out/f'test_reports/{name}.xml').getroot();suite=next(iter(root))
        tests[name]={key:int(suite.attrib.get(key,0)) for key in ('tests','failures','errors','skipped')}
    test_total=sum(row['tests'] for row in tests.values())
    all_records=a['records']+b['records']
    resource_rows=[]
    for record in all_records:
        receipt=record.get('resource_receipt') or {}
        resource_rows.append(f"| {record['name']} | {receipt.get('generated_tokens','—')} | {receipt.get('runtime_seconds',0):.2f} | {receipt.get('peak_inference_vram_bytes',0)/2**30:.2f} | {'PASS' if (record.get('validation') or {}).get('valid') else 'FAIL'} |")
    loader=b['health'];peak=max((r.get('resource_receipt') or {}).get('peak_inference_vram_bytes',0) for r in all_records)
    report=f'''# Pass T Phase2b Qwen NF4 整合報告

日期：2026-10-14（Asia/Taipei）。最終狀態：`{status}`。

## 本次成果

既有 `.models/Qwen2.5-VL-7B-Instruct` 已實際載入並成功生成。NF4 double 4-bit、BF16、SDPA、CUDA placement 與 bitsandbytes0.50.2 已由有效runtime確認。未使用AWQ、3B或mock代替。model-loader初始化 v1 {a['health']['model_load_seconds']:.2f}s、v2 {loader['model_load_seconds']:.2f}s。

五次V1真實synthetic generation與一次V2 bounded repair均保存，沒有下載權重或套件，沒有重跑舊九窗口，也沒有任何Phase2a視窗推論、GT/evaluator/Graph修改、benchmark scoring、protocol freeze或commit/push。

## 既有元件重用與來源查證

通用loader設定沿用 `src/memory_graph/reasoning/model.py` 和 `src/memory_graph/vlm/local_backend.py` 的 NF4 double／BF16／SDPA/local_files_only 模式。重用 cuDNN SDPA優先、MATH fallback 的已工作kernel政策。僅提取通用模式，不匯入舊prompt、答案、GT或舊窗口。

native video沿用 `video_experiment.py` 的官方 apply_chat_template video路徑与透明sample_frames observer；仍由processor取樣，沒有用images冒充video。使用現有experiment `.deps` 的PyAV，不改主環境。

五個shard共 {assets['weight_bytes']:,} bytes，{assets['tensor_count']} tensor keys與index逐一核對。processor/tokenizer/provenance齊全，{len(assets['files_sha256'])}個模型檔案SHA已記錄並在結束重新比對。revision `cc594898137f460bfe9f0759e9844b3ce807cfb5` 由本機download_provenance与歷史config支持；沒有本機權威upstream weight checksum，因此不宣稱獨立官方checksum確認。

## 整合實作

- `local_vlm/nf4.py`：新的distinct NF4 runtime，資產檢查、10GiB GPU／8GiB RAM載入gate、2GiB inference headroom、實際量化與device確認。
- `catalog.py`：新增 `LOCAL_QWEN25_VL_NF4`，保留AWQ原candidate。
- `runtime.py`：沿用image生成，增加可選JSON formatting system layer和bounded generation deadline。
- `transport.py`：沿用numeric loopback/no redirect/no proxy；synthetic approval只接受已固定payload hash，正式pilot gate保持獨立。
- `serve_pass_t_local_vlm.py`：固定synthetic allowlist、單runtime lock与owned shutdown。
- `run_pass_t_qwen_nf4.py`：新synthetic fixtures、separateprocess、real registry adapter、嚴格parser與immutable receipts。

model-visible payload均通過既有allowlist与serialized leakage inspector，沒有PT2A ID、human event、GT timing、previous answer或reviewer資料。煙霧測試沒有呼叫GT evaluator。

## 真實測試狀態

| 測試 | 狀態 | 實際證據／限制 |
|---|---|---|
| Checkpoint load / effective NF4 | PASS | real_model、NF4設定、GPUdevice map已確認 |
| Real CUDA generation | PASS | 六次raw output與實際token/resource trace |
| Single-image modality | PASS | 224×224一張圖；processor grid1×16×16 |
| Multi-image modality | PASS | 三張不同圖；三個grid，原順序保留 |
| Storyboard modality | PASS | 672×248單圖；grid1×18×48；不是native video |
| Native synthetic video | PASS | 八影格4fps AVI，indices0–7全數處理；timestamps0–1.75s；video_grid_thw，非image-list |
| V1 strict JSON/citation validation | FAIL | 五次code fence；前三次还在80sdeadline時未完成 |
| V2 strict JSON/citation validation | {'PASS' if success else 'FAIL'} | 真實registry .invoke→raw storage→strict parser→validator，沒有修補模型输出 |
| Local loopback transport | PASS | 實際model HTTP，synthetic allowlist與hash檢查 |
| Clean unload | PASS | 两個owned runtime均退出；结束GPU讀数 `{b['post_unload_gpu']}` |

Modality能接受/生成，与strict structured-output成功分開報告。V1的single/multi/storyboard格式失败没有被刪除。V1 video與structured完整輸出仍因Markdown fence被strictparser拒絕；不剝除fence。

V2只执行一次：同checkpoint、同量化、同224×224图與相同既有事件prompt，加入「只输出compact JSON，不用Markdown」system格式指令；deadline80→180s，token cap768→512。這是明確版本化的engineering repair，不是已批准的scientific protocol；event prompt文件沒有改。

V2輸出schema/citation通過，但例如 `end_visibility=NOT_VISIBLE` 是模型声明，不能當作視覺正确或事件推理accuracy。Synthetic沒有人工event truth；本任務沒有计算accuracy、precision、recall、F1或hallucination rate。

## 實際資源

| smoke | generated tokens | inference seconds | peak allocated GiB | strict parser/validator |
|---|---:|---:|---:|---|
{chr(10).join(resource_rows)}

Model-load peak allocated {loader['model_load_peak_vram_bytes']/2**30:.2f}GiB；各次inference最大allocated {peak/2**30:.2f}GiB；reserved約6.85GiB。這些是torch process allocation，不是global WDDM peak。receipt內有每次GPU free/total snapshot；新的global peak與peak CPU RSS沒有連續取樣，不借用舊14.16GiB數字替代。offload=False、device_map整個cuda已實測。初次安全RAM查询可用約20GiB；本報告生成時RAM free {psutil.virtual_memory().available/2**30:.2f}GiB。

保留的warnings：fast processor default（歷史路徑也使用fast）、torch_dtype deprecation、greedy下temperature參數被忽略、bnb非對齊維度轉用較慢kernel、torchvision video decoder deprecation。沒有隐藏警告，也沒有降低batch/影格或更换baseline来掩盖失败。

## 測試與保護

Unit/mock/local-loopback suite {tests['local_and_nf4']['tests']}項，以及Phase2b/PassT regression {tests['regression']['tests']}項，合計{test_total}項，0failure／0error／0skip。這与兩次real-model load、六次actual synthetic generation分開计数。

原Phase2a {protected['protected_files_checked']}个保護檔案無变动，HEAD/index/既有tracked diff保持不变；{len(historical)}个歷史資料与loader檔案以及全部模型hash结束一致。AWQ原候選／舊immutable receipts未修改。權重只讀，沒有複製16.58GB到artifact。

## 待核准的下一步

新的NF4 candidate config、实际modality receipts与protocol proposal與此報告同目录。所有正式pilot參數仍是PROPOSED：uniform3張、storyboard相同3張、max_pixels200704、output512、timeout180、greedy/seed42、repeat1、time tolerance0.2s。較稀疏影格可能不足以定位短transition，這是科學輸入限制，不能由smoke通过推定。

Native video只证明8-frame／4fps synthetic输入；真实约100-frame authorized clips的processor抽樣budget与memory尚未批准。target reference NONE亦存在目标定位限制。formatting system V2須作為新protocol prompt/adapter version受你批准，不能沿用旧prompt hash假裝全部model-visible prompt不变。

你需批准：NF4 baseline與local revision证据、實際model-visible formatting、representations/frame/pixel budgets、reference政策、generation与repeat、matching tolerance、资源budget。之後另prepare/freeze完整protocol；再独立授权 `RUN_PHASE2B_EXPLORATORY_PILOT`。本次沒有该pilot authorization。

## 已实际執行命令

```powershell
.\\.venv\\Scripts\\python.exe scripts/run_pass_t_qwen_nf4.py prepare
.\\.venv\\Scripts\\python.exe scripts/run_pass_t_qwen_nf4.py run --prepared artifacts/pass_t/phase2b/local_runtime/qwen_nf4/prepared/8e9452240b27dfd89dec9e5ac04726d481f9fdbcccc714605178797c49cb9295
.\\.venv\\Scripts\\python.exe scripts/run_pass_t_qwen_nf4.py prepare-repair --prepared artifacts/pass_t/phase2b/local_runtime/qwen_nf4/prepared/8e9452240b27dfd89dec9e5ac04726d481f9fdbcccc714605178797c49cb9295
.\\.venv\\Scripts\\python.exe scripts/run_pass_t_qwen_nf4.py run --prepared artifacts/pass_t/phase2b/local_runtime/qwen_nf4/prepared/{PREP}
```

以上是已完成的bounded smoke，不是要求你重新跑。未来runtime仍須synthetic approval/hash inventory与单modellock；不應直接拿它跑DEV视窗。

最終狀態：`{status}`。
'''
    sources={p.relative_to(ROOT).as_posix():file_sha256(p) for p in (ROOT/'src/memory_graph/pass_t/phase2b/local_vlm').glob('*.py')}
    result=exclusive_tree(out/'reports',{'PASS_T_PHASE2B_QWEN_NF4_INTEGRATION_REPORT.md':report.encode('utf8'),
        'preservation.json':pretty_bytes(preservation),'model_config.candidate.json':pretty_bytes(config),
        'deployment.candidate.json':pretty_bytes(deployment),'baseline_runtime.json':pretty_bytes(runtime_identity),
        'protocol_proposal.json':pretty_bytes(proposals),'test_results.json':pretty_bytes(tests),
        'capability_report.json':pretty_bytes({'generation_modalities':{'single_image':'REAL_MODEL_SMOKE_PASSED','multi_image':'REAL_MODEL_SMOKE_PASSED','storyboard':'REAL_MODEL_SMOKE_PASSED','video':'REAL_MODEL_SMOKE_PASSED'},
            'structured_v1':'FAILED','structured_v2':'REAL_MODEL_SMOKE_PASSED' if success else 'FAILED','receipt_v1':V1,'receipt_v2':V2,'research_accuracy':'NOT_EVALUATED'}),
        'implementation_hashes.json':pretty_bytes({'files_sha256':sources})},
        {'schema_version':'PASS_T_NF4_INTEGRATION_RECEIPT_V1','status':status,'smoke_v1':V1,'smoke_v2':V2,'protocol_frozen':False})
    print(json.dumps({'status':status,'report_path':str(result/'PASS_T_PHASE2B_QWEN_NF4_INTEGRATION_REPORT.md'),'protected_verified':True},ensure_ascii=False))

if __name__=='__main__':main()
