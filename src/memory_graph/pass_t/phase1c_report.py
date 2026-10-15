"""Consolidate the bounded task; never submits, selects or rewrites answers."""
import ast
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from PIL import Image
from .phase1c_common import ROOT, OUT, COUNTERS, read, write, sha, now, safety_scan
from .phase1c_policy import verify_freeze, NAME
from .phase1c_responses import load_reviews
from .media import require_media, rgb_signature

PROMPT_SHA='b6057e19de893514fabba7842dbd3a91957fc17e7255c2e9bfb2a3b16dd7b53d'


def new_code_paths():
    return sorted((ROOT/'src/memory_graph/pass_t').glob('phase1c_*.py'))+[
        ROOT/'scripts/run_pass_t_phase1c.py',ROOT/'scripts/run_pass_t_human_seed_review.py',
        ROOT/'tests/test_pass_t_phase1c.py',ROOT/'tests/test_pass_t_causality_audit.py']


def audit_isolation(report):
    paths=[ROOT/'src/memory_graph/pass_t/phase1c_audit.py',ROOT/'tests/test_pass_t_causality_audit.py']
    allowed={'hashlib','subprocess','pathlib','json','ast','pytest','phase1c_common',
             'memory_graph.pass_t','memory_graph.pass_t.phase1c_common'}
    forbidden=['human_seed_review/responses','human_seed_outcomes_v1','phase1c_review',
               'phase1c_responses','phase1c_viewer','event_gt','reference_label','physical_gt']
    errors=[];imports=[]
    for path in paths:
        text=path.read_text(encoding='utf-8');tree=ast.parse(text)
        for token in forbidden:
            if token in text:errors.append(f'{path.name}: forbidden input/module reference {token}')
        for n in ast.walk(tree):
            names=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module or ''] if isinstance(n,ast.ImportFrom) else []
            for name in names:
                imports.append(name)
                if name not in allowed:errors.append(f'{path.name}: unexpected import {name}')
    expected=read(OUT/'reports/PASS_T_BINDING_CAUSALITY_AUDIT.json')['input_allowlist']
    if not set(report['actual_inputs_read'])<=set(expected):errors.append('Audit read outside allowlist')
    for p in expected:
        if any(t in p.lower() for t in forbidden):errors.append('Prohibited audit input')
    return {'status':'PASS' if not errors else 'FAIL','errors':errors,'imports':sorted(set(imports)),
            'files_checked':[p.relative_to(ROOT).as_posix() for p in paths],
            'explicit_input_allowlist':expected,'actual_input_count':len(report['actual_inputs_read']),
            'all_reads_allowlisted':set(report['actual_inputs_read'])<=set(expected)}


