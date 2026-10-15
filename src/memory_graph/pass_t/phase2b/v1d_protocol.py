"""Explicit V1D pilot contracts. Text/metadata only; no model/media imports.

Approval records are caller-supplied human provenance, not cryptographic proof of
human authorship. No function infers approval from a draft or environment flag.
"""
from __future__ import annotations
import copy
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from .common import Phase2BBlocked, canonical_bytes, digest, file_sha256, read_json, safe_join, exclusive_tree, pretty_bytes, repository_root

VERSION = 'PASS_T_QWEN_NF4_V1D_PILOT_V1'
REAL_MODE = 'FROZEN_V1D_PILOT_V1'
MATCHER = 'CLOSED_INTERVAL_GAP_V1'
REPRESENTATIONS = ('MULTI_IMAGE', 'STORYBOARD', 'NATIVE_VIDEO_ARRAY')
V1D_SHA = '7008254e618dc8bacdbdeaae3cbf471220afb5efd6c80afc8b9ea5fb5c96b9b0'
V2_SHA = '9b76b7e320dfb677a1cb8566c16dff15785759bc4915375123bc12dd118fd08e'
SCHEMA_SHA = 'f8b0dfb6c62301baabff5e1adfddf14dc6be9381aa84c884fc70f5318abcedc3'
VALIDATOR_SHA = 'c4b077374d50fc478c29d0009180d488c60a463fa8bffa183a179c5f736f1d37'
MODEL = 'Qwen/Qwen2.5-VL-7B-Instruct'
REVISION = 'cc594898137f460bfe9f0759e9844b3ce807cfb5'
REVIEW = 'WORKSPACE/Pass_T/Final_Pilot_Protocol_Review_20261015/FINAL_COMPONENT_HASH_MANIFEST.json'
REVIEW_SHA = '97be3f4a1e93583eaa295348ba9a01f3d1fb1d855bf3a28e5a26857e917d95a1'
ASSETS = 'artifacts/pass_t/phase2b/qwen_nf4_v1d_synthetic_regression/20261015_e9dcef2c/model_assets.json'
BASE = 'src/memory_graph/pass_t/phase2b/'
COMPONENTS = (BASE+'local_vlm/nf4.py', BASE+'local_vlm/video_array_bridge.py', BASE+'local_vlm/qwen_contract.py',
              BASE+'local_vlm/runtime.py', BASE+'local_vlm/catalog.py', BASE+'common.py', BASE+'model_visible.py',
              BASE+'predictions.py', BASE+'contracts/prediction_v1.json', BASE+'contracts/model_visible_payload_v1.json', BASE+'evaluation.py',
              BASE+'v1d_protocol.py', BASE+'v1d_execution.py', BASE+'v1d_outputs.py',
              'scripts/run_pass_t_v1d_pilot.py', ASSETS)

def require(condition, message):
    if not condition:
        raise Phase2BBlocked(message)

def _root(root):
    return Path(root) if root is not None else repository_root()

def _review(root):
    p = safe_join(root, REVIEW)
    require(file_sha256(p) == REVIEW_SHA, 'REVIEW_AUTHORITY_CHANGED')
    return read_json(p)

def _source(window, root):
    path = safe_join(root, window['source_metadata_path'])
    require(file_sha256(path) == window['source_metadata_sha256'], 'WINDOW_METADATA_CHANGED')
    return read_json(path)

def uniform8(frames):
    require(len(frames) >= 8, 'EIGHT_DISTINCT_SOURCE_FRAMES_REQUIRED')
    return [round(i * (len(frames)-1) / 7) for i in range(8)]

