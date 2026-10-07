"""Publish measured identity rebuild results without modifying historical outputs."""
from pathlib import Path
import ast,json,sys,time,runpy
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from memory_graph.identity.pipeline import ROOT,OUT,read,write,sha

def tests(name):
    root=ET.parse(OUT/f'tests/{name}.xml').getroot()
    rows=root.findall('.//testcase')
    return {'total':len(rows),'passed':sum(not any(r.find(k) is not None for k in ('failure','error','skipped')) for r in rows),
        'failed':sum(r.find('failure') is not None for r in rows),'errors':sum(r.find('error') is not None for r in rows),
        'skipped':sum(r.find('skipped') is not None for r in rows),
        'cases':[{'name':r.attrib['name'],'class':r.attrib.get('classname'),
            'status':'FAILED' if r.find('failure') is not None or r.find('error') is not None else 'SKIPPED' if r.find('skipped') is not None else 'PASSED'} for r in rows]}

def table(metrics):
    lines=['| 影片 | 初始 track/影格一致 | 授權影格舊→新 | 有候選但未授權影格 | 新長間隔確認 |', '|---|---|---:|---:|---:|']
    for v,m in metrics['videos'].items():
        match=m['initial_track_matches_baseline'] and m['old_initial_frame']==m['new_initial_frame']
        lines.append(f"| {v} | {match} | {m['old_authorized_sampled_frames']} → {m['authorized_observations']} | {m['unresolved_candidate_frames']} | {m['confirmed_recoveries']} |")
    return '\n'.join(lines)

def synthetic():
    fixtures=runpy.run_path(str(ROOT/'tests/test_identity_authorization.py'))
    bound,obs=fixtures['bound'],fixtures['obs'];cases=[]
    def record(name,g,passed):
        if not passed:raise AssertionError(name)
        s=g.snapshot();cases.append({'scenario':name,'passed':passed,'epochs':s['epochs'],
            'aliases':s['aliases'],'decisions':s['decisions'],'banks':s['banks'],
            'final_authorized_observations':len(g.final_ledger()),'ledger_history_count':len(s['ledger'])})
    g=bound();g.process(4.,[obs(4.,'new',sam_overlap=1.)]);record('post-gap inherited SAM + raw phone IoU',g,len(g.snapshot()['aliases'])==1)
    g=bound();g.process(4.,[obs(4.,'new')]);record('single perfect appearance score stays provisional',g,g.snapshot()['decisions'][-1]['decision']=='PROVISIONAL')
    g=bound();g.process(4.,[obs(4.,'a'),obs(4.,'b',box=(100.,0.,120.,30.))]);record('similar coexisting competitors',g,all(d['decision']=='AMBIGUOUS' for d in g.snapshot()['decisions'][-2:]))
    g=bound();g.process(.6,[obs(.6,drift=True,sam_overlap=1.)]);record('drift blocks same local ID',g,len(g.final_ledger())==1)
    g=fixtures['strong_recovered']();record('synthetic full multi-evidence confirmation',g,len(g.snapshot()['aliases'])==2)
    g=fixtures['strong_recovered']();g.process(4.6,[obs(4.6,'new'),obs(4.6,'track:1',box=(100.,0.,120.,30.))]);record('original returns: revoke recovered alias and descendants',g,not any(x['candidate_id']=='new' for x in g.final_ledger()))
    g=bound();g.process(.6,[obs(.6),obs(.6,'other',vector=(0.,1.),box=(100.,0.,120.,30.))]);g.process(4.,[obs(4.,'other',vector=(0.,1.))]);record('known coexisting distractor rejected later',g,g.snapshot()['decisions'][-1]['decision']=='REJECTED')
    return {'scope':'DETERMINISTIC SYNTHETIC CONTRACTS; enabled confirmation fixtures are not production policy','passed':len(cases),'total':len(cases),'cases':cases}

