"""Post-run evaluation/reporting; never imported by identity inference."""
import sys,time,json
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.v296_reid.io import ROOT,OUT,OLD,read,save,sha
from memory_graph.v296_reid.runner import source_hashes,verify_freeze

def review_sheets(kind):
    from PIL import Image,ImageDraw
    import cv2
    ids=[f'test{i}' for i in range(1,10)] if kind=='development' else [f'val_{i}' for i in range(1,12)]
    items=[]
    for vid in ids:
        s=read(OUT/f'{kind}/runs/{vid}/identity.json');meta=read(OUT/f'{kind}/runs/{vid}/metadata.json')
        original=meta[s['banks']['core'][0]['observation_id']] if s['banks']['core'] else None
        for a in s['confirmation_audit']:
            items.append({'video':vid,'confirmation_frame':a['frame'],'route':a['route'],'candidate_epoch_id':a['candidate_epoch_id'],
                'observation_id':a['current_observation'],'initial':original,'current':meta[a['current_observation']],
                'active_alias':any(x['alias_id']==a['alias_id'] and x['status']=='CONFIRMED' for x in s['aliases'])})
    for page in range((len(items)+4)//5):
        group=items[page*5:page*5+5];sheet=Image.new('RGB',(1100,260*len(group)),(240,240,240));draw=ImageDraw.Draw(sheet)
        for j,item in enumerate(group):
            draw.text((5,j*260+5),f'{page*5+j}: {item["video"]} f{item["confirmation_frame"]} route{item["route"]} {item["candidate_epoch_id"]}',fill='black')
            for k,r in enumerate([item['initial'],item['current']]):
                crop=Image.open(r['raw_crop_path']).convert('RGB');crop.thumbnail((180,215));sheet.paste(crop,(5+k*190,j*260+30))
            video=ROOT/(f'{item["video"]}.mp4' if kind=='development' else f'val_set/{item["video"]}.mp4')
            cap=cv2.VideoCapture(str(video));cap.set(cv2.CAP_PROP_POS_FRAMES,item['confirmation_frame']);ok,im=cap.read();cap.release()
            if ok:
                original=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));original.thumbnail((700,230));sheet.paste(original,(390,j*260+25))
            item['review_index']=page*5+j
        dest=OUT/f'{kind}/review_sheets/confirmations_{page}.png';dest.parent.mkdir(parents=True,exist_ok=True);sheet.save(dest)
        for item in group:item['review_sheet']=str(dest.relative_to(OUT));item['review_sheet_sha256']=sha(dest)
    save(OUT/f'{kind}/review_index.json',[{k:v for k,v in x.items() if k not in ['initial','current']} for x in items])
    print(kind,'confirmation frames to review',len(items),flush=True)

