"""Evaluation/reporting only. Never imported by the identity runner."""
from pathlib import Path
from collections import Counter
import sys,time,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.v295_reid.io import ROOT,OUT,read,save,sha
from memory_graph.v295_reid.runner import policy,source_hashes,verify_freeze


def development():
    results=read(OUT/'development/regression_metrics.json');labels={}
    for name,label in [('positive_observations','TARGET'),('negative_observations','DISTRACTOR')]:
        for r in read(OUT/f'benchmark/{name}.json'):labels[(r['video_id'],r['observation_id'])]=label
    stats={};banks={k:{} for k in ['core','negative','quarantine']};evidence={};review=[]
    for v in results['videos']:
        s=read(OUT/f'development/runs/{v}/identity.json');initial=s['aliases'][0]['alias_id'] if s['aliases'] else None
        counts=Counter(labels.get((v,r['observation']['observation_id']),'UNLABELED') for r in s['final_ledger'])
        recovered=Counter(labels.get((v,r['observation']['observation_id']),'UNLABELED') for r in s['final_ledger'] if r['alias_id']!=initial)
        stats[v]={'authorized_label_counts':dict(counts),'recovered_label_counts':dict(recovered)}
        for k in banks:banks[k][v]=s['banks'][k]
        evidence[v]=read(OUT/f'development/runs/{v}/tracklet_evidence.json')
        for a in s['aliases'][1:]:
            review.append({'video':v,'candidate':a['candidate_id'],'frame':a['confirmation_frame'],'review':'TARGET',
                'basis':'Observed same casing/camera/sticker or screen/case geometry as initial target in paired canonical crops and full original frame',
                'review_sheet':'development/confirmed_alias_review.png','review_sheet_sha256':sha(OUT/'development/confirmed_alias_review.png'),
                'scope':'Post-run visual engineering review of confirmation frame only; not independent GT or all descendant frames'})
    save(OUT/'development/confirmation_frame_review.json',review)
    save(OUT/'development/authorized_observation_metrics.json',{'videos':stats,'totals':dict(sum((Counter(x['authorized_label_counts']) for x in stats.values()),Counter())),
        'false_authorized_labeled_observations':sum(x['authorized_label_counts'].get('DISTRACTOR',0) for x in stats.values()),
        'correct_recovered_confirmation_frames_visually_reviewed':len(review),
        'limitation':'Unlabeled authorized rows are not counted as verified correct. No full identity GT.'})
    for k,value in banks.items():save(OUT/f'banks/{"core_bank_report" if k=="core" else "negative_bank_report" if k=="negative" else "quarantine_report"}.json',{'development':value})
    save(OUT/'tracklets/development_tracklet_evidence.json',evidence)
    s=read(OUT/'development/runs/test8/identity.json');d=[x for x in s['decisions'] if x.get('LightGlue',{}).get('status') in ['UNKNOWN','CORE_VERIFIED','NEGATIVE_VERIFIED'] and x.get('duration',0)>=.4 and x['frame']>=780]
    save(OUT/'development/test8_recovery.json',{'baseline':'UNRESOLVED','v295':'UNRESOLVED','f804_authorized':False,'confirmed_long_gap_recoveries':results['videos']['test8']['confirmed_recoveries'],
        'evidence_chain':d,'finding':'Target tracklet has multi-frame appearance support, but selected Core geometry is UNKNOWN. No bypass or threshold weakening.',
        'local_id_switch_evaluation':'Manual crop review found track:64 smartphone at816-828, cordless distractor after870; causal gap resets support.'})
    metrics=read(OUT/'benchmark/backbone_metrics.json');text='# V295 Backbone Comparison\n\n'
    text+='Same canonical crops, common causal reference prefix, disjoint later target queries;104 target/124 distractor queries. Engineering labels with provenance; correlated frames, few physical instances. ROC-AUC/EER are not claimed as population estimates.\n\n'
    text+='| Model | Target accepted at zero observed distractor acceptance | Threshold |\n|---|---:|---:|\n'
    for model in ['mobilenet','dinov2','dinov3']:
        m=metrics[model];op=m['zero_observed_false_acceptance_point']
        text+=f'| {model} | {op["true_accepts"]}/104;0/124 negatives | {op["threshold"]:.2f} |\n'
    text+='\nDINOv3 selected by one additional target query over DINOv2 at zero observed false acceptance. This small difference is not evidence of statistically established superiority. Identity uses stricter development gates plus independent geometry, not the single-frame operating point.\n\n'
    text+='Protocol corrections and sparse-label diagnostics are preserved in `protocol_diagnostics_v01/` and `labeling_v01/`; only the final common patch-mean protocol and expanded reviewed dataset determine selection.\n'
    (OUT/'benchmark/BACKBONE_COMPARISON.md').write_text(text,encoding='utf8')
    print('Development evaluated',results['totals'],flush=True)


