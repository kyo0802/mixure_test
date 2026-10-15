"""One-shot, two-generation DEV experiment; reuses unmodified NF4 loading/generation.

Phase2b CLI and its freeze/lease are NOT reused or relaxed. This is a separate
explicitly authorized experiment with a new prompt and bounded local entrypoint.
No GT/human review is read by prepare/worker. Report analysis happens afterward.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/p) for p in ("src","artifacts/pass_i/runtime/vendor","outputs/current_development/video_event_experiment/.deps")]
OUT=ROOT/"artifacts/pass_t/phase3/vlm_physical_state_pilot_v1"
BUNDLE=ROOT/"artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f/frozen_bundle.json"


def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def save(p,d):
    with Path(p).open("x",encoding="utf-8") as f:
        json.dump(d,f,ensure_ascii=False,indent=2)
        f.flush();os.fsync(f.fileno())


def validate_raw(raw,aliases):
    """No repair, fence removal, filling, or malformed->NO_EVENT conversion."""
    import jsonschema
    def strict_pairs(pairs):
        d={}
        for k,v in pairs:
            if k in d: raise ValueError("DUPLICATE_JSON_KEY:"+k)
            d[k]=v
        return d
    result={"json_valid":False,"schema_valid":None,"citation_valid":None,"semantic_valid":None,"full_v3_valid":False,"parsed":None,"diagnostics":[],"classification":"INVALID_MODEL_OUTPUT"}
    try:
        d=json.loads(raw,object_pairs_hook=strict_pairs,parse_constant=lambda s:(_ for _ in ()).throw(ValueError("NON_JSON_CONSTANT:"+s)))
        result.update(json_valid=True,parsed=d)
    except (ValueError,TypeError) as e:
        result["diagnostics"].append({"stage":"JSON","error":str(e)});return result
    errors=sorted(jsonschema.Draft202012Validator(read(OUT/"schema_v3.json")).iter_errors(d),key=lambda e:str(list(e.path)))
    result["schema_valid"]=not errors
    result["diagnostics"].extend({"stage":"SCHEMA","path":list(e.path),"error":e.message} for e in errors)
    if errors: return result
    citation_errors=[];semantic_errors=[]
    order={a:i for i,a in enumerate(aliases)}
    for i,e in enumerate(d["events"]):
        for a in e["before_frames"]+e["after_frames"]:
            if a not in order: citation_errors.append(f"events[{i}]:UNSUPPLIED_ALIAS:{a}")
        if all(a in order for a in e["before_frames"]+e["after_frames"]) and max(order[a] for a in e["before_frames"])>=min(order[a] for a in e["after_frames"]):
            semantic_errors.append(f"events[{i}]:BEFORE_NOT_BEFORE_AFTER")
        expected=("ON_SURFACE","HELD_BY_PERSON") if e["event_type"]=="PICKUP" else ("HELD_BY_PERSON","ON_SURFACE")
        if e["before_state"] not in ("UNKNOWN","OTHER",expected[0]) or e["after_state"] not in ("UNKNOWN","OTHER",expected[1]):
            semantic_errors.append(f"events[{i}]:CONTRADICTORY_KNOWN_STATE_ORDER")
    for i,o in enumerate(d.get("other_objects",[])):
        citation_errors.extend(f"other_objects[{i}]:UNSUPPLIED_ALIAS:{a}" for a in o["frames"] if a not in order)
    result.update(citation_valid=not citation_errors,semantic_valid=not semantic_errors)
    result["diagnostics"].extend({"stage":"CITATION","error":e} for e in citation_errors)
    result["diagnostics"].extend({"stage":"SEMANTIC","error":e} for e in semantic_errors)
    result["full_v3_valid"]=not citation_errors and not semantic_errors
    if result["full_v3_valid"]:
        result["classification"]={"EVENTS":"VLM_EVENT_CANDIDATE","NO_CONFIRMED_EVENT":"VLM_NO_CONFIRMED_EVENT","UNCERTAIN":"VLM_UNCERTAIN"}[d["status"]]
    result["physical_correctness_independently_validated"]=False
    return result


def prepare():
    if (OUT/"frozen_experiment.json").exists(): raise RuntimeError("ALREADY_PREPARED_NO_OVERWRITE")
    draft=read(BUNDLE)["protocol"]["draft"]
    windows=[]
    for name in ("test5__W05","test7__W05"):
        w=next(w for w in draft["windows"] if name in w["original_pack_ids"])
        assert len(w["selected"])==8
        frames=w["selected"]
        assert all(frames[i]["native_source_pts_s"]<frames[i+1]["native_source_pts_s"] for i in range(7))
        for s in frames:
            assert sha(ROOT/s["source_path"])==s["recorded_source_png_sha256"]
        windows.append({"window":name,"call":"A" if not windows else "B","frames":frames,"recorded_source_video_sha256":w["window_boundaries"]["source_video_sha256"],"source_video_reopened":False})
    prompt=read(OUT/"prompt_v3.json")
    assert not any(t in json.dumps(prompt).lower() for t in ("smartphone","basketball","test5","test7"))
    import jsonschema
    jsonschema.Draft202012Validator.check_schema(read(OUT/"schema_v3.json"))
    # Four minimal parser checks, no image/video fixtures or extra generations.
    checks={
        "malformed_stays_invalid":validate_raw("broken",["F0001"])["classification"]=="INVALID_MODEL_OUTPUT",
        "empty_events_status_rejected":not validate_raw('{"status":"EVENTS","events":[],"notes":""}',["F0001"])["schema_valid"],
        "valid_uncertain_kept_distinct":validate_raw('{"status":"UNCERTAIN","events":[],"notes":"insufficient"}',["F0001"])["classification"]=="VLM_UNCERTAIN",
        "valid_no_event_kept_distinct":validate_raw('{"status":"NO_CONFIRMED_EVENT","events":[],"notes":"observations only"}',["F0001"])["classification"]=="VLM_NO_CONFIRMED_EVENT"}
    assert all(checks.values())
    asset_path=ROOT/draft["model_assets_manifest"]
    config={"experiment":"PHASE3_VLM_FIRST_PHYSICAL_STATE_V1","model":"Qwen/Qwen2.5-VL-7B-Instruct","revision":"cc594898137f460bfe9f0759e9844b3ce807cfb5","model_snapshot":draft["model_snapshot"],"model_assets_manifest":draft["model_assets_manifest"],"quantization":"NF4_DOUBLE_BF16","attention":"sdpa","device":"cuda","representation":"MULTI_IMAGE_8_CHRONOLOGICAL_STILLS","reference":"NONE","processor_max_pixels":200704,"processor_min_pixels":3136,"max_images":8,"generation":{"sampling":False,"seed":42,"max_output_tokens":1024},"generation_timeout_seconds":300,"load_timeout_seconds":120,"request_timeout_seconds":330,"max_calls":2,"retry":0,"hardware_gib":draft["settings"]["hardware_gib"],"windows":windows,"authorization":{"source":"Explicit user attachment authorizes two calls only, no separate GPU approval required","attachment_sha256":sha(Path('C:/Users/smile/.codex/attachments/1da81e30-faa2-40de-a919-b5d8acae5871/貼上的文字.txt')),"historical_phase2b_lease_reused":False},"parser_contract_checks":checks,"no_memory_graph_writes":True}
    save(OUT/"configuration.json",config)
    # Preserve exact existing historical sources and every signal-spike file.
    old=ROOT/"WORKSPACE/Pass_T/Phase3_Observation_Capability_Audit_20261015"
    protected={**read(old/"PRESERVATION_BASELINE.json")["source_files"],**read(old/"ARTIFACT_PRESERVATION_BASELINE.json")}
    for folder in (ROOT/"artifacts/pass_t/phase3/signal_spike_v1",ROOT/"artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1"):
        for p in folder.rglob("*"):
            if p.is_file():protected[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all((ROOT/p).is_file() and sha(ROOT/p)==h for p,h in protected.items())
    save(OUT/"preservation_before.json",protected)
    frozen={"frozen_utc":now(),"configuration_sha256":sha(OUT/"configuration.json"),"prompt_sha256":sha(OUT/"prompt_v3.json"),"schema_sha256":sha(OUT/"schema_v3.json"),"runner_sha256":sha(Path(__file__)),"bundle_sha256":sha(BUNDLE),"asset_manifest_sha256":sha(asset_path),"runtime_sources_sha256":{p:sha(ROOT/p) for p in ("src/memory_graph/pass_t/phase2b/local_vlm/nf4.py","src/memory_graph/pass_t/phase2b/local_vlm/qwen_contract.py","src/memory_graph/pass_t/phase2b/local_vlm/runtime.py")},"calls_authorized":2,"prompt_same_for_both":True,"schema_same_for_both":True,"phase2b_protocol_changed":False}
    save(OUT/"frozen_experiment.json",frozen)
    print(json.dumps({"prepared":str(OUT),"frozen":frozen,"parser_checks":checks}),flush=True)


def verify_frozen():
    frozen=read(OUT/"frozen_experiment.json")
    for n,key in (("configuration.json","configuration_sha256"),("prompt_v3.json","prompt_sha256"),("schema_v3.json","schema_sha256")):
        assert sha(OUT/n)==frozen[key],"FROZEN_INPUT_CHANGED:"+n
    assert sha(Path(__file__))==frozen["runner_sha256"]
    for p,h in frozen["runtime_sources_sha256"].items(): assert sha(ROOT/p)==h
    return frozen,read(OUT/"configuration.json")


def worker():
    frozen,cfg=verify_frozen()
    os.environ.update(PASS_T_LOCAL_RUNTIME_APPROVAL="true",HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false")
    for n in ("HF_HOME","TORCH_HOME","TMP","TEMP","TMPDIR","TRITON_CACHE_DIR"):
        cache=OUT/"runtime_cache";cache.mkdir(exist_ok=True);os.environ[n]=str(cache)
    from memory_graph.pass_t.phase2b.local_vlm.nf4 import QwenNF4Runtime
    from memory_graph.pass_t.phase2b.local_vlm.catalog import SPECS
    from memory_graph.pass_t.phase2b.local_vlm.qwen_contract import processor_size,grid_accounting
    from memory_graph.pass_t.phase2b.local_vlm.video_array_bridge import tensor_record
    from PIL import Image
    class V3Runtime(QwenNF4Runtime):
        def preprocess(self,envelope):
            t0=time.perf_counter()
            verify_frozen()
            row=envelope["window"]
            prompt=read(OUT/"prompt_v3.json");schema=read(OUT/"schema_v3.json")
            images=[];content=[]
            for i,s in enumerate(row["frames"]):
                assert sha(ROOT/s["source_path"])==s["recorded_source_png_sha256"],"IMAGE_HASH_CHANGED"
                with Image.open(ROOT/s["source_path"]) as im: images.append(im.convert("RGB"))
                content.extend([{"type":"text","text":f'Image {i+1} corresponds exactly to frame alias {s["supplied_alias"]}.'},{"type":"image","image":images[-1]}])
            content.append({"type":"text","text":prompt["task"]+"\nRequired JSON schema:\n"+json.dumps(schema,ensure_ascii=False,sort_keys=True)})
            conversation=[{"role":"system","content":prompt["system"]},{"role":"user","content":content}]
            rendered=self.processor.apply_chat_template(conversation,tokenize=False,add_generation_prompt=True)
            size=processor_size(cfg["processor_max_pixels"])
            self.processor.image_processor.size=dict(size)
            self.processor.image_processor.min_pixels=cfg["processor_min_pixels"]
            self.processor.image_processor.max_pixels=cfg["processor_max_pixels"]
            inputs=self.processor(text=[rendered],images=images,padding=True,return_tensors="pt",device="cpu")
            grid=grid_accounting(inputs)
            assert "video_grid_thw" not in inputs and inputs["image_grid_thw"].shape[0]==8,"WRONG_REPRESENTATION"
            for dims in grid["per_grid_spatial_pixels"].values():assert all(p<=cfg["processor_max_pixels"] for p in dims)
            captured={"prompt_sha256":frozen["prompt_sha256"],"schema_sha256":frozen["schema_sha256"],"rendered_text":rendered,"rendered_text_sha256":hashlib.sha256(rendered.encode()).hexdigest(),"frame_mapping":row["frames"],"representation":cfg["representation"],"effective_temporal_representation":"Eight independent image inputs in chronological order, no native video tensor/time units; source PTS kept private in receipt only", "grid_accounting":grid,"tensor_records":{k:tensor_record(v) for k,v in inputs.items()},"processor_effective":self.processor.image_processor.to_dict(),"preprocessing_seconds":time.perf_counter()-t0}
            save(OUT/f'call_{row["call"]}_input_receipt.json',captured)
            return inputs,{"preprocessing_seconds":captured["preprocessing_seconds"],"grid_accounting":grid,"input_receipt_sha256":sha(OUT/f'call_{row["call"]}_input_receipt.json')}
    deployment={"approved":True,"processor_max_pixels":cfg["processor_max_pixels"],"generation_timeout_seconds":cfg["generation_timeout_seconds"],"asset_audit_path":str(ROOT/cfg["model_assets_manifest"]),"scratch_path":str(OUT/"runtime_cache"),"video_input_mode":"NATIVE_VIDEO_ARRAY_DISABLED"}
    try:
        runtime=V3Runtime(SPECS["qwen_nf4"],deployment,ROOT/cfg["model_snapshot"],None)
        save(OUT/"model_load_receipt.json",runtime.health())
        for row in cfg["windows"]:
            verify_frozen()
            call=row["call"]
            # Durable at-most-once marker BEFORE invoking shared generate.
            save(OUT/f"call_{call}_attempt.json",{"utc":now(),"window":row["window"],"generation_budget_ordinal":1 if call=="A" else 2,"max_generations":2,"freeze_sha256":sha(OUT/"frozen_experiment.json")})
            try:
                result=runtime.generate({"window":row,"generation":cfg["generation"]})
                # Raw decoded model response is preserved first, with no parser intervention.
                raw=result.pop("raw_output")
                with (OUT/f"call_{call}_raw.txt").open("xb") as f:
                    f.write(raw.encode("utf-8"));f.flush();os.fsync(f.fileno())
                save(OUT/f"call_{call}_execution.json",{**result,"window":row["window"],"call":call,"completed_utc":now(),"raw_sha256":sha(OUT/f"call_{call}_raw.txt"),"frozen_experiment_sha256":sha(OUT/"frozen_experiment.json")})
                save(OUT/f"call_{call}_parsed.json",validate_raw(raw,[s["supplied_alias"] for s in row["frames"]]))
                print("CALL_COMPLETED "+call,flush=True)
            except Exception as e:
                save(OUT/f"call_{call}_failure.json",{"error_type":type(e).__name__,"error":str(e),"traceback":traceback.format_exc(),"utc":now(),"no_retry":True})
                raise  # Fail closed on technical failure; do not change settings or retry.
    except Exception as e:
        save(OUT/"worker_failure.json",{"error":str(e),"traceback":traceback.format_exc(),"utc":now()})
        raise


def run():
    frozen,cfg=verify_frozen()
    # Never reuse the execution directory for another model generation.
    save(OUT/"execution_started.json",{"utc":now(),"frozen_experiment_sha256":sha(OUT/"frozen_experiment.json"),"max_calls":2,"retry":0})
    import psutil
    # No extra model call/warmup. nvidia-smi is metadata only.
    ram=psutil.virtual_memory().available/2**30
    gpu=subprocess.check_output(["nvidia-smi","--query-gpu=memory.free,memory.used","--format=csv,noheader,nounits"],text=True).strip().splitlines()[0]
    free,used=[float(x.strip())/1024 for x in gpu.split(",")]
    if ram<8 or free<10:raise RuntimeError("INSUFFICIENT_LOAD_HEADROOM_NO_MODEL_STARTED")
    save(OUT/"hardware_before.json",{"available_ram_gib":ram,"gpu_free_gib":free,"gpu_used_gib":used,"utc":now()})
    with (OUT/"runtime.log").open("xb") as log:
        p=subprocess.Popen([sys.executable,"-X","utf8","-B",str(Path(__file__)),"worker"],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        t0=time.monotonic();reason=None;last_gpu=0;peak_rss=0;peak_gpu_used=0
        while p.poll() is None:
            time.sleep(1)
            try:
                process=psutil.Process(p.pid)
            except psutil.NoSuchProcess:
                # Child may exit between poll() and resource sampling.
                p.wait()
                break
            try: rss=sum(x.memory_info().rss for x in [process]+process.children(recursive=True) if x.is_running())/2**30
            except psutil.NoSuchProcess:rss=0
            peak_rss=max(peak_rss,rss)
            elapsed=time.monotonic()-t0
            if rss>20 or psutil.virtual_memory().available<2*2**30:reason="RAM_SAFETY_GATE"
            loaded=(OUT/"model_load_receipt.json").exists()
            if not loaded and elapsed>cfg["load_timeout_seconds"]:reason="LOAD_TIMEOUT"
            if elapsed>cfg["load_timeout_seconds"]+2*cfg["request_timeout_seconds"]:reason="TOTAL_TIMEOUT"
            for call in ("A","B"):
                attempt=OUT/f"call_{call}_attempt.json"
                if attempt.exists() and not (OUT/f"call_{call}_execution.json").exists() and time.time()-attempt.stat().st_mtime>cfg["request_timeout_seconds"]:reason="CALL_TIMEOUT_"+call
            if elapsed-last_gpu>=3:
                used=float(subprocess.check_output(["nvidia-smi","--query-gpu=memory.used","--format=csv,noheader,nounits"],text=True).strip().splitlines()[0])/1024
                peak_gpu_used=max(peak_gpu_used,used);last_gpu=elapsed
                if used>14.5:reason="GLOBAL_GPU_USED_OVER_14_5_GIB"
            if reason:
                for child in process.children(recursive=True):child.terminate()
                process.terminate();p.wait(timeout=20);break
        code=p.wait()
    save(OUT/"execution_summary.json",{"completed_utc":now(),"process_exit_code":code,"guard_stop":reason,"elapsed_seconds":time.monotonic()-t0,"peak_owned_tree_rss_gib":peak_rss,"peak_sampled_global_gpu_used_gib":peak_gpu_used,"sampling_interval_s":3,"completed_calls":[c for c in ("A","B") if (OUT/f"call_{c}_execution.json").exists()],"attempt_markers":[c for c in ("A","B") if (OUT/f"call_{c}_attempt.json").exists()],"not_executed":[c for c in ("A","B") if not (OUT/f"call_{c}_attempt.json").exists()],"retries":0,"graph_writes":0})
    print((OUT/"execution_summary.json").read_text(encoding="utf-8"),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("prepare","run","worker"))
    args=parser.parse_args()
    {"prepare":prepare,"run":run,"worker":worker}[args.mode]()
