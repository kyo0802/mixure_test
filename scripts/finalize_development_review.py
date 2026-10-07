"""Record post-freeze engineering observations; never change inference artifacts."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from memory_graph.reasoning.pipeline import verify, verify_manifest
from memory_graph.reasoning.common import OUT

FIELDS = ('event_type', 'interaction_anchor', 'released', 'target_visible_after',
          'final_relation', 'final_relation_anchor')

def row(pack, eligible, complete, placement, values, relation, unsafe, safe, failures, finding, confirmed=False):
    return {'pack_id':pack, 'reasoning_eligible':eligible,
            'visually_complete_transition':complete,
            'placement_release_reviewable':placement,
            'confirmed_visible_release':confirmed,
            'admissible_values':dict(zip(FIELDS, values)),
            'relation_review':relation, 'unsafe_overclaim':unsafe,
            'material_assertions_safe':safe, 'search_useful':False,
            'failure_categories':failures, 'finding':finding}

def main():
    checks = {'primary':verify(), 'baseline':verify_manifest(OUT, OUT/'final/baseline_prediction_manifest.json')}
    if not all(c['valid'] for c in checks.values()):
        raise RuntimeError(checks)
    e=[]
    e.append(row('test1__W01', True, False, False,
        [['CARRIED_OR_HELD'],['A'],['NO'],['YES','PARTIAL'],['HELD_BY'],['A']],
        'INSUFFICIENT',False,False,
        ['NO_STABLE_PRE_STATE','WINDOW_END_TOO_EARLY','TRANSITION_NOT_CAPTURED'],
        '開頭已在 A 手中，持握與攝影機移動可見，但沒有未持握 PRE 或完整拿起/放下；未送 Qwen。'))
    for pack in ['test1__W03','test1__W05']:
        e.append(row(pack, True, True, True,
            [['PLACED_OR_PUT_DOWN'],['A'],['YES'],['YES'],['ON'],['B']],
            'SUPPORTED' if pack.endswith('W03') else 'INCORRECT',False,False,
            ['QWEN_EVENT_REASONING_ERROR','QWEN_ACTOR_ERROR'] + ([] if pack.endswith('W03') else ['QWEN_RELATION_ERROR']),
            '5.2–8.8 秒：手 A 持手機、f186–192 放手、手機留在桌面；有完整持握→release→靜置。B 在後段為桌面。兩個窗口邊界/影格相同，屬同一次 release；W03 ON B 合理但 STATIC/NONE actor/NO release 錯，W05 又漏掉 ON B。', True))
    e.append(row('test2__W01',True,False,False,
        [['STATIC'],['NONE'],['NO'],['YES'],['ON'],['B']],
        'INCORRECT',False,False,
        ['WINDOW_START_TOO_LATE','TRANSITION_NOT_CAPTURED','EVENT_SELECTION_WRONG','QWEN_RELATION_ERROR'],
        '6.0–9.6 秒手機已在桌上，只有攝影機/框抖動，未捕捉 placement；STATIC 可量測且正確，NONE 漏掉供有 B 桌面的 ON。自動 COMPLETE 不等於真正物理轉折。'))
    e.append(row('test2__W08',True,False,True,
        [['BECAME_OCCLUDED'],['A'],['UNCERTAIN'],['NO'],None,None],
        'INSUFFICIENT',False,False,
        ['NO_STABLE_PRE_STATE','WINDOW_START_TOO_LATE','UPSTREAM_IDENTITY_LIMITATION'],
        '開頭已持握，手機移到微波爐上熊後，手後段改碰熊。遮擋/放低過程可供檢查，但確切 release 與末端關係不足，不把 behind/inside 設成確定 truth；未送 Qwen。'))
    for pack in ['test3__W02','test3__W03','test3__W07']:
        dispatched=pack.endswith('W07')
        e.append(row(pack,True,True,True,
            [['PICKED_UP','CARRIED_OR_HELD','BECAME_OCCLUDED'],['A','B'],['UNCERTAIN'],['NO'],['NONE','UNCERTAIN'],['NONE','UNCERTAIN']],
            'SUPPORTED' if dispatched else 'INSUFFICIENT',False,False,
            ([] if dispatched else ['NO_STABLE_PRE_STATE']) +
            ['LOCATION_CONTEXT_MISSING','UPSTREAM_IDENTITY_LIMITATION'] +
            (['QWEN_EVENT_REASONING_ERROR','QWEN_ACTOR_ERROR'] if dispatched else []),
            '手機在桌面，約 14.6 秒手拿起，再向開口箱放低並被箱/手遮住。完整 pickup→移動→不可見可辨，release 本身未看清。箱不是供有 marker 的 location，不能強迫 INSIDE 某個球/椅子/微波爐。W02/W03 視覺有轉折卻因授權/穩定 PRE gate 未通過；W07 推論 STATIC/NONE actor 錯。三者重疊同一次事件。'))
    for pack in ['test4__W06','test4__W08']:
        e.append(row(pack,True,False,True,
            [['CARRIED_OR_HELD','BECAME_OCCLUDED'],['A','B'],['UNCERTAIN'],['NO'],['NONE','UNCERTAIN'],['NONE','UNCERTAIN']],
            'INSUFFICIENT',False,False,
            ['NO_STABLE_PRE_STATE','WINDOW_START_TOO_LATE','UPSTREAM_IDENTITY_LIMITATION','LOCATION_CONTEXT_MISSING'],
            '開頭手機已垂直握在手中，移向箱口後被箱壁/手擋住；可檢查放低與遮擋，缺 pickup 前 PRE，未能確認放手。箱沒有可靠 location marker；W08 僅 1.8 秒，未送 Qwen。'))
    e.append(row('test5__W01',True,False,False,
        [['STATIC'],['NONE'],['NO'],['YES'],['NONE'],['NONE']],
        'SUPPORTED',False,True,
        ['EVENT_SELECTION_WRONG','TRANSITION_NOT_CAPTURED','UPSTREAM_IDENTITY_LIMITATION'],
        '5.4–7.8 秒手机一直在桌面，攝影機改變而授權 T 中段消失；手機仍可見，不是拿起/放下。供有球/箱(原偵測標籤 laptop)/椅子，無有效桌面 marker，NONE 合理。六個可評欄位正確，但 NONE 不建立位置記憶。'))
    e.append(row('test5__W05',True,True,True,
        [['PICKED_UP','CARRIED_OR_HELD','BECAME_OCCLUDED'],['A','B'],['UNCERTAIN'],['NO'],None,['E','UNCERTAIN','NONE']],
        'WEAKLY_SUPPORTED',True,False,
        ['QWEN_EVENT_REASONING_ERROR','QWEN_ACTOR_ERROR','QWEN_RELATION_ERROR','LOCATION_CONTEXT_MISSING','UPSTREAM_IDENTITY_LIMITATION'],
        '11.4–15.0 秒由桌面拿起手機，再往箱口放低；後段手机被遮住。E raw label laptop 實際框到箱區，INSIDE E 方向有弱證據，但末端 containment/release 未完整確認，因此 relation truth 不可決、HIGH INSIDE 為過強物理宣稱。STATIC、E 當 actor 與 visible YES 都錯；不能安全寫入。'))
    e.append(row('test7__W05',True,True,False,
        [['PICKED_UP','CARRIED_OR_HELD','BECAME_OCCLUDED'],['A'],['NO'],['NO'],['NONE','UNCERTAIN'],['NONE','UNCERTAIN']],
        'SUPPORTED',True,False,
        ['QWEN_EVENT_REASONING_ERROR','QWEN_ACTOR_ERROR','UPSTREAM_IDENTITY_LIMITATION'],
        '12.4–16.0 秒手 A 將桌面手機抬成垂直後拿走，後段出畫面。沒有可見 release；STATIC+released YES 錯，validator 已以 STATIC_RELEASE 拒絕，NONE final relation/visible NO 合理。'))
    e.append(row('test8__W04',False,False,False,
        [None,['NONE'],['UNCERTAIN'],['NO'],['NONE','UNCERTAIN'],['NONE','UNCERTAIN']],
        'INSUFFICIENT',False,False,
        ['NO_STABLE_PRE_STATE','WINDOW_END_TOO_EARLY','TARGET_NOT_VISIBLE_ENOUGH','EVENT_SELECTION_WRONG','UPSTREAM_IDENTITY_LIMITATION'],
        '14.4–15.6 秒只有開頭桌面手機與手，攝影機立即移開，目標授權/可見資訊不足。後段 A 是椅子誤分類 person，不能当 actor，也不能推定拿走或 release；未送 Qwen。'))
    e.append(row('test8__W06',True,True,True,
        [['PLACED_OR_PUT_DOWN'],['A'],['YES'],['YES','PARTIAL'],['NONE','UNCERTAIN'],['NONE','UNCERTAIN']],
        'INCORRECT',True,False,
        ['LOCATION_CONTEXT_MISSING','QWEN_EVENT_REASONING_ERROR','QWEN_ACTOR_ERROR','QWEN_RELATION_ERROR','UPSTREAM_IDENTITY_LIMITATION'],
        '28.57–32.07 秒手 A 持手機，約 f906–918 放到黄色電話底座後離手，有可見 release。B/C cell-phone 框與 T 自身重疊/別名，D 是其他電話；沒有獨立底座 location marker。ON B 不是合法獨立目的地關係，STATIC/NO release/NONE actor 也錯；禁止自關係與混淆手機導致寫入。',True))
    e.append(row('test8__W07',False,False,False,
        [['STATIC','NO_CLEAR_INTERACTION'],['NONE'],['NO'],['NO'],['NONE','UNCERTAIN'],['NONE','UNCERTAIN']],
        'SUPPORTED',False,False,
        ['EVENT_SELECTION_WRONG','TRANSITION_NOT_CAPTURED','TARGET_NOT_VISIBLE_ENOUGH','UPSTREAM_IDENTITY_LIMITATION'],
        '31.2–35.14 秒手機已放好，攝影機轉開使目標出畫面；後段其他人/裝置沒有 T 授權，不替換為 phone_01。STATIC/NONE/NO release 可評，但末端 visible YES 錯，整體不納 reasoning-eligible。僅錯誤可見性未計入沿用的 unsafe placement/release/relation 定義。'))
    e.append(row('test9__W03',False,False,False,
        [None,['A'],['UNCERTAIN'],None,['NONE','UNCERTAIN'],['NONE','UNCERTAIN']],
        'INSUFFICIENT',False,False,
        ['NO_STABLE_PRE_STATE','WINDOW_END_TOO_EARLY','TARGET_NOT_VISIBLE_ENOUGH','UPSTREAM_IDENTITY_LIMITATION'],
        '18.4–19.6 秒只有起始 T 授權，後續手與手機外觀可見但身份未確認。不能從外觀/將來影格補授權，無可信連續 PRE/POST，test9 仍 unresolved；未送 Qwen。'))
    review={'review_completed_unix':time.time(),'predictions_changed':False,
        'primary_and_baseline_freeze_verified_before_review':True,
        'review_scope':'Execution-agent post-freeze visual engineering review of all 17 selected physical sheets; no independent human GT',
        'review_method':'All chronological sampled images viewed; only authorized T grounds target. Ambiguous containment is indeterminate; release UNCERTAIN when occluded. Labels do not feed builder or inference.',
        'unsafe_overclaim_definition':'Unestablished affirmative placement/release or real physical relation. Wrong actor and visibility counted separately, matching original V2945 review definition.',
        'placement_release_reviewable_definition':'Window shows lowering/occlusion or placement/release to inspect; this does not imply confirmed release. confirmed_visible_release is reported separately.',
        'events':e,
        'duplicate_window_pairs':[['test1__W03','test1__W05']],
        'correlated_event_groups':[['test1__W03','test1__W05'],['test3__W02','test3__W03','test3__W07'],['test4__W06','test4__W08']],
        'old_visual_complete_transition':0,'old_placement_release_reviewable':0,
        'single_bottleneck':'Qwen7B temporal action/marked-region interpretation: even visibly captured pickup/release sequences are answered STATIC; 9/9 STATIC and no actor A/B is correctly used in action windows. Dense evidence alone does not solve safe memory.',
        'decision':'EVENT_WINDOW_BUILDER_PARTIAL_IMPROVEMENT',
        'readiness':'READY_TO_FREEZE_FOR_VALIDATION'}
    dest=OUT/'evaluation';dest.mkdir(exist_ok=True)
    (dest/'post_freeze_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    old=json.loads((ROOT/'outputs/reference_qwen/evaluation/post_freeze_review.json').read_text(encoding='utf-8'))
    old['review_completed_unix']=time.time()
    old['same_runtime_predictions_frozen_before_review']=True
    old['review_scope']='Same frozen baseline image evidence and reference labels; new runtime predictions inspected after freeze'
    original=json.loads((ROOT/'outputs/reference_qwen/model_7b/responses.json').read_text(encoding='utf-8'))
    current=json.loads((OUT/'evaluation/runtime_matched_baseline/responses.json').read_text(encoding='utf-8'))
    old['same_runtime_changes']=[{'pack_id':b['pack_id'],'changed_fields':{k:{'original':a['answer'][k],'current':b['answer'][k]} for k in b['answer'] if a['answer'][k]!=b['answer'][k]}} for a,b in zip(original,current) if a['answer']!=b['answer']]
    old['same_runtime_change_note']='Three answers change visibility and/or confidence under the SDPA kernel correction. Reference labels remain frozen; physical unsafe flags stay unchanged. Metric scoring uses fresh answers, not historical scores.'
    (dest/'baseline_same_runtime_review.json').write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Reviewed physical windows:',len(e),'freeze checks:',{k:c['valid'] for k,c in checks.items()})

if __name__=='__main__':main()
