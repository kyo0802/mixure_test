"""Authorized NF4 synthetic-only execution; never imports the GT evaluator."""
from __future__ import annotations
import argparse,base64,io,json,os,subprocess,sys,time,traceback
from pathlib import Path
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
for relative in ("src","artifacts/pass_i/runtime/vendor","outputs/current_development/video_event_experiment/.deps"):
    sys.path.insert(0,str(ROOT/relative))
from memory_graph.pass_t.phase2b.common import canonical_bytes,digest,file_sha256,pretty_bytes,read_json,exclusive_tree,Phase2BBlocked
from memory_graph.pass_t.phase2b.local_vlm.nf4 import verify_assets,BASELINE_ID
from memory_graph.pass_t.phase2b.local_vlm.diagnostics import diagnose
from memory_graph.pass_t.phase2b.local_vlm.transport import request_json
from memory_graph.pass_t.phase2b.backends import real_backend
from memory_graph.pass_t.phase2b.model_visible import inspect_payload
from memory_graph.pass_t.phase2b.predictions import parse_raw,validate_prediction
from memory_graph.pass_t.phase2b.config import unresolved_template
from memory_graph.pass_t.phase2b.builders import build_video

OUT=ROOT/"artifacts/pass_t/phase2b/local_runtime/qwen_nf4"
MODEL=ROOT/".models/Qwen2.5-VL-7B-Instruct"

def immutable(base,files,receipt):
    if os.name=='nt':base=Path('\\\\?\\'+str(base.resolve()))
    return exclusive_tree(base,files,receipt)

def fixtures(folder):
    folder.mkdir(parents=True,exist_ok=True); blobs=[]
    for index,color in enumerate(('red','blue','green')):
        image=Image.new('RGB',(224,224),'white');ImageDraw.Draw(image).rectangle((48+index*16,80,112+index*16,144),fill=color)
        stream=io.BytesIO();image.save(stream,format='PNG');blobs.append(stream.getvalue())
    board=Image.new('RGB',(672,248),'white')
    for index,blob in enumerate(blobs):
        board.paste(Image.open(io.BytesIO(blob)),(index*224,24));ImageDraw.Draw(board).text((index*224+8,4),f'F{index+1:04d}',fill='black')
    stream=io.BytesIO();board.save(stream,format='PNG');board_blob=stream.getvalue()
    prompt=(ROOT/'artifacts/pass_t/phase2b/templates/event_reasoning_prompt_v1.txt').read_text(encoding='utf8')
    def make(name,rep,assets,aliases,instructions):
        payload={'schema_version':'PASS_T_PHASE2B_MODEL_PAYLOAD_V1','request_id':'REQ_'+digest(name.encode())[:20],
            'target':{'opaque_id':'TARGET_A','description':'the colored geometric block in the supplied synthetic illustration'},
            'ontology':{'event_types':['PICKUP','PLACEMENT'],'window_outcomes':['CONFIRMED_EVENTS','NO_CONFIRMED_EVENT','INSUFFICIENT_EVIDENCE','TARGET_NOT_OBSERVABLE']},
            'representation':rep,'media':[], 'instructions':instructions,'output_contract':'PASS_T_PHASE2B_PREDICTION_V1'}
        media={}
        for i,(blob,ids) in enumerate(zip(assets,aliases)):
            mid=f'MEDIA_{i+1:03d}';media[mid]=blob
            payload['media'].append({'media_id':mid,'media_type':'video/x-msvideo' if rep=='REENCODED_AUTHORIZED_VIDEO' else 'image/png',
                'content_sha256':digest(blob),'supplied_frame_aliases':ids})
        if not inspect_payload(payload)['safe']:raise Phase2BBlocked('SYNTHETIC_PAYLOAD_LEAKAGE')
        return {'name':name,'payload':payload,'media_base64':{k:base64.b64encode(v).decode() for k,v in media.items()}}
    cases=[make('single_image','MULTI_IMAGE',[blobs[0]],[['F0001']], 'Describe visible geometric shapes and colors in your rationale. Do not infer physical events from one illustration; use the required JSON contract.'),
           make('multi_image','MULTI_IMAGE',blobs,[[f'F{i+1:04d}'] for i in range(3)], 'Describe the ordered visible geometric/color differences in your rationale. Do not treat illustration differences as established physical events. Use the required JSON contract.'),
           make('storyboard','STORYBOARD',[board_blob],[['F0001','F0002','F0003']], 'Describe the chronological panels and visible colors. Do not infer actor actions. Use the required JSON contract.')]
    frames=[]
    for index in range(8):
        path=folder/f'FRAME_{index:02d}.png';image=Image.new('RGB',(224,224),'white');ImageDraw.Draw(image).rectangle((40+index*8,80,96+index*8,136),fill='red');image.save(path)
        frames.append({'opaque_alias':f'F{index+1:04d}','private_path':str(path),'content_sha256':file_sha256(path),
                       'private_source_frame_index':index,'private_source_timestamp_s':index/4})
    video=build_video({'frames':frames,'width':224,'height':224},folder/'video',4)
    cases.append(make('synthetic_video','REENCODED_AUTHORIZED_VIDEO',[(folder/'video/AUTHORIZED_CLIP.avi').read_bytes()],
                      [[f'F{i+1:04d}' for i in range(8)]], 'Describe the visible geometric motion. Do not invent an actor or physical pickup/placement. Use the required JSON contract.'))
    cases.append(make('structured_contract','MULTI_IMAGE',[blobs[0]],[['F0001']],prompt))
    return cases,video

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    assets=verify_assets(MODEL)
    historical={p.relative_to(ROOT).as_posix():file_sha256(p) for p in (ROOT/'outputs/current_development/video_event_experiment').rglob('*')
                if p.is_file() and '/.deps/' not in p.as_posix() and '/.runtime/' not in p.as_posix() and '__pycache__' not in p.as_posix()}
    for p in (ROOT/'src/memory_graph/reasoning/model.py',ROOT/'src/memory_graph/vlm/local_backend.py',ROOT/'src/memory_graph/reasoning/video_experiment.py'):
        historical[p.relative_to(ROOT).as_posix()]=file_sha256(p)
    audit=immutable(OUT/'asset_audits',{'assets.json':pretty_bytes(assets),'historical_hashes.json':pretty_bytes(historical),
        'hardware.json':pretty_bytes(diagnose(cuda_probe=True))},{'schema_version':'PASS_T_NF4_ASSET_AUDIT_V1','weights_copied':False})
    fixture_folder=OUT/'synthetic_fixture_v1'
    cases,video=fixtures(fixture_folder)
    config=unresolved_template();config.update(provider='LOCAL_ONLY',backend='LOCAL_QWEN25_VL_NF4',model='Qwen/Qwen2.5-VL-7B-Instruct',
        revision='cc594898137f460bfe9f0759e9844b3ce807cfb5',execution_location='LOCAL',modalities=['image','video'])
    config['generation']={'temperature':0.0,'sampling':False,'seed':42,'max_output_tokens':768}
    config['transport']={'timeout_seconds':100,'max_retries':0,'monetary_budget_usd':0}
    config['limits']={'max_images':3,'max_pixels_per_image':200704,'context_tokens':8192}
    deployment={'schema_version':'PASS_T_NF4_SYNTHETIC_DEPLOYMENT_V1','endpoint':'http://127.0.0.1:8770','quantization':'NF4_DOUBLE_BF16',
        'approved':True,'synthetic_only':True,'approved_representations':['MULTI_IMAGE','STORYBOARD','REENCODED_AUTHORIZED_VIDEO'],
        'max_images':3,'max_frames':8,'max_input_pixels':672*248,'processor_max_pixels':200704,
        'generation_timeout_seconds':80,'attention':'sdpa','snapshot_path':str(MODEL),
        'asset_audit_path':str(audit/'assets.json'),'scratch_path':str(OUT/'scratch'),
        'synthetic_payload_sha256_allowlist':[digest(canonical_bytes(case['payload'])) for case in cases]}
    prepared=immutable(OUT/'prepared',{'config.json':pretty_bytes(config),'deployment.json':pretty_bytes(deployment),
        'cases.json':pretty_bytes({'cases':cases}), 'video_mapping.json':pretty_bytes(video)},
        {'schema_version':'PASS_T_NF4_SMOKE_PREPARATION_V1','baseline_id':BASELINE_ID,'asset_audit':str(audit),'pilot_authorized':False})
    print(json.dumps({'prepared':str(prepared),'audit':str(audit)},ensure_ascii=False),flush=True)

