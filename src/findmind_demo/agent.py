"""Deterministic request interpretation and evidence-grounded answer templates."""
import re
import time
from .sessions import load_session,read
from memory_graph.integration.fresh_video import search_session,query_category

ALIASES={'phone':['手機','電話','smartphone','cell phone','mobile phone','phone'],
    'bottle':['水瓶','瓶子','bottle'], 'cup':['杯子','水杯','cup','mug'],
    'keys':['鑰匙','keys','key'],'wallet':['錢包','wallet']}
ZH={'phone':'手機','bottle':'瓶子','cup':'杯子','keys':'鑰匙','wallet':'錢包'}
REGIONS={'tabletop':'桌面','desk_surface':'書桌表面','microwave_top':'微波爐頂面','table':'桌子區域',
    'microwave':'微波爐區域','shelf_top':'層架頂面','other_visible_surface':'可見表面'}
RELATIONS={'NEAR_REGION':'影像中靠近該區域','POSSIBLY_ON_SURFACE':'可能位於表面，接觸未確認',
    'INSIDE_REGION':'影像投影位於區域內','OVERLAPS_REGION':'影像投影與區域重疊'}


def interpret(text, entities=(), explicit_entity=None):
    text=text.strip()
    if not text or len(text)>300:raise ValueError('請輸入簡短的找物問題。')
    language='zh' if re.search(r'[\u3400-\u9fff]',text) else 'en'
    if explicit_entity:
        if explicit_entity not in entities:raise ValueError('這個物品身分尚未註冊或授權。')
        return dict(category=None,entity_id=explicit_entity,language=language)
    if text in entities:return dict(category=None,entity_id=text,language=language)
    found=set()
    for category,aliases in ALIASES.items():
        for alias in aliases:
            pattern=re.escape(alias) if re.search(r'[\u3400-\u9fff]',alias) else r'(?<!\w)'+re.escape(alias)+r'(?!\w)'
            if re.search(pattern,text,re.I):found.add(category)
    if len(found)>1:raise ValueError('請一次查詢一種物品，例如「幫我找手機」。')
    if not found:raise ValueError('目前可理解手機、瓶子、杯子、鑰匙或錢包的找物問題。已有證據才會回傳位置；鑰匙與錢包的感知效果尚未驗證。')
    return dict(category=found.pop(),entity_id=None,language=language)


def region_label(value,language='zh'):
    raw=value.replace(' candidate','').strip()
    return REGIONS.get(raw,raw) if language=='zh' else raw.replace('_',' ')


def group_candidates(candidates):
    # Display grouping only. Keep Graph ordering and every underlying record.
    # A time/region group is not a claim about the number or identity of objects.
    groups=[];by_key={}
    for c in candidates:
        k=(c['source_frame_index'],c['region_id'],c.get('persistent_entity_id'),c['grounding_status'])
        if k not in by_key:
            group=dict(primary=c,records=[],ambiguous_tie=bool(c.get('ordering_unresolved_tie')))
            groups.append(group);by_key[k]=group
        by_key[k]['records'].append(c)
    return groups


def describe(result,intent,groups):
    zh=intent['language']=='zh';name=ZH.get(intent['category'],intent['category']) if zh else intent['category']
    status=result['status']
    if status=='UNKNOWN':
        answer=f'目前無法從這段記憶確定{name}的位置。' if zh else f'I cannot establish a location for the {name} from this memory.'
        return answer+(' 可以查看最後可用的觀察；缺少偵測不表示物品不存在。' if zh else ' You can inspect the last available observation. A missed detection does not establish absence.')
    first=groups[0]['primary'];label=region_label(first.get('location_label','unresolved region'),intent['language']);t=first['source_time_s']
    if status=='LAST_CONFIRMED_LOCATION':
        answer=f'最後一筆可信位置是 {t:.1f} 秒的{label}。' if zh else f'The last verified location was {label} at {t:.1f} seconds.'
    else:
        answer=f'在 {t:.1f} 秒找到{name}與{label}相關的候選觀察，共有 {len(groups)} 組時間／區域證據。' if zh else f'I found a possible {name} observation associated with {label} at {t:.1f} seconds, with {len(groups)} time/region evidence groups.'
    if not intent['entity_id']:
        answer+=(' 這是類別候選，還不能確認是你的特定物品。' if zh else ' These are category candidates; they are not confirmed as your particular item.')
    answer+=(' 歷史畫面無法保證它現在仍在原處。' if zh else ' Historical observations do not establish that it is still there.')
    return answer


def ask(root,identifier,text,entities=(),explicit_entity=None,*,category_hint=None):
    start=time.perf_counter()
    if category_hint is not None:
        if not isinstance(category_hint,str) or not 1<=len(category_hint)<=80 or any(ord(c)<32 for c in category_hint):raise ValueError('Invalid explicit object category')
        intent=dict(category=query_category(category_hint),entity_id=None,language='zh' if re.search(r'[\u3400-\u9fff]',text) else 'en')
    else:intent=interpret(text,entities,explicit_entity)
    path,manifest,receipt=load_session(root,identifier)
    if intent['entity_id']:
        g=read(path/'memory_graph.json')
        intent['category']=next(o['object_category'] for o in g['metadata']['observations'] if o.get('authorized_entity_id')==intent['entity_id'])
    result=search_session(root,path,intent['category'],intent['entity_id'])
    groups=group_candidates(result['candidates'])
    return dict(session_id=identifier,intent=intent,result=result,groups=groups,
        answer=describe(result,intent,groups),elapsed_s=time.perf_counter()-start,
        last_observation=result.get('last_useful_observation'),manifest=manifest)


def history(root,identifier,response,limit=10):
    path,_,_=load_session(root,identifier);graph=read(path/'memory_graph.json');intent=response['intent']
    observations=[o for o in graph['metadata']['observations'] if
        (o.get('authorized_entity_id')==intent['entity_id'] if intent['entity_id'] else o['object_category']==intent['category'])
        and o['source_times_s']]
    rows=[]
    if observations:
        first=min(observations,key=lambda o:min(o['source_times_s']));last=max(observations,key=lambda o:max(o['source_times_s']))
        for label,o,fn in [('首次相關觀察',first,min),('最後相關觀察',last,max)]:
            rows.append(dict(time=fn(o['source_times_s']),kind=label,detail=o['object_description'],status='觀察／不保證身分',frame=o['source_frame_indices'][-1]))
    for group in response['groups']:
        c=group['primary'];rows.append(dict(time=c['source_time_s'],kind='候選位置' if c['grounding_status']!='VERIFIED' else '可信歷史位置',
            detail=region_label(c.get('location_label',''))+' · '+RELATIONS.get(c['spatial_relation'],c['spatial_relation']),status=c['grounding_status'],frame=c['source_frame_index']))
    for e in graph.get('events',[]):
        relevant=e.get('authorized_entity_id')==intent['entity_id'] if intent['entity_id'] else e.get('object_category')==intent['category']
        if relevant and e.get('native_interval_s'):
            rows.append(dict(time=e['native_interval_s'][0],kind='事件假說',detail=e['type'],status=e['decision']+'（非實際動作確認）',frame=None))
    rows.sort(key=lambda r:r['time'])
    if len(rows)>limit:rows=[rows[round(i*(len(rows)-1)/(limit-1))] for i in range(limit)]
    return rows
