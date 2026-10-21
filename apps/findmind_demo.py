"""FindMind local competition demo. Recorded mode never invokes model workers."""
import os
from pathlib import Path
import sys
import uuid
import time

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'artifacts/pass_i/runtime/vendor')]
import streamlit as st
from findmind_demo.agent import ask,history,interpret,region_label,RELATIONS
from findmind_demo.sessions import discover_sessions,load_session,enrolled_entities
from findmind_demo.evidence import overlay,source_frame,source_video
from findmind_demo.jobs import store_upload,submit,list_jobs,poll,job_path
from findmind_demo.checklist_store import ChecklistStore
from findmind_demo.departure_ui import render_departure,preferences

st.set_page_config(page_title='FindMind · 找物記憶',page_icon='🧭',layout='wide')
st.markdown('''<style>
.block-container{max-width:1250px;padding-top:2rem;padding-bottom:3rem}
h1{letter-spacing:-.04em} [data-testid="stMetric"]{background:var(--secondary-background-color);border:1px solid #8aa19944;border-radius:12px;padding:14px}
.fm-eyebrow{color:#378979;font-size:.8rem;letter-spacing:.12em;font-weight:700}
.fm-subtitle{color:#66747c;max-width:780px;margin-bottom:1.5rem}
</style>''',unsafe_allow_html=True)

MODE_RECORDED='錄製結果 Demo';MODE_NEW='新影片分析'
VIEW_HOME='FindMind 首頁';VIEW_DEPARTURE='我要出門了';VIEW_SEARCH='尋找物品'
if st.session_state.get('pending_mode'):st.session_state['demo_mode']=st.session_state.pop('pending_mode')
if st.session_state.get('pending_view'):st.session_state['demo_view']=st.session_state.pop('pending_view')
if st.session_state.get('pending_open'):
    st.session_state['demo_mode']=MODE_RECORDED
    st.session_state['recorded_session']=st.session_state.pop('pending_open')
    st.session_state.pop('response',None)
    st.session_state['demo_view']=VIEW_HOME
if st.session_state.get('pending_search'):
    handoff=st.session_state.pop('pending_search')
    st.session_state['demo_mode']=MODE_RECORDED;st.session_state['demo_view']=VIEW_SEARCH
    st.session_state['recorded_session']=handoff['session_id']
    st.session_state['search_query_'+handoff['session_id']]=handoff['question']
    st.session_state['handoff_context']=handoff
    st.session_state.pop('response',None);st.session_state.pop('query_error',None)


def show_evidence(identifier,group,key):
    try:
        data=overlay(ROOT,identifier,group)
        st.image(data['png'],caption=f"原片 f{data['frame']['source_frame_index']} · native PTS {data['frame']['source_time_s']:.6f} 秒",width='stretch')
        st.caption('綠色：物體定位　黃色：候選區域；遮罩與投影不代表物理接觸。')
        with st.expander('查看原始影格與引用'):
            st.image(data['original'],width='stretch')
            st.code(data['reference'],language=None)
            st.download_button('下載原始證據影格',data['original'],file_name=f"frame_{data['frame']['source_frame_index']}.png",mime='image/png',key=key+'_download')
            st.json(dict(source_frame=data['frame'],evidence_records=[dict(observation_id=c['observation_id'],object_refs=c.get('object_evidence_refs'),region_refs=c.get('region_evidence_refs')) for c in group['records']]))
    except (ValueError,OSError,KeyError) as exc:st.error('證據無法顯示：'+str(exc))