def run(folder):
    config=read_json(folder/'config.json');deployment=read_json(folder/'deployment.json');cases=read_json(folder/'cases.json')['cases']
    run_folder=OUT/f'run_{int(time.time())}';run_folder.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ);env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PASS_T_LOCAL_RUNTIME_APPROVAL='true',
        PASS_T_LOCAL_SMOKE_APPROVAL='true',PASS_T_LOCAL_SYNTHETIC_APPROVAL='true',PASS_T_LOCAL_DEPLOYMENT_CONFIG=str(folder/'deployment.json'),
        PYTHONPATH=';'.join(str(ROOT/r) for r in ('src','artifacts/pass_i/runtime/vendor','outputs/current_development/video_event_experiment/.deps')))
    for key in ('HF_HOME','TORCH_HOME','TMP','TEMP','TMPDIR','TRITON_CACHE_DIR'):
        path=run_folder/'runtime_cache';path.mkdir(exist_ok=True);env[key]=str(path)
    env.pop('PASS_T_PHASE2B_REAL_RUN_PERMISSION',None)
    os.environ['PASS_T_LOCAL_SYNTHETIC_APPROVAL']='true';os.environ['PASS_T_LOCAL_DEPLOYMENT_CONFIG']=str(folder/'deployment.json')
    log=open(run_folder/'runtime.log','wb');process=None;records=[];health=None;failure=None;unload=False
    try:
        process=subprocess.Popen([sys.executable,str(ROOT/'scripts/serve_pass_t_local_vlm.py'),'--config',str(folder/'config.json'),
            '--deployment',str(folder/'deployment.json'),'--metadata-manifest',deployment['asset_audit_path'],'--approve-runtime-load'],
            cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        deadline=time.monotonic()+240
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('MODEL_LOAD_PROCESS_EXIT:'+str(process.returncode))
            try:
                health=request_json(deployment['endpoint']+'/health',None,2)
                if health.get('model_loaded'):break
            except Exception:pass
            time.sleep(2)
        if not health:raise TimeoutError('MODEL_LOAD_240S_TIMEOUT')
        (run_folder/'health.json').write_bytes(pretty_bytes(health));print('MODEL_LOADED',health.get('model_load_seconds'),flush=True)
        adapter=real_backend(config)
        for case in cases:
            payload=case['payload'];media={k:base64.b64decode(v) for k,v in case['media_base64'].items()}
            started=time.perf_counter();response=None;raw=b'';validation=None;error=None
            try:
                if case['name'].startswith('structured_contract'):
                    raw=adapter.invoke(payload,media,config['transport']['timeout_seconds']);response=adapter.last_receipt
                else:
                    response=request_json(deployment['endpoint']+'/smoke',adapter.construct_request(payload,media),config['transport']['timeout_seconds'])
                    raw=response.get('raw_output','').encode('utf8')
                    if response.get('error'):raise RuntimeError(response['error'])
                aliases=list(dict.fromkeys(a for row in payload['media'] for a in row['supplied_frame_aliases']))
                validation=validate_prediction(parse_raw(raw),aliases)
            except Exception as exc:error=type(exc).__name__+':'+str(exc)
            record={'name':case['name'],'actual_model':True,'raw_output':raw.decode('utf8',errors='replace'),
                    'transport_generation_passed':bool(raw) and not (response or {}).get('error'),
                    'validation':validation,'resource_receipt':response,'error':error,'wall_seconds':time.perf_counter()-started,
                    'request_sha256':digest(canonical_bytes(payload)),'research_scoring_performed':False}
            records.append(record)
            (run_folder/(case['name']+'.json')).write_bytes(pretty_bytes(record))
            print('SMOKE',case['name'],record['transport_generation_passed'],validation and validation.get('valid'),error,flush=True)
            if error and ('out of memory' in error.lower() or 'OOM' in error):break
    except Exception as exc:
        failure={'error':str(exc),'traceback':traceback.format_exc()};print('FAILURE',failure['error'],flush=True)
    finally:
        if process is not None and process.poll() is None:
            try:request_json(deployment['endpoint']+'/shutdown',{},3)
            except Exception:pass
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
        unload=process is not None and process.poll() is not None
        log.close()
    summary={'schema_version':'PASS_T_NF4_REAL_SMOKE_V1','baseline_id':BASELINE_ID,'health':health,'records':records,
             'failure':failure,'owned_runtime_exited':unload,'prepared_path':str(folder),'pilot_run':False,'gt_used':False,
             'post_unload_gpu':subprocess.check_output(['nvidia-smi','--query-gpu=memory.free,memory.used','--format=csv,noheader']).decode().strip()}
    files={'summary.json':pretty_bytes(summary),'runtime.log':(run_folder/'runtime.log').read_bytes()}
    for case in cases:files['inputs/'+case['name']+'.json']=pretty_bytes(case)
    result=immutable(OUT/'smoke_results',files,{'schema_version':'PASS_T_NF4_REAL_SMOKE_RECEIPT_V1','real_model':True,'source':str(run_folder)})
    print(json.dumps({'result':str(result),'owned_runtime_exited':unload},ensure_ascii=False),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','run','prepare-repair']);p.add_argument('--prepared');a=p.parse_args()
    if a.command=='prepare':prepare()
    elif not a.prepared:raise ValueError('--prepared required')
    elif a.command=='prepare-repair':
        previous=Path(a.prepared);config=read_json(previous/'config.json');deployment=read_json(previous/'deployment.json')
        case=next(case for case in read_json(previous/'cases.json')['cases'] if case['name']=='structured_contract')
        case['name']='structured_contract_v2'
        config['generation']['max_output_tokens']=512;config['transport']['timeout_seconds']=200
        deployment['generation_timeout_seconds']=180
        deployment['response_format_system']='Respond with exactly one compact JSON object conforming to the user supplied schema. Begin with { and end with }. Do not use Markdown fences or prose outside JSON. Keep rationale and uncertainty strings short; do not copy the schema into the response.'
        deployment['synthetic_payload_sha256_allowlist']=[digest(canonical_bytes(case['payload']))]
        result=immutable(OUT/'prepared',{'config.json':pretty_bytes(config),'deployment.json':pretty_bytes(deployment),'cases.json':pretty_bytes({'cases':[case]})},
            {'schema_version':'PASS_T_NF4_SMOKE_ENGINEERING_REPAIR_V2','parent_preparation':str(previous),'event_prompt_changed':False,
             'changes':['formatting system message','bounded deadline 80->180s','output cap 768->512 tokens'],'max_model_calls':1})
        print(json.dumps({'prepared_repair':str(result)},ensure_ascii=False))
    else:run(Path(a.prepared))
if __name__=='__main__':main()
