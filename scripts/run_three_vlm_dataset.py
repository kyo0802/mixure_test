"""Sequential raw-first evaluation; exact dataset freeze, no human labels imported."""
from __future__ import annotations
import os,sys,json,hashlib,time,traceback,argparse,gc
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/pass_t/phase3/three_vlm_full_v1';sys.dont_write_bytecode=True
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
def ledger(model,record):
    with (OUT/f'{model}_ledger.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps({'utc':utc(),**record},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
def main(model):
    deps=[ROOT/'src',ROOT/'artifacts/pass_i/runtime/vendor',ROOT/'outputs/current_development/video_event_experiment/.deps']
    if model=='videollama':deps.insert(1,ROOT/'.runtime/videollama3/vendor')
    sys.path[:0]=list(map(str,deps))
    from memory_graph.experiments.observation_interface import SourceFrame,ObservationRequest,verify_sources
    from memory_graph.experiments.three_vlm_contract import validate_raw
    from memory_graph.experiments.three_vlm_adapters import VideoLLaMAFullAdapter,QwenFullAdapter
    freeze=read(OUT/'dataset_freeze.json')
    for p,h in freeze['components'].items():assert sha(ROOT/p)==h,('COMPONENT_HASH_MISMATCH',p)
    cfg=read(OUT/'configuration.json');prompt=read(OUT/'prompt.json');schema=read(OUT/'schema.json');windows=[w for w in read(OUT/'dataset.json')['windows'] if w['status']=='ELIGIBLE' and not w['duplicate_of']]
    base=OUT/'runs'/model;base.mkdir(parents=True,exist_ok=True)
    unfinished=[w for w in windows if not any((base/w['window_id']/name).exists() for name in ('receipt.json','failure.json'))]
    if not unfinished:print('ALL_TERMINAL_NO_MODEL_LOAD',model);return
    adapter=(QwenFullAdapter if model=='qwen' else VideoLLaMAFullAdapter)(ROOT);started=time.perf_counter();attempt=len(list(base.glob('model_load_*.json')))+1
    try:metadata=adapter.load(cfg['models'][model]);save(base/f'model_load_{attempt:02d}.json',{'utc':utc(),'metadata':metadata,'elapsed_s':time.perf_counter()-started,'adapter_source_sha256':sha(ROOT/'src/memory_graph/experiments/three_vlm_adapters.py')})
    except Exception as e:save(base/f'load_failure_{int(time.time())}.json',{'error':str(e),'traceback':traceback.format_exc(),'unfinished_windows':len(unfinished)});raise
    try:
        for w in unfinished:
            dest=base/w['window_id'];dest.mkdir(exist_ok=True)
            frames=tuple(SourceFrame(f['alias'],ROOT/f['path'],f['source_frame_index'],f['native_pts_s'],f['sha256']) for f in w['frames'])
            req=ObservationRequest(frames,w['source_video_sha256'],prompt['system'],prompt['task'],schema,cfg['generation'],cfg['models'][model],cfg['models'][model].get('preprocessing',{}));verify_sources(req)
            if (dest/'raw.txt').exists():
                if not (dest/'validation.json').exists():save(dest/'validation.json',validate_raw((dest/'raw.txt').read_text(encoding='utf8'),[f.alias for f in frames]))
                save(dest/'receipt.json',{'completed':True,'recovered_raw':True,'raw_sha256':sha(dest/'raw.txt'),'new_generation':False});continue
            if (dest/'started.json').exists():save(dest/'failure.json',{'classification':'INTERRUPTED_UNKNOWN_GENERATION_STATE_NO_AUTOMATIC_RETRY'});continue
            stage='PREPARE';tick=time.perf_counter();prepared=None;rendered=None
            try:
                adapter.check_resources(load=False);rendered=adapter.render(req);save(dest/'rendered.json',rendered.metadata)
                prepared=adapter.preprocess(frames,rendered,req.preprocessing);assert prepared.metadata['consumed_aliases']==[f.alias for f in frames]
                save(dest/'input.json',{'frames':w['frames'],'source_video_sha256':w['source_video_sha256'],'visual_input_sha256':w['visual_input_sha256'],'dataset_freeze_sha256':sha(OUT/'dataset_freeze.json'),'prompt_sha256':sha(OUT/'prompt.json'),'schema_sha256':sha(OUT/'schema.json'),'preprocessing':prepared.metadata})
                stage='GENERATE';save(dest/'started.json',{'utc':utc(),'maximum_generations':1});ledger(model,{'window':w['window_id'],'stage':'GENERATE_STARTED'})
                response=adapter.generate(prepared,rendered,cfg['generation'])
                with (dest/'raw.txt').open('xb') as f:f.write(response.text.encode('utf8'));f.flush();os.fsync(f.fileno())
                save(dest/'generation.json',response.metadata);stage='VALIDATE';save(dest/'validation.json',validate_raw(response.text,[f.alias for f in frames]))
                receipt={'completed':True,'utc':utc(),'elapsed_s':time.perf_counter()-tick,'raw_sha256':sha(dest/'raw.txt'),'dataset_freeze_sha256':sha(OUT/'dataset_freeze.json'),'resources':adapter.resources(),'quality_retries':0,'physical_support':'NOT_ESTABLISHED_BY_VALIDATION'}
                save(dest/'receipt.json',receipt);ledger(model,{'window':w['window_id'],'stage':'COMPLETED','elapsed_s':receipt['elapsed_s']});print('COMPLETED',model,w['window_id'],round(receipt['elapsed_s'],1),flush=True)
            except Exception as e:
                save(dest/'failure.json',{'stage':stage,'error_type':type(e).__name__,'error':str(e),'traceback':traceback.format_exc(),'raw_preserved':(dest/'raw.txt').exists(),'quality_retry':False});ledger(model,{'window':w['window_id'],'stage':'FAILED','error':str(e)});print('FAILED',model,w['window_id'],str(e),flush=True)
                if stage=='PREPARE' and isinstance(e,(TypeError,AttributeError,ImportError)):raise
            finally:prepared=None;rendered=None;adapter.cleanup()
    finally:adapter.close()
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('model',choices=['qwen','videollama']);main(parser.parse_args().model)
