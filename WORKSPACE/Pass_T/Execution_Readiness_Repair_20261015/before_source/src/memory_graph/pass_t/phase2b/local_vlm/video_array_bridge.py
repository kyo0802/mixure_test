"""Feature-gated native Video Array preprocessing; shared NF4 generation stays unchanged."""
from __future__ import annotations
import hashlib,json,math,time

DISABLED='NATIVE_VIDEO_ARRAY_DISABLED'
ENABLED='NATIVE_ARRAY_EXPERIMENTAL'
V1C_SHA256='3ee1259930984abb8ca321f0d4ca14e46843c6cd714516b09ef94d1b94223722'

def tensor_record(tensor):
    import numpy as np
    import torch
    if not isinstance(tensor,torch.Tensor) or tensor.device.type!='cpu' or tensor.layout!=torch.strided:
        raise ValueError('CPU_STRIDED_TENSOR_REQUIRED')
    array=tensor.detach().contiguous().numpy()
    dtype=array.dtype.newbyteorder('<')
    array=np.asarray(array,dtype=dtype,order='C')
    header={'serialization':'TENSOR_LE_C_V1','dtype':dtype.str,'shape':list(tensor.shape)}
    raw=array.tobytes(order='C')
    return {**header,'torch_dtype':str(tensor.dtype),'device':str(tensor.device),'numel':tensor.numel(),
      'layout':str(tensor.layout),'contiguous':tensor.is_contiguous(),'strides':list(tensor.stride()),
      'canonical_sha256':hashlib.sha256(json.dumps(header,sort_keys=True,separators=(',',':')).encode()+b'\n'+raw).hexdigest(),
      'raw_le_c_sha256':hashlib.sha256(raw).hexdigest()}

def static_timeline(aliases,pts,fps,seconds):
    import torch
    indices=torch.arange(4).view(-1,1)
    # Installed get_rope_index converts seconds to range_tensor.dtype (int64)
    # before multiplication. These are relative contributions, not absolute IDs.
    source_seconds=torch.as_tensor(seconds,dtype=indices.dtype)
    ids=(indices*source_seconds*2).long().flatten().tolist()
    rows=[]
    for i,(alias,t) in enumerate(zip(aliases,pts)):
        native=t-pts[0];nominal=i/fps;unit=i//2;processor=unit*seconds;proxy=ids[unit]/2
        rows.append({'source_frame_position':i,'alias':alias,'native_synthetic_pts_s':t,'native_relative_s':native,
          'reconstructed_frame_time_s':nominal,'temporal_unit':unit,'unit_aliases':aliases[unit*2:unit*2+2],
          'unit_native_span_s':pts[unit*2:unit*2+2],'processor_unit_time_s':processor,
          'seconds_per_grid_ts':seconds,'seconds_after_source_integer_cast':int(source_seconds.item()),
          'static_relative_model_temporal_id':ids[unit],'id_div_tokens_per_second_proxy_s':proxy,
          'nominal_reconstruction_error_s':nominal-native,'processor_quantization_from_nominal_s':processor-nominal,
          'processor_unit_vs_native_error_s':processor-native,'static_model_proxy_error_s':proxy-native,
          'runtime_position_verification':'STATIC_SOURCE_CALCULATION_NOT_ACTUAL_FORWARD_POSITIONS'})
    return rows