def draft_protocol(root=None):
    """Construct an UNAPPROVED metadata draft, never open image/model bytes."""
    root = _root(root); review = _review(root)
    sources = review['source_components']
    sample_path=safe_join(root,sources['E07']['path'])
    require(file_sha256(sample_path)==sources['E07']['sha256'],'SAMPLING_MANIFEST_AUTHORITY_CHANGED')
    sampling_manifests=json.loads(sample_path.read_text(encoding='utf8'))
    windows = []
    for row in review['cohort']:
        meta = sources['INPUT-'+row['opaque_id']]
        source = read_json(safe_join(root, meta['path']))
        frames = source['frames']; pos = uniform8(frames)
        selected = []
        for i, index in enumerate(pos):
            f = frames[index]; recorded = row['selected_mapping'][i]
            require(f['frame_id'] == recorded['source_frame_id'] and f['sha256'] == recorded['recorded_source_png_sha256']
                    and f['source_timestamp_s'] == recorded['native_source_pts_s'], 'REVIEW_SELECTION_MISMATCH')
            selected.append({**recorded, 'source_path': f['image_path']})
        sb=next(x for x in sampling_manifests if x['item_id']==row['item_id'] and x['name']=='UNIFORM_8_STORYBOARD')
        require(sb['sampling']['positions']==pos and sb['reference_count']==0, 'STORYBOARD_SELECTION_CHANGED')
        sb_path=str(Path(sources['E07']['path']).parent.parent/ sb['media_files'][0]).replace('\\','/')
        sb_hash=sb['media_hashes'][0] if isinstance(sb['media_hashes'],list) else sb['media_hashes'][sb['media_files'][0]]
        windows.append({'item_id':row['item_id'], 'opaque_id':row['opaque_id'], 'original_pack_ids':row['original_pack_ids'],
            'permission':row['permission'], 'source_metadata_path':meta['path'], 'source_metadata_sha256':meta['sha256'],
            'authorized_frame_list_sha256':digest(canonical_bytes(frames)),
            'window_boundaries':{k:source['authoritative_item_metadata'][k] for k in ('half_open_frames','half_open_pts','source_video_sha256','authorized_visual_manifest_sha256')},
            'positions':pos, 'selected':selected, 'storyboard_media':{'path':sb_path,'sha256':sb_hash},
            'media_integrity':'PENDING_AUTHORIZED_EXECUTION'})
    components = {p:file_sha256(safe_join(root,p)) for p in COMPONENTS}
    for key, expected in [('E16',V1D_SHA),('E18',V2_SHA),('E22',SCHEMA_SHA),('E23',VALIDATOR_SHA)]:
        p = sources[key]['path']; require(file_sha256(safe_join(root,p)) == expected, 'IMMUTABLE_COMPONENT_CHANGED:'+key)
        components[p] = expected
    return {'schema_version':VERSION, 'status':'DRAFT', 'review_authority':{'path':REVIEW,'sha256':REVIEW_SHA},
        'settings':copy.deepcopy(review['proposed_settings']), 'matcher_policy':MATCHER,
        'human_decisions':copy.deepcopy(review['human_decisions']), 'windows':windows,
        'run_order':copy.deepcopy(review['proposed_run_order']), 'components_sha256':components,
        'prompt_path':sources['E16']['path'], 'system_path':sources['E18']['path'],
        'model_assets_manifest':ASSETS, 'model_snapshot':'.models/Qwen2.5-VL-7B-Instruct',
        'execution_route':'EXPLICIT_IN_PROCESS_NF4_V1D', 'media_integrity':'PENDING_AUTHORIZED_EXECUTION',
        'engineering_resolution':{'T01':'SEPARATE_FROZEN_REAL_V1D_GATE','T02':'VERSIONED_IN_PROCESS_PROTOCOL_ROUTE','T04':MATCHER,
                                 'historical_decision_risk_text':'Preserved from review; not an updated approval or historical artifact rewrite'},
        'protocol_approval':None, 'execution_authorization':None}

def validate_draft(draft, root=None):
    root = _root(root); expected = draft_protocol(root)
    # Full equality prevents silent new fields, changes to any of the 21 decisions,
    # scientific settings, source boundaries, model, sampling or legacy fallbacks.
    require(draft == expected, 'V1D_DRAFT_OR_COMPONENT_MISMATCH')
    require(len(draft['windows']) == 6 and len(draft['run_order']) == 18, 'SIX_BY_THREE_REQUIRED')
    require({r['representation'] for r in draft['run_order']} == set(REPRESENTATIONS), 'REPRESENTATION_MISMATCH')
    require(len({(r['opaque_id'],r['representation']) for r in draft['run_order']}) == 18, 'DUPLICATE_CALL')
    for w in draft['windows']:
        source = _source(w, root); frames = source['frames']
        require(digest(canonical_bytes(frames)) == w['authorized_frame_list_sha256'], 'FRAME_LIST_CHANGED')
        require(w['positions'] == uniform8(frames), 'NON_UNIFORM_SELECTION')
        times = [f['native_source_pts_s'] for f in w['selected']]
        require(all(type(t) in (int,float) and math.isfinite(t) for t in times) and all(b>a for a,b in zip(times,times[1:])), 'NATIVE_PTS_INVALID')
        require(len({s['supplied_alias'] for s in w['selected']}) == 8, 'SOURCE_ALIAS_DUPLICATE')
        require(all(re.fullmatch(r'F\d{4}',s['supplied_alias']) for s in w['selected']), 'SOURCE_ALIAS_INVALID')
    return {'valid':True,'status':'DRAFT_NOT_APPROVED','draft_sha256':digest(canonical_bytes(draft)),
            'decisions_pending':21,'planned_calls':18,'media_integrity':'PENDING_AUTHORIZED_EXECUTION'}

