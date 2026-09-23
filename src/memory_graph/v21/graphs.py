"""Keep image-plane observations out of physical memory; promote conservatively."""
from collections import defaultdict
from ..vlm.schemas import INTERACTIONS

IMAGE_PREDICATES={'LEFT_OF','RIGHT_OF','ABOVE','BELOW','NEAR','OVERLAPPING'}


def convert_relations(scenes,mapping,context_results,duration):
    observations=[]; candidates=[]
    for scene in scenes:
        for r in scene['relations']:
            a,b=mapping.get(r['subject_track_id']),mapping.get(r['object_track_id'])
            if not a or not b or a==b: continue
            pred=r['predicate']; vlm=r['evidence']['vlm']
            image_only=pred in IMAGE_PREDICATES or not vlm
            item={'subject_entity_id':a,'object_entity_id':b,'predicate':'IMAGE_'+pred if image_only else pred,
                'reference_frame':'image_plane' if image_only else 'physical_hypothesis',
                'observation_confidence':r['confidence'],'physical_confidence':None,
                'memory_status':'OBSERVATION_ONLY' if image_only else 'CANDIDATE',
                'start_time':r['start_time'],'end_time':r['end_time'],'observed_times':r['observed_times'],
                'event_ids':r['event_ids'],'evidence':r['evidence']}
            observations.append(item)
            if not image_only: candidates.append(item)
    for result,context in context_results:
        if result is None: continue
        for claim in result.claims:
            phases=[f for f in context['frames'] if f['phase'] in claim.supporting_phases]
            covisible=[f for f in phases if {claim.subject_entity_id,claim.object_entity_id}<=set(f['visible_entity_ids'])]
            times=[f['timestamp'] for f in phases]
            if not times: continue
            candidates.append({'subject_entity_id':claim.subject_entity_id,'object_entity_id':claim.object_entity_id,
                'predicate':claim.predicate,'reference_frame':'physical_hypothesis','observation_confidence':None,
                'physical_confidence':claim.confidence,'memory_status':'CANDIDATE',
                'start_time':min(times),'end_time':max(times),'observed_times':times,'event_ids':[result.event_id],
                'evidence':{'vlm':True,'decision':result.decision,'co_visible_frames':len({f['timestamp'] for f in covisible}),
                            'explanation':claim.explanation,'historical_crop_is_not_current_evidence':True}})
    # Promotion requires repeated independent event support and two actual co-visible frames.
    groups=defaultdict(list)
    for c in candidates: groups[(c['subject_entity_id'],c['predicate'],c['object_entity_id'])].append(c)
    memory=[]
    for group in groups.values():
        supported=[c for c in group if c['evidence'].get('decision')=='SUPPORTED'
                   and c['evidence'].get('co_visible_frames',0)>=2 and (c['physical_confidence'] or 0)>=.8]
        events={e for c in supported for e in c['event_ids']}
        independent=any(set(a['event_ids']).isdisjoint(b['event_ids']) and
                        set(a['observed_times']).isdisjoint(b['observed_times'])
                        for i,a in enumerate(supported) for b in supported[i+1:])
        for c in group:
            promote=c in supported and len(events)>=2 and independent
            # Repetition alone is insufficient: require an independently geometry-validated V2 claim.
            geometry_support=any(x['evidence'].get('details',{}).get('phase_checks') and x['evidence'].get('geometry')!='conflicts' for x in group)
            promote &= geometry_support
            c['promotion_reason']='independent event, tracking and geometry support' if promote else 'insufficient independent physical evidence'
            c['memory_status']=('STALE' if duration-c['end_time']>4 else 'PROMOTED') if promote else 'CANDIDATE'
            c['ever_promoted']=bool(promote)
            if promote: memory.append(c)
    return observations,candidates,memory


def attach_semantics(entities,aggregation):
    lookup={r['track_id']:r for r in aggregation}
    for entity in entities:
        entries=[lookup[t] for t in entity.local_track_ids if t in lookup]
        entity.semantic_evidence=[{'track_id':e['track_id'],'class':e['semantic_class'],
            'confidence':e['semantic_confidence'],'event_evidence':e['evidence']} for e in entries]
        labels={e['semantic_class'] for e in entries if e['semantic_class']!='unknown'}
        entity.semantic_class=next(iter(labels)) if len(labels)==1 else 'unknown'
