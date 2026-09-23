"""Audit frozen inference outputs; review artifacts intentionally outside prediction manifest."""
import argparse
from pathlib import Path
import cv2
from memory_graph.v21.artifacts import read
from memory_graph.v21.contracts import PersistentEntity
from memory_graph.v21.contracts import ContextResult
from memory_graph.v21.graphs import convert_relations
from memory_graph.perception.track_manager import sha256
from memory_graph.memory.memory_store import save_json


def audit(output):
    output=Path(output); errors=[]
    manifest=read(output/'prediction_manifest.json')
    # Earlier runs may have created the independent review folder concurrently.
    # Exclude only those non-prediction entries, never change a prediction hash.
    cleaned={p:h for p,h in manifest.items() if not p.startswith('gt_review/')}
    if cleaned!=manifest:save_json(output/'prediction_manifest.json',cleaned)
    for name,digest in cleaned.items():
        if not(output/name).is_file() or sha256(output/name)!=digest:errors.append('Modified frozen prediction: '+name)
    entities=[PersistentEntity.model_validate(x) for x in read(output/'persistent_entities.json')]
    ids={e.entity_id for e in entities}; tracks=[t for e in entities for t in e.local_track_ids]
    if len(tracks)!=len(set(tracks)):errors.append('Track belongs to more than one entity')
    mapping={t:e.entity_id for e in entities for t in e.local_track_ids}
    quality=read(output/'track_quality_report.json')
    if set(tracks)!={q['track_id'] for q in quality if q['usable_for_identity']}:errors.append('Usable track lost before identity')
    for e in entities:
        for sample in e.visibility_history:
            if sample['state']!='VISIBLE' and sample['current_bbox'] is not None:errors.append('Invented box')
        for name in ['contact_sheet.jpg','entity.json','association_history.json']:
            if not(output/'entities'/e.entity_id/name).is_file():errors.append('Missing entity artifact')
    for q in quality:
        for name in ['contact_sheet.jpg','tracklet.json']:
            if not(output/'tracklets'/f"track_{q['track_id']}"/name).is_file():errors.append('Missing tracklet artifact')
    for rel in read(output/'memory_graph.json')['relations']:
        if rel['predicate'].startswith('IMAGE_') or not rel['ever_promoted']:errors.append('Unpromoted physical memory claim')
        if not {rel['subject_entity_id'],rel['object_entity_id']}<=ids:errors.append('Dangling endpoint')
    for name in ['tracking_diagnostic_timeline.png','memory_graph_overview.png','observation_graph_debug.png']:
        if cv2.imread(str(output/name)) is None:errors.append('Unreadable '+name)
    scenes=[];contexts=[]
    for event in read(output/'event_analysis'/'active_event_ids.json'):
        directory=output/'event_analysis'/'events'/event
        scenes.append(read(directory/'scene_graph.json'))
        if (directory/'persistent_context_vlm.json').is_file():
            record=read(directory/'persistent_context_vlm.json')
            validated=ContextResult.model_validate(record['validated']) if record.get('validated') else None
            contexts.append((validated,read(directory/'persistent_context_input.json')))
    metadata=read(output/'event_analysis'/'video_metadata.json')
    observation,candidates,memory=convert_relations(scenes,mapping,contexts,metadata['duration'])
    for actual,expected,name in [(observation,read(output/'observation_graph.json')['relations'],'observation'),
                                  (candidates,read(output/'relation_candidates.json'),'candidates'),
                                  (memory,read(output/'memory_graph.json')['relations'],'memory')]:
        if actual!=expected:errors.append('Current graph rules differ from frozen '+name)
    status=read(output/'run_status.json')
    baseline=read('docs/v21_preservation_baseline.json')
    changed=[p for p,h in baseline.items() if not Path(p).is_file() or sha256(p)!=h]
    errors.extend('V1/V2 changed: '+p for p in changed)
    result={'passed':not errors,'errors':errors,'preserved_baseline_files':len(baseline),
            'inference_gt_parameter':False,'all_usable_tracks_resolved':len(mapping),'status':status}
    save_json(output/'evaluation_audit.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('outputs',nargs='+');args=parser.parse_args()
    results=[audit(p) for p in args.outputs]
    save_json('docs/v21_artifact_audit.json',results)
    print([(r['passed'],r['errors']) for r in results])
    raise SystemExit(int(any(not r['passed'] for r in results)))
