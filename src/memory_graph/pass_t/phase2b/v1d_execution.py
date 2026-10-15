"""Explicit in-process V1D transport, guarded media boundary and supervised run.

Importing this module or dry-running does not import a pixel/model/GPU library.
Legacy HTTP/AVI executors are deliberately never selected as a fallback.
"""
from __future__ import annotations
import base64
import json
import os
import time
import traceback
from pathlib import Path
from .common import canonical_bytes, digest, file_sha256, pretty_bytes, read_json, safe_join, environment_bool, repository_root
from .v1d_protocol import (authorize_execution, call_context, require, require_production_human_records, REAL_MODE, V1D_SHA, VERSION, MODEL, REVISION)
from .v1d_outputs import classify_output, preserve_raw, gated_evaluation

def _save(path,value):
    path=Path(path);tmp=path.with_suffix(path.suffix+'.pending')
    tmp.write_bytes(pretty_bytes(value));os.replace(tmp,path)

def runtime_deployment(bundle,authorization,call_id,root=None):
    root=Path(root) if root is not None else repository_root()
    draft=authorize_execution(bundle,authorization,call_id,root)
    call,_=call_context(draft,call_id)
    return {'approved':True,'synthetic_only':False,'real_pilot_mode':REAL_MODE,
        'real_pilot_context':{'frozen_bundle':bundle,'execution_authorization':authorization,'call_id':call_id},
        'processor_max_pixels':200704,'generation_timeout_seconds':300,
        'response_format_system':safe_join(root,draft['system_path']).read_text(encoding='utf8'),
        'asset_audit_path':str(safe_join(root,draft['model_assets_manifest'])),
        'identity_clause_enabled':False,'video_input_mode':'NATIVE_ARRAY_EXPERIMENTAL' if call['representation']=='NATIVE_VIDEO_ARRAY' else 'NATIVE_VIDEO_ARRAY_DISABLED',
        'experimental_task_prompt_candidate':'V1D','experimental_task_prompt_sha256':V1D_SHA}

def inspect_envelope(envelope,call,window,draft,root=None):
    """Retain the existing schema/key/serialized-leak guards for every format.

    The new in-process array has no encoded-media rows. Its *validation-only*
    projection uses the approved source descriptors to apply the unchanged
    legacy payload schema/leak guard. The projection is never sent to Qwen.
    Array dtype/order/pixels remain separately checked by the unchanged bridge.
    """
    import copy
    from .model_visible import inspect_payload
    root=Path(root) if root is not None else repository_root()
    payload=envelope['payload'];rep=call['representation']
    require(payload.get('representation')==rep,'PAYLOAD_REPRESENTATION_CHANGED')
    require(payload.get('instructions')==safe_join(root,draft['prompt_path']).read_text(encoding='utf8'),'PAYLOAD_TASK_CHANGED')
    require(envelope.get('generation')=={'max_output_tokens':1024,'sampling':False,'seed':42},'PAYLOAD_GENERATION_CHANGED')
    require(payload.get('target')=={'opaque_id':'TARGET_A','description':'the designated object in supplied bounded media'},'PAYLOAD_TARGET_CHANGED')
    aliases=[f['supplied_alias'] for f in window['selected']]
    expected=[{'media_id':f'MEDIA_{i:03d}','media_type':'image/png','content_sha256':f['recorded_source_png_sha256'],'supplied_frame_aliases':[f['supplied_alias']]} for i,f in enumerate(window['selected'])]
    projection=copy.deepcopy(payload)
    if rep=='NATIVE_VIDEO_ARRAY':
        require(payload['media']==[] and envelope['media']==[], 'NATIVE_ARRAY_MUST_NOT_USE_ENCODED_TRANSPORT')
        projection['representation']='MULTI_IMAGE';projection['media']=expected
    else:
        if rep=='STORYBOARD':expected=[{'media_id':'MEDIA_000','media_type':'image/png','content_sha256':window['storyboard_media']['sha256'],'supplied_frame_aliases':aliases}]
        require(payload['media']==expected,'PAYLOAD_MEDIA_IDENTITY_CHANGED')
        rows=envelope['media'];require(len(rows)==len(expected),'ENCODED_MEDIA_COUNT_CHANGED')
        for blob,descriptor in zip(rows,expected):
            require(set(blob)=={'media_id','base64'} and blob['media_id']==descriptor['media_id'],'ENCODED_MEDIA_ID_CHANGED')
            require(digest(base64.b64decode(blob['base64'],validate=True))==descriptor['content_sha256'],'ENCODED_MEDIA_BYTES_CHANGED')
    inspection=inspect_payload(projection)
    require(inspection['safe'],'MODEL_VISIBLE_SECURITY_GUARD:'+json.dumps(inspection['errors']))
    return {'safe':True,'validation_projection_only':rep=='NATIVE_VIDEO_ARRAY','actual_payload_sha256':digest(canonical_bytes(payload))}

