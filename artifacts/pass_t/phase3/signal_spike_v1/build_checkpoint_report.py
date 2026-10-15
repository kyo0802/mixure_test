"""Post-seal reporting only; no inference. Human records never return to runtime."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(n,d):
    p=OUT/n
    if p.exists():
        raise RuntimeError(f"Refusing overwrite: {p}")
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")


def main():
    receipt=read(OUT/"COMPUTED_STATES_RECEIPT.json")
    assert sha(OUT/"COMPUTED_STATES.json")==receipt["computed_sha256"]
    data=read(OUT/"COMPUTED_STATES.json")
    run=read(OUT/"RUN_RECEIPT.json")
    frames=data["frames"]
    # Explicitly separate after-seal evaluation from the inference program.
    humanpath=ROOT/"artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1/HUMAN_ADJUDICATED_CALLS.json"
    humans=read(humanpath)
    comparisons=[]
    comments={
        1:("test5 F0001/F0016 的物件可見相機模組／手機背面；F0062/F0077 可見手中直立／橫持手機。", "手機類別只在早期3張被偵測；沒有獨立 card producer 或持握判定，不能自動宣告 card claim 已被驗證為錯。"),
        3:("test5 F0001/F0016/F0032 支持桌面手機的視覺脈絡；F0062/F0077 可見手持手機，與既有人工 pickup 說明一致。", "後狀態手機漏檢、沒有 grip/support primitive，計算結果不足以獨立支持 PICKUP；F0016 不能作為已拿起的證據。"),
        4:("test7 F0001/F0016/F0031/F0046 的籃球仍在桌邊，手操作的是手機；F0062 的籃球變大伴隨相機接近，之後轉向而離開畫面。", "F0031 球漏檢使 ball local chain 中斷；未觀測到自動的 surface/contact state，不能靠消失或影像移動自動拒絕球 pickup。"),
        8:("test7 F0031/F0046 可見手抓握手機，支持既有人工作出的 physical-event-level 判斷。", "手機 F0031 轉為新 local ID，F0046 漏檢；generic object 無法僅靠現有連續性可靠綁定同一手機。"),
        10:("test5 F0062/F0077 可見手持手機，F0077 已是後狀態，不能同時充當 before／事件精確時間。", "計算後狀態沒有手機候選，因此不能以這次 independent evidence 支持原時間與完整狀態轉換。")
    }
    for h in humans["records"]:
        cid=h["call_id"]
        if cid not in comments:
            continue
        rec=h["human_record_unchanged"]
        comparisons.append({"call_id":cid,"existing_human_disposition":rec["disposition"],"source_human_sha256":h["submission_sha256"],"qualitative_visual_observation_by_report_author":comments[cid][0],"independent_computed_evidence_limit":comments[cid][1],"automatic_physical_decision":"NOT_ESTABLISHED","human_decision_modified":False})
    save("POST_COMPUTE_REVIEW.json",{"reviewed_utc":datetime.now(timezone.utc).isoformat(),"computed_receipt_sha256":sha(OUT/"COMPUTED_STATES_RECEIPT.json"),"human_source":str(humanpath.relative_to(ROOT)),"human_source_sha256":sha(humanpath),"comparisons":comparisons,"investigator_blind":False,"runtime_features_use_human_labels":False,"note":"Hashing human records for preservation is byte access, not semantic parsing or label input. The computed-file human_data_read=false and receipt runtime_never_reads_human_data=true refer only to semantic/feature consumption, not byte hashing. This clarification supersedes any literal no-byte-access reading."})
    # Evidence coverage and producer metadata: never substitute non-exact samples.
    coverage={}
    for name in ("test5__W05","test7__W05"):
        rows=[r for r in frames if r["window"]==name]
        video=name.split("__")[0]
        selected={r["source_frame_index"] for r in rows}
        low,high=(342,450) if video=="test5" else (372,480)
        ds_path=ROOT/f"outputs_v292/{video}/perception/yolo_detections.json"
        tracks_path=ROOT/f"outputs_v292/{video}/perception/tracks.json"
        sam_path=ROOT/f"outputs_v292/{video}/sam/sam_continuity_log.json"
        ds,tracks,sam=read(ds_path),read(tracks_path),read(sam_path)
        coverage[name]={"legacy_detection_file_sha256":sha(ds_path),"legacy_track_file_sha256":sha(tracks_path),"legacy_sam_file_sha256":sha(sam_path),"legacy_sam_checkpoint_sha256":sam.get("checkpoint_sha256"),"legacy_sam_config":sam.get("config"),"legacy_sam_step_frames":sam.get("step_frames"),"legacy_samples_in_window":sorted({d["frame_index"] for d in ds if low<=d["frame_index"]<high}),"exact_uniform8_intersection":sorted(selected & {d["frame_index"] for d in ds}),"intervening_legacy_phone_detections":[d for d in ds if low<=d["frame_index"]<high and d["frame_index"] not in selected and d["class_name"]=="cell phone"],"phone_track_fragments_in_window":[{"track_id":t["track_id"],"source_track_key":t.get("source_track_key"),"observations":[o for o in t["observations"] if low<=o["frame_index"]<high]} for t in tracks if t["detector_class"]=="cell phone" and any(low<=o["frame_index"]<high for o in t["observations"])],"used_intervening_frames_to_fill_exact_states":False,"propagated_new_sam":False,"identity_authority":"Current guard only; no upgrade from legacy tracks/masks"}
    save("EVIDENCE_COVERAGE.json",coverage)
    # CPU-only integrity checks on actual outputs, not a physical-event benchmark.
    a=ROOT/"WORKSPACE/Pass_T/Phase3_Observation_Capability_Audit_20261015"
    baseline={**read(a/"PRESERVATION_BASELINE.json")["source_files"],**read(a/"ARTIFACT_PRESERVATION_BASELINE.json")}
    changed=[n for n,h in baseline.items() if not (ROOT/n).is_file() or sha(ROOT/n)!=h]
    checks={
        "exactly_two_windows_16_unique_inputs":len(frames)==16 and len({r["window"] for r in frames})==2 and len({r["source_path"] for r in frames})==16,
        "all_16_png_hashes_match_frozen_manifest":all(sha(ROOT/r["source_path"])==r["recorded_source_png_sha256"]==r["verified_png_sha256"] for r in frames),
        "all_model_hashes_unchanged":all(sha(ROOT/n)==h for n,h in run["model_hashes"].items()),
        "preregistration_and_sealed_states_unchanged":sha(OUT/"PREREGISTRATION.json")==data["preregistration_sha256"] and sha(OUT/"COMPUTED_STATES.json")==receipt["computed_sha256"],
        "both_windows_sealed_before_comparison":datetime.fromisoformat(receipt["saved_utc"])<datetime.now(timezone.utc),
        "no_positive_state_without_contact_support":all(o["physical_state"]=="UNKNOWN" and o["grip_contact_confidence"] is None and o["support_boundary_confidence"] is None for r in frames for o in r["candidates"]),
        "no_missing_detection_converted_to_absence":all(r["missingness_meaning"]=="NO_DETECTION_NOT_ABSENCE" for r in frames),
        "all_candidate_persistent_identities_unassigned":all(o["persistent_entity"] is None for r in frames for o in r["candidates"]),
        "no_qwen_calls_or_graph_writes_or_video_decodes":run["qwen_calls"]==run["graph_writes"]==run["source_video_decodes"]==0,
        "all_522_historical_sources_and_references_unchanged":len(baseline)==522 and not changed,
    }
    assert all(checks.values()),checks
    save("CHECKPOINT_CHECKS.json",{"checks":checks,"pass_count":sum(checks.values()),"failure_count":sum(not x for x in checks.values()),"historical_files_checked":len(baseline),"changed":changed,"scope":"CPU artifact/provenance checks, not event accuracy or CV unit validation"})
    # Regenerate readable panels from sealed computations only (no inference).
    from PIL import Image,ImageDraw,ImageFont
    font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",18)
    small=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",15)
    for name in ("test5__W05","test7__W05"):
        sheet=Image.new("RGB",(1600,2160),"#111111")
        for i,r in enumerate(x for x in frames if x["window"]==name):
            tile=Image.new("RGB",(800,540),"#111111")
            im=Image.open(ROOT/r["source_path"]).convert("RGB")
            draw=ImageDraw.Draw(im)
            for o in r["candidates"]:
                color="lime" if o["class_name"]=="cell phone" else "orange"
                draw.rectangle(o["bbox"],outline=color,width=4)
                draw.text((o["bbox"][0],max(0,o["bbox"][1]-23)),f'{o["local_id"].split(":")[-1]} {o["class_name"]} {o["confidence"]:.2f}',font=font,fill=color,stroke_width=1,stroke_fill="black")
            for w in r["confident_wrists"]:
                x,y=w["xy"]
                draw.ellipse((x-6,y-6,x+6,y+6),fill="cyan")
                draw.text((x+8,y),f'W{w["keypoint_index"]}',font=font,fill="cyan",stroke_width=1,stroke_fill="black")
            tile.paste(im.resize((800,450)),(0,0))
            d=ImageDraw.Draw(tile)
            d.text((8,454),f'{r["supplied_alias"]} / {r["source_frame_id"]} / native PTS {r["native_source_pts_s"]:.6f}',font=font,fill="white")
            d.text((8,477),f'phone={int(not r["missing_phone_detection"])} ball={int(not r["missing_ball_detection"])} pose={len(r["pose_persons"])} wrist={len(r["confident_wrists"])} camera_fit={r["camera"]["reliable"]}',font=small,fill="white")
            d.text((8,497),'Physical state: UNKNOWN / local candidate IDs UNVERIFIED',font=font,fill="yellow")
            d.text((8,520),'Cyan = pose wrist prediction; includes false positives on background figurine',font=small,fill="white")
            sheet.paste(tile,((i%2)*800,(i//2)*540))
        sheet.save(OUT/f"{name}_annotated_readable.png")
    lines=["# Phase 3 v2 — Physical State Evidence Spike", "", "更新：2026-10-15。狀態：**PHASE3_SIGNAL_CHECKPOINT_BLOCKED**。", "", "## 結論", "", "已完成 Step 1 的 exact-frame YOLO11s、YOLO11n-pose、背景相對運動與既有 SAM／ByteTrack／Guard 覆蓋檢查。**目前不足以用獨立計算的物理狀態，同時支持正確手機 PICKUP 並排除錯誤籃球 PICKUP。** 沒有把 UNKNOWN 改成 NO_EVENT，也沒有把人工可見動作當成 runtime 觀察。", "", "這是 **development-set feasibility check, not a validated PICKUP detector.** Phase 3 全部實作尚未完成；依本次 prompt 第6節，停在第一個強制 checkpoint。", "", "## 實際執行與對齊", "", "只解碼既有的16張 PNG，沒有重解碼影片。16/16 SHA 與 frozen Uniform8 清單相符，保留原 alias、source index、native PTS；不使用近鄰取代、index/FPS 重算或插補。重用 current `perception.Detector.detect`，conf=.25、imgsz960；另以相同影像跑官方 YOLO11n-pose。模型無訓練、未新增框架。", "", "| 視窗 | 手機偵測影格 | 籃球偵測影格 | Pose輸出影格 | 高信心手腕輸出影格* | 背景fit通過/相鄰7組 | exact既有SAM影格 | Guard授權影格 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for n,s in run["summary"].items():
        lines.append(f'| {n} | {s["phone_frames"]}/8 | {s["ball_frames"]}/8 | {s["pose_frames"]}/8 | {s["wrist_frames"]}/8 | {s["reliable_camera_pairs"]}/7 | {s["exact_masks_frames"]}/8 | {s["guard_authorized_frames"]}/8 |')
    lines += ["", "*只計模型輸出，不是人工驗證的正確手腕。圖上多個 cyan 點其實落在微波爐上的玩偶；不可解讀為手的高覆蓋率。", "", "### 每一張 exact frame", "", "| 視窗 | alias | source frame | native PTS秒 | 手機conf | 球conf | 物理狀態 |", "|---|---|---:|---:|---|---|---|"]
    for r in frames:
        conf=lambda n: ", ".join(f'{d["confidence"]:.3f}' for d in r["detections"] if d["class_name"]==n) or "未偵測≠不存在"
        lines.append(f'| {r["window"]} | {r["supplied_alias"]} | {r["source_frame_index"]} | {r["native_source_pts_s"]:.9f} | {conf("cell phone")} | {conf("sports ball")} | UNKNOWN／無候選則無狀態 |')
    lines += ["", "完整 path、SHA、bbox、class、confidence、person detections、缺失、姿態、關聯與逐物件狀態見 [COMPUTED_STATES.json](COMPUTED_STATES.json)。", "", "## 物理訊號與失敗點", "", "- **手機後狀態漏檢：** test5 僅 F0001/F0016/F0032 偵測手機；可見手持的 F0062/F0077 反而沒有手機候選。test7 F0031 偵測到直立手機，F0046 仍可見手機但漏檢；F0031 因大幅外觀／方位變化成為新 tentative local ID。", "- **Pose 不等於手部／接觸：** 17點人身姿態無手指與抓握分類；第一人稱手臂截斷，輸出常落在前臂或背景玩偶。現有每個 phone 候選的最近輸出手腕距 bbox 均超過40px，未通過先註冊的近接門檻。沒有人為剔除模型點或補出手腕。", "- **相機校正只擬合2D背景：** LK forward/backward一致性 + RANSAC homography；test5 7/7、test7 6/7 達擬合數值門檻，並非經過外部驗證的物理相機解。test5 F0077 的球相對背景 residual 約19.64px，觸發 IMAGE_MOVING_PROXY；人工視覺脈絡仍見球留在桌面，顯示視差／平面差異可製造假移動。test7 F0016 球 residual 1.66px 只是投影近靜止，不能據此證明機械支撐。", "- **SAM與ByteTrack：** 既有5FPS樣本對 exact8 的交集 test5=1/8、test7=0/8；exact SAM只有 test5 F0001，紫色mask見原 contact sheet，身份未驗證。沒有近鄰mask移植、沒有新 SAM 推論。舊 track片段及 intervening detections 分開保存在 EVIDENCE_COVERAGE；未拿來填補 exact frame 的狀態。", "- **局部與持續身分：** 新候選以同類別、唯一IoU≥.30、間隔≤.65秒暫接；test5共2個 local IDs，test7共5個。只是未驗證 association，不能從同ID證明同一實體；沒有足夠證據判定真實 ID switch 次數。Guard final ledger 在這兩段皆無授權，沒有升格成 phone_01。", "- **ON_SURFACE / HELD 的獨立 primitive 缺口：** support boundary、grip/contact、surface separation 沒有可用的測量 producer，confidence 都是 null。先註冊正狀態需≥.8的相關支持、至少2個連續觀察，HELD還需 wrist≥.5且≤40px、相對位移≤6px；缺值即 UNKNOWN。因此18筆 phone/ball候選全UNKNOWN不是模型分類錯誤率，亦不是一個實際驗證過的全UNKNOWN偵測器；是明確暴露尚未實作／未取得的必要觀察。", "", "## 保存計算後才做的質性對照", "", "兩個視窗的 COMPUTED_STATES 及SHA receipt 已先寫入，再由獨立 reporting script 語意讀取人工審閱。調查者原已知DEV結果，不能宣稱研究者雙盲或獨立驗證；此流程只防止標註成為計算feature。runtime曾對人工檔案做保全hash，未解析其答案；詳見 POST_COMPUTE_REVIEW 的讀取範圍澄清。", "", "| Call | 既有人工結論（保留） | 報告作者的可見證據 | 獨立計算目前能否支持 |", "|---|---|---|---|"]
    for x in comparisons:
        lines.append(f'| {x["call_id"]:02d} | {x["existing_human_disposition"]} | {x["qualitative_visual_observation_by_report_author"]} | {x["independent_computed_evidence_limit"]} |')
    lines += ["", "上述視覺敘述是報告作者的質性觀察，不是新增人類GT、模型輸出、或可送入 Decision 的感測值。原有5筆 strict-invalid 及人工決定完全保留，未重新計分。Call08的 object 類型仍需明確 grounding，不能借人工答案補上。", "", "## 規則、順序與資源", "", f'- 規則SHA：`{run["preregistration_sha256"]}`；revision=0，沒有門檻差異或調參。', f'- 計算結果SHA：`{receipt["computed_sha256"]}`；保存UTC：`{receipt["saved_utc"]}`。', f'- YOLO11s SHA：`{run["model_hashes"][".models/yolo11s.pt"]}`。', f'- YOLO11n-pose SHA：`{run["model_hashes"][".models/yolo11n-pose.pt"]}`；官方下載6,255,593 bytes，低於100MB，未下載其他權重。', f'- 實測程式計時 {run["elapsed_s"]:.2f} 秒；Torch峰值allocated {run["torch_peak_allocated_bytes"]/1048576:.2f} MiB、reserved {run["torch_peak_reserved_bytes"]/1048576:.2f} MiB。這是該process allocator數值，不是整張GPU／所有process的峰值。', '- Ultralytics8.4.158、Torch2.10.0+cu128、OpenCV4.14.0.94；GPU用於這16張YOLO／pose，Qwen呼叫0，Graph寫入0，原影片解碼0。', '- CPU artifact checks：10/10通過；16張PNG及兩權重hash相符，522個既有source/reference hashes未變。這些是完整性檢查，不是CV分類驗證或正式event benchmark。', '- 初次啟動因Ultralytics預設寫入AppData而失敗；已在import前重用專案configure_ultralytics，正式一次完整跑完16張。未生成任何Qwen輸出。', "", "## 實作與下一步（最多三項）", "", "目前這些觀察可供候選探索、缺失診斷與不確定性，**不能可靠構造 SUPPORTED 或因球仍被支撐而 REJECTED 的物理判斷**。未先做最終 validator／Decision／V3 prompt。", "", "1. **小範圍手／物接觸可行性測試（成本低至中、直接性最高）**：經使用者批准具體輕量hand模型後，只在同16張測手指／抓握可見性；可搭現有SAM2.1候選mask，但先驗證hand-object segmentation與support分離是否真的有用，不保證能產生接觸。", "2. **同視窗較密的現成PNG觀察（成本中）**：重用已存在影格改善phone後狀態追蹤，配合桌面局部平面／視差診斷；這需要另外核准擴大本次exact8分析範圍，不能把多觀察的收益說成原Uniform8成功。", "3. **保持Physical State為UNKNOWN，先用分離的人工物理證據層做研究診斷（成本低但有人工作量）**：不可冒稱自動Decision已可用，也不可讓人工狀態變runtime feature。", "", "**停在 PHASE3_SIGNAL_CHECKPOINT_BLOCKED。等待使用者決定上述缺口的處理方向；沒有啟動下一階段、沒有Qwen、沒有改GT／歷史報告／V297／Graph、沒有commit或push。**", "", "## 入口與可視證據", "", "- [test5：8張逐格偵測／姿態／狀態](test5__W05_annotated_readable.png)", "- [test7：8張逐格偵測／姿態／狀態](test7__W05_annotated_readable.png)", "- [test5含exact legacy SAM overlay版本](test5__W05_contact_sheet.png)", "- [已封存計算資料](COMPUTED_STATES.json)、[原始run receipt](RUN_RECEIPT.json)、[CPU完整性檢查](CHECKPOINT_CHECKS.json)、[既有採樣與producer來源](EVIDENCE_COVERAGE.json)", "- 新增執行入口：scripts/phase3_signal_spike.py；僅此spike與report工具，未修改既有src pipeline。所有檔案hash見DELIVERABLE_HASHES.json。"]
    report=OUT/"PHASE3_SIGNAL_CHECKPOINT_REPORT.md"
    report.write_text("\n".join(lines)+"\n",encoding="utf-8")
    hashes={str(p.relative_to(ROOT)):sha(p) for p in OUT.iterdir() if p.is_file() and p.name!="DELIVERABLE_HASHES.json"}
    hashes["scripts/phase3_signal_spike.py"]=sha(ROOT/"scripts/phase3_signal_spike.py")
    save("DELIVERABLE_HASHES.json",hashes)
    print(json.dumps({"status":"PHASE3_SIGNAL_CHECKPOINT_BLOCKED","checks":checks,"report":str(report),"sha256":sha(report)},ensure_ascii=False))


if __name__=="__main__":
    main()
