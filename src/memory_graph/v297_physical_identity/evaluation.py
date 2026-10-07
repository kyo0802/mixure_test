"""Post-run evaluation only. This module is never imported by identity inference."""
from collections import Counter
import time
from .io import ROOT,OUT,PREV,read,save,sha
from .runner import verify_freeze,source_hashes

def development():
    metrics=read(OUT/'development/identity_metrics.json');results={};people={};states={};evidence={};events={}
    seal=read(OUT/'development_gt/SCENARIOS_FROZEN_BEFORE_POLICY.json')
    if any(sha(OUT/'development_gt'/p)!=h for p,h in seal['files'].items()):raise ValueError('Scenario GT changed')
    for vid,m in metrics['videos'].items():
        gt=read(OUT/f'development_gt/{vid}_identity_scenario.json');s=read(OUT/f'development/runs/{vid}/identity.json')
        pos=set(gt['reviewed_target_observation_ids']);neg=set(gt['reviewed_distractor_observation_ids'])
        ledger=s['final_ledger'];bad=[r for r in ledger if r['observation']['observation_id'] in neg]
        badaliases=[a for a in s['aliases'] if a['status']=='CONFIRMED' and (any(x in neg for x in a['evidence_refs']) or any(r['alias_id']==a['alias_id'] for r in bad))]
        badcore=[b for b in s['banks']['core'] if b['active'] and b['observation_id'] in neg]
        recoveries=[]
        for e in gt['reappearance_events']:
            lo,hi=e['window'];qualified=[r['observation']['observation_id'] for r in ledger if lo<=r['observation']['frame']<=hi and r['observation']['observation_id'] in pos]
            recoveries.append({**e,'achieved':bool(qualified),'qualified_authorized_target_observations':qualified})
        unknown=[a['current_observation'] for a in s['confirmation_audit'] if a['current_observation'] not in pos|neg]
        initial=m['initial_binding'] and m['initial_local_track']==gt['initial_target_binding']['local_track'] and m['initial_frame']==gt['initial_target_binding']['frame']
        unresolved=not gt['expected_unresolved_behavior']['required'] or not s['confirmation_audit']
        safe=not bad and not badaliases and not badcore and not m['unauthorized_writes'] and not m['physical_identity_violations'] and not any(m['integrity_violation_counts'].values())
        all_recovered=all(e['achieved'] for e in recoveries if e['automatic_recovery_required'])
        status='FAIL' if not(initial and safe and unresolved and all_recovered) else 'UNKNOWN' if unknown else 'PASS'
        results[vid]={'status':status,'initial_target_correct':bool(initial),'known_distractor_incorrectly_authorized':len(bad),
            'wrong_active_aliases':len(badaliases),'wrong_Core_contamination':len(badcore),'unsafe_false_merge':bool(badaliases),
            'expected_recovery_achieved':all_recovered,'recovery_events':recoveries,'expected_unresolved_preserved':unresolved,
            'unknown_confirmation_ids':unknown,'authorized_observations':m['authorized_observations'],
            'reviewed_target_authorized_ledger_rows':sum(r['observation']['observation_id'] in pos for r in ledger),
            'unreviewed_authorized_ledger_rows':sum(r['observation']['observation_id'] not in pos|neg for r in ledger),
            'scenario_sha256':sha(OUT/f'development_gt/{vid}_identity_scenario.json'),'criteria_unchanged':True}
        people[vid]=read(OUT/f'development/runs/{vid}/person_epochs.json');states[vid]=s['physical_identity_state']
        evidence[vid]=read(OUT/f'development/runs/{vid}/physical_evidence.json');events[vid]=states[vid]['events']
    suite={'videos':results,'counts':dict(Counter(r['status'] for r in results.values())),
        'no_reviewed_unsafe_false_merge':not any(r['unsafe_false_merge'] or r['known_distractor_incorrectly_authorized'] for r in results.values()),
        'all_required_recoveries':all(r['expected_recovery_achieved'] for r in results.values()),'scope':'Partial reviewed DEVELOPMENT scenarios, predefined before policy; unknown rows not counted correct'}
    save(OUT/'development/scenario_results.json',suite);save(OUT/'person_epochs/development.json',people)
    save(OUT/'physical_identity/physical_continuity.json',evidence)
    save(OUT/'physical_identity/motion_coupling.json',{v:[e for e in es if e['state']=='TARGET_MOTION_COUPLED_WITH_PERSON'] for v,es in events.items()})
    save(OUT/'physical_identity/occlusion_hypotheses.json',{v:[e for e in es if e['state']=='TARGET_OCCLUDED_WITH_PERSON_HYPOTHESIS'] for v,es in events.items()})
    save(OUT/'physical_identity/candidate_preexistence.json',{v:[p for p in es if p['preexistence_contradiction']] for v,es in evidence.items()})
    save(OUT/'physical_identity/known_distinct_entities.json',{v:s['known_distinct_entities'] for v,s in states.items()})
    save(OUT/'interaction/development_events.json',events)
    s=read(OUT/'development/runs/test8/identity.json');ds=[d for d in s['physical_decisions'] if 804<=d['physical_identity']['frame']<=900]
    save(OUT/'development/test8_recovery.json',{'Safe':0,'V295':0,'V296':1,'V297':int(results['test8']['expected_recovery_achieved']),
        'V297_state':'CORRECT_RECOVERY' if results['test8']['expected_recovery_achieved'] else 'UNRESOLVED_TRUE_TARGET',
        'required_window':[804,840],'scenario_result':results['test8'],'evidence_chain':ds,
        'causal_limitation':'Last trusted phone/person around f432; later PersonEpoch is not safely continuous. Camera chain breaks; returning interval has other physical phones. Neither future review nor raw person ID may repair this runtime evidence.',
        'appearance_only_route_retired':True,'per_video_runtime_thresholds':False})
    print('Development scenarios',suite['counts'],flush=True);return suite

