import argparse
from collections import defaultdict
from memory_graph.memory.memory_store import load_graph


def timestamp(seconds):
    minutes, seconds = divmod(seconds, 60)
    return f"{int(minutes):02d}:{seconds:04.1f}"


def main():
    parser = argparse.ArgumentParser(description="Inspect saved temporal memory without running YOLO")
    parser.add_argument("graph")
    args = parser.parse_args()
    data = load_graph(args.graph)
    anchors = sum(n.node_type == "anchor" for n in data.nodes)
    print(f"Video: {data.video}\nEpisodes: {len(data.episodes)}\nTracked objects (including anchors): {len(data.nodes)}"
          f"\nAnchors: {anchors}\nStable relations: {len(data.relations)}\nTransitions: {len(data.transitions)}")
    print(f"Geometry: {data.geometry}")
    grouped = defaultdict(list)
    for relation in data.relations:
        grouped[relation.subject].append(relation)
    for subject, relations in sorted(grouped.items()):
        print(f"\nObject {subject}:")
        for relation in sorted(relations, key=lambda r: (r.start_time, r.object, r.predicate)):
            print(f"  {timestamp(relation.start_time)}-{timestamp(relation.end_time)}  {relation.predicate} {relation.object}"
                  f"  [{relation.episode_id}, {relation.reference_frame}, support={relation.support_count}, confidence={relation.confidence:.2f}]")
    for event in data.transitions:
        print(f"\nTransition {event.object_id}: {event.from_anchor} -> {event.to_anchor} at {timestamp(event.transition_time)}"
              f" (observed association, confidence={event.confidence:.2f})")


if __name__ == "__main__":
    main()
