"""Bounded perception -> existing spatial memory. No GT or new event inference."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"artifacts/pass_i/runtime/vendor"),str(ROOT/"outputs/current_development/video_event_experiment/.deps")]
import cv2
import numpy as np
from memory_graph.integration.adapters import read,sha
from memory_graph.integration.regions import scope
from memory_graph.integration.target_surface import integrate,scoped_baseline,prompt
from memory_graph.integration.pipeline import search
from memory_graph.scene_graph.models import TemporalMemory
from memory_graph.integration.perception_runtime import save


def choose_frames(video,memory,count=2):
    """Generic gap-based selection from metadata, never annotation decisions."""
    duration=video["source_duration_s"]
    obs=memory.metadata["observations"]
    cv={f for o in obs if o["source"]=="CV" and o["object_category"]=="phone" for f in o["source_frame_indices"]}
    vlm={f for o in obs if o["source"]=="VLM" and o["object_category"]=="phone" for f in o["source_frame_indices"]}
    region_frames={r["source_frame_index"] for r in memory.metadata["scene_regions"]}
    early=lambda f:video["frame_timeline"][f]["source_time_s"]<.6*duration
    pools=[sorted(f for f in vlm-cv if early(f)),sorted(f for f in cv-region_frames if early(f)),sorted(f for f in cv if not early(f))]
    selected=[]
    for pool in pools:
        pool=[f for f in pool if f not in selected]
        if pool:selected.append(pool[len(pool)//2])
        if len(selected)==count:break
    for f in sorted(cv|vlm):
        if len(selected)>=count:break
        if f not in selected:selected.append(f)
    if not selected:selected=[video["frame_count"]//2]
    return sorted(selected)


def prepare(output,args):
    canvas=[1008,560] if args.coordinate_mode=="canvas_pixels" else None
    bundle=read(ROOT/args.bundle) if args.bundle else None
    manifest_path=ROOT/(bundle["source_manifest"] if bundle else "tools/findmind-gt-annotator/manifest.json")
    manifest=read(manifest_path)
    graphs=bundle["phase5_graphs"] if bundle else {v["video_id"]:f"artifacts/phase5/demo/{v['video_id']}/memory_graph.json" for v in manifest["videos"]}
    # User-suggested inspection indices affect selection only, not answers.
    examples={} if bundle else {"test1":[240,360],"test2":[85,102,282],"test8":[300,372]}
    protected={str(manifest_path):sha(manifest_path)}
    for directory in ("artifacts/phase4","artifacts/phase5","artifacts/vlmtest/gt_consolidation_v1"):
        for path in (ROOT/directory).rglob("*"):
            if path.is_file():protected[str(path.resolve())]=sha(path)
    # Upstream raw prediction / image / identity hashes from Phase 4 receipt.
    receipt=ROOT/"artifacts/phase4/demo/run_receipt.json"
    if not bundle and receipt.exists():
        for path,h in read(receipt)["checked_input_hashes"].items():
            if sha(path)!=h:raise ValueError("HISTORICAL_INPUT_HASH_MISMATCH:"+path)
            protected[path]=h
    output.mkdir(parents=True,exist_ok=False)
    frames=[];selected={};videos={v["video_id"]:v for v in manifest["videos"] if v["video_id"] in graphs}
    for vid,video in videos.items():
        graph=ROOT/graphs[vid];protected[str(graph)]=sha(graph)
        memory=TemporalMemory.model_validate(read(graph))
        ids=examples.get(vid) or choose_frames(video,memory,3 if not bundle and vid in {"test5","test9"} else 2)
        selected[vid]=ids
        media=ROOT/video.get("source_path",video["original_filename"])
        if sha(media)!=video["source_sha256"]:raise ValueError("SOURCE_VIDEO_HASH_MISMATCH")
        protected[str(media)]=video["source_sha256"]
        cap=cv2.VideoCapture(str(media));idx=0
        try:
            while idx<=max(ids):
                ok,image=cap.read()
                if not ok:raise RuntimeError("SOURCE_DECODE_FAILED")
                if idx in ids:
                    if image.shape[:2]!=(video["height"],video["width"]):raise ValueError("SOURCE_DIMENSION_MISMATCH")
                    identifier=__import__('hashlib').sha256((video["source_sha256"]+":"+str(idx)).encode()).hexdigest()[:16]
                    path=output/"frames"/(identifier+".png");path.parent.mkdir(exist_ok=True)
                    cv2.imwrite(str(path),image)
                    frames.append(dict(**scope(video,idx),frame_id=identifier,path=str(path.relative_to(ROOT)),sha256=sha(path),
                        model_canvas=canvas,
                        width=video["width"],height=video["height"],selection_reason="INSPECTION_EXAMPLE" if vid in examples else "METADATA_COVERAGE_GAP",
                        decoded_pixel_sha256=__import__('hashlib').sha256(image.tobytes()).hexdigest()))
                idx+=1
        finally:cap.release()
    reference=None
    if args.reference_image:
        path=(ROOT/args.reference_image).resolve();reference=dict(path=str(path),sha256=sha(path),persistent_identity_authorized=False)
    save(output/"manifest.json",dict(frames=frames,videos=videos,graphs=graphs,query=args.target_query,reference=reference,
        selection=selected,protected_hashes=protected,prompt=prompt(args.target_query,canvas),model_canvas=canvas,
        prompt_sha256=__import__('hashlib').sha256(prompt(args.target_query,canvas).encode()).hexdigest(),
        maximum_localization_calls=len(frames),scope="MATCHED_SELECTED_FRAMES_NOT_FULL_VIDEO_PERFORMANCE"))
    print(json.dumps(dict(stage="PREPARED",frames=len(frames),selection=selected),ensure_ascii=False),flush=True)


def draw(frame,targets,regions,locations,path):
    image=cv2.imread(str(ROOT/frame["path"]))
    overlay=image.copy()
    from memory_graph.v22.sam_tracking import decode_mask
    for r in regions:
        if r.get("pixel_mask_rle"):
            mask=decode_mask(r["pixel_mask_rle"]).astype(bool);overlay[mask]=(0,180,240)
        cv2.polylines(overlay,[np.rint(r["polygon"]).astype(np.int32)],True,(0,230,255),3)
    image=cv2.addWeighted(image,.7,overlay,.3,0)
    for o in targets:
        box=np.rint(o["bbox"]).astype(int)
        color=(50,255,80) if o["target_kind"]=="smartphone" else (80,100,255)
        cv2.rectangle(image,tuple(box[:2]),tuple(box[2:]),color,2)
        cv2.putText(image,o["target_kind"]+" / "+o["state_claim"],(box[0],max(25,box[1]-5)),cv2.FONT_HERSHEY_SIMPLEX,.6,color,2)
    image=cv2.resize(image,(960,540))
    panel=np.zeros((125,960,3),np.uint8)
    text=[f"{frame['video_id']} f{frame['source_frame_index']} t={frame['source_time_s']:.3f}s",
          "Identity: unresolved for NEW boxes | support: UNVERIFIED / CANDIDATE",
          "Surfaces: "+", ".join(r["region_label"] for r in regions),
          "Relations: "+", ".join(sorted({r["spatial_relation"] for r in locations if r["grounding_status"]!="UNKNOWN"})),
          "Yellow: model top-face polygon / SAM boundary; overlap is not contact."]
    for i,line in enumerate(text):cv2.putText(panel,line[:120],(8,20+i*23),cv2.FONT_HERSHEY_SIMPLEX,.48,(255,255,255),1)
    cv2.imwrite(str(path),np.concatenate([image,panel]))


def finish(output,manifest):
    if (output/"run_receipt.json").exists():raise FileExistsError("FINAL_RESULT_EXISTS")
    summaries={};frame_stats=[]
    for vid,video in manifest["videos"].items():
        frames=[f for f in manifest["frames"] if f["video_id"]==vid]
        base=TemporalMemory.model_validate(read(ROOT/manifest["graphs"][vid]))
        baseline=scoped_baseline(base,{f["source_frame_index"] for f in frames})
        payload={}
        for f in frames:
            directory=output/"perception"/f["frame_id"]
            from memory_graph.integration.target_surface import parse
            raw=(directory/"raw.txt").read_bytes().decode("utf8")
            checked,_=parse(raw,manifest.get("model_canvas"))
            if checked!=read(directory/"parsed.json"):raise ValueError("PARSED_OUTPUT_NOT_DERIVED_FROM_RAW")
            if read(directory/"input.json")["frames"]!=[f]:raise ValueError("MODEL_INPUT_FRAME_MISMATCH")
            refinements=read(directory/"refinements.json")
            for refinement in refinements.values():
                if refinement.get("accepted") and sha(ROOT/refinement["mask_ref"]["path"])!=refinement["mask_ref"]["sha256"]:
                    raise ValueError("MASK_FILE_HASH_MISMATCH")
            payload[f["source_frame_index"]]=dict(parsed=read(directory/"parsed.json"),raw_ref=str(directory/"raw.txt"),
                target_query=manifest["query"],refinements=refinements)
        memory=integrate(base,video,frames,payload)
        assert memory.events==base.events and memory.transitions==base.transitions
        queries={q:search(memory,q) for q in ["Where is my phone?","cup"]}
        before=search(baseline,"Where is my phone?")
        target=output/vid;target.mkdir(exist_ok=True)
        save(target/"memory_graph.json",memory.model_dump(mode="json"))
        restored=TemporalMemory.model_validate(read(target/"memory_graph.json"))
        assert all(search(restored,q)==v for q,v in queries.items())
        save(target/"search_results.json",queries);save(target/"phase5_matched_search.json",before)
        for field in ("target_localizations","new_surface_regions","location_observations","vlm_cv_associations","localization_audit"):
            save(target/(field+".json"),memory.metadata[field])
        localizations=memory.metadata["target_localizations"];regions=memory.metadata["new_surface_regions"]
        for f in frames:
            idx=f["source_frame_index"]
            targets=[o for o in localizations if o["source_frame_indices"]==[idx]]
            rs=[r for r in regions if r["source_frame_index"]==idx]
            ls=[r for r in memory.metadata["location_observations"] if r["source_frame_index"]==idx and r["object_category"]=="phone"]
            old=[o for o in baseline.metadata["observations"] if o["source"]=="CV" and o["object_category"]=="phone" and o["source_frame_indices"]==[idx]]
            old_rel=[r for r in baseline.metadata["location_observations"] if r["source_frame_index"]==idx and r["object_category"]=="phone" and r["grounding_status"]=="CANDIDATE"]
            sheet=target/(f"f{idx:06d}_evidence.jpg");draw(f,targets,rs,ls,sheet)
            frame_stats.append(dict(video_id=vid,source_frame_index=idx,source_time_s=f["source_time_s"],
                baseline_phone_boxes=len(old),new_smartphone_boxes=sum(o["target_kind"]=="smartphone" for o in targets),
                other_kind_counts=dict(Counter(o["target_kind"] for o in targets if o["target_kind"]!="smartphone")),
                new_surface_proposals=len(rs),baseline_phone_candidates=len(old_rel),
                phase6_phone_candidates=sum(r["grounding_status"]=="CANDIDATE" for r in ls),
                evidence_image=str(sheet.relative_to(ROOT)),visual_review_status="NOT_YET_REVIEWED"))
        tiles=[cv2.resize(cv2.imread(str(target/f"f{f['source_frame_index']:06d}_evidence.jpg")),(640,443)) for f in frames]
        while len(tiles)%2:tiles.append(np.zeros((443,640,3),np.uint8))
        sheet=np.concatenate([np.concatenate(tiles[i:i+2],axis=1) for i in range(0,len(tiles),2)])
        cv2.imwrite(str(target/"evidence_sheet.jpg"),sheet)
        associations=memory.metadata["vlm_cv_associations"]
        historical={o["observation_id"] for o in baseline.metadata["observations"] if o["source"]=="VLM"}
        summaries[vid]=dict(frames=len(frames),target_kinds=dict(Counter(o["target_kind"] for o in localizations)),
            new_surface_regions=len(regions),new_sam_surface_masks=sum(bool(r.get("mask_ref")) for r in regions),
            baseline_search_status=before["status"],baseline_phone_candidates=len(before["candidates"]),
            phase6_search_status=queries["Where is my phone?"]["status"],phase6_phone_candidates=len(queries["Where is my phone?"]["candidates"]),
            new_surface_phone_candidates=sum(c["region_id"].startswith("surface:") for c in queries["Where is my phone?"]["candidates"]),
            new_local_claims_resolved=sum(a["status"]=="RESOLVED_LOCAL_OBSERVATION" and a["vlm_observation_id"] not in historical for a in associations),
            historical_vlm_resolved=sum(a["status"]=="RESOLVED_LOCAL_OBSERVATION" and a["vlm_observation_id"] in historical for a in associations),
            authorized_new_localizations=sum(bool(o["authorized_entity_id"]) for o in localizations),
            existing_authorized_candidate_locations=sum(bool(c["persistent_entity_id"]) for c in queries["Where is my phone?"]["candidates"]),
            verified_locations=len(memory.metadata["trusted_location_history"]),reload_query_equal=True)
    changed=[path for path,h in manifest["protected_hashes"].items() if sha(path)!=h]
    if changed:raise RuntimeError("HISTORICAL_INPUT_CHANGED:"+str(changed))
    save(output/"frame_comparison.json",frame_stats)
    calls=[read(output/"perception"/f["frame_id"]/"generation.json") for f in manifest["frames"]]
    save(output/"run_receipt.json",dict(summary=summaries,localization_generations=len(calls),
        protected_files=len(manifest["protected_hashes"]),changed_inputs=changed,gt_used=False,production_memory_written=False,
        peak_qwen_allocated_bytes=max(c.get("resources",{}).get("gpu_peak_allocated_gib",0)*2**30 for c in calls),
        total_qwen_generation_seconds=sum(c.get("elapsed_s",0) for c in calls),
        raw_output_hashes={f["frame_id"]:sha(output/"perception"/f["frame_id"]/"raw.txt") for f in manifest["frames"]},
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),*sorted((ROOT/"src/memory_graph/integration").glob("*.py"))]},
        scope="SAME_SELECTED_FRAMES_ONLY",historical_event_decisions_unchanged=True))
    print(json.dumps(summaries,ensure_ascii=False),flush=True)


def render_comparison(output,manifest):
    """Matched-frame baseline visualization, without any GT or manual decisions."""
    graphs={vid:TemporalMemory.model_validate(read(ROOT/path)) for vid,path in manifest["graphs"].items()}
    for f in manifest["frames"]:
        image=cv2.imread(str(ROOT/f["path"]));base=graphs[f["video_id"]]
        idx=f["source_frame_index"]
        for region in base.metadata["scene_regions"]:
            if region["source_frame_index"]==idx:
                cv2.polylines(image,[np.rint(region["polygon"]).astype(np.int32)],True,(0,220,255),2)
        for obs in base.metadata["observations"]:
            if obs["source"]=="CV" and obs["object_category"]=="phone" and obs["source_frame_indices"]==[idx] and obs.get("bbox"):
                b=np.rint(obs["bbox"]).astype(int)
                cv2.rectangle(image,tuple(b[:2]),tuple(b[2:]),(80,255,80),2)
                cv2.putText(image,"Phase5 phone / "+("authorized" if obs.get("authorized_entity_id") else "unresolved"),(b[0],max(25,b[1]-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,(80,255,80),1)
        image=cv2.resize(image,(960,540));panel=np.zeros((125,960,3),np.uint8)
        cv2.putText(panel,f"PHASE 5 SAME FRAME: {f['video_id']} f{idx}",(10,35),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),1)
        left=np.concatenate([image,panel]);right=cv2.imread(str(output/f["video_id"]/f"f{idx:06d}_evidence.jpg"))
        cv2.imwrite(str(output/f["video_id"]/f"f{idx:06d}_comparison.jpg"),np.concatenate([left,right],axis=1))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",default="artifacts/phase6/pixel_demo")
    parser.add_argument("--bundle",help="source_manifest + arbitrary video-ID phase5_graphs mapping")
    parser.add_argument("--target-query",default="smartphone")
    parser.add_argument("--reference-image",help="Optional appearance context only; never identity authorization")
    parser.add_argument("--prepare-only",action="store_true")
    parser.add_argument("--coordinate-mode",choices=["canvas_pixels","normalized_legacy"],default="canvas_pixels")
    parser.add_argument("--reuse-perception",action="store_true",help="Integrate saved model outputs; no generation")
    parser.add_argument("--render-comparison",action="store_true",help="Render baseline and Phase 6 on identical frames; no inference")
    parser.add_argument("--memory",help="Query existing Phase 6 graph without model/media loading")
    parser.add_argument("--query",default="Where is my phone?")
    args=parser.parse_args()
    if args.memory:
        result=search(TemporalMemory.model_validate(read(ROOT/args.memory)),args.query)
        result["total_candidates"]=len(result["candidates"]);result["candidates"]=result["candidates"][:5]
        result.pop("location_history",None)
        print(json.dumps(result,ensure_ascii=False,indent=2));return
    output=(ROOT/args.output).resolve()
    if not output.is_relative_to((ROOT/"artifacts/phase6").resolve()):raise PermissionError("ISOLATED_PHASE6_ONLY")
    if not (output/"manifest.json").exists():prepare(output,args)
    manifest=read(output/"manifest.json")
    if manifest["prompt"]!=prompt(manifest["query"],manifest.get("model_canvas")):
        raise ValueError("PERCEPTION_PROMPT_CHANGED_USE_NEW_OUTPUT")
    if args.prepare_only:return
    if args.render_comparison:
        render_comparison(output,manifest);return
    if not args.reuse_perception:
        from memory_graph.integration.perception_runtime import localize,refine
        localize(ROOT,manifest["frames"],output,manifest["query"],manifest["reference"],manifest.get("model_canvas"))
        refine(ROOT,manifest["frames"],output)
    finish(output,manifest)
    render_comparison(output,manifest)


if __name__=="__main__":main()