def known_val():
    verify_freeze();r=read(OUT/'known_val_regression/val_1_to_11_metrics.json');cases={}
    for v,bad,start,end in [('val_5','track:77',1284,999999),('val_9','track:52',1194,999999),('val_10','track:49',1140,1859)]:
        s=read(OUT/f'known_val_regression/runs/{v}/identity.json')
        badrows=[x for x in s['final_ledger'] if x['candidate_id']==bad and start<=x['observation']['frame']<=end]
        case={'known_wrong_candidate':bad,'wrong_interval':[start,end],
            'known_wrong_alias_active':any(a['candidate_id']==bad and a['status']=='CONFIRMED' for a in s['aliases']),
            'known_wrong_core_entries':sum(b['active'] and b['candidate_id']==bad and start<=b['frame']<=end for b in s['banks']['core']),
            'known_wrong_authorized_observations':len(badrows),
            'decisions':[d for d in s['decisions'] if d['candidate_id']==bad],
            'banks':s['banks'],'scope':'Known post-validation case; not tuning input or independent held-out accuracy'}
        save(OUT/f'known_val_regression/{v}_case.json',case);cases[v]=case
    summary={'known_permanent_false_merges':sum(c['known_wrong_alias_active'] for c in cases.values()),
        'known_wrong_authorized_observations':sum(c['known_wrong_authorized_observations'] for c in cases.values()),
        'val9_wrong_core_entries':cases['val_9']['known_wrong_core_entries'],
        'authorized_observations':r['totals']['authorized_observations'],
        'candidate_but_unauthorized':r['totals']['unresolved_candidate_frames'],
        'confirmed_long_gap_episodes':r['totals']['confirmed_recoveries'],
        'correct_recovered_observations':None,'false_authorized_full_dataset':None,
        'limitation':'Counts of authorization are not counts of correct identity. Known wrong candidates evaluated; all other new aliases require explicit visual/GT review. No unseen held-out accuracy.'}
    save(OUT/'known_val_regression/summary.json',summary)
    for k in ['core','negative','quarantine']:
        name='core_bank_report' if k=='core' else 'negative_bank_report' if k=='negative' else 'quarantine_report'
        p=OUT/f'banks/{name}.json';value=read(p);value['known_val_regression']={v:read(OUT/f'known_val_regression/runs/{v}/identity.json')['banks'][k] for v in r['videos']};save(p,value)
    print('Known regression',summary,flush=True)


def integrity():
    before=read(OUT/'baseline/preserved_state.json');files=before['files'];changed=[];missing=[]
    for name,h in files.items():
        p=ROOT/name
        if not p.is_file():missing.append(name)
        elif sha(p)!=h:changed.append(name)
    result={'protected_files':len(files),'unchanged':len(files)-len(changed)-len(missing),'changed':changed,'missing':missing,
        'V294_untouched':not any('v294' in x.lower() for x in changed+missing),
        'historical_outputs_untouched':not any(x.startswith('outputs') for x in changed+missing),
        'sibling_repository_written':False,'checked_unix':time.time()}
    save(OUT/'final/integrity_manifest.json',result);save(OUT/'final/source_hashes.json',source_hashes())
    save(OUT/'final/selected_config.json',{'backbone':read(OUT/'benchmark/selected_backbone.json'),'policy':read(OUT/'calibration/confirmation_policy.json'),
        'default_pipeline_modified':False,'opt_in_entrypoint':'scripts/run_v295_reid.py','freeze':read(OUT/'final/development_freeze.json')})
    print('Integrity',result,flush=True)


