from collections import defaultdict
import networkx as nx
from ..config import TransitionsConfig
from ..models import (AnchorInfo, Episode, MemoryEdge, MemoryGraphData, MemoryNode, ObjectTrack,
                      RelationTransition, StableRelation)


def derive_transitions(relations: list[StableRelation], config: TransitionsConfig) -> list[RelationTransition]:
    """Only report disjoint, unambiguous stable anchor association changes."""
    subjects = defaultdict(list)
    for relation in relations:
        if relation.predicate in config.predicates:
            subjects[relation.subject_id].append(relation)
    events = []
    for subject, intervals in subjects.items():
        # Merge overlapping intervals for the same anchor; different predicates are not movements.
        by_anchor = defaultdict(list)
        for interval in intervals:
            by_anchor[interval.object_id].append(interval)
        associations = []
        for anchor, values in by_anchor.items():
            group = []
            end = -1

            def append_group(items):
                representative = min(items, key=lambda r: (config.predicates.index(r.predicate), -r.confidence))
                associations.append((min(r.start_time for r in items), max(r.end_time for r in items), anchor, representative))

            for relation in sorted(values, key=lambda r: r.start_time):
                if group and relation.start_time > end:
                    append_group(group)
                    group = []
                group.append(relation)
                end = max(r.end_time for r in group)
            if group:
                append_group(group)
        associations.sort(key=lambda x: (x[0], x[1], x[2]))
        previous = None
        for current in associations:
            ambiguous = any(other[2] != current[2] and other[0] <= current[1] and current[0] <= other[1]
                            for other in associations)
            if ambiguous:
                previous = None
                continue
            if previous is not None and previous[2] != current[2] and 0 < current[0]-previous[1] <= config.max_gap_seconds:
                old, new = previous[3], current[3]
                events.append(RelationTransition(object_id=subject, from_anchor=previous[2], to_anchor=current[2],
                    from_relation=old.predicate, to_relation=new.predicate, transition_time=current[0],
                    previous_end_time=previous[1], confidence=min(old.confidence, new.confidence),
                    from_episode=old.episode_id, to_episode=new.episode_id))
            previous = current
    return sorted(events, key=lambda e: (e.transition_time, e.object_id))


def build_graph(video: str, metadata: dict, episodes: list[Episode], tracks: list[ObjectTrack],
                anchors: list[AnchorInfo], relations: list[StableRelation],
                transitions: list[RelationTransition]) -> MemoryGraphData:
    anchor_map = {a.object_id: a for a in anchors if a.is_anchor}
    nodes = [MemoryNode(id=t.object_id, class_name=t.class_name,
        node_type="anchor" if t.object_id in anchor_map else "object", first_seen=t.first_seen,
        last_seen=t.last_seen, observation_count=len(t.observations),
        anchor_score=anchor_map[t.object_id].anchor_score if t.object_id in anchor_map else None) for t in tracks]
    edges = [MemoryEdge(subject=r.subject_id, object=r.object_id,
                        **r.model_dump(exclude={"subject_id", "object_id"})) for r in relations]
    return MemoryGraphData(video=video, metadata=metadata, episodes=episodes, nodes=nodes,
                           relations=edges, transitions=transitions)


def to_networkx(data: MemoryGraphData) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph(video=data.video, schema_version=data.schema_version)
    for node in data.nodes:
        graph.add_node(node.id, **node.model_dump(exclude={"id"}))
    for i, edge in enumerate(data.relations):
        graph.add_edge(edge.subject, edge.object, key=f"relation_{i:06d}",
                       **edge.model_dump(exclude={"subject", "object"}))
    return graph
