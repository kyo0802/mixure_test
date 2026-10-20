"""Publish explicitly AI-reviewed source evidence; never impersonate human GT."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
from consolidate_findmind_gt import ROOT, OUT, EXP, file_sha, load_json, save, verify
from memory_graph.experiments.three_vlm_contract import interval_distance

DEST = OUT / 'ai_visual_review'
# Authored after visual inspection of chronological original frames, not generated
# from agreement, model outputs, or interval overlap. Times select saved evidence.
# S=supported transition, U=uncertain, O=descriptive observation, M=modified observation.
DECISIONS = [
('G001','U',2.268,2.768,'test1_detail_1','手機首次出現在畫面時已被拿著；看不到由支撐面離開的過程。'),
('G002','S',3.768,6.270,'test1_detail_1','先看到手持手機下降至桌面，之後手離開且手機留在桌上。'),
('G003','S',11.505,11.772,'test1_detail_2','手機由桌面支撐變成手持離桌；兩人較寬的時間範圍改以可見前後狀態定位。'),
('G004','U',13.507,16.007,'test1_detail_2','手機及手移至籃球後方；手退出並不能證明遮擋中的手機已鬆手放下。'),
('G005','S',3.005,5.775,'test2_overview,test2_detail_1','先手持接近桌面，之後手機獨立留在桌上，手已撤離。'),
('G006','S',10.282,10.782,'test2_detail_2','手機先在桌面，後傾斜並隨手抬起。'),
('G007','U',19.778,24.502,'test2_detail_3','手機移到玩偶後方後被遮擋，無可見釋放與支撐後狀態。'),
('G008','U',3.9,6.275,'test3_boundary_3.5,test3_detail_1','手機由畫面下緣進入；已見平放受手接觸，缺乏可確認的手持前狀態。手撤離本身不是放置轉換。'),
('G009','S',14.505,15.005,'test3_detail_2','手機由桌面支撐，經傾斜後明確被手拿起。'),
('G010','U',16.273,20.280,'test3_detail_2','手機進入不透明箱內，手退出後仍看不到手機或釋放動作。'),
('G011','S',6.275,8.278,'test4_detail_1','手機由手持下降至桌面，手離開後手機仍留在桌面。'),
('G012','O',10.015,11.767,'test4_detail_2','採樣畫面中手機相對桌面保持不動，鏡頭改變；僅支持這段可見狀態描述。'),
('G013','S',13.002,13.503,'test4_detail_3','手機由桌面支撐變成手持離桌。'),
('G014','U',15.773,18.510,'test4_detail_3','手機被籃球遮住；手退出後無可見手機支撐狀態，不確認放置。'),
('G015','U',2.2,4.267,'test5_boundary_1.5,test5_detail_1','手機初次可見時位於畫面下緣，未看清由手持到桌面支撐的轉換。'),
('G016','S',12.767,13.267,'test5_detail_2','桌面上的手機傾斜並被手抬離。'),
('G017','U',14.5,18.5,'test5_detail_2','手機移入箱內後不可見；不能以空手退出推定放置完成。'),
('G018','U',5.208,6.275,'test6_boundary_4,test6_detail_1','首次清楚看見手機時已在下緣桌面受手接觸，缺少手持前狀態。'),
('G019','S',12.768,13.270,'test6_detail_2','由桌面支撐變成手持離桌。'),
('G020','S',23.5,25.770,'test6_detail_3','手持手機下降至微波爐頂部右側；手離開後可見手機獨立平放。'),
('G021','U',3.5,6.008,'test7_boundary_3,test7_detail_1','初段手機位於畫面下緣；只能確認後來在桌上，無充分手持到支撐的可見轉換。'),
('G022','S',12.768,13.270,'test7_detail_2','先在桌面，後被拿起。KUO 的起點晚於可見離桌轉換。'),
('G023','M',12.268,12.768,'test7_detail_2','原 CONTACT_ONLY 延伸至 14.357 秒，已涵蓋拿起；縮至離桌前接觸片段。13.270 秒已手持，不能整段當純接觸負例。'),
('G024','U',31.012,35.268,'test7_detail_3','約 31 秒前仍手持，後被玩偶遮住；原放置區間末端未提供可見釋放證據。'),
('G025','O',31.504,36.788,'test7_detail_3,test7_overview','保留手機被玩偶遮擋、事件不可確認的紀錄；不是無事件證明。'),
('G026','U',5.808,6.777,'test8_boundary_4.5,test8_detail_1','手機從畫面下緣出現時已接近桌面；無清楚手持前狀態，不由手離開推定放置。'),
('G027','U',14.270,14.772,'test8_boundary_14.25,test8_detail_2','抓握後鏡頭移動使手機離開畫面；未明確看見手機離開支撐面，後段再出現不能補證此瞬間。'),
('G028','S',28.508,30.512,'test8_detail_3','手持手機下降至窗邊平台，手撤離後手機仍留在支撐物上。'),
('G029','S',6.777,8.780,'test9_detail_1','手持手機下降至球與箱子之間；後方可見手機邊緣平放，手已離開。部分遮擋但有後狀態。'),
('G030','O',10.365,11.423,'test9_detail_1','球遮住手機，保留不可判定紀錄；不自動當沒有拿起或放下。'),
('G031','O',17.508,18.277,'test9_detail_2','原標的是 Ball：手推動桌面上的球，球仍由桌面支撐；不是手機接觸事件。'),
('G032','S',20.012,20.280,'test9_detail_2','手機原在桌面，之後明確手持離桌。'),
('G033','S',27.773,30.512,'test9_detail_3,test9_boundary_30,test9_detail_4','手持手機下降到微波爐頂；手撤離後可見白色圓柱後的黑色手機邊緣，後續角度也顯示手機平放。'),
('G034','M',33.782,35.000,'test9_detail_4','原標的是 Phone：可見段手機留在微波爐頂、鏡頭移動；縮至仍可辨認手機的段落，後來移出畫面的部分不視為可評負例。'),
]

def nearest(frames, t):
    return min(frames, key=lambda f: abs(f['native_pts_s'] - t))

def main():
    assert not (DEST / 'final_gt.json').exists(), 'Never overwrite an adjudication release'
    verify(OUT)
    registry = load_json(OUT / 'alignment_registry.json')
    assert {x[0] for x in DECISIONS} == set(registry) and len(DECISIONS) == len(registry)
    decisions, events = [], []
    evidence_index = []
    for path in sorted((DEST / 'evidence').glob('*/source_frames.json')):
        manifest = load_json(path)
        evidence_index.append({'manifest':str(path.relative_to(ROOT)), 'sha256':file_sha(path),
            'pages':[{'path':p['path'],'sha256':file_sha(ROOT/p['path'])} for p in manifest['pages']]})
    for gid, status, before, after, folders, note in DECISIONS:
        records = registry[gid]; video = records[0]['video_id']
        manifests = [load_json(DEST/'evidence'/d/'source_frames.json') for d in folders.split(',')]
        assert all(m['video']==video for m in manifests)
        frames = [dict(f, page=p['path']) for m in manifests for p in m['pages'] for f in p['frames']]
        cited = [nearest(frames,t) for t in (before,after)]
        kind = records[0]['event']['type']
        row = {'group_id':gid, 'video_id':video, 'source_sha256':manifests[0]['source_sha256'],
            'review_status':'AI_VISUAL_REVIEW','reviewer_id':'codex_ai_visual_review',
            'owner_delegated':True,'owner_accepted_individual_decision':False,
            'decision':{'S':'MODIFY','U':'UNCERTAIN','O':'ACCEPT','M':'MODIFY'}[status],
            'result':{'S':'VISUALLY_SUPPORTED_TRANSITION','U':'INSUFFICIENT_VISIBLE_TRANSITION','O':'DESCRIPTIVE_OBSERVATION','M':'MODIFIED_DESCRIPTIVE_OBSERVATION'}[status],
            'event_type':kind,'object_category':records[0]['event']['object_category'],
            'original_records':records, 'source_evidence':cited, 'decision_notes_zh':note,
            'negative_scoring_eligible':False,
            'evidence_manifests':[str((DEST/'evidence'/d/'source_frames.json').relative_to(ROOT)) for d in folders.split(',')]}
        decisions.append(row)
        if status=='S':
            assert kind in ('PICKUP','PLACEMENT')
            events.append({'final_event_id':'AI_'+gid,'group_id':gid,'video_id':video,
                'source_sha256':row['source_sha256'],'type':kind,'object_category':row['object_category'],
                'review_status':'AI_VISUAL_REVIEW','source_evidence':cited,
                'evidence_bracket_s':[x['native_pts_s'] for x in cited],
                'bracket_is_not_physical_event_duration':True,'exact_event_time_s':None,
                'before_state':'ON_SURFACE' if kind=='PICKUP' else 'HELD_BY_PERSON',
                'after_state':'HELD_BY_PERSON' if kind=='PICKUP' else 'ON_SURFACE',
                'identity_scope':'VISIBLE_LOCAL_TRANSITION_ONLY','cross_gap_identity_confirmed':False,
                'original_refs':[r['ref'] for r in records], 'notes_zh':note})
    save(DEST/'adjudication_decisions.json',decisions)
    save(DEST/'reviewed_evidence_manifest.json',evidence_index)
    save(DEST/'final_gt.json',{'status':'AI_ADJUDICATED_REFERENCE_NOT_HUMAN_GT','events':events,
        'unresolved_groups':[r['group_id'] for r in decisions if r['decision']=='UNCERTAIN'],
        'observations':[r for r in decisions if 'OBSERVATION' in r['result']],
        'exhaustiveness':'NOT_ATTESTED','method':'Original source-frame chronological inspection: 1 s overviews, 0.25 s details, selected 0.1 s boundaries. Not continuous all-native-frame review.'})
    save(DEST/'gt_eligibility.json',{'reference_kind':'AI_VISUAL_REVIEW','exhaustive_eligible_scopes':[],
        'positive_exploratory_reference_ids':[e['final_event_id'] for e in events],
        'formal_metrics_eligible':False,'reason':'No exhaustive attestation; AI review is not human confirmation. Model citation/instance support not adjudicated by temporal overlap.',
        'preserved_original_exhaustiveness':'NOT_ATTESTED','uncertain_is_negative':False})
    proposals = load_json(EXP/'event_proposals.json')['proposals']
    models = load_json(EXP/'model_results.json')
    # Proximity lookup ONLY. Never inject a reviewed identity into the strict
    # matcher, turn overlap into TP, or collapse distinct overlapping events.
    proximity=[]
    for e in events:
        for p in proposals:
            b=p.get('evidence_bracket_native_pts')
            if p['video_id']!=e['video_id'] or p['type']!=e['type'] or not b or b[0]>b[1]:continue
            if 'phone' not in p['object_description'].lower():continue
            distance=interval_distance(b,e['evidence_bracket_s'])
            if distance <= .5+1e-9:
                proximity.append({'reference_id':e['final_event_id'],'proposal_id':f"{p['model']}:{p['window_id']}:{p['event_index']}",
                    'model':p['model'],'strict_valid':p['strict_accepted'],'object_description':p['object_description'],
                    'proposal_evidence_bracket_s':b,'reference_evidence_bracket_s':e['evidence_bracket_s'],
                    'bracket_distance_s':distance,'within_tolerances':[t for t in (0,.2,.5) if distance<=t+1e-9],
                    'is_authoritative_match':False,'physical_support':'NOT_INFERRED_FROM_TEMPORAL_PROXIMITY'})
    save(DEST/'temporal_proximity_review.json',{'status':'DESCRIPTIVE_NOT_EVENT_MATCHING','pairs':proximity,
        'deduplication':'No event identity inferred. Report distinct reference IDs reached, not summed overlapping-window hits.',
        'limitations':'Evidence brackets are not event durations; proximity may reflect wide brackets, wrong object, unsupported states or invalid outputs.'})
    stats={m:{k:d[k] for k in ('completed','raw_json_parse_count','raw_schema_valid_count','raw_strict_valid_count','event_proposal_count','strict_event_proposal_count')} for m,d in models.items()}
    save(DEST/'three_model_comparison.json',{'models':stats,'formal_precision_recall_f1':None,
        'wrong_target_error_count':None,'physical_state_consistency_count':None,
        'reason':'No exhaustive eligible scope or adjudicated model-instance correspondence. Missing values are not zero.',
        'new_model_generations':0,'existing_generations':sum(d['completed'] for d in models.values())})
    counts=Counter(e['type'] for e in events)
    lines=['# 原片視覺裁決與三模型比較報告','', '更新：2026-10-20。來源：`artifacts/vlmtest/gt_consolidation_v1/ai_visual_review/`。','',
        '## 已完成與適用範圍','',
        f'依你授權代為裁決，已檢視 test1–test9 原片的按時間排序影格，完成 34 組裁決。15 個可見物理轉換：{counts["PICKUP"]} 個 PICKUP、{counts["PLACEMENT"]} 個 PLACEMENT；13 個物理轉換不確定；另 6 組為接觸、鏡頭移動、遮擋描述。', '',
        '**這是 AI 原片視覺複核，不是新增人工標註或人工完備性背書。** 全片概覽每秒一格，事件細節每 0.25 秒一格，部分邊界每 0.1 秒一格；沒有宣稱逐格連續播放。證據保留原片 SHA、native PTS、來源格號與接觸表。','',
        '原始兩位 JSON、主裁決 CSV、coverage CSV、模型輸出與歷史結果保持不變。新 final_gt.json 明確標記 AI_ADJUDICATED_REFERENCE_NOT_HUMAN_GT，不能冒充 HUMAN_REVIEWED 進入既有正式評分。','',
        '## 關鍵修正','',
        '- 手把手機移進箱子、籃球或玩偶後方，不能只憑手最後退出就確認放置；這些案例保留不確定。',
        '- 多支影片開頭只見手機在畫面下緣、手接觸後離開，沒有充分手持前狀態，不硬標 PLACEMENT。',
        '- test7 的 CONTACT_ONLY 原區間含真正拿起動作，縮至離桌前接觸片段。',
        '- test8 的拿起候選在抓握後離開畫面，缺少清楚離桌畫面，保留不確定。',
        '- test9 的 G031 是球的接觸、G034 是手機的鏡頭移動；依原始類別分開處理。',
        '- 事件只主張可見局部轉換，不跨離鏡或長遮擋認定全程同一個物理實例。','',
        '## 逐組裁決與原片依據','',
        '時間為前／後證據影格，並非事件持續時間。UNCERTAIN 不是否認事件曾發生，也不是負例。每組原始 event_id、reviewer、confidence、evidence references 完整保留於 adjudication_decisions.json。','']
    for r in decisions:
        original='；'.join(f"{x['reviewer_id']} {x['event']['type']} {x['event']['start_s']}–{x['event']['end_s']} 秒" for x in r['original_records'])
        evidence='；'.join(f"[{f['native_pts_s']:.3f}s / f{f['source_frame_index']}]({(ROOT/f['page']).as_posix()})" for f in r['source_evidence'])
        lines += [f"### {r['group_id']} · {r['video_id']} · {r['event_type']}",'',f'- 原始：{original}',f"- 裁決：**{r['decision']} / {r['result']}**。{r['decision_notes_zh']}",f'- 原片證據：{evidence}','']
    lines += ['## 552 次既有推論：格式與事件候選比較','', '| 模型 | 完成 | 原始 JSON 合法 | Schema 合法 | Strict 合法 | 事件候選 | Strict 事件候選 |','|---|---:|---:|---:|---:|---:|---:|']
    for m,s in stats.items():lines.append('| '+m+' | '+' | '.join(str(v) for v in s.values())+' |')
    lines += ['', 'Strict-invalid 仍然保留，不等於 NO_EVENT。Qwen 外層 code fence 中的內容可以描述性查看，不能回寫成原始 strict-valid。候選多不代表更準確；沒有因此宣布 Nemotron 勝出。','',
        '### 時間鄰近的候選檢索（不是 TP、recall 或實體匹配）','',
        '只查同片、同事件類型、文字包含 phone 的候選。以既有 interval_distance 在 0／0.2／0.5 秒找前後證據 bracket 的距離；以下是有任何候選接近的不同參考事件數，同一事件多窗命中只計一個參考 ID。沒有用此規則合併模型事件。','',
        '| 模型 | 所有候選：0 / .2 / .5 秒 | Strict 候選：0 / .2 / .5 秒 |','|---|---|---|']
    for m in models:
        vals=[]
        for strict in (False,True): vals.append(' / '.join(str(len({p['reference_id'] for p in proximity if p['model']==m and (not strict or p['strict_valid']) and t in p['within_tolerances']})) for t in (0,.2,.5)))
        lines.append(f'| {m} | {vals[0]} | {vals[1]} |')
    lines += ['', '**此表不驗證模型引用影格足以支持事件、不確認目標實例、不證明時間定位正確。** 詳細 proposal ID 與 bracket 留在 temporal_proximity_review.json；它不進入 authoritative 一對一匹配。','',
        '## 尚不能報出的分數與原因','',
        '- 兩位原始 event_list_exhaustiveness=NOT_ATTESTED 完整保留；採樣複核不足以新增無遮擋且完整的負例範圍。',
        '- 正式 PICKUP／PLACEMENT precision、recall、F1 與整體 F1 均為 unavailable，沒有把未知區間算 FP/TN。',
        '- Wrong-target 與物理 state consistency 尚無逐模型引用影格／實例裁決，因此不填零或推估數字。',
        '- 去重與正式一對一匹配仍要求已確認同一事件／物件；本次不以重疊時間或 phone 字串替代這個要求。',
        '- 15 個可見正事件可用於探索性對照，13 個未確認事件保留日後檢查；沒有因局部不確定刪掉全片的可見證據。','',
        '## 交付與狀態','',
        '已完成 34 組 AI 裁決、可見正事件參考、證據索引、既有模型格式比較與時間候選檢索。正式實體事件評分未完成，原因是完備範圍與模型引用／實例資格不足，並非要求你再讀 CSV。','',
        '可直接閱讀本報告逐組中文判斷並點選原片影格。若要下一步完成正式比較，需對照模型實際引用影格完成物理支持及同一事件裁決，且只在明確完備的局部範圍計算負例相關分數；本次未自行製造這些資格。','',
        '狀態：AI_VISUAL_ADJUDICATION_COMPLETE_WITH_UNCERTAINTY；FORMAL_EVENT_METRICS_NOT_ELIGIBLE。未新增模型推論、未更新 Graph、未 commit/push。']
    report='\n'.join(lines)+'\n'
    (DEST/'AI_VISUAL_ADJUDICATION_REPORT.md').write_text(report,encoding='utf-8')
    (DEST/'final_gt_summary.md').write_text(f'# AI visual reference\n\n15 supported transitions: {dict(counts)}. 13 unresolved physical groups; 6 descriptive observations.\nNot human-reviewed GT. No exhaustive negative scope. See AI_VISUAL_ADJUDICATION_REPORT.md.\n',encoding='utf-8')
    verify(OUT)
    save(DEST/'completion_receipt.json',{'preserved_files_verified':len(load_json(OUT/'preservation_manifest.json')),
        'decision_groups':len(decisions),'positive_events':len(events),'event_counts':dict(counts),
        'source_review_manifest_count':len(evidence_index),'new_model_generations':0,
        'files':{p.name:file_sha(p) for p in DEST.iterdir() if p.is_file()}})
    (ROOT/'WORKSPACE/VLMtest/LATEST_REPORT.md').write_text(report,encoding='utf-8')
    print(json.dumps({'groups':len(decisions),'events':dict(counts),'preservation':'PASS','report':str(DEST/'AI_VISUAL_ADJUDICATION_REPORT.md')}))

if __name__=='__main__':main()
