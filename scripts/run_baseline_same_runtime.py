"""Old clean windows, identical current Qwen runtime; frozen labels excluded from inference."""
import sys,os,time,json
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
task_cache=ROOT/'outputs/current_development/.runtime';task_cache.mkdir(exist_ok=True)
for key in ['TMP','TEMP','HF_HOME','TORCH_HOME']:os.environ[key]=str(task_cache)
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
from memory_graph.reasoning.common import OUT,read,sha256
from memory_graph.reasoning.pipeline import verify_reference,freeze_files,source_hashes
from memory_graph.reasoning.model import Backend,Monitor
from memory_graph.reasoning.contract import parse_json
from memory_graph.reasoning.validator import DirectReasoningValidator

def write(path,value):
    path=Path(path)
    if path==OUT/'final/baseline_prediction_manifest.json':
        if path.exists():raise RuntimeError('Baseline comparison is frozen')
    else:path.resolve().relative_to((OUT/'evaluation/runtime_matched_baseline').resolve())
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf8')

def run():
    folder=OUT/'evaluation/runtime_matched_baseline'
    if folder.exists() and any(folder.iterdir()):raise RuntimeError('One canonical baseline execution only')
    if not verify_reference()['valid']:raise ValueError('Baseline drift')
    folder.mkdir(parents=True,exist_ok=True);requests=read(ROOT/'outputs/reference_qwen/model_7b/requests.json')
    events={e['pack_id']:e for e in read(ROOT/'outputs/reference_qwen/event_packs/event_pack_manifest.json')}
    write(folder/'requests.json',requests);started=time.monotonic()
    with Monitor() as mon:backend=Backend()
    load={'seconds':time.monotonic()-started,**mon.result()};write(folder/'model_config.json',backend.identity())
    results=[];validations=[];validator=DirectReasoningValidator()
    for req in requests:
        if any(sha256(p)!=h for p,h in zip(req['images'],req['image_sha256'])):raise ValueError('Baseline image drift')
        raw='';answer=None;error=None;backend.last_trace={};print('Same-runtime old window',req['pack_id'],flush=True)
        try:raw=backend(req['images'],req['prompt'],1400);answer=parse_json(raw)
        except Exception as exc:error=type(exc).__name__+': '+str(exc)
        valid=validator.validate(events[req['pack_id']],answer)
        if not backend.last_trace.get('ended_with_EOS'):valid['valid']=False;valid['errors'].append('INCOMPLETE_GENERATION')
        results.append({'pack_id':req['pack_id'],'raw_output':raw,'answer':answer,'error':error,'compute_trace':backend.last_trace,'actual_inference':True,'retries':0})
        validations.append(valid);write(folder/'responses.json',results);write(folder/'validator_results.json',validations)
        print(answer,flush=True)
    runtime={'calls':len(results),'EOS_count':sum(r['compute_trace'].get('ended_with_EOS',False) for r in results),
        'runtime_errors':sum(r['error'] is not None for r in results),'load':load,'inference_seconds':sum(r['compute_trace']['runtime_seconds'] for r in results),
        'schema_valid':sum(v['schema_valid'] for v in validations),'validator_valid':sum(v['valid'] for v in validations)}
    write(folder/'runtime.json',runtime)
    write(OUT/'final/baseline_prediction_manifest.json',{'stage':'RUNTIME_MATCHED_BASELINE_FROZEN_BEFORE_REVIEW',
        'freeze_unix':time.time(),'files':freeze_files(OUT,list(folder.glob('*.json'))),
        'sources':{**source_hashes(),'scripts/run_baseline_same_runtime.py':sha256(Path(__file__))},
        'original_baseline_not_modified':True,'same_images_prompt_checkpoint_quantization':True})
    return runtime

if __name__=='__main__':print(run())