def main():
    dev=read(OUT/'development/identity_metrics.json');val=read(OUT/'known_validation_regression/val_1_to_11_identity_metrics.json')
    unit,full,focused=tests('unit'),tests('full'),tests('focused')
    for result in (unit,full,focused):
        if result['failed'] or result['errors']:raise RuntimeError('Tests not passing')
    write(OUT/'tests/unit_results.json',unit);write(OUT/'tests/full_test_results.json',full)
    write(OUT/'tests/focused_regression_results.json',focused);write(OUT/'tests/synthetic_identity_results.json',synthetic())
    # Preservation checks include original snapshot and all paths referenced by historical manifests.
    original=read(OUT/'audit/prechange_manifest.json')['files'];errors=[];unreadable=[]
    for rel,h in original.items():
        p=ROOT/rel
        try:
            if not p.is_file() or sha(p)!=h:errors.append(rel)
        except PermissionError as exc:
            unreadable.append({'path':rel,'error':str(exc)})
    from memory_graph.v293.report import verify as verify_v293
    from memory_graph.reasoning.pipeline import verify_manifest
    v293=verify_v293();reference=verify_manifest(ROOT/'outputs/current_development',ROOT/'outputs/current_development/final/final_integrity_manifest.json')
    critical_unreadable=[r for r in unreadable if not any(part.startswith('.pytest') for part in Path(r['path']).parts)]
    integrity={'prechange_files_in_snapshot':len(original),'prechange_files_checked':len(original)-len(unreadable),
        'unreadable_historical_temporary_files':unreadable,'prechange_errors':errors,'V293':v293,'current_development_reference':reference,
        'validation_files_checked':sum(r.startswith('outputs/validation/') for r in original),'verified_unix':time.time(),
        'valid':not errors and not critical_unreadable and v293['valid'] and reference['valid'],
        'scope':'All required frozen artifacts and all readable prechange files; inaccessible historical pytest scratch files are explicitly unverified, not claimed unchanged.'}
    if not integrity['valid']:raise RuntimeError(integrity)
    write(OUT/'final/preservation_verification.json',integrity)
    modules={}
    sources=list((ROOT/'src/memory_graph/identity').glob('*.py'))+[ROOT/'scripts/run_findmind.py']
    for path in sources:
        tree=ast.parse(path.read_text(encoding='utf8'));imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):imports.append('.'*node.level+(node.module or ''))
            elif isinstance(node,ast.Import):imports.extend(a.name for a in node.names)
        modules[path.relative_to(ROOT).as_posix()]={'sha256':sha(path),'imports':sorted(set(imports))}
    source_hashes={p.relative_to(ROOT).as_posix():sha(p) for p in sources}
    freeze=read(OUT/'development/development_freeze.json')
    frozen_normalized={p.replace('\\','/'):h for p,h in freeze['identity_source_hashes'].items()}
    if source_hashes!=frozen_normalized:raise RuntimeError('Identity source drift after development freeze')
    write(OUT/'final/source_hashes.json',source_hashes)
    write(OUT/'final/active_identity_manifest.json',{'entrypoint':'scripts/run_findmind.py','authority':'memory_graph.identity.guard.IdentityGuard',
        'current_documentation':'CURRENT_PIPELINE.md','historical_readme_byte_frozen':True,'modules':modules,
        'decision_policy':read(OUT/'calibration/confirmation_policy.json'),'identity_authority_count':1,
        'final_regression_run_directory':'runs_final','legacy_reference_only':['v21.pipeline','v23.fusion','v24.reid','v25rerun.fusion','v26.pipeline','v292.pipeline','validation.upstream','scripts/run_current_pipeline.py'],
        'current_raw_sam_seed':'live capability only; propagated masks UNVERIFIED',
        'restored_legacy_bytes':True,'token_security_scope':'application API; not hostile in-process Python isolation'})
    qwen=read(OUT/'development/runs_final/test2/prepared/qwen/responses.json')
    if not qwen or not all(r['trace'].get('ended_with_EOS') for r in qwen):raise RuntimeError('Final downstream smoke incomplete')
    raw=read(OUT/'smoke_raw_test2_final/metrics.json')
    if not raw['fresh_yolo'] or not raw['fresh_sam']:raise RuntimeError('Raw execution not verified')
    # Additional metrics are actual state counts, not inferred accuracy.
    secondary={}
    for kind,metrics in [('development',dev),('known_validation_regression',val)]:
        acc={'epochs':0,'epoch_breaks':0,'core_entries':0,'quarantined_entries':0,'negative_entries':0,'revoked_aliases':0,'rejected_bank_updates':0}
        decisions={}
        for video,m in metrics['videos'].items():
            for k in acc:acc[k]+=m[k]
            for k,n in m['decision_counts'].items():decisions[k]=decisions.get(k,0)+n
        secondary[kind]={**acc,'candidate_decisions':decisions,'real_correct_recovery_latency_seconds':None,
            'latency_reason':'No real long-gap recovery confirmed; frame cost includes decode/embedding and cannot be called recovery latency.'}
    write(OUT/'final/secondary_metrics.json',secondary)
    report=f'''# FindMind 身份授權重建報告

日期：2026-10-03。工作範圍：mixure_test_SAM；相鄰 mixure_test 未寫入。

## 1. Executive summary

**目前 canonical 路徑已移除 SAM／YOLO overlap 直接授予持久身份的旁路，身份授權集中於一個 IdentityGuard。** 已知錯誤合併 3→0，val_9 錯誤核心外觀寫入 12→0；初始綁定維持 development 9/9、已知回歸 11/11，track 與綁定影格一致。

判定為 **部分成功**：正式政策尚無可辯護的長間隔強確認校準，因此保持 PROVISIONAL；test8 正確回收退回未解決。已知集授權影格 896→169，不能把安全改善描述為整體辨識能力提升。沒有進行新一輪 held-out accuracy 測量。

## 2. Previous failure mechanisms

A：val_5／val_10 的 SAM inherited ID 在丟失後仍被保留，raw phone 高 IoU 經 `_attach(trusted=True)` 成為可信觀測，再把新 track 寫入 phone_01；根本不需要通過 Re-ID appearance guard。

B：val_9 單一候選 crop similarity 0.7287、margin 0.1629 通過舊 guard，立即 alias、重啟 SAM 並產生 12 個後續 bank updates。這是外觀誤確認，不是 A 的結構旁路。

C：val_8／val_11 是身份回收未解決。新系統保留不確定性，沒有把它們宣稱為已修復。

21 個寫入／信任傳遞路徑列於 audit/IDENTITY_WRITE_PATH_AUDIT.md/json。舊 unauthorized MATCHED=0 只代表當時形式檢查通過，不能證明語意身份安全。

## 3. New canonical architecture

```mermaid
flowchart TD
 A[凍結 YOLO / local tracks / SAM2.1] --> B[不可變觀測與 candidate registry]
 B --> C[IdentityGuard 唯一授權者]
 E[Identity epoch 開啟／中断] --> C
 K[Core / quarantine / negative bank] --> C
 C --> T[一次性、範圍限定 capability]
 T --> W[Alias / 觀測 / bank / target-SAM 寫入]
 W --> L[可追溯 ledger]
 X[矛盾監測與撤銷] --> L
 L --> F[最終撤銷過濾後 timeline]
 F --> D[原 Event Window Builder / 5fps dense images / Qwen7B]
```

新模組位於 src/memory_graph/identity；沒有新增另一棵版本化實驗 identity tree。raw 命令直接使用純 perception collect_tracks，避開 V21 persistent resolver 與 V23/V26 既有身份寫入。

## 4. Identity epochs

初始綁定開啟 epoch 1。全域 gap .4 秒，等於 5fps 的兩個間隔，另容許 1ms 數值誤差；此值來自既有 development sampling/binding/window 配置，不使用 val GT 校準。觀測中斷、drift、scene break、不支持的跳動、競爭者或核心外觀矛盾關閉連續性。

Epoch 關閉後，SAM mask、local ID 或高 IoU 均不能直接重開身份。舊 alias 可保留歷史紀錄，但不提供跨中斷的未來權限。

## 5. Authorization states

CONTINUITY_AUTHORIZED 僅授予當次觀測；PROVISIONAL 為隔離候選；CONFIRMED_MATCH 才能建立持久 alias；AMBIGUOUS／REJECTED 不授予目標；REVOKED 移除先前授權衍生資料的有效性。短 track fragment 可以延續一次觀測，但不能因此獲得永久 alias。

## 6. Persistent-write capability system

Guard 私有 issuer registry 持有 opaque handles。JSON audit 不可當作 token；觀測 digest、candidate、epoch、alias、bank destination 和一次性 capability 都必須吻合。權限涵蓋 AUTHORIZE_OBSERVATION／BIND_ALIAS／RESTART_TARGET_SAM／COMMIT_BANK_ENTRY／REVOKE_ALIAS。

這是程式 API 邊界，並非對任意惡意 Python 私有記憶體操作的安全沙箱。測試涵蓋偽造、序列化、重放、錯 scope、過期 epoch、直接 registry/bank 寫入及 SAM restart。

## 7. Re-ID confirmation policy

.60 similarity／.10 margin 只作 admission。強確認另外需要多 core prototype 一致、多時間觀測、真正空間分離的同時競爭實體、共存排除、negative 排除、bank provenance、epoch 狀態及校準政策通過；每項 gate 獨立保存，沒有 opaque weighted score。

不同 prototype 的差距不是唯一性 margin。沒有可觀測的實體競爭者，不能把缺乏競爭者當成唯一身份證據。正式 automatic_confirmation_enabled=False；合成測試中的 true 是標示清楚的測試配置，沒有部署到影片回歸。

## 8. Appearance-bank policy

CORE 僅保留已見初始綁定的三個可信觀測；QUARANTINE 保存 provisional／recent-confirmed views；NEGATIVE 保存和當前可信目標同時空間分離的其他手機。Quarantine 不參與正式目標原型比對。

每筆含 observation、authorization、candidate/entity、epoch、frame/time、reason/status、parent alias/bank 及 parent authorization lineage。正式版尚未開放 quarantine→core 自動提升，比僅要求穩定期更保守；不能把這項尚未校準的功能說成已完成可靠的穩定更新。

## 9. Contradiction and revocation

同時存在不同 target claims、已知 distractor match 或 recovered alias 與核心矛盾會撤銷最新錯誤 claim。Alias/ledger 保留歷史但 inactive，相關 quarantine 與衍生 bank 以 lineage 過濾，SAM ticket 失效。Final builder rows 從最終 ledger 重新建立，不沿用線上曾經標過 T 的歷史。

真實回歸沒有正式長間隔確認，因此真實撤銷次數為 0；撤銷、既有觀測排除及 bank cascade 是合成契約驗證，不能冒稱已在真實錯合併中測得回復成功。

## 10. Development calibration

只讀 pre-existing test1–test9 的 scored audits 與既有 reviewed identity 標籤。去重後 258 candidate-view records，其中 5 TARGET、3 DISTRACTOR、250 UNLABELED；TARGET 範圍 .3352–.6813、DISTRACTOR .3732–.6111，明顯重疊。重複 attempt 不是獨立時間證據。

資料不足以定出強確認門檻；未使用 val similarity/GT 調參。新重算使用原 MobileNet 權重的統一未遮罩 crop，舊 masked-crop 分佈僅為風險診斷，不能當作新 crop 的校準。confirmation_policy.json 在影片回歸前保存，第二輪仍使用相同政策 hash。

第一輪已知回歸發現 initial selector 遺漏「已見但當前缺席」的成熟競爭者，導致提早綁定；以原 frozen binding 程式語意和新增合成測試修正，沒有變更數值。修正後重新跑 development、重新 source freeze、再重跑 11 支已知集。runs_final 才是最終結果；舊試跑保留供稽核。

## 11. Development regressions

{table(dev)}

總授權影格 {dev['totals']['old_authorized_sampled_frames']}→{dev['totals']['authorized_observations']}；有候選但未授權 {dev['totals']['unresolved_candidate_frames']} 影格。test2 保留 33/39 基本短連續性；test7 干擾者不合併；test9 持續未解決。test8 原 f804 正確 CONFIRMED_MATCH 現為未授權，f804 之後授權數 0：**正確長間隔回收損失 1→0**。

## 12. Known val_1–val_11 regressions

**POST-VALIDATION KNOWN REGRESSION SET — 非 held-out。** 重播既有 raw YOLO/local tracks/SAM 觀測，重新抽外觀與執行 identity；沒有採用舊 alias、trusted timeline 或 bank trust 作新授權。不是重新跑 11 支 YOLO/SAM。

{table(val)}

| 指標 | 舊 | 新 |
|---|---:|---:|
| 初始綁定 | 11/11 | 11/11，同 track、同 frame |
| 三個已知永久錯合併 | 3 | 0 |
| 錯誤 guard confirmation | 1 | 0 |
| 正確 guard long-gap recovery | 0 | 0 |
| val_9 錯誤 forward/core bank 寫入 | 12 | 0 |
| 已知錯誤區段仍授權的影格 | 有 | 0 |
| 授權 sampled frames | 896 | 169 |
| 新流程無有效 capability 的授權觀測 | 舊指標未涵蓋旁路 | 0 |

上述錯合併數只涵蓋已確認的三個失敗案例，不是完整新 accuracy。新系統有候選但未授權 {val['totals']['unresolved_candidate_frames']} 影格；這是影格數，不是 unique unresolved episodes。

## 13. val_5

原 f1284 raw-phone/SAM overlap 使干擾者可信，之後 track 77 變成 phone_01。新流程該錯誤區間授權 0、track 77 active alias=False、其 core entries=0。SAM 高 IoU 不再擁有授權能力。真目標後續是否存在不由非偵測推定。

## 14. val_9

原 candidate_005 單 crop 外觀通過並污染 12 個後續 bank views。新流程未讀其舊 identity label，從 raw track/crop 重新評估；正式長間隔確認 0、對應錯誤 track 52 無 active alias、錯誤核心寫入 0。解決的是不可逆寫入風險，尚未證明外觀模型能正確區分該干擾者。

## 15. val_10

原 f1140 SAM/raw overlap 及後續 track 49 直接沿用目標身份。新錯誤區段至 f1859 授權 0、track 49 active alias=False；原手機後來回來也不會被無證據自動合併。代價是正確返回仍可能 unresolved。

## 16. Safety / recall tradeoff

安全提升有兩部分：結構上統一授權；政策上不足證據不確認。後者會大量減少授權觀測，不能只展示 false merge=0。Development 授權下降 {100*(1-dev['totals']['authorized_observations']/dev['totals']['old_authorized_sampled_frames']):.1f}%，已知集下降 {100*(1-val['totals']['authorized_observations']/val['totals']['old_authorized_sampled_frames']):.1f}%。許多舊觀測本身就不安全，因此減少量也不等於全部是正確 recall loss。

全域 .4s gap 與少量初始外觀會把部分正常視角變化或偵測缺口切斷。只證明 test2 基本短連續性保留，不能宣稱所有影片連續性無退步。

## 17. Current active architecture / verification

Current entrypoint：scripts/run_findmind.py；根目錄 CURRENT_PIPELINE.md 為操作說明。README.md 亦被舊 manifest 凍結，已恢復原始位元組；其中舊 current 字樣屬歷史。版本化 runners 僅供 reference，沒有修改來偷換其身份邏輯。

新測試 {unit['passed']} 通過；focused {focused['passed']} 通過、{focused['skipped']} 跳過；完整 {full['passed']} 通過、{full['skipped']} 跳過；7/7 合成情境通過。初始 baseline 為 361 通過、1 跳過。早期 PYTHONPATH/temp 路徑失敗及 README freeze 檢查失敗保留日誌，最終測試已修正執行路徑／恢復凍結文件，不修改測試規則。

V293 {v293['files_checked']} 項、current development {reference['files_checked']} 項及預先記錄中可讀的 {integrity['prechange_files_checked']} 個檔案雜湊通過；其中 validation {integrity['validation_files_checked']} 個檔案完全一致。另有 {len(unreadable)} 個歷史 pytest 暫存檔因作業系統權限，即使提升權限唯讀仍無法重讀，列在 final/preservation_verification.json，**不宣稱這些暫存檔已核對通過**，也沒有改它們的 ACL 或內容。這不影響正式 frozen manifests 的核對。Event Window Builder、5fps 表示、Qwen model/prompt/schema/validator、physical Memory Graph trust 與 Search Planner 原始碼未改。

Fresh raw test2 確實執行 YOLO＋SAM，仍得 33 個授權影格；身份/外觀/SAM 段落計時 {raw['wall_seconds']:.2f}s，**不包含前段 collect_tracks 的時間**。Development replay {dev['totals']['wall_seconds']:.2f}s、已知集 replay {val['totals']['wall_seconds']:.2f}s 為各影片 identity/embedding/decode 計時合計，非完整模型載入及整體端到端耗時。

最終 test2 builder 產生 1 個可呼叫 physical pack，19 張 dense frames。原 Qwen7B 介面實際呼叫 1 次，EOS=True、schema/validator=True，回答 STATIC；generation {qwen[0]['trace']['runtime_seconds']:.2f}s、global GPU peak {qwen[0]['trace']['global_gpu_used_peak_bytes']/2**30:.2f} GiB。這是接線測試，不是 Qwen accuracy 改善實驗；沒有 Memory Graph 寫入。

## 18. Remaining identity bottleneck

1. **P0：恢復可用的連續性與安全長間隔 recall。** 先增加 development 中有身份標籤的多時間、多角度、同類干擾者證據；不能用已開封 val 集定強確認門檻。
2. **P0：校準強確認／稳定期／core promotion。** 目前全部自動長間隔確認關閉、core 不自動擴充；完整 synthetic gate 不等於可部署的數值校準。
3. **P1：區分真斷裂、短偵測缺口、正常視角變化。** .4s 與初始三視圖保守且易降低 recall；須使用 development 測量，不能個別影片調閾值。
4. **P1：真實撤銷與再回收測試。** 現在只驗證合成共存矛盾／lineage，尚無真實成功回復結果。看不到交換、極相似手機或反射都仍是風險。
5. **P1：候選 physical entity grouping。** 同時空間分離可證明不同實體；跨時間相同 local ID 或候選名仍不足以證明同一實體。
6. **P2：identity ledger 的持久化／重啟續跑。** Audit JSON 不是可重放 capability；目前需重新執行 guard，不提供 token 反序列化恢復權限。

## 19. Next step

先在既有 development 補足安全 recovery 與穩定更新的證據、改善召回成本，再錄製新的 distractor-heavy unseen set。現在不啟動下一輪 held-out、不改 Qwen／Event Window、不再調 SAM。

IDENTITY_REBUILD_PARTIAL_SUCCESS

NOT_READY_FOR_NEW_HELD_OUT_VALIDATION
'''
    (OUT/'IDENTITY_REBUILD_REPORT.md').write_text(report,encoding='utf8')
    (OUT/'development/regression_report.md').write_text('# Development identity regression\n\n'+table(dev)+'\n\nInitial binding preserved. test8 f804/forward recovery lost. test7/test9 remain unresolved without false confirmation. Final runs are in runs_final; earlier folders are superseded diagnostics.\n',encoding='utf8')
    (OUT/'known_validation_regression/case_report.md').write_text('# POST-VALIDATION KNOWN REGRESSION SET\n\n'+table(val)+'\n\nval_5 track77, val_9 track52/candidate005, val_10 track49: no active wrong alias, no known-wrong-interval authorized observation, no wrong core entries. val_8/val_11 recovery remains unresolved. This is not held-out accuracy. See the full report for recall losses and the generic initial-selector compatibility correction.\n',encoding='utf8')
    files={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='integrity_manifest.json' and '__pycache__' not in p.parts}
    write(OUT/'final/integrity_manifest.json',{'created_unix':time.time(),'files':files,'sources':source_hashes,
        'preservation':integrity,'decision':'IDENTITY_REBUILD_PARTIAL_SUCCESS','readiness':'NOT_READY_FOR_NEW_HELD_OUT_VALIDATION'})
    print(json.dumps({'files':len(files),'tests_passed':full['passed'],'preservation':integrity,'report':str(OUT/'IDENTITY_REBUILD_REPORT.md')},indent=2))

if __name__=='__main__':main()