def results(identifier,response):
    result=response['result'];status=result['status'];zh=response['intent']['language']=='zh'
    if status=='LAST_CONFIRMED_LOCATION':st.success('可信歷史位置 · LAST_CONFIRMED_LOCATION')
    elif status=='POSSIBLE_LOCATIONS':st.info('可能位置 · POSSIBLE_LOCATIONS')
    else:st.warning('位置未能確認 · UNKNOWN')
    st.write(response['answer'])
    st.caption(f"查詢耗時 {response['elapsed_s']*1000:.0f} ms · 從已保存 Graph 取證 · 本次搜尋沒有模型推論")
    if result.get('incomplete_stages'):st.warning('這份記憶有未完成階段；目前顯示可安全讀取的部分證據。')
    for n,group in enumerate(response['groups'][:6]):
        c=group['primary'];verified=c['grounding_status']=='VERIFIED'
        with st.container(border=True):
            st.markdown(f"### {'可信歷史位置' if verified else '候選'} {n+1} · {region_label(c.get('location_label',''),response['intent']['language'])}")
            left,right=st.columns([1,1.6])
            with left:
                st.write(f"**{c['source_time_s']:.2f} 秒 · f{c['source_frame_index']}**")
                st.write(RELATIONS.get(c['spatial_relation'],c['spatial_relation']))
                st.write('身分：'+('已授權實例' if c.get('persistent_entity_id') else '類別候選，尚非你的特定物品'))
                st.caption(f"{len(group['records'])} 筆同格／同區域證據；不是物體數量。沿用 Graph 證據排序。")
                if group['ambiguous_tie']:st.caption('與其他候選無法依現有證據可靠區分。')
                if not verified:st.write('**候選原因：** 同一影格有物體定位與區域幾何關係。接觸、身分與目前位置尚未確認。')
                else:st.write('依 Graph 的身分及獨立驗證證據；只描述當時位置。')
                with st.expander('完整不確定性與依據'):
                    for note in c.get('uncertainty',[]):st.write('• '+note)
                    st.json(dict(grounding_status=c['grounding_status'],reasons=c.get('reason_codes'),rank=c.get('rank'),identity_scope=c.get('identity_scope')))
            with right:show_evidence(identifier,group,f'{identifier}_{n}')
    if len(response['groups'])>6:st.caption(f"先顯示 6 組，共 {len(response['groups'])} 組；完整紀錄見技術詳情。")
    if status=='UNKNOWN':
        obs=response['last_observation']
        if obs and obs.get('source_frame_indices'):
            st.markdown('### 最後可用的物體觀察')
            idx=obs['source_frame_indices'][-1]
            try:
                f,path=source_frame(ROOT,identifier,idx)
                st.write(f"{f['source_time_s']:.2f} 秒 · f{idx} · {obs['object_description']}，尚不足以建立可信區域。")
                st.image(path.read_bytes(),width='stretch')
            except (ValueError,OSError,KeyError) as exc:st.caption('最後觀察沒有可顯示的同格證據：'+str(exc))
        else:st.write('沒有足夠的相關物體觀察。可嘗試另一個已有感知的物品類別。')


@st.fragment(run_every=2)
def job_status(job_id):
    state=poll(ROOT,job_id)
    st.subheader('背景處理狀態')
    st.write('工作：'+job_id[:12]+' · '+state['status'])
    labels={'registration':'影片登錄','extraction':'影格與原生 PTS','cv':'偵測與追蹤','nemotron':'Nemotron 時序推論',
        'localization':'目標／表面定位與 SAM','memory':'建立空間記憶','ready':'可開始搜尋'}
    st.dataframe([dict(階段=labels[k],狀態=v) for k,v in state['stages'].items()],hide_index=True,width='stretch')
    if state.get('error'):st.error(state['error'])
    if state.get('session_id') and state['stages']['ready']=='COMPLETED':
        if state['status']=='PARTIAL':st.warning('部分階段失敗，已保留可查詢的記憶。')
        if st.button('開啟這份記憶並搜尋',key='open_'+job_id):
            st.session_state['pending_open']=state['session_id'];st.rerun()
    with st.expander('執行日誌'):
        log=job_path(ROOT,job_id)/'pipeline.log'
        if log.exists():st.code(log.read_text(encoding='utf8',errors='replace')[-6000:],language=None)
        else:st.caption('等待背景程序啟動。')


