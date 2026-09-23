"""Deterministic, conservative multi-cue association. No VLM/GT-driven merges."""
import math
import numpy as np
from .quality import similarity
from .contracts import PersistentEntity


def pair_evidence(previous, current, features, config):
    a,b = previous.observations[-1],current.observations[0]
    gap = b.timestamp-a.timestamp
    distance = math.dist(a.normalized_center,b.normalized_center)
    app = similarity(features[previous.track_id][-1],features[current.track_id][0])
    scale = min(a.area_fraction,b.area_fraction)/max(a.area_fraction,b.area_fraction,1e-9)
    predicted = np.array(a.normalized_center)+np.clip(np.array(a.velocity)*max(0,gap),-.2,.2)
    motion = math.dist(predicted,b.normalized_center)
    n1,n2 = {x['track_id'] for x in a.nearest_tracks},{x['track_id'] for x in b.nearest_tracks}
    context = len(n1 & n2)/len(n1 | n2) if n1|n2 else None
    semantic = previous.detector_class == current.detector_class
    score = (.30*(app or 0)+.25*max(0,1-distance/config.max_center_distance)+
             .20*max(0,1-motion/config.max_center_distance)+.15*scale+.10*float(semantic))
    eligible = (0<gap<=config.max_association_gap and distance<=config.max_center_distance
                and motion<=config.max_center_distance and app is not None
                and app>=config.min_appearance_similarity and scale>=.5)
    return {'previous_track_id':previous.track_id,'track_id':current.track_id,'temporal_gap':gap,
        'temporal_compatible':0<gap<=config.max_association_gap,'semantic_compatibility':semantic,
        'appearance_similarity':app,'center_distance':distance,'motion_prediction_error':motion,
        'bbox_area_ratio':scale,'context_jaccard':context,'stable_anchor_context':None,
        'interaction_continuity':None,'score':score,'eligible':eligible,
        'semantic_note':'Detector hypotheses only; equality never suffices for association.'}


def resolve(tracks, quality, features, metadata, config):
    lookup = {t.track_id:t for t in tracks}
    entities, associations, rejected = [], [], []
    for track in sorted(tracks,key=lambda t:(t.first_seen,t.track_id)):
        q = quality[track.track_id]
        if not q['usable_for_identity']:
            rejected.append({'track_id':track.track_id,'reason':q['flags']})
            continue
        candidates = []
        for entity in entities:
            prev = lookup[entity.local_track_ids[-1]]
            evidence = pair_evidence(prev,track,features,config)
            evidence['entity_id'] = entity.entity_id
            # Any temporal overlap anywhere in the entity is a hard cannot-link.
            overlap = any(not(track.first_seen>lookup[x].last_seen or track.last_seen<lookup[x].first_seen)
                          for x in entity.local_track_ids)
            evidence['temporal_overlap'] = overlap
            evidence['quality_veto'] = any(flag in q['flags'] or flag in quality[prev.track_id]['flags']
                                            for flag in ['UNSTABLE','POSSIBLE_ID_SWITCH'])
            evidence['eligible'] &= not overlap and not evidence['quality_veto']
            if 0<evidence['temporal_gap']<=config.max_association_gap or evidence['eligible']:
                candidates.append(evidence)
        eligible = sorted([c for c in candidates if c['eligible']], key=lambda c:-c['score'])
        decision = 'NEW_ENTITY'
        if eligible:
            top = eligible[0]
            if top['score']>=config.min_match_score and (len(eligible)==1 or top['score']-eligible[1]['score']>=config.ambiguity_margin):
                decision='MATCH'
            else:
                decision='AMBIGUOUS'
        if decision=='MATCH':
            entity=next(e for e in entities if e.entity_id==eligible[0]['entity_id'])
            entity.local_track_ids.append(track.track_id)
        else:
            entity=PersistentEntity(entity_id=f'entity_{len(entities)+1:04d}',local_track_ids=[track.track_id],
                first_seen=track.first_seen,last_confirmed_seen=track.last_seen,
                last_confirmed_bbox=track.observations[-1].bbox,visibility='UNOBSERVED',uncertainty=1)
            entities.append(entity)
        record={'track_id':track.track_id,'entity_id':entity.entity_id,'decision':decision,
                'candidates':sorted(candidates,key=lambda c:-c['score']),
                'reason':'multi-cue gated match' if decision=='MATCH' else 'no forced merge; independent hypothesis'}
        associations.append(record)
        entity.association_history.append(record)
        entity.last_confirmed_seen=track.last_seen
        entity.last_confirmed_bbox=track.observations[-1].bbox
    for entity in entities:
        observations={o.frame_index:o for tid in entity.local_track_ids for o in lookup[tid].observations}
        last=None
        for frame in metadata.sampled_frames:
            if frame.timestamp<entity.first_seen: continue
            now=observations.get(frame.frame_index)
            if now: last=now
            if last is None: continue
            age=frame.timestamp-last.timestamp
            state='VISIBLE' if now else 'LOST' if age>=config.lost_after_seconds else 'UNOBSERVED'
            entity.visibility_history.append({'frame_index':frame.frame_index,'timestamp':frame.timestamp,
                'state':state,'last_confirmed_seen':last.timestamp,
                'current_bbox':list(now.bbox) if now else None,'uncertainty':min(1,age/config.lost_after_seconds) if not now else 1-now.confidence})
        tail=entity.visibility_history[-1]
        entity.visibility=tail['state']; entity.current_bbox=tail['current_bbox']; entity.uncertainty=tail['uncertainty']
    return entities, associations, rejected