def load_envelope(bundle,authorization,call_id,root=None):
    """Only authorized future execution opens the approved image bytes here."""
    root=Path(root) if root is not None else repository_root()
    draft=authorize_execution(bundle,authorization,call_id,root)
    call,w=call_context(draft,call_id)
    blobs=[];identities=[]
    for frame in w['selected']:
        raw=safe_join(root,frame['source_path']).read_bytes()
        require(digest(raw)==frame['recorded_source_png_sha256'], 'APPROVED_SOURCE_MEDIA_HASH_CHANGED')
        i=frame['source_frame_index'];pts=frame['native_source_pts_s'];bounds=w['window_boundaries']
        require(bounds['half_open_frames'][0]<=i<bounds['half_open_frames'][1] and bounds['half_open_pts'][0]<=pts<bounds['half_open_pts'][1], 'SOURCE_FRAME_OUTSIDE_APPROVED_WINDOW')
        blobs.append(raw);identities.append({**frame,'verified_source_file_sha256':digest(raw)})
    aliases=[f['supplied_alias'] for f in w['selected']]
    payload={'schema_version':'PASS_T_PHASE2B_MODEL_PAYLOAD_V1','request_id':'REQ_'+digest(canonical_bytes({'protocol':bundle['freeze_receipt']['protocol_sha256'],'call':call_id}))[:20],
       'target':{'opaque_id':'TARGET_A','description':'the designated object in supplied bounded media'},
       'ontology':{'event_types':['PICKUP','PLACEMENT'],'window_outcomes':['CONFIRMED_EVENTS','NO_CONFIRMED_EVENT','INSUFFICIENT_EVIDENCE','TARGET_NOT_OBSERVABLE']},
       'representation':call['representation'],'instructions':safe_join(root,draft['prompt_path']).read_text(encoding='utf8'),'media':[],
       'output_contract':'PASS_T_PHASE2B_PREDICTION_V1'}
    envelope={'payload':payload,'media':[],'generation':{'max_output_tokens':1024,'sampling':False,'seed':42}}
    if call['representation']=='NATIVE_VIDEO_ARRAY':
        # All approval/hash checks above precede any pixel/model imports.
        import io
        import numpy as np
        from PIL import Image
        arrays=[]
        for raw in blobs:
            with Image.open(io.BytesIO(raw)) as image:arrays.append(np.asarray(image.convert('RGB')).copy())
        envelope['native_video_array']={'frames':np.stack(arrays),'aliases':aliases,
           'native_pts_s':[s['native_source_pts_s'] for s in w['selected']],
           'source_rgb_sha256':[digest(a.tobytes()) for a in arrays]}
    else:
        rows=list(zip(blobs,[[a] for a in aliases]))
        if call['representation']=='STORYBOARD':
            raw=safe_join(root,w['storyboard_media']['path']).read_bytes()
            require(digest(raw)==w['storyboard_media']['sha256'], 'APPROVED_STORYBOARD_HASH_CHANGED')
            rows=[(raw,aliases)]
        for i,(raw,used_aliases) in enumerate(rows):
            media_id=f'MEDIA_{i:03d}'
            payload['media'].append({'media_id':media_id,'media_type':'image/png','content_sha256':digest(raw),'supplied_frame_aliases':used_aliases})
            envelope['media'].append({'media_id':media_id,'base64':base64.b64encode(raw).decode('ascii')})
    inspect_envelope(envelope,call,w,draft,root)
    return envelope,{'media_integrity':'VERIFIED_APPROVED_INPUT_BYTES','source_video_bytes_reverified':False,
        'native_PTS_provenance':'APPROVED_HASH_PINNED_SOURCE_METADATA','source_metadata_sha256':w['source_metadata_sha256'],
        'authorized_frame_list_sha256':w['authorized_frame_list_sha256'],'window_boundaries':w['window_boundaries'],
        'frame_alias_mapping':identities,'reference':'NONE','sampling':'GT_INDEPENDENT_UNIFORM_8',
        'temporal_limitation':'FRAME_MATCHED_ONLY_8_SOURCE_FRAMES_4_UNITS' if call['representation']=='NATIVE_VIDEO_ARRAY' else 'EIGHT_SOURCE_FRAMES_NOT_EQUAL_VISUAL_TOKEN_BUDGET'}

