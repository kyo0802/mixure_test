"""Small Streamlit views for the persistent checklist and departure Agent."""
import uuid
import streamlit as st
from .checklist_store import ChecklistStore
from .departure import evaluate

LABELS={'phone':'手機 / Phone','keys':'鑰匙 / Keys','wallet':'錢包 / Wallet','bottle':'瓶子 / Bottle','cup':'杯子 / Cup'}


def preferences(store):
    with st.expander('設定必帶物品 / Edit essentials'):
        st.caption('設定會用於下一次新檢查；本次與歷史檢查保留各自的清單快照。預設物品是清單範例，不表示已偵測到。')
        data=store.read()
        for item in data['items']:
            with st.form('edit_essential_'+item['item_id']):
                cols=st.columns([2,2,1]);name=cols[0].text_input('物品名稱',value=item['label'])
                category=cols[1].text_input('搜尋類別',value=item['category'],help='Graph 的物品類別，例如 phone、keys、wallet、umbrella。可設定其他類別，但不保證已有相關感知。')
                enabled=cols[2].checkbox('啟用',value=item['enabled'])
                left,right=st.columns(2)
                save=left.form_submit_button('儲存設定');remove=right.form_submit_button('移除此物品')
            if save or remove:
                try:
                    if remove:store.remove(item['item_id'])
                    else:store.update(item['item_id'],label=name,category=category,enabled=enabled)
                    st.rerun()
                except (ValueError,OSError,RuntimeError) as exc:st.error(str(exc))
        with st.form('add_essential'):
            name=st.text_input('新增物品名稱')
            category=st.selectbox('新增物品類別',[*LABELS,'其他'],format_func=lambda x:LABELS.get(x,x))
            other=st.text_input('其他類別（選其他時填寫）',placeholder='例如 umbrella')
            if st.form_submit_button('新增必帶物品'):
                try:
                    store.add(name,other if category=='其他' else category);st.rerun()
                except (ValueError,OSError,RuntimeError) as exc:st.error(str(exc))


def render_departure(root,memory_id,show_evidence):
    store=ChecklistStore(root)
    check=store.active(memory_id) or store.start(memory_id,purpose='DEMO_PRESENTATION')
    st.subheader("我要出門了 / I'm Leaving")
    st.caption('你啟動的離開提醒，不會自動偵測出門、監控攝影機或判定忘帶。')
    with st.form('new_departure_check'):
        demo=st.checkbox('展示檢查：操作紀錄不代表實際攜帶',value=True)
        fresh=st.form_submit_button('開始新檢查 / New Check')
    if fresh:
        store.start(memory_id,new=True,request_id=uuid.uuid4().hex,purpose='DEMO_PRESENTATION' if demo else 'USER_DEPARTURE')
        st.rerun()
    if check.get('purpose')=='DEMO_PRESENTATION':st.info('目前是展示用檢查。手動勾選只記錄展示操作，不作實際攜帶證明。')
    st.caption('檢查 '+check['check_id'][:10]+' · '+check['created']+' · 只屬於目前這份記憶')
    try:summary=evaluate(root,check,memory_id)
    except (ValueError,OSError,KeyError) as exc:st.error('記憶證據無法載入：'+str(exc));return
    if summary['complete']:st.success(summary['reminder'])
    elif summary['items']:st.warning(summary['reminder'])
    else:st.info(summary['reminder'])
    for row in summary['items']:
        item=row['item'];packed=row['packing_status']=='USER_CONFIRMED_PACKED'
        with st.container(border=True):
            left,right=st.columns([2,1])
            with left:
                st.markdown('### '+item['label'])
                if packed:st.success('手動確認：已帶妥 / User confirmed')
                else:st.warning('仍需確認 / Needs confirmation')
                st.write(row['message'])
                if row['last_observation_time'] is not None:st.caption(f"最後相關觀察：原片 {row['last_observation_time']:.2f} 秒；不代表目前持有。")
                if packed:st.caption('來源：'+row['manual_confirmation']['source']+' · '+row['manual_confirmation']['time'])
                else:st.caption('證據狀態：'+row['evidence_status'])
            with right:
                if packed:
                    if st.button('撤銷確認 / Undo',key='undo_'+check['check_id']+item['item_id']):
                        store.set_packed(check['check_id'],item['item_id'],False);st.rerun()
                else:
                    if st.button('我已帶妥 / Confirm packed',key='pack_'+check['check_id']+item['item_id'],type='primary'):
                        store.set_packed(check['check_id'],item['item_id'],True);st.rerun()
                    if st.button('尋找 '+item['label']+' / Find',key='find_'+check['check_id']+item['item_id']):
                        st.session_state['pending_search']=row['handoff'];st.rerun()
            if row['response']['groups']:
                with st.expander('查看歷史線索（不是打包證明）'):
                    st.write(row['response']['answer'])
                    show_evidence(memory_id,row['response']['groups'][0],'departure_'+check['check_id']+item['item_id'])
    preferences(store)
    data=store.read();past=[c for c in reversed(data['checks']) if c['memory_session_id']==memory_id and c['check_id']!=check['check_id']]
    with st.expander('檢視之前的檢查 / Previous checks'):
        if not past:st.caption('尚無之前的檢查。開始新檢查會保留目前紀錄。')
        for old in past[:10]:
            st.write(old['created']+' · '+old.get('purpose','USER_DEPARTURE')+' · '+old['status'])
            for item in old['items']:
                confirmed=old['confirmations'].get(item['item_id'],{}).get('packed',False)
                st.caption(item['label']+'：'+('當次手動確認' if confirmed else '當次未確認'))
        st.caption('之前的確認不會套用到本次新檢查。這裡只讀取歷史紀錄。')