def decision_digest(decision):
    return digest(canonical_bytes(decision))

def _approval(draft, approval):
    expected = 'APPROVE_PHASE2B_V1D_FREEZE '+digest(canonical_bytes(draft))+' NO_EXECUTION'
    require(isinstance(approval,dict) and approval.get('confirmation') == expected, 'EXPLICIT_HUMAN_FREEZE_APPROVAL_REQUIRED')
    require(isinstance(approval.get('reviewer_id'),str) and bool(approval['reviewer_id'].strip()), 'HUMAN_REVIEWER_REQUIRED')
    actual = approval.get('decisions')
    required = [{'id':d['id'],'decision_sha256':decision_digest(d),'status':'APPROVED'} for d in draft['human_decisions']]
    require(actual == required and len(actual) == 21, 'ALL_21_EXPLICIT_DECISIONS_REQUIRED')
    require(approval.get('execution_authorized') is False, 'FREEZE_IS_NOT_EXECUTION')

def frozen_bundle(draft, approval, root=None):
    """Pure serialization, used by freeze writer and *in-memory mock* tests.

    This does not create a frozen artifact or grant a human approval.
    """
    validate_draft(draft,root); _approval(draft,approval)
    protocol = {'schema_version':VERSION,'status':'FROZEN','draft':copy.deepcopy(draft),'human_approval':copy.deepcopy(approval)}
    return {'protocol':protocol,'freeze_receipt':{'protocol_sha256':digest(canonical_bytes(protocol)),
        'draft_sha256':digest(canonical_bytes(draft)), 'approval_sha256':digest(canonical_bytes(approval))}}

def freeze_protocol(draft, approval, root=None, output_base=None):
    """Future explicit freeze operation; never called in the readiness task."""
    require(not str(approval.get('reviewer_id','')).upper().startswith('MOCK'), 'MOCK_APPROVAL_CANNOT_CREATE_REAL_FREEZE')
    root=_root(root); bundle=frozen_bundle(draft,approval,root)
    return exclusive_tree(output_base or root/'artifacts/pass_t/phase2b/v1d_protocols',
        {'frozen_bundle.json':pretty_bytes(bundle)}, {'schema_version':VERSION,'kind':'HUMAN_APPROVED_FREEZE_ONLY',**bundle['freeze_receipt']})

def verify_frozen(bundle, root=None):
    require(isinstance(bundle,dict) and set(bundle)=={'protocol','freeze_receipt'}, 'VALID_FROZEN_V1D_MANIFEST_REQUIRED')
    p=bundle['protocol'];receipt=bundle['freeze_receipt']
    require(p.get('schema_version')==VERSION and p.get('status')=='FROZEN', 'FROZEN_V1D_PROTOCOL_REQUIRED')
    validate_draft(p['draft'],root); _approval(p['draft'],p['human_approval'])
    require(receipt=={'protocol_sha256':digest(canonical_bytes(p)),'draft_sha256':digest(canonical_bytes(p['draft'])),
        'approval_sha256':digest(canonical_bytes(p['human_approval']))}, 'FROZEN_MANIFEST_HASH_MISMATCH')
    return p['draft']

def authorize_execution(bundle, authorization, call_id=None, root=None, now=None):
    draft=verify_frozen(bundle,root)
    h=bundle['freeze_receipt']['protocol_sha256']
    require(isinstance(authorization,dict), 'SEPARATE_EXECUTION_AUTHORIZATION_REQUIRED')
    require(authorization.get('schema_version')==VERSION+'_EXECUTION_AUTHORIZATION', 'EXECUTION_AUTHORIZATION_VERSION')
    require(authorization.get('confirmation')=='EXECUTE_PHASE2B_V1D '+h+' 18_CALLS', 'SEPARATE_EXECUTION_AUTHORIZATION_REQUIRED')
    require(authorization.get('protocol_sha256')==h and authorization.get('max_calls')==18, 'AUTHORIZATION_BINDING_MISMATCH')
    require(isinstance(authorization.get('reviewer_id'),str) and bool(authorization['reviewer_id'].strip()), 'EXECUTION_REVIEWER_REQUIRED')
    require(isinstance(authorization.get('nonce'),str) and re.fullmatch(r'[0-9a-f]{32}',authorization['nonce']), 'EXECUTION_NONCE_REQUIRED')
    try:
        until=datetime.fromisoformat(authorization['expires_at_utc'])
        current=now or datetime.now(timezone.utc)
        require(until.tzinfo is not None and until>current, 'EXECUTION_AUTHORIZATION_EXPIRED')
    except (KeyError,TypeError,ValueError) as error:
        raise Phase2BBlocked('EXECUTION_AUTHORIZATION_EXPIRY_INVALID') from error
    ids=[r['proposed_call_index'] for r in draft['run_order']]
    require(authorization.get('call_ids')==ids, 'AUTHORIZED_CALL_INVENTORY_MISMATCH')
    if call_id is not None:require(call_id in ids, 'CALL_NOT_AUTHORIZED')
    return draft

