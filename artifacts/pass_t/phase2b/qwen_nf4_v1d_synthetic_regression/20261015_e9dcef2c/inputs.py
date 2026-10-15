"""Materialize only locked new fixtures into existing NF4 input envelopes."""
import support as s
import base64,hashlib

def prompt_path():return s.OUT/'QWEN_NF4_EVENT_REASONING_PROMPT_V1D.txt'
def deployment(mode='NATIVE_VIDEO_ARRAY_DISABLED'):
    return {'approved':True,'synthetic_only':True,'processor_max_pixels':200704,'generation_timeout_seconds':300,
      'response_format_system':(s.REF/'prompt_candidate/v2_system_unchanged.txt').read_text(encoding='utf8'),
      'asset_audit_path':str(s.OUT/'model_assets.json'),'scratch_path':str(s.OUT/'scratch'),
      'identity_clause_enabled':False,'video_input_mode':mode,'experimental_task_prompt_candidate':'V1D',
      'experimental_task_prompt_sha256':s.sha(prompt_path())}

def fixture(scenario_id):
    manifest=s.read(s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json')
    return next(x for x in manifest['scenarios'] if x['scenario_id']==scenario_id)

def envelope(scenario_id):
    import numpy as np
    from PIL import Image
    f=fixture(scenario_id);rep=f['representation'];aliases=[x['alias'] for x in f['frames']]
    payload={'schema_version':'PASS_T_PHASE2B_MODEL_PAYLOAD_V1','request_id':'REQ_'+hashlib.sha256(('V1D|'+scenario_id).encode()).hexdigest()[:20],
      'target':{'opaque_id':'TARGET_A','description':'the designated object in supplied bounded media'},
      'ontology':{'event_types':['PICKUP','PLACEMENT'],'window_outcomes':['CONFIRMED_EVENTS','NO_CONFIRMED_EVENT','INSUFFICIENT_EVIDENCE','TARGET_NOT_OBSERVABLE']},
      'representation':rep,'media':[],'instructions':prompt_path().read_text(encoding='utf8'),'output_contract':'PASS_T_PHASE2B_PREDICTION_V1'}
    result={'payload':payload,'media':[],'generation':{'max_output_tokens':1024,'sampling':False,'seed':42}}
    if rep=='NATIVE_VIDEO_ARRAY':
        arrays=[]
        for row in f['frames']:
            assert s.sha(s.OUT/row['filename'])==row['sha256']
            with Image.open(s.OUT/row['filename']) as im:arrays.append(np.asarray(im.convert('RGB')).copy())
        result['native_video_array']={'frames':np.stack(arrays),'aliases':aliases,'native_pts_s':[x['synthetic_timestamp_s'] for x in f['frames']],
          'source_rgb_sha256':[x['rgb_sha256'] for x in f['frames']]}
    else:
        rows=f['frames'] if rep=='MULTI_IMAGE' else [f['storyboard']]
        for index,row in enumerate(rows):
            path=s.OUT/row['filename'];assert s.sha(path)==row['sha256']
            mid=f'MEDIA_{index+1:03d}'
            payload['media'].append({'media_id':mid,'media_type':'image/png','content_sha256':row['sha256'],
              'supplied_frame_aliases':[aliases[index]] if rep=='MULTI_IMAGE' else aliases})
            result['media'].append({'media_id':mid,'base64':base64.b64encode(path.read_bytes()).decode()})
    return result

def assert_no_metadata_leak(payload,rendered):
    import re
    text=s.canonical(payload).decode()+rendered
    forbidden=['intended_event_count_private','rendered_object_state_sequence_private','synthetic_timestamp_s','source_frame_position',
      'reviewer_id','physical_gt','IdentityGuard','lightglue','dino_score','annotation_item_id','S_']
    if any(token in text for token in forbidden):
        # S_ is too broad for words in the schema; exact scenario IDs are tested below.
        actual=[t for t in forbidden[:-1] if t in text]
        if actual:raise RuntimeError('MODEL_VISIBLE_METADATA_LEAK:'+str(actual))
    for f in s.read(s.OUT/'V1D_SYNTHETIC_FIXTURE_MANIFEST.json')['scenarios']:
        if f['scenario_id'] in text:raise RuntimeError('MODEL_VISIBLE_SCENARIO_ID_LEAK')
    if re.search(r'(?i)test[0-9]+(?:__W[0-9]+)?',text):raise RuntimeError('REAL_SOURCE_IDENTIFIER_LEAK')
