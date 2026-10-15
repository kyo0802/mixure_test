"""Incremental preregistration and preservation, followed by engineering manifest."""
import core
import ast,json,re
from collections import Counter
from datetime import datetime,timezone

def table(header,rows):
    def s(v):return str(v).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(header)+' |','|'+'|'.join('---' for _ in header)+'|']+
        ['| '+' | '.join(s(x) for x in row)+' |' for row in rows])

def design():
    core.authorities()
    assert core.read(core.OUT/'STEP_RECEIPT_0.json')['status']=='COMPLETE'
    assert core.read(core.OUT/'STEP_RECEIPT_1.json')['status']=='COMPLETE'
    lock=core.read(core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json')
    fixtures=core.read(core.OUT/'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json')['scenarios']
    candidate=core.read(core.OUT/'prompt_candidate/receipt.json');results=core.read(core.OUT/'matched8_results.json')
    cases=sorted(x['fixture_id'] for x in fixtures if x['intended_stratum']!='WARMUP')
    warmup=next(x['fixture_id'] for x in fixtures if x['intended_stratum']=='WARMUP')
    reps=['MULTI_IMAGE_8','STORYBOARD_8','VIDEO_MATCHED_8']
    matrix=[]
    for f in cases:
        for rep in reps:
            key=f'QWEN_NF4_HOLDOUT_ORDER_REV2/{f}/{rep}/0'
            matrix.append({'fixture_id':f,'representation':rep,'repeat_index':0,'order_sha256':core.byte_sha(key.encode())})
    matrix.sort(key=lambda x:x['order_sha256'])
    variant_b=[x for x in matrix if x['representation']!='VIDEO_MATCHED_8']
    repeatconditions=matrix[:2]
    repeats=[{**x,'repeat_index':i,'performed_after_primary':True} for x in repeatconditions for i in [1,2]]
    video_status=[x['outcome'] for x in results if x['kind']=='SYNTHETIC_EVAL']
    config={'status':'DRAFT_NOT_APPROVED_NOT_EXECUTED','task_id':'PREPARE_QWEN_NF4_PROMPT_CLARIFICATION_AND_MATCHED8_CPU_PREFLIGHT',
       'fixture_manifest_sha256':lock['fixture_manifest_sha256'],'fixture_lock_receipt_sha256':core.sha(core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json'),
       'prompt_candidate_sha256':candidate['prompt_sha256'],'pending_identity_clause_active':False,
       'v2_system_sha256':candidate['v2_system_sha256'],'schema_v1_sha256':candidate['prediction_v1_schema_sha256'],
       'v3_runtime_task_sha256':candidate['v3_construction_sha256'],
       'model':'Qwen/Qwen2.5-VL-7B-Instruct','revision':'cc594898137f460bfe9f0759e9844b3ce807cfb5',
       'quantization':'NF4_DOUBLE_BF16_SDPA','generation':{'max_new_tokens':1024,'do_sample':False,'seed':42},
       'timeouts_s':{'load':120,'generation':300,'request':330},
       'retry_policy':{'generation':0,'infrastructure':1,'infrastructure_only_before_generation_started':True},
       'primary_calls':18,'variant_a_order':matrix,'variant_b_calls':12,'variant_b_order':variant_b,
       'video_arm_authorized':False,'video_arm_status':'BLOCKED_UNTIL_EXPLICIT_FRAME_MATCHED_ONLY_AND_ARRAY_ROUTE_APPROVAL',
       'synthetic_video_outcomes':video_status,'warmup_fixture':warmup,'warmup_calls_proposed':3,
       'warmup_separate_from_scored_18':True,'extra_repeat_calls_proposed':4,'repeat_conditions':repeats,
       'automatic_variant_fallback':False,'order_rule':'sha256(QWEN_NF4_HOLDOUT_ORDER_REV2/fixture_id/representation/repeat_index), seed-independent deterministic interleaving',
       'coverage':{'per_representation_event_bearing_min':2,'per_representation_known_state_applicable_min':1,'pooled_event_bearing_min':6},
       'protocol_frozen':False,'new_model_calls':0}
    core.save('regression_preregistration.json',config)
    ordertable=table(['Order','Opaque fixture','Representation','Order hash'],[(i+1,x['fixture_id'],x['representation'],x['order_sha256']) for i,x in enumerate(matrix)])
    core.save('QWEN_NF4_18_CALL_SYNTHETIC_REGRESSION_PREREGISTRATION.md',f'''# 18-call regression前瞻草案

**DRAFT_NOT_APPROVED_NOT_EXECUTED**。任何實際執行仍需另行明確授權。沒有GPU call或model load。

Variant A：6鎖定evaluationfixtures×3表示法=18，repeatindex0；intended stratum不強制模型輸出。Video CPU均FRAME_MATCHED_ONLY，且native-array尚未接入原V3 transport，所以目前Video arm阻擋；需要明確接受frame-matched-only、時間/alias粒度，以及獨立review nativearray runtime route，不能把CPU通過當原runtime可直接執行。

Variant B：另列6×Multi/Storyboard=12calls，見regression_preregistration.json獨立order；不是自動fallback，須人工選定才能啟動。不能將12個有利結果與未核准Video合併充作18。

Warmup用獨立fixture `{warmup}`，若啟用，每表示法一次=3額外calls，不評分，不用evaluationfixtures暖機。repeatability另2固定conditions×2extra同設定repeats=4calls，primary之後執行；condition由已公布order前兩項決定，不按event answers選。若選Variant B，需另固定其repeatconditions，不偷偷沿用不可用Video條件。若完整Variant A+warmup+repeat獲批准，明確總上限25calls（18+3+4），不是暗中把warmup算進18。僅批准18不自動授權額外7。

排序：sha256(QWEN_NF4_HOLDOUT_ORDER_REV2/opaque_fixture/representation/repeat_index)，固定無隨機抽樣；模型seed42與runorder無關。先公布order/hash，不能按輸出重排。

{ordertable}

工程接受：所有18輸出均須通過完整authoritative strict parser、schema、semantic、citation。分階段報，不能用schema pass掩蓋known-state問題。每表示法6份中至少2份event-bearing且至少1份known-state support適用，合併至少6/18event-bearing；這是branchcoverage提案，不是eventtruth要求。報intendedstrata（private）、emittedcounts、event-bearing和zero-event各strictvalidity、abstention以及knownstate是否被測到。覆蓋不足→EVENT_BEARING_BRANCH_NOT_EXERCISED，不能說原缺陷解決。forcedbranch另決策，不能製造事件。

Verdicts：REGRESSION_PASS=全部valid且coverage達標；STRUCTURAL_PASS_COVERAGE_INSUFFICIENT=全部valid但coverage不足；REGRESSION_FAIL=任一已完成輸出strict/runtime失敗；REGRESSION_INCOMPLETE=必要calls缺少，另列已知failure，不隱藏未完成。Variant B為12call独立variant，其每rep2/6、knownstate1/6和pooled4/12 coverage須在選B時獨立批准；不得套用18call的pooled6而不說明。

凍結待批准的componentmanifest：model revision/localassetmanifest、NF4、V2system、V1Cprompt、PredictionV1、validator、runtime/backend、model-visiblepayloadcontract、fixturesmanifest、repconfig、processorconfig、alias/native/modeltime mapping、order、generation和retry policy，各別hash。當前component/hash見prompt_candidate/receipt、processor_source_inventory、regression_preregistration與DELIVERABLE_MANIFEST；未整合的native-array bridge與尚未批准的條款不能產生假的finalruntime hash。

負面結果原raw/resource/開始邊界/EOS/token/partialfailure均保留。generationretry0；infra最多1且generation未開始有證據，不能按結果重試。OOM不自動降pixel/frame、不換模型；timeout不依答案增deadline；invalidJSON/citation不修補、不當作no-event。fixedgreedy/seed不保證bitwise重複，repeat是工程重現性不是獨立session。

本任務只一個candidate；未來失敗保留並回humanreview，最多再一個另批、另版本candidate，沒有自動迭代。沒有full-schema答案examples。測試是engineering，不是event detection、precision/recall/F1/hallucination測量或泛化/顯著/因果證據。

Timing敏感度0/.2/.5全報、point/interval/uncertainstatusaware一對一matching在realDEV仍待獨立批准；syntheticstrata只是designerintention，這個regression不grade physicaleventtruth。
''')
    core.receipt(3,[core.OUT/'STEP_RECEIPT_1.json',core.OUT/'STEP_RECEIPT_2.json',core.OUT/'SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json'],
       [core.OUT/'regression_preregistration.json',core.OUT/'QWEN_NF4_18_CALL_SYNTHETIC_REGRESSION_PREREGISTRATION.md'],
       'DRAFT_NOT_APPROVED_NOT_EXECUTED',video_arm_blocked=True,automatic_fallback=False)
    decision_rows=[
      ('Prompt','V1C659tasktokens，原contract保留','批准核心A/B/C，仍不含identity條款','未測branchcoverage','YES'),
      ('Target ambiguity','INSUFFICIENT_EVIDENCE CPU接受；無新schema','單獨批准或拒絕pendingexactclause','technicalacceptance≠policyapproval','YES'),
      ('Matched Video8','13/13 CPUarray source/order匹配','接受FRAME_MATCHED_ONLY或選12callB','pairedtime與8alias/4unit；原runtimebridge未實作','YES'),
      ('Reference NONE','沒有referencepixels／extra tokens','六clean DEV commonNONE','opaqueTARGET_A可能無unique association','YES'),
      ('Pixels','200704 effectivecap；actualgrids已記','固定原cap/3col480×270+32label','2016/240/1008visualtokens不相等','YES'),
      ('Sampling','六DEV既有uniform8indices全重現','原round ties-to-even/endpoints','可能漏短事件；不調offset','YES'),
      ('Output budget','原633max、無capfailure；candidate尚未推論','1024/greedy/seed42','realmulti-event容量未知','YES'),
      ('Timeout','load120/gen300/request330 proposal','固定界線且preservepartial','18×330=99min未含load/prep/retry','YES'),
      ('Matching time','原V2status+nativePTS權威保存','0/.2/.5全報；point/closedinterval/uncertainUNDEFINED、一對一','現greedy/evaluatorstatus須獨立review；不拿wholeevidenceenvelope當duration','YES'),
      ('Run order','prospective18与12orderhash已列','批准選定variantorder及optionalrepeat','未按答案排序；最後runtimehash尚缺','YES'),
      ('Holdout','六evaluation+onewarmup先鎖再prompt','沿已鎖manifest，不改fixture','作者知概念；2.5Drender與realworld差異','YES'),
      ('Regression','18/12variants+coveragegate已寫','另授權明確variant/extra warmup/4repeat數','尚未批准、未執行、無效能證据','YES'),
      ('Real cohort','2knownpickup/3negative/1uncertain，test3排除','limitedexploratory；formal0','causality/sessionindependence未建立','YES'),
      ('Actual freeze','沒有任何newfreeze','後續finalsettings/componenthash定稿再人審','21項仍有UNRESOLVED','YES_SEPARATE_GATE'),
    ]
    blockers=[
      ('1 collect-all replay','RESOLVED'),('2 Validator hash unchanged','RESOLVED'),('3 known-state taxonomy','RESOLVED'),
      ('4 prompt candidate approved','UNRESOLVED'),('5 identity clause approved/rejected','UNRESOLVED'),('6 fixtures locked before prompt','RESOLVED'),
      ('7 regression design approved','UNRESOLVED'),('8 regression executed/reviewed','UNRESOLVED'),
      ('9 CPU preflight performed DEV/synthetic','RESOLVED'),('10 native/model-time mapping for approved use','UNRESOLVED'),
      ('11 runtime model-consumed alias policy/granularity','UNRESOLVED'),('12 approved representation budgets','UNRESOLVED'),
      ('13 point/interval/uncertain matching approved','UNRESOLVED'),('14 timing sensitivity approved','UNRESOLVED'),
      ('15 approved final model-visible prompt hashes','UNRESOLVED'),('16 generation settings approved','UNRESOLVED'),
      ('17 failure/retry approved','UNRESOLVED'),('18 proposed run order fixed','RESOLVED'),
      ('19 source cohort fixed','RESOLVED'),('20 frame/fixture/sourceasset hashes verified','RESOLVED'),
      ('21 explicit final protocol human approval','UNRESOLVED')]
    core.save('freeze_blockers.json',{'status':'PROTOCOL_NOT_READY_TO_FREEZE','items':dict(blockers),'no_freeze_receipt':True})
    core.save('QWEN_NF4_PILOT_DECISION_PACKAGE_V3.md',f'''# Pilot decision package V3

**PROPOSED_AWAITING_USER_APPROVAL；PROTOCOL_NOT_READY_TO_FREEZE**。

Sampling policy UNIFORM_8和representation Multi/Storyboard/Video是不同軸，不列成同級條件。六cleanDEV：test1 W03/W05dedup、test2 W01、test5 W01 casealerts；test5W05/test7W05 non-exhaustive knownPICKUPmatching；額外predictions UNEVALUATED；test8uncertainty descriptive；test3excluded禁止cleanrun。formaleligible0、CAUSALITY_UNVERIFIED，無正式metrics/泛化/sessionindependence聲稱。

{table(['Decision','Verified evidence','Proposed setting','Unresolved risk','User approval required'],decision_rows)}

## 21個freeze gate

{table(['Requirement','Status'],blockers)}

CPU數值mapping已建立並保存，不代表Video已符合批准的精度與aliaspolicy。原V3runtime固定encodedvideo sampling路徑，publicnativearray預檢沒有偷偷修改backend；futurebridge是否可整合須獨立審查與授權。0.1s偏差界線仍只是本任務要求測試的proposal。

GT匹配提案沿前audit：exactsource PTS以tick/timebase或Decimal表示，不加浮點epsilon當真值；bounded使用人工存的event_time而不是整段before/after證據包，closedinterval最短距離；uncertainGT/pred timingunknown→time compatibilityUNDEFINED，type另描述；最大一對一matching/tie規則需獨立CPUgate。沒有在本任務修改evaluator、計分或定tolerance。0/.2/.5全部報而非挑最佳。

精確下一步：請人審核心prompt、pendingidentityclause、Video FRAME_MATCHED_ONLY與12callvariant選擇、budget/retry/coverage等表。若選A，還須批准原生array與runtime橋接的獨立工程任務，不能直接執行本CPU腳本充作VLMregression；若選B，可另授權固定12callsyntheticregression及明確optionalwarmup/repeat數。未收到明確新授權前，不跑任一variant。

之後freeze和RUN_PHASE2B_EXPLORATORY_PILOT仍是兩道獨立人類gate。此次準備任務不授權任一推論。
''')
    core.receipt(4,[core.OUT/'STEP_RECEIPT_3.json',core.OUT/'prompt_candidate/receipt.json'],
       [core.OUT/'QWEN_NF4_PILOT_DECISION_PACKAGE_V3.md',core.OUT/'freeze_blockers.json'],'AWAITING_USER_APPROVAL')
    print({'preregistration':'DRAFT_NOT_APPROVED_NOT_EXECUTED','variantA':18,'variantB':12,'warmup_extra':3,'repeat_extra':4,'protocol':'NOT_READY'})

def preservation():
    core.authorities();before=core.read(core.OUT/'PREFLIGHT_BEFORE.json');changed=[]
    for n,h in before['files'].items():
        p=core.ROOT/n
        if not p.is_file() or core.sha(p)!=h:changed.append(n)
    def command(args):
        p=core.subprocess.run(args,cwd=core.ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    after={'timestamp':datetime.now(timezone.utc).isoformat(),'git':core.git(),
       'gpu':command(['nvidia-smi','--query-gpu=index,name,memory.used,memory.free,utilization.gpu','--format=csv,noheader']),
       'compute_processes':command(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader']),
       'running_processes':command(['powershell','-NoProfile','-Command','Get-Process | Select-Object Id,ProcessName | ConvertTo-Json -Compress'])}
    scan=[];forbidden=[]
    for p in core.OUT.rglob('*.py'):
        text=p.read_text();calls=[]
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node,ast.Call):continue
            if isinstance(node.func,ast.Attribute):
                if node.func.attr in {'generate','from_pretrained'}:
                    spelling=ast.unparse(node.func);allowed=spelling=='AutoProcessor.from_pretrained';calls.append({'line':node.lineno,'call':spelling,'processor_only_allowed':allowed})
                    if not allowed:forbidden.append((str(p),node.lineno,spelling))
            if isinstance(node.func,ast.Name) and node.func.id in {'serve','serve_forever','uvicorn'}:forbidden.append((str(p),node.lineno,node.func.id))
        scan.append({'script':str(p.relative_to(core.OUT)),'sha256':core.sha(p),'sensitive_calls':calls})
    result={'protected_files_checked':len(before['files']),'changed_files':changed,'git_before':before['git'],'git_after':after['git'],
       'git_unchanged':before['git']==after['git'],'before_gpu':before['gpu'],'after_gpu':after['gpu'],
       'before_compute_processes':before['compute_processes'],'after_compute_processes':after['compute_processes'],
       'environment':{k:core.os.environ[k] for k in ['CUDA_VISIBLE_DEVICES','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE']},
       'script_scan':scan,'forbidden_calls':forbidden,'processor_pretrained_calls_only':True,
       'new_model_calls':0,'GPU_inference':0,'phase2a_predictions':0,'freezes':0,'graph_writes':0,'commit_push':0,
       'verification_scope':'Own scripts and guarded CPU calls, before/after observed processes, listed hashes. Not a continuous machine-wide trace or proof about unrelated processes.'}
    core.save('PREFLIGHT_AFTER.json',after);core.save('preservation.json',result)
    if changed or not result['git_unchanged'] or forbidden:raise RuntimeError('INTEGRITY_BLOCKED')
    tests=core.read(core.OUT/'cpu_tests.json')
    core.save('QWEN_NF4_CPU_PREFLIGHT_PRESERVATION_REPORT.md',f'''# CPU預檢保存報告

Before/after保護 {result['protected_files_checked']} 檔，changed={changed}；Git HEAD/index/trackeddiff/stageddiff/status均不變。HEAD={after['git']['head']}。原Validator、PredictionV1、V2格式、V3runtime/code、historicalcapacity raw/receipts、Phase2a policy/GT與sidecars均在保護範圍。6權重binary不讀、不copy、不load；原權重metadata沿既有manifest，沒有本次model能力宣稱。

GPU before={before['gpu']}；GPU after={after['gpu']}；computeprocessbefore/after在preservation.json，全部runningprocesslist在PREFLIGHT_BEFORE/AFTER。Nvidia WDDM/N/A與外部程序限制保留；記憶體變動可来自其他程序，不是單靠GPU數值證明否定。所有script環境={result['environment']}；CPUprocessor每次記cuda_initialized=false。

強制：network socket connect拒絕，weightbinary open拒絕，torch.load/jit.load/CUDA初始化拒絕，PreTrainedModel.from_pretrained和GenerationMixin.generate被fail-closed guard取代；只有本機AutoProcessor.from_pretrained local_files_only/trust_remote_code=false，沒有serverlaunch。全新script AST scan={len(scan)}檔，forbiddencalls={forbidden}；permitprocessor唯一loader記錄完整。Torch/PIL/processor CPU張量是影格處理，不是model forward。只存張量shape/hash，沒有大型tensor檔。

CPU tests={tests}。同60uniquechecks最後全pass；最初opaquefilename測試以POSIXslash解析Windows路徑而誤報，初始testlog及序列化失敗的空json保存在processor_diagnostics/cpu_tests_initial。修正test Path.name及error-to-string後重跑，不改fixtures/prompt/validator；不把兩次測試加成120unique。

CPUprocessor初版請求return_metadata=true又return_tensors=pt，VideoMetadata不能tensorize；另一次float32 seconds_per_grid被不合理1e-12精度assert阻擋。保留trialinputs/log，不改原runtime；正式CPU稿return_metadata=false，另存metadata觀察；時間採actualfloat32輸出，nominal對照仅做serialization精度check。這是CPU預檢instrumentation修正，不是model-output repair或自動generation retry。locked56sourceframes與generatorhash保持原樣。

Shadow對wrong-type list enums增加dependencytypeguard，原33影子/strict结果重確認不變，STEP_RECEIPT_0_CONFIRMATION記before/aftermodulehash；productionvalidator不改。Prompt第一次literalguard把ontology lifted當私有lift子字串，採wholeliteral檢查後才寫prompt，沒有生成第二個候選。

new_model_calls=0，GPUinference=0，Phase2apredictions=0，freeze=0，Graphwrites=0，commit/push=0。核對範圍只涵蓋本任務script與guard、所列29kfilehash、開始/結束processsnapshot，不是全機連續追蹤，不能证明別的程式沒有GPU活動。所有新writes限本namespace。工程fixturelock不是protocolfreeze。
''')
    core.receipt(5,[core.OUT/'PREFLIGHT_BEFORE.json',core.OUT/'cpu_tests.json'],
       [core.OUT/'PREFLIGHT_AFTER.json',core.OUT/'preservation.json',core.OUT/'QWEN_NF4_CPU_PREFLIGHT_PRESERVATION_REPORT.md'],protected_changes=0,new_model_calls=0)
    print({'protected_files':len(before['files']),'changed':changed,'git_unchanged':result['git_unchanged'],'AST_scanned':len(scan),'forbidden':forbidden})

def seal():
    core.authorities();results=core.read(core.OUT/'matched8_results.json');p=core.read(core.OUT/'prompt_candidate/receipt.json')
    tests=core.read(core.OUT/'cpu_tests.json');preservation=core.read(core.OUT/'preservation.json')
    gates=core.read(core.OUT/'diagnostics/frequencies.json')['gates']
    positions=core.read(core.OUT/'MODEL_VISIBLE_TEMPORAL_POSITION_AUDIT.json')
    byid={x['id']:x for x in positions['rows']}
    assert all(gates.values()) and tests['passed']==60 and not preservation['changed_files']
    core.save('PASS_T_PHASE2B_QWEN_NF4_PROMPT_MATCHED8_PREFLIGHT_REPORT.md',f'''# FindMind Pass T Phase2b Revision2 完成報告

2026-10-15。**PASS_T_PHASE2B_QWEN_NF4_PROMPT_MATCHED8_PREFLIGHT_COMPLETE_AWAITING_USER_APPROVAL**。

## 1–3 Strict與完整shadow

33/33 strictreplay一致，原15/33pass不變，G2–G5全部PASS。13attempt/18欄位emptytiming、5attempt/5emptywindowlists，11attempt/20maskedknownstatesupport。knownstate breakdown：after_state11、before_state6、laststate3。分NA/NE/SAT/VIOL與原errorfirst順序保留；沒有自造HIGHconfirmedfail。完整JSONL、frequencies、影子dependency修正confirmation均有hash和receipt。

## 4–6 Fixture與prompt

6eval（0/1/2intended各2）+1warmup，56新CPUscene影格，先lock再prompt。鎖回條SHA={p['fixture_lock_receipt_sha256']}，manifest與所有pixels鎖定，promptreceipt直接引用lockhash與Step0B，非僅時間戳。沒有舊capacityimages、realPhase2apixels或舊raw作syntheticinputs；作者仍知場景概念，不声稱概念blind。脚本意圖不等於modelrecognizedevents。

唯一候選：[QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt](QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt)，SHA `{p['prompt_sha256']}`，{p['file_size']}bytes、exacttask-onlytokens={p['tokenizer']['token_count']}（Qwen2TokenizerFast/transformers4.57.6，無system/schema/media expansion）。只新增A非空時間解释、B各outcome引用、Cknown/unknownstate證據規則；V1schema/V2system/V3runtime不改；沒有答案examples。D身分條款只在[TARGET_IDENTITY_AMBIGUITY_CLAUSE_PENDING_APPROVAL.md](TARGET_IDENTITY_AMBIGUITY_CLAUSE_PENDING_APPROVAL.md)，core不含、未批准、未啟用。

## 7–9 Matched8與時間限制

{table(['Case','Kind','Outcome','Max nominal Δs','Max processor-unit Δs','Max static-model-position proxy Δs'],[(x.get('source',x['id']),x['kind'],x['outcome'],x.get('time',{}).get('max_abs_nominal_deviation_s'),x.get('time',{}).get('max_abs_model_patch_deviation_s'),byid[x['id']]['max_abs_proxy_deviation_s']) for x in results])}

六DEV+六eval+warmup全部FRAME_MATCHED_ONLY。八個sourceRGBdigest/order/lineage/Uniform8與前receipt位置一致；原生VideoarraypublicAPI有video_grid_thw，沒有影像列表冒充Video，也没有forward。無container，所以encodedtime=null；nativePTSprivate，Video時間以fps作uniform重建。actual2frame/patch→4時間位置，相對native每frame偏差超0.1proposal；nominal8frameCFR可能很接近native，但不可忽略actualtemporalunit量化。reason詞CFR_TIME_DISTORTION在此指uniform reconstruction/temporalunits的偏差，並非宣稱有containerCFR。影像/storyboardORDER_ONLY，原生時序沒提供；無time-information/pixel/tokenparity聲稱。

8sourcealiases可通過membership，但模型是否逐frame辨識尚未證明；RUNTIME_CONSUMPTION_NOT_VERIFIED。原V3runtime走AVI，nativearrayroute尚未整合，是另個工程決策。不能把本CPUpreflight接成GPUrun。詳細sourceIDs/nativePTS/digests、tiletransforms、observer/grid/tensorhash、perframe rawdeviation見[Matched8 CPU report](QWEN_NF4_MATCHED_VIDEO8_CPU_PREFLIGHT_REPORT.md)及private_mappings。

補充[model temporal-position audit](MODEL_VISIBLE_TEMPORAL_POSITION_AUDIT.md)為Step2必要合讀：實際config tokens_per_second=2，get_rope_index再.long()，表中另列staticmodelpositionproxy；它不同於processorgrid秒數，也不是呼叫model得出的runtime證據。

## 10 Regression草案

[18-call preregistration](QWEN_NF4_18_CALL_SYNTHETIC_REGRESSION_PREREGISTRATION.md)：6fixture×3rep，固定hash交錯，Video arm未批准而阻擋；VariantB獨立12call，不自動fallback。獨立warmup最多3與2condition×2repeat=4均另計且需另批。每rep>=2/6event-bearing、>=1knownstate適用，pooled>=6/18；所有strictvalid+coverage才REGRESSION_PASS，否則STRUCTURAL_PASS_COVERAGE_INSUFFICIENT/FAIL/INCOMPLETE，不能强迫事件以填coverage。Generationretry0，infra最多1僅開始前；一candidate失敗停止，最多一個另批revision，未執行。

## 11–12 Tests／保存

60 uniqueCPUchecks＋3個modelposition計算檢查全部PASS；{preservation['protected_files_checked']}既有檔案hash全不變，Git HEAD/index/worktree不變。所有script設CUDA_VISIBLE_DEVICES=-1、HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1，網路/權重/model-pretrained/generation/CUDAinit failclosed，scriptAST沒有非processorfrompretrained/generate/serverlaunchcall。GPU/processbeforeafter與CPUcuda_initialized紀錄保留；對外部程序沒有連續trace，不聲稱hash能证明全機否定。new_model_calls0、GPUinference0、realPhase2a prediction0、protocolfreeze0、Graphwrite0、commit/push0。

## 13–14 剩餘gate／下個授權

PROTOCOL_NOT_READY_TO_FREEZE。21gate見[Pilot decision package](QWEN_NF4_PILOT_DECISION_PACKAGE_V3.md)：核心prompt、identityclause、NONE語意、Videoframeonly與alias精度、nativearrayruntimebridge、budget/generation/retry/時間matching/敏感度、regression與最終protocol仍需human決策。knownPICKUPonly、negativecasealerts、test8descriptive、test3excluded、formal0與CAUSALITY_UNVERIFIED保留。

下一步需要你的**明確選擇與授權**：批准或拒絕V1C及独立identityclause；選18callVariantA（先另行runtimebridge審查及FRAME_MATCHED_ONLY批准），或獨立12callVariantB；明示warmup/4extra-repeat是否授權，再授權該版本的有限syntheticregression。未決前不執行任何calls。Regression結果審阅後的protocolfreeze和RUN_PHASE2B_EXPLORATORY_PILOT仍各自獨立授權。

本次成功條件是CPUdiagnostic、先鎖fixtures、單一candidate与诚實preflight；沒有宣稱事件偵測改善或GPU成功。所有stepreceipts和檔案hash列在DELIVERABLE_MANIFEST.json，這是工程交付manifest而非humanapprovedprotocolfreeze。
''')
    required=['COLLECT_ALL_VALIDATOR_DIAGNOSTIC_REPORT.md','COLLECT_ALL_ATTEMPT_VIOLATIONS.jsonl',
      'SYNTHETIC_HOLDOUT_FIXTURE_MANIFEST.json','SYNTHETIC_HOLDOUT_LOCK_RECEIPT.json','QWEN_NF4_EVENT_REASONING_PROMPT_V1C.txt',
      'TARGET_IDENTITY_AMBIGUITY_CLAUSE_PENDING_APPROVAL.md','PROMPT_CLARIFICATION_TRACEABILITY.md',
      'QWEN_NF4_MATCHED_VIDEO8_CPU_PREFLIGHT_REPORT.md','QWEN_NF4_18_CALL_SYNTHETIC_REGRESSION_PREREGISTRATION.md',
      'QWEN_NF4_PILOT_DECISION_PACKAGE_V3.md','QWEN_NF4_CPU_PREFLIGHT_PRESERVATION_REPORT.md',
      'PASS_T_PHASE2B_QWEN_NF4_PROMPT_MATCHED8_PREFLIGHT_REPORT.md']
    assert all((core.OUT/n).is_file() and (core.OUT/n).stat().st_size for n in required)
    assert core.git()==preservation['git_after']
    core.receipt('FINAL',[core.OUT/'STEP_RECEIPT_5.json'],[core.OUT/n for n in required],
       'PASS_T_PHASE2B_QWEN_NF4_PROMPT_MATCHED8_PREFLIGHT_COMPLETE_AWAITING_USER_APPROVAL')
    files={str(p.relative_to(core.OUT)):core.sha(p) for p in sorted(core.OUT.rglob('*')) if p.is_file()}
    core.save('DELIVERABLE_MANIFEST.json',{'kind':'ENGINEERING_DELIVERABLE_MANIFEST_NOT_PROTOCOL_FREEZE',
       'status':'PASS_T_PHASE2B_QWEN_NF4_PROMPT_MATCHED8_PREFLIGHT_COMPLETE_AWAITING_USER_APPROVAL',
       'required_deliverables':required,'files_sha256':files,'new_model_calls':0,'protocol_approved':False,
       'identity_clause_approved':False,'regression_executed':False,'prompt_candidate_count':1})
    for p in core.OUT.rglob('*'):
        if p.is_file():p.chmod(0o444)
    assert all(core.sha(core.OUT/n)==h for n,h in files.items())
    print({'status':'PASS_T_PHASE2B_QWEN_NF4_PROMPT_MATCHED8_PREFLIGHT_COMPLETE_AWAITING_USER_APPROVAL','sealed_files':len(files)+1,
       'manifest_sha256':core.sha(core.OUT/'DELIVERABLE_MANIFEST.json'),'required_artifacts':len(required)+1})

if __name__=='__main__':
    import sys
    {'design':design,'preservation':preservation,'seal':seal}[sys.argv[1]]()