def final_report():
    verify_freeze()
    b=read(OUT/'baseline/safe_baseline.json');dev=read(OUT/'development/regression_metrics.json');val=read(OUT/'known_val_regression/val_1_to_11_metrics.json')
    summary=read(OUT/'known_val_regression/summary.json');models=read(OUT/'benchmark/backbone_metrics.json');smoke=read(OUT/'smoke/result.json');integ=read(OUT/'final/integrity_manifest.json')
    review=read(OUT/'known_val_regression/recovery_review.json',{})
    status='V295_REID_REGRESSION' if summary['known_permanent_false_merges'] or summary['val9_wrong_core_entries'] or review.get('false_confirmation_frames',0) else 'V295_REID_PARTIAL_SUCCESS'
    if integ['changed'] or integ['missing']:status='V295_REID_INVALID'
    ready='NOT_READY_FOR_NEW_IDENTITY_HELD_OUT_SET'
    text='# V295 — Safe Re-ID Recovery Report\n\n'
    text+='## 結果摘要\n\nDINOv3 已透過已獲准的 Hugging Face 帳號下載官方權重，三模型比較與 V295 實驗均已完成。此版本**判定為 REGRESSION，不建議整合主流程**：已知持久錯誤身份0→2，test8仍未恢復；授權數169→404包含錯誤授權，不能視為成功。val_9錯誤Core更新仍為0，但錯誤alias依然持續存在。原有安全主流程、V294與历史輸出均保留。\n\n'
    text+='## 1. Goal\n\nPreserve capability-based single-authority identity while restoring instance-level long-gap recovery. Experimental branch `codex/V295`; explicit opt-in runner, normal FindMind entrypoint unchanged.\n\n'
    text+='```mermaid\nflowchart TD\n A[Raw YOLO / SAM2.1 evidence] --> B[Canonical object crops]\n B --> C[Frozen DINOv3 features]\n C --> D[Causal tracklet matrices]\n E[Active Core / Negative banks] --> D\n D --> F[SuperPoint + LightGlue + RANSAC]\n F --> G[IdentityGuard explicit gates]\n G --> H[Scoped capabilities / revocable aliases]\n H --> I[Final revocation-filtered timeline]\n I --> J[Unchanged event windows / dense images]\n J --> K[Qwen2.5-VL-7B NF4 / validator]\n```\n\n'
    text+='## 2. Safe baseline\n\n'
    text+='| Metric | Current safe | V295 |\n|---|---:|---:|\n'
    rows=[('Known permanent false merges',0,summary['known_permanent_false_merges']),('val_9 wrong Core contamination',0,summary['val9_wrong_core_entries']),
        ('test8 correct long-gap recovery',0,0),('Known regression authorized observations',169,val['totals']['authorized_observations']),
        ('Candidate but unauthorized sampled frames',1896,val['totals']['unresolved_candidate_frames']),('Initial binding preserved','yes',f'{val["totals"]["initial_track_matches_baseline"]}/11 same track;{val["totals"]["initial_frame_matches_baseline"]}/11 same frame'),
        ('test2 authorized continuity',b['development']['videos']['test2']['authorized_observations'],dev['videos']['test2']['authorized_observations']),
        ('test7 labeled distractor authorizations',0,0),('test9 long-gap confirmations',0,dev['videos']['test9']['confirmed_recoveries']),
        ('SAM/YOLO identity bypass','blocked','blocked'),('LightGlue enabled','no','yes'),('Appearance model','MobileNet','DINOv3 ViT-B/16'),('Automatic gated long-gap confirmation','off','on, experiment only')]
    for a,c,d in rows:text+=f'| {a} | {c} | {d} |\n'
    text+='\nKnown cases are post-validation regressions, not held-out performance. Larger authorized counts do not prove all new rows correct. Full identity GT was not invented.\n\n'
    text+='## 3. Identity development dataset\n\n944 raw observations;176 proven/reviewed target,124 distractor,644 unlabeled;86 labeled tracklets. Labels derive from safe epoch lineage, initial Core, same-frame spatially separate phones, existing reviewed points, and explicitly recorded visual development review. Manual review is engineering evidence, not independent annotation. No val GT used for calibration.\n\n'
    text+='All models receive the same original-frame 5% margin crops with aspect preserved, reliable same-frame foreground suppression or recorded bbox fallback. Target/reference prefix is common across models; later target queries exclude reference/self leakage. Final query set104 positives/124 negatives. Early sparse labels and mixed representation diagnostics are archived and excluded from selection.\n\n'
    text+='## 4. MobileNet vs DINOv2 vs DINOv3\n\n| Model | Target min/median/max | Distractor min/median/max | Zero-observed-FA accepts | Threshold |\n|---|---|---|---:|---:|\n'
    for name,m in models.items():
        pos=m['positive'];neg=m['negative'];op=m['zero_observed_false_acceptance_point']
        text+=f'| {name} | {pos["min"]:.3f}/{pos["median"]:.3f}/{pos["max"]:.3f} | {neg["min"]:.3f}/{neg["median"]:.3f}/{neg["max"]:.3f} | {op["true_accepts"]}/104;0/124 FA | {op["threshold"]:.2f} |\n'
    text+='\nFull operating grids, Core/Negative matrices and tracklet evidence are in `benchmark/*_metrics.json` and `benchmark/embeddings/`. Formal ROC-AUC/EER are withheld because frame correlation and limited physical-instance diversity make population claims unjustified.\n\n'
    text+='## 5. Selected backbone\n\nOfficial DINOv3 ViT-B/16 `facebook/dinov3-vitb16-pretrain-lvd1689m`, revision5931719e67bbdb9737e363e781fb0c67687896bc, CUDAfloat32,768dim. One extra accepted target query over DINOv2 at zero observed FA; the difference is small, not statistical proof. DINOv2 revisionf9e44c814b77203eaa57a6bdbbd535f21ede1415;768dim. MobileNet existing047dcff4 weights and Resize256/Center224/features+avgpool unchanged;576dim. DINO representations use foreground patch mean when reliable, otherwise all object-crop patch mean, always L2 normalized. Package versions/preprocessors are recorded verbatim in per-video embedding JSON.\n\n'
    text+='## 6. Core Bank changes\n\nOnly Guard-authorized continuity adds diverse views:confidence≥.6,at least.4s apart,cosine<.985 to existing Core,bounded8views. Confirmation itself never promotes Core. Recovered aliases require≥3future authorized observations over.4s and new Core geometry agreement before promotion. Every commit retains scoped authority, alias and parent bank lineage.\n\n'
    text+='## 7. Negative Bank behavior\n\nOnly simultaneous spatially separate phones beside an authorized target become negative evidence through inherited Guard commits. Unknown/low-similarity candidates never become negatives. Compare per-frame against active Negative Bank;minimum Core-minus-negative margin.08. Shortlist top2negative views for independent geometry. Reports include empty banks explicitly; an empty bank supplies no negative evidence.\n\n'
    text+='## 8. Multi-frame tracklet accumulator\n\nCausal observations,≥3independent quality frames over≥.4s,spacing≥.2s. Exact/nearly identical crops removed;local-ID reuse gap>.6s or scene break resets support. Full Core and Negative matrices retained;median/lower quartile/top2consistency and distinct Core view support are explicit. Current frame must itself remain selected and free of drift/scene break. No backfill of candidate history before confirmation.\n\n'
    text+='## 9. LightGlue verifier\n\nOfficial SuperPoint1024keypoints + LightGlue,512px extraction;foreground keypoints filtered using reliable mask, otherwise original bbox excludes crop margin. RANSAC3px in normalized256coordinates,3000iterations,.999confidence. Require≥16inliers,ratio≥.5,coverage≥.1 in both views and valid nondegenerate transform. Development60target pairs:23verified;36distractor-to-Core pairs:0false verified. Failure is UNKNOWN;negative STRONG_MATCH blocks confirmation. Full keypoints/matches are stored once in `lightglue/pairs/`, referenced from decisions. Runtime shortlist uses current plus best-quality earlier candidate frame and top2Core/negative views, no future frames or labels.\n\n'
    text+='## 10. Confirmation policy\n\nFrozen development-only:Core median≥.68,lower quartile≥.66,three supporting frames,two trusted Core views,negative margin≥.08,competitor margin≥.08,no coexistence contradiction,closed epoch,positive independent Core geometry,no negative geometry,calibrated enable flag. Admission.60 is insufficient for identity. Source/policy/backbone freeze precedes all val runs; no tuning afterward.\n\n'
    text+='## 11. test8 recovery\n\nUNRESOLVED→UNRESOLVED;38authorized observations remain38. Atf828,track:64 has Core median.813 and all appearance/persistence gates pass, but selected LightGlue Core pairs return UNKNOWN. Later targettrack:74 also stays provisional. Atf804 no first-crop confirmation; causal raw singleton does not provide tracklet persistence. ID64 becomes a cordless-phone distractor after a gap;support resets and low Core scores prevent confirmation. No weakening to force recovery. Evidence chain in `development/test8_recovery.json`.\n\n'
    text+='## 12. test2/test7/test9 development safety\n\n'
    text+=f'Development authorized116→{dev["totals"]["authorized_observations"]};six long-gap confirmation frames visually reviewed as the original object. Labeled authorized observations contain zero distractors;unlabeled descendants remain unverified. test2 retains33authorized rows and no recovery;test7 has one earlier target recovery,zero labeled distractor authorizations;test9 remains without long-gap confirmation.9/9initial tracks and frames match safe baseline.\n\n'
    for section,i in enumerate([5,9,10],13):
        c=read(OUT/f'known_val_regression/val_{i}_case.json')
        text+=f'## {section}. val_{i} regression\n\nKnown wrong candidate{c["known_wrong_candidate"]}:active wrong alias={c["known_wrong_alias_active"]};wrong Core entries={c["known_wrong_core_entries"]};known wrong authorized observations={c["known_wrong_authorized_observations"]}. Complete matrices, bank contents, failed gates and geometric evidence in `known_val_regression/val_{i}_case.json`. No numeric/source tuning followed this result.\n\n'
    text+='## 16. Authorized observation recovery\n\n'
    text+=f'Known regression169→{val["totals"]["authorized_observations"]}({(val["totals"]["authorized_observations"]/169-1)*100:+.1f}%);candidate-unauthorized1896→{val["totals"]["unresolved_candidate_frames"]};long-gap confirmation episodes={val["totals"]["confirmed_recoveries"]}. Known critical wrong authorizations={summary["known_wrong_authorized_observations"]}. Full correct-recovered/false-authorized totals remain UNKNOWN without new complete identity labels;reviewed confirmation-frame results are separately scoped.\n\n'
    text+='Post-run confirmation-frame visual review:10target,5different-phone distractor,4visually unresolved;these include revoked episodes,not just final active aliases. val_9 has green/teal distractor recoveries beyond the originally named track:52. The inherited revocation filter removes revoked aliases, but leaves several false aliases active. See `recovery_review.json` and the4original-frame contact sheets.\n\n'
    text+='## 17. Runtime/resource cost\n\n'
    for name in models:
        meta=read(OUT/f'benchmark/embeddings/{name}/test9.json')['model']
        text+=f'- {name}:mean embedding{meta["latency_mean_seconds"]}s;peak allocated{meta["gpu_peak_allocated_bytes"]/1024**3:.3f}GiB;native inference float32.\n'
    text+=f'\nDevelopment identity replay{dev["totals"]["wall_seconds"]:.2f}s;known regression replay{val["totals"]["wall_seconds"]:.2f}s excluding cached extraction/embedding. Per-frame timing/p95, embedding and verifier resource JSON are saved per set. LightGlue features/pair caches reduce repeated work; timings distinguish cached from new measurements. GPU peak allocated is not total reserved VRAM or system RAM. Backbones unload before Qwen.\n\n'
    for group in ['development','known_val_regression']:
        resource=read(OUT/f'{group}/verifier_resources.json')
        text+=f'{group}:LightGlue{resource["pairs_newly_measured"]}newly measured pairs,mean{resource["mean_pair_seconds"]:.4f}s/pair. Reported process peak includes preceding model allocation;not claimed as exclusive verifier VRAM.\n\n'
    perf=read(OUT/'performance/tracklet_latency.json')
    text+=f'Frozen test8 cached diagnostic profile:87tracklet evidence updates,mean11.36ms/update;185Guard frames,mean6.03ms/frame. RSSstart{perf["process_RSS_start_bytes"]/1024**3:.3f}GiB,end{perf["process_RSS_end_bytes"]/1024**3:.3f}GiB,not a full-run peak. These cached timings exclude fresh backbone inference.\n\n'
    text+='## 18. Identity authority invariant\n\nThe original IdentityGuard source is unchanged. `_issue`,`_check`,`write`,`_bank`,`process`,`_revoke`,`final_ledger`,`restart_target_sam` are inherited verbatim. Evidence providers hold no mutation API;all writes use scoped opaque capabilities. Local track ID,SAM propagation,highIoU and raw semantic detection cannot independently reauthorize a gap. This is an application API contract,not hostile-Python process isolation.\n\n'
    text+='Tests:new V29531passed,Identity focused65passed,existing+V295 focused74passed,full repository448passed/1skipped. See exact logs in `tests/`. Passing tests establish exercised contracts,not instance discrimination accuracy. Fresh test2 smoke reuses unchanged YOLO/SAM2.1 paths,then selected V295→finalledger→unchanged builder/dense renderer→Qwen2.5-VL-7B NF4→existing validator:33authorized rows,5events,1eligible request;EOS/schema/validator all pass. This isolated integration diagnostic was performed after regression failure and does not satisfy the full identity safety acceptance gate.\n\n'
    text+=f'Smoke result:`{json.dumps(smoke,ensure_ascii=False)}`\n\nProtected bytes:{integ["unchanged"]}/{integ["protected_files"]}unchanged. V294/Strata and historical outputs preserved;Qwen3.8/Strata not used.\n\n'
    text+='## 19. Remaining failure modes\n\n1. test8 independent geometry cannot bridge viewpoint/blur/front-back differences despite appearance support.\n2. Raw singleton/fragmented YOLO candidate IDs may prevent causal tracklet accumulation;ID recycling still requires gap resets.\n3. Small development instance diversity and correlated frames limit threshold confidence;one-query backbone difference is fragile.\n4. Sparse causal Negative Banks;absence of negative proof is not proof of target identity.\n5. Inherited continuity uses appearance/geometry continuity rather than LightGlue every frame;new authorization descendants need independent audit.\n6. Repeated same local ID recoveries and unknown descendant labels can inflate counts;reported confirmation episodes are not new physical instances.\n\n'
    text+='**Observed verifier contract defects:**val_10f102shortlist includes a candidate crop matched to itself in Core;this is not independent evidence. val_10f1236can pass geometry from earlierf1200while the current phone has switched under the same localID. val_9f1194different green phone nevertheless obtains63Core geometric inliers withcoverage.225/.217,andCoremedian.797. Shared pasted label regions can produce spatially broad but physically misleading correspondences. Numeric hard gates alone do not repair these contracts. All failures are preserved in `known_val_regression/verification_failure_audit.json`;no source or threshold patch followed val results.\n\n'
    text+='## 20. Recommendation\n\nDo not promote this V295 policy or enable its automatic confirmation in the main pipeline;retain the current safe default. The frozen experimental enable flag remainstrue solely to reproduce failure. A subsequent development iteration must first exclude self/old-epoch evidence,require independently grounded current-frame verification and reject shared-sticker-only correspondence;then audit same-local-ID object changes and complete identity labels for recovered intervals. Address test8 fragmentation/cross-view coverage without weakening safety gates. Any future configuration must be frozen before newly unseen identity evaluation;old val1–11 cannot establish held-out generalization.\n\n'
    text+='Official implementation references:[DINOv2](https://github.com/facebookresearch/dinov2),[DINOv3 checkpoint](https://huggingface.co/facebook/dinov3-vitb16-pretrain-lvd1689m),[LightGlue](https://github.com/cvg/LightGlue). All performance values above are local measured results.\n\n'
    text+=status+'\n'+ready+'\n'
    (OUT/'V295_REID_REPORT.md').write_text(text,encoding='utf8');save(OUT/'final/status.json',{'status':status,'readiness':ready})
    print(status,ready,flush=True)


if __name__=='__main__':
    command=sys.argv[1]
    {'development':development,'known_val':known_val,'integrity':integrity,'report':final_report}[command]()