def validate_runtime_receipt(receipt,envelope,call,window,draft):
    require(receipt.get('model')==MODEL and receipt.get('revision')==REVISION, 'RUNTIME_MODEL_CHANGED')
    require(receipt.get('generation_controls')=={'do_sample':False,'max_new_tokens':1024,'max_time':300} and receipt.get('seed_applied')==42, 'GENERATION_POLICY_CHANGED')
    text=receipt.get('rendered_prompt')
    require(isinstance(text,str) and digest(text.encode())==receipt.get('rendered_prompt_sha256'), 'RENDERED_TEXT_RECEIPT_REQUIRED')
    require(envelope['payload']['instructions'] in text, 'V1D_NOT_IN_CAPTURED_RENDERED_TEXT')
    require(digest(receipt.get('captured_system_text','').encode())==draft['settings']['system_sha256'], 'V2_SYSTEM_CAPTURE_REQUIRED')
    require(receipt['captured_system_text'] in text, 'V2_NOT_IN_CAPTURED_RENDERED_TEXT')
    require(receipt.get('processed_frame_aliases')==[s['supplied_alias'] for s in window['selected']], 'PROCESSOR_ALIAS_MAPPING_CHANGED')
    require(receipt.get('processor_frame_count')==8 and receipt.get('reference_image_count')==0, 'PROCESSOR_FRAME_REFERENCE_CHANGED')
    require(receipt.get('configured_pixel_cap')==200704, 'PROCESSOR_CAP_CHANGED')
    if call['representation']=='NATIVE_VIDEO_ARRAY':
        require(receipt.get('native_video_modality') is True and receipt.get('temporal_patch_count')==4 and receipt.get('representation_status')=='FRAME_MATCHED_ONLY', 'NATIVE_VIDEO_UNITS_CHANGED')

def record_call_result(destination,raw,receipt,envelope,provenance,bundle,authorization,call_id,*,execution_kind='REAL_AUTHORIZED',root=None):
    """Common durable recording path; mock tests explicitly label their receipts."""
    root=Path(root) if root is not None else repository_root()
    draft=authorize_execution(bundle,authorization,call_id,root)
    call,w=call_context(draft,call_id);destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    preserve_raw(destination/'raw_output.txt',raw)
    # Save every original runtime receipt before validating it; never discard raw.
    _save(destination/'runtime_receipt.json',receipt)
    aliases=[s['supplied_alias'] for s in w['selected']]
    classified=classify_output(raw,aliases)
    receipt_error=None
    try:validate_runtime_receipt(receipt,envelope,call,w,draft)
    except Exception as error:
        receipt_error=str(error);classified['authoritative_prediction']=None
        classified['matching_status']='UNAVAILABLE_INVALID_RUNTIME_RECEIPT'
    record={'schema_version':VERSION+'_CALL_RECEIPT','execution_kind':execution_kind,
        'protocol_sha256':bundle['freeze_receipt']['protocol_sha256'],'execution_authorization_sha256':digest(canonical_bytes(authorization)),
        'call':call,'components_sha256':draft['components_sha256'],'provenance':provenance,
        'payload_sha256':digest(canonical_bytes(envelope['payload'])),'generation_sha256':digest(canonical_bytes(envelope['generation'])),
        'runtime_receipt_sha256':file_sha256(destination/'runtime_receipt.json'),'raw_sha256':digest(raw),
        'classification':classified,'runtime_receipt_error':receipt_error,
        'qualitative_review':{'status':'UNREVIEWED','scope':'DESCRIPTIVE_ONLY','authoritative_prediction':False},
        'structured_matching':'PENDING_APPROVED_GT_EVALUATION' if classified['authoritative_prediction'] is not None else classified.get('matching_status','UNAVAILABLE_INVALID'),
        'memory_graph_written':False}
    _save(destination/'call_receipt.json',record)
    if receipt_error:raise ValueError('RUNTIME_RECEIPT_INVALID_RAW_PRESERVED:'+receipt_error)
    return record