def verify_packages(manifest):
    errors=[];rows=[];av=require_media();base=OUT/'human_seed_review'
    for entry in manifest['items']:
        path=base/entry['item_path'];folder=path.parent;item=read(path)
        if sha(path)!=entry['item_sha256']:errors.append(f'{item["pack_id"]}: changed item')
        signatures=[]
        for asset in item['frames']+item['references']:
            actual=(folder/asset['image_path']).resolve()
            if not actual.is_relative_to(folder.resolve()) or sha(actual)!=asset['sha256']:
                errors.append(f'{item["pack_id"]}: changed/escaped asset');continue
            with Image.open(actual) as image:
                if asset in item['frames']:signatures.append(rgb_signature(np.asarray(image.convert('RGB'))))
            if asset in item['frames']:
                a,b=item['authorized_half_open_frames']
                if not (a<=asset['source_frame_index']<b and item['window_start_s']<=asset['source_timestamp_s']<item['window_end_s']):
                    errors.append(f'{item["pack_id"]}: outside-window frame')
            elif not asset['source_timestamp_s']<item['window_start_s'] or asset['role']!='REFERENCE_PRE_WINDOW':
                errors.append(f'{item["pack_id"]}: unauthorized seed reference')
        clip=folder/item['clip']['path'];decoded=[];pts=[]
        if sha(clip)!=item['clip']['sha256']:errors.append(f'{item["pack_id"]}: clip hash mismatch')
        with av.open(str(clip),'r') as container:
            for frame in container.decode(video=0):
                decoded.append(rgb_signature(frame.to_ndarray(format='rgb24')));pts.append(float(frame.pts*frame.time_base))
        intended=[f['source_timestamp_s']-item['window_start_s'] for f in item['frames']]
        timing_error=max((abs(a-b) for a,b in zip(pts,intended)),default=0)
        if decoded!=signatures or len(pts)!=len(intended) or timing_error>.001:
            errors.append(f'{item["pack_id"]}: decoded clip correspondence failed')
        rows.append({'pack_id':item['pack_id'],'full_rate_frames':len(item['frames']),
                     'pre_window_reference_crops':len(item['references']),
                     'original_seed_observations_in_window':item['original_seed_observations_in_window'],
                     'original_seed_observations_pre_window':item['original_seed_observations_pre_window'],
                     'candidate_ids':[c['candidate_id'] for c in item['candidates']],
                     'clip_decode_count':len(decoded),'max_pts_deviation_s':timing_error,
                     'review_only':item['human_review_only'] and item['not_model_input'] and not item['evaluation_eligible']})
    return {'status':'PASS' if not errors else 'FAIL','errors':errors,'items':rows,
            'full_rate_frames':sum(r['full_rate_frames'] for r in rows),
            'reference_crops':sum(r['pre_window_reference_crops'] for r in rows),
            'full_source_video_exposed':False,'review_answers_written_during_qa':0}


def test_results():
    path=OUT/'smoke/phase1c_final.xml'
    if not path.is_file():return {'status':'MISSING','tests':0,'failures':0,'errors':0,'skipped':0}
    document=ET.fromstring(path.read_text(encoding='utf-8'))
    suites=list(document.iter('testsuite'))
    result={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    cases=list(document.iter('testcase'));groups={}
    for case in cases:
        module=case.get('classname','').split('.')[-1]
        groups[module]=groups.get(module,0)+1
    return {**result,'status':'PASS' if result['tests'] and not result['failures'] and not result['errors'] and not result['skipped'] else 'FAIL',
            'groups':groups,'junit_path':path.relative_to(ROOT).as_posix(),
            'command':'python -B -m pytest tests/test_pass_t.py tests/test_pass_t_phase1b.py tests/test_pass_i.py tests/test_pass_i_pilot.py tests/test_event_window_builder.py tests/test_pass_t_phase1c.py tests/test_pass_t_causality_audit.py -q -p no:cacheprovider --basetemp artifacts/pass_t/smoke/phase1c_release_tmp --junitxml artifacts/pass_t/smoke/phase1c_final.xml'}


def preservation_check(mappings):
    names=['protected_before.json','phase1b_protected_before.json','phase1c_protected_before.json']
    manifests={n:read(OUT/'manifests'/n) for n in names};combined={}
    for m in manifests.values():combined.update(m)
    actual={p:sha(ROOT/p) if (ROOT/p).is_file() else None for p in combined}
    mismatches={n:[p for p,h in m.items() if actual[p]!=h] for n,m in manifests.items()}
    source_hashes={}
    for mapping in mappings:
        path=mapping['source_video_path']
        if path not in source_hashes:
            source_hashes[path]={'actual_sha256':sha(ROOT/path),'expected_sha256':mapping['source_video_hash']}
    prompt=sha(ROOT/'artifacts/pass_i/prompts/pass_i_prelabel_prompt.txt')
    pre=read(OUT/'manifests/phase1c_preflight.json')
    def git(args):
        r=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,check=False)
        if r.returncode:raise ValueError('Read-only Git inspection failed')
        return r.stdout.decode('utf-8').rstrip('\r\n'),r.stderr.decode('utf-8')
    head,_=git(['rev-parse','HEAD'])
    status,warnings=git(['status','--porcelain=v1','--untracked-files=no'])
    after=status.splitlines()
    before=[s for s in pre['git_status_lines'] if not s.startswith(('??','!!'))]
    same_status=sorted(after)==sorted(before)
    good=not any(mismatches.values()) and all(v['actual_sha256']==v['expected_sha256'] for v in source_hashes.values()) and prompt==PROMPT_SHA and head==pre['HEAD'] and same_status
    return {'status':'PASS' if good else 'FAIL','protected_counts':{n:len(m) for n,m in manifests.items()},
            'union_files_checked':len(actual),'mismatches':mismatches,'source_video_hashes':source_hashes,
            'pass_i_prompt_sha256':prompt,'prompt_sha_matches':prompt==PROMPT_SHA,
            'HEAD_before':pre['HEAD'],'HEAD_after':head,'HEAD_unchanged':head==pre['HEAD'],
            'preexisting_tracked_worktree_status_unchanged':same_status,
            'preexisting_tracked_status_count':len(before),'tracked_status_after_count':len(after),
            'git_inspection_warnings':warnings,'historical_git_status_warnings':pre['git_status_warnings'],
            'no_commit_or_push':True,'old_protected_manifests_extended':False,
            'coverage':'V297, Pass I, outputs_v292, Builder, original packs, Pass T v1/Phase1/Phase1b preserved by individual hashes; source media hashes checked separately.'}


