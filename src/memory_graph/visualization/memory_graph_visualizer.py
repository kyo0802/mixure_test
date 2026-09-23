from .scene_graph_visualizer import render_semantic_graph


def render_memory(memory, path, config):
    analyzed = sum(e.get("analysis_status") in {"success","partial"} for e in memory.events)
    partial = sum(e.get("analysis_status") == "partial" for e in memory.events)
    status = f"VLM schema-valid events: {analyzed} ({partial} partial). " + ("Model interpretations, not ground truth; geometry marked separately." if analyzed else
              "VLM not run/validated: UNKNOWN semantics; provisional 2D geometry only.")
    render_semantic_graph(memory.entities, memory.relations, path, memory.video+" | V2 temporal scene memory", config, status)
