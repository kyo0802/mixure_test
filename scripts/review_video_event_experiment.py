"""Persist execution-agent observations after native predictions have frozen."""
import copy
import sys
import time
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.reasoning.video_experiment import EXP,OUT,read,write,events,verify_baseline
from memory_graph.reasoning.pipeline import verify_manifest

def main():
    verify_baseline();check=verify_manifest(EXP,EXP/'final/artifact_manifest.json')
    if not check['valid']:raise RuntimeError(check)
    ref={r['pack_id']:r for r in read(OUT/'evaluation/post_freeze_review.json')['events']}
    details={
        'test1__W03':('INCORRECT',False,False,
            ['STATIC_COLLAPSE','QWEN_EVENT_REASONING_ERROR','QWEN_ACTOR_ERROR','QWEN_RELEASE_ERROR','QWEN_VISIBILITY_ERROR','QWEN_RELATION_ERROR'],
            'Native 順序清楚看到手放下手機並離手、手機仍在桌面。Video STATIC/NONE actor/NO release/NO visibility/NONE relation 全錯；沒有肯定假 release 或實際 relation，因此 unsafe=False。Image 原本 ON B 正確，video 又漏掉該關係。'),
        'test1__W05':('INCORRECT',False,False,
            ['STATIC_COLLAPSE','QWEN_EVENT_REASONING_ERROR','QWEN_ACTOR_ERROR','QWEN_RELEASE_ERROR','QWEN_VISIBILITY_ERROR','QWEN_RELATION_ERROR'],
            '與 W03 同一次放手、同 underlying frames；不同 trigger phases 仍得相同 STATIC/NONE/NO/NO/NONE。不是第二個獨立 release episode，保留 canonical pack 比較但 unique 只算一次。'),
        'test2__W01':('INCORRECT',False,False,
            ['QWEN_VISIBILITY_ERROR','QWEN_RELATION_ERROR','WINDOW_NOT_ACTUALLY_ACTION_COMPLETE'],
            'Native 仍顯示手機靜置在桌面、沒有真正 pickup/placement。STATIC/NONE actor/NO release 正確；NO visibility 錯，手機最後可見；NONE 漏掉 ON B 桌面。自動 COMPLETE 的既有 false-positive window 原樣保留。'),
        'test3__W07':('SUPPORTED',True,False,
            ['QWEN_RELEASE_ERROR','UPSTREAM_LOCATION_CONTEXT_MISSING','UPSTREAM_IDENTITY_LIMITATION'],
            'Native 更清楚呈現從桌面拿起，再向箱口放低、被箱壁/手遮住。PICKED_UP/A/NO visibility 正確，比 image STATIC/NONE 改善；但末端 release 仍沒有直接可見證據，凍結 reference UNCERTAIN 不改，YES 為 unsafe overclaim。真正箱目的地未供 marker，NONE final relation 合理。'),
        'test5__W01':('INCORRECT',True,False,
            ['QWEN_RELATION_ERROR','UPSTREAM_LOCATION_CONTEXT_MISSING','UPSTREAM_IDENTITY_LIMITATION','WINDOW_NOT_ACTUALLY_ACTION_COMPLETE'],
            'Native 显示靜置與攝影機移動，STATIC/NONE actor/NO release/YES visibility 正確。NEAR + NONE relation anchor 無 grounded pair，原 minimal validator 以 IMPOSSIBLE_RELATION_ANCHOR 拒絕；NEAR 也是未建立的肯定物理關係，因此 ALL unsafe=True。原 image NONE 合理。未修正箱 raw label laptop 或新增桌面候選。'),
        'test5__W05':('INSUFFICIENT',True,False,
            ['QWEN_RELEASE_ERROR','UPSTREAM_LOCATION_CONTEXT_MISSING','UPSTREAM_IDENTITY_LIMITATION'],
            'Native 顯示拿起/手 A/箱口放低後遮住，PICKED_UP/A/NO visibility 改善。看不清確切 release，YES 超過 frozen UNCERTAIN reference 可支持的證據。NONE 取代 image HIGH INSIDE E，減少特定位置強判，但整個 answer 仍不能作 safe memory；relation truth 原不可決保持 null。箱/laptop 誤分類沒有修復。'),
        'test7__W05':('SUPPORTED',True,False,
            ['QWEN_RELEASE_ERROR','UPSTREAM_IDENTITY_LIMITATION'],
            'Native 顯示手 A 從桌面抬起手機、持握帶走後攝影機轉開，沒有放手。PICKED_UP/A/NO visibility 正確，但 released YES 明確錯且 unsafe。原 STATIC+YES 被 minimal validator 拒絕；video PICKED_UP+YES 可過原 minimal validator，說明 validator 通過不代表物理安全。'),
        'test8__W06':('SUPPORTED',False,False,
            ['STATIC_COLLAPSE','QWEN_EVENT_REASONING_ERROR','QWEN_ACTOR_ERROR','QWEN_RELEASE_ERROR','QWEN_VISIBILITY_ERROR','UPSTREAM_LOCATION_CONTEXT_MISSING','UPSTREAM_IDENTITY_LIMITATION'],
            'Native 清楚顯示持手機放到黃色電話底座、手離開、手機留下；reference YES release/YES或PARTIAL visibility 不變。STATIC/NONE actor/NO release/NO visibility 錯。NONE final relation合理避開 B/C 的 target self-alias；沒有獨立底座 marker，不能強迫 ON B。比 image 自關係 ON B 安全，但未解決真正 release。'),
        'test8__W07':('SUPPORTED',False,True,
            ['WINDOW_NOT_ACTUALLY_ACTION_COMPLETE','UPSTREAM_IDENTITY_LIMITATION'],
            'Native 仍是原手機靜置後攝影機移開、最後目標出畫面。STATIC/NONE actor/NO release/NO visibility/NONE relation 符合可判欄位，改善 image 的 YES visibility。原整體 eligible=False 保持，其他人/裝置沒有 retroactive target authority。')}
    rows=[]
    for e in events():
        p=e['pack_id'];r=copy.deepcopy(ref[p]);relation,unsafe,safe,failures,finding=details[p]
        r.update(relation_review=relation,unsafe_overclaim=unsafe,material_assertions_safe=safe,search_useful=False,
            failure_categories=failures,finding=finding)
        rows.append(r)
    write('evaluation/post_freeze_video_review.json',{'review_completed_unix':time.time(),
        'predictions_changed':False,'prediction_freeze_verified_before_review':True,
        'review_method':'Execution-agent inspection of all nine chronological official processor-selected native clip contact sheets after prediction freeze. Not independent human GT.',
        'baseline_admissible_values_unchanged':True,'strata_unchanged':True,
        'unsafe_definition':'Same baseline definition: unestablished affirmative placement/release or real relation; all outputs count, even validator-invalid. Actor/visibility scored separately.',
        'reference_disagreements':[], 'events':rows,
        'bottleneck_conclusion':'高密度原生影片改善三個 pickup 的 event/actor 判讀，表示輸入條件影響這部分推理；但真正放手仍0/3，反而有 pickup 後錯誤 release YES、錯誤 final visibility 與未grounded NEAR。Temporal representation只解決部分問題，不能解決Qwen release/uncertainty與marked-region grounding瓶頸。未授權影格不畫T使標記密度仍稀疏，這是嚴格權限下的既知限制；不能僅憑本次結果把所有提升或退步因果歸於FPS。'})
    print('Frozen reference unchanged; video reviews',len(rows))

if __name__=='__main__':main()
