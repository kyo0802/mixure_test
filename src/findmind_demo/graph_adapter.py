"""Read-only projection of persisted records, never a memory writer or ranker."""
import copy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from .sessions import load_session

KINDS=('Candidate','Identity','Observation','Region','SpatialEvidence','Event')


def node_id(session, kind, record):
    return session+'|'+kind+'|'+str(record)


def project(graph, session):
    meta=graph['metadata'];nodes={};records={};edges=[];lookup={};seen=set()
    def add(kind,rid,record,pointer,category=None,times=(),frames=(),status='OBSERVED',label=None):
        nid=node_id(session,kind,rid)
        if nid in nodes:return nid
        nodes[nid]=dict(id=nid,kind=kind,record_id=rid,source_pointer=pointer,category=category,
            times=list(times),frames=list(frames),status=status,label=label or str(rid),session_id=session)
        records[nid]=record;lookup[rid]=nid
        return nid
    def edge(a,b,predicate,pointer,status='REFERENCE',reference_only=False):
        if a not in nodes or b not in nodes:return
        key=(a,b,predicate)
        if key in seen:return
        seen.add(key);edges.append(dict(id=hashlib.sha256(repr(key).encode()).hexdigest()[:24],
            source=a,target=b,predicate=predicate,source_pointer=pointer,status=status,reference_only=reference_only))
    observations=meta.get('observations',[])
    by_obs={o['observation_id']:o for o in observations}
    for i,o in enumerate(observations):
        times=o.get('source_times_s',[]);frames=o.get('source_frame_indices',[]);cat=o.get('object_category')
        add('Observation',o['observation_id'],o,f'/metadata/observations/{i}',cat,times,frames,
            'VLM_CLAIM' if o.get('source')=='VLM' else 'OBSERVED',
            f"{cat} · {times[-1]:.3f}s · {o.get('source','?')}" if times else str(cat))
        candidate=o.get('object_instance_candidate')
        if candidate:
            nid=add('Candidate',candidate,dict(candidate_id=candidate,identity_scope='UNRESOLVED_LOCAL_REFERENCE',
                observation_ids=[]),f'/metadata/observations/{i}/object_instance_candidate',cat,
                status='UNRESOLVED',label=f'{cat} candidate · {candidate[-8:]}')
            records[nid]['observation_ids'].append(o['observation_id'])
            nodes[nid]['times'].extend(t for t in times if t not in nodes[nid]['times'])
            nodes[nid]['frames'].extend(f for f in frames if f not in nodes[nid]['frames'])
        # Authorization requires the explicit capability evidence, not the ID string alone.
        if o.get('authorized_entity_id') and o.get('identity_authorization'):
            eid=o['authorized_entity_id']
            nid=add('Identity',eid,dict(entity_id=eid,authorization=o['identity_authorization']),
                f'/metadata/observations/{i}/identity_authorization',cat,times,frames,'AUTHORIZED',str(eid))
            edge(nid,lookup[o['observation_id']],'AUTHORIZED_OBSERVATION_REF',
                f'/metadata/observations/{i}/identity_authorization',reference_only=True)
    for i,r in enumerate(meta.get('scene_regions',[])):
        add('Region',r['region_id'],r,f'/metadata/scene_regions/{i}',times=[r['source_time_s']],
            frames=[r['source_frame_index']],status=r.get('grounding_status','CANDIDATE'),
            label=f"{r.get('region_label',r['region_id'])} · {r['source_time_s']:.3f}s")
    # Canonical location_observations also contains rejected/unknown relations.
    location_keys=['location_observations'] if meta.get('location_observations') else ['candidate_location_history','trusted_location_history']
    locations=[(f'/metadata/{key}/{i}',c) for key in location_keys for i,c in enumerate(meta.get(key,[]))]
    for pointer,c in locations:
        add('SpatialEvidence',c['observation_id'],c,pointer,c.get('object_category'),[c['source_time_s']],
            [c['source_frame_index']],c.get('grounding_status','UNKNOWN'),
            f"{c.get('spatial_relation','UNKNOWN')} · {c['source_time_s']:.3f}s")
    for i,e in enumerate(graph.get('events',[])):
        refs=e.get('before_refs',[])+e.get('after_refs',[])
        add('Event',e.get('hypothesis_id',str(i)),e,f'/events/{i}',e.get('object_category'),
            [r['source_time_s'] for r in refs if 'source_time_s' in r],
            [r['source_frame_index'] for r in refs if 'source_frame_index' in r],
            e.get('decision','UNKNOWN'),f"{e.get('type','EVENT')} · {e.get('decision','UNKNOWN')}")
    omitted=0
    for i,e in enumerate(meta.get('graph_edges',[])):
        a,b=lookup.get(e['source']),lookup.get(e['target'])
        if a and b:edge(a,b,e['predicate'],f'/metadata/graph_edges/{i}',e.get('grounding_status','REFERENCE'))
        else:omitted+=1  # Frame anchors shown as node timestamps, never fabricated nodes.
    for nid,n in list(nodes.items()):
        r=records[nid];ptr=n['source_pointer']
        if n['kind']=='SpatialEvidence':
            other=lookup.get(r.get('object_observation_id'))
            if other:edge(other,nid,'OBJECT_OBSERVATION_REF',ptr+'/object_observation_id',reference_only=True)
        if n['kind']=='Event':
            for field in ['supporting_observation_ids','conflicting_observation_ids']:
                for rid in r.get(field,[]):
                    if rid in lookup:edge(nid,lookup[rid],field.upper(),ptr+'/'+field,reference_only=True)
    return dict(session_id=session,nodes=list(nodes.values()),edges=edges,records=records,
        categories=sorted({n['category'] for n in nodes.values() if n['category']}),
        omitted_frame_or_unresolved_endpoint_edges=omitted,
        persisted_entities=graph.get('entities',[]),semantics='READ_ONLY_RECORD_PROJECTION; NO_CONTINUOUS_PRESENCE')