def evaluate_recorded_call(destination,bundle,authorization,record,eligibility,root=None):
    """CPU-only post-call matching, with GT supplied only to this private API.

    Never reads GT itself or exposes it to model input; software mocks are not GT.
    """
    root=Path(root) if root is not None else repository_root();destination=Path(destination)
    saved=read_json(destination/'call_receipt.json');cid=saved['call']['proposed_call_index']
    draft=authorize_execution(bundle,authorization,cid,root);_,w=call_context(draft,cid)
    require(saved['protocol_sha256']==bundle['freeze_receipt']['protocol_sha256'] and saved['execution_authorization_sha256']==digest(canonical_bytes(authorization)), 'RECORDED_CALL_PROTOCOL_CHANGED')
    require(file_sha256(destination/'raw_output.txt')==saved['raw_sha256'] and file_sha256(destination/'runtime_receipt.json')==saved['runtime_receipt_sha256'], 'RECORDED_CALL_BYTES_CHANGED')
    require(record['annotation_item_id']==w['item_id'] and eligibility['annotation_item_id']==w['item_id'] and eligibility['pilot_scoring_permission']==w['permission'], 'EVALUATION_SCOPE_CHANGED')
    if saved['runtime_receipt_error'] or saved['classification']['authoritative_prediction'] is None:
        return {'matching_status':'UNAVAILABLE_STRICT_INVALID_OR_BAD_RECEIPT','sensitivity_results':None,'no_event_inferred':False}
    mapping=[{'opaque_alias':x['supplied_alias'],'source_timestamp_s':x['native_source_pts_s']} for x in w['selected']]
    return gated_evaluation((destination/'raw_output.txt').read_bytes(),[x['opaque_alias'] for x in mapping],record,eligibility,
                            {'private_mapping':mapping},matcher_policy=draft['matcher_policy'])

def safety_reason(sample,stage):
    if stage=='BEFORE_LOAD' and (sample['gpu_free_gib']<10 or sample['ram_available_gib']<8):return 'LOAD_RESOURCE_GATE'
    if stage=='BEFORE_GENERATION' and sample['gpu_free_gib']<2:return 'GENERATION_RESOURCE_GATE'
    if sample['gpu_used_gib']>14.5 or sample['owned_rss_gib']>20 or sample['ram_available_gib']<2:return 'RESOURCE_STOP'
    return None

def call_completion_summary(destination,run_order):
    """Absent, incomplete and never-started calls stay separate from valid NO_EVENT."""
    destination=Path(destination);rows=[]
    for call in run_order:
        cid=call['proposed_call_index'];folder=destination/f'call_{cid:02d}'
        if (folder/'call_receipt.json').exists():
            receipt=read_json(folder/'call_receipt.json')
            status='INVALID_RUNTIME_RECEIPT' if receipt['runtime_receipt_error'] else receipt['classification']['classification']
        elif (folder/'raw_output.txt').exists():status='INCOMPLETE_RECEIPT_RAW_PRESERVED'
        elif (destination/f'call_{cid:02d}.started').exists():status='ABSENT_PREDICTION_AFTER_START'
        else:status='NOT_EXECUTED_AFTER_STOP'
        rows.append({'call_id':cid,'status':status})
    return rows