def development():
    r=read(OUT/'development/recovery_metrics.json');labels={(x['video_id'],x['observation_id']):lab for file,lab in [('positive_observations','TARGET'),('negative_observations','DISTRACTOR')] for x in read(OLD/f'benchmark/{file}.json')}
    totals=Counter();recovered=Counter();audits={};epochs={};banks={};decisions=[]
    for vid in r['videos']:
        s=read(OUT/f'development/runs/{vid}/identity.json');first=s['aliases'][0]['alias_id'] if s['aliases'] else None
        for row in s['final_ledger']:
            label=labels.get((vid,row['observation']['observation_id']),'UNLABELED');totals[label]+=1
            if row['alias_id']!=first:recovered[label]+=1
        audits[vid]=read(OUT/f'development/runs/{vid}/confirmation_audit.json');epochs[vid]=read(OUT/f'development/runs/{vid}/candidate_epochs.json');banks[vid]=s['banks'];decisions+=s['decisions']
    save(OUT/'candidate_epochs/development_epochs.json',epochs)
    save(OUT/'candidate_epochs/epoch_diagnostics.json',{'development':{vid:m['epoch_counts'] for vid,m in r['videos'].items()}})
    save(OUT/'evidence_integrity/confirmation_audit.json',{'development':audits})
    save(OUT/'evidence_integrity/violations.json',{'development':{flag:sum(a['violation_counts'][flag] for a in audits.values()) for flag in next(iter(audits.values()))['violation_counts']},
        'scope':'Violations in accepted confirmation evidence. Rejected invalid Core proposals are separately retained in decisions.'})
    save(OUT/'appearance/dinov3_metrics.json',{'primary':'official DINOv3 ViT-B/16','development_labels':dict(totals),'recovered_label_counts':dict(recovered),'matrices':[{'frame':d['frame'],'epoch':d['candidate_id'],'DINOv3':d['DINOv3']} for d in decisions if d.get('DINOv3')]})
    save(OUT/'appearance/dinov2_crosscheck.json',{'correlated_not_independent':True,'development_counts':dict(Counter(d.get('DINOv2',{}).get('state','NOT_REQUESTED') for d in decisions)),
        'confirmation_summaries':[{'epoch':a['candidate_epoch_id'],'DINOv2':a['DINOv2']} for v in audits.values() for a in v['recoveries']]})
    save(OUT/'lightglue/verification_results.json',{'development':{v:read(OUT/f'development/runs/{v}/LightGlue.json') for v in r['videos']}})
    save(OUT/'development/labeled_identity_evaluation.json',{'authorized':dict(totals),'recovered':dict(recovered),'labeled_false_authorizations':totals['DISTRACTOR'],'unlabeled_not_counted_correct':True})
    save(OUT/'development/bank_reports.json',banks)
    s=read(OUT/'development/runs/test8/identity.json');matches=s['confirmation_audit']
    save(OUT/'development/test8_recovery.json',{'safe_baseline':'UNRESOLVED','V295':'UNRESOLVED','V296':'CONFIRMED_PENDING_VISUAL_REVIEW' if matches else 'UNRESOLVED',
        'evidence_chain':matches,'authorized_observations':r['videos']['test8']['authorized_observations'],'known_initial38_authorized':38,
        'evaluation_only':'Frame and source candidate IDs do not enter runtime policy.'})
    baseline=read(ROOT/'outputs/identity_rebuild/development/runs_final/test2/authorized_rows.json');new=read(OUT/'development/runs/test2/authorized_rows.json')
    oldset={x['frame'] for x in baseline if x['identity_authorized']};newset={x['frame'] for x in new if x['identity_authorized']}
    save(OUT/'development/test2_continuity_comparison.json',{'baseline':len(oldset),'V296':len(newset),'lost_baseline_frames':sorted(oldset-newset),'additional_frames':sorted(newset-oldset)})
    print('Development',r['totals'],'labeled',dict(totals),flush=True)