def call_context(draft, call_id):
    rows=[r for r in draft['run_order'] if r['proposed_call_index']==call_id]
    require(len(rows)==1, 'UNKNOWN_CALL_ID')
    r=rows[0];w=next(x for x in draft['windows'] if x['opaque_id']==r['opaque_id'])
    return r,w

def require_production_human_records(bundle,authorization):
    require(not str(authorization.get('reviewer_id','')).upper().startswith('MOCK')
            and not str(bundle['protocol']['human_approval']['reviewer_id']).upper().startswith('MOCK'),
            'MOCK_RECORDS_CANNOT_AUTHORIZE_REAL_MODEL_OR_FREEZE')

def bridge_eligibility(envelope, deployment, root=None):
    """Separate real-pilot gate, evaluated before torch/processor imports."""
    require(deployment.get('real_pilot_mode')==REAL_MODE and deployment.get('synthetic_only') is False, 'REAL_PILOT_MODE_REQUIRED')
    context=deployment.get('real_pilot_context')
    require(isinstance(context,dict), 'FROZEN_PILOT_CONTEXT_REQUIRED')
    draft=authorize_execution(context.get('frozen_bundle'),context.get('execution_authorization'),context.get('call_id'),root)
    call,w=call_context(draft,context['call_id'])
    require(call['representation']=='NATIVE_VIDEO_ARRAY', 'NATIVE_REPRESENTATION_NOT_AUTHORIZED')
    require(deployment.get('experimental_task_prompt_sha256')==V1D_SHA and deployment.get('experimental_task_prompt_candidate')=='V1D', 'REAL_V1D_PIN_REQUIRED')
    require(deployment.get('identity_clause_enabled') is False, 'IDENTITY_CLAUSE_NOT_APPROVED')
    require(deployment.get('processor_max_pixels')==200704 and deployment.get('generation_timeout_seconds')==300, 'REAL_DEPLOYMENT_BUDGET_CHANGED')
    root=_root(root)
    require(deployment.get('response_format_system')==safe_join(root,draft['system_path']).read_text(encoding='utf8'), 'REAL_V2_FORMATTING_CHANGED')
    payload=envelope.get('payload',{})
    require(payload.get('instructions')==safe_join(root,draft['prompt_path']).read_text(encoding='utf8'), 'REAL_V1D_PROMPT_CHANGED')
    require(payload.get('representation')=='NATIVE_VIDEO_ARRAY' and payload.get('media')==[], 'REAL_REPRESENTATION_MISMATCH')
    native=envelope.get('native_video_array',{})
    require(native.get('aliases')==[s['supplied_alias'] for s in w['selected']], 'REAL_ALIAS_MAPPING_CHANGED')
    require(native.get('native_pts_s')==[s['native_source_pts_s'] for s in w['selected']], 'REAL_NATIVE_PTS_CHANGED')
    from .v1d_execution import inspect_envelope
    inspect_envelope(envelope,call,w,draft,root)
    return {'protocol_sha256':context['frozen_bundle']['freeze_receipt']['protocol_sha256'],
            'execution_authorization_sha256':digest(canonical_bytes(context['execution_authorization'])),
            'call_id':context['call_id'],'representation_status':'FRAME_MATCHED_ONLY', 'source_frames':8,'temporal_units':4}

def dry_run(root=None):
    draft=draft_protocol(root); result=validate_draft(draft,root)
    return {'draft':draft,'readiness':result,'next_freeze_confirmation':'APPROVE_PHASE2B_V1D_FREEZE '+result['draft_sha256']+' NO_EXECUTION',
            'model_initialized':False,'media_read':False,'protocol_frozen':False,'calls_executed':0}
