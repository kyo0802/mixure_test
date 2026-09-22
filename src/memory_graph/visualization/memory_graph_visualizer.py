from .scene_graph_visualizer import render_semantic_graph


def render_memory(memory, path, config):
    analyzed = sum(e.get("analysis_status") == "success" for e in memory.events)
    status = f"VLM-valid events: {analyzed}. " + ("Semantic interpretations + separately marked geometry." if analyzed else
              "VLM not run/validated: UNKNOWN semantics; provisional 2D geometry only.")
    render_semantic_graph(memory.entities, memory.relations, path, memory.video+" | V2 temporal scene memory", config, status)
