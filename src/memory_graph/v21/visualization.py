import math
import networkx as nx
from ..visualization.graph_visualizer import plt


def render_graph(entities,relations,path,title):
    graph=nx.DiGraph()
    for e in entities: graph.add_node(e.entity_id,label=f'{e.entity_id}\n{e.semantic_class}\ntracks:{e.local_track_ids}')
    labels={}
    for r in relations:
        edge=(r['subject_entity_id'],r['object_entity_id'])
        graph.add_edge(*edge)
        labels.setdefault(edge,set()).add(r['predicate'])
    positions={}; groups=sorted(nx.weakly_connected_components(graph),key=len,reverse=True)
    columns=max(1,math.ceil(math.sqrt(len(groups))))
    for i,group in enumerate(groups):
        for n,xy in nx.circular_layout(graph.subgraph(group)).items(): positions[n]=(xy[0]+3*(i%columns),xy[1]-3*(i//columns))
    fig,ax=plt.subplots(figsize=(22,16)); ax.axis('off'); ax.set_title(title+'\nAll persistent hypotheses; identities and semantics remain uncertain',fontsize=14)
    if graph:
        nx.draw_networkx(graph,positions,labels=nx.get_node_attributes(graph,'label'),node_size=1000,font_size=5,
                         node_color='#b4d5ed',edge_color='#a9b4bc',ax=ax,arrowsize=8)
        if len(labels)<=24: nx.draw_networkx_edge_labels(graph,positions,edge_labels={k:'/'.join(sorted(v)) for k,v in labels.items()},font_size=5,ax=ax)
    fig.text(.02,.02,f'{len(entities)} entities, {len(relations)} relation observations. Dense edge details are in JSON. No 3D claims.',fontsize=10)
    fig.savefig(path,dpi=150); plt.close(fig)


def render_timeline(tracks,quality,mapping,path):
    fig,ax=plt.subplots(figsize=(18,max(8,len(tracks)*.18)))
    labels=[]
    for y,t in enumerate(tracks):
        color='#287eaf' if quality[t.track_id]['usable_for_identity'] else '#b8b8b8'
        ax.scatter([o.timestamp for o in t.observations],[y]*len(t.observations),s=5,color=color)
        labels.append(f"T{t.track_id} {mapping.get(t.track_id,'not usable')} {','.join(quality[t.track_id]['flags'])}")
    ax.set_yticks(range(len(tracks)),labels,fontsize=6); ax.set_xlabel('seconds'); ax.set_title('Local observations and persistent hypotheses — no fabricated gap boxes')
    fig.tight_layout(); fig.savefig(path,dpi=140); plt.close(fig)