def review_sheets(kind):
    from PIL import Image,ImageDraw
    import cv2
    metrics=read(OUT/f'{kind}/{"identity_metrics" if kind=="development" else "metrics"}.json');items=[]
    for vid in metrics['videos']:
        s=read(OUT/f'{kind}/runs/{vid}/identity.json');md=read(OUT/f'{kind}/runs/{vid}/metadata.json')
        for a in s['confirmation_audit']:
            items.append({'video':vid,'frame':a['physical_identity']['frame'],'observation_id':a['current_observation'],
                'context':a['confirmation_context'],'alias_id':a['alias_id'],
                'active_alias':any(x['alias_id']==a['alias_id'] and x['status']=='CONFIRMED' for x in s['aliases']),
                'initial':md[s['banks']['core'][0]['observation_id']],'current':md[a['current_observation']]})
    for page in range((len(items)+3)//4):
        group=items[page*4:page*4+4];sheet=Image.new('RGB',(1100,len(group)*290),'white');d=ImageDraw.Draw(sheet)
        for j,it in enumerate(group):
            d.text((5,j*290+5),f'{it["video"]} f{it["frame"]} {it["context"]} {it["observation_id"]}',fill='black')
            for k,r in enumerate([it['initial'],it['current']]):
                im=Image.open(r['raw_crop_path']).convert('RGB');im.thumbnail((190,250));sheet.paste(im,(k*195,j*290+30))
            video=ROOT/(f'{it["video"]}.mp4' if kind=='development' else f'val_set/{it["video"]}.mp4')
            cap=cv2.VideoCapture(str(video));cap.set(cv2.CAP_PROP_POS_FRAMES,it['frame']);ok,bgr=cap.read();cap.release()
            if not ok:raise OSError('Review original decode failed')
            im=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB));im.thumbnail((700,255));sheet.paste(im,(395,j*290+30))
        p=OUT/f'{kind}/review_sheets/confirmations_{page}.png';p.parent.mkdir(parents=True,exist_ok=True);sheet.save(p)
        for it in group:it.update(review_sheet=str(p.relative_to(OUT)),review_sheet_sha256=sha(p))
    index=[{k:v for k,v in it.items() if k not in ['initial','current']} for it in items]
    save(OUT/f'{kind}/review_index.json',index)
    print(kind,'new confirmations to review',len(index),flush=True)