def staged_run_summary(destination,run_order):
    from collections import Counter
    destination=Path(destination)
    states=call_completion_summary(destination,run_order)
    stages={k:Counter() for k in ('JSON_SYNTAX','SCHEMA','SEMANTIC','CITATION','FULL_STRICT')}
    for row in states:
        file=destination/f"call_{row['call_id']:02d}/call_receipt.json"
        if file.exists():
            classified=read_json(file)['classification']
            for key,counter in stages.items():counter[classified['stages'][key]]+=1
    return {'planned_calls':len(run_order),'call_classifications':dict(Counter(s['status'] for s in states)),
            'stage_counts_over_recorded_outputs':{k:dict(v) for k,v in stages.items()},
            'no_event_inferred_from_invalid':False,'formal_metrics':'UNDEFINED'}

def claim_authorization_use(destination,authorization):
    """Exclusive lease: replay cannot restart the same 18-call permission."""
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
    _save(destination/'authorization_use.json',authorization)

def _resources(pid=None):
    import subprocess,psutil
    text=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader,nounits'],text=True,timeout=5)
    require(len(text.strip().splitlines())==1,'EXACTLY_ONE_GPU_REQUIRED')
    used,free=[float(v.strip())/1024 for v in text.strip().split(',')]
    rss=0
    if pid:
        try:
            parent=psutil.Process(pid)
            for process in [parent]+parent.children(recursive=True):
                try:rss+=process.memory_info().rss
                except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        except psutil.NoSuchProcess:pass
    return {'gpu_used_gib':used,'gpu_free_gib':free,'ram_available_gib':psutil.virtual_memory().available/2**30,'owned_rss_gib':rss/2**30}

def _runtime_factory(deployment,draft,root):
    # The shared NF4 loader/generate source is not edited. This observer only
    # captures original CPU processor tensors before its unchanged CUDA transfer.
    context=deployment['real_pilot_context']
    require_production_human_records(context['frozen_bundle'],context['execution_authorization'])
    from .local_vlm.nf4 import QwenNF4Runtime
    from .local_vlm.catalog import SPECS
    from .local_vlm.video_array_bridge import tensor_record
    class ObservedNF4(QwenNF4Runtime):
        def preprocess(self,envelope):
            inputs,receipt=super().preprocess(envelope)
            records={k:tensor_record(t) for k,t in inputs.items()}
            if 'tensor_records' in receipt:require(receipt['tensor_records']==records,'PROCESSOR_TENSOR_CAPTURE_CHANGED')
            receipt['tensor_records']=records
            receipt['captured_input_ids']=inputs['input_ids'].tolist()
            receipt['captured_system_text']=self.deployment['response_format_system']
            return inputs,receipt
    return ObservedNF4(SPECS['qwen_nf4'],deployment,safe_join(root,draft['model_snapshot']),None)

def _worker(bundle,authorization,destination,root,execution_kind='REAL_AUTHORIZED'):
    root=Path(root);destination=Path(destination);runtime=None
    try:
        draft=authorize_execution(bundle,authorization,root=root)
        require(environment_bool('PASS_T_LOCAL_RUNTIME_APPROVAL') and environment_bool('PASS_T_PHASE2B_REAL_RUN_PERMISSION'), 'EXTERNAL_RUNTIME_AND_REAL_RUN_PERMISSION_REQUIRED')
        reason=safety_reason(_resources(),'BEFORE_LOAD');require(reason is None,str(reason))
        first=draft['run_order'][0]['proposed_call_index']
        deployment=runtime_deployment(bundle,authorization,first,root);deployment['scratch_path']=str(destination/'scratch')
        _save(destination/'progress.json',{'stage':'MODEL_LOADING','started_unix':time.time()})
        runtime=_runtime_factory(deployment,draft,root)
        for call in draft['run_order']:
            cid=call['proposed_call_index'];authorize_execution(bundle,authorization,cid,root)
            _save(destination/'progress.json',{'stage':'CALL','call_id':cid,'started_unix':time.time()})
            reason=safety_reason(_resources(os.getpid()),'BEFORE_GENERATION');require(reason is None,str(reason))
            # Exclusive claim is persistent even if a worker crashes mid-generation.
            with (destination/f'call_{cid:02d}.started').open('xb') as f:f.write(canonical_bytes({'call_id':cid,'started_unix':time.time()}))
            envelope,provenance=load_envelope(bundle,authorization,cid,root)
            runtime.deployment=runtime_deployment(bundle,authorization,cid,root);runtime.deployment['scratch_path']=str(destination/'scratch')
            result=runtime.generate(envelope)  # Exactly one call, no retries/warmups.
            raw=result.pop('raw_output').encode('utf8')
            record_call_result(destination/f'call_{cid:02d}',raw,result,envelope,provenance,bundle,authorization,cid,root=root,execution_kind=execution_kind)
            require(not result.get('generation_deadline_reached',False),'GENERATION_DEADLINE_RAW_PRESERVED')
        _save(destination/'progress.json',{'stage':'COMPLETE','completed_calls':18,'started_unix':time.time()})
    except BaseException:
        _save(destination/'worker_failure.json',{'error':traceback.format_exc(),'retry':False})
        raise
    finally:
        if runtime is not None:del runtime

