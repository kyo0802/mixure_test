"""Bounded Qwen B/C ablation; four calls maximum, no retry or historical writes."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, time, traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/p) for p in ("src","artifacts/pass_i/runtime/vendor","outputs/current_development/video_event_experiment/.deps")]
OUT=ROOT/"artifacts/pass_t/phase3/observation_ablation_v1"
BASE=ROOT/"artifacts/pass_t/phase3/vlm_physical_state_pilot_v1"
CONDITIONS={"B":"condition_b_higher_detail","C":"condition_c_state_first"}
def read(p): return json.loads(Path(p).read_text(encoding="utf8"))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc(): return datetime.now(timezone.utc).isoformat()
def save(p,d):
    with Path(p).open("x",encoding="utf8") as f:
        json.dump(d,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
def rawsave(p,text):
    with Path(p).open("xb") as f:f.write(text.encode("utf8"));f.flush();os.fsync(f.fileno())

def strict_load(text):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError("DUPLICATE_JSON_KEY:"+k)
            d[k]=v
        return d
    return json.loads(text,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError("NON_JSON_CONSTANT:"+x)))

def schema_errors(d,schema):
    from jsonschema import Draft202012Validator
    return [{"path":list(e.path),"message":e.message,"validator":e.validator} for e in sorted(Draft202012Validator(schema).iter_errors(d),key=lambda e:str(list(e.path)))]

def validation(raw,schema,aliases,condition):
    """Strict results never use extraction. Extraction is descriptive, never repaired."""
    result={"strict":{"json_valid":False,"schema_valid":None,"citation_valid":None,"semantic_valid":None,"full_valid":False,"classification":"INVALID_MODEL_OUTPUT","errors":[]},"strict_parsed":None,"formatting_errors":[],"qualitative_extraction":None}
    if re.search(r"(?m)^\s*```",raw):result["formatting_errors"].append("MARKDOWN_FENCE")
    d=None
    try:
        d=strict_load(raw);result["strict"]["json_valid"]=True;result["strict_parsed"]=d
    except (ValueError,TypeError) as e:result["strict"]["errors"].append({"stage":"JSON","message":str(e)})
    if result["strict"]["json_valid"]:
        errors=schema_errors(d,schema);result["strict"]["schema_valid"]=not errors
        result["strict"]["errors"].extend({"stage":"SCHEMA",**e} for e in errors)
        if not errors:
            order={a:i for i,a in enumerate(aliases)};cite=[];semantic=[]
            def scan(x):
                if isinstance(x,dict):
                    for k,v in x.items():
                        if k in ("frames","before_frames","after_frames"):
                            cite.extend("UNSUPPLIED_ALIAS:"+a for a in v if a not in order)
                        else:scan(v)
                elif isinstance(x,list):
                    for v in x:scan(v)
            scan(d)
            for i,e in enumerate(d.get("events",[])):
                if all(a in order for a in e["before_frames"]+e["after_frames"]):
                    if max(order[a] for a in e["before_frames"])>=min(order[a] for a in e["after_frames"]):semantic.append(f"EVENT_{i}_TEMPORAL_ORDER")
                if condition=="C":
                    candidates=[o for o in d["observations"] if o["object"]==e["object"]]
                    if len(candidates)!=1:semantic.append(f"EVENT_{i}_OBJECT_REFERENCE")
                    else:
                        citations={a for s in candidates[0]["states"] for a in s["frames"]}
                        if not set(e["before_frames"]+e["after_frames"])<=citations:semantic.append(f"EVENT_{i}_UNREFERENCED_STATE_EVIDENCE")
                else:
                    b,a=("ON_SURFACE","HELD_BY_PERSON") if e["event_type"]=="PICKUP" else ("HELD_BY_PERSON","ON_SURFACE")
                    if e["before_state"] not in (b,"UNKNOWN","OTHER") or e["after_state"] not in (a,"UNKNOWN","OTHER"):semantic.append(f"EVENT_{i}_CONTRADICTORY_STATES")
            result["strict"].update(citation_valid=not cite,semantic_valid=not semantic,full_valid=not cite and not semantic)
            result["strict"]["errors"].extend({"stage":"CITATION","message":x} for x in cite)
            result["strict"]["errors"].extend({"stage":"SEMANTIC","message":x} for x in semantic)
            if result["strict"]["full_valid"]:result["strict"]["classification"]={"EVENTS":"VLM_EVENT_CANDIDATE","NO_CONFIRMED_EVENT":"VLM_NO_CONFIRMED_EVENT","UNCERTAIN":"VLM_UNCERTAIN"}[d["status"]]
    # Exactly one outer fence only; no substring search, field filling or JSON repair.
    match=re.fullmatch(r"\s*```(?:json)?\s*\n(.*?)\n```\s*",raw,re.DOTALL)
    if match and "```" not in match.group(1):
        try:
            body=strict_load(match.group(1))
            result["qualitative_extraction"]={"method":"EXACT_SINGLE_OUTER_FENCE_BODY_JSON_READ_ONLY","authoritative":False,"changes_strict_validity":False,"claims":body,"body_schema_errors":schema_errors(body,schema)}
        except (ValueError,TypeError):pass
    result["independent_physical_validation"]=False
    return result

def prepare():
    assert not (OUT/"freeze.json").exists(),"EXPERIMENT_ALREADY_FROZEN"
    original=read(BASE/"configuration.json")
    old=ROOT/"WORKSPACE/Pass_T/Phase3_Observation_Capability_Audit_20261015"
    protected={**read(old/"PRESERVATION_BASELINE.json")["source_files"],**read(old/"ARTIFACT_PRESERVATION_BASELINE.json")}
    for folder in (BASE,ROOT/"artifacts/pass_t/phase3/signal_spike_v1"):
        for p in folder.rglob("*"):
            if p.is_file() and "runtime_cache" not in p.parts:protected[p.relative_to(ROOT).as_posix()]=sha(p)
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    save(OUT/"preservation_before.json",protected)
    from transformers import AutoProcessor
    from PIL import Image
    from memory_graph.pass_t.phase2b.local_vlm.qwen_contract import processor_size,grid_accounting
    from jsonschema import Draft202012Validator
    processor=AutoProcessor.from_pretrained(ROOT/original["model_snapshot"],local_files_only=True,trust_remote_code=False,max_pixels=200704)
    preflight={};configs={}
    for c in ("B","C"):
        dest=OUT/CONDITIONS[c];dest.mkdir(exist_ok=True)
        if c=="B":
            for src,name in (("prompt_v3.json","prompt.json"),("schema_v3.json","schema.json")): (dest/name).write_bytes((BASE/src).read_bytes())
        else:
            cp=read(dest/"prompt.json");cp={"system":read(BASE/"prompt_v3.json")["system"],"task":cp["task"]}
            assert not re.search(r"\b(smartphone|basketball|card|test5|test7)\b",json.dumps(cp),re.I)
            (dest/"prompt.json").write_text(json.dumps(cp,ensure_ascii=False,indent=2),encoding="utf8")
        schema=read(dest/"schema.json");Draft202012Validator.check_schema(schema)
        cfg={k:original[k] for k in ("model","revision","model_snapshot","model_assets_manifest","quantization","attention","device","representation","reference","processor_min_pixels","max_images","generation","generation_timeout_seconds","load_timeout_seconds","request_timeout_seconds","hardware_gib","windows")}
        cfg.update(condition=c,processor_max_pixels=401408 if c=="B" else 200704,max_calls=2,global_max_calls=4,retries=0,baseline_directory=str(BASE.relative_to(ROOT)),human_answers_model_visible=False)
        cfg["expected_baseline_rendered_sha256"]={w["window"]:read(BASE/f'call_{w["call"]}_input_receipt.json')["rendered_text_sha256"] for w in original["windows"]}
        save(dest/"configuration.json",cfg);configs[c]=cfg
        processor.image_processor.size=processor_size(cfg["processor_max_pixels"])
        processor.image_processor.min_pixels=3136;processor.image_processor.max_pixels=cfg["processor_max_pixels"]
        for w in cfg["windows"]:
            frames=w["frames"]
            assert len(frames)==8 and all(frames[i]["native_source_pts_s"]<frames[i+1]["native_source_pts_s"] for i in range(7))
            images=[]
            for f in frames:
                assert sha(ROOT/f["source_path"])==f["recorded_source_png_sha256"]
                with Image.open(ROOT/f["source_path"]) as im:images.append(im.convert("RGB"))
            p=read(dest/"prompt.json");content=[]
            for i,(s,im) in enumerate(zip(frames,images)):content.extend([{"type":"text","text":f'Image {i+1} corresponds exactly to frame alias {s["supplied_alias"]}.'},{"type":"image","image":im}])
            content.append({"type":"text","text":p["task"]+"\nRequired JSON schema:\n"+json.dumps(schema,ensure_ascii=False,sort_keys=True)})
            rendered=processor.apply_chat_template([{"role":"system","content":p["system"]},{"role":"user","content":content}],tokenize=False,add_generation_prompt=True)
            rendered_sha=hashlib.sha256(rendered.encode()).hexdigest()
            if c=="B":assert rendered_sha==cfg["expected_baseline_rendered_sha256"][w["window"]],"B_TASK_CHANGED"
            pixel_kwargs={"max_pixels":cfg["processor_max_pixels"],"min_pixels":3136} if c=="B" else {}
            inputs=processor(text=[rendered],images=images,padding=True,return_tensors="pt",device="cpu",**pixel_kwargs)
            preflight[c+"_"+w["call"]]={"grid":grid_accounting(inputs),"input_tokens":int(inputs["input_ids"].shape[-1]),"rendered_sha256":rendered_sha,"model_loaded":False,"generation_calls":0}
            assert inputs["image_grid_thw"].shape[0]==8 and "video_grid_thw" not in inputs
            if c=="B":assert preflight[c+"_"+w["call"]]["grid"]["grid_derived_visual_tokens"]>2016,"HIGHER_DETAIL_NOT_EFFECTIVE"
    # Tiny parser safety checks only; no visual fixtures or model warmups.
    b_schema=read(OUT/CONDITIONS["B"]/"schema.json")
    safety={"fence_is_strict_invalid":not validation('```json\n{"status":"NO_CONFIRMED_EVENT","events":[],"notes":""}\n```',b_schema,["F0001"],"B")["strict"]["full_valid"],"invalid_never_no_event":validation('bad',b_schema,["F0001"],"B")["strict"]["classification"]=="INVALID_MODEL_OUTPUT","missing_events_reported":bool(validation('```json\n{"status":"NO_CONFIRMED_EVENT","notes":""}\n```',b_schema,["F0001"],"B")["qualitative_extraction"]["body_schema_errors"])}
    assert all(safety.values())
    save(OUT/"cpu_preflight.json",{"inputs":preflight,"parser_checks":safety,"higher_detail_rationale":"2x spatial-pixel cap; CPU processor input confirmed. Historical baseline load peak6.744GiB / inference6.197GiB on16GiB GPU suggests headroom, NOT a guaranteed higher-detail memory bound. Actual resource gates stay active.","new_model_calls":0})
    components={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),ROOT/"src/memory_graph/pass_t/phase2b/local_vlm/nf4.py",ROOT/"src/memory_graph/pass_t/phase2b/local_vlm/qwen_contract.py",ROOT/original["model_assets_manifest"]]}
    for c in ("B","C"):
        for n in ("configuration.json","prompt.json","schema.json"):
            p=OUT/CONDITIONS[c]/n;components[p.relative_to(ROOT).as_posix()]=sha(p)
    save(OUT/"freeze.json",{"utc":utc(),"components":components,"maximum_new_generations":4,"order":["B_A","B_B","C_A","C_B"],"source_authorization_sha256":sha(Path('C:/Users/smile/.codex/attachments/04f105aa-5aa2-4a5f-b83d-a51147ee1bf5/貼上的文字.txt')),"baseline_reexecuted":False,"future_models_authorized":False,"evaluation_rubric":["target","state","temporal","event","wrong_target","uncertainty","structure"],"qualitative_extraction_policy":"Exact single outer fence body may be JSON-read in a separately labeled non-authoritative record; never feeds strict validation or repairs missing fields"})
    print(json.dumps({"frozen":sha(OUT/"freeze.json"),"cpu_preflight":preflight,"parser_checks":safety}),flush=True)

def verify():
    f=read(OUT/"freeze.json")
    assert all(sha(ROOT/p)==h for p,h in f["components"].items()),"FROZEN_COMPONENT_CHANGED"
    return f

def worker(condition):
    verify();dest=OUT/CONDITIONS[condition];cfg=read(dest/"configuration.json")
    os.environ.update(PASS_T_LOCAL_RUNTIME_APPROVAL="true",HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false")
    cache=dest/"runtime_cache";cache.mkdir(exist_ok=True)
    for k in ("HF_HOME","TORCH_HOME","TMP","TEMP","TMPDIR","TRITON_CACHE_DIR"):os.environ[k]=str(cache)
    from memory_graph.pass_t.phase2b.local_vlm.nf4 import QwenNF4Runtime
    from memory_graph.pass_t.phase2b.local_vlm.catalog import SPECS
    from memory_graph.pass_t.phase2b.local_vlm.qwen_contract import processor_size,grid_accounting
    from memory_graph.pass_t.phase2b.local_vlm.video_array_bridge import tensor_record
    from PIL import Image
    class Runtime(QwenNF4Runtime):
        def preprocess(self,envelope):
            verify();w=envelope["window"];p=read(dest/"prompt.json");schema=read(dest/"schema.json")
            images=[];content=[]
            for i,s in enumerate(w["frames"]):
                assert sha(ROOT/s["source_path"])==s["recorded_source_png_sha256"]
                with Image.open(ROOT/s["source_path"]) as im:images.append(im.convert("RGB"))
                content.extend([{"type":"text","text":f'Image {i+1} corresponds exactly to frame alias {s["supplied_alias"]}.'},{"type":"image","image":images[-1]}])
            content.append({"type":"text","text":p["task"]+"\nRequired JSON schema:\n"+json.dumps(schema,ensure_ascii=False,sort_keys=True)})
            rendered=self.processor.apply_chat_template([{"role":"system","content":p["system"]},{"role":"user","content":content}],tokenize=False,add_generation_prompt=True)
            rendered_sha=hashlib.sha256(rendered.encode()).hexdigest()
            if condition=="B":assert rendered_sha==cfg["expected_baseline_rendered_sha256"][w["window"]]
            self.processor.image_processor.size=processor_size(cfg["processor_max_pixels"])
            self.processor.image_processor.min_pixels=3136;self.processor.image_processor.max_pixels=cfg["processor_max_pixels"]
            pixel_kwargs={"max_pixels":cfg["processor_max_pixels"],"min_pixels":3136} if condition=="B" else {}
            inputs=self.processor(text=[rendered],images=images,padding=True,return_tensors="pt",device="cpu",**pixel_kwargs)
            grid=grid_accounting(inputs);expected=read(OUT/"cpu_preflight.json")["inputs"][condition+"_"+w["call"]]
            assert grid==expected["grid"] and rendered_sha==expected["rendered_sha256"],"PROCESSOR_PREFLIGHT_MISMATCH"
            receipt={"rendered_text":rendered,"rendered_sha256":rendered_sha,"prompt_sha256":sha(dest/"prompt.json"),"schema_sha256":sha(dest/"schema.json"),"frames":w["frames"],"processor":self.processor.image_processor.to_dict(),"grid":grid,"tensor_records":{k:tensor_record(v) for k,v in inputs.items()},"representation":"EIGHT_INDEPENDENT_CHRONOLOGICAL_IMAGES_NOT_NATIVE_VIDEO"}
            save(dest/f'call_{w["call"]}_input.json',receipt)
            return inputs,{"grid":grid,"input_receipt_sha256":sha(dest/f'call_{w["call"]}_input.json')}
    deployment={"approved":True,"processor_max_pixels":cfg["processor_max_pixels"],"generation_timeout_seconds":cfg["generation_timeout_seconds"],"asset_audit_path":str(ROOT/cfg["model_assets_manifest"]),"scratch_path":str(cache),"video_input_mode":"NATIVE_VIDEO_ARRAY_DISABLED"}
    try:
        runtime=Runtime(SPECS["qwen_nf4"],deployment,ROOT/cfg["model_snapshot"],None)
        save(dest/"model_load.json",runtime.health())
        for w in cfg["windows"]:
            verify();call=w["call"]
            assert len(list(OUT.glob('condition_*/call_*_attempt.json')))<4,"GLOBAL_BUDGET_EXHAUSTED"
            save(dest/f"call_{call}_attempt.json",{"utc":utc(),"condition":condition,"window":w["window"],"freeze_sha256":sha(OUT/"freeze.json"),"max_global_calls":4})
            try:
                result=runtime.generate({"window":w,"generation":cfg["generation"]})
                raw=result.pop("raw_output");rawsave(dest/f"call_{call}_raw.txt",raw)
                save(dest/f"call_{call}_execution.json",{**result,"completed_utc":utc(),"window":w["window"],"condition":condition,"raw_sha256":sha(dest/f"call_{call}_raw.txt")})
                save(dest/f"call_{call}_validation.json",validation(raw,read(dest/"schema.json"),[s["supplied_alias"] for s in w["frames"]],condition))
                print("COMPLETED "+condition+"_"+call,flush=True)
            except Exception as e:
                save(dest/f"call_{call}_failure.json",{"utc":utc(),"error":str(e),"traceback":traceback.format_exc(),"retry":False});raise
    except Exception as e:
        save(dest/"worker_failure.json",{"utc":utc(),"error":str(e),"traceback":traceback.format_exc()});raise

def resources():
    import psutil
    gpu=subprocess.check_output(["nvidia-smi","--query-gpu=memory.free,memory.used","--format=csv,noheader,nounits"],text=True).strip().splitlines()[0]
    free,used=[float(x.strip())/1024 for x in gpu.split(',')]
    return {"free_gpu_gib":free,"used_gpu_gib":used,"free_ram_gib":psutil.virtual_memory().available/2**30}

def run():
    verify();save(OUT/"execution_started.json",{"utc":utc(),"maximum_generations":4,"retry":0})
    import psutil
    for condition in ("B","C"):
        dest=OUT/CONDITIONS[condition];cfg=read(dest/"configuration.json");r=resources()
        save(dest/"hardware_before.json",r)
        if r["free_gpu_gib"]<10 or r["free_ram_gib"]<8:
            save(dest/"condition_summary.json",{"status":"NOT_EXECUTED_HEADROOM_GATE","resources":r,"not_executed":["A","B"]});continue
        reason=None;max_rss=0;max_gpu=r["used_gpu_gib"];last=0;t0=time.monotonic()
        with (dest/"runtime.log").open("xb") as log:
            proc=subprocess.Popen([sys.executable,"-X","utf8","-B",str(Path(__file__)),"worker","--condition",condition],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            while proc.poll() is None:
                time.sleep(1)
                try:
                    ps=psutil.Process(proc.pid)
                    rss=sum(p.memory_info().rss for p in [ps]+ps.children(recursive=True) if p.is_running())/2**30
                except psutil.NoSuchProcess:
                    if proc.poll() is not None:break
                    rss=0
                max_rss=max(max_rss,rss);elapsed=time.monotonic()-t0
                if rss>20 or psutil.virtual_memory().available<2*2**30:reason="RAM_GATE"
                if not (dest/"model_load.json").exists() and elapsed>cfg["load_timeout_seconds"]:reason="LOAD_TIMEOUT"
                if elapsed>cfg["load_timeout_seconds"]+2*cfg["request_timeout_seconds"]:reason="CONDITION_TIMEOUT"
                for c in ("A","B"):
                    p=dest/f"call_{c}_attempt.json"
                    if p.exists() and not (dest/f"call_{c}_execution.json").exists() and time.time()-p.stat().st_mtime>cfg["request_timeout_seconds"]:reason="CALL_TIMEOUT_"+c
                if elapsed-last>=3:
                    r=resources();max_gpu=max(max_gpu,r["used_gpu_gib"]);last=elapsed
                    if r["used_gpu_gib"]>14.5:reason="GPU_GATE"
                if reason:
                    try:
                        ps=psutil.Process(proc.pid)
                        for child in ps.children(recursive=True):child.terminate()
                        ps.terminate()
                    except psutil.NoSuchProcess:pass
                    proc.wait(timeout=20);break
            code=proc.wait()
        save(dest/"condition_summary.json",{"status":"COMPLETED" if code==0 and not reason else "STOPPED","worker_exit_code":code,"guard_stop":reason,"wall_s":time.monotonic()-t0,"peak_owned_tree_rss_gib":max_rss,"peak_sampled_global_gpu_used_gib":max_gpu,"gpu_sampling_interval_s":3,"completed":[c for c in ("A","B") if (dest/f"call_{c}_execution.json").exists()],"not_executed":[c for c in ("A","B") if not (dest/f"call_{c}_attempt.json").exists()],"retry":0})
        print("CONDITION_FINISHED "+condition,flush=True)
    save(OUT/"execution_summary.json",{"utc":utc(),"conditions":{c:read(OUT/n/"condition_summary.json") for c,n in CONDITIONS.items()},"attempt_count":len(list(OUT.glob('condition_*/call_*_attempt.json'))),"max_generations":4,"new_model_inference":False,"graph_writes":0})
    print((OUT/"execution_summary.json").read_text(encoding="utf8"),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','run','worker']);p.add_argument('--condition',choices=['B','C']);a=p.parse_args()
    if a.mode=='prepare':prepare()
    elif a.mode=='run':run()
    elif a.condition:worker(a.condition)
    else:p.error('worker requires --condition')