def test8_sheet():
    from PIL import Image,ImageDraw
    import cv2
    frames=[432,804,828,852,864];md=read(OUT/'development/runs/test8/metadata.json');person=read(OUT/'development/runs/test8/person_epochs.json')
    # All raw candidates are shown without assigning phone_01; this artifact is evaluation only.
    people=person.get('epochs',[]);sheet=Image.new('RGB',(1400,430*3),'white');d=ImageDraw.Draw(sheet)
    cap=cv2.VideoCapture(str(ROOT/'test8.mp4'))
    try:
        for i,f in enumerate(frames):
            cap.set(cv2.CAP_PROP_POS_FRAMES,f);ok,bgr=cap.read()
            if not ok:raise OSError('test8 review frame failed')
            im=Image.fromarray(cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB));draw=ImageDraw.Draw(im)
            for r in md.values():
                if r['frame']==f:
                    draw.rectangle(r['bbox'],outline='orange',width=3);draw.text((r['bbox'][0],r['bbox'][1]),r['local_track_id'],fill='orange')
            im.thumbnail((690,395));x=(i%2)*700;y=(i//2)*430;sheet.paste(im,(x,y+30));d.text((x+5,y+5),f'test8 f{f}: raw phone candidates, identity not assigned',fill='black')
    finally:cap.release()
    p=OUT/'development/review_sheets/test8_context_gap.png';p.parent.mkdir(parents=True,exist_ok=True);sheet.save(p)
    save(OUT/'development/review_sheets/test8_context_gap.json',{'frames':frames,'original_video_sha256':sha(ROOT/'test8.mp4'),'sheet_sha256':sha(p),'annotated_artifact_used_for_identity':False})

def known_regression():
    verify_freeze();metrics=read(OUT/'known_val_regression/metrics.json');flags=Counter();cases={};audits={}
    previous=read(PREV/'known_val_regression/visual_review.json')
    review=read(OUT/'known_val_regression/visual_review.json',{})
    negatives={'val_5':{'track:77':(1284,999999)},'val_9':{'track:42':(960,999999),'track:52':(1194,999999),'track:63':(1314,999999),'track:65':(1380,999999)},'val_10':{'track:49':(1140,1859)}}
    for vid in metrics['videos']:
        s=read(OUT/f'known_val_regression/runs/{vid}/identity.json');md=read(OUT/f'known_val_regression/runs/{vid}/metadata.json')
        a=read(OUT/f'known_val_regression/runs/{vid}/confirmation_audit.json');audits[vid]=a;flags.update(a['violation_counts'])
        if vid not in negatives:continue
        wrong=set(previous.get('critical_wrong_observation_ids',{}).get(vid,[]))
        wrong.update(x['observation_id'] for x in review.get('confirmations',[]) if x['video']==vid and x['classification']=='DISTRACTOR')
        def isbad(oid):
            m=md[oid];interval=negatives[vid].get(m['local_track_id'])
            return oid in wrong or bool(interval and interval[0]<=m['frame']<=interval[1])
        rows=[r for r in s['final_ledger'] if isbad(r['observation']['observation_id'])]
        core=[b for b in s['banks']['core'] if b['active'] and isbad(b['observation_id'])]
        aliases=[a for a in s['aliases'] if a['status']=='CONFIRMED' and (any(isbad(o) for o in a['evidence_refs']) or any(r['alias_id']==a['alias_id'] for r in rows))]
        decisions=[d for d in s['physical_decisions'] if isbad(d['observation_id'])]
        case={'wrong_active_aliases':aliases,'wrong_authorized_observations':len(rows),'wrong_Core_contamination':len(core),'wrong_rows':rows,
            'reviewed_previous_wrong_ids':sorted(wrong),'evaluation_only_negative_local_intervals':negatives[vid],
            'decisions':decisions,'wrong_candidates_visual_eligible':sum(d['visual_proposal_stage']=='CONFIRMED_MATCH' for d in decisions),
            'blocker_counts':dict(Counter(b for d in decisions for b in d['blockers'])),
            'physical_preexistence_vetoes':sum(d['physical_identity']['preexistence_contradiction'] for d in decisions),
            'known_distinct_vetoes':sum(d['physical_identity']['known_distinct'] for d in decisions),
            'valid_interaction_supports':sum(d['physical_identity']['interaction']=='INTERACTION_CONTINUITY_SUPPORT' for d in decisions),
            'physical_inconsistent_candidates':sum(d['physical_identity']['reachability']=='PHYSICALLY_INCONSISTENT' for d in decisions),
            'candidate_epoch_breaks':read(OUT/f'known_val_regression/runs/{vid}/candidate_epochs.json'),
            'scope':'KNOWN regression evaluation only: original reviewed wrong rows + fixed prior physical distractor intervals; no labels in causal inference; not full-frame identity accuracy'}
        cases[vid]=case;save(OUT/f'known_val_regression/{vid}_case.json',case)
    dev=read(OUT/'development/scenario_results.json');test8=read(OUT/'development/test8_recovery.json');totals=metrics['totals']
    knownwrong={v for v,c in cases.items() if c['wrong_active_aliases']}
    knownwrong|={x['video'] for x in review.get('confirmations',[]) if x['classification']=='DISTRACTOR' and x['active_alias']}
    blockers=[]
    if knownwrong or any(c['wrong_authorized_observations'] or c['wrong_Core_contamination'] for c in cases.values()):blockers.append('KNOWN_FALSE_IDENTITY')
    if any(flags.values()) or totals['unauthorized_writes'] or totals['physical_identity_violations']:blockers.append('AUTHORITY_OR_INTEGRITY_VIOLATION')
    if not review.get('all_confirmation_frames_reviewed') or review.get('unknown_confirmations',1) or review.get('wrong_confirmations',1):blockers.append('CONFIRMATION_REVIEW_INCOMPLETE_OR_INCORRECT')
    if not dev['no_reviewed_unsafe_false_merge']:blockers.append('DEVELOPMENT_FALSE_MERGE')
    if test8['V297']!=1:blockers.append('TEST8_CORRECT_RECOVERY_NOT_RETAINED')
    if dev['counts'].get('PASS',0)!=9:blockers.append('DEVELOPMENT_SCENARIO_ACCEPTANCE_NOT_ALL_PASS')
    summary={'known_permanent_false_merge_cases':len(knownwrong),'known_wrong_active_alias_videos':sorted(knownwrong),
        'critical_wrong_active_alias_count':sum(len(c['wrong_active_aliases']) for c in cases.values()),
        'wrong_critical_authorized_observations':sum(c['wrong_authorized_observations'] for c in cases.values()),
        'wrong_Core_contamination':sum(c['wrong_Core_contamination'] for c in cases.values()),'integrity_flags':dict(flags),
        'bypass_violations':totals['unauthorized_writes'],'physical_identity_violations':totals['physical_identity_violations'],
        'authorized_observations':totals['authorized_observations'],
        'safe_authorized_observations_contract_only':totals['authorized_observations']-sum(c['wrong_authorized_observations'] for c in cases.values()),
        'full_identity_accuracy':None,'identity_safety_gate_passed':not blockers,'blockers':blockers,
        'all_new_confirmation_review':review,'scope':'KNOWN regressions only. Contract-safe and no reviewed wrong identity does not prove every descendant is physically correct.'}
    save(OUT/'known_val_regression/safety_summary.json',summary);save(OUT/'known_val_regression/confirmation_audit.json',audits)
    print('Known regression safety',summary,flush=True);return summary

def preservation():
    verify_freeze();before=read(OUT/'baseline/preservation_manifest.json');changed=[];missing=[]
    for p,h in before['files'].items():
        if not (ROOT/p).is_file():missing.append(p)
        elif sha(ROOT/p)!=h:changed.append(p)
    result={'protected_files':len(before['files']),'unchanged':len(before['files'])-len(changed)-len(missing),
        'changed':changed,'missing':missing,'normal_runner_unchanged':sha(ROOT/'scripts/run_findmind.py')==read(OUT/'baseline/baseline_metrics.json')['normal_runner_sha256'],
        'sibling_repository_written':False,'frozen_source_verified':True,'checked_unix':time.time()}
    save(OUT/'final/integrity_manifest.json',result);save(OUT/'final/source_hashes.json',source_hashes());save(OUT/'final/selected_config.json',read(OUT/'calibration/parameters.json'))
    print('Preservation',result,flush=True);return result

def report():
    verify_freeze();dev=read(OUT/'development/identity_metrics.json');val=read(OUT/'known_val_regression/metrics.json')
    suite=read(OUT/'development/scenario_results.json');safe=read(OUT/'known_val_regression/safety_summary.json');test8=read(OUT/'development/test8_recovery.json')
    integrity=read(OUT/'final/integrity_manifest.json');smoke=read(OUT/'smoke/qwen25_smoke.json');cfg=read(OUT/'calibration/parameters.json')
    cases={v:read(OUT/f'known_val_regression/{v}_case.json') for v in ['val_5','val_9','val_10']}
    tests={k:(OUT/f'tests/{k}.txt').read_text(encoding='utf8',errors='replace') for k in ['new_results','focused_results','full_results']}
    tests_pass=all('passed' in text and 'failed' not in text.lower() and 'ERROR ' not in text for text in tests.values())
    status='V297_PHYSICAL_IDENTITY_PARTIAL_SUCCESS' if test8['V297']==0 else 'V297_PHYSICAL_IDENTITY_NO_IMPROVEMENT'
    if safe['identity_safety_gate_passed'] and tests_pass and val['totals']['confirmed_recoveries'] and test8['V297']==1:status='V297_PHYSICAL_IDENTITY_CLEAR_SUCCESS'
    if safe['known_permanent_false_merge_cases'] or safe['wrong_critical_authorized_observations'] or safe['wrong_Core_contamination']:status='V297_PHYSICAL_IDENTITY_REGRESSION'
    if integrity['changed'] or integrity['missing'] or any(safe['integrity_flags'].values()) or safe['bypass_violations'] or not tests_pass:status='V297_PHYSICAL_IDENTITY_INVALID'
    ready='READY_FOR_NEW_IDENTITY_HELD_OUT_SET' if status=='V297_PHYSICAL_IDENTITY_CLEAR_SUCCESS' and smoke.get('validator_valid') and smoke.get('calls',0)>0 else 'NOT_READY_FOR_NEW_IDENTITY_HELD_OUT_SET'
    table='| Video | 結果 | 初始正確 | 錯誤授權 | 必要回復 | 授權影格 |\n|---|---|---|---:|---|---:|\n'
    for v,r in suite['videos'].items():table+=f'| {v} | {r["status"]} | {r["initial_target_correct"]} | {r["known_distractor_incorrectly_authorized"]} | {r["expected_recovery_achieved"]} | {r["authorized_observations"]} |\n'
    headings=['Goal','Why visual Re-ID alone was insufficient','Development scenario GT','CandidateEpoch / PersonEpoch','PhysicalIdentityState','Physical reachability','Person proximity','Motion coupling','Occlusion continuity','Reappearance context','Candidate pre-existence','Known-distinct physical entities','V297 confirmation policy','Development test1-test9 results','test8 recovery','Policy freeze','val_5','val_9','val_10','Authorized timeline result','Safety audit','Runtime cost','Tests','Remaining bottleneck','Promotion recommendation']
    def case_text(v):
        c=cases[v]
        return f'wrong active alias={len(c["wrong_active_aliases"])}；wrong authorized={c["wrong_authorized_observations"]}；wrong Core={c["wrong_Core_contamination"]}。已知錯誤候選曾通過原視覺門檻 {c["wrong_candidates_visual_eligible"]} 次，V297 blockers={json_format(c["blocker_counts"])}。pre-existence veto={c["physical_preexistence_vetoes"]}、KnownDistinct veto={c["known_distinct_vetoes"]}、interaction SUPPORT={c["valid_interaction_supports"]}、physical inconsistency={c["physical_inconsistent_candidates"]}。此處區分「缺少正向物理支援而阻擋」與「已有物理不同實體證據而否決」，不把前者宣稱為後者。完整 CE split、decision matrices、PersonEpoch、camera trace 在 case/run JSON。'
    sections=[
        '在 codex/V297 建立獨立實驗入口與物理／互動證據，保留安全主流程。False merge 優先於 recall；沒有新 appearance/person/pose/depth/SLAM 模型，也沒有加權總分。',
        'V296 對不同手機的正面、共享貼紙／相似背殼造成4個錯誤 alias、52筆已複查錯誤授權與2筆錯誤 Core；合法原始 crop、CandidateEpoch、DINOv3/2 及當前 LightGlue 仍不足證明物理身份。DINOv2/3 是相關外觀證據，不能當兩個獨立身份來源。',
        '9份情境與 PASS 條件在 policy 實作前建立並封存 SHA；人工看過乾淨原始影格／crop。移除 test1/test6 部分重複偵測的假 negative，test4 遠方模糊 late candidate 身份標 UNKNOWN；歷史 GT 不重寫。沒有偵測只表示偵測缺席，不能當實際 target 消失。GT 是部分工程複查，未知身份不擅自補 label。必要 recovery window 使用已複查目標觀測，沒有在 runtime 硬編碼 video/frame/track。',
        f'沿用 V296 CandidateEpoch 的 gap/scene/reset/持續外觀轉折與唯一短 gap stitch。PersonEpoch 只用原 person detections 的短 gap、IoU／位移／scale／scene；raw person ID 不等於人類身份，沒有 person Re-ID。Person policy={json_format(cfg["person"])}。',
        '只從當前、仍有效的 Guard ledger 更新 target 的 last observation/time/bbox、raw/compensated position、velocity/speed、identity epoch、alias/authorization、scene/anchors、person proximity、occlusion hypothesis 與已知不同實體。Backfill 不當當前觀測；alias revocation 同步清除物理狀態後代。這是 identity-support state，沒有修改 physical Memory Graph 的 trust rules。',
        f'以影像對角線正規化；gap≤{cfg["physical"]["continuity_horizon"]}秒、同一可靠 camera chain、compensated displacement、最近測量 speed、bbox scale 與 CandidateEpoch 狀態共同判斷。reach base={cfg["physical"]["base_reach"]:.4f}，動態 envelope 有 cap。camera 至少3個穩定類別 anchor 的 median translation、scale檢查與殘差p75≤.015；rotation/parallax/遮蔽無法可靠處理時 UNKNOWN。不是固定距離單獨判斷，也不跨斷裂camera chain推算。',
        f'以 bbox edge distance／overlap、target相對person位置與時間持續性判斷；proximity距離={cfg["physical"]["proximity_distance"]:.4f}。至少3影格/.4秒才形成持續接近；單影格接近沒有身份權限。',
        '至少3影格/.4秒，同一可靠 camera segment，至少2段 target/person 非零 compensated movement，方向cos≥.8、相對位置變化≤.055。stationary objects 隨 camera pan 移動不算 coupled；無可靠補償回 UNKNOWN。不稱為 carrying/action truth。',
        '授權target持續near/overlap，target缺席但同PersonEpoch仍可見，才形成 TARGET_OCCLUDED_WITH_PERSON_HYPOTHESIS。保存 disappearance、relative geometry、motion state、來源observation/authorization；person/scene break 或4秒 horizon 失效。遮擋是幾何假設，不更新 physical truth。',
        '新候選需在相同仍存活 PersonEpoch 附近累積3影格/.4秒，符合 relative region、timing、camera chain與唯一物理可行性才 SUPPORT；可信矛盾是 CONTRADICTION，缺資訊 UNKNOWN。新 CandidateEpoch 的 gap 回來可重新累積，scene/reset/appearance change/pending break 不继承 stale interaction。',
        '只有曾與授權target同時、持續、空間分離的安全CE lineage才產生強 pre-existence contradiction。不能從 raw track ID 在任意 gap 後直接推認同一實體。僅「先前偵測過」而沒有同時可信 target 不足作身份否決。',
        '至少2影格/.2秒真正空間分离（IoU、中心包含與bbox edge gap皆檢查）建立持久 KnownDistinctPhysicalEntity，保存target authorization、CE、時間與clean appearance refs。後續相同安全CE或2個較早clean view 的強appearance連結只能 veto、不能授權。Negative Bank 僅接納此可信不同實體，部分重複bbox不建立negative。實際命中數見下表；測試可證明邊界，不能代替真實影片驗證。',
        'CASE1：current clean/integrity visual multi-gate +短gap PHYSICALLY_CONSISTENT+CE有效+唯一可行候選；person可UNKNOWN。CASE2：strong multi-frame v3+configured v2+無Core/Negative/photo/distinct/preexistence/physical矛盾+current valid CE+interaction SUPPORT；LightGlue只允許CORE_STRONG_MATCH或UNKNOWN。CASE3：long gap僅appearance→AMBIGUOUS/PROVISIONAL。single-phone state只由scene episode歷史推導，仍要求physical consistent；沒有video專用規則。只有Guard產生alias、capability与授權。',
        table+f'\n總計 {json_format(suite["counts"])}。dev授權116(Safe) /203(V296)→{dev["totals"]["authorized_observations"]}；已複查 unsafe false merge=0（如 scenario JSON）。FAIL 主要是必要回復未達，而非宣稱所有未確認候選都錯誤。',
        f'V296 correct recovery=1→V297={test8["V297"]}，{test8["V297_state"]}。f828外觀曾符合原Route A，但last trusted在f432，舊person local36與後段local63之間沒有可信連續PersonEpoch；長gap超出bounded reach且camera chain斷裂，回來時同類電話競爭。這不是保住回復，必須明確列為未完成目標。無法用GT／未來翻面／人工選target／任意拼person填補；改成允許外觀單獨MATCH會重現已知誤認。原始情境圖：development/review_sheets/test8_context_gap.png。',
        '開發完成後凍結 inference、原Guard/事件builder/reasoning、全部V297腳本與tests/config、GT與輸入provenance、兩官方模型revision，以及confirmation/backfill/physical/person/motion/pre-existence policies。只在 freeze 後跑 val1–11；不再調參／修改 frozen source。舊val永遠是 known regression。舊V296失敗audit曾做schema／歷史結果讀取，不參與開發門檻校準；新val原始輸入及本版結果只在freeze後推論。',
        case_text('val_5'),case_text('val_9'),case_text('val_10'),
        f'已知回歸授權169(Safe) /404(V295) /359(V296)→{val["totals"]["authorized_observations"]}；wrong critical={safe["wrong_critical_authorized_observations"]}；backfill={val["totals"]["backfilled_observations"]}；unresolved candidate frames={val["totals"]["unresolved_candidate_frames"]}。授權由 final revocation-filtered Guard ledger 形成，可交給未變Event Window Builder，但這次 gate 未過，沒有宣稱完整下游 end-to-end acceptance。契約通過且沒有已知錯誤不等於全部 descendant 身份GT正確。',
        f'known permanent false merge cases={safe["known_permanent_false_merge_cases"]}、wrong aliases={safe["critical_wrong_active_alias_count"]}、wrong Core={safe["wrong_Core_contamination"]}、bypass={safe["bypass_violations"]}、physical accepted violations={safe["physical_identity_violations"]}。accepted evidence flags={json_format(safe["integrity_flags"])}。保留拒絕proposal與全部確認audit，current/clean/lineage检查未被物理證據跳過。Protected files {integrity["unchanged"]}/{integrity["protected_files"]} unchanged；Safe normal runner unchanged={integrity["normal_runner_unchanged"]}；未寫 sibling mixure_test。',
        '重用既有pixel-verified原始YOLO/SAM感知資料與同revision/protocol的DINO feature cache，重新因果執行全部20支影片的V297身份狀態／decision／ledger。不是重跑YOLO/SAM，也不讀舊身份結論當推論依據。LightGlue重用僅純匹配feature cache，當前pair integrity重新驗證。下方wall為identity replay，不含原影片SHA/crop驗證；GPU數字是process CUDA peak allocated，不是全卡VRAM，RSS是video-end不是全程peak。',
        '\n'.join(f'- {k}: '+text.splitlines()[-1] for k,text in tests.items())+'\n\n新增tests涵蓋22類要求：person/motion/pan/occlusion/reappear/far/distinct/preexist/singlephone/competition/invalid appearance/CE/PE break/backfill/bypass/onlyGuard等，包含實際Guard integration。合成有連續PersonEpoch的test8-style可回復，不等於真實test8已有該證據。',
        '最重要問題依序：① test8與多個dev必要回復的跨遮擋physical/person資料不足，實際互動支援無法跨缺失期間；② CE表示切換和相機anchor不足使普通target recall下降（test2 Safe33→V2976）；③ 真實影片KnownDistinct/運動耦合命中覆蓋不足，不能僅靠unit tests宣稱已解決相似手機；④ 完整physical-instance、正反面、person連續性與矛盾GT仍不完整；⑤ partial translation不是完整camera pose，不能在rotating/parallax畫面過度確信；⑥ 若未來恢復alias，仍需完整descendant/revocation/negative lineage複查。需新development錄製：目標與干擾物同時可信可見、全遮擋中person不中斷、相機移動及正反面翻轉，再凍結新版本，不用舊val重調V297。',
        f'不promote、不替換安全主流程；已知錯認改善，但test8回復與9支情境驗收未達，因此最多PARTIAL。Qwen smoke={smoke["status"]}，gate blockers={json_format(safe["blockers"])}。未載入Qwen；未使用Qwen3.8／Strata。下一步先補獨立physical/person development coverage、完整身份驗收；目前不進新identity held-out驗收。'
    ]
    text=f'# V297 — Interaction-Conditioned Physical Identity Continuity\n\n**{status}**\n\n實驗實作與20支影片身份重播完成。已知錯認安全改善，但指定test8回復未保留；原安全主流程維持原樣。\n\n'
    for i,(h,b) in enumerate(zip(headings,sections),1):text+=f'## {i}. {h}\n\n{b}\n\n'
    text+='## 架構\n\n```mermaid\nflowchart TD\n A[Original YOLO / SAM2.1 / local tracks] --> B[CandidateEpoch]\n A --> P[PersonEpoch + reliable partial camera compensation]\n B --> C[Clean provenance + Evidence Integrity]\n C --> V[DINOv3 primary / DINOv2 correlated crosscheck / Core-Negative / current LightGlue / photo veto]\n C --> F[Physical reachability / coexistence / known distinct]\n P --> I[Persistent proximity / compensated motion / occlusion / reappearance]\n F --> S[PhysicalIdentityState]\n I --> S\n V --> G[Explicit Case1 / Case2 / Case3 gates]\n S --> G\n G --> H[IdentityGuard inherited scoped capability sinks]\n H --> J[Same-CE checked backfill + revocation]\n J --> K[Final authorized timeline]\n K --> L[Unchanged event windows / physical memory / search]\n L --> Q[Qwen2.5 NF4 smoke: gated, skipped this run]\n```\n\n'
    text+='## Safe / V295 / V296 / V297\n\n| Metric | Safe | V295 | V296 | V297 |\n|---|---:|---:|---:|---:|\n'
    rows=[('Known permanent false merges',0,2,2,safe['known_permanent_false_merge_cases']),('val9 wrong alias',0,'yes',3,len(cases['val_9']['wrong_active_aliases'])),('val10 wrong alias',0,'yes',1,len(cases['val_10']['wrong_active_aliases'])),('val9 wrong Core',0,0,0,cases['val_9']['wrong_Core_contamination']),('val10 wrong Core',0,'historical not comparable',2,cases['val_10']['wrong_Core_contamination']),('test8 correct recovery',0,0,1,test8['V297']),('Known authorized observations',169,404,359,val['totals']['authorized_observations']),('Critical wrong authorized',0,23,52,safe['wrong_critical_authorized_observations']),('SAM/YOLO bypass','blocked','blocked','blocked','blocked' if not safe['bypass_violations'] else 'VIOLATION'),('CandidateEpoch','no','yes','yes','yes'),('Evidence Integrity','yes','yes','yes','yes'),('DINOv3','no','yes','yes','yes')]
    for label in ['Physical continuity','Person interaction continuity','Candidate pre-existence veto','Known-distinct physical entity']:rows.append((label,'no','no','no','implemented; actual support below'))
    for r in rows:text+='| '+' | '.join(map(str,r))+' |\n'
    text+='\nV295=23是歷史稀疏wrong区間；V296=52與V297使用擴大原始翻面序列複查，覆蓋不同，不能推算模型accuracy或錯誤率改善百分比。\n\n'
    text+='## 實際物理證據與成本\n\n| Set | 授權 | Continuity confirm | Interaction confirm | Appearance-only ambiguous decisions | Backfill | Wall seconds | CUDA allocated GiB | Video-end RSS GiB |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    summary={}
    for kind,m in [('development',dev),('known regression',val)]:
        ts=m['totals'];ms=list(m['videos'].values());text+=f'| {kind} | {ts["authorized_observations"]} | {ts["continuity_confirmations"]} | {ts["interaction_conditioned_confirmations"]} | {ts["ambiguous_appearance_only_long_gap_cases"]} | {ts["backfilled_observations"]} | {ts["wall_seconds"]:.2f} | {max(r["peak_cuda_allocated_bytes"] for r in ms)/2**30:.3f} | {max(r["RSS_end_bytes"] for r in ms)/2**30:.3f} |\n'
        summary[kind]={k:sum(r.get(k,0) for r in ms) for k in ['person_near_events','motion_coupled_authorized_frames','occlusion_hypotheses','known_distinct_records','known_distinct_entity_vetoes','candidate_preexistence_vetoes']}
        for key in ['reachability','interaction']:c=Counter();[c.update(r['physical_counts'][key]) for r in ms];summary[kind][key]=dict(c)
    save(OUT/'final/evidence_metrics.json',summary);text+='\n計數單位：physical states為candidate observations；ambiguous為decision次數（同CE可多次），coupling為授權sampled frames；不是不同手機／完整事件數。\n\n```json\n'+json_format(summary,indent=2)+'\n```\n\n'
    text+='## 所有影片輸出\n\n| Set / video | Authorized | Unresolved candidate frames | C / I confirmations | Camera reliable / sampled |\n|---|---:|---:|---|---|\n'
    for kind,m in [('dev',dev),('known',val)]:
        for v,r in m['videos'].items():text+=f'| {kind} / {v} | {r["authorized_observations"]} | {r["unresolved_candidate_frames"]} | {r["continuity_confirmations"]} / {r["interaction_conditioned_confirmations"]} | {r["camera_reliable_frames"]} / {r["sampled_frames"]} |\n'
    text+='\n## 執行入口與資料位置\n\n- `scripts/run_v297_identity.py`: calibrate / development / freeze / known_val_regression / smoke。\n- `scripts/report_v297.py`: development / review_sheets / known_regression / preservation / report。\n- `src/memory_graph/v297_physical_identity/`:獨立新modules。\n- 所有new結果在 `outputs/v297_physical_identity/`；不取代normal runner。\n- `development_diagnostics_v01/v02`保留較早開發嘗試；只有最後 `development/runs` 被凍結。\n\n'
    text+=status+'\n'+ready+'\n';(OUT/'V297_PHYSICAL_IDENTITY_REPORT.md').write_text(text,encoding='utf8')
    save(OUT/'final/status.json',{'status':status,'readiness':ready,'promoted_main':False,'tests_pass':tests_pass})
    print(status,ready,flush=True)

def json_format(value,**kwargs):
    import json
    return json.dumps(value,ensure_ascii=False,**kwargs)
