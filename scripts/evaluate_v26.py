"""Post-freeze V2.6 review, comparison, and human-readable visualizations."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs_v26"
BASE = ROOT / "outputs_v25_rerun"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_freeze():
    manifest = read(OUT / "prediction_manifest.json")
    assert manifest["stage"] == "B_POSTFREEZE_PROVENANCE_REPAIR"
    assert manifest["postfreeze_repair_after_review"] and not manifest["gt_labels_used_in_repair"]
    assert manifest["categorical_reid_decisions_identical_to_initial_blind"]
    initial = read(OUT / "initial_blind/prediction_manifest.json")
    assert initial["stage"] == "A_BLIND_INFERENCE_COMPLETE" and not initial["gt_read_before_freeze"]
    assert sha(OUT / "initial_blind/prediction_manifest.json") == manifest["initial_blind_manifest_sha256"]
    assert sha(OUT / "baseline_manifest.json") == manifest["baseline_manifest_sha256"]
    for name, expected in manifest["inference_code_sha256"].items():
        assert sha(ROOT / name) == expected, name
    for task, files in manifest["videos"].items():
        for name, expected in files.items():
            assert sha(OUT / task / name) == expected, f"{task}/{name}"
    baseline = read(OUT / "baseline_manifest.json")
    assert sha(BASE / "prediction_manifest.json") == baseline["v25_prediction_manifest_sha256"]
    for name, expected in baseline["video_sha256"].items():
        assert sha(ROOT / name) == expected, name
    return sha(OUT / "prediction_manifest.json")


REVIEWED = {
    "test4": {"candidate_018": "TARGET"},
    "test7": {"candidate_004": "DISTRACTOR", "candidate_014": "TARGET", "candidate_015": "TARGET"},
    "test8": {"candidate_009": "TARGET", "candidate_014": "TARGET",
              "candidate_018": "DISTRACTOR", "candidate_020": "DISTRACTOR"},
}


def first_v25_decisions(audit):
    result = {}
    for attempt in audit["attempts"]:
        for row in attempt.get("candidate_decisions", []):
            result.setdefault(row["candidate_entity_id"], row)
            if row["decision"] == "MATCH": result[row["candidate_entity_id"]] = row
    return result


def first_v26_decisions(audit):
    result = {}
    for attempt in audit["attempts"]:
        for row in attempt.get("candidate_decisions", []):
            result.setdefault(row["candidate_entity_id"], row)
            if row["decision"] in ("CONFIRMED_MATCH", "PROVISIONAL_MATCH"):
                result[row["candidate_entity_id"]] = row
    return result


def decision_at(task, candidate_id, frame):
    audit = read(OUT / task / "reid_audit.json")
    attempt = next((a for a in audit["attempts"] if a["frame_index"] == frame), None)
    if attempt is None:
        return None
    return next((row for row in attempt.get("candidate_decisions", [])
                 if row["candidate_entity_id"] == candidate_id), None)


def comparison(task):
    old = read(BASE / task / "reid_audit.json")
    new = read(OUT / task / "reid_audit.json")
    groups = read(OUT / task / "candidate_grouping_audit.json")["candidates"]
    a = first_v25_decisions(old); b = first_v26_decisions(new)
    rows = []
    for group in groups:
        cid = group["candidate_id"]
        old_row, new_row = a.get(cid), b.get(cid)
        row = {"candidate_id": cid, "first_frame": group["observations"][0]["frame_index"],
               "source_track_ids": group["source_track_ids"],
               "v25_decision": old_row["decision"] if old_row else "NOT_EVALUATED",
               "v26_decision": new_row["decision"] if new_row else "NOT_EVALUATED",
               "v26_similarity": new_row["appearance"]["max_similarity"] if new_row else None,
               "v26_second_similarity": new_row["second_candidate_similarity"] if new_row else None,
               "v26_margin": new_row["best_vs_second_margin"] if new_row else None,
               "reviewed_identity": REVIEWED.get(task, {}).get(cid, "UNKNOWN")}
        rows.append(row)
    path = OUT / task / "v25_vs_v26_candidates.json"
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with (OUT / task / "v25_vs_v26_candidates.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return rows


def render_reid_timeline(task, rows, helper):
    audit = read(OUT / task / "reid_audit.json")
    old = read(BASE / task / "reid_audit.json")
    groups = read(OUT / task / "candidate_grouping_audit.json")["candidates"]
    interesting = {"test7": {"candidate_004", "candidate_014", "candidate_015"},
                   "test8": {"candidate_009", "candidate_014", "candidate_018", "candidate_020"}}.get(task, set())
    fig, ax = plt.subplots(figsize=(20, max(9, len(groups)*.43)), layout="constrained")
    position = {g["candidate_id"]: i for i,g in enumerate(groups)}
    for g in groups:
        cid = g["candidate_id"]; i = position[cid]
        fs = [o["frame_index"] for o in g["observations"]]
        ax.plot([min(fs), max(fs)], [i,i], color="#bbbbbb", linewidth=2)
        if cid in interesting:
            ax.axhspan(i-.4,i+.4,color="#f0f5ff",zorder=-2)
    for attempt in audit["attempts"]:
        f = attempt["frame_index"]
        for d in attempt.get("candidate_decisions", []):
            cid = d["candidate_entity_id"]
            if cid not in position: continue
            dec = d["decision"]
            color = {"CONFIRMED_MATCH":"#168438", "PROVISIONAL_MATCH":"#c66a00",
                     "REJECTED":"#b82626", "AMBIGUOUS":"#606c80"}.get(dec,"gray")
            ax.scatter(f, position[cid], s=20 if dec=="AMBIGUOUS" else 65, color=color,
                       marker="D" if dec in ("CONFIRMED_MATCH","PROVISIONAL_MATCH") else "o", alpha=.8)
    for row in rows:
        cid = row["candidate_id"]
        if cid not in interesting: continue
        f = row["first_frame"]
        sim = row["v26_similarity"]
        second = row["v26_second_similarity"]
        margin = row["v26_margin"]
        label = (f"{cid} track{row['source_track_ids']} | sim {sim:.3f} | second "
                 f"{second:.3f} | margin {margin:.3f}" if sim is not None and second is not None and margin is not None
                 else f"{cid} track{row['source_track_ids']} | sim {sim:.3f} | second/margin N/A" if sim is not None
                 else f"{cid} track{row['source_track_ids']} | similarity N/A")
        label += f" | V2.5 {row['v25_decision']} -> V2.6 {row['v26_decision']} | review {row['reviewed_identity']}"
        ax.annotate(label,(f,position[cid]),xytext=(8,3),textcoords="offset points",fontsize=8)
    baseline_timeline = read(BASE / task / "identity_timeline.json")["phone_timeline"]
    unobserved = [x["frame_index"] for x in baseline_timeline if x["state"]=="UNOBSERVED"]
    if unobserved: ax.axvline(min(unobserved),color="#2159b0",linestyle="--",label="phone_01 UNOBSERVED")
    for a in old["attempts"]:
        if a["decision"]=="MATCH": ax.axvline(a["frame_index"],color="#ad1f1f",linestyle=":",label="V2.5 MATCH")
    if audit["confirmed_match"]:
        ax.axvline(audit["confirmed_match"]["frame_index"],color="#168438",label="V2.6 CONFIRMED + SAM")
    ax.set_ylim(-1,len(groups)); ax.set_yticks(range(len(groups)),[g["candidate_id"] for g in groups],fontsize=7)
    ax.set_xlim(0, max(x["frame_index"] for x in baseline_timeline)+120)
    ax.set_xlabel("Frame / time progression; each dot is one scored candidate event")
    ax.set_ylabel("Candidate ID")
    ax.set_title(f"{task}: V2.6 continued Re-ID audit | green confirmed, orange provisional, gray ambiguous")
    ax.grid(axis="x",alpha=.2); ax.legend(loc="upper left")
    fig.savefig(OUT / task / "reid_timeline.png",dpi=170)
    plt.close(fig)


def render_contact(task, rows, helper):
    groups = read(OUT / task / "candidate_grouping_audit.json")["candidates"]
    old = read(BASE / task / "reid_audit.json")
    registry = read(BASE / task / "entity_registry.json")
    bank = next((a.get("bank_prototypes") for a in reversed(old["attempts"]) if a.get("bank_prototypes")),None)
    prototypes = bank["prototypes"] if bank else []
    target_sam = read(BASE / task / "sam/sam_continuity_log.json")
    masks = {key:value for segment in target_sam["segments"] for key,value in segment["masks_rle"].items()}
    trusted = next((e for e in registry["entities"] if e["entity_id"]=="phone_01"),None)
    selected = helper.important_candidates(task,groups)
    cols=4;tw=410;th=365;sheet=np.full(((1+(len(selected)+cols-1)//cols)*th,cols*tw,3),249,np.uint8)
    cv2.putText(sheet,"PHONE_01 TRUSTED APPEARANCE BANK",(12,28),cv2.FONT_HERSHEY_SIMPLEX,.75,(0,0,0),2)
    for i,p in enumerate(prototypes[:4]):
        f=p["frame_index"]
        ob=next((o for o in trusted["observation_history"] if o["frame_index"]==f and o.get("source_object_id")==p["source"]),None)
        if ob is None:continue
        mask=next((v for k,v in masks.items() if k.startswith(f"{f}:")),None)
        crop=helper.box_crop(task,f,ob["bbox"],mask)
        x=i*tw;sheet[55:290,x+12:x+tw-12]=cv2.resize(crop,(tw-24,235))
        cv2.putText(sheet,f"f{f} {p['source']} YOLO {ob['detector_confidence']:.2f}",(x+12,315),cv2.FONT_HERSHEY_SIMPLEX,.53,(0,0,0),1)
        cv2.putText(sheet,f"SAM supported: {p['mask_used']}",(x+12,341),cv2.FONT_HERSHEY_SIMPLEX,.52,(0,0,0),1)
    rowmap={r["candidate_id"]:r for r in rows}
    for n,(g,f) in enumerate(selected):
        o=helper.candidate_observation(g,f);cid=g["candidate_id"];r=rowmap[cid]
        specific=decision_at(task,cid,f)
        crop=helper.box_crop(task,o["frame_index"],o["bbox"])
        x=(n%cols)*tw;y=(1+n//cols)*th
        sheet[y+35:y+270,x+12:x+tw-12]=cv2.resize(crop,(tw-24,235))
        sim="N/A" if specific is None else f"{specific['appearance']['max_similarity']:.3f}"
        margin="N/A" if specific is None or specific["best_vs_second_margin"] is None else f"{specific['best_vs_second_margin']:.3f}"
        current_decision=specific["decision"] if specific else "NOT_EVALUATED"
        cv2.putText(sheet,f"{cid} f{o['frame_index']} track{o['source_track_id']}",(x+12,y+24),cv2.FONT_HERSHEY_SIMPLEX,.54,(0,0,0),1)
        cv2.putText(sheet,f"sim {sim} margin {margin}",(x+12,y+293),cv2.FONT_HERSHEY_SIMPLEX,.52,(0,0,0),1)
        cv2.putText(sheet,f"V2.5 {r['v25_decision']} | V2.6 {current_decision}",(x+12,y+319),cv2.FONT_HERSHEY_SIMPLEX,.48,(0,0,0),1)
        cv2.putText(sheet,f"POST-FREEZE REVIEW: {r['reviewed_identity']}",(x+12,y+343),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,0),1)
    cv2.imwrite(str(OUT / task / "reid_contact_sheet.png"),sheet)


def render_explainer(task, rows, helper):
    if task not in ("test7","test8"):return
    groups = {g["candidate_id"]:g for g in read(OUT / task / "candidate_grouping_audit.json")["candidates"]}
    registry = read(BASE / task / "entity_registry.json")
    q=next(e for e in registry["entities"] if e["entity_id"]=="phone_01")
    bank=next(a["bank_prototypes"] for a in read(BASE/task/"reid_audit.json")["attempts"] if a.get("bank_prototypes"))
    p=bank["prototypes"][0];f=p["frame_index"]
    o=next(o for o in q["observation_history"] if o["frame_index"]==f and o.get("source_object_id")==p["source"])
    choices=[("ORIGINAL PHONE_01",helper.box_crop(task,f,o["bbox"]),f"Trusted f{f} {p['source']}")]
    wanted=[("candidate_004",636),("candidate_014",720),("candidate_015",888)] if task=="test7" else \
           [("candidate_009",804),("candidate_014",888),("candidate_018",888),("candidate_020",888)]
    rowmap={r["candidate_id"]:r for r in rows}
    for cid,fr in wanted:
        obs=helper.candidate_observation(groups[cid],fr);r=rowmap[cid]
        specific=decision_at(task,cid,fr)
        sim="N/A" if specific is None else f"{specific['appearance']['max_similarity']:.3f}"
        current_decision=specific["decision"] if specific else "NOT_EVALUATED"
        choices.append((cid,helper.box_crop(task,obs["frame_index"],obs["bbox"]),
                        f"f{fr} | sim {sim} | V2.5 {r['v25_decision']} -> V2.6 {current_decision}\nPOST-FREEZE: {r['reviewed_identity']}"))
    fig,axes=plt.subplots(1,len(choices),figsize=(5*len(choices),6),layout="constrained")
    for ax,(title,img,caption) in zip(axes,choices):
        ax.imshow(cv2.cvtColor(img,cv2.COLOR_BGR2RGB));ax.set_title(title,fontsize=16,fontweight="bold")
        ax.set_xlabel(caption,fontsize=11);ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle("test7: false merge prevented; later target audited" if task=="test7" else
                 "test8: correct target remains confirmed; later phones audited",fontsize=19,fontweight="bold")
    fig.savefig(OUT/task/("test7_identity_failure_explainer.png" if task=="test7" else "test8_correct_reid_explainer.png"),dpi=170)
    plt.close(fig)


def main():
    frozen_hash=verify_freeze()
    spec=importlib.util.spec_from_file_location("v26_baseline_render",ROOT/"scripts/build_v26_baseline.py")
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    videos={};all_rows=[]
    for i in range(3,10):
        task=f"test{i}";rows=comparison(task);all_rows.extend({"task":task,**r} for r in rows)
        helper.identity_timeline(task,OUT/task)
        render_reid_timeline(task,rows,helper)
        render_contact(task,rows,helper)
        render_explainer(task,rows,helper)
        audit=read(OUT/task/"reid_audit.json")
        v25=read(BASE/task/"reid_audit.json")
        videos[task]={"v25_match":v25["match_candidate_id"],"v26_confirmed":audit["confirmed_match"],
            "v26_provisional":audit["provisional_candidate_ids"],
            "audit_event_frames":len(audit["attempts"]),
            "candidate_hypotheses":len(rows),
            "reviewed_false_confirmed_merges":sum(r["v26_decision"]=="CONFIRMED_MATCH" and r["reviewed_identity"]=="DISTRACTOR" for r in rows)}
        notable=[r for r in rows if r["reviewed_identity"]!="UNKNOWN"]
        (OUT/task/"review.md").write_text(f"# {task} post-freeze review\n\n"+
            "| Candidate | Frame | V2.5 | V2.6 | Similarity | Reviewed identity |\n|---|---:|---|---|---:|---|\n"+
            "\n".join(f"| {r['candidate_id']} | {r['first_frame']} | {r['v25_decision']} | {r['v26_decision']} | "
            f"{r['v26_similarity'] if r['v26_similarity'] is not None else 'N/A'} | {r['reviewed_identity']} |" for r in notable)+"\n",encoding="utf-8")
    confirmed=[r for r in all_rows if r["v26_decision"]=="CONFIRMED_MATCH"]
    provisional=[r for r in all_rows if r["v26_decision"]=="PROVISIONAL_MATCH"]
    later_target=[r for r in all_rows if r["reviewed_identity"]=="TARGET" and
                  r["v25_decision"]=="NOT_EVALUATED" and r["v26_similarity"] is not None]
    aggregate={"confirmed_matches":len(confirmed),"provisional_matches":len(provisional),
        "true_confirmed_matches":sum(r["reviewed_identity"]=="TARGET" for r in confirmed),
        "false_confirmed_matches":sum(r["reviewed_identity"]=="DISTRACTOR" for r in confirmed),
        "reviewed_false_physical_merges":sum(v["reviewed_false_confirmed_merges"] for v in videos.values()),
        "later_reviewed_target_candidates_evaluated_after_v25_first_match":len(later_target),
        "test8_positive_match_preserved":videos["test8"]["v26_confirmed"] is not None and
             videos["test8"]["v26_confirmed"]["candidate_id"]=="candidate_009"}
    summary={"prediction_manifest_sha256":frozen_hash,"videos":videos,"aggregate":aggregate,
             "review_scope":"sparse post-freeze physical identity labels; UNKNOWN is not a negative label"}
    (OUT/"fusion_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    (OUT/"v25_vs_v26_summary.json").write_text(json.dumps({"videos":videos,"aggregate":aggregate,
        "reviewed_candidate_rows":[r for r in all_rows if r["reviewed_identity"]!="UNKNOWN"]},indent=2),encoding="utf-8")
    print(json.dumps(aggregate,indent=2))


if __name__=="__main__":
    main()
