import copy
import inspect
from pathlib import Path
import pytest
from memory_graph.reasoning import video_experiment as v
from memory_graph.reasoning.common import OUT,ROOT,sha256

def test_exact_nine_complete_ids_boundaries_and_triggers():
    req=v.read(OUT/'qwen/requests.json');es=v.events()
    original={e['pack_id']:e for e in v.read(OUT/'event_windows/event_manifest.json')}
    assert [e['pack_id'] for e in es]==[r['pack_id'] for r in req]
    assert len(es)==9
    for e in es:
        assert e==original[e['pack_id']]
        assert e['completeness']=='COMPLETE_EVENT_WINDOW'

def test_annotation_never_fills_authority_or_context():
    e=v.events()[0];f=e['start_frame']+1
    timeline={e['start_frame']:{'frame':e['start_frame'],'time':e['start_time'],
        'identity_authorized':True,'target_bbox':[1,1,10,10],'anchors':[], 'mask_reference':'x'}}
    r=v.render_row(e,f,timeline, e['start_frame']/e['start_time'])
    assert not r['identity_authorized'] and r['target_bbox'] is None
    assert r['mask_reference'] is None and r['anchors']==[]
    timeline[f]={'frame':f,'time':r['time'],'identity_authorized':False,'target_bbox':[1,1,10,10],
        'mask_reference':'x','anchors':[{'anchor_key':'new_hand','bbox':[1,1,10,10]}]}
    r=v.render_row(e,f,timeline,e['start_frame']/e['start_time'])
    assert not r['identity_authorized'] and r['target_bbox'] is None and r['anchors']==[]

def test_clip_source_timestamps_inside_exact_boundaries():
    dev={d['video_id']:d for d in v.read(OUT/'event_windows/development_inputs.json')}
    for e in v.events():
        fs=list(v.source_frame_indices(e));fps=dev[e['video_id']]['fps']
        assert fs[0]==e['start_frame'] and fs[-1]==e['end_frame']
        assert all(e['start_time']-1e-8<=f/fps<=e['end_time']+1e-8 for f in fs)

def test_prompt_only_video_wording_and_same_schema_roles():
    from memory_graph.reasoning.contract import prompt,KEYS,EVENT_TYPES,RELATIONS
    for e in v.events():
        phases=', '.join(f['phase'] for f in e['frames'])
        expected=prompt(e).replace('over the chronological visual sequence.','over the supplied event video.').replace(
            f'Image phases in order: {phases}. Same-image reference panels repeat that image.',
            'Video phases are trigger-relative. Same-frame reference panels repeat that video frame.')
        assert v.video_prompt(e)==expected
        assert all(k in expected for k in KEYS)
        assert all(k in expected for k in EVENT_TYPES+RELATIONS)

def test_native_request_and_processor_not_image_list():
    msg=v.message(Path('event.mp4'),'prompt')
    assert msg[0]['content'][0]=={'type':'video','path':'event.mp4'}
    text=inspect.getsource(v.processor_inputs)
    assert 'apply_chat_template' in text and 'do_sample_frames=True' in text
    assert 'images=' not in text and 'fps=req' in text

def test_unchanged_baseline_validator_and_identity_sources():
    m=v.read(OUT/'final/final_integrity_manifest.json')
    for p,h in m['sources'].items():assert sha256(ROOT/p)==h
    safety=v.read(OUT/'regression/identity_safety.json')
    assert safety['identity_threshold']==.60 and safety['margin']==.10
    assert safety['unauthorized_matched']==0 and safety['identity_and_memory_unchanged']
    assert v.POLICY['identity_writes']==v.POLICY['trusted_physical_writes']==0

def test_no_new_context_candidates_in_encoded_annotation():
    manifests=v.read(v.EXP/'videos/video_manifest.json');es={e['pack_id']:e for e in v.events()}
    for m in manifests:
        e=es[m['pack_id']]
        assert m['contexts']==e['contexts']
        assert m['actor_markers']==e['actor_markers'] and m['location_markers']==e['location_markers']
        keys={c['key'] for c in e['contexts']}
        assert all(set(r['candidate_keys'])<=keys for r in m['annotation_frames'])
        timeline=v.read(OUT/f"event_windows/target_timelines/{e['video_id']}.json")
        authorized={r['frame'] for r in timeline['rows'] if r['identity_authorized']}
        assert all(not r['T_marked'] or r['source_frame'] in authorized for r in m['annotation_frames'])

def test_real_encoded_cfr_fps_audio_duration_and_decode_count():
    v.setup()
    for m in v.read(v.EXP/'videos/video_manifest.json'):
        meta=v.inspect_clip(m['path'])
        assert meta['constant_frame_rate'] and meta['audio_streams']==0
        assert meta['resolution']==[800,600] and meta['codec']=='h264'
        assert abs(meta['fps']-m['source_fps'])<1e-5
        assert meta['frame_count']==m['end_frame']-m['start_frame']+1
        assert abs(meta['duration']-m['window_duration'])<=1/m['source_fps']+.002
        assert meta['sha256']==m['encoding']['sha256']

def test_baseline_unchanged_and_no_unknown_media_membership():
    check=v.verify_baseline();assert check['valid']
    known={d['path'] for d in v.read(OUT/'event_windows/development_inputs.json')}
    for m in v.read(v.EXP/'videos/video_manifest.json'):assert m['source_path'] in known
    assert v.read(v.EXP/'config/baseline_reference.json')['held_out_accessed'] is False

def test_processor_temporal_density_and_native_modality():
    config=v.read(v.EXP/'config/experiment_config.json')
    assert config['video_processor_target_fps'] in {15.0,10.0}
    metrics=v.read(v.EXP/'processor/processor_metrics.json')
    assert len(metrics)==9
    for m in metrics:
        assert m['native_video_modality'] and not m['image_list_inputs']
        assert m['effective_processor_fps']>=10.0 and m['density_valid']
        assert m['requested_processor_fps']==min(m['source_fps'],config['video_processor_target_fps'])
        assert m['actual_selected_frame_count']/m['clip_duration']==m['effective_processor_fps']

def test_no_operational_graph_or_identity_write_functions():
    text=inspect.getsource(v)
    for token in ['update_trusted_bank(','authorize_match(','restart_sam(','MemoryGraph(','SearchPlanner(']:assert token not in text