def finalize():
    receipt=verify_freeze();manifest=read(OUT/'human_seed_review/review_manifest.json')
    reviews=load_reviews();audit=read(OUT/'reports/PASS_T_BINDING_CAUSALITY_AUDIT.json')
    original=read(OUT/'reports/PASS_T_PHASE1B_REPORT.json')
    mappings=read(OUT/'manifests/window_target_mapping.json')['packs']
    tests=test_results();assets=verify_packages(manifest);safety=safety_scan(new_code_paths())
    isolation=audit_isolation(audit);preservation=preservation_check(mappings)
    receipt_after=verify_freeze()
    policy_same=receipt==receipt_after
    answers_folder=OUT/'human_seed_review/responses'
    answer_files=list(answers_folder.iterdir())
    response_path_checks=[]
    for p in answer_files:
        try:
            value=read(p);sub=value['submission'];pack=value['primary_response']['pack_id']
            ok=p.name==pack+'.json' and sub['submitted_via']=='human_seed_review_viewer' and sub['timestamp_recorded_automatically'] is True
        except (ValueError,KeyError,TypeError,IsADirectoryError):ok=False
        response_path_checks.append({'file':p.name,'viewer_save_metadata_valid':ok})
    safe=not any(COUNTERS.values()) and safety['status']=='PASS' and isolation['status']=='PASS'
    scope_ok=len(manifest['items'])==7 and len(audit['packs'])==9 and audit['completion']=='NINE_PACK_AUDIT_COMPLETE'
    if preservation['status']!='PASS' or assets['status']!='PASS' or not safe or not policy_same:
        status='PASS_T_PHASE1C_BLOCKED'
    elif not scope_ok or tests['status']!='PASS':status='PASS_T_PHASE1C_PARTIAL_WITH_BLOCKERS'
    elif reviews['completed']<7:status='PASS_T_PHASE1C_WAITING_FOR_HUMAN_REVIEW'
    else:status='PASS_T_PHASE1C_REVIEW_AND_CAUSAL_AUDIT_COMPLETE'
    source=[m for m in mappings if m['resolution_status']=='RESOLVED_UNIQUE']
    if len(source)!=2:raise ValueError('Original source-resolved stratum changed')
    selected={r['pack_id'] for r in reviews['items'] if r['human_seed_eligibility']}
    eligible=[m for m in mappings if m in source or m['pack_id'] in selected]
    media_keys={(m['video_id'],m['window_start_s'],m['window_end_s']) for m in eligible}
    candidates_present={m['pack_id'] for m in source}|{e['pack_id'] for e,item in [(x,read(OUT/'human_seed_review'/x['item_path'])) for x in manifest['items']] if item['candidates']}
    candidate_media={(m['video_id'],m['window_start_s'],m['window_end_s']) for m in mappings if m['pack_id'] in candidates_present}
    readiness={'original_packs':9,'unique_media_windows':original['unique_media_windows'],
               'nonoverlapping_evidence_groups':original['nonoverlapping_evidence_groups'],
               'distinct_source_video_files':original['distinct_source_video_files'],
               'independent_source_recording_sessions':'UNKNOWN','source_resolved_packs':2,
               'source_resolved_dev_eligible_packs':2,'source_resolved_formal_eligible':0,
               'valid_human_seeded_packs':reviews['human_seeded_valid'],'human_seeded_dev_eligible':reviews['dev_eligible'],
               'human_seeded_formal_eligible':0,'still_unresolved':7-reviews['human_seeded_valid'],
               'causal_verified':audit['causal_verified'],'causality_unverified':audit['causality_unverified'],'non_causal':audit['noncausal'],
               'unique_candidate_present_media_windows':len(candidate_media),
               'unique_target_usable_media_windows':len(media_keys),
               'candidate_usable_media_window_definition':f'Visible candidate present: {len(candidate_media)}; current target-localized DEV usable: {len(media_keys)}. Candidate discovery is not target resolution.',
               'dev_preparation_eligible_by_stratum':{'SOURCE_RESOLVED':2,'HUMAN_SEEDED':reviews['dev_eligible'],'UNRESOLVED':0},
               'formal_evaluation_ready':False}
    new_files=[p.relative_to(ROOT).as_posix() for p in new_code_paths()]
    protected=read(OUT/'manifests/phase1c_protected_before.json')
    new_files += [p.relative_to(ROOT).as_posix() for parent in [OUT/'contracts',OUT/'manifests',OUT/'reports',OUT/'human_seed_review']
                  for p in parent.rglob('*') if p.is_file() and p.relative_to(ROOT).as_posix() not in protected]
    new_files += ['artifacts/pass_t/reports/'+name for name in ['PASS_T_PHASE1C_REPORT.md',
                  'PASS_T_PHASE1C_REPORT.json','phase1c_safety_scan.json','phase1c_preservation_final.json']]
    if reviews['completed']:new_files.append('artifacts/pass_t/manifests/human_seed_outcomes_v1.json')
    result={'primary_status':status,'generated_at_utc':now(),'baseline':'V297_FROZEN',
            'pass_i':'PASS_I_CLOSED_ACQUISITION_LIMITED','pass_t_phase1b':'PASS_T_PHASE1B_PILOT_SMOKE_PASS',
            'policy_status':'FROZEN','policy_receipt':receipt,'policy_unchanged_after_validation':policy_same,
            'review_packages':assets,'human_reviews':reviews,'binding_audit':{'completion':audit['completion'],
                'causal_verified':audit['causal_verified'],'causality_unverified':audit['causality_unverified'],
                'noncausal':audit['noncausal'],'packs':audit['packs']},'readiness':readiness,
            'tests':tests,'safety':safety,'audit_isolation':isolation,'runtime_counters':dict(COUNTERS),
            'preservation':preservation,'production_response_files':response_path_checks,
            'production_responses_empty':not answer_files,'responses_written_by_agent':0,
            'next_action':'HUMAN_REVIEW_SEVEN_WINDOWS' if reviews['completed']<7 else 'STOP_AND_AWAIT_SEPARATE_NEXT_STAGE_AUTHORIZATION',
            'new_files':sorted(set(new_files)),
            'limitations':['Local hash/UTC freeze is not external timestamp or commit proof.',
                'Viewer metadata/attestations cannot cryptographically prove human authorship or visual support.',
                'All automatic binding/upstream causality remains unverified; static correctness does not establish lineage.',
                'Recording-session independence is unknown; duplicated/overlapping windows are grouped.',
                'Formal evaluation and A/B/C inference remain unauthorized and were not started.'],
            'internal_repair_notes':['Initial focused test misclassified PIL image.save as viewer.save; test corrected; no answer was submitted.']}
    write(OUT/'reports/phase1c_safety_scan.json',{'safety':safety,'audit_isolation':isolation,'runtime_counters':dict(COUNTERS)})
    write(OUT/'reports/phase1c_preservation_final.json',preservation)
    if reviews['completed']:
        write(OUT/'manifests/human_seed_outcomes_v1.json',{'generated_at_utc':result['generated_at_utc'],
              'policy_md_sha256':receipt['policy_md_sha256'],'policy_json_sha256':receipt['policy_json_sha256'],**reviews})
    write(OUT/'human_seed_review/reports/pending_review_state.json',{
        'status':'HUMAN_REVIEW_COMPLETE' if reviews['completed']==7 else 'WAITING_FOR_AUTHENTIC_HUMAN_REVIEW',
        'is_pending':reviews['completed']<7,'responses_received':reviews['responses_present'],
        'completed':reviews['completed'],'agent_generated_responses':0,'items':reviews['items'],
        'generated_at_utc':result['generated_at_utc'],'human_seed_outcomes_created':bool(reviews['completed'])})
    write(OUT/'reports/PASS_T_PHASE1C_REPORT.json',result)
    write(OUT/'reports/PASS_T_PHASE1C_REPORT.md',markdown(result))
    return {'status':status,'tests':tests,'preservation':preservation['status'],
            'review_completed':reviews['completed'],'human_seeded_valid':reviews['human_seeded_valid'],
            'report':'artifacts/pass_t/reports/PASS_T_PHASE1C_REPORT.md'}


