import argparse
from pathlib import Path
from memory_graph.scene_graph.models import TemporalMemory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect V2 semantic status, fixed IDs, evidence and temporal relations")
    parser.add_argument("graph")
    args = parser.parse_args()
    memory = TemporalMemory.model_validate_json(Path(args.graph).read_text(encoding="utf-8"))
    print(f"Video: {memory.video}\nEntities: {len(memory.entities)}\nUnknown: {sum(e.semantic_class=='unknown' for e in memory.entities)}"
          f"\nRelations: {len(memory.relations)}\nVLM-backed relations: {sum(r.evidence.vlm for r in memory.relations)}"
          f"\nEvents: {len(memory.events)}\nTransitions: {len(memory.transitions)}")
    for entity in memory.entities:
        print(f"ID:{entity.track_id} -> {entity.entity_id} | semantic={entity.semantic_class} | detector? {entity.detector_class}")
    for relation in memory.relations:
        print(f"  {relation.start_time:05.1f}-{relation.end_time:05.1f}s  ID:{relation.subject_track_id} {relation.predicate} "
              f"{('ID:'+str(relation.object_track_id)) if relation.object_track_id else ''} "
              f"[{'VLM' if relation.evidence.vlm else 'GEOMETRY ONLY'}; events={','.join(relation.event_ids)}]")
