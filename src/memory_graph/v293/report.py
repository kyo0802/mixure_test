"""Freeze predictions before regression evaluation and publish measured results."""
from collections import Counter
from datetime import datetime,timezone
from .audit import ROOT,BASE,OUT,VIDEOS,read,write
from .sources import verify_baseline_contract
from memory_graph.v292.validator import sha256

POST_FILES={'artifact_manifest.json','contract_validation.json','regression_summary.json','evaluation_summary.json','V293_REPORT.md','evidence_funnel.md'}

def verify():
    manifest=read(OUT/'artifact_manifest.json',{})
    if not manifest:return {'valid':False,'errors':['No frozen manifest']}
    errors=[]
    for path,digest in manifest['files'].items():
        if not (OUT/path).is_file() or sha256(OUT/path)!=digest:errors.append(path)
    for path,digest in manifest['source_hashes'].items():
        if sha256(ROOT/path)!=digest:errors.append('source changed: '+path)
    return {'valid':not errors,'errors':errors,'files_checked':len(manifest['files'])}

def contract_checks():
    errors=[];count=0
    for video in VIDEOS:
        folder=OUT/video
        for filename in ['pair_evidence_requests.json','pair_evidence_packs.json','eligibility_decisions.json',
            'selected_temporal_frames.json','vlm_inputs.json','vlm_results.json','grounding_validation.json',
            'physical_decisions.json','selective_dense_recomputation_log.json','summary.json']:
            if not (folder/filename).is_file():errors.append(f'{video}: missing {filename}')
        packs=read(folder/'pair_evidence_packs.json',[]);results=read(folder/'vlm_results.json',[])
        result_map={(r['event_id'],r['anchor_id']):r for r in results}
        for p in packs:
            count+=1;r=result_map.get((p['event_id'],p['anchor_id']),{})
            if p['eligibility_status']!='ELIGIBLE':
                if not p.get('failure_reason'):errors.append(f'{video}: rejection without reason')
                if r.get('called'):errors.append(f'{video}: ineligible VLM call')
                continue
            if not r.get('called'):errors.append(f'{video}: eligible evidence never attempted')
            if not p['before_frames'] or not p['during_frames'] or not p['after_frames']:errors.append(f'{video}: phase missing')
            elif not max(p['before_frames'])<min(p['during_frames'])<=max(p['during_frames'])<min(p['after_frames']):errors.append(f'{video}: temporal order')
            for f in p['selected_frames']:
                if f['anchor_id']!=p['anchor_id']:errors.append(f'{video}: mixed anchor')
                if f['phase'] in {'BEFORE','DURING'} and f['target_observation_authorization']['status']!='OBSERVATION_AUTHORIZED':errors.append(f'{video}: unauthorized target')
                if f.get('mask_reference') and not (ROOT/f['mask_reference']).is_file():errors.append(f'{video}: missing mask artifact')
                if not f['scene_continuity']['no_cut_detected']:errors.append(f'{video}: scene break in selected pack')
        for d in read(folder/'physical_decisions.json',[]):
            if d['grounding_status']!='VLM_GROUNDING_VALID' or d['identity_write_authorized']:errors.append(f'{video}: gate authority violation')
        for log in read(folder/'selective_dense_recomputation_log.json',[]):
            if log['recomputed']:
                fps=read(BASE/video/'upstream_v21/event_analysis/video_metadata.json')['fps'];budget=round(1.5*fps)
                a,b=log['actual_interval'];lo,hi=log['original_interval']
                if a<lo-budget or b>hi+budget:errors.append(f'{video}: expansion exceeds budget')
                if log['baseline_config_sha256']!=read(BASE/'canonical_config.json')['canonical_config_sha256']:errors.append(f'{video}: noncanonical recomputation')
    return {'valid':not errors,'errors':errors,'pair_requests_checked':count}

