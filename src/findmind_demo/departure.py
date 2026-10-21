"""User-triggered departure assistant. Visual evidence never confirms packing."""
from .agent import ask,region_label
from .sessions import load_session


def search_handoff(check,item):
    return dict(session_id=check['memory_session_id'],check_id=check['check_id'],item_id=item['item_id'],
        question=f"{item['label']}在哪裡？",category=item['category'])


def evaluate(root,check,memory_id):
    if check['memory_session_id']!=memory_id:raise ValueError('Departure check belongs to another memory session')
    load_session(root,memory_id)
    rows=[];by_category={}
    for item in check['items']:
        category=item['category']
        if category not in by_category:
            by_category[category]=ask(root,memory_id,f"{item['label']}在哪裡？",category_hint=category)
        response=by_category[category];result=response['result'];last=response['last_observation']
        confirmation=check['confirmations'].get(item['item_id'],{})
        packed=bool(confirmation.get('packed'))
        availability='HAS_LOCATION_CANDIDATE' if response['groups'] else 'OBSERVATION_ONLY' if last else 'NO_RELEVANT_OBSERVATION'
        label='USER_CONFIRMED_PACKED' if packed else 'HAS_LOCATION_CANDIDATE' if response['groups'] else 'NO_RELEVANT_OBSERVATION' if not last else 'NEEDS_CONFIRMATION'
        message='你已在本次檢查手動確認帶妥。' if packed else '尚未確認帶妥。'
        if response['groups']:
            c=response['groups'][0]['primary']
            message+=f" 記憶中 {c['source_time_s']:.1f} 秒有{region_label(c.get('location_label',''))}相關的歷史線索；不代表你現在帶著它。"
            if not c.get('persistent_entity_id'):message+=' 這是類別線索，尚未確認為你的同一件物品。'
        elif last:message+=' 有相關物體觀察，但沒有足夠的位置證據。'
        else:message+=' 目前沒有相關的可用觀察；這不表示你遺忘或沒有攜帶。'
        rows.append(dict(item=item,status=label,packing_status='USER_CONFIRMED_PACKED' if packed else 'NEEDS_CONFIRMATION',
            evidence_status=availability,manual_confirmation=confirmation if packed else None,
            possession_verified=False,response=response,message=message,handoff=search_handoff(check,item),
            last_observation_time=max(last['source_times_s']) if last and last.get('source_times_s') else None))
    pending=sum(r['packing_status']!='USER_CONFIRMED_PACKED' for r in rows)
    if not rows:reminder='這次沒有啟用的必帶物品。請先設定清單，再開始新檢查。'
    elif pending:reminder=f'還有 {pending} 件必帶物品需要你確認。歷史影像只能提供找物線索，不能確認已隨身帶妥。'
    else:reminder='你已在本次檢查手動確認所有必帶物品。祝你出門順利！'
    return dict(check_id=check['check_id'],memory_session_id=memory_id,items=rows,pending=pending,
        complete=bool(rows) and pending==0,reminder=reminder)