def known_regression():
    verify_freeze();r=read(OUT/'known_val_regression/metrics.json');audits={};critical={};flags=Counter()
    review=read(OUT/'known_val_regression/visual_review.json',{})
    # These fixed labels are evaluation only, derived from already opened critical cases and V295 post-run reviews.
    negatives={'val_5':{'track:77':(1284,999999)},'val_9':{'track:42':(960,999999),'track:52':(1194,999999),'track:63':(1314,999999),'track:65':(1380,999999)},'val_10':{'track:49':(1140,1859)}}
    for vid in r['videos']:
        s=read(OUT/f'known_val_regression/runs/{vid}/identity.json');md=read(OUT/f'known_val_regression/runs/{vid}/metadata.json');a=read(OUT/f'known_val_regression/runs/{vid}/confirmation_audit.json')
        audits[vid]=a;flags.update(a['violation_counts'])
        if vid not in negatives:continue
        reviewed_wrong=set(review.get('critical_wrong_observation_ids',{}).get(vid,[]))
        def isbad(oid):
            m=md[oid];interval=negatives[vid].get(m['local_track_id']);return oid in reviewed_wrong or bool(interval and interval[0]<=m['frame']<=interval[1])
        badrows=[x for x in s['final_ledger'] if isbad(x['observation']['observation_id'])]
        badcore=[b for b in s['banks']['core'] if b['active'] and isbad(b['observation_id'])]
        aliases=[a for a in s['aliases'] if a['status']=='CONFIRMED' and (any(isbad(oid) for oid in a['evidence_refs']) or any(x['alias_id']==a['alias_id'] for x in badrows))]
        case={'wrong_active_aliases':aliases,'wrong_authorized_observations':len(badrows),'wrong_core_updates':len(badcore),'wrong_rows':badrows,
            'additional_post_run_review_wrong_observation_ids':sorted(reviewed_wrong),
            'evaluated_negative_local_intervals':negatives[vid],'decisions':[d for d in s['decisions'] if d.get('observation_id') and isbad(d['observation_id'])],
            'scope':'Fixed previous critical intervals plus explicitly reviewed V296 wrong observations from original crops and physical flip sequence. Evaluation only after freeze; never read by inference.'}
        critical[vid]=case;save(OUT/f'known_val_regression/{vid}_case.json',case)
    save(OUT/'known_val_regression/confirmation_audit.json',audits)
    wrongvideos=sum(bool(x['wrong_active_aliases']) for x in critical.values())
    gate=not wrongvideos and not any(x['wrong_authorized_observations'] or x['wrong_core_updates'] for x in critical.values()) and not any(flags.values()) and r['totals']['unauthorized_writes']==0 and review.get('all_confirmation_frames_reviewed',False) and review.get('wrong_confirmation_frames',1)==0 and review.get('unresolved_confirmation_frames',1)==0
    visual_wrong_active={x['video'] for x in review.get('confirmations',[]) if x.get('classification')=='DISTRACTOR' and x.get('active_alias')}
    known_wrong_videos={vid for vid,x in critical.items() if x['wrong_active_aliases']} | visual_wrong_active
    summary={'known_permanent_false_merge_cases':len(known_wrong_videos),'known_wrong_active_alias_videos':sorted(known_wrong_videos),'critical_wrong_active_alias_count':sum(len(x['wrong_active_aliases']) for x in critical.values()),
        'wrong_critical_authorized_observations':sum(x['wrong_authorized_observations'] for x in critical.values()),'val9_wrong_core_contamination':critical['val_9']['wrong_core_updates'],
        'critical_wrong_core_updates':sum(x['wrong_core_updates'] for x in critical.values()),'val10_wrong_core_contamination':critical['val_10']['wrong_core_updates'],
        'authorized_observations':r['totals']['authorized_observations'],'backfilled_observations':r['totals']['backfilled_observations'],
        'route_g':r['totals']['route_g'],'route_a':r['totals']['route_a'],'integrity_flags':dict(flags),'bypass_violations':r['totals']['unauthorized_writes'],
        'identity_safety_gate_passed':gate,'visual_wrong_confirmation_frames':review.get('wrong_confirmation_frames'),
        'visual_unresolved_confirmation_frames':review.get('unresolved_confirmation_frames'),'full_identity_accuracy':None,'scope':'Known post-validation regression plus confirmation-frame engineering review; not held-out and not complete descendant identity GT'}
    save(OUT/'known_val_regression/safety_summary.json',summary)
    v=read(OUT/'evidence_integrity/violations.json');v['known_val_regression']=dict(flags);save(OUT/'evidence_integrity/violations.json',v)
    for path,key,value in [('evidence_integrity/confirmation_audit.json','known_val_regression',audits),
            ('candidate_epochs/epoch_diagnostics.json','known_val_regression',{vid:m['epoch_counts'] for vid,m in r['videos'].items()}),
            ('lightglue/verification_results.json','known_val_regression',{vid:read(OUT/f'known_val_regression/runs/{vid}/LightGlue.json') for vid in r['videos']})]:
        obj=read(OUT/path);obj[key]=value;save(OUT/path,obj)
    snapshots={vid:read(OUT/f'known_val_regression/runs/{vid}/identity.json') for vid in r['videos']}
    decisions=[d for s in snapshots.values() for d in s['decisions']]
    obj=read(OUT/'appearance/dinov2_crosscheck.json');obj['known_counts']=dict(Counter(d.get('DINOv2',{}).get('state','NOT_REQUESTED') for d in decisions));obj['known_confirmation_summaries']=[{'video':vid,'epoch':a['candidate_epoch_id'],'DINOv2':a['DINOv2']} for vid,v in audits.items() for a in v['recoveries']];save(OUT/'appearance/dinov2_crosscheck.json',obj)
    obj=read(OUT/'appearance/dinov3_metrics.json');obj['known_matrices']=[{'video':vid,'frame':d['frame'],'epoch':d['candidate_id'],'DINOv3':d['DINOv3']} for vid,s in snapshots.items() for d in s['decisions'] if d.get('DINOv3')];save(OUT/'appearance/dinov3_metrics.json',obj)
    save(OUT/'known_val_regression/bank_reports.json',{vid:s['banks'] for vid,s in snapshots.items()})
    evidence={}
    for kind,metrics in [('development',read(OUT/'development/recovery_metrics.json')),('known_val_regression',r)]:
        counters={key:Counter() for key in ['LightGlue','epoch_counts','decisions']}
        for m in metrics['videos'].values():
            for key in counters:counters[key].update(m[key])
        evidence[kind]={'totals':metrics['totals'],**{key:dict(v) for key,v in counters.items()},'active_recovered_aliases':sum(m['active_recovered_aliases'] for m in metrics['videos'].values()),'revoked_aliases':sum(m['revoked_aliases'] for m in metrics['videos'].values()),'rejected_invalid_pair_attempts':sum(m['rejected_invalid_pair_attempts'] for m in metrics['videos'].values())}
    save(OUT/'final/evidence_metrics.json',evidence)
    print('Known safety',summary,flush=True)

