"""Bounded exact-PNG detector/pose feasibility spike. Never reads GT or VLM outputs.

The unavailable contact/support primitives are explicit nulls, never inferred
from motion/pose/boxes. This is an investigation, not a PICKUP classifier.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import sys
import time
from collections import Counter
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "artifacts/pass_t/phase3/signal_spike_v1"
BUNDLE = ROOT / "artifacts/pass_t/phase2b/v1d_pilot_runs/eb9435cf0102631e0456f3a05232d4eebbde5127cb480b6042ff584f244c109f/frozen_bundle.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(name, data):
    path = OUT / name
    if path.exists():
        raise RuntimeError(f"Refusing to overwrite spike artifact: {path}")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def iou(a, b):
    x = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    y = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = x*y
    return inter / max(1e-9, (a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)


def pixel_flow(previous, current, boxes0, boxes1, cfg):
    """Background transform and dense-enough sparse object residuals; no state claims."""
    import cv2
    import numpy as np
    g0, g1 = [cv2.cvtColor(x, cv2.COLOR_BGR2GRAY) for x in (previous, current)]
    points = cv2.goodFeaturesToTrack(g0, cfg["max_corners"], cfg["quality_level"], cfg["min_distance_px"])
    if points is None or len(points) < 4:
        return {"reliable": False, "reason": "INSUFFICIENT_FEATURES"}, []
    q, ok1, _ = cv2.calcOpticalFlowPyrLK(g0, g1, points, None, winSize=(31,31), maxLevel=4)
    if q is None:
        return {"reliable": False, "reason": "FLOW_FAILED"}, []
    back, ok2, _ = cv2.calcOpticalFlowPyrLK(g1, g0, q, None, winSize=(31,31), maxLevel=4)
    if back is None:
        return {"reliable": False, "reason": "BACKWARD_FLOW_FAILED"}, []
    good = (ok1[:,0] == 1) & (ok2[:,0] == 1) & (np.linalg.norm(points[:,0]-back[:,0], axis=1) <= cfg["fb_error_px"])
    a, b = points[good,0], q[good,0]
    bg = np.ones(len(a), dtype=bool)
    for pts, boxes in ((a, boxes0), (b, boxes1)):
        for x1,y1,x2,y2 in boxes:
            bg &= ~((pts[:,0]>=x1-8)&(pts[:,0]<=x2+8)&(pts[:,1]>=y1-8)&(pts[:,1]<=y2+8))
    if int(bg.sum()) < 4:
        return {"reliable": False, "reason": "INSUFFICIENT_BACKGROUND_FEATURES", "background_points": int(bg.sum())}, []
    h, inlier = cv2.findHomography(a[bg], b[bg], cv2.RANSAC, cfg["ransac_px"])
    if h is None:
        return {"reliable": False, "reason": "HOMOGRAPHY_FAILED"}, []
    projected = cv2.perspectiveTransform(a[:,None,:], h)[:,0]
    residual = b-projected
    ni = int(inlier.sum())
    ratio = ni/int(bg.sum())
    med = float(np.median(np.linalg.norm(residual[bg][inlier[:,0].astype(bool)],axis=1)))
    reliable = ni>=cfg["min_inliers"] and ratio>=cfg["min_inlier_ratio"] and med<=cfg["max_median_reprojection_px"]
    return {"reliable": bool(reliable), "method": "LK_RANSAC_HOMOGRAPHY", "background_points": int(bg.sum()), "inliers": ni, "inlier_ratio": ratio, "median_reprojection_px": med, "homography": h.tolist(), "limitation": "2D background fit; table parallax/rotation/local motion may remain. Not world motion."}, [(aa.tolist(),bb.tolist(),rr.tolist()) for aa,bb,rr in zip(a,b,residual)]


def main():
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from memory_graph.config import DetectorConfig
    from memory_graph.models import FrameInfo
    from memory_graph.perception.detector import Detector
    from memory_graph.perception.runtime import configure_ultralytics
    configure_ultralytics()
    from ultralytics import YOLO
    import torch

    started = time.perf_counter()
    cfg = read(OUT / "PREREGISTRATION.json")
    prereg = sha(OUT / "PREREGISTRATION.json")
    if (OUT / "COMPUTED_STATES.json").exists():
        raise RuntimeError("Previous computed artifact exists. Do not overwrite or silently rerun.")
    save("PREREGISTRATION_RECEIPT.json", {"sha256": prereg, "recorded_utc": datetime.now(timezone.utc).isoformat(), "threshold_revisions": 0, "before_image_inference": True})
    windows = [w for w in read(BUNDLE)["protocol"]["draft"]["windows"] if set(w["original_pack_ids"]) & set(cfg["scope"])]
    assert len(windows) == 2 and all(len(w["selected"])==8 for w in windows)
    # Guard historical sources, current implementation, prompt/policies, and all input PNGs.
    protected = {}
    for baseline in ("PRESERVATION_BASELINE.json", "ARTIFACT_PRESERVATION_BASELINE.json"):
        bp = ROOT / "WORKSPACE/Pass_T/Phase3_Observation_Capability_Audit_20261015" / baseline
        protected[str(bp.relative_to(ROOT))] = sha(bp)
    for folder in (ROOT / "src", ROOT / "configs", ROOT / "artifacts/pass_t/phase2b/human_adjudicated_error_analysis/20261015_pilot_v1"):
        for p in folder.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                protected[str(p.relative_to(ROOT))] = sha(p)
    for w in windows:
        for s in w["selected"]:
            p = ROOT/s["source_path"]
            actual = sha(p)
            assert actual == s["recorded_source_png_sha256"], str(p)
            protected[s["source_path"]] = actual
    save("PRESERVATION_BEFORE.json", protected)
    det = Detector(DetectorConfig(model=str(ROOT/cfg["detector"]["model"]), confidence=cfg["detector"]["conf"], image_size=cfg["detector"]["imgsz"]))
    pose = YOLO(str(ROOT/cfg["pose"]["model"]))
    device = det.device
    if device != "cpu":
        torch.cuda.reset_peak_memory_stats()
    all_frames, sheets = [], {}
    for w in windows:
        name = next(n for n in w["original_pack_ids"] if n in cfg["scope"])
        video = name.split("__")[0]
        olddet_path = ROOT/f"outputs_v292/{video}/perception/yolo_detections.json"
        oldtrack_path = ROOT/f"outputs_v292/{video}/perception/tracks.json"
        sam_path = ROOT/f"outputs_v292/{video}/sam/sam_continuity_log.json"
        auth_path = ROOT/f"outputs/identity_rebuild/development/runs_final/{video}/authorized_rows.json"
        olddet, oldtracks, sam, auth = [read(p) for p in (olddet_path, oldtrack_path, sam_path, auth_path)]
        if isinstance(oldtracks, dict):
            oldtracks = oldtracks.get("tracks", [])
        masks = {}
        for seg in sam.get("segments", []):
            for fr, mask in seg.get("masks_rle", {}).items():
                masks.setdefault(int(str(fr).split(":")[0]), []).append(mask)
        tiles, prior, prior_objects, counter = [], None, [], 0
        for s in w["selected"]:
            frame = cv2.imread(str(ROOT/s["source_path"]))
            assert frame is not None and frame.shape[:2] == (720,1280)
            info = FrameInfo(frame_index=s["source_frame_index"], timestamp=s["native_source_pts_s"])
            t0 = time.perf_counter()
            detections = det.detect(frame, info)
            ds = [asdict(d) if is_dataclass(d) else d.model_dump(mode="json") for d in detections]
            pr = pose.predict(frame, conf=cfg["pose"]["conf"], imgsz=cfg["pose"]["imgsz"], device=device, verbose=False)[0]
            persons = []
            if pr.keypoints is not None:
                for j, kp in enumerate(pr.keypoints.data.cpu().tolist()):
                    persons.append({"person_index": j, "bbox": pr.boxes.xyxy[j].cpu().tolist(), "confidence": float(pr.boxes.conf[j]), "keypoints_xy_conf": kp})
            wrists = [{"person_index": p["person_index"], "keypoint_index": k, "xy": p["keypoints_xy_conf"][k][:2], "confidence": p["keypoints_xy_conf"][k][2]} for p in persons for k in cfg["pose"]["wrists_zero_based"] if p["keypoints_xy_conf"][k][2]>=cfg["pose"]["keypoint_conf"]]
            relevant = [d for d in ds if d["class_name"] in ("cell phone", "sports ball", "person")]
            camera, flow = ({"reliable": False, "reason": "FIRST_FRAME"}, []) if prior is None else pixel_flow(prior["image"], frame, prior["boxes"], [d["bbox"] for d in relevant], cfg["camera"])
            objects = []
            used_previous = set()
            for d in [d for d in ds if d["class_name"] in ("cell phone", "sports ball")]:
                bb = d["bbox"]
                choices = [(j,o) for j,o in enumerate(prior_objects) if o["class_name"]==d["class_name"] and iou(o["bbox"],bb)>=cfg["local_consistency"]["min_iou"] and s["native_source_pts_s"]-o["native_source_pts_s"]<=cfg["local_consistency"]["max_gap_seconds"]]
                # Refuse merges: both directions must be unique within this sample.
                unique = len(choices)==1 and choices[0][0] not in used_previous
                if unique:
                    po = choices[0][1]
                    n = sum(x["class_name"]==po["class_name"] and iou(x["bbox"],po["bbox"])>=cfg["local_consistency"]["min_iou"] for x in ds)
                    unique = n==1
                if unique:
                    used_previous.add(choices[0][0])
                    local = po["local_id"]
                else:
                    counter += 1
                    local = f"{name}:candidate_{counter:03d}"
                distances = []
                for wrist in wrists:
                    x,y = wrist["xy"]
                    distance = float(np.hypot(max(bb[0]-x,0,x-bb[2]),max(bb[1]-y,0,y-bb[3])))
                    distances.append({**wrist,"bbox_distance_px":distance})
                objflow = []
                if unique:
                    pb = po["bbox"]
                    objflow = [r for a,b,r in flow if pb[0]<=a[0]<=pb[2] and pb[1]<=a[1]<=pb[3] and bb[0]<=b[0]<=bb[2] and bb[1]<=b[1]<=bb[3]]
                residual = float(np.median(np.linalg.norm(objflow,axis=1))) if len(objflow)>=cfg["motion"]["min_object_flow_points"] and camera["reliable"] else None
                motion = "UNKNOWN" if residual is None else ("IMAGE_STATIONARY_PROXY" if residual<=cfg["motion"]["stationary_max_residual_px"] else "IMAGE_MOVING_PROXY" if residual>=cfg["motion"]["moving_min_residual_px"] else "INDETERMINATE_IMAGE_MOTION")
                objects.append({**d, "local_id":local, "native_source_pts_s":s["native_source_pts_s"], "tentative_previous_association": unique, "association_kind":"SAME_CLASS_UNIQUE_IOU_ONLY_UNVERIFIED", "persistent_entity":None, "physical_state":"UNKNOWN", "missing_primitives":["INDEPENDENT_SUPPORT_BOUNDARY", "GRIP_CONTACT", "SURFACE_SEPARATION"], "support_boundary_confidence":None,"grip_contact_confidence":None,"surface_separation_confidence":None,"wrists":distances, "object_flow_points":len(objflow),"camera_relative_residual_px":residual,"image_motion_proxy":motion})
            exacttracks = [{"track_id": t.get("track_id"), "class": t.get("detector_class"), "observations": [o for o in t.get("observations",[]) if o.get("frame_index",o.get("frame"))==s["source_frame_index"]]} for t in oldtracks]
            exacttracks = [t for t in exacttracks if t["observations"]]
            exactauth = [a for a in auth if a.get("frame",a.get("frame_index"))==s["source_frame_index"]]
            row = {"window":name, **s, "verified_png_sha256":sha(ROOT/s["source_path"]),"width":1280,"height":720,"detections":ds,"candidates":objects,"pose_persons":persons,"confident_wrists":wrists,"camera":camera,"mask_references_exact_only":[{"path":str(sam_path.relative_to(ROOT)),"source_frame":s["source_frame_index"],"encoding":"RLE","mask":m,"identity_authority":"NONE_LEGACY_MASK"} for m in masks.get(s["source_frame_index"],[])],"legacy_exact_tracks":exacttracks,"current_guard_exact_rows":exactauth,"current_guard_identity_authorized":any(a.get("identity_authorized",False) for a in exactauth),"missing_phone_detection":not any(d["class_name"]=="cell phone" for d in ds),"missing_ball_detection":not any(d["class_name"]=="sports ball" for d in ds),"missingness_meaning":"NO_DETECTION_NOT_ABSENCE", "elapsed_detection_pose_s":time.perf_counter()-t0}
            all_frames.append(row)
            image = Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(image)
            for obj in objects:
                color = "lime" if obj["class_name"]=="cell phone" else "orange"
                draw.rectangle(obj["bbox"],outline=color,width=4)
                draw.text((obj["bbox"][0],max(0,obj["bbox"][1]-18)), f'{obj["local_id"].split(":")[-1]} {obj["class_name"]} {obj["confidence"]:.2f}', fill=color)
            for p in persons:
                for k in (7,8,9,10):
                    x,y,c = p["keypoints_xy_conf"][k]
                    if c>=cfg["pose"]["keypoint_conf"]:
                        draw.ellipse((x-5,y-5,x+5,y+5), fill="cyan")
            # Overlay only true exact-frame SAM masks, visibly separate from detector identities.
            for m in masks.get(s["source_frame_index"],[]):
                binary = np.zeros(int(np.prod(m["shape"])),dtype=np.uint8)
                for start,length in zip(m["starts"],m["lengths"]):
                    binary[start:start+length]=1
                binary=binary.reshape(m["shape"])
                if binary.shape==(720,1280):
                    arr=np.array(image)
                    arr[binary.astype(bool)]=(arr[binary.astype(bool)]*.65+np.array([255,0,255])*.35).astype(np.uint8)
                    image=Image.fromarray(arr)
            tile = Image.new("RGB", (640,440),"#111111")
            tile.paste(image.resize((640,360)),(0,0))
            td=ImageDraw.Draw(tile)
            td.text((8,365),f'{s["supplied_alias"]} / {s["source_frame_id"]} / PTS {s["native_source_pts_s"]:.6f}',fill="white")
            td.text((8,383),f'phone={sum(d["class_name"]=="cell phone" for d in ds)} ball={sum(d["class_name"]=="sports ball" for d in ds)} pose={len(persons)} wrist={len(wrists)} cam_fit={camera["reliable"]}',fill="white")
            td.text((8,401),"ALL PHYSICAL STATES UNKNOWN / local IDs tentative",fill="yellow")
            td.text((8,419),"magenta: exact legacy SAM only; NOT identity binding",fill="white")
            tiles.append(tile)
            prior={"image":frame,"boxes":[d["bbox"] for d in relevant]}
            prior_objects=objects
        sheet=Image.new("RGB",(1280,1760),"black")
        for i,tile in enumerate(tiles):
            sheet.paste(tile,((i%2)*640,(i//2)*440))
        sheets[name]=sheet
    # Seal ALL runtime observations for BOTH windows before any external human comparison.
    save("COMPUTED_STATES.json", {"preregistration_sha256":prereg,"frames":all_frames,"human_data_read":False,"qwen_calls":0,"interpretation":"Development feasibility, no physical state producer proven"})
    save("COMPUTED_STATES_RECEIPT.json", {"computed_sha256":sha(OUT/"COMPUTED_STATES.json"),"saved_utc":datetime.now(timezone.utc).isoformat(),"human_comparison_permitted_after_this_receipt":True,"runtime_never_reads_human_data":True})
    for name,sheet in sheets.items():
        sheet.save(OUT/f"{name}_contact_sheet.png")
    summaries={}
    for name in cfg["scope"]:
        rows=[r for r in all_frames if r["window"]==name]
        summaries[name]={"frames":len(rows),"phone_frames":sum(not r["missing_phone_detection"] for r in rows),"ball_frames":sum(not r["missing_ball_detection"] for r in rows),"pose_frames":sum(bool(r["pose_persons"]) for r in rows),"wrist_frames":sum(bool(r["confident_wrists"]) for r in rows),"reliable_camera_pairs":sum(r["camera"]["reliable"] for r in rows),"local_candidate_ids":len({o["local_id"] for r in rows for o in r["candidates"]}),"physical_states":dict(Counter(o["physical_state"] for r in rows for o in r["candidates"])),"exact_masks_frames":sum(bool(r["mask_references_exact_only"]) for r in rows),"guard_authorized_frames":sum(r["current_guard_identity_authorized"] for r in rows)}
    elapsed=time.perf_counter()-started
    save("RUN_RECEIPT.json", {"script_sha256":sha(__file__),"preregistration_sha256":prereg,"bundle_sha256":sha(BUNDLE),"model_hashes":{n:sha(ROOT/n) for n in (cfg["detector"]["model"],cfg["pose"]["model"])},"versions":{n:importlib.metadata.version(n) for n in ("ultralytics","torch","opencv-python")},"device":device,"elapsed_s":elapsed,"torch_peak_allocated_bytes":torch.cuda.max_memory_allocated() if device!="cpu" else None,"torch_peak_reserved_bytes":torch.cuda.max_memory_reserved() if device!="cpu" else None,"summary":summaries,"threshold_revisions":0,"qwen_calls":0,"graph_writes":0,"source_video_decodes":0,"pose_download":{"url":"https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n-pose.pt","bytes":(ROOT/cfg["pose"]["model"]).stat().st_size},"preservation":{"checked":len(protected),"mismatches":[p for p,h in protected.items() if sha(ROOT/p)!=h]}})
    print(json.dumps({"summary":summaries,"elapsed_s":elapsed,"out":str(OUT)},indent=2))


if __name__ == "__main__":
    main()
