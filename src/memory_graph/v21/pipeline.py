"""V2.1 extension. Inference has no annotation/GT argument or evaluator dependency."""
from pathlib import Path
import shutil
import time
from ..perception.track_manager import collect_tracks, sha256
from ..pipeline_v2 import run_video_v2
from ..memory.memory_store import save_json
from ..vlm.base import create_backend
from .contracts import IdentityConfig
from .artifacts import read,track_artifacts,entity_artifacts
from .quality import measure
from .resolver import resolve
from .context import build_context,analyze_context
from .graphs import convert_relations,attach_semantics
from .visualization import render_graph,render_timeline


def run(source,config,output,reuse=None,events_only=False):
    start=time.monotonic(); source=Path(source).resolve(); output=Path(output).resolve()
    protected=[Path(p).resolve() for p in ['outputs','outputs_v2','outputs_v2_events','outputs_v1_comparison','src','tests','configs','.models']]
    if output==Path.cwd() or any(output==p or p in output.parents or output in p.parents for p in protected):
        raise ValueError('V2.1 requires a separate output directory')
    output.mkdir(parents=True,exist_ok=True); legacy=output/'event_analysis'; legacy.mkdir(exist_ok=True)
    save_json(output/'run_status.json',{'status':'running'})
    identity_config=IdentityConfig()
    save_json(output/'identity_config.json',identity_config)
    if reuse:
        reuse=Path(reuse)
        fingerprint=read(reuse/'perception_cache.json')
        if fingerprint['source_sha256']!=sha256(source): raise ValueError('Reuse video hash mismatch')
        for name in ['perception_cache.json','video_metadata.json','episodes.json','detections.json','track_timelines.json','track_id_mapping.json']:
            shutil.copy2(reuse/name,legacy/name)
        # Content addressed keys are revalidated by the unchanged V2 backend/cache.
        if (reuse/'.vlm_cache').is_dir(): shutil.copytree(reuse/'.vlm_cache',legacy/'.vlm_cache',dirs_exist_ok=True)
    metadata,episodes,tracks=collect_tracks(source,legacy,config)
    features,crops=track_artifacts(source,tracks,output)
    period=1/min(config.perception.video.sample_fps,metadata.fps)
    quality={t.track_id:measure(t,features[t.track_id],period,identity_config) for t in tracks}
    entities,associations,rejected=resolve(tracks,quality,features,metadata,identity_config)
    mapping={tid:e.entity_id for e in entities for tid in e.local_track_ids}
    for a in associations:
        quality[a['track_id']]['fragmentation_context']=a['candidates']
    save_json(output/'track_quality_report.json',list(quality.values()))
    save_json(output/'track_entity_associations.json',associations)
    save_json(output/'ambiguous_associations.json',[a for a in associations if a['decision']=='AMBIGUOUS'])
    save_json(output/'identity_rejected_tracks.json',rejected)
    # Identity is already resolved and saved BEFORE any event-specific admission/semantic evidence.
    save_json(output/'persistent_entities_pre_semantics.json',entities)
    backend=None if events_only else create_backend(config.vlm)
    run_video_v2(source,config,legacy,events_only=events_only,backend=backend)
    aggregation=read(legacy/'semantic_aggregation.json')
    attach_semantics(entities,aggregation)
    old_rejected=read(legacy/'rejected_tracks.json')
    admission={'usable_tracks_before_admission':len(mapping),'usable_tracks_removed_before_identity':0,
        'v2_counterfactual_removed':[r for r in old_rejected if r['track_id'] in mapping],
        'identity_relevant_removed':'NOT MEASURABLE FROM CURRENT GT; evaluation-only mapping required',
        'meaning':'V2 semantic admission is diagnostic only; it cannot delete V2.1 identities.'}
    save_json(output/'admission_failures.json',admission)
    scenes=[]; context_results=[]; context_counts={'attempted':0,'valid':0,'failed':0,'cache_hits':0}
    for event_id in read(legacy/'active_event_ids.json'):
        event_path=legacy/'events'/event_id
        scenes.append(read(event_path/'scene_graph.json'))
        context,images=build_context(event_path,tracks,mapping,source,identity_config)
        save_json(event_path/'persistent_context_input.json',context)
        if backend is not None:
            context_counts['attempted']+=1
            print(f'Persistent context {source.name} {event_id}',flush=True)
            result,hit=analyze_context(backend,event_path,context,images,output/'.context_cache')
            context_counts['valid']+=int(result is not None); context_counts['failed']+=int(result is None)
            context_counts['cache_hits']+=int(hit)
            context_results.append((result,context))
    observations,candidates,relations=convert_relations(scenes,mapping,context_results,metadata.duration)
    save_json(output/'persistent_entities.json',entities)
    common={'schema_version':'2.1','video':source.name,'entities':entities,'not_true_3d':True}
    save_json(output/'observation_graph.json',{**common,'relations':observations,'reference_frame':'image_plane or explicitly marked physical hypothesis'})
    save_json(output/'relation_candidates.json',candidates)
    save_json(output/'memory_graph.json',{**common,'relations':relations,
        'policy':'Only independently supported physical hypotheses; IMAGE_* observations never promoted.',
        'supported_states':['OBSERVATION_ONLY','CANDIDATE','PROMOTED','STALE','ENDED'],
        'state_note':'No automatic ENDED from non-detection; no asserted OCCLUDED/OUT_OF_VIEW without evidence.'})
    entity_artifacts(entities,crops,output)
    render_timeline(tracks,quality,mapping,output/'tracking_diagnostic_timeline.png')
    render_graph(entities,observations,output/'observation_graph_debug.png','Observation graph (IMAGE_* is not physical geometry)')
    render_graph(entities,relations,output/'memory_graph_overview.png','Physical temporal memory (sparse is allowed)')
    status={'status':'complete','video_sha256':sha256(source),'local_tracks':len(tracks),'usable_tracks':len(mapping),
        'persistent_entities':len(entities),'matches':sum(a['decision']=='MATCH' for a in associations),
        'ambiguous':sum(a['decision']=='AMBIGUOUS' for a in associations),'context_vlm':context_counts,
        'observation_relations':len(observations),'physical_candidates':len(candidates),'promoted_relations':len(relations),
        'v2_counterfactual_admission_loss':len(admission['v2_counterfactual_removed']),
        'model':backend.identity if backend else {'backend':'disabled'},'elapsed_seconds':time.monotonic()-start,
        'inference_order':['perception','quality','persistent_identity','events_vlm','graphs'],
        'gt_used':False}
    save_json(output/'run_status.json',status)
    evaluation_names={'gt_review','error_analysis.json','bottleneck_assessment.json','validation_report.md','evaluation_audit.json'}
    files=[p for p in output.rglob('*') if p.is_file() and not any(x.startswith('.') or x in evaluation_names for x in p.relative_to(output).parts)]
    save_json(output/'prediction_manifest.json',{str(p.relative_to(output)).replace('\\','/'):sha256(p) for p in files if p.name!='prediction_manifest.json'})
    return status