def prepare_video_array(processor,envelope,deployment):
    """Local in-process opt-in extension; no AVI/image fallback or new prediction schema."""
    import numpy as np
    import torch
    from transformers.video_utils import VideoMetadata
    from .qwen_contract import grid_accounting,processor_size
    from ..predictions import schema
    started=time.perf_counter()
    if deployment.get('video_input_mode',DISABLED)!=ENABLED:
        raise ValueError('NATIVE_VIDEO_ARRAY_NOT_ENABLED')
    if deployment.get('identity_clause_enabled',False) is not False:
        raise ValueError('IDENTITY_CLAUSE_NOT_APPROVED')
    bundle=envelope.get('native_video_array')
    if not isinstance(bundle,dict) or set(bundle)!={'frames','aliases','native_pts_s','source_rgb_sha256'}:
        raise ValueError('EXPLICIT_NATIVE_VIDEO_ARRAY_REQUIRED')
    array=bundle['frames'];aliases=bundle['aliases'];pts=bundle['native_pts_s']
    if (not isinstance(array,np.ndarray) or array.shape[0]!=8 or array.ndim!=4 or array.shape[-1]!=3
        or array.dtype!=np.uint8 or not array.flags.c_contiguous or min(array.shape[1:3])<28):
        raise ValueError('EXACTLY_EIGHT_ORDERED_RGB_UINT8_THWC_FRAMES_REQUIRED')
    import re
    if len(aliases)!=8 or len(set(aliases))!=8 or any(not isinstance(a,str) or re.fullmatch(r'F\d{4}',a) is None for a in aliases):
        raise ValueError('EIGHT_UNIQUE_SOURCE_ALIASES_REQUIRED')
    if len(pts)!=8 or any(type(t) not in {int,float} or not math.isfinite(t) for t in pts) or any(b<=a for a,b in zip(pts,pts[1:])):
        raise ValueError('STRICTLY_INCREASING_PRIVATE_PTS_REQUIRED')
    rgb_hashes=[hashlib.sha256(frame.tobytes()).hexdigest() for frame in array]
    if rgb_hashes!=bundle['source_rgb_sha256']:raise ValueError('SOURCE_RGB_HASH_OR_ORDER_MISMATCH')
    payload=envelope['payload']
    if payload.get('representation')!='NATIVE_VIDEO_ARRAY' or payload.get('media')!=[]:
        raise ValueError('EXPLICIT_IN_PROCESS_NATIVE_ARRAY_ROUTE_REQUIRED')
    prompt=payload['instructions']
    expected_prompt_sha256=deployment.get('experimental_task_prompt_sha256',V1C_SHA256)
    if expected_prompt_sha256!=V1C_SHA256 and (
        deployment.get('synthetic_only') is not True or deployment.get('experimental_task_prompt_candidate')!='V1D'
        or not isinstance(expected_prompt_sha256,str) or re.fullmatch(r'[0-9a-f]{64}',expected_prompt_sha256) is None):
        raise ValueError('EXPLICIT_PINNED_SYNTHETIC_V1D_CANDIDATE_REQUIRED')
    if hashlib.sha256(prompt.encode()).hexdigest()!=expected_prompt_sha256:raise ValueError('PINNED_TASK_PROMPT_HASH_CHANGED')
    cap=deployment['processor_max_pixels']
    if cap!=200704:raise ValueError('PINNED_PIXEL_CAP_REQUIRED')
    for component in [processor.image_processor,processor.video_processor]:
        component.size=processor_size(cap);component.min_pixels=3136;component.max_pixels=cap
    video=processor.video_processor
    if (video.temporal_patch_size,video.patch_size,video.merge_size)!=(2,14,2):
        raise ValueError('PINNED_VIDEO_PATCH_CONFIGURATION_REQUIRED')
    content=[{'type':'text','text':'Supplied aliases: '+', '.join(aliases)},{'type':'video'},
      {'type':'text','text':prompt+'\nRequired JSON schema:\n'+json.dumps(schema())}]
    messages=[{'role':'system','content':[{'type':'text','text':deployment['response_format_system']}]},
      {'role':'user','content':content}]
    rendered=processor.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
    if rendered.count('<|video_pad|>')!=1 or '<|image_pad|>' in rendered:raise ValueError('VIDEO_MARKER_REQUIRED')
    fps=7/(pts[-1]-pts[0])
    inputs=processor(text=[rendered],videos=[array],video_metadata=[VideoMetadata(total_num_frames=8,fps=fps,duration=8/fps)],
      fps=fps,do_sample_frames=False,return_tensors='pt',return_metadata=False,device='cpu')
    expected={'input_ids','attention_mask','pixel_values_videos','video_grid_thw','second_per_grid_ts'}
    if set(inputs)!=expected or any(t.device.type!='cpu' for t in inputs.values()):raise ValueError('NATIVE_VIDEO_CPU_TENSORS_REQUIRED')
    grid=inputs['video_grid_thw'].tolist()
    if len(grid)!=1 or grid[0][0]!=4:raise ValueError('EIGHT_FRAMES_FOUR_UNITS_REQUIRED')
    seconds=float(inputs['second_per_grid_ts'][0])
    if not math.isclose(seconds,2/fps,rel_tol=1e-6):raise ValueError('PROCESSOR_TIME_METADATA_MISMATCH')
    accounting=grid_accounting(inputs)
    if any(v>cap for vs in accounting['per_grid_spatial_pixels'].values() for v in vs):raise ValueError('PIXEL_CAP_EXCEEDED')
    receipt={'video_input_mode':ENABLED,'representation_status':'FRAME_MATCHED_ONLY','native_video_modality':True,
      'processor_seconds':time.perf_counter()-started,'processor_frame_count':8,'processed_frame_aliases':aliases,
      'source_rgb_sha256':rgb_hashes,'processor_selected_indices':list(range(8)),'do_sample_frames':False,
      'temporal_patch_count':4,'temporal_patch_size':2,'temporal_padding':0,'reference_image_count':0,
      'processor_fps':fps,'second_per_grid_ts':inputs['second_per_grid_ts'].tolist(),
      'native_pts_model_visible':False,'native_time_sidecar_usage':'span only determines FPS; individual native PTS never serialized',
      'rendered_prompt':rendered,'rendered_prompt_sha256':hashlib.sha256(rendered.encode()).hexdigest(),
      'task_prompt_sha256':expected_prompt_sha256,'configured_pixel_cap':cap,'input_image_dimensions':[],
      'alias_unit_mapping':[{'unit':i//2,'aliases':aliases[i:i+2]} for i in range(0,8,2)],
      'static_timeline':static_timeline(aliases,pts,fps,seconds),'actual_model_positions':'NOT_INSTRUMENTED',
      'identity_clause_enabled':False,'tensor_records':{k:tensor_record(v) for k,v in inputs.items()},**accounting}
    return inputs,receipt
