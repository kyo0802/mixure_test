"""Shared NF4 task formatting/generation controls; no load on import."""
import hashlib,json,math
from ..common import Phase2BBlocked,canonical_bytes

CONTRACT_VERSION='QWEN_NF4_PARITY_V3_SYNTHETIC_VERIFIED_CANDIDATE'
def validate_modalities(payload):
    video=[r for r in payload['media'] if r['media_type']=='video/x-msvideo']
    if payload['representation']=='REENCODED_AUTHORIZED_VIDEO':
        if len(video)!=1 or video[0]['media_id'].startswith('REFERENCE_'):
            raise Phase2BBlocked('NATIVE_VIDEO_REQUIRED_NO_IMAGE_LIST_FALLBACK')
        if any(r['media_type']!='video/x-msvideo' and not r['media_id'].startswith('REFERENCE_') for r in payload['media']):
            raise Phase2BBlocked('ONLY_STATIC_REFERENCES_ALLOWED_BESIDE_NATIVE_VIDEO')
    elif video:raise Phase2BBlocked('VIDEO_CANNOT_BE_SERIALIZED_AS_IMAGE_REPRESENTATION')
    for row in payload['media']:
        if row['media_id'].startswith('REFERENCE_') and (row['media_type']!='image/png' or row['supplied_frame_aliases']):
            raise Phase2BBlocked('STATIC_REFERENCE_MUST_BE_IMAGE_AND_NON_CITABLE')

def generation_controls(generation,deadline):
    maximum=generation['max_output_tokens'];sampling=generation['sampling']
    if type(maximum) is not int or maximum<=0 or type(sampling) is not bool or deadline<=0:
        raise Phase2BBlocked('INVALID_GENERATION_CONTROLS')
    kwargs={'max_new_tokens':maximum,'do_sample':sampling,'max_time':deadline}
    if sampling:
        if generation.get('temperature',0)<=0:raise Phase2BBlocked('POSITIVE_SAMPLING_TEMPERATURE_REQUIRED')
        kwargs['temperature']=generation['temperature']
        for key in ('top_p','top_k'):
            if key in generation:kwargs[key]=generation[key]
    return kwargs,generation.get('seed')

def messages(payload,media,schema,system,selected_video_aliases=None):
    validate_modalities(payload)
    if len(media)!=len(payload['media']):raise Phase2BBlocked('MEDIA_ASSET_COUNT_MISMATCH')
    content=[];serialization=[]
    for row,asset in zip(payload['media'],media):
        reference=row['media_id'].startswith('REFERENCE_')
        aliases=selected_video_aliases if row['media_type']=='video/x-msvideo' else row['supplied_frame_aliases']
        label='Static target reference only; non-citable for events.' if reference else 'Supplied aliases: '+', '.join(aliases)
        content.append({'type':'text','text':label})
        content.append({'type':'video','path':str(asset)} if row['media_type']=='video/x-msvideo' else {'type':'image','image':asset})
        serialization.append({'type':row['media_type'],'sha256':row['content_sha256'],'aliases':aliases,'framing':label})
    task=payload['instructions']+'\nRequired JSON schema:\n'+json.dumps(schema)
    content.append({'type':'text','text':task})
    conversation=[{'role':'user','content':content}]
    if system:conversation.insert(0,{'role':'system','content':[{'type':'text','text':system}]})
    contract={'version':CONTRACT_VERSION,'system':system,'task':task,'ontology':payload['ontology'],
              'target':payload['target'],'representation':payload['representation'],'media':serialization,
              'ordering':'system; per-media neutral aliases/reference framing; media; common task+schema'}
    return conversation,contract,hashlib.sha256(canonical_bytes(contract)).hexdigest()

def processor_size(pixels):
    if type(pixels) is not int or pixels<3136:raise Phase2BBlocked('INVALID_PROCESSOR_PIXEL_BUDGET')
    return {'shortest_edge':3136,'longest_edge':pixels}

def grid_accounting(inputs,merge_size=2,patch_size=14):
    grids={k:inputs[k].tolist() for k in ['image_grid_thw','video_grid_thw'] if k in inputs}
    return {'grids':grids,'grid_derived_visual_tokens':sum(math.prod(g)//merge_size**2 for gs in grids.values() for g in gs),
            'resized_dimensions_hw':{k:[[g[1]*patch_size,g[2]*patch_size] for g in gs] for k,gs in grids.items()},
            'per_grid_spatial_pixels':{k:[g[1]*g[2]*patch_size**2 for g in gs] for k,gs in grids.items()}}

def verify_processed_aliases(request,response,explicit_video_sampling=False):
    aliases=list(dict.fromkeys(a for row in request['media'] for a in row['supplied_frame_aliases']))
    if request['representation']!='REENCODED_AUTHORIZED_VIDEO' or not explicit_video_sampling:
        if response.get('processed_frame_aliases')!=aliases:raise Phase2BBlocked('PROCESSOR_DROPPED_REORDERED_OR_ADDED_FRAMES')
        return aliases
    video=[r for r in request['media'] if r['media_type']=='video/x-msvideo']
    if len(video)!=1:raise Phase2BBlocked('ONE_NATIVE_VIDEO_REQUIRED')
    source=video[0]['supplied_frame_aliases'];indices=response.get('processor_selected_indices')
    if (not isinstance(indices,list) or not indices or any(type(i) is not int or not 0<=i<len(source) for i in indices)
            or indices!=sorted(set(indices)) or response.get('encoded_frame_count')!=len(source)
            or response.get('actually_selected_indices')!=indices or response.get('native_video_modality') is not True):
        raise Phase2BBlocked('UNVERIFIED_NATIVE_VIDEO_SELECTION')
    selected=[source[i] for i in indices]
    if response.get('processed_frame_aliases')!=selected:raise Phase2BBlocked('PROCESSED_VIDEO_ALIAS_MAPPING_MISMATCH')
    return selected