def markdown(r):
    receipt=r['policy_receipt'];ready=r['readiness'];reviews=r['human_reviews'];tests=r['tests']
    response_summary=(f'目前收到 {reviews["responses_present"]} 份人工原始回覆，{reviews["completed"]}/7 通過驗證；結果另存 human_seed_outcomes_v1.json，原始回覆未修改。'
                      if reviews['completed'] else '目前 responses/ 為空；沒有產生 human_seed_outcomes_v1.json，待辦狀態另存 pending_review_state.json。')
    next_step=('七份真實人工審閱與獨立審計已完成，本次任務停止。保留獨立 HUMAN_SEEDED stratum 與未驗證因果性，等待另外授權的下一階段。'
               if reviews['completed']==7 else '由你本人在本機 viewer 完成尚未完成的視窗，允許合法未解答案，然後僅執行 finalize 驗證。工程任務在此停止。')
    lines=['# Pass T Phase 1c — 進度與保留驗證報告','',f'**{r["primary_status"]}**','',
           '## 1. 工程與人工審閱進度','',
           f'政策先行凍結；7 個審閱包完成，{r["review_packages"]["full_rate_frames"]} 張完整幀率乾淨影格、{r["review_packages"]["reference_crops"]} 張獨立前窗 seed 參考 crops、7 段逐幀對應的 lossless FFV1 clips。9/9 自動 binding 的獨立因果性審計完成。',
           f'人工有效回覆 {reviews["completed"]}/7；有效 HUMAN_SEEDED {reviews["human_seeded_valid"]}；DEV eligible {reviews["dev_eligible"]}；formal eligible 0。工程師未提交任何答案。',
           '', 'V297、Pass I、IdentityGuard、Re-ID、Builder、原 Event Packs、舊 Pass T 契約/報告/mappings 均保留。沒有 inference、模型重跑、Graph 寫入、commit 或 push。',
           '', '## 2. 先行凍結的資格政策','',
           f'版本 `{receipt["policy_version"]}`；建立 UTC `{receipt["created_at_utc"]}`。凍結前正式 human seed 回覆不存在；4 份舊 GPT 測試 fixture 已排除且未當作人類答案。',
           '',
           f'- MD SHA-256：`{receipt["policy_md_sha256"]}`',
           f'- JSON SHA-256：`{receipt["policy_json_sha256"]}`',
           '- `allow_pre_window_seed_reference=true`，僅嚴格早於視窗開始的原 seed 觀測；使用時必須標為 HUMAN_VISUAL_LOCALIZATION_ONLY。',
           '- 政策與原 schema hashes 於驗證後保持一致；receipt 是本機 hash/UTC 證據，沒有外部時間戳或 commit 錨定。',
           '', '| Stratum | DEV | Formal | 身分/因果性 |','|---|---|---|---|',
           '| SOURCE_RESOLVED | 各自分層；未驗證因果性仍可 DEV 準備 | 本階段不可 | 既有正向 local provenance；不等於全域身分或 causal verification |',
           '| HUMAN_SEEDED | 僅真實有效提交、存在 candidate、窗內 frame/obs 引用、理由與 provenance、無洩漏/事件依賴/矛盾/全域身分主張 | 預設不可 | 只支持本地定位，不能創造 machine edge 或升級原 automatic binding |',
           '| UNRESOLVED | 不進入目標已定位 DEV 分母 | 不可 | 合法審閱結果；也包含尚未審閱 |',
           '', '## 3. 七個視窗審閱狀態','',
           '| Pack | 原狀態 | Human 狀態 | 決策 / candidate | 引用 frame | Provenance support | Seed eligible | 剩餘不確定性 |',
           '|---|---|---|---|---|---|---|---|']
    for row in reviews['items']:
        lines.append(f"| {row['pack_id']} | {row['original_resolution']} | {row['human_review_status']} | {row['review_decision'] or '—'} / {row['selected_local_candidate'] or '—'} | {', '.join(row['evidence_frame_ids']) or '—'} | {row['provenance_support']} | {row['human_seed_eligibility']} | {str(row['remaining_uncertainty']).replace('|','/')} |")
    lines += ['', 'test8 W06/W07 共用 overlap group，不能算成獨立 evidence；test1 W03/W05 共用同一 media window。',
              '', '| Pack | Full-rate frames | 原 seed 窗內 / 前窗觀測 | 參考 crops | 既有 candidate IDs |',
              '|---|---:|---|---:|---|']
    for row in r['review_packages']['items']:
        lines.append(f"| {row['pack_id']} | {row['full_rate_frames']} | {row['original_seed_observations_in_window']} / {row['original_seed_observations_pre_window']} | {row['pre_window_reference_crops']} | {', '.join(row['candidate_ids'])} |")
    lines += ['', 'Candidate IDs 依 ID 升冪，包含既有無 source-track 的 candidate references；不顯示 detector confidence、面積、可見數量或 Re-ID/Guard 排序。額外 candidate references 來自實際窗內 allowlist，非 diagnostic_only，沒有修改原 request 或 mapping。候選存在不代表是目標。',
              '', '## 4. 如何開啟、儲存、暫停','', '在 Windows PowerShell 執行：','', '```powershell',
              "Set-Location 'C:\\Users\\smile\\Desktop\\test2\\mixure_test_SAM'", ".\\.venv\\Scripts\\python.exe -B scripts/run_pass_t_human_seed_review.py", '```','',
              '這是 native Tk 本機視窗，不使用 Streamlit/127.0.0.1 或網路。依 pack 看完整幀率影格，Play/Previous/Next 或滑桿查看；Cite displayed frame 精確引用窗內證據。前窗 crops 另列 REFERENCE_PRE_WINDOW；勾選實際使用的參考圖，雙擊可放大。只能看裁切視窗與授權參考，不能 scrub 整段來源影片。',
              '', '填入真實 reviewer ID、四選一決策、必要的候選 ID、provenance、理由、uncertainty、自己的 confidence，逐一回答 attestations，勾選人類身分再 Save。選 candidate 必須引用它的實際觀測幀；觀測 IDs 自動由引用連結。SELECT 若仍 UNCERTAIN/UNRESOLVED，會保留紀錄但不升格。無充分支持可用 UNRESOLVED/NO_VISIBLE_TARGET/MULTIPLE_PLAUSIBLE_TARGETS，不強迫選擇。',
              '', 'Save 才產生真實 UTC 與 immutable JSON；導航/播放不會儲存。關閉可暫停，重開同指令可接續；原回覆只讀、不能覆寫，duplicate 明確阻擋而不挑選其中一份。七份完成即停止。',
              '', '人工完成後，於同一 PowerShell 執行驗證與更新本次新報告：','', '```powershell',
              '.\\.venv\\Scripts\\python.exe -B scripts/run_pass_t_phase1c.py --step finalize','```','',
              response_summary+' Viewer attestations 能檢查必要資訊，不能以密碼學證明作者或視覺判斷正確。',
              '', 'Human seed 的授權只涵蓋明確選取的 local candidate 與實際觀測；理由中提及其他 track/candidate 的關聯保留為人工假說，不會新增 tracking edge、延伸到後續 IDs 或建立全域身分。',
              '', '## 5. 獨立自動 binding 因果性審計','',
              f'CAUSAL_VERIFIED={ready["causal_verified"]}/9；CAUSALITY_UNVERIFIED={ready["causality_unverified"]}/9；NON_CAUSAL={ready["non_causal"]}/9。完整審計結果仍未驗證，並非審計未完成。',
              '', '| Pack | 原 seed | 決策截止 frame | Binding 直接讀取至 | 選擇前綴至 | Upstream 潛在影響至 | Upstream / 原 binding |',
              '|---|---:|---:|---:|---:|---:|---|']
    for row in r['binding_audit']['packs']:
        lines.append(f"| {row['pack_id']} | {row['original_seed_track']} | {row['claimed_binding_decision_frame']} | {row['latest_frame_read_directly_by_binding_logic']} | {row['latest_frame_in_recorded_selection_prefix']} | {row['latest_source_frame_that_may_influence_upstream']} | {row['final_causality_classification']} |")
    lines += ['', '正向證據：初始 binding 讀的是 upstream 原始 tracks；選擇紀錄與 seen-prefix 邏輯停在 binding frame；初始 binding 位於 SAM/admission/Re-ID/Guard 之前；允許輸入的 hashes 與既有 baseline 一致。每個 pack 的 generator、artifact path/hash、recorded Git revision/current blob comparison、config、正向與缺失 lineage 詳見獨立審計 JSON。',
              '', '`automatic_bind` 先讀完整 phone observations 建立 by_frame，之後才從已見前綴選擇。Upstream 在 ByteTrack 之前做完整影片 episode segmentation，之後寫 full-video cache/timelines；finish 能根據完整影片長度處理末尾短 episode。目前未找到它影響這些早期 binding 的正向證據。',
              '', '缺失證據：沒有截至 cutoff 的 incremental tracker state/dependency logs、完整歷史 invocation/config receipt，以及排除完整影片 episode/cache 對前綴影響的獨立 runtime lineage。靜態 code、matching hashes 或選對目標，都不能補足此證據。6 支 source 的 recorded sessions 獨立性未知。',
              '', '沒有證明禁止的未來資訊或 GT 影響選擇，故 NON_CAUSAL=0；也沒有足夠證據排除 runtime 影響，故 CAUSAL_VERIFIED=0。離線檔案生成時間晚於影片秒數不構成非因果證據。人類 seed 結果不會改寫這些分類。',
              '', f'隔離檢查 {r["audit_isolation"]["status"]}：審計 source/tests 僅允許明列 imports；實際 {r["audit_isolation"]["actual_input_count"]} 個讀取路徑全在 input allowlist。審計未讀 human responses/outcomes、review modules 或 GT/reference labels；被查 code 未 import 或執行，沒有 prefix-only 重跑模型。',
              '', '## 6. Dataset readiness 與分母','',
              '| 項目 | 數量 / 狀態 |','|---|---|',
              f'| Original packs / unique media / non-overlap groups | 9 / {ready["unique_media_windows"]} / {ready["nonoverlapping_evidence_groups"]} |',
              f'| SOURCE_RESOLVED packs / unique localized media | 2 / 1 |',
              f'| HUMAN_SEEDED valid / DEV eligible / formal eligible | {ready["valid_human_seeded_packs"]} / {ready["human_seeded_dev_eligible"]} / 0 |',
              f'| Still unresolved | {ready["still_unresolved"]} |',
              f'| 有可見候選的 unique media windows | {ready["unique_candidate_present_media_windows"]}，不是已定位 target |',
              f'| 已定位可用 DEV unique media windows | {ready["unique_target_usable_media_windows"]} |',
              '| Independent recording sessions | UNKNOWN |','| Formal evaluation ready | NO |',
              '', '只可依 source-resolved / human-seeded 分層準備 DEV；未定位案例不進入目標已定位分母。本次沒有啟動 DEV model comparison。Formal benchmark、人類 seed 的正式例外與因果性修補均需另外預註冊/授權；本次不實作。',
              '', '## 7. 測試、安全與保留','',
              f'完整最終測試：{tests["tests"]}/{tests["tests"]}，failures={tests["failures"]}、errors={tests["errors"]}、skipped={tests["skipped"]}；狀態 {tests["status"]}。',
              '', '| Suite | Tests |','|---|---:|']
    lines += [f'| {group} | {count} |' for group,count in tests.get('groups',{}).items()]
    lines += ['', '新增測試涵蓋政策/不升格、四類決策、缺失或無效證據、事件/身分污染紀錄、duplicate/immutable、full-rate half-open bounds、前窗 reference、候選投影、模型 contract 拒收 review items、overlap、7-case Tk QA、獨立因果性分類/allowlist、no-inference/static imports、UTF-8、protected hashes。測試答案只在 project-local synthetic fixture 檔案，不寫任何 responses/。',
              '', f'Preservation={r["preservation"]["status"]}。舊 manifests 與 expanded protection 計數：`{r["preservation"]["protected_counts"]}`；Pass I prompt SHA `{r["preservation"]["pass_i_prompt_sha256"]}`，原來源影片各自 hash 一致；HEAD 與既有 tracked changes 未變。',
              '', '既有 Git status 包含大量先前 tracked deletions 與不可讀舊 temp-directory warnings，均在 preflight 記錄，未整理/還原。此次 temp 使用 project-local smoke 目錄；測試沒有 temp-cleanup PermissionError。初次 focused test 曾誤將 PIL.save 當作答案提交，已修正測試並保留初次 JUnit，再以完整 suite 驗證。',
              '', f'Static safety={r["safety"]["status"]}，all new text IO explicit UTF-8；runtime counters `{r["runtime_counters"]}`。原 protected manifests 未加入本次新 artifact，也未執行 commit/push。',
              '', '## 8. 新檔案與最小下一步','',
              '- contracts/：policy MD/JSON/freeze receipt 與 companion wrapper schema；原 v1 schema 未改。',
              f'- human_seed_review/：manifest、操作說明、7 item.json + 726 PNG + 19 reference PNG + 7 clips、{reviews["responses_present"]} 份原始人工回覆與更新的進度狀態。',
              '- reports/：Phase1c MD/JSON、binding causality audit MD/JSON、preflight/plan/safety/preservation 記錄。',
              '- manifests/：Phase1c expanded protection snapshot、independent binding lineage；存在真實有效回覆時另產生 human_seed_outcomes_v1.json。',
              '- src/scripts/tests：7 個新 Phase1c modules、2 個 launcher/checkpoint scripts、2 個新測試檔；完整清單在 JSON。',
              '', '**'+next_step+' 沒有擴大 annotation、Re-ID/SAM 調整或正式評估。**']
    return '\n'.join(lines)+'\n'