def execute_authorized(bundle,authorization,root=None):
    """The only production run entry. It is never invoked by CPU dry-run.

    Authorization-use directory prevents reuse/replay of the same permission;
    no arbitrary output directory or legacy transport fallback is accepted.
    """
    root=Path(root) if root is not None else repository_root()
    draft=authorize_execution(bundle,authorization,root=root)
    require_production_human_records(bundle,authorization)
    require(environment_bool('PASS_T_LOCAL_RUNTIME_APPROVAL') and environment_bool('PASS_T_PHASE2B_REAL_RUN_PERMISSION'), 'EXTERNAL_RUNTIME_AND_REAL_RUN_PERMISSION_REQUIRED')
    destination=root/'artifacts/pass_t/phase2b/v1d_pilot_runs'/digest(canonical_bytes(authorization))
    claim_authorization_use(destination,authorization)
    _save(destination/'frozen_bundle.json',bundle)
    import multiprocessing
    process=multiprocessing.get_context('spawn').Process(target=_worker,args=(bundle,authorization,str(destination),str(root)))
    samples=[];reason=None;began=time.time()
    process.start()
    try:
        while process.is_alive():
            sample=_resources(process.pid);samples.append({'elapsed_s':time.time()-began,**sample})
            reason=safety_reason(sample,'RUNNING')
            progress_path=destination/'progress.json'
            if progress_path.exists():
                progress=read_json(progress_path);elapsed=time.time()-progress['started_unix']
                if progress['stage']=='MODEL_LOADING' and elapsed>120:reason='LOAD_TIMEOUT'
                if progress['stage']=='CALL' and elapsed>330:reason='REQUEST_TIMEOUT'
            if time.time()-began>6060:reason='WHOLE_PILOT_TIMEOUT'
            if reason:break
            process.join(timeout=1)
    except BaseException:
        reason='SUPERVISOR_FAILURE';raise
    finally:
        if process.is_alive():process.terminate()
        process.join(timeout=10)
        if process.is_alive():process.kill();process.join(timeout=10)
        statuses=call_completion_summary(destination,draft['run_order'])
        missing=[r['call_id'] for r in statuses if r['status'] in {'NOT_EXECUTED_AFTER_STOP','ABSENT_PREDICTION_AFTER_START','INCOMPLETE_RECEIPT_RAW_PRESERVED'}]
        _save(destination/'run_receipt.json',{'protocol_sha256':bundle['freeze_receipt']['protocol_sha256'],
            'authorization_sha256':digest(canonical_bytes(authorization)),'planned_calls':18,'missing_call_ids':missing,
            'call_statuses':statuses,'stage_summary':staged_run_summary(destination,draft['run_order']),
            'stop_reason':reason,'worker_exit_code':process.exitcode,
            'resource_samples':samples,'generation_retries':0,'memory_graph_written':False,'formal_metrics':'UNDEFINED'})
    return destination
