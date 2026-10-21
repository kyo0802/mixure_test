"""CPU-only spatial grounding over existing Phase 4 observations and real frames."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
try:import jsonschema
except ImportError:sys.path.append(str(ROOT/"artifacts/pass_i/runtime/vendor"))
import cv2
import numpy as np
from memory_graph.integration.adapters import read,sha
from memory_graph.integration.regions import propose_regions,viewpoint_change,validate_region,REGION_CLASSES
from memory_graph.integration.spatial import enrich_memory
from memory_graph.integration.pipeline import search
from memory_graph.scene_graph.models import TemporalMemory
from memory_graph.memory.memory_store import save_json


def persist_spatial(memory,path):
    path=Path(path).resolve()
    if not path.is_relative_to((ROOT/"artifacts/phase5").resolve()) or not memory.metadata.get("isolated_demo"):
        raise PermissionError("PHASE5_ISOLATED_OUTPUT_ONLY")
    save_json(path,memory)


def draw(image,regions,objects,title):
    canvas=image.copy()
    for r in regions:
        pts=np.asarray(r["polygon"],np.int32)
        cv2.polylines(canvas,[pts],True,(0,220,255),2)
        x,y=pts[0]
        cv2.putText(canvas,r["region_label"],(int(x),max(20,int(y))),cv2.FONT_HERSHEY_SIMPLEX,.45,(0,180,255),1)
    for o in objects:
        if o.get("bbox"):
            x1,y1,x2,y2=map(int,o["bbox"])
            cv2.rectangle(canvas,(x1,y1),(x2,y2),(60,255,80),2)
            cv2.putText(canvas,o["object_category"]+" candidate",(x1,max(20,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,(50,255,80),1)
    canvas=cv2.resize(canvas,(640,360))
    cv2.rectangle(canvas,(0,0),(640,25),(0,0,0),-1)
    cv2.putText(canvas,title,(5,18),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
    return canvas


def execute(args):
    started=time.monotonic()
    output=(ROOT/args.output).resolve()
    if not output.is_relative_to((ROOT/"artifacts/phase5").resolve()):raise PermissionError("PHASE5_OUTPUT_ONLY")
    if output.exists():raise FileExistsError("Use a fresh output directory")
    touched={}
    def tracked(path):
        path=Path(path)
        if not path.is_absolute():path=ROOT/path
        path=path.resolve()
        touched[str(path)]=sha(path)
        return path
    def load(path):return read(tracked(path))
    if args.bundle:
        bundle=load(args.bundle)
        manifest=load(bundle["source_manifest"])
        graphs=bundle["phase4_graphs"]
        receipts=bundle.get("input_receipts",[])
    else:
        manifest=load("tools/findmind-gt-annotator/manifest.json")
        graphs={v["video_id"]:f"artifacts/phase4/demo/{v['video_id']}/memory_graph.json" for v in manifest["videos"]}
        receipts=["artifacts/phase4/demo/run_receipt.json"]
    # Check every recorded upstream input BEFORE consuming its derived graph.
    for receipt in receipts:
        for path,expected in load(receipt).get("checked_input_hashes",{}).items():
            if sha(tracked(path))!=expected:raise ValueError("PHASE4_INPUT_CHANGED: "+path)
    bootstrap=load(args.regions) if args.regions else []
    videos={v["video_id"]:v for v in manifest["videos"]}
    selected=args.videos or list(graphs)
    if not set(selected)<=videos.keys():raise ValueError("UNKNOWN_VIDEO")
    # Preserve full Phase 4 artifacts and GT/consolidation files without using
    # their contents for decisions. Only byte hashes are read for this audit.
    preserved={}
    for directory in ("artifacts/phase4","artifacts/vlmtest/gt_consolidation_v1"):
        for path in (ROOT/directory).rglob("*"):
            if path.is_file():preserved[str(path.resolve())]=sha(path)
    output.mkdir(parents=True)
    summaries={};examples=[]
    for vid in selected:
        video=videos[vid]
        media=tracked(video.get("source_path",video["original_filename"]))
        if sha(media)!=video["source_sha256"]:raise ValueError("SOURCE_VIDEO_HASH_MISMATCH")
        memory=TemporalMemory.model_validate(load(graphs[vid]))
        if memory.video!=vid or not memory.metadata.get("isolated_demo"):raise ValueError("WRONG_GRAPH_SCOPE")
        event_snapshot=json.dumps([memory.events,memory.transitions],sort_keys=True)
        observations=memory.metadata["observations"]
        by_frame={}
        for o in observations:
            if o["video_id"]!=vid or o["source_video_sha256"]!=video["source_sha256"]:raise ValueError("OBS_SOURCE_MISMATCH")
            if len(o["source_frame_indices"])!=len(o["source_times_s"]):raise ValueError("OBS_TIMING_MISMATCH")
            for f,t in zip(o["source_frame_indices"],o["source_times_s"]):
                if not 0<=f<len(video["frame_timeline"]) or video["frame_timeline"][f]["source_time_s"]!=t:raise ValueError("OBS_NATIVE_PTS_MISMATCH")
                by_frame.setdefault(f,[]).append(o)
        wanted={f for f,obs in by_frame.items() if any(o["source"]=="CV" and o["object_category"] in REGION_CLASSES for o in obs)}
        # Include a sparse original-frame overview and VLM-phone frames for
        # missing-detection inspection; this does not create object detections.
        overview=set(range(0,video["frame_count"],max(1,video["frame_count"]//16)))
        missing={f for f,obs in by_frame.items() if any(o["source"]=="VLM" and o["object_category"]=="phone" for o in obs)
            and not any(o["source"]=="CV" and o["object_category"]=="phone" for o in obs)}
        wanted|=overview|missing
        regions=[];frames={};motion=[];previous=None;previous_index=None
        target=output/vid; (target/"frames").mkdir(parents=True)
        capture=cv2.VideoCapture(str(media))
        if not capture.isOpened():raise RuntimeError("VIDEO_DECODE_OPEN_FAILED")
        index=0
        try:
            while index<=max(wanted,default=-1):
                ok,image=capture.read()
                if not ok:raise RuntimeError(f"VIDEO_EARLY_EOF:{vid}:{index}")
                if index in wanted:
                    path=target/"frames"/f"S{index:06d}.jpg"
                    if not cv2.imwrite(str(path),image):raise RuntimeError("FRAME_WRITE_FAILED")
                    ref=dict(path=str(path.relative_to(ROOT)),sha256=sha(path),
                        source_video_sha256=video["source_sha256"],source_frame_index=index,
                        source_time_s=video["frame_timeline"][index]["source_time_s"],
                        decoded_pixels_sha256=__import__('hashlib').sha256(image.tobytes()).hexdigest(),
                        note="JPEG inspection copy; extraction used original decoded pixels")
                    current=propose_regions(image,video,index,by_frame.get(index,[]),ref)
                    regions+=current
                    frames[index]=dict(ref=ref,thumbnail=draw(image,current,[o for o in by_frame.get(index,[]) if o["source"]=="CV" and o["object_category"]=="phone"],f"{vid} frame {index} / {ref['source_time_s']:.3f}s"))
                    if previous is not None:
                        motion.append(dict(previous_frame=previous_index,frame=index,**viewpoint_change(previous,image)))
                    previous=image;previous_index=index
                index+=1
        finally:capture.release()
        for r in bootstrap:
            if r["video_id"]==vid:
                if r.get("provenance",{}).get("origin")!="REVIEWER_SUPPLIED_REGION":raise ValueError("BOOTSTRAP_PROVENANCE_REQUIRED")
                regions.append(validate_region(r,video))
        enrich_memory(memory,video,regions)
        assert event_snapshot==json.dumps([memory.events,memory.transitions],sort_keys=True)
        memory.metadata["viewpoint_diagnostics"]=motion
        response=search(memory,args.query)
        persist_spatial(memory,target/"memory_graph.json")
        reloaded=TemporalMemory.model_validate(read(target/"memory_graph.json"))
        assert search(reloaded,args.query)==response
        locations=memory.metadata["location_observations"]
        associations=memory.metadata["vlm_cv_associations"]
        for name,data in [("scene_regions",regions),("object_region_relationships",locations),
            ("vlm_cv_associations",associations),("unresolved_associations",[a for a in associations if a["status"]=="UNRESOLVED"]),
            ("grounded_location_observations",[r for r in locations if r["grounding_status"] in {"CANDIDATE","VERIFIED"}]),
            ("viewpoint_diagnostics",motion),("search_result",response)]:save_json(target/(name+".json"),data)
        # Uniform overview plus evidence-rich candidate examples, no GT times.
        selected_frames=sorted(overview & frames.keys())
        loc_frames=sorted({r["source_frame_index"] for r in locations if r["grounding_status"]=="CANDIDATE"})
        selected_frames+=loc_frames[::max(1,len(loc_frames)//8)][:8]
        selected_frames+=sorted(missing & frames.keys())[::max(1,len(missing)//4)][:4]
        selected_frames=list(dict.fromkeys(selected_frames))
        for page in range(0,len(selected_frames),8):
            ids=selected_frames[page:page+8]
            tiles=[frames[f]["thumbnail"] for f in ids]
            while len(tiles)%2:tiles.append(np.zeros((360,640,3),np.uint8))
            sheet=np.concatenate([np.concatenate(tiles[i:i+2],axis=1) for i in range(0,len(tiles),2)],axis=0)
            sheet_path=target/f"evidence_{page//8+1:02d}.jpg";cv2.imwrite(str(sheet_path),sheet)
            examples.append(dict(video_id=vid,path=str(sheet_path.relative_to(ROOT)),source_frames=ids))
        summaries[vid]=dict(decoded_source_frames=index,extracted_frames=len(frames),
            region_candidates=sum(r["grounding_status"]=="CANDIDATE" for r in regions),
            verified_regions=sum(r["grounding_status"]=="VERIFIED" for r in regions),
            region_geometry=dict(Counter(r["geometry_kind"] for r in regions)),
            object_region_status=dict(Counter(r["grounding_status"] for r in locations)),
            relations=dict(Counter(r["spatial_relation"] for r in locations)),
            persistent_identity_associations=sum(bool(r["persistent_entity_id"]) and r["grounding_status"] in {"CANDIDATE","VERIFIED"} for r in locations),
            trusted_location_observations=len(memory.metadata["trusted_location_history"]),
            vlm_cv_status=dict(Counter(a["status"] for a in associations)),
            vlm_cv_reasons=dict(Counter(a["reason"] for a in associations)),
            search_status=response["status"],search_candidates=len(response["candidates"]),
            candidate_named_regions=sorted({r["region_label"] for r in response["candidates"]}),
            event_decisions=dict(Counter(e["decision"] for e in memory.events)),
            graph_reload_query_equal=True)
        print(json.dumps(dict(video_id=vid,summary=summaries[vid]),ensure_ascii=False),flush=True)
    changed=[p for p,h in {**preserved,**touched}.items() if sha(p)!=h]
    if changed:raise RuntimeError("INPUT_PRESERVATION_FAILED:"+str(changed))
    save_json(output/"evidence_manifest.json",examples)
    receipt=dict(summary=summaries,elapsed_s=time.monotonic()-started,new_model_calls=0,
        production_memory_written=False,gt_verdicts_used=False,
        preserved_file_count=len(preserved),checked_input_hashes=touched,changed_inputs=changed,
        preservation_hashes=preserved,source_code_hashes={str(p.relative_to(ROOT)):sha(p) for p in
            [Path(__file__),*sorted((ROOT/"src/memory_graph/integration").glob("*.py"))]},
        policy="frame-local proposals; projected geometry is not physical support; no propagation",
        original_event_decisions_preserved=True)
    save_json(output/"run_receipt.json",receipt)
    print(json.dumps(dict(output=str(output),elapsed_s=receipt["elapsed_s"],preserved_files=len(preserved)),ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",default="artifacts/phase5/demo")
    parser.add_argument("--videos",nargs="+")
    parser.add_argument("--query",default="Where is my phone?")
    parser.add_argument("--bundle",help="Source manifest, arbitrary video-ID to phase4_graph path, optional input_receipts")
    parser.add_argument("--regions",help="Optional explicitly sourced reviewer regions; default automatic only")
    parser.add_argument("--memory",help="Query a saved Phase 5 graph without decoding video or rebuilding")
    parser.add_argument("--entity-id",help="Optional exact authorized persistent entity ID")
    parser.add_argument("--limit",type=int,default=5,help="Query-only display limit; 0 shows all candidates")
    args=parser.parse_args()
    if args.memory:
        memory=TemporalMemory.model_validate(read(ROOT/args.memory))
        if memory.metadata.get("spatial_version")!="phase5_v1":raise ValueError("PHASE5_GRAPH_REQUIRED")
        result=search(memory,args.query,args.entity_id)
        result["total_candidates"]=len(result["candidates"])
        if args.limit>0:result["candidates"]=result["candidates"][:args.limit]
        result["location_history_observation_ids"]=[r["observation_id"] for r in result.pop("location_history")]
        print(json.dumps(result,ensure_ascii=False,indent=2))
    else:execute(args)


if __name__=="__main__":main()
