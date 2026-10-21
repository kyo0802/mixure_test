"""Small single-image perception batch; existing loaders, no benchmark edits."""
import gc
import json
from pathlib import Path
import time
import cv2
import numpy as np
from .adapters import sha
from .target_surface import prompt,parse,pixels


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf8") as f:json.dump(value,f,ensure_ascii=False,indent=2)


def localize(root,frames,output,query="smartphone",reference=None,canvas=None):
    from memory_graph.experiments.three_vlm_adapters import QwenFullAdapter
    from memory_graph.experiments.observation_interface import AdapterValue
    from memory_graph.pass_t.phase2b.local_vlm.qwen_contract import grid_accounting
    from memory_graph.pass_t.phase2b.local_vlm.video_array_bridge import tensor_record
    from PIL import Image
    adapter=QwenFullAdapter(root)
    settings=dict(model_path=".models/Qwen2.5-VL-7B-Instruct",processor_max_pixels=canvas[0]*canvas[1] if canvas else 786432)
    pending=[]
    for frame in frames:
        folder=output/"perception"/frame["frame_id"]
        if (folder/"raw.txt").exists():
            if not (folder/"generation.json").exists():raise RuntimeError("INCOMPLETE_GENERATION_RECEIPT_NO_RETRY")
            continue
        if (folder/"started.json").exists():raise RuntimeError("INTERRUPTED_GENERATION_NO_AUTOMATIC_RETRY")
        pending.append(frame)
    if not pending:return
    save(output/"inference_scope.json",dict(max_new_generations=len(pending),query=query,
        settings=settings,reference=reference,physical_contact_not_established=True,
        generation=dict(seed=42,max_new_tokens=1200,do_sample=False),
        estimate_gpu_gib=[8,11],gpu_models_sequential=True))
    try:
        health=adapter.load(settings);save(output/"qwen_load.json",health)
        for frame in pending:
            adapter.check_resources(load=False)
            folder=output/"perception"/frame["frame_id"];folder.mkdir(parents=True,exist_ok=True)
            path=root/frame["path"]
            if sha(path)!=frame["sha256"]:raise ValueError("SOURCE_IMAGE_CHANGED")
            image=Image.open(path).convert("RGB")
            if canvas:
                image=image.resize(tuple(canvas),Image.Resampling.LANCZOS)
                image.save(folder/"model_input.png")
            images=[image]
            content=[dict(type="text",text="F0001: current source image."),dict(type="image",image=image)]
            if reference:
                rp=root/reference["path"]
                if sha(rp)!=reference["sha256"]:raise ValueError("REFERENCE_CHANGED")
                ref=Image.open(rp).convert("RGB");images.append(ref)
                content.extend([dict(type="text",text="Optional target appearance reference; not source frame or identity authorization."),dict(type="image",image=ref)])
            content.append(dict(type="text",text=prompt(query,canvas)))
            text=adapter.processor.apply_chat_template([dict(role="system",content="Report only visible evidence. Unknown is permitted. Never invent coordinates for an invisible object."),dict(role="user",content=content)],tokenize=False,add_generation_prompt=True)
            inputs=adapter.processor(text=[text],images=images,padding=True,return_tensors="pt")
            if canvas:
                actual=inputs["image_grid_thw"][0].tolist()
                if actual!=[1,canvas[1]//14,canvas[0]//14]:raise ValueError("PROCESSOR_CANVAS_RESIZED_UNEXPECTEDLY")
            metadata=dict(rendered_text=text,frames=[frame],reference=reference,
                coordinate_contract="MODEL_CANVAS_PIXELS" if canvas else "NORMALIZED_0_1000_OF_SOURCE_F0001",
                model_canvas=canvas,model_input_sha256=sha(folder/"model_input.png") if canvas else frame["sha256"],grid=grid_accounting(inputs),
                tensors={k:tensor_record(v) for k,v in inputs.items()})
            save(folder/"input.json",metadata)
            save(folder/"started.json",dict(maximum_generations=1,frame_id=frame["frame_id"]))
            response=adapter.generate(AdapterValue(inputs,metadata),None,dict(seed=42,max_new_tokens=1200))
            (folder/"raw.txt").write_bytes(response.text.encode("utf8"))
            save(folder/"generation.json",response.metadata)
            parsed,status=parse(response.text,canvas)
            save(folder/"validation.json",status)
            save(folder/"parsed.json",parsed)
            print(json.dumps(dict(frame=frame["frame_id"],stage="LOCALIZED",valid=status["valid"],
                targets=len(parsed["targets"]) if parsed else None,surfaces=len(parsed["surfaces"]) if parsed else None)),flush=True)
            del inputs,response
    finally:
        adapter.close();gc.collect()


def refine(root,frames,output):
    """SAM2.1 image predictor refines proposals, never discovers semantics.

    Intersection with the supplied box/polygon prevents a body mask being
    silently promoted to the model's requested top face. Result remains model
    dependent and UNVERIFIED. No temporal propagation between selected frames.
    """
    import sys
    sys.path[:0]=[str(root/".sam2_official"),str(root/".sam2_deps")]
    import torch
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    from memory_graph.v22.sam_tracking import encode_mask
    if (output/"sam_receipt.json").exists():return
    if torch.cuda.mem_get_info()[0]<4*2**30:raise RuntimeError("SAM_GPU_HEADROOM_REQUIRES_4GIB")
    torch.cuda.reset_peak_memory_stats();started=time.monotonic()
    checkpoint=root/".models/sam2.1_hiera_small.pt"
    predictor=SAM2ImagePredictor(build_sam2("configs/sam2.1/sam2.1_hiera_s.yaml",str(checkpoint),device="cuda"))
    calls=0;accepted=0
    try:
        with torch.inference_mode(),torch.autocast("cuda",dtype=torch.bfloat16):
            for frame in frames:
                folder=output/"perception"/frame["frame_id"]
                if (folder/"refinements.json").exists():continue
                data=json.loads((folder/"parsed.json").read_text(encoding="utf8"))
                records={}
                if data:
                    path=root/frame["path"]
                    if sha(path)!=frame["sha256"]:raise ValueError("SAM_FRAME_HASH_MISMATCH")
                    image=cv2.imread(str(path));height,width=image.shape[:2]
                    predictor.set_image(cv2.cvtColor(image,cv2.COLOR_BGR2RGB))
                    for row in data["targets"]+data["surfaces"]:
                        try:
                            if "bbox" in row:
                                box=np.array(pixels(row["bbox"],width,height,box=True),np.float32)
                                poly=np.array([[box[0],box[1]],[box[2],box[1]],[box[2],box[3]],[box[0],box[3]]])
                            else:
                                poly=np.array(pixels(row["polygon"],width,height),np.float32)
                                box=np.r_[poly.min(axis=0),poly.max(axis=0)]
                        except ValueError as e:records[row["id"]]=dict(accepted=False,reason=str(e));continue
                        allowed=np.zeros((height,width),np.uint8);cv2.fillConvexPoly(allowed,np.rint(poly).astype(np.int32),1)
                        masks,scores,_=predictor.predict(box=box,multimask_output=True)
                        calls+=1
                        ix=int(np.argmax(scores));raw=masks[ix].astype(bool)
                        clipped=raw & allowed.astype(bool)
                        fraction=float(clipped.sum()/max(1,allowed.sum()))
                        ok=bool(clipped.sum()>=16 and fraction>=.08)
                        record=dict(accepted=ok,proposal_coverage=fraction,sam_predicted_iou=float(scores[ix]),
                            semantic_verification=False,clipped_to_model_geometry=True,source_frame_sha256=frame["sha256"])
                        if ok:
                            # Model local IDs are untrusted path components.
                            name="mask_"+__import__('hashlib').sha256(row["id"].encode()).hexdigest()[:16]+".png"
                            path=folder/name;cv2.imwrite(str(path),clipped.astype(np.uint8)*255)
                            record.update(mask_ref=dict(path=str(path.relative_to(root)),sha256=sha(path)),mask_rle=encode_mask(clipped))
                            accepted+=1
                        else:record["reason"]="EMPTY_OR_LOW_COVERAGE_SAM_REFINEMENT"
                        records[row["id"]]=record
                save(folder/"refinements.json",records)
        save(output/"sam_receipt.json",dict(checkpoint_sha256=sha(checkpoint),model="SAM2.1_HIERA_SMALL",
            mask_prompt_calls=calls,accepted_masks=accepted,elapsed_s=time.monotonic()-started,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
            independent_semantic_or_contact_verification=False,temporal_propagation=False))
    finally:
        del predictor
        gc.collect();torch.cuda.empty_cache()