def preservation():
    before=read(OUT/'baseline/preservation_manifest.json');changed=[];missing=[]
    for name,h in before['files'].items():
        p=ROOT/name
        if not p.is_file():missing.append(name)
        elif sha(p)!=h:changed.append(name)
    result={'protected_files':len(before['files']),'unchanged':len(before['files'])-len(changed)-len(missing),'changed':changed,'missing':missing,
        'safe_main_unchanged':sha(ROOT/'scripts/run_findmind.py')==read(OUT/'baseline/baseline_metrics.json')['normal_runner_sha256'],
        'sibling_repository_written':False,'checked_unix':time.time()}
    save(OUT/'final/integrity_manifest.json',result);save(OUT/'final/source_hashes.json',source_hashes());save(OUT/'final/selected_config.json',read(OUT/'calibration/parameters.json'))
    print('Preservation',result,flush=True)

def report():
    verify_freeze();dev=read(OUT/'development/recovery_metrics.json');val=read(OUT/'known_val_regression/metrics.json');safe=read(OUT/'known_val_regression/safety_summary.json');integ=read(OUT/'final/integrity_manifest.json')
    review=read(OUT/'development/visual_review.json');test8=read(OUT/'development/test8_recovery.json');smoke=read(OUT/'smoke/qwen25_smoke.json')
    status='V296_REID_REGRESSION' if safe['known_permanent_false_merge_cases'] or safe['critical_wrong_active_alias_count'] or safe['wrong_critical_authorized_observations'] else 'V296_REID_CLEAR_SUCCESS' if safe['identity_safety_gate_passed'] and test8['V296']=='CONFIRMED_CORRECT' and val['totals']['authorized_observations']>=212 else 'V296_REID_PARTIAL_SUCCESS'
    if integ['changed'] or integ['missing'] or any(safe['integrity_flags'].values()):status='V296_REID_INVALID'
    full_test=(OUT/'tests/full_results.txt').read_text(encoding='utf8',errors='replace')
    full_passed='failed' not in full_test.lower() and 'passed' in full_test.lower()
    ready='READY_FOR_NEW_IDENTITY_HELD_OUT_SET' if status=='V296_REID_CLEAR_SUCCESS' and full_passed and smoke.get('calls',0)>0 and smoke.get('validator_valid') and smoke.get('EOS_complete') else 'NOT_READY_FOR_NEW_IDENTITY_HELD_OUT_SET'
    cfg=read(OUT/'calibration/parameters.json');p=cfg['confirmation'];text='# V296 — Evidence Integrity + Dual-Route Safe Re-ID\n\n'
    text+=f'**結論：{status}。** 實驗已完成，主流程維持原安全預設；V295與歷史結果保留。開發與已知回歸結果分開計算，不宣稱新held-out準確率。\n\n'
    headings=['Goal','V295 failure mechanisms addressed','Candidate Epoch architecture','Evidence Integrity contract','DINOv3 primary evidence','DINOv2 cross-check','Core / Negative Bank policy','Low-level contradiction veto','LightGlue current-frame contract','Route G','Route A','Delayed confirmation','Retroactive backfill','Development results','test8','test2 / test7 / test9','Frozen policy','val_5','val_9','val_10','Authorized observation recovery','Evidence-integrity audit','Runtime/resource cost','Tests','Remaining bottleneck','Promotion recommendation']
    sections=[
        '以原始乾淨影格、候選epoch與可追溯證據修復Re-ID。DINOv3為主，DINOv2只做相關外觀交叉檢查。False merge優先於recall；只允許IdentityGuard授權。',
        '排除自我crop/同epoch/循環lineage與候選epoch之後才建立的Core；G路徑必須驗證當前影格。舊影格不能替當前手機通過幾何驗證。共享貼紙仍非物理身份證明，加入foreground photometric veto。',
        '以gap、scene/reset、bbox/motion、持續外觀與SAM連續性變化建立獨立CandidateEpoch。只有唯一、短gap、合理運動與外觀一致才串接local IDs；共現不串接。不確定轉折影格不授權、不回填。可靠mask取得造成的表示切換不獨自當作換物。',
        '每項證據保存video/frame/observation/local ID/candidate epoch/identity epoch、原始像素SHA與路徑、crop SHA、overlay狀態、producer、bank/alias/authorization lineage。Core參考的觀測與commit都必須早於候選epoch。輸入逐像素比對原始解碼與canonical crop，拒絕rendered/annotated/stale內容。',
        '沿用官方facebook/dinov3-vitb16-pretrain-lvd1689m，revision5931719e67bbdb9737e363e781fb0c67687896bc，CUDAfloat32，768dim；可靠foreground patch mean，否則canonical object crop patch mean，L2normalize。V295有效cache讀取而不重寫，沒有重新做模型搜尋。',
        '官方facebook/dinov2-base，revisionf9e44c814b77203eaa57a6bdbbd535f21ede1415；候選接近確認才请求候選／Core視角feature。DINOv2與3高度相關，不能算兩個獨立身份證人。不同意／部分一致時保留未確認。',
        'Core最多8視角，quality/diversity/.4s間隔；確認本身只進Quarantine。恢復後至少3個未来授權觀測、穩定時間、無矛盾及獨立當前geometry才能加Core。回填不算未来穩定證據。Negative只用可信target共現的分離手機；empty/no-match是NO_INFORMATION，非正向身份證據。',
        f'小型非學習Lab/chroma foreground統計；無可靠mask或足夠色度則UNKNOWN。距所有可比較Core的最近色差>{p["photometric_threshold"]}才STRONG_CONTRADICTION；其他是NO_CONTRADICTION，從不輸出positive identity。門檻高於全部可比較開發target距離加buffer，未依val顏色調整，也沒有任何顏色名稱規則。',
        '官方SuperPoint1024+LightGlue，512resize，RANSAC3px/normalized256。沿用16inliers/.5ratio/.1coverage，另看3x3occupied cells及border/background分布。只以CURRENT原始candidate對合法較早Core；存inlier座標、完整pair JSON與原始crop audit線圖。狀態CORE_STRONG_MATCH/NEGATIVE_STRONG_MATCH/UNKNOWN/INVALID_EVIDENCE。這是local correspondence support，不是單獨物理身份證明。',
        f'G：≥{p["g_frames"]}非重複影格／{p["g_duration"]}s，v3median≥{p["g_support"]:.2f}、lower≥{p["g_lower"]:.2f}、current≥{p["g_current"]:.2f}，多個獨立trustedCore、v2agree，無Negative/photo/coexistence/competitor矛盾，加CURRENT independentCore geometry。',
        f'A：geometry只能UNKNOWN，≥{p["a_frames"]}影格／{p["a_duration"]}s，v3median/current≥{p["a_support"]:.2f}、lower≥{p["a_lower"]:.2f}，v2median/lower/current≥{p["v2_support"]:.2f}，其餘完整veto與integrity gates全通過。INVALID_EVIDENCE不能支持A。門檻由全球開發操作點選擇，優先零已標註distractor接受，再最大已標註target恢復、同recall選較嚴值。',
        'NEW_CANDIDATE→EVIDENCE_ACCUMULATING→PROVISIONAL→CONFIRMED/AMBIGUOUS/REJECTED。不存在第一crop或單一最高cosine直接MATCH。保留per-frame×Core/Negative矩陣、median/lower/current與distinctviews，而不是opaque加權總分。',
        '確認後只回填本CandidateEpoch中已選入且通過逐列v3/v2/quality/photo/lineage檢查的觀測；不跨scene/epoch，不回填不確定或矛盾影格。每列由Guard._issue＋Guard.write消耗scopedcapability，記confirmation frame/range/observationIDs；沒有直接改ledger。aliasrevocation仍移除所有回填後代。',
        f'開發test1–9：授權116→{dev["totals"]["authorized_observations"]}；G={dev["totals"]["route_g"]}、A={dev["totals"]["route_a"]}，回填={dev["totals"]["backfilled_observations"]}。每個新確認皆有乾淨原始crop＋全影格review；結果見visual_review.json。早期開發attempts保留diagnostics_v01/v02；只有最终attempt被凍結。',
        f'UNRESOLVED→{test8["V296"]}。詳細candidate epoch/current/v3/v2/photo/Negative/geometry/route/backfill/authorization chain見development/test8_recovery.json。無frame或track IDs硬編碼進runtime。',
        f'test2：baseline33→{dev["videos"]["test2"]["authorized_observations"]}；初始綁定track/frame保留；具體lost/additionalframe列表另存。test7確認與干擾物逐列label check，test9long-gap確認={dev["videos"]["test9"]["confirmed_recoveries"]}。9/9初始track和frame比較見metrics。',
        '凍結全部推論source、原Guard/renderer/builder/entrypoint、兩模型revision、split/stitch/photo/G/A/geometry/backfill/bankpolicy與開發metrics SHA，之後才啟動val1–11。val結果出現後未修改推論程式或參數。',
        json.dumps(read(OUT/'known_val_regression/val_5_case.json'),ensure_ascii=False)[:0]+f'wrong activealiases={len(read(OUT/"known_val_regression/val_5_case.json")["wrong_active_aliases"])}；wrongauthorized={read(OUT/"known_val_regression/val_5_case.json")["wrong_authorized_observations"]}；wrongCore={read(OUT/"known_val_regression/val_5_case.json")["wrong_core_updates"]}。完整矩陣／失敗gate保存case JSON。',
        f'wrong activealiases={len(read(OUT/"known_val_regression/val_9_case.json")["wrong_active_aliases"])}；wrongauthorized={read(OUT/"known_val_regression/val_9_case.json")["wrong_authorized_observations"]}；wrongCore={read(OUT/"known_val_regression/val_9_case.json")["wrong_core_updates"]}。除原track52，亦評估V295已review的其他同一實體干擾物local IDs；不只檢查舊alias名字。',
        f'wrong activealiases={len(read(OUT/"known_val_regression/val_10_case.json")["wrong_active_aliases"])}；wrongauthorized={read(OUT/"known_val_regression/val_10_case.json")["wrong_authorized_observations"]}；wrongCore={read(OUT/"known_val_regression/val_10_case.json")["wrong_core_updates"]}。當前frame缺席／Core同源／跨候選epoch不可形成確認。',
        f'已知回歸授權總数169→{val["totals"]["authorized_observations"]}，candidate-unauthorized1896→{val["totals"]["unresolved_candidate_frames"]}；backfill={val["totals"]["backfilled_observations"]}。其中已確認錯誤授權={safe["wrong_critical_authorized_observations"]}，所以增加的數量不能當作安全改善。其餘觀測缺完整descendant GT，亦不能把總數扣除錯誤後直接宣稱全部正確。原固定稀疏區間只計19筆；原始pickup/flip影格補查後，val9有40筆、val10有12筆。V295的23是歷史稀疏標註口徑，沒有重寫V295結果。',
        json.dumps(safe['integrity_flags'],ensure_ascii=False)+'。统计acceptedconfirmation使用的違規，不把被拒絕proposal算成成功使用證據。所有排除Core和invalidpairattempt在原決策另存；audit同時包含bootstrap初始綁定(不宣稱獨立Re-ID證據)。',
        '有效DINOv3/DINOv2開發cache唯讀重用；DINOv2僅seriouscandidate相關row/Core推論。每video的feature_requests、freshinference時間、wall/framep95、LightGlue新pairlatency、CUDApeakallocated、RSSend均在metrics/resources。GPUallocated非全卡VRAM；RSSend不是全程peak。模型在Qwen前卸載。',
        '\n'.join(f'{name}: '+(OUT/f'tests/{name}.txt').read_text(encoding='utf8',errors='replace').splitlines()[-1] for name in ['new_results','focused_results','full_results']),
        '實測首要瓶頸是相似手機缺少可辨識的物理身份證據。val9 f1080/f1302及val10 f1170透過Route A錯認；val9 f1380甚至有合法CURRENT independent LightGlue STRONG_MATCH仍錯認。兩DINO相關且語義/貼紙相似，不能排除不同手機。四次錯認的photo皆UNKNOWN、Negative皆NO_INFORMATION，沒有有效矛盾訊號可擋下。val10錯認後的future continuity與獨立current geometry仍通過，造成2筆錯誤Core更新；延遲穩定規則不能補救起始身份錯誤。CandidateEpoch在front/back表示切換時可split，但split不能解決下一次錯誤重新確認；回填還擴大錯誤時間軸。後續需更豐富、具完整physical-instance及正反面身份標註的development資料與失敗驗收，再做新版本；本次依要求未使用val結果重調政策。',
        f'{"具已知安全改善，但本次仍保持實驗入口，正常主流程未替換；可開始錄製新的identity held-out集。" if ready.startswith("READY") else "不替換安全主流程；未達可進新held-out驗收的完整條件。保留所有失敗與未確認證據，後續需獨立新資料驗證。"} Qwen smoke：{json.dumps(smoke,ensure_ascii=False)}。未使用Qwen3.8/Strata。'
    ]
    for i,(heading,body) in enumerate(zip(headings,sections),1):text+=f'## {i}. {heading}\n\n{body}\n\n'
    text+='## 架構\n\n```mermaid\nflowchart TD\n A[Raw YOLO / SAM / local tracks] --> B[CandidateEpoch Builder]\n B --> C[Clean original provenance + Integrity]\n C --> D[DINOv3 temporal Core / Negative matrices]\n D --> E[On-demand correlated DINOv2 crosscheck]\n E --> F[Foreground photometric contradiction veto]\n F --> G[Current independent LightGlue support]\n G --> H[Route G / stricter Route A]\n H --> I[IdentityGuard scoped capabilities]\n I --> J[Same-epoch checked backfill]\n J --> K[Final revocation-filtered timeline]\n K --> L[Unchanged event windows / Qwen2.5 NF4]\n```\n\n'
    text+='## Baseline comparison\n\n| Metric | Safe | V295 | V296 |\n|---|---:|---:|---:|\n'
    rows=[('Known permanent false merges',0,2,safe['known_permanent_false_merge_cases']),('val9 wrong active alias',0,'yes',len(read(OUT/'known_val_regression/val_9_case.json')['wrong_active_aliases'])),('val10 wrong active alias',0,'yes',len(read(OUT/'known_val_regression/val_10_case.json')['wrong_active_aliases'])),('val9 wrong Core',0,0,safe['val9_wrong_core_contamination']),('test8 correct recovery',0,0,int(test8['V296']=='CONFIRMED_CORRECT')),('Known authorized observations',169,404,val['totals']['authorized_observations']),('Critical wrong authorized',0,23,safe['wrong_critical_authorized_observations']),('SAM/YOLO bypass','blocked','blocked','blocked' if safe['bypass_violations']==0 else 'violation'),('Self evidence used',0,'observed',safe['integrity_flags'].get('SELF_EVIDENCE',0)),('Cross-epoch leakage',0,'observed',safe['integrity_flags'].get('CROSS_CANDIDATE_EPOCH_EVIDENCE',0))]
    for label,a,b,c in rows:text+=f'| {label} | {a} | {b} | {c} |\n'
    for label in ['DINOv3 primary','DINOv2 crosscheck','Photometric veto','Current-frame LightGlue','Dual routes','Same-epoch backfill']:text+=f'| {label} | no | {"yes" if label=="DINOv3 primary" else "no"} | yes |\n'
    text+='\nCritical wrong authorization的V295=23保留歷史稀疏已知區間口徑；V296固定區間=19，新增原始影格/翻面序列完整補查後=52。兩者標註覆蓋不同，不能據此計算錯誤率差。無論採19或52，零錯誤安全門檻都已失敗。\n\n'
    text+='\n## 每支影片結果\n\n| Set / video | Authorized | G | A | Backfill | Unresolved candidate frames |\n|---|---:|---:|---:|---:|---:|\n'
    for kind,metrics in [('development',dev),('known regression',val)]:
        for vid,m in metrics['videos'].items():text+=f'| {kind} / {vid} | {m["authorized_observations"]} | {m["route_g"]} | {m["route_a"]} | {m["backfilled_observations"]} | {m["unresolved_candidate_frames"]} |\n'
    text+='\n## 實測成本與證據統計\n\n| Set | Identity replay wall seconds | Max process CUDA allocated GiB | Max video-end RSS GiB | Fresh DINOv2 inference seconds |\n|---|---:|---:|---:|---:|\n'
    for kind,metrics in [('development',dev),('known regression',val)]:
        ms=list(metrics['videos'].values());text+=f'| {kind} | {sum(m["wall_seconds"] for m in ms):.2f} | {max(m["peak_cuda_allocated_bytes"] for m in ms)/2**30:.3f} | {max(m["RSS_end_bytes"] for m in ms)/2**30:.3f} | {sum(m["feature_resources"]["inference_seconds"].get("dinov2",0) for m in ms):.2f} |\n'
    text+='\n上表是identity replay成本，未包含首次原影片解碼／canonical逐像素驗證，也未包含YOLO/SAM重跑或Qwen。開發重用DINOv3與DINOv2cache；已知回歸DINOv3重用，DINOv2按需新算。CUDA allocated只計本process tensor allocation，非全卡VRAM；RSS為video結尾，不是全程peak。\n\n'
    text+='```json\n'+json.dumps(read(OUT/'final/evidence_metrics.json'),ensure_ascii=False,indent=2)+'\n```\n\n'
    text+='全套測試首次暫存設在outputs下，觸發舊V2/V2.1輸出目錄保護，4項拒絕；未改任何程式，以獨立temporary test workspace重跑後採用full_results.txt。原紀錄full_results_path_isolation_diagnostic.txt保留。\n\n'
    text+=f'\nProtectedbytes:{integ["unchanged"]}/{integ["protected_files"]}unchanged。Normalrunnerunchanged={integ["safe_main_unchanged"]}。\n\n'+status+'\n'+ready+'\n'
    (OUT/'V296_REID_REPORT.md').write_text(text,encoding='utf8');save(OUT/'final/status.json',{'status':status,'readiness':ready,'promoted_main':False})
    print(status,ready,flush=True)

if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='review_sheets':review_sheets(sys.argv[2])
    else:{'development':development,'known_regression':known_regression,'preservation':preservation,'report':report}[cmd]()