st.markdown('<div class="fm-eyebrow">FINDMIND / PERSONAL BELONGINGS MEMORY</div>',unsafe_allow_html=True)
st.title('物品的線索，留在記憶裡。')
st.markdown('<div class="fm-subtitle">找回歷史線索，出門前逐項確認。搜尋依據影片記憶；是否帶妥由你手動確認。</div>',unsafe_allow_html=True)
rows=discover_sessions(ROOT);available={r['id']:r for r in rows if r['queryable']}
with st.sidebar:
    st.markdown('## 🧭 FindMind')
    mode=st.radio('使用方式',[MODE_RECORDED,MODE_NEW],key='demo_mode')
    if mode==MODE_RECORDED:view=st.radio('FindMind 導覽',[VIEW_HOME,VIEW_DEPARTURE,VIEW_SEARCH],key='demo_view')
    st.caption('錄製結果可離線立即互動。新影片需要實際 GPU 處理。')
    if st.button('重新整理記憶清單'):st.rerun()
    st.divider()
    st.caption('本機競賽原型 · 目前無可信位置實跑案例。類別相似不代表同一件物品。')

if st.session_state.get('previous_mode')!=mode:
    st.session_state.pop('response',None);st.session_state.pop('query_error',None)
    st.session_state['previous_mode']=mode

if mode==MODE_NEW:
    st.subheader('加入一段新影片')
    st.write('提交後會啟動實際 Phase 7 流程。先前 36.77 秒影片約需 12 分鐘；你可以重新整理頁面，工作紀錄仍會保留。')
    limit=int(os.environ.get('FINDMIND_UPLOAD_MAX_MB','200'))
    with st.form('new_video_form'):
        upload=st.file_uploader(f'MP4 影片（上限 {limit} MB）',type=['mp4'])
        question=st.text_input('希望查找什麼？',value='我的手機在哪裡？')
        approved=st.checkbox('開始實際影片分析（會使用本機 GPU）')
        start=st.form_submit_button('開始分析',type='primary')
    if start:
        try:
            if upload is None:raise ValueError('請先選擇 MP4 影片。')
            if not approved:raise ValueError('請勾選開始實際影片分析。')
            intent=interpret(question)
            path,digest=store_upload(ROOT,upload.name,upload.getvalue(),limit)
            request_key=(digest,intent['category'])
            if st.session_state.get('submission_key')!=request_key:
                st.session_state['submission_token']=uuid.uuid4().hex;st.session_state['submission_key']=request_key
            job=submit(ROOT,path,intent['category'],st.session_state['submission_token'])
            st.session_state['active_job']=job;st.success('已提交。工作由磁碟紀錄管理，重新整理不會重複啟動。')
        except (OSError,ValueError,RuntimeError) as exc:st.error(str(exc))
    jobs=list_jobs(ROOT)
    if jobs:
        ids=[j['job_id'] for j in jobs]
        active=st.session_state.get('active_job',ids[0]);active=active if active in ids else ids[0]
        selected=st.selectbox('最近的背景工作',ids,index=ids.index(active),format_func=lambda x:x[:12]+' · '+next(j['status'] for j in jobs if j['job_id']==x))
        job_status(selected)
    st.stop()

if not available:
    st.info('目前還沒有完成的記憶。請切換「新影片分析」上傳影片，或等待背景工作完成。');st.stop()
if st.session_state.get('recorded_session') not in available:st.session_state['recorded_session']=next(iter(available))
identifier=st.selectbox('選擇已錄製的記憶',list(available),key='recorded_session',
    format_func=lambda x:available[x]['label']+' · '+(available[x]['created'] or '日期未知')[:19]+' · '+available[x]['status'])
summary=available[identifier]
try:path,manifest,receipt=load_session(ROOT,identifier)
except (ValueError,OSError,KeyError) as exc:st.error('記憶無法安全載入：'+str(exc));st.stop()
if st.session_state.get('response_session')!=identifier:
    st.session_state.pop('response',None);st.session_state['response_session']=identifier
    if st.session_state.get('handoff_context',{}).get('session_id')!=identifier:st.session_state.pop('handoff_context',None)
