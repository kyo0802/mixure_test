"""Explicit held-out phases. GT opening is not implemented in this inference runner."""
import argparse
import gc
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.dont_write_bytecode=True
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'Ultralytics')
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
from memory_graph.validation.common import OUT,VIDEOS,read,write,sha,source_hashes,check_sources,register

def run_one(video, runroot):
    from memory_graph.validation.upstream import run
    from memory_graph.validation.evidence import prepare
    from memory_graph.reasoning import pipeline,model
    import torch
    runroot.mkdir(parents=True,exist_ok=True)
    started=time.time()
    with model.Monitor() as monitor:
        upstream=run(video,runroot)
        gc.collect();torch.cuda.empty_cache()
        prepared=prepare(video,runroot)
        original=(pipeline.OUT,pipeline.write,model.OUT)
        pipeline.OUT=runroot/'prepared';pipeline.write=write;model.OUT=runroot/'prepared'
        try:
            requests=read(runroot/'prepared/qwen/requests.json')
            if requests:
                qwen=pipeline.run()
            else:
                qwen={'complete':True,'canonical_calls':0,'reason':'NO_COMPLETE_PHYSICAL_WINDOWS','inference_seconds':0}
                for name in ('responses','parsed_outputs','validator_results'):write(runroot/f'prepared/qwen/{name}.json',[])
                write(runroot/'prepared/qwen/runtime.json',qwen)
        finally:pipeline.OUT,pipeline.write,model.OUT=original
    responses=read(runroot/'prepared/qwen/responses.json')
    vals=read(runroot/'prepared/qwen/validator_results.json')
    proposals=[]
    for response,val in zip(responses,vals):
        answer=response.get('answer') or {}
        proposals.append({'pack_id':response['pack_id'],'candidate_relation':answer.get('final_relation'),
            'anchor':answer.get('final_relation_anchor'),'pre_review_disposition':'REJECTED' if not val['valid'] else 'UNCERTAIN',
            'reason':'Frozen offline mapping requires post-freeze evidence review; no trusted promotion before review.',
            'proposed_search_hint':None,'actual_trusted_writes':0})
    write(runroot/'memory_simulation.json',proposals)
    result={'video_id':video,'status':'COMPLETE','started_unix':started,'finished_unix':time.time(),
        'total_seconds':time.time()-started,'upstream':upstream,'windows':prepared,'qwen':qwen,**monitor.result()}
    write(runroot/'result.json',result)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['register','pilot','video','freeze-code','freeze-predictions'])
    ap.add_argument('--video',choices=VIDEOS);ap.add_argument('--attempt',default='pilot_01');a=ap.parse_args()
    if a.phase=='register':print(json.dumps(register(),ensure_ascii=False));return
    if a.phase=='freeze-code':
        if (OUT/'pre_run_freeze_manifest.json').exists():raise RuntimeError('Already frozen')
        write(OUT/'pre_run_freeze_manifest.json',{'frozen_unix':time.time(),'sources':source_hashes(),
            'ground_truth_read':False,'representation':'DENSE_ORDERED_EVENT_FRAMES'})
        return
    check_sources()
    if a.phase in {'pilot','video'}:
        if not a.video:raise ValueError('video required')
        if (OUT/'PREDICTION_FREEZE_COMPLETE.txt').exists():raise RuntimeError('Predictions sealed')
        if a.phase=='video' and not (OUT/'pre_run_freeze_manifest.json').exists():raise RuntimeError('Freeze code first')
        runroot=OUT/('preflight/'+a.attempt if a.phase=='pilot' else 'runs')/a.video
        try:result=run_one(a.video,runroot)
        except Exception:
            write(runroot/'failure.json',{'error':traceback.format_exc(),'unix':time.time(),'gt_read':False});raise
        check_sources();print(json.dumps({'video':a.video,'status':result['status'],'seconds':result['total_seconds'],'calls':result['qwen']['canonical_calls']}));return
    results=[read(OUT/'runs'/v/'result.json') for v in VIDEOS]
    if any(r['status']!='COMPLETE' for r in results):raise RuntimeError('Not all eleven complete')
    inputs=read(OUT/'input_manifest.json')
    for v in inputs['videos']:
        if sha(v['video_path'])!=v['video_SHA256'] or sha(v['txt_path'])!=v['txt_SHA256']:raise RuntimeError('Dataset changed')
    write(OUT/'predictions/per_video_predictions.json',results)
    files=[p for directory in ('runs','predictions') for p in (OUT/directory).rglob('*') if p.is_file()]
    manifest={'freeze_unix':time.time(),'gt_read':False,'files':{p.relative_to(OUT).as_posix():sha(p) for p in files},'sources':source_hashes()}
    write(OUT/'prediction_freeze_manifest.json',manifest)
    for rel,h in manifest['files'].items():
        if sha(OUT/rel)!=h:raise RuntimeError('Prediction freeze verification failed')
    (OUT/'PREDICTION_FREEZE_COMPLETE.txt').write_text('All eleven machine predictions SHA256 verified before any GT content access.\n'+str(time.time()),encoding='utf-8')

if __name__=='__main__':main()
