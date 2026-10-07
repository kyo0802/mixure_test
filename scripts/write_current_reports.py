"""Build reports from frozen development artifacts without changing predictions."""
import json
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/current_development'
def read(rel):return json.loads((OUT/rel).read_text(encoding='utf-8'))
def put(rel,text):
    p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text.strip()+'\n',encoding='utf-8')
def fraction(x):
    return f"{x['correct']}/{x['denominator']} ({x['rate']:.1%})" if x['denominator'] else '不可判定'

def main():
    cleanup=read('cleanup/CLEANUP_MANIFEST_AFTER.json')
    audit=read('cleanup/REPOSITORY_AUDIT.json')
    inventory=read('regression/active_test_inventory.json')
    windows=read('event_windows/event_manifest.json')
    physical=[x for x in windows if x['category']=='PHYSICAL_INTERACTION_EVENT']
    complete=[x for x in physical if x['completeness']=='COMPLETE_EVENT_WINDOW']
    metrics=read('evaluation/reasoning_metrics.json')
    quality=read('evaluation/window_quality.json')
    comparison=read('evaluation/baseline_comparison.json')
    old=comparison['same_runtime_old_windows']
    review=read('evaluation/post_freeze_review.json')
    by={x['pack_id']:x for x in review['events']}
    memory=read('evaluation/search_memory.json')
    runtime=read('qwen/runtime.json')
    old_runtime=read('evaluation/runtime_matched_baseline/runtime.json')
    cfg=read('event_windows/config.json')['initial_global_config']
    req=read('qwen/requests.json')
    sources=read('final/baseline_prediction_manifest.json')['sources']
    deleted=[x for x in cleanup['records'] if x['deleted']]
    deleted_tests=[x['path'] for x in deleted if x['path'].startswith('tests/test_') and x['path'].endswith('.py')]
    deleted_src=[x['path'] for x in deleted if x['path'].startswith('src/') and '__pycache__' not in x['path']]
    deleted_models=[x for x in deleted if x['path'].startswith('.models/') or x['path'] in ['outputs_v2946','.venv_sam3','.venv_sam31','.sam31_official']]
    actor_loc=(sum(x['actor_available'] for x in physical),sum(x['location_available'] for x in physical))
    gip=cleanup['known_reclaimed_bytes']/2**30
    table='| 欄位 | 舊窗口・ALL | 新窗口・ALL | 舊 eligible | 新 eligible |\n|---|---:|---:|---:|---:|\n'
    labels={'event_type':'事件類型','interaction_anchor':'互動 actor','released':'是否放手','target_visible_after':'最末可見性','final_relation':'最末關係','final_relation_anchor':'最末 location/關係對象'}
    for f,label in labels.items():
        table+=f"| {label} | {fraction(old['ALL'][f])} | {fraction(metrics['ALL'][f])} | {fraction(old['REASONING_ELIGIBLE'][f])} | {fraction(metrics['REASONING_ELIGIBLE'][f])} |\n"
    rows='| 影片 | 物理 selected | COMPLETE | INCOMPLETE | 實際 Qwen calls |\n|---|---:|---:|---:|---:|\n'
    for i in range(1,10):
        es=[e for e in physical if e['video_id']==f'test{i}'];n=sum(e['completeness']=='COMPLETE_EVENT_WINDOW' for e in es)
        rows+=f'| test{i} | {len(es)} | {n} | {len(es)-n} | {n} |\n'
    event_table='| pack | 時間 (秒) | 自動 gate | 視覺完整 | eligible | 放低/release 可檢查 | 明確 release |\n|---|---|---|---|---|---|---|\n'
    for e in physical:
        r=by[e['pack_id']]
        event_table+=f"| {e['pack_id']} | {e['start_time']:.2f}–{e['end_time']:.2f} | {'C' if e['completeness']=='COMPLETE_EVENT_WINDOW' else 'I'} | {r['visually_complete_transition']} | {r['reasoning_eligible']} | {r['placement_release_reviewable']} | {r['confirmed_visible_release']} |\n"
    action=[e for e in complete if by[e['pack_id']]['visually_complete_transition']]
    confirmed=[e for e in complete if by[e['pack_id']]['confirmed_visible_release']]
    extra={
        'visual_complete_among_dispatched':len(action),'visual_complete_among_dispatched_denominator':len(complete),
        'confirmed_visible_release_windows':len(confirmed),'confirmed_release_unique_episodes':2,
        'confirmed_release_pack_ids':[e['pack_id'] for e in confirmed],
        'visually_complete_action_event_type_correct':0,'visually_complete_action_denominator':len(action),
        'confirmed_release_answer_correct':0,'confirmed_release_answer_denominator':len(confirmed),
        'raw_frame_count_sent':sum(len(r['images']) for r in req),
        'reviewable_placement_lowering_unique_episodes':6,
        'reviewable_episode_groups':[['test1__W03','test1__W05'],['test2__W08'],['test3__W02','test3__W03','test3__W07'],['test4__W06','test4__W08'],['test5__W05'],['test8__W06']],
        'note':'Descriptive engineering grouping, not independent GT or whole-video recall.'}
    # Six visually identified lowering/release episodes; two show confirmed release.
    extra['reviewable_placement_lowering_unique_episodes']=len(extra['reviewable_episode_groups'])
    extra['note']='Descriptive engineering grouping, not independent GT or whole-video recall.'
    (OUT/'evaluation/coverage_details.json').write_text(json.dumps(extra,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    preserved="""
| 元件 | 保留理由 |
|---|---|
| `memory_graph.v293`、`outputs_v293` | Operational/reference；419 個 frozen artifacts 符合原 manifest。 |
| `v292` canonical identity + shared import closure | V293 實際依賴 102 個 modules；不能依版本名稱刪除。 |
| YOLO11s / SAM2.1 Hiera Small / MobileNetV3 | 原 identity/perception/Re-ID 仍需要。 |
| Qwen2.5-VL-7B-Instruct | 当前 direct-event reasoning checkpoint，NF4 4-bit。 |
| Qwen2.5-VL-3B-Instruct | V293 仍實際載入；不是無用重複 checkpoint。 |
| `outputs/reference_qwen` | 原 V2945 的 exact requests、responses、46 個 PNG、labels/runtime/reports/source snapshots；73 項 hash 可核對。 |
| `v21/v22/v23/v24/v25rerun/v26/v27/v28/v29/v291` 與需要的 outputs | 實際 runtime imports、protected fixtures、canonical lineage；不是保留全部歷史分支。 |
| raw development、manifested GT/data、未知使用者媒體 | 未刪；未知/validation 內容 opaque，不遍歷、不讀 metadata。 |
| `.venv`、project/lock/config/docs/git | 活躍依賴；修復 `.venv/pyvenv.cfg` 已不存在的 Python 路徑，不改模型/套件版本。 |
"""
    model_paths='\n'.join(f"- `{x['path']}`：已刪；已知 {x['bytes']/2**30:.3f} GiB。" for x in deleted_models)
    source_paths='\n'.join(f'- `{x}`' for x in deleted_src)
    test_paths='\n'.join(f'- `{x}`' for x in deleted_tests)
    output_paths='\n'.join(f"- `{x['path']}`：{x['bytes']/2**30:.4f} GiB。" for x in deleted if x['path'].startswith('outputs_v') and x['path']!='outputs_v2946')
    put('cleanup/CLEANUP_REPORT.md',f"""
# FindMind Repository Consolidation — Cleanup Report

日期：2026-10-01。所有實作、刪除與輸出限 `mixure_test_SAM`；相鄰 `mixure_test` 未修改。

## A. Before cleanup

| 已安全稽核範圍 | bytes | GiB |
|---|---:|---:|
| 已知 repository files（排除 opaque/raw 未檢查 metadata） | {audit['audited_bytes']:,} | {audit['audited_bytes']/2**30:.3f} |
| source | {audit['sizes']['src']:,} | {audit['sizes']['src']/2**30:.6f} |
| tests | {audit['sizes']['tests']:,} | {audit['sizes']['tests']/2**30:.6f} |
| `.models` | {audit['sizes']['.models']:,} | {audit['sizes']['.models']/2**30:.3f} |
| generated outputs（另含 Molmo checkpoint/deps） | {audit['sizes']['generated_outputs']:,} | {audit['sizes']['generated_outputs']/2**30:.3f} |
| `.venv` | {audit['sizes']['.venv']:,} | {audit['sizes']['.venv']/2**30:.3f} |
| `.uv-cache` | {audit['sizes']['.uv-cache']:,} | {audit['sizes']['.uv-cache']/2**30:.3f} |

清理前 40 個 `test_*.py` modules；清理後 28 個（刪 14 個、加 2 個 current/builder modules）。完整 repository 大小沒有量測：要完整量測會違反 opaque validation / unknown raw metadata 限制。這不是完整硬碟使用量。

## B. Preserved

{preserved}

## C. Deleted

### 不再使用的模型與環境

{model_paths}

`outputs_v2946` 整體為 Molmo 分支：包含 Molmo weights/cache、remote-code、processor、`.deps/.modules`、runtime recovery、benchmark responses；不是只刪報告。SAM3/SAM3.1 官方 checkout、專用環境與權重也經實際依賴排除後刪除。

### 無活躍依賴的 source branches

{source_paths}

V2945 所需 helper 已移入 current reasoning；原 source exact bytes 另存 compact reference。V294 的 IDENTITY_ONLY 存放原 reference 記錄；活躍 trust gate 仍在 `v29/physical_gate.py`。剩餘活躍 tests/imports 不依賴已刪分支。

### obsolete tests（14 個 modules）

{test_paths}

先前 3 個 historical hash failures 隨 V241/V25 rerun output-only fixture scope 移除，**沒有宣稱修復其歷史資料**。其餘 identity、core、V293、current tests 均保留。

### 舊 outputs

{output_paths}

另刪 V293 的 `.development_attempt_01/_02` 未凍結試跑、舊 generated system audit runtime；保留 V293 原 frozen files。歷史結論已摘要成 `../ARCHIVED_EXPERIMENT_HISTORY.md`。

### caches/temp

刪 `.uv-cache`、`.pytest_cache`、manifest 列出的 Python `__pycache__`、SAM 專用 temp/dependencies。未任意刪主環境 site-packages。Molmo-only deps 原在被刪的 V2946 專用 `.deps`。少數鎖定/權限舊 cache 以明確 SAM 內絕對路徑範圍解除後刪除，最終 failures 為空。

## D. Consolidated

| 原用途 | current 檔案 |
|---|---|
| 成功的 V2945 Qwen7B loader + 原 generation backend + V2943 monitor | `src/memory_graph/reasoning/model.py` |
| clean 七欄 direct-event prompt | `reasoning/baseline_contract.py` 原 prompt；`reasoning/contract.py` 僅追加 actor/location roles |
| strict whole JSON parser / minimal validator | `reasoning/json_contract.py`、`reasoning/validator.py` |
| prepare / execute / freeze / verify | `reasoning/pipeline.py`、`scripts/run_current_pipeline.py` |
| post-freeze 統計與離線 trust simulation | `reasoning/evaluation.py`、`scripts/run_development_eval.py` |
| adaptive windows | 既有 `events` package 內 `window_builder.py`、`development_sources.py` |

audit scratch `scripts/consolidate_repository.py` 本身含 obsolete import literals，隨已完成的 cleanup tooling 移除；完整 audit/dependency/manifest 已持久保存。沒有移動受保護 source 或改 git metadata。

## E. Disk space reclaimed

已知 **{cleanup['known_deleted_files']:,} 個 files、{cleanup['known_deleted_directories']:,} 個 directories**；**{cleanup['known_reclaimed_bytes']:,} bytes = {gip:.3f} GiB**。

這是 manifest 的已知 file-byte/entry 下限：一個舊 SAM temp subtree 在刪除前無法完整 enumerate，因此實際數量可能更高。不是 filesystem allocation 或清理後新增 current artifacts 扣抵後的淨空間。所有 delete entries 最終 absence 已核對；failures = 0。

## F. Active repository structure after cleanup

```text
src/memory_graph/
  perception/, events/, memory/, vlm/, shared modules
  v21 ... v293/          # 僅保留實際 shared/reference import lineage
  events/window_builder.py, development_sources.py
  reasoning/            # current clean Qwen pipeline
scripts/
  run_v293.py           # reference
  run_current_pipeline.py
  run_baseline_same_runtime.py
  run_development_eval.py
tests/                  # 28 modules，分類 inventory 另存
.models/                # YOLO / SAM2.1 / Qwen3B / Qwen7B
outputs_v292/, outputs_v293/, required older operational fixtures
outputs/reference_qwen/ # compact exact clean baseline
outputs/current_development/
  cleanup/, event_windows/, qwen/, evaluation/, regression/, final/
```

## G. Safety

刪除依據 AST/import/reference closure、literal/model refs 與 protected manifest；先 dry-run 再依明確清單刪除。V293 imports、current imports、模型存在與 frozen identity hashes 有核對。開發資料只取既有 frozen manifests 的 test1–test9；未知/validation 路徑以 opaque 資料保護，內容未 enumerate、未 metadata、未 decode、未推論。相鄰 `mixure_test` 未寫入。完整證據：`REPOSITORY_AUDIT.json`、`ACTIVE_DEPENDENCY_MAP.json`、`CLEANUP_MANIFEST_BEFORE.json`（含 supplement）、`CLEANUP_MANIFEST_AFTER.json`、`dry_run.json`。
""")
    architecture="""```mermaid
flowchart TD
  A[已授權影片輸入] --> B[既有 YOLO + SAM2.1 候選/連續觀測]
  B --> C[TargetBinding / PersistentEntity / Re-ID]
  C --> D[Identity Guard 與觀測授權]
  D --> E[Authorized target timeline]
  E --> F[Physical transitions 與 adaptive PRE/POST windows]
  E --> G[獨立 lifecycle queue / diagnostics]
  F --> H[COMPLETE gate / actor-location candidates]
  H --> I[窗口內 5 fps ordered frames]
  I --> J[Qwen2.5-VL-7B NF4 / 7-field direct reasoning]
  J --> K[Strict JSON / minimal validator]
  K --> L[凍結 prediction / 離線工程評估與 trust simulation]
  D --> M[既有 trusted Memory Graph / Search Planner]
  L -. future reviewed integration .-> M
```

虛線本次沒有實際更新。VLM 沒有 identity authority；window geometry 只產生窗口，不判定最終物理關係。
"""
    findings='\n\n'.join(f"### {r['pack_id']}\n\n{r['finding']}\n\nFailure：`{'`, `'.join(r['failure_categories'])}`。" for r in review['events'])
    params='| 全域參數 | 值 |\n|---|---:|\n'+'\n'.join(f'| `{k}` | {v} |' for k,v in cfg.items())
    put('EVENT_WINDOW_BUILDER_REPORT.md',f"""
# FindMind — Event Window Builder Report

日期：2026-10-01。決策：**EVENT_WINDOW_BUILDER_PARTIAL_IMPROVEMENT**。密集影格已成功實測；證據捕捉改善，安全搜尋記憶沒有增加。

## 1. Why old windows were insufficient

清理前驗證 latest executable clean path 為 V2945 Qwen direct-event，而非失敗 Molmo/V2946。9 個 old packs、6 個 logical events，取自 test1/test2/test8；46 張 ordered sparse composites。原工程 review 5/9 eligible 是持握判讀可量測，沒有完整 pickup/placement/release 轉折，不等於 transition complete。舊模型 6 STATIC/3 PLACED、9 NONE relations，safe memory 0。

## 2. New builder design

deterministic target-centric timeline → state transition trigger → backward stable PRE / forward stable POST → seconds-based bounds → completeness/chain gate → independent physical/lifecycle budget → actor/location roles → dense window-only evidence。

{architecture}

## 3. State timeline

合併既有 V292 canonical sampled metadata、trusted memory observations/masks 與已授權 V293 dense rows。VISIBLE/MATCHED 必須具 trusted observation 或既有 geometry authorization；candidate 外觀本身不成 phone_01。保存 frame/time/FPS、authorized bbox/mask/provenance、chain_id、observed/partial/untrusted/unobserved、motion speed/state、existing actor associations。PARTIAL 為 bbox 邊界 proxy，非新 learned visibility model。

幾何使用 normalized image-diagonal speed，若至少兩個同 track location contexts 連續存在，減去其 median translation 以粗略補攝影機移動。這不是完整 camera motion compensation，因此仍會產生 false physical triggers。沒有新 YOLO/SAM 推論，也沒有用 GT 或 VLM 建 window。

## 4. Transition triggers

STATIONARY_TO_MOVING、MOVING_TO_STATIONARY、MOVEMENT_TO_UNOBSERVED 等 physical patterns；appearance/recovery/gap/continuity 類另入 lifecycle。任何 trigger 都不是 PICKED_UP/PLACED 的 truth label。持握 hand/person source 只用原 detector observations，沒有新增手部 detector。

## 5. Adaptive start/end logic

{params}

同一組全域參數適用 test1–test9。後向找稳定 PRE；前向找稳定 POST，延續到 post dwell，考慮 observation gap、chain continuity、scene/timebase 和界限。最大 6 秒，找不到即 INCOMPLETE；不依影片調整。窗口參數修正次數 **0**。實際 COMPLETE 時長 2.4–4.8 秒。

## 6. Completeness gate

只有 HAS_PRE_STATE + HAS_TRANSITION + HAS_POST_STATE，且 duration/authorization/chain 条件通過才是 COMPLETE。8 個 INCOMPLETE 沒有送 physical Qwen。自動 complete 與視覺 complete 分別報告，不能把存在 state trigger 當實際語意轉折。工程檢查 9 個 dispatched 有 6 個視覺完整動作窗口；其餘 test2 W01/test5 W01/test8 W07 主要是 stationary/camera triggers。test3 W02/W03 雖可視覺看到轉折，卻因授權/PRE 穩定 gate 拒絕，屬 false-negative coverage。

## 7. Lifecycle vs physical events

每影片 physical budget 4、lifecycle budget 6，獨立選取；本次 17 physical + 52 lifecycle。test6 沒有合格 physical trigger，沒有硬塞窗口；test9 僅 incomplete，仍 unresolved。Lifecycle 未耗用 physical budget，不送此次 physical reasoning。

## 8. Actor vs location context

原 person/hand/arm/carrier 類為 actor，其他 detector-supported objects 為 location candidate；最多 2 actor + 3 location。15/17 窗口供有 actor、16/17 供有 location，**不代表供有正確目的地**。無 actor 可答 NONE。保持原七欄命名 `interaction_anchor`，prompt 只追加 roles。test5 box 被原偵測叫 laptop、test8 T 別名混入 location、test8 W04 椅子被叫 person 皆為已凍結 context 限制，review 不改輸入。

## 9. Temporal representation

**DENSE_ORDERED_EVENT_FRAMES**：現有 image backend 已可運行，沒有另加 video architecture。每窗口取接近 5 fps 的順序 frame，保留界限/trigger；9 次共 **{sum(len(r['images']) for r in req)} 张 800×600 composites**，每次 {min(len(r['images']) for r in req)}–{max(len(r['images']) for r in req)} 張。所有 frame 都在 adaptive boundaries 內，T 只標授權 frame，未插值 target，未靠將來影格補身份。圖上的 BEFORE/DURING/AFTER 是 trigger-relative phase，不是 action GT。

初次 dense run 的 Windows SDPA math fallback 在約 12k tokens 配出 15.17 GiB attention matrix，4 個已完成 OOM、第五個中斷；保留 `qwen/runtime_compatibility_initial`。唯一通用 runtime 修正是在同 SDPA 中優先 cuDNN、math fallback；checkpoint/quantization/image dimensions/prompt/request/frame/builder parameters 全不變。三種 causal GQA、vision noncausal、cached decode synthetic checks 通過。修正後 9/9 EOS、0 OOM/timeout，再把舊 9 packs 用相同 runtime 全重跑。這是 runtime correction 1，不是 window tuning。

## 10. Window-quality results

{rows}

| 指標 | 結果 |
|---|---:|
| 選取物理窗口 | 17 |
| 自動 COMPLETE / INCOMPLETE | 9 / 8 |
| 自動 complete rate | 52.9% |
| 視覺完整 PRE→transition→POST（所有 selected） | 8/17 |
| 視覺完整（已 dispatch） | 6/9 |
| 個別 direct reasoning eligible（selected） | 14/17 |
| reasoning eligible（已 dispatch） | 8/9 = 88.9% |
| 可檢查 placement/release/放低轉折 | 10/17；其中 5 個送 Qwen |
| 明確可見放手 | 3 packs，2 次實際 episode（test1/test8） |

「可檢查」包括箱口放低/遮擋，不宣稱都真的放手。10 packs 合併重疊窗口為 6 個可檢查 episode；有兩次確認 release。沒有全片獨立 GT action census，因此**不能報全影片 placement recall**。視覺 labels 為執行代理的 post-freeze 工程 review，非獨立人類標註或完整模型 accuracy。

{event_table}

## 11. Qwen results

9/9 schema、8/9 minimal validator；1 個 STATIC_RELEASE 被拒。全部 9 個 event_type 都 STATIC；relation ON 2 / NONE 6 / INSIDE 1。6 個視覺完整且已 dispatch 的動作窗口，event type **0/6**；3 個確認 release packs，release YES **0/3**。整体 3/9 event 正確主要來自原本靜置/camera窗口，不能宣稱 physical action 已改善。

{table}

新 final relation 有 1 個 containment truth 不可決，故 denominator 8；其餘欄位依 review admissible values 評分，UNCERTAIN 表示供圖不能證明 release。invalid answer 沒有從內容 denominator 排除。

load {runtime['load']['seconds']:.2f} 秒；9 次 inference {runtime['inference_seconds']:.2f} 秒；peak **global GPU used** {runtime['peak_global_gpu_bytes']/2**30:.2f} GiB。這是 monitor 的全 GPU 使用量峰值，非僅此 process 的 tensor allocation。無答案重試；初次 aborted runtime 另列，未混入 canonical 9 calls。

## 12. Baseline vs new-window comparison

原 V2945 frozen benchmark unchanged，另用新 cuDNN SDPA 在 exact old prompt/images 重跑 9 次：9 EOS/9 schema/7 validator、{old_runtime['inference_seconds']:.2f} 秒。3 個答案的 visibility/confidence 有差異；event/actor/release/relation fields 不變。舊 fresh eligible 5/9，新 8/9；明確 transition capture 0 old → 8 selected / 6 dispatched new；old confirmed release 0 → new 3 packs/2 episodes。

表中 primary comparison 用 **fresh same-runtime baseline**。同 checkpoint/revision/NF4/BF16/preprocessing/generation/kernel；minimal actor/location prompt adaptation 是已知 confound。Old 只 test1/test2/test8、新 builder 包含 9 個 manifested scenes，只有 6 個影片有 COMPLETE dispatch；boundary/contexts/class proportions 改變且 packs 相關。另存同 scene subset 5 new packs，但不是相同事件 paired accuracy。不能從小樣本數據宣稱純因果模型 accuracy 提升。

release 6/9 → 3/9、relation 7/9 → 5/8 變差；visibility 3/9 → 7/9 改善；actor 1/9 → 3/9、location 5/9 → 6/9，但新動作窗口仍沒判對 actor/action。Unsafe 3/9 → 3/9，safe memory 0 → 0。因此只判 **PARTIAL_IMPROVEMENT（evidence quality）**。

## 13. Safe searchable memory

沿用保守 V2945 offline mapping，不改 operational Memory Graph trust policy。SUPPORTED real relation 仍需 material assertions safe；weak relation 還需 search usefulness；invalid/unsafe/wrong relation 拒絕。結果 P=0/C=0/U=4/R=5，**safe searchable memory 0/9**，actual identity/physical writes、Memory Graph/Search Planner updates 全為 0。NONE abstention 有價值但不會產生位置記憶；test1 W03 ON B 雖對，其他核心事件/放手欄位錯，未 promotion。

## 14. Failure cases

{findings}

test1 W03/W05 是相同 underlying frames/boundaries，不同 trigger-phase，算相關 packs；test3 和 test4 也有重疊。同事件去重尚待後續，不把它們算独立成功。`evaluation/failure_analysis.json` 使用指定 taxonomy，review 後沒有調模型/窗口。

## 15. Remaining bottleneck

**Qwen7B 對標記區域的時序動作理解**：即使 release/pickup 全程存在，仍全判 STATIC、動作 actor 全判錯，無法產生安全記憶。先凍結這次 evidence 與結果；後續問題按優先序：①動作/actor/release推理；②location 的 self-alias、錯誤 detector class、實際目的地缺失；③camera compensation與完整gate false positive/negative；④重疊事件去重、trigger phase bias；⑤獨立 GT/人類 review 與 unique-episode metrics；⑥解耦舊 shared lineage 路徑；⑦安全規則下的 operational memory integration/端到端延遲。此次沒有調上述參數、改模型或做新 validation。

## 16. Validation readiness

**READY_TO_FREEZE_FOR_VALIDATION**：repo dependency consolidation 完成、current executable、dense runtime defect 已修正、原始預測與 architecture frozen、Identity Guard 安全無變。READY 指可做預先凍結的 held-out 量測，**不是 production-ready 或 physical reasoning 成功**。下一個科學上有用步驟是同設定 held-out 評估，不再依 development 單片調 window。詳細冻结條件見 `VALIDATION_HANDOFF.md`；本次未讀/跑新 validation。
""")
    put('CURRENT_PIPELINE_REPORT.md',f"""
# FindMind — Current Pipeline Status

日期：2026-10-01。Repository consolidation、adaptive event windows、dense Qwen development inference 與報告完成。

## 決策摘要

**EVENT_WINDOW_BUILDER_PARTIAL_IMPROVEMENT**；**READY_TO_FREEZE_FOR_VALIDATION**。

已捕捉更多真正 pickup/放手/遮擋 evidence，但 Qwen9/9 STATIC，動作窗口 event 0/6、明確 release 0/3，safe searchable memory 0/9。這是可量測的 development 結果，不宣稱模型準確率已改善或可部署。

## 現在保留什麼

{preserved}

Current entrypoint：`scripts/run_current_pipeline.py`；source：`memory_graph.events.window_builder` + `memory_graph.reasoning`。V293 原 operational/reference 及 trusted identity/memory pipeline 保留；沒有硬把 102 個 shared modules搬成新 core/identity 架構。不存在新的版本號實驗堆疊。

## 架構與權限

{architecture}

TargetBinding 建立目標、YOLO/SAM2候選/propagation、Re-ID similarity ≥ .60 且 best-second margin ≥ .10，再經 Identity Guard；候選/local IDs 不自動升為 PersistentEntity。授權 timeline 才能給 T marker。event/VLM 不可改身份、bank、guard、SAM reinit；下游 physical proposals 本次只 offline simulation。V293 原 promoted/identity-only/trust semantics 在 preserved source/hash/test 下有效。

## 模型及環境

Qwen/Qwen2.5-VL-7B-Instruct，revision `cc594898137f460bfe9f0759e9844b3ce807cfb5`；NF4 double quant / BF16，transformers4.57.6、torch2.10.0+cu128、CUDA12.8、RTX5070Ti16GB。相同 image preprocessing、800px thumbnail、greedy、max_new_tokens1400、120秒 timeout。

唯一 runtime correction：same SDPA 優先 CUDNN_ATTENTION，MATH fallback；解决 Windows dense math attention OOM，沒有降低 dense frames/尺寸/precision。修正前 abort4OOM+第五中斷；修正後 actual9/9EOS，inference133.36s，global peak11.01GiB。精確 config 在 `qwen/model_config.json`。`.venv` 的失效 Python home已修復；Windows 使用 `-X utf8 -B`，避免中文工程報告被 cp950 stdout 阻擋。

## Event Window Builder 完成度

已實作 trusted seconds-based timeline、motion/visibility/actor-association triggers、adaptive PRE .7s / POST1s、2–6s bounds、complete gate、獨立4 physical/6 lifecycle budgets、2 actor/3 location roles、5fps ordered frames與frozen manifests。沒有 window tuning（corrections0）。

{rows}

已處理 frozen manifested test1–test9（9部）上下游歷史授權資料；本次 fresh adaptive frame decode + Qwen inference，**沒有把 YOLO/SAM/Re-ID 全部重新跑**。test6無physicaltrigger、test9只有incomplete，皆有 timeline/diagnostics。Raw media hashes/timebase記於 `event_windows/development_inputs.json`，與 V292 manifests 核對。

## Development 結果

17 physical selected、9complete/8incomplete、52獨立lifecycle；自動complete52.9%。工程review視覺complete8/17（dispatch6/9），eligible14/17（dispatch8/9），placement/放低/release可檢查10/17，確認release3packs/2episodes。Old eligible5/9 → new8/9，但跨事件/scene分布改變，非pairedaccuracy。

{table}

Actual9EOS、9schema、8validator；unsafephysical3/9同舊3/9；safe searchable memory0、P/C/U/R=0/0/4/5。完整動作6packs全部STATIC錯，confirmed release3packs全答NO。原 frozen baseline沒有覆寫；fresh same-runtime old9calls另保存。

## Repository 清理

已刪已知 {cleanup['known_deleted_files']:,} files / {cleanup['known_deleted_directories']:,} directories，reclaimed {cleanup['known_reclaimed_bytes']:,} bytes = {gip:.3f}GiB（下限）。Molmoweights/code/tests/remote-code/deps/outputs全部移除；unusedSAM3/SAM3.1權重與環境、obsoleteVLMbranches/14testmodules/大型歷史outputs/caches移除。原Qwen exact baseline consolidation後原V2945versionfolder刪除。完整清單及理由見 `cleanup/CLEANUP_REPORT.md`，歷史摘要見 `ARCHIVED_EXPERIMENT_HISTORY.md`。

## 測試與安全

28active testmodules；focused116pass、full346pass、0fail/skip。原3historical hash failures是obsoletefixture scope刪除，不是修好。V293419frozenfiles通過、canonical identity/memory hashes不變；test2 fusion、test7 safety、test8f804/forward recovery、test9unresolved保留。unauthorizedMATCHED0、VLMidentitywrites0、actualphysicalwrites0。沒有改相鄰mixure_test，也沒有讀取新validation內容。

## 尚未完成與問題優先序

| 優先 | 問題 | 證據/後續量測需求 |
|---|---|---|
| P0 | Qwen event/actor/release理解 | complete action0/6、release0/3；需凍結證據測一般化，不能再以增加影格當已解決。 |
| P1 | 正確独立location context | phone self-alias、箱誤分類laptop、正確destination沒marker；需 generic context contract/來源改善。 |
| P1 | motion/complete gate | camera falsephysical3/9；test3兩個視覺complete被拒；需独立標註與camera/stability診斷。 |
| P2 | episode dedup/phase | test1重複窗及test3/4重疊；當前計pack、不可假設獨立sample。 |
| P2 | 評估可信度 | review是執行代理、非blind獨立human GT；無全片physicalGT，未知 recall。 |
| P2 | operational memory integration | 本次僅離線，沒有將Qwencandidate接進trustedgraph；safe0所以不能啟用無保護寫入。 |
| P3 | 維護與性能 | sharedlegacyimports仍必要；.venv依本機bundledPython；load/kernelwarmup和完整perception端到端成本未量測。 |

## 如何使用已凍結結果

```powershell
# 工作目錄必須為 mixure_test_SAM
.venv/Scripts/python.exe -X utf8 -B scripts/run_current_pipeline.py verify
.venv/Scripts/python.exe -X utf8 -B scripts/run_current_pipeline.py verify-reference
.venv/Scripts/python.exe -X utf8 -B scripts/run_v293.py verify
.venv/Scripts/python.exe -X utf8 -B scripts/run_development_eval.py
```

`prepare/run` 受 frozen artifact guard限制，不能覆寫已凍結 results。上述eval只重建review衍生統計，不改prediction；正式交付後如要維持finalintegritymanifest，應先核對已存JSON，不任意覆寫衍生files。未新增接受任意validationmedia的入口，本次handoff是凍結規格而非已執行的validation。

## 報告索引

- `cleanup/CLEANUP_REPORT.md`：A–G完整清理與保留理由。
- `EVENT_WINDOW_BUILDER_REPORT.md`：16節、17窗逐事件失敗歸因。
- `evaluation/baseline_comparison.json`：original/同runtimeold/new/matchedscene。
- `evaluation/window_quality.json`、`coverage_details.json`、`reasoning_metrics.json`、`search_memory.json`。
- `regression/test_results.json`、`identity_safety.json`。
- `final/artifact_manifest.json`、`baseline_prediction_manifest.json`、`final_integrity_manifest.json`。
- `VALIDATION_HANDOFF.md`：模型、prompt、全域params、選窗/roles/validator/metrics凍結。

## Validation readiness

READY_TO_FREEZE_FOR_VALIDATION：architecture與identity safety可重現，denseAPI/runtime已有真實測量，沒有阻止量測的已知contract/runtime defect。既有context與模型推理缺陷是要量測的limitations；READY不代表準確或production-ready。下一步held-out應一次使用相同frozen配置，預先定denominator、保留unsafe/write門檻；本次停止於development報告。
""")
    frozen_source_table='| 檔案 | SHA256 |\n|---|---|\n'+'\n'.join(f'| `{p}` | `{h}` |' for p,h in sources.items())
    put('VALIDATION_HANDOFF.md',f"""
# FindMind — Frozen Validation Handoff

狀態：**READY_TO_FREEZE_FOR_VALIDATION**。本檔是預先凍結規格；沒有讀取validation filenames、metadata、thumbnail或影格，沒有跑validation。

## Model / environment

Qwen/Qwen2.5-VL-7B-Instruct；revision`cc594898137f460bfe9f0759e9844b3ce807cfb5`；本地`.models/Qwen2.5-VL-7B-Instruct`；NF4 double/BF16；torch 2.10.0+cu128、transformers 4.57.6、bitsandbytes 0.50.2、SDPA cuDNN preferred/MATH fallback。原 checkpoint hash 證據見 `outputs/reference_qwen/checkpoint_verification.json`。Greedy/max_new_tokens 1400/timeout 120s/800px image，各 frame composite 800×600；不可在看 validation 後調分辨率/量化/frames。

## Prompt / contract

七欄：event_type、interaction_anchor、released、target_visible_after、final_relation、final_relation_anchor、confidence。No frame citation/geometry questions/examples。只在原cleanprompt增加actor/locationrole宣告。Exact current prompts在`qwen/requests.json`；template/schema的hash如下。不能把BEFORE/DURING/AFTERphase當actiontruth。

## Builder parameters

{params}

Builder initialconfiguration只有一組，globalcorrections0。1個runtimeSDPA修正記於`cleanup/runtime_correction.json`，不更改windowboundaries。時基來自明確授權manifest，不硬編framecount。

## Identity / actor / location policy

Re-IDsimilarity .60、best-secondmargin .10；IdentityGuard、PersistentEntity、YOLO、SAM2.1、bank、trust/searchpolicy保持原hash。T只能是當frame授權observation，不追認untrustedphone、不用futureframes選phone_01。Actor只原person/hand/arm/carrier，其他detectorclasses做locationcandidate；無actor允許NONE。最多2actors/3locations；location誤分類/alias需原樣記錄，不能看validation後手動換正確anchor。

## Selection / completeness

物理/lifecyclequeues獨立budget4/6。對motion/stability/visibilitypattern deterministictrigger，後向/前向找stablePRE/POST；chain、gap、durationgate通過才COMPLETE。Physicalreasoning只送COMPLETE，INCOMPLETE保留診斷。NoGT/VLM選窗。Denseordered5fps+boundaries/trigger，絕不跨界補frame；沒有per-videotuning，不能強迫沒有trigger的影片生成動作窗口。

## Validator / memory policy

StrictwholeJSONparser、exact7fields/enums、suppliedmarkercheck、minimalconsistencyvalidator，無geometryreasoner。Validatorpass不等於真實物理正確。VLMidentitywrites0；現在memorymapping只offlineengineeringreview，realrelation+SUPPORTED+safe-material才能simulatepromotion，wrong/unsafe/invalidreject；沒有actualtrustedwrites。不得用validationreviewlabels作operationalidentityauthority。

## Evaluation plan / denominators

先freezeboundaries/selection/requests/responses/parsed/deterministicmetrics，再獨立視覺review；不要修改prediction。報selected/complete/incomplete、全片有無physicaltrigger、PRE/transition/POSTvisualcomplete、actor/locationavailability、revieweligible、可檢查lowering/release與confirmedrelease分開、uniqueepisode與pack數分開。沒有全片independentGT不可報recall。逐欄可決denominator，不可決單列；invalid/schemafail仍計入calleddenominator。ALL與eligible分層都報event/actor/release/visibility/relation/anchor、unsafephysical、safe-searchablememory、actualwritecount、runtimeglobalVRAM。評估taxonomy保持原14類。Developmentreview是執行代理，正式validation宜獨立humanreview，避免把這次review當GTfeed回模型。

## Reference and reproducibility

V293419frozenfiles、compactQwenreference73files、primary330files、same-runtimebaseline5files與sourcehash核對。完整releaseepisode目前只有2次development，事件type偏STATIC與selflocationcontext是既知限制；下一個科學步驟為固定architectureheld-out測量，不在此要求perfectaccuracy或繼續調development。

{frozen_source_table}

Exactfinalartifact/reporthash見`final/final_integrity_manifest.json`與`final_integrity_verification.json`；相鄰`mixure_test`不作此pipeline工作區。
""")
    print('Reports written; coverage',extra)

if __name__=='__main__':main()
