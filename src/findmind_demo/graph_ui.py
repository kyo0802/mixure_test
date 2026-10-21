"""Streamlit UI for a bounded, CPU-only record projection and existing evidence."""
import hashlib
import json
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from .graph_adapter import load_projection,filter_graph,search_focus,evidence_groups,KINDS

_component=components.declare_component('findmind_memory_graph',path=str(Path(__file__).with_name('graph_component')))


def request_graph(root,identifier,response):
    graph,_=load_projection(root,identifier)
    return search_focus(graph,response)


def reset_selection(state,identity):
    """Called before widgets are instantiated; prevent cross-session evidence."""
    if state.get('gv_identity')!=identity or state.pop('gv_reset_pending',False):
        for key in list(state):
            if key.startswith('gv_'):del state[key]
        state['gv_identity']=identity


def render_graph(root,identifier,show_evidence):
    graph,manifest=load_projection(root,identifier)
    identity=identifier+':'+graph['graph_sha256'];reset_selection(st.session_state,identity)
    handoff=st.session_state.pop('pending_graph',None)
    if handoff and handoff['session_id']==identifier:
        st.session_state['gv_category']=handoff['category'];st.session_state['gv_handoff']=handoff
        for key in ['gv_selection','gv_time','gv_status','gv_relations','gv_kinds']:st.session_state.pop(key,None)
    st.subheader('Memory Graph / 記憶圖譜')
    st.write('從這份記憶的原始紀錄建立唯讀視圖。節點數不是實體數量；候選關係不代表接觸、同一物體或目前位置。')
    if st.button('返回尋找物品 / Back to Find Item'):
        st.session_state['pending_view']='尋找物品';st.rerun()
    categories=['',*graph['categories']]
    requested=st.session_state.get('gv_category')
    if requested and requested not in categories:categories.append(requested)
    if st.session_state.get('gv_category') not in categories:st.session_state['gv_category']='phone' if 'phone' in categories else ''
    top=st.columns([1,1.5,1])
    category=top[0].selectbox('物品類別 / Category',categories,key='gv_category',format_func=lambda c:c or '全部 / Overview')
    kinds=top[1].multiselect('節點類型 / Node types',KINDS,default=list(KINDS),key='gv_kinds')
    limit=top[2].number_input('節點上限 / Node limit',min_value=10,max_value=300,value=100,step=10,key='gv_limit')
    times=[t for n in graph['nodes'] for t in n['times']];lo=min(times,default=0.);hi=max(times,default=0.)
    time_range=st.slider('原生時間範圍 / Native PTS (s)',float(lo),float(hi),(float(lo),float(hi)),key='gv_time') if hi>lo else None
    with st.expander('關係與證據狀態 / Relation and status filters'):
        statuses=st.multiselect('證據狀態 / Status',sorted({n['status'] for n in graph['nodes']}),key='gv_status')
        predicates=st.multiselect('連線關係 / Relationships',sorted({e['predicate'] for e in graph['edges']}),key='gv_relations')
        st.caption('留空代表不限。狀態篩選不會改寫原始候選或事件決策。OBJECT_OBSERVATION_REF 等虛線僅是原始欄位引用。')
    handoff=st.session_state.get('gv_handoff',{})
    active_focus=handoff.get('focus',[]) if handoff.get('category')==category else []
    if handoff:
        st.info('搜尋 → 圖譜：'+handoff['mapping']+' · 來源類別 '+str(handoff['category'])+' · 搜尋狀態 '+handoff['search_status'])
        if handoff['mapping']=='CATEGORY_FILTER_ONLY':st.caption('沒有可解出的精確搜尋紀錄，只套用類別篩選；沒有建立假想物件。')
    focused=st.checkbox('只看搜尋證據與直接連結 / Search evidence neighborhood',value=bool(active_focus),key='gv_focus_only') if active_focus else False
    sub=filter_graph(graph,category=category,kinds=kinds,time_range=time_range,statuses=statuses,
        predicates=predicates,limit=int(limit),focus=active_focus,focus_only=focused)
    st.caption(f"顯示 {len(sub['nodes'])} / {sub['total_nodes']} 節點；篩選隱藏 {sub['hidden_by_filter']}，上限隱藏 {sub['hidden_by_limit']}。框架時間錨點以 PTS 顯示，不另造大量時間節點。")
    if st.button('重設圖譜篩選與選取 / Reset Graph'):
        st.session_state['gv_reset_pending']=True;st.rerun()
    if not sub['nodes']:
        st.info('目前篩選沒有原始紀錄。沒有偵測不代表物品不存在；此處不會生成替代節點。');return
    ids=[n['id'] for n in sub['nodes']];byid={n['id']:n for n in sub['nodes']}
    if st.session_state.get('gv_selection') not in ids:
        st.session_state['gv_selection']=next((n for n in ids if n in handoff.get('focus',[]) and byid[n]['kind']=='SpatialEvidence'),ids[0])
    view_token=hashlib.sha256(json.dumps([identity,ids,[e['id'] for e in sub['edges']]]).encode()).hexdigest()
    payload=dict(nodes=sub['nodes'],edges=sub['edges'],focus=active_focus)
    clicked=_component(graph=payload,selected=st.session_state['gv_selection'],view_token=view_token,key='gv_canvas_'+view_token,default=None)
    if clicked and clicked.get('view_token')==view_token:
        nonce=clicked.get('nonce')
        if nonce!=st.session_state.get('gv_click_seen'):
            st.session_state['gv_click_seen']=nonce
            if clicked.get('node_id') in ids:
                st.session_state['gv_selection']=clicked['node_id'];st.session_state.pop('gv_edge',None)
            elif clicked.get('edge_id') in {e['id'] for e in sub['edges']}:
                st.session_state['gv_edge']=clicked['edge_id']
                st.session_state['gv_selection']=next(e['source'] for e in sub['edges'] if e['id']==clicked['edge_id'])
            st.rerun()
    selected=st.selectbox('選取節點 / Selected node',ids,key='gv_selection',format_func=lambda n:byid[n]['kind']+' · '+byid[n]['label'])
    n=byid[selected];record=graph['records'][selected]
    st.markdown('### '+n['kind']+' · '+n['status'])
    st.code(n['record_id'],language=None);st.caption('來源 JSON pointer：'+n['source_pointer'])
    if n['kind']=='Candidate':st.warning('本機候選引用；不是已授權個人物品。多個時點不證明持續存在或同一實體。')
    if n['kind']=='Event':st.warning('事件假說決策：'+n['status']+'。BEFORE/AFTER 範圍是證據界限，不是事件持續時間。')
    if n['times']:st.write('實際觀察 PTS：'+', '.join(f'{t:.6f}s' for t in n['times'][:16])+(' …' if len(n['times'])>16 else ''))
    adjacent=[e for e in sub['edges'] if selected in [e['source'],e['target']]]
    if adjacent:
        edge_ids=[e['id'] for e in adjacent];byedge={e['id']:e for e in adjacent}
        if st.session_state.get('gv_edge') not in edge_ids:st.session_state['gv_edge']=edge_ids[0]
        eid=st.selectbox('相關連線 / Related relationship',edge_ids,key='gv_edge',format_func=lambda x:byedge[x]['predicate']+' · '+byedge[x]['status'])
        st.json(byedge[eid]);st.caption('只顯示原始紀錄／欄位連結。2D 幾何或模型說法不是獨立物理驗證。')
    elif st.session_state.get('gv_edge'):
        e=next((e for e in sub['edges'] if e['id']==st.session_state['gv_edge']),None)
        if e:st.json(e)
    groups=evidence_groups(graph,selected)
    if groups:
        ix=st.selectbox('同格證據 / Evidence frame',range(len(groups)),format_func=lambda i:f"{groups[i]['primary']['source_time_s']:.6f}s · f{groups[i]['primary']['source_frame_index']}",key='gv_evidence_'+selected)
        show_evidence(identifier,groups[ix],'graph_'+selected)
    else:st.info('此節點沒有可顯示的來源影格；不以相似畫面替代。')
    with st.expander('來源紀錄與不確定性 / Source record'):
        st.json({k:v for k,v in record.items() if k!='pixel_mask_rle'})
    st.caption('圖譜解析與顯示使用 CPU；沒有模型推論。每次先檢查 session hashes，切換 session 或 Graph 版本會清除選取。')
