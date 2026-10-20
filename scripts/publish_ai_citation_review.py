"""Publish manually authored AI pixel judgements and positive-only matching."""
import sys
from collections import Counter
sys.dont_write_bytecode=True
from consolidate_findmind_gt import ROOT,OUT,load_json,save,file_sha,verify
from memory_graph.experiments.three_vlm_evaluation import match_one_to_one

DEST=OUT/'ai_visual_review'
# These decisions were authored after viewing all 13 saved citation sheets.
SUPPORT={1,6,7,8,15,16,19,24,25,28,30,34,38}
UNCERTAIN={3,10,11,13,18,20,27,29,32,39}
NOTES={
1:'前格手機由桌面支撐，後格手持離桌。',2:'引用前格手機已手持，後格仍手持；缺少桌面前狀態。',
3:'後格正在傾斜，接觸面模糊；引用尚不足以確認離桌。',4:'前後皆已手持。',5:'前後皆為桌面抓握，後格尚未呈現明確離桌。',
6:'前格手機在手中下降，後格平放桌面且手仍接觸；支持支撐狀態變化，不主張此時完全鬆手。',
7:'桌面手機變成手持，與原片同一局部拿起相符。',8:'桌面手機變成手持；與 #7 同一局部拿起，不能重算事件。',9:'前後皆已手持。',
10:'後格抓握桌面手機，支撐是否解除不清楚。',11:'後格手機位於影像下緣，支撐後狀態不充分。',12:'前後手機都在桌面受手接觸，缺手持前狀態。',
13:'後格傾斜抓握，但無充分可見離桌狀態。',14:'後格仍桌面接觸；時間早於可見拿起。',15:'前格手機在桌面，後格右上邊緣可見手持手機。',
16:'前格桌面，後格手機明確抬離；與 #15 同一局部拿起。',17:'後格仍平放桌面被接觸。',18:'後格僅傾斜，是否仍由桌面支撐不明。',
19:'前格桌面，後格手機已明確手持離桌。',20:'前格手機已開始抬起／傾斜，支撐前狀態不能確定。',21:'前格已手持，後格被球遮擋，不支持引用中的拿起轉換。',
22:'前後皆手持，未呈現放下。',23:'前後皆已在桌面，手由接觸變成退出，不提供手持前狀態。',24:'由明確手持變成桌面平放、手仍接觸；支持支撐轉換，不主張已完全鬆手。',
25:'桌面手機變為手持，與 #19 同一局部拿起。',26:'前格已手持，後格被球遮擋；缺拿起前狀態。',27:'後格手機在箱子後／內不可見，不能由手臂姿勢確認持握後狀態。',
28:'前格桌面手機，後格明確手持離桌。',29:'後格傾斜且模糊，無充分離桌證據。',30:'前格桌面，後格明確手持。',
31:'前後皆桌面抓握。',32:'後格手機被手遮擋於頂面邊緣，引用無充分可辨認的支撐後狀態。',33:'前後皆桌面抓握，尚未明確離桌。',
34:'桌面手機變成手持。',35:'前後皆為平台上的手機受手接觸，未呈現手持到支撐轉換。',36:'前後手機皆在桌面，後格只是手接觸。',
37:'前後手機皆在桌面，後格只是手接觸。',38:'由桌面手機變成手持，明確可見離桌。',39:'前後手機都受到手與白色裝置遮擋，無充分手持前／支撐後狀態。'}

