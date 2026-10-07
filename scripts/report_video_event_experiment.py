"""Read frozen comparison and produce the requested sixteen-section report."""
import json
import sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from memory_graph.reasoning.video_experiment import EXP,OUT,read

def ratio(x):return f"{x['correct']}/{x['denominator']} ({x['rate']:.1%})" if x['denominator'] else '不可決'
def table(result):
    text='| 欄位 | Image | Video |\n|---|---:|---:|\n'
    for f,name in [('event_type','事件'),('interaction_anchor','Actor'),('released','Release'),
        ('target_visible_after','最末可見性'),('final_relation','關係'),('final_relation_anchor','Location／關係對象')]:
        text+=f"| {name} | {ratio(result['image']['ALL'][f])} | {ratio(result['video']['ALL'][f])} |\n"
    return text

def main():
    decision=read(EXP/'evaluation/decision.json');all9=read(EXP/'evaluation/paired_all9.json')
    action=read(EXP/'evaluation/paired_complete_action6.json');release=read(EXP/'evaluation/paired_release3.json')
    eligible=read(EXP/'evaluation/paired_eligible.json');unique=read(EXP/'evaluation/unique_episode_analysis.json')
    compute=read(EXP/'evaluation/compute_comparison.json');memory=read(EXP/'evaluation/search_memory.json')
    review=read(EXP/'evaluation/post_freeze_video_review.json');runtime=read(EXP/'qwen/runtime.json')
    pm=read(EXP/'processor/processor_metrics.json');clips=read(EXP/'videos/video_manifest.json')
    conf=read(EXP/'config/experiment_config.json');relation=read(EXP/'evaluation/relation_analysis.json')
    regression=read(EXP/'regression/test_results.json')
    density=read(EXP/'evaluation/annotation_density.json')
    unsafe=read(EXP/'evaluation/unsafe_sensitivity.json')
    pt='| pack | source FPS | source clip frames | requested FPS | sampled frames | effective FPS | selected T marks | visual tokens |\n|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for m in pm:pt+=f"| {m['pack_id']} | {m['source_fps']:.5f} | {m['encoded_frame_count']} | {m['requested_processor_fps']} | {m['actual_selected_frame_count']} | {m['effective_processor_fps']:.3f} | {m['selected_T_authorized_frames']} | {m['visual_tokens']} |\n"
    rt='| pack | Image release | Video release | Frozen reference | Image 正確 | Video 正確 |\n|---|---|---|---|---|---|\n'
    for r in release['rows']:rt+=f"| {r['pack_id']} | {r['image_answer']['released']} | {(r['video_answer'] or {}).get('released')} | YES | {r['image_correctness']['released']} | {r['video_correctness']['released']} |\n"
    ur='| unique release episode | Image（所有窗口一致正確） | Video（所有窗口一致正確） |\n|---|---|---|\n'
    for r in unique['RELEASE']['rows']:ur+=f"| {', '.join(r['pack_ids'])} | {r['image_all_correct']['released']} | {r['video_all_correct']['released']} |\n"
    times='| pack | 推論秒 | wall秒（含 processor） | GPU used GiB | allocated GiB | reserved GiB | CPU RSS GiB | EOS |\n|---|---:|---:|---:|---:|---:|---:|---|\n'
    for r in read(EXP/'qwen/responses.json'):
        t=r['compute_trace'];times+=f"| {r['pack_id']} | {t['runtime_seconds']:.2f} | {t['wall_seconds']:.2f} | {t.get('global_gpu_used_peak_bytes',0)/2**30:.2f} | {t['peak_allocated_bytes']/2**30:.2f} | {t['peak_reserved_bytes']/2**30:.2f} | {t.get('process_RSS_peak_bytes',0)/2**30:.2f} | {t.get('ended_with_EOS')} |\n"
    findings='\n\n'.join(f"### {r['pack_id']}\n\n{r['finding']}\n\n歸因：`{'`, `'.join(r['failure_categories'])}`。" for r in review['events'])
    text=f"""# FindMind — Native Annotated Event Video Experiment

日期：2026-10-02。結論：**{decision['decision']}**。Representation：**{decision['representation']}**。

## 1. 實驗問題

相同 adaptive event windows 改用原生 annotated video 與更密 temporal sampling，能否改善 Qwen2.5-VL-7B 的動作、actor、release 推理？主要比較凍結的 action6（image0/6）與 release3（image0/3），不是只看 JSON 或輸出多樣性。

## 2. 唯一改變的變數

```mermaid
flowchart LR
  F[相同9個COMPLETE凍結窗口] --> A[Image baseline 5fps ordered images]
  F --> B[Video condition source-FPS annotated MP4]
  B --> P[官方 native video processor 15fps]
  A --> Q[同一 Qwen7B NF4 / prompt semantics / validator]
  P --> Q
  Q --> E[凍結結果 / 相同 reference paired review]
```

YOLO/SAM2.1/MobileNet、TargetBinding/PersistentEntity/Re-ID(.60/.10)/Identity Guard、timeline、17窗選擇/9個COMPLETE、boundaries/triggers、候選、window parameters、review strata、Memory Graph/Search Planner均未改。沒有重跑 A，沒有 deduplicate 再推論。Model revision `cc594898137f460bfe9f0759e9844b3ce807cfb5`、NF4 double/BF16、transformers4.57.6、torch2.10.0+cu128、CUDA12.8、SDPA cuDNN/MATH、greedy1400tokens/120s與 image baseline相同。

Prompt 只把 chronological visual sequence/image phase/reference panels 改為 supplied event video/video frames；七欄/enums/roles/minimal validator保持相同。影片編碼/temporal patch packing為 native modality的一部分；沒有改解析度來取得優勢。

## 3. Annotated Video 如何生成

只解碼 `event_windows/development_inputs.json` 已授權的 source paths，九個窗口共有952來源影格。包含 frozen start_frame到end_frame，每一來源 timestamp均在原bounds；inclusive最後frame使encoded duration多至1/sourceFPS，已逐片核對正常timebase tolerance。原來源FPS約29.986–30，MP4保留該FPS、800×600、H.264(libx264)、CFR、yuv420p、CRF18/presetmedium/threads1、無音訊。

Reuse現有 `render_frame`：同T/A/B/C colors、bbox線寬、same-frame crop panels；每一exact frame只能用原timeline authority與原候選觀測，無T/actor/location forward/backward-fill或新detector。不修箱的laptop誤分類、selfalias、缺table/destination。BEFORE/DURING/AFTER是原trigger-relativephase，沒有PICKUP/RELEASE真值提示。影片中未授權frame不畫T，這也使標記密度與來源fps不同；下表明確報processor看到多少T標記。

9個MP4 path/hash、sourcefps/count/size、decodedpts/CFR/audio/authority records完整存`videos/video_manifest.json`。PyAV16.0.1安裝在experiment自己的`.deps`，未修改主`.venv`。

## 4. Qwen 實際吃到多少 temporal evidence

使用目前 transformers 的官方 `apply_chat_template` video modality，video processor從MP4自行採樣；沒有把影片轉成manual image-list request。沒有使用default2fps。Nativevideo輸出`video_grid_thw`和`pixel_values_videos`，非`image_grid_thw/pixel_values`。

{pt}

總計 **{compute['video_selected_frames']} selected frames**，baseline **{compute['image_frames']} images**。每窗口有效取樣 {min(m['effective_processor_fps'] for m in pm):.3f}–{max(m['effective_processor_fps'] for m in pm):.3f}fps，全部≥10且明顯高於5fps。Requested15fps因官方temporal patch2取整而略低；sourceMP4約30fps不等於model觀察fps。實際indices/timestamps由官方sampler原回傳值記錄，沒有捏造。

Exact-frame標記限制：image有T標記 {density['image_T_marked_frames']}/{density['image_sampled_frames']}；video官方選入有T標記 {density['video_T_marked_selected_frames']}/{density['video_selected_frames']}。相同授權政策下，native採到更多無上游標記的frame。未標T不等於真實目標不可見；這是grounding interpretation的限制，不能宣稱純FPS造成所有差異。

唯一通用compatibility correction：transformers4.57.6無法把return_metadata的VideoMetadata tensorize，改用transparent observer記錄未改動的官方sample_frames；沒有換sampler/processor/config/frames。初次CPU metadata失敗沒有generation或semanticreview。兼容修正次數{conf['compatibility_corrections']}；15→10 OOM fallback **未使用**。

## 5. Runtime

最長窗口test8 W07作唯一technicalpreflight，36.81秒EOS、沒有語意review；正式九次每event一次、無答案retry。Model load {runtime['load']['seconds']:.2f}s；generation inference {runtime['inference_seconds']:.2f}s；含processorwall {runtime['wall_inference_seconds']:.2f}s；globalGPU peak {runtime['peak_global_gpu_bytes']/2**30:.2f}GiB。EOS{runtime['EOS_count']}/9、OOM{runtime['OOM_count']}、timeouts{runtime['timeouts']}、runtimeerrors{runtime['runtime_errors']}。

上述canonical時間不含36.81秒preflight、clip編碼、或第一次CPU metadata失敗的額外初始化；初次失敗沒有generation。所有generation/inputtoken與個別記憶體細項存qwen/responses.json。

{times}

Image baseline133.36s（原wall measurement）/globalpeak11.01GiB。Tokens：image input{compute['image_input_tokens']:,}/visual{compute['image_visual_tokens']:,}；video input{compute['video_input_tokens']:,}/visual{compute['video_visual_tokens']:,}。Video temporal patch將兩個frames一起編碼；visualtokens不同，runtime只作描述，不宣稱吞吐改善。Global GPU used含其他process，allocated/reserved為本process tensor峰值。

## 6. ALL 9 paired result

{table(all9)}

Schema image{all9['image']['schema_valid']}/9 vs video{all9['video']['schema_valid']}/9；validator image{all9['image']['validator_valid']}/9 vs video{all9['video']['validator_valid']}/9。Finalrelation保留原一個不可決，因此denominator8；invalid outputs不從calleddenominator排除。Primary reference完全沿用image凍結工程review，非獨立humanGT。

Reasoning-eligible固定8，不因video結果重新分層：

{table(eligible)}

## 7. 6 個完整動作窗口

**Image event0/6 → Video event{action['video']['ALL']['event_type']['correct']}/6**。

{table(action)}

六packs包括test1重複兩窗；unique action為5episodes，保守所有同episode窗口正確：image{unique['ACTION']['image_all_correct']['event_type']}/5 → video{unique['ACTION']['video_all_correct']['event_type']}/5。`paired_complete_action6.json`保留每個answer與欄位正誤，不能用其他靜置窗口STATIC正確冒充動作成功。

## 8. 3 個確認 release windows

**Image release0/3 → Video release{release['video']['ALL']['released']['correct']}/3**。

{rt}

Unique release2episodes：

{ur}

保守all-window agreement：image0/2 → video{unique['RELEASE']['video_all_correct']['released']}/2；any-window成功另存，未把test1兩窗算成兩次真實release。Reference仍YES，video新看見的任何review分歧另記，不覆寫原labels。

## 9. STATIC collapse

Image：STATIC9/9。Video distribution：`{all9['video']['event_types']}`。分類：**{decision['STATIC_collapse']}**。多樣性本身不等於正確，判斷以primary action/release與安全為準。

## 10. Actor reasoning

Image {ratio(all9['image']['ALL']['interaction_anchor'])} → Video {ratio(all9['video']['ALL']['interaction_anchor'])}；action6的actor {ratio(action['image']['ALL']['interaction_anchor'])} → {ratio(action['video']['ALL']['interaction_anchor'])}。Location另外計，不合併為anchoraccuracy。誤分類person/未標actor是upstream context，供有正確A/B卻選錯是reasoning error。

## 11. Final visibility / physical relation

Visibility {ratio(all9['image']['ALL']['target_visible_after'])} → {ratio(all9['video']['ALL']['target_visible_after'])}；relation {ratio(all9['image']['ALL']['final_relation'])} → {ratio(all9['video']['ALL']['final_relation'])}；relationlocation {ratio(all9['image']['ALL']['final_relation_anchor'])} → {ratio(all9['video']['ALL']['final_relation_anchor'])}。Appropriate final-relation abstention image{relation['appropriate_abstention_image']} → video{relation['appropriate_abstention_video']}；這只評關係abstention，不表示整個answer正確。

test8 self-alias、test3缺box marker、test5 box被叫laptop保持既有分類，不自動歸因為Qwen，不靠VLM補身份。供圖最後可見性描述不代表physicalabsence。

## 12. Search memory

沿用相同`evaluation.simulation`，只offline proposal，沒有actualMemoryGraph/SearchPlanner/trustedphysical/identitywrites。Image P/C/U/R：`{memory['image']['P_C_U_R']}`；video：`{memory['video']['P_C_U_R']}`。

Safe searchable memory image{memory['image']['safe_searchable_memory']}/9 → video{memory['video']['safe_searchable_memory']}/9。Unsafephysicalclaims image{memory['image']['unsafe_physical_claims']}/9 → video{memory['video']['unsafe_physical_claims']}/9。Wronglocationmemory image{memory['image']['wrong_location_memory']} → video{memory['video']['wrong_location_memory']}。錯actor/visibility另計；unsafe沿用「未建立的肯定placement/release/real relation」定義。不同video答案需重新工程reviewsafe flags，但reference truth完全不改。

Sensitivity：僅計validator-valid的unsafe，image {unsafe['validator_valid_unsafe_image']} → video {unsafe['validator_valid_unsafe_video']}，仍增加；整體退步判斷不是只取決於invalid NEAR/NONE那一筆。拒絕所有錯誤proposal的既有trust gate仍保護實際memory，actual錯誤位置寫入0。

## 13. Image vs Video 到底誰比較好

**{decision['decision']}**；選擇 **{decision['representation']}**。Predefined selection：至少2個uniqueaction或1個unique release all-window agreement改善，且unsafe不增加、actor不下降、safe memory不下降。實際primary action={decision['complete_action_event_correct']}/6、release={decision['confirmed_release_correct']}/3、uniquerelease={decision['unique_release_correct']}/2；輸出多樣性不作選擇理由。

## 14. 真正瓶頸

{review['bottleneck_conclusion']}

{findings}

Reference disagreements：`{review.get('reference_disagreements',[])}`。未修predictions、truth、sourcecandidates、窗口或模型。High-density nativevideo是本次已實際測到的條件；如果accuracy差，屬有效負結果，不能因此叫experimentinvalid。

## 15. Validation representation decision

**{decision['representation']}**。若KEEP_IMAGES，原`VALIDATION_HANDOFF.md` bytes/hash完整保留；若VIDEO被選，只在comparison/decision凍結後更新handoff且存previoushash。所有upstream/window/identity/validator/metrics凍結條件繼續適用。

Regression：video focused {regression['video_focused']['tests']}、current focused {regression['current_focused']['tests']}、full {regression['full']['tests']}；各errors/failures0。既有370-file交付hash與V293419files保護核對；test2/test7/test8f804及forward/test9unresolved不變。UnauthorizedMATCHED0、VLMidentitywrites0、actualtrustedphysicalwrites0。相鄰mixure_test未修改；held-out內容未列舉/metadata/解碼/推論。

## 16. 下一步

**{decision['next_step']}**

本次停止於凍結representation與報告，不執行held-out。Exactpaired JSON、rawanswers、processorindices、MP4與finalmanifest皆存這個experiment目錄。
"""
    p=EXP/'VIDEO_EVENT_EXPERIMENT_REPORT.md';p.write_text(text,encoding='utf-8')
    print('Report:',p)

if __name__=='__main__':main()