@lru_cache(maxsize=3)
def _cached_projection(path, digest, identifier):
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Graph changed during read')
    return project(json.loads(raw),identifier)


def load_projection(root,identifier):
    path,manifest,receipt=load_session(root,identifier)
    # load_session checks current manifest and Graph bytes on every UI run.
    result=copy.deepcopy(_cached_projection(str(path/'memory_graph.json'),receipt['graph_sha256'],identifier))
    result['graph_sha256']=receipt['graph_sha256']
    return result,manifest


def filter_graph(graph, *, category='phone', kinds=KINDS, time_range=None, statuses=(),
        predicates=(), limit=100, focus=(), focus_only=False):
    if not 1<=limit<=300:raise ValueError('Graph limit must be 1..300')
    allnodes={n['id']:n for n in graph['nodes']};focus=set(focus)
    eligible={nid for nid,n in allnodes.items() if n['kind'] in kinds
        and (not statuses or n['status'] in statuses)
        and (not time_range or any(time_range[0]<=t<=time_range[1] for t in n['times']))
        and (not category or n['category']==category)}
    # Include actual referenced regions for filtered object records; never invent spatial edges.
    regions={e['target'] for e in graph['edges'] if e['source'] in eligible
        and e['target'] in allnodes and allnodes[e['target']]['kind']=='Region'}
    for nid in regions:
        n=allnodes[nid]
        if n['kind'] in kinds and (not statuses or n['status'] in statuses) and (
                not time_range or any(time_range[0]<=t<=time_range[1] for t in n['times'])):eligible.add(nid)
    if focus_only and focus:
        neighborhood=set(focus)
        for e in graph['edges']:
            if e['source'] in focus or e['target'] in focus:neighborhood.update([e['source'],e['target']])
        eligible&=neighborhood
    # Prefer selected/search-relevant records, then spatial evidence and newest observed times.
    priority={'SpatialEvidence':0,'Region':1,'Observation':2,'Event':3,'Identity':4,'Candidate':5}
    chosen=sorted(eligible,key=lambda nid:(nid not in focus,priority[allnodes[nid]['kind']],
        -max(allnodes[nid]['times'],default=0),nid))[:limit]
    visible=set(chosen)
    return dict(nodes=[allnodes[n] for n in chosen],edges=[e for e in graph['edges'] if
        e['source'] in visible and e['target'] in visible and (not predicates or e['predicate'] in predicates)],
        total_nodes=len(allnodes),eligible_nodes=len(eligible),hidden_by_filter=len(allnodes)-len(eligible),
        hidden_by_limit=max(0,len(eligible)-len(chosen)))


def search_focus(graph,response):
    ids={r['observation_id'] for g in response.get('groups',[]) for r in g['records']}
    ids.update(r['object_observation_id'] for g in response.get('groups',[]) for r in g['records'])
    ids.update(r['region_id'] for g in response.get('groups',[]) for r in g['records'])
    mapped=[n['id'] for n in graph['nodes'] if n['record_id'] in ids]
    return dict(session_id=response['session_id'],category=response['intent']['category'],focus=mapped,
        search_status=response['result']['status'],mapping='EXACT_RECORD_IDS' if mapped else 'CATEGORY_FILTER_ONLY')


def evidence_groups(graph,nid):
    """Return exact frame groups consumable by Phase8 overlay(). No pixel reads."""
    n=next(n for n in graph['nodes'] if n['id']==nid);record=graph['records'][nid]
    records=graph['records'];observations={x['record_id']:records[x['id']] for x in graph['nodes'] if x['kind']=='Observation'}
    regions={x['record_id']:records[x['id']] for x in graph['nodes'] if x['kind']=='Region'}
    locs=[records[x['id']] for x in graph['nodes'] if x['kind']=='SpatialEvidence']
    if n['kind']=='SpatialEvidence':locs=[record]
    elif n['kind']=='Observation':locs=[c for c in locs if c['object_observation_id']==n['record_id']]
    elif n['kind']=='Region':locs=[c for c in locs if c['region_id']==n['record_id']]
    elif n['kind']=='Candidate':locs=[c for c in locs if c.get('object_candidate_id')==n['record_id']]
    else:locs=[]
    rows=[]
    for c in locs:
        o=observations.get(c['object_observation_id'],{});r=regions.get(c['region_id'],{})
        rows.append(dict(c,object_bbox=o.get('bbox'),object_mask=o.get('candidate_mask_ref'),
            region_polygon=r.get('polygon'),region_mask=r.get('mask_ref')))
    if not rows:
        for i,t in zip(n['frames'],n['times']):
            rows.append(dict(observation_id=n['record_id'],source_frame_index=i,source_time_s=t,
                object_bbox=record.get('bbox') if n['kind']=='Observation' else None,
                object_mask=record.get('candidate_mask_ref') if n['kind']=='Observation' else None,
                region_polygon=record.get('polygon') if n['kind']=='Region' else None,
                region_mask=record.get('mask_ref') if n['kind']=='Region' else None))
    groups={}
    for r in rows:
        key=(r['source_frame_index'],r['source_time_s'])
        groups.setdefault(key,dict(primary=r,records=[]))['records'].append(r)
    return sorted(groups.values(),key=lambda g:g['primary']['source_time_s'],reverse=True)