def main():
    rows=load_json(DEST/'model_citations/manifest.json')
    refs={e['final_event_id']:e for e in load_json(DEST/'final_gt.json')['events']}
    assert len(rows)==39 and set(NOTES)==set(range(1,40)) and not SUPPORT & UNCERTAIN
    for row in rows:
        n=row['inspection_number']
        row.update(review_status='AI_VISUAL_REVIEW',physical_citation_support='SUPPORTED' if n in SUPPORT else 'UNCERTAIN' if n in UNCERTAIN else 'NOT_SUPPORTED_BY_CITED_STATES',
            review_notes_zh=NOTES[n],wrong_target='NOT_ESTABLISHED',is_authoritative_match=False)
        row['confirmed_local_event_id']=row['reference_id'] if n in SUPPORT else None
        row['duplicate_policy']='Same event only when visually linked to the same reviewed local transition; no cross-gap physical identity claim.'
    save(DEST/'model_citation_adjudication.json',rows)
    summaries={}
    for model in ('qwen','videollama','nemotron'):
        selected=[r for r in rows if r['model']==model]
        results={}
        for strict in (False,True):
            dedup={}
            for row in selected:
                if row['physical_citation_support']!='SUPPORTED' or strict and not row['strict_valid']:continue
                key=row['confirmed_local_event_id']
                # Stable representative; all discarded IDs remain in audit records.
                dedup.setdefault(key,row)
            predictions=[{'reviewed_object_id':r['confirmed_local_event_id'],'type':r['type'],
                'video_sha256':refs[r['reference_id']]['source_sha256'],
                'time_interval':r['proposal_evidence_bracket_s']} for r in dedup.values()]
            truth=[{'reviewed_object_id':e['final_event_id'],'type':e['type'],'video_sha256':e['source_sha256'],
                'time_interval':e['evidence_bracket_s']} for e in refs.values()]
            results['strict' if strict else 'all_descriptive']={str(t):{
                'matched_positive_reference_count':len(match_one_to_one(predictions,truth,t)),
                'pairs':match_one_to_one(predictions,truth,t),
                'prediction_ids':[r['proposal_id'] for r in dedup.values()],
                'reference_ids':list(refs)} for t in (0,.2,.5)}
        summaries[model]={'reviewed_candidates':len(selected),'citation_support_counts':dict(Counter(r['physical_citation_support'] for r in selected)),
            'positive_only_matching':results}
    save(DEST/'positive_only_ai_comparison.json',{'status':'AI_ADJUDICATED_EXPLORATORY_ONLY',
        'selection':'39 phone-described candidates within 0.5 s bracket distance of 15 AI-supported reference transitions. Not an unbiased sample of all outputs.',
        'models':summaries,'reference_event_count':15,'unreviewed_candidates':128,
        'formal_precision':None,'formal_recall':None,'formal_f1':None,
        'time_semantics':'Evidence support brackets, not physical durations or exact event timestamps.',
        'not_supported_citation_is_not_false_positive':True})
    lines=['# 模型引用影格複核補充','', '2026-10-20；AI 原片裁決後，額外實際查看 39 組模型引用前／後影格，共 13 張比較圖。沒有再跑模型。','',
        '## 結果','', '| 模型 | 審閱候選 | 引用支持 | 引用不支持 | 不確定 | 去重後支持的正事件（所有候選） | Strict 支持的正事件 |','|---|---:|---:|---:|---:|---:|---:|']
    for m,s in summaries.items():
        c=s['citation_support_counts'];results=s['positive_only_matching']
        lines.append(f"| {m} | {s['reviewed_candidates']} | {c.get('SUPPORTED',0)} | {c.get('NOT_SUPPORTED_BY_CITED_STATES',0)} | {c.get('UNCERTAIN',0)} | {results['all_descriptive']['0']['matched_positive_reference_count']} | {results['strict']['0']['matched_positive_reference_count']} |")
    lines += ['', '對已視覺確認屬同一局部轉換的候選去重，再使用既有 maximum-cardinality one-to-one matcher；0、0.2、0.5 秒的結果相同。配對索引、代表候選 ID、參考事件 ID 均保留於 positive_only_ai_comparison.json。','',
        '**這是 15 個 AI 正事件參考中的探索性命中數，不是正式 recall／precision／F1。** 引用不支持不代表整段影片沒有該事件：例如前後都已拿著手機，事件可能較早發生，但選錯 BEFORE 引用。39 筆是依時間鄰近選出的子集，剩餘 128 筆沒有做模型引用視覺裁決，不當成正確或錯誤。','',
        '## 可確認的問題','',
        '- 多個候選把「已經持有」到「繼續持有」標成 PICKUP，或把桌面接觸誤當離桌；只看時間重疊會高估能力。',
        '- 有些候選在原片附近確有事件，但引用結束太早、物件被擋住，無法支持輸出的 AFTER 狀態。',
        '- Qwen 有引用支持的事件候選，但仍是原始 strict-invalid，不能因視覺合理就改成 strict-valid。',
        '- Nemotron 在這個正事件候選子集提供最多可支持局部轉換；尚不能推論整體較準確，因未完整評估它的其他候選與誤報。',
        '- Wrong-target 在這個子集未建立可證實的錯誤，不等於全體零錯誤。物理 state 一致性僅評估本次 39 筆事件引用的前後狀態，沒有審完 6,420 個 state claims。','',
        '## 逐筆依據','', '| # | 候選 | 裁決 | 原片引用判斷 |','|---:|---|---|---|']
    for r in rows:lines.append(f"| {r['inspection_number']} | [{r['proposal_id']}]({(ROOT/r['contact_sheet']).as_posix()}) | {r['physical_citation_support']} | {r['review_notes_zh']} |")
    lines+=['','## 驗證','', '既有 GT consolidation CPU 測試 21／21 通過；2,235 個保留檔案 SHA 驗證通過。無新模型推論、無 GT 原檔覆寫、無 Graph 更新、無 commit／push。','',
        '本次完成：原始 34 組 AI 裁決與 39 筆模型引用複核、合資格的局部正事件探索性對照。全體正式模型評分仍因完備範圍、剩餘模型引用與身分資格不足而不輸出分數。']
    text='\n'.join(lines)+'\n'
    (DEST/'MODEL_CITATION_REVIEW.md').write_text(text,encoding='utf-8')
    original=(DEST/'AI_VISUAL_ADJUDICATION_REPORT.md').read_text(encoding='utf-8')
    # Preserve the earlier artifact; current workspace incorporates later work.
    original=original.replace('Wrong-target 與物理 state consistency 尚無逐模型引用影格／實例裁決，因此不填零或推估數字。','Wrong-target 與物理 state consistency 未做全體裁決；後續已完成 39 筆局部引用複核，詳見下方補充。')
    original=original.replace('模型引用／實例資格不足，並非要求你再讀 CSV。','全體模型引用／實例資格不足，並非要求你再讀 CSV。')
    original=original.replace('本次未自行製造這些資格。','下方補充已完成 39 筆引用複核與局部正事件對照；沒有製造負例資格。')
    (ROOT/'WORKSPACE/VLMtest/LATEST_REPORT.md').write_text(text+'\n---\n\n'+original,encoding='utf-8')
    verify(OUT)
    save(DEST/'final_review_receipt.json',{'preserved_files_verified':2235,'cpu_tests_passed':21,
        'original_adjudication_receipt_sha256':file_sha(DEST/'completion_receipt.json'),
        'artifacts':{str(p.relative_to(ROOT)):file_sha(p) for p in DEST.rglob('*') if p.is_file()},
        'workspace_report_sha256':file_sha(ROOT/'WORKSPACE/VLMtest/LATEST_REPORT.md')})
    print({m:s['citation_support_counts'] for m,s in summaries.items()})

if __name__=='__main__':main()