st.caption('錄製結果 Demo：此頁只搜尋既有記憶，不會重新啟動模型。')
a,b,c=st.columns(3)
a.metric('來源影片',summary['label']);b.metric('處理結果',summary['status']);c.metric('證據影格','可用' if summary['evidence'] else '缺少')
if view==VIEW_HOME:
    st.subheader('今天讓 FindMind 幫你做什麼？')
    first,second,third=st.columns(3)
    if first.button('尋找物品 / Find an Item',type='primary'):
        st.session_state['pending_view']=VIEW_SEARCH;st.rerun()
    if second.button("我要出門了 / I'm Leaving"):
        st.session_state['pending_view']=VIEW_DEPARTURE;st.rerun()
    if third.button('分析新影片 / Analyze New Video'):
        st.session_state['pending_mode']=MODE_NEW;st.rerun()
    st.write('找物時查看同格框、區域與時間；出門提醒會保留你的清單及每次手動確認。')
    st.caption('離開提醒由你點擊啟動；影片中的物體、手持動作或漏偵測都不會自動判定已帶妥或忘帶。')
    try:preferences(ChecklistStore(ROOT))
    except (OSError,ValueError,RuntimeError) as exc:st.error('清單無法讀取：'+str(exc))
    st.stop()
if view==VIEW_DEPARTURE:
    try:render_departure(ROOT,identifier,show_evidence)
    except (OSError,ValueError,RuntimeError) as exc:st.error('離開檢查無法儲存：'+str(exc))
    st.stop()
if st.button('返回出門檢查 / Back to checklist'):
    st.session_state['pending_view']=VIEW_DEPARTURE;st.rerun()
handoff=st.session_state.get('handoff_context')
if handoff and handoff['session_id']==identifier:st.caption('來自本次離開檢查的找物請求；搜尋結果不會自動改成已帶妥。')
entities=enrolled_entities(ROOT,identifier)
ask_tab,history_tab,about_tab=st.tabs(['詢問 FindMind','空間記憶時間線','影片與記憶資訊'])
with ask_tab:
    st.subheader('你想找什麼？')
    query_key='search_query_'+identifier
    if query_key not in st.session_state:st.session_state[query_key]='我的手機在哪裡？'
    with st.form('ask_'+identifier):
        question=st.text_input('找物問題',key=query_key,placeholder='Where did you last see my phone?')
        entity=st.selectbox('查詢範圍',['類別候選',*entities]) if entities else None
        clicked=st.form_submit_button('查找線索',type='primary')
    st.caption('例如：幫我找手機。／Where did you last see my phone?／手機最後出現在哪裡？　鑰匙與錢包的感知效果尚未驗證。')
    if clicked or 'response' not in st.session_state:
        try:
            hint=handoff['category'] if handoff and handoff['session_id']==identifier and handoff['question']==question else None
            if hint is None:st.session_state['response']=ask(ROOT,identifier,question,entities,None if entity=='類別候選' else entity)
            else:st.session_state['response']=ask(ROOT,identifier,question,category_hint=hint)
            st.session_state.pop('query_error',None)
        except (ValueError,OSError,KeyError,StopIteration) as exc:
            st.session_state['response']=None;st.session_state['query_error']=str(exc)
    if st.session_state.get('query_error'):st.warning(st.session_state['query_error'])
    response=st.session_state.get('response')
    if response:results(identifier,response)
with history_tab:
    response=st.session_state.get('response')
    if response:
        entries=history(ROOT,identifier,response)
        if entries:st.dataframe([dict(時間=f"{r['time']:.2f} s",內容=r['kind'],線索=r['detail'],狀態=r['status'],影格=r['frame']) for r in entries],hide_index=True,width='stretch')
        else:st.info('這個物品尚無可顯示的記憶線索。')
        st.caption('依原生時間整理的摘要。事件假說可能不確定或被拒絕，不代表實際發生；時間較新也不表示是你的同一件物品。')
    else:st.info('請先輸入一個支援的找物問題。')
with about_tab:
    st.write('記憶 ID：'+identifier)
    st.write('這份 session 使用原生來源 PTS，保存歷史採樣影格；不保證完整涵蓋所有動作。')
    with st.expander('播放原片（可選）'):
        if st.button('載入這份記憶的原片'):
            try:st.video(source_video(ROOT,identifier).read_bytes())
            except (ValueError,OSError,KeyError) as exc:st.warning(str(exc))
    with st.expander('技術詳情與執行品質'):
        st.json(dict(session=identifier,stages=receipt['stages'],elapsed_s=receipt['elapsed_s'],source_sha256=manifest['video']['source_sha256'],
            validation=st.session_state.get('response',{}).get('result',{}).get('temporal_model_outputs') if st.session_state.get('response') else None))
        if st.session_state.get('response'):st.json(st.session_state['response']['result'])