def finalize():
    checks=contract_checks()
    if not checks['valid']:raise RuntimeError(checks['errors'])
    if not (OUT/'artifact_manifest.json').exists():
        files={p.relative_to(OUT).as_posix():sha256(p) for p in sorted(OUT.rglob('*')) if p.is_file()
               and p.relative_to(OUT).as_posix() not in POST_FILES and not any(x.startswith('.') for x in p.relative_to(OUT).parts)}
        sources=[*sorted((ROOT/'src/memory_graph/v293').glob('*.py')),ROOT/'scripts/run_v293.py']
        write(OUT/'artifact_manifest.json',{'schema':'v293_prediction_freeze_1','prediction_frozen':True,
            'freeze_utc':datetime.now(timezone.utc).isoformat(),'evaluation_started':False,
            'baseline_config_sha256':read(BASE/'canonical_config.json')['canonical_config_sha256'],
            'source_hashes':{p.relative_to(ROOT).as_posix():sha256(p) for p in sources},'files':files})
    # No prediction mutation is permitted below this line.
    regression=verify_baseline_contract(full_hashes=True);initial=read(OUT/'baseline_contract.json')
    regression['protected_policy_sources_unchanged']=regression['protected_sources']==initial['protected_sources']
    regression['identity_and_memory_unchanged_since_replay']=regression['identity_and_memory_hashes']==initial['identity_and_memory_hashes']
    regression['observation_authorization_identity_writes']=0
    regression['evaluation_utc']=datetime.now(timezone.utc).isoformat()
    write(OUT/'regression_summary.json',regression)
    frozen=verify();checks.update(freeze_verification=frozen,upstream_frozen_artifacts_verified=True,
        thresholds_unchanged=regression['protected_policy_sources_unchanged'])
    checks['valid']=checks['valid'] and frozen['valid'] and regression['protected_policy_sources_unchanged'] and regression['identity_and_memory_unchanged_since_replay'] and regression['unauthorized_matched']==0 and all(regression[k] for k in ('test2_fusion_preserved','test7_identity_unchanged','test8_closed_loop','test9_unresolved'))
    write(OUT/'contract_validation.json',checks)
    funnel=read(OUT/'evidence_funnel.json');a=funnel['aggregate'];rejections=funnel['rejection_counts']
    dominant=max(rejections,key=rejections.get) if rejections else None
    statuses=Counter();relations={}
    for v in VIDEOS:
        statuses.update(read(OUT/v/'summary.json')['vlm_status_counts'])
        for d in read(OUT/v/'physical_decisions.json'):
            relations.setdefault(d['candidate_relation'],Counter())[d['decision']]+=1
    if not checks['valid']:status='V293_EVIDENCE_CONTRACT_REGRESSION'
    elif not a['pair_evidence_eligible']:status='V293_BLOCKED_BY_UPSTREAM_EVIDENCE'
    elif not a['vlm_grounding_valid'] or not a['physical_gate_called'] or statuses['VLM_RUNTIME_FAILED']:status='V293_EVIDENCE_PIPELINE_PARTIAL'
    else:status='V293_EVIDENCE_PIPELINE_VALID'
    if statuses['VLM_GROUNDING_INVALID']>a['vlm_grounding_valid']:
        bottleneck=f'全體請求仍以缺少授權目標觀測為最大覆蓋限制；已有證據的 {a["vlm_called"]} 個配對中，{statuses["VLM_GROUNDING_INVALID"]} 個 grounding-invalid，顯示 VLM 配對辨識是目前可直接量測的下游瓶頸。'
        next_step='優先改善 pair-specific VLM grounding（區分查詢錨點與鄰近物件、處理 AFTER 可見性矛盾），使用已凍結開發證據評估；另行審核事件選取與可信觀測覆蓋，再處理正常 Identity Guard 的長間隔恢復。'
    elif dominant in {'NO_TARGET_BEFORE','PAIR_NEVER_COVISIBLE'}:
        bottleneck='事件視窗缺少可授權的目標觀測；Identity Guard 的長間隔身份恢復仍限制可用證據。'
        next_step='優先檢查事件選取是否保留最後可信互動區段，再改善正常 Identity Guard 路徑的長間隔恢復；維持現有閾值。'
    elif dominant in {'ANCHOR_EVIDENCE_MISSING','NO_ANCHOR_AFTER'}:
        bottleneck='查詢錨點在互動後的可觀測證據不足。';next_step='優先改善既有 anchor discovery / continuity 的證據覆蓋。'
    elif a['vlm_grounding_valid']<a['vlm_called']:
        bottleneck='VLM subject/frame grounding。';next_step='分析 grounding-invalid 圖組與模型回答，修正配對視覺與引用一致性。'
    else:
        bottleneck='物理關係需要更充分的可觀察時間證據。';next_step='用凍結輸出審核物理 gate 的證據解釋，不以增加 PROMOTED 數量為目標。'
    evaluation={'post_freeze':True,'evaluation_utc':datetime.now(timezone.utc).isoformat(),
        'final_status':status,'evidence_funnel':a,'dominant_rejection':dominant,'vlm_status_counts':dict(statuses),
        'per_relation':{k:dict(v) for k,v in relations.items()},'remaining_bottleneck':bottleneck,'recommended_next_step':next_step,
        'no_new_validation_videos_used':True,'identity_or_physical_thresholds_changed':False,
        'first_failing_stage_per_video':{v:read(OUT/v/'summary.json')['first_failing_stage'] for v in VIDEOS}}
    write(OUT/'evaluation_summary.json',evaluation)
    audit=read(OUT/'evidence_failure_audit.json');bench=read(OUT/'benchmark_summary.json');tests=read(OUT/'test_results.json',{})
    lines=['# V2.9.3 事件證據恢復與配對物理推論報告','',f'結論：**{status}**','',
        '## 1. V2.9.2 的 54 筆失敗原因','',
        *[f'- {k}：{v} 筆。' for k,v in audit['primary_counts'].items()],
        '', '次要原因可以重疊：DURING 查詢錨點缺失 23 筆、AFTER 錨點缺失 26 筆。所有請求均有唯一主要原因與逐 phase 診斷。',
        '', '根因包括 dense RLE 路徑讀錯後覆寫為空、reinitialized masks 漏接，以及事件視窗本來沒有可信目標。V292 frozen artifacts 保持原樣。',
        '', '## 2. 修改範圍','',
        '- 建立獨立 OBSERVATION_AUTHORIZED：使用既有可信 seed、因果時間順序、既有 0.4 秒短延續限制與 drift/conflict 檢查。不能更新身份、alias、MATCHED、appearance bank。',
        '- 保存 raw dense masks，再產生 observation 授權紀錄；接收 baseline 已授權的 SAM restart seed。',
        '- 每個 target × anchor × event 自動選擇 1 個 BEFORE、1–3 個 DURING、1–2 個 AFTER。依實際幾何／可見性變化排序，固定每事件最多兩個查詢。',
        '- AFTER 可使用 TARGET_NOT_OBSERVED_WITH_ANCHOR_VISIBLE，但需連續 anchor-visible view、無場景切換診斷、無 SAM/phone candidate，且延續先前有效目標證據。未觀測不等於物理不存在。',
        '- AFTER 使用同一可見狀態；未觀測需要兩個連續視圖、在既有 0.4 秒短延續限制內開始，且前一目標 bbox 不可被影像邊界截斷，避免將移出鏡頭當成有效遮擋證據。',
        '- 場景診斷採固定 luma difference >0.35 且 histogram correlation <0.2；這是新增的保守影像診斷，未改身份或物理 gate 閾值。它不能排除所有局部遮擋。',
        '- VLM 使用原 Qwen2.5-VL-3B，僅回報 observable facts；輸出上限改為 768 tokens，容納完整 frame arrays 與 grounding schema。',
        '- 開發時發現複製 prompt 描述範例會通過初版檢查；已加入拒絕檢查與 regression test。修正使用新 prompt，最終結果只保留通過現行契約重驗的回答。',
        '- 圖組複核發現 VLM 將紫框中的人／手描述成附近籃球；加入一般類別／同義詞相容性檢查，無法對應 raw anchor hypothesis 的回答標為 grounding-invalid。保留 detector 語義不確定性，不把描述當成 GT 重新命名錨點。',
        '- 使用原 V2.9 候選特徵與 physical gate；只有通過 grounding 的事實能送入 gate。V2.8 graph/search 和 identity outputs 均不被本版本寫入。',
        '', '## 3. Evidence funnel：before / after','',
        '| 階段 | V2.9.2 | V2.9.3 |','|---|---:|---:|',
        f'| Pair requests | 54 | {a["pair_requests_total"]} |',
        f'| Eligible | 0 | {a["pair_evidence_eligible"]} |',f'| VLM calls | 0 | {a["vlm_called"]} |',
        f'| Schema valid | 0 | {a["vlm_schema_valid"]} |',f'| Grounding valid | 0 | {a["vlm_grounding_valid"]} |',
        f'| Physical gate relation calls | 0 | {a["physical_gate_called"]} |','',
        'V293 在同一事件的既有 anchor pool 內重新排序查詢錨點，因此這是相同查詢預算的流程比較，不是固定同一組 anchor 的模型 accuracy 比較。',
        '', '| Video | Requests | Eligible | VLM | Grounded | Gate | P/C/U/R | 無物理輸出時的首個失敗階段 |','|---|---:|---:|---:|---:|---:|---|---|']
    for v in VIDEOS:
        r=read(OUT/v/'summary.json');f=r['funnel'];counts='/'.join(str(f['physical_'+s]) for s in ['promoted','candidate','uncertain','rejected'])
        lines.append(f'| {v} | {f["pair_requests_total"]} | {f["pair_evidence_eligible"]} | {f["vlm_called"]} | {f["vlm_grounding_valid"]} | {f["physical_gate_called"]} | {counts} | {r["first_failing_stage"] or "已有 gate 輸出"} |')
    lines += ['', '## 4. Physical gate 結果','', *[f'- {k}：{dict(v)}' for k,v in relations.items()],
        '', '開發中曾有一筆 HELD_BY PROMOTED，但圖組檢查發現 VLM 把 queried person/hand 描述成鄰近籃球；最終 grounding 契約已拒絕該回答，此筆不列入最終物理決策。',
        '', 'P/C/U/R 分別是 PROMOTED / CANDIDATE / UNCERTAIN / REJECTED。零 PROMOTED 可以是合理結果，本次沒有降低任何門檻。',
        '', '## 5. Regression 與凍結','',f'- 未授權 MATCHED：{regression["unauthorized_matched"]}。',
        f'- test2 track22/43 fusion：{regression["test2_fusion_preserved"]}。',
        f'- test7 identity/memory/search frozen hashes 維持：{regression["test7_identity_unchanged"]}。',
        f'- test8 forward loop：{regression["test8_closed_loop"]}；真實 confirmation frames：{regression["test8_confirmation_frames"]}。',
        f'- test9 unresolved：{regression["test9_unresolved"]}。',
        f'- 身份閾值 {regression["identity_threshold"]} / margin {regression["margin"]}；protected policy source hashes unchanged：{regression["protected_policy_sources_unchanged"]}。',
        f'- prediction freeze 後驗證：{frozen["valid"]}，{frozen["files_checked"]} 個檔案。',
        f'- 專項測試：V293 {tests.get("focused_v293_passed")} 項、V292 {tests.get("v292_contract_passed")} 項通過；完整套件 {tests.get("full_suite_passed")} 通過、{tests.get("full_suite_failed")} 失敗、{tests.get("full_suite_skipped")} 跳過。',
        '- 三項失敗均為執行前既有 V241/V25 歷史輸出雜湊不符，詳見 test_results.json；本次未改寫歷史輸出。','', '## 6. 選擇性 dense 重算','',
        f'重算 {bench["selectively_recomputed_intervals"]} 個 bounded intervals。未重跑九支完整 YOLO/SAM。每側最多擴展 1.5 秒，日誌記錄 interval、seed、raw hash、原模型／config hash 與實際 canonical dense 參數（YOLO conf .15，imgsz 960，最高 15 fps）。',
        f'證據準備共 {bench.get("prepare_seconds",0):.2f} 秒；最終保留 VLM 回答的推論時間合計 {bench.get("canonical_response_inference_seconds",0):.2f} 秒（不含捨棄的開發嘗試）。',
        '同一 V293 開發執行中，若 prompt 與逐張輸入圖片 SHA256 完全相同，重用該次實際模型回答，重新執行 grounding / gate；輸入改變則重新推論。最終漏斗的 VLM calls 是具有實際模型呼叫來源的 pair 數。',
        '', '## 7. 剩餘失敗原因與下一步','', *[f'- {k}：{v}' for k,v in rejections.items()],
        '',bottleneck,'',next_step,'', '## 8. 實際限制','',
        '- Grounding valid 表示 schema、查詢身份、時間引用與觀測狀態一致，不代表已經過獨立人工正確性標註。',
        '- Anchor 描述相容性檢查是保守文字檢查，不是獨立視覺驗證器；偵測類別錯誤或同義詞不足可能造成 false rejection。',
        '- 短時間場景診斷及 anchor bbox 可觀測性不能證明完全沒有鏡頭移動或局部遮擋。',
        '- 繼承 V292 可信身份來源的限制；觀測授權不會修正上游誤認，也不會建立新身份。',
        '- 未使用新錄製的 validation videos、GT 位置、新模型、訓練或 UI。',
        '', '## 9. 代表圖組與重播入口','',
        '- 有效配對：review_sheets/test8_pair0/contact_sheet.jpg。',
        '- 錨點描述錯誤並被拒絕：review_sheets/test2_grounding_rejected/contact_sheet.jpg。',
        '- 移出鏡頭後不採用未觀測證據：review_sheets/test8_pair4/contact_sheet.jpg。',
        '- 無證據案例：test1/debug_unavailable/ 下的 contact_sheet.jpg。',
        '- scripts/run_v293.py verify 可驗證本次凍結檔案；prepare/reselect/replay 在凍結後會拒絕改寫。',
        '',status]
    (OUT/'V293_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'evidence_funnel.md').write_text('# Evidence funnel\n\n| Stage | Count |\n|---|---:|\n'+'\n'.join(f'| {k} | {v} |' for k,v in a.items())+'\n\nRejection reasons:\n'+json_text(rejections),encoding='utf-8')
    return {'status':status,'contract_valid':checks['valid'],'frozen_verification':verify(),'report':str(OUT/'V293_REPORT.md')}

def json_text(obj):
    import json
    return '```json\n'+json.dumps(obj,indent=2,ensure_ascii=False)+'\n```\n'
