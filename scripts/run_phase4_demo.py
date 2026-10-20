"""CPU-only isolated FindMind replay. No model or annotation-review imports."""
import argparse
from collections import Counter
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
# Reuse the existing CPU validator dependency without loading model runtimes.
try:
    import jsonschema
except ImportError:
    sys.path.append(str(ROOT/"artifacts/pass_i/runtime/vendor"))
    import jsonschema
from memory_graph.integration.adapters import read,sha,adapt_nemotron,adapt_cv
from memory_graph.integration.pipeline import run,persist,search
from memory_graph.memory.memory_store import save_json
from memory_graph.scene_graph.models import TemporalMemory


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",default="artifacts/phase4/recorded_demo_v1")
    p.add_argument("--videos",nargs="+",default=None)
    p.add_argument("--query",default="Where is my phone?")
    p.add_argument("--future-bundle",help="JSON with source_manifest, results [{window, raw_path, raw_sha256}], optional cv_sources")
    args=p.parse_args()
    output=(ROOT/args.output).resolve()
    if not output.is_relative_to((ROOT/"artifacts/phase4").resolve()):
        raise ValueError("Only isolated artifacts/phase4 output is allowed")
    if output.exists():raise FileExistsError("Select a new isolated --output; previous run is immutable")
    touched={}
    def track(path):
        path=Path(path)
        if not path.is_absolute():path=ROOT/path
        path=path.resolve(); touched[str(path)]=sha(path)
        return path
    def load(path):return read(track(path))
    cv_sources={}
    if args.future_bundle:
        bundle=load(args.future_bundle)
        manifest=load(bundle["source_manifest"])
        entries=bundle["results"]
        cv_sources=bundle.get("cv_sources",{})
    else:
        exp=ROOT/"artifacts/pass_t/phase3/three_vlm_full_v1"
        manifest=load("tools/findmind-gt-annotator/manifest.json")  # Source timing metadata only, no annotations.
        dataset=load(exp/"dataset.json")
        windows={w["window_id"]:w for w in dataset["windows"]}
        entries=[dict(window=windows[r["window_id"]],raw_path=r["raw_path"],raw_sha256=r["raw_sha256"])
                 for r in load(exp/"model_results.json")["nemotron"]["rows"]]
        for video in manifest["videos"]:
            vid=video["video_id"]
            cv_sources[vid]=dict(identity=f"outputs/identity_rebuild/development/runs_final/{vid}/identity.json",
                metrics=f"outputs/identity_rebuild/development/runs_final/{vid}/metrics.json",
                tracks=f"outputs_v292/{vid}/perception/tracks.json",sam=f"outputs_v292/{vid}/sam/sam_continuity_log.json")
    videos={v["video_id"]:v for v in manifest["videos"]}
    selected=set(args.videos or [e["window"]["video_id"] for e in entries])
    if not selected<=videos.keys():raise ValueError("Unknown video selection")
    results={};diagnostics=[]
    for vid in sorted(selected):
        video=videos[vid]
        media=track(video.get("source_path",video["original_filename"]))
        if sha(media)!=video["source_sha256"]:raise ValueError("Original video identity changed: "+vid)
        obs=[];hyp=[];receipts=[]
        for entry in entries:
            window=entry["window"]
            if window["video_id"]!=vid:continue
            raw_path=track(entry["raw_path"])
            if sha(raw_path)!=entry["raw_sha256"]:raise ValueError("Raw model output changed")
            for f in window["frames"]:track(f["path"])
            o,h,r=adapt_nemotron(raw_path.read_bytes().decode("utf-8"),window,video,str(raw_path),ROOT)
            obs+=o;hyp+=h;receipts.append(r)
        source=cv_sources.get(vid)
        if source:
            try:
                metrics=load(source["metrics"])
                if metrics["video_sha256"]!=video["source_sha256"]:raise ValueError("CV_VIDEO_IDENTITY_MISMATCH")
                refs={k:str(track(source[k])) for k in ("identity","tracks")}
                if sha(refs["tracks"])!=metrics["source_hashes"]["tracks"]:raise ValueError("CV_TRACK_HASH_MISMATCH")
                sam=[]
                if source.get("sam"):
                    refs["sam"]=str(track(source["sam"]))
                    if sha(refs["sam"])!=metrics["source_hashes"]["sam"]:raise ValueError("CV_SAM_HASH_MISMATCH")
                    sam=[r for segment in read(refs["sam"]).get("segments",[]) for r in segment.get("observations",[])]
                refs.update({k+"_sha256":sha(v) for k,v in list(refs.items())})
                obs+=adapt_cv(read(refs["tracks"]),read(refs["identity"]),video,refs,sam)
            except FileNotFoundError as exc:
                diagnostics.append(dict(video_id=vid,status="CV_UNAVAILABLE",reason=str(exc)))
            # Integrity errors are fatal, never silently discarded as missing CV.
        memory=run(vid,obs,hyp,receipts)
        results[vid]=(memory,search(memory,args.query))
    # All inputs validated before any output is persisted.
    output.mkdir(parents=True)
    summary={}
    for vid,(memory,response) in results.items():
        persist(memory,output/vid/"memory_graph.json")
        reloaded=TemporalMemory.model_validate(read(output/vid/"memory_graph.json"))
        assert search(reloaded,args.query)==response
        save_json(output/vid/"event_decisions.json",memory.events)
        save_json(output/vid/"search_result.json",response)
        counts=Counter(e["decision"] for e in memory.events)
        observations=memory.metadata["observations"]
        summary[vid]=dict(model_responses=len(memory.metadata["response_receipts"]),
            observations=len(observations),sources=dict(Counter(o["source"] for o in observations)),
            authorized_cv_observations=sum(bool(o["authorized_entity_id"]) for o in observations),
            entities=len(memory.entities),event_decisions=dict(counts),confirmed_transitions=len(memory.transitions),
            search_status=response["status"],locations=[c["location"]["id"] for c in response["candidates"]],
            raw_strict_valid=sum(r["validation"]["raw"]["full_valid"] for r in memory.metadata["response_receipts"]))
    changed=[path for path,before in touched.items() if sha(path)!=before]
    if changed:raise RuntimeError("Input preservation failed: "+str(changed))
    save_json(output/"run_receipt.json",dict(summary=summary,diagnostics=diagnostics,
        checked_input_hashes=touched,preserved_inputs=len(touched),changed_inputs=changed,
        new_model_calls=0,media_access="SHA256 bytes only; no decode needed for recorded observations",
        review_verdicts_loaded=False,production_memory_written=False,
        source_code_hashes={str(path.relative_to(ROOT)):sha(path) for path in
            [Path(__file__),*sorted((ROOT/"src/memory_graph/integration").glob("*.py"))]}))
    lines=["# Phase 4 recorded demo","",
        "```mermaid","flowchart LR","CV[YOLO / ByteTrack / SAM / IdentityGuard] --> N[Evidence normalization]",
        "V[Nemotron raw outputs] --> N","N --> D[Event decision]",
        "N --> G[Existing TemporalMemory: observations]","D --> G","G --> S[Object search]","```","",
        "| Video | CV / VLM observations | Supported / Rejected / Uncertain | Search |",
        "|---|---|---|---|"]
    for vid,s in summary.items():
        c=s["event_decisions"]
        lines.append(f"| {vid} | {s['sources'].get('CV',0)} / {s['sources'].get('VLM',0)} | {c.get('SUPPORTED',0)} / {c.get('REJECTED',0)} / {c.get('UNCERTAIN',0)} | {s['search_status']} |")
    lines+=["","Graph records and provenance are in each video directory. No VLM category is bound to a persistent entity. CV geometry alone supplies no named destination or independent held/surface transition."]
    (output/"DEMO.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(__import__("json").dumps(dict(output=str(output),summary=summary),ensure_ascii=False))


if __name__=="__main__":main()
