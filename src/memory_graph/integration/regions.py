"""CPU scene proposals. A named detector extent is NOT a support surface.

All automatic geometries expire at their source frame. No tracker ID or similar
pixel position is used to assert semantic region identity across camera views.
"""
import math
import cv2
import numpy as np
from .adapters import key

REGION_CLASSES = {"table", "desk", "microwave", "shelf", "sofa", "box", "cabinet"}


def scope(video, frame):
    timeline = video["frame_timeline"]
    if not isinstance(frame, int) or not 0 <= frame < len(timeline):
        raise ValueError("REGION_FRAME_OUT_OF_BOUNDS")
    native = timeline[frame]
    if native["index"] != frame:
        raise ValueError("REGION_TIMELINE_INDEX_MISMATCH")
    return dict(video_id=video["video_id"], source_video_sha256=video["source_sha256"],
                source_frame_index=frame, source_time_s=native["source_time_s"],
                native_pts=native["pts"], time_base=video["time_base"])


def box_polygon(bbox):
    x1, y1, x2, y2 = map(float, bbox)
    if not all(math.isfinite(x) for x in (x1,y1,x2,y2)) or x2 <= x1 or y2 <= y1:
        raise ValueError("INVALID_BBOX")
    return [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]


def validate_region(region, video):
    expected = scope(video, region["source_frame_index"])
    if any(region.get(k) != v for k,v in expected.items()):
        raise ValueError("REGION_SOURCE_SCOPE_MISMATCH")
    polygon = np.asarray(region["polygon"], dtype=np.float32)
    if polygon.ndim != 2 or polygon.shape[1] != 2 or len(polygon) < 3 or not np.isfinite(polygon).all():
        raise ValueError("INVALID_REGION_POLYGON")
    if not cv2.isContourConvex(polygon) or cv2.contourArea(polygon) <= 0:
        raise ValueError("REGION_REQUIRES_CONVEX_POLYGON")
    if (polygon[:,0]<0).any() or (polygon[:,1]<0).any() or (polygon[:,0]>video["width"]).any() or (polygon[:,1]>video["height"]).any():
        raise ValueError("REGION_OUT_OF_IMAGE")
    # Until a separately validated tracking contract exists, accept frame-only.
    if region.get("valid_frame_indices") != [expected["source_frame_index"]]:
        raise ValueError("UNSUPPORTED_REGION_PROPAGATION")
    if not region.get("evidence_refs") or not region.get("viewpoint_id"):
        raise ValueError("REGION_EVIDENCE_REQUIRED")
    if region.get("grounding_status") not in {"CANDIDATE", "VERIFIED", "UNKNOWN", "CONTRADICTED"}:
        raise ValueError("INVALID_REGION_STATUS")
    if region["grounding_status"] == "VERIFIED":
        att = region.get("verification", {})
        if att.get("origin") not in {"INDEPENDENT_GEOMETRIC_MEASUREMENT", "EXPLICIT_REGION_REVIEW"} or not att.get("refs"):
            raise ValueError("REGION_VERIFICATION_EVIDENCE_REQUIRED")
    return region


def propose_regions(image, video, frame, observations, image_ref):
    """Detector extents + optional interior convex edge patch, all candidates.

    Edges add pixel evidence, not semantic/planarity/contact verification. No
    assumption that the upper fraction of a microwave bbox is its top surface.
    """
    if image.shape[:2] != (video["height"], video["width"]):
        raise ValueError("SOURCE_IMAGE_DIMENSION_MISMATCH")
    base = scope(video, frame)
    regions=[]
    for obs in observations:
        if obs["source"] != "CV" or obs["object_category"] not in REGION_CLASSES or not obs.get("bbox"):
            continue
        if obs["source_video_sha256"] != base["source_video_sha256"] or obs["source_frame_indices"] != [frame] or obs["source_times_s"] != [base["source_time_s"]]:
            continue
        if obs["visibility"] != "VISIBLE":
            continue
        x1,y1,x2,y2=obs["bbox"]
        x1,y1=max(0,int(x1)),max(0,int(y1))
        x2,y2=min(video["width"],int(x2)),min(video["height"],int(y2))
        if x2-x1<12 or y2-y1<12:continue
        label=obs["object_category"]
        common=dict(**base, region_category=label, visibility="DETECTOR_VISIBLE_PROPOSAL",
            viewpoint_id="view:"+key(base["source_video_sha256"],frame),
            valid_frame_indices=[frame], validity="SOURCE_FRAME_ONLY", semantic_region_id=None,
            grounding_status="CANDIDATE", evidence_refs=[image_ref,*obs["evidence_refs"]],
            source_observation_id=obs["observation_id"],
            provenance=dict(origin="DETECTOR_PLUS_SOURCE_PIXELS", detector=obs["provenance"],
                confidence=obs.get("detector_confidence"), physical_surface_verified=False))
        regions.append(validate_region(dict(**common,region_id="region:"+key(obs["observation_id"],"extent"),
            region_label=label+" detected extent",geometry_kind="DETECTOR_BBOX",
            polygon=box_polygon([x1,y1,x2,y2]),usable_surface=False,
            limitations=["Detector semantic label may be wrong", "Extent includes background and object sides", "Not a usable support surface"]),video))
        crop=image[y1:y2,x1:x2]
        gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
        edges=cv2.Canny(cv2.GaussianBlur(gray,(5,5),0),60,150)
        contours,_=cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        patches=[]
        for contour in contours:
            area=cv2.contourArea(contour)
            if not .12*crop.shape[0]*crop.shape[1] <= area <= .9*crop.shape[0]*crop.shape[1]:continue
            poly=cv2.approxPolyDP(contour,.025*cv2.arcLength(contour,True),True)
            if len(poly)!=4 or not cv2.isContourConvex(poly):continue
            patches.append((area,poly[:,0,:]))
        if patches:
            poly=max(patches,key=lambda x:x[0])[1]+np.array([x1,y1])
            regions.append(validate_region(dict(**common,region_id="region:"+key(obs["observation_id"],"patch"),
                region_label=label+" planar-looking patch candidate", geometry_kind="EDGE_QUADRILATERAL",
                polygon=poly.tolist(),usable_surface=False,surface_candidate=True,
                limitations=["Convex image edges do not establish a 3D plane", "May be front face, background or texture", "Not verified table/microwave top"]),video))
    return regions


def viewpoint_change(previous, current):
    """Diagnostic only; never permits geometry reuse, even when shift is small."""
    a=cv2.resize(cv2.cvtColor(previous,cv2.COLOR_BGR2GRAY),(320,180)).astype(np.float32)
    b=cv2.resize(cv2.cvtColor(current,cv2.COLOR_BGR2GRAY),(320,180)).astype(np.float32)
    shift,response=cv2.phaseCorrelate(a,b)
    displacement=float(np.linalg.norm(shift))
    return dict(status="VIEW_CHANGE_OR_SCENE_MOTION" if displacement>4 or response<.15 else "NO_LARGE_GLOBAL_SHIFT_ESTIMATED",
                displacement_px_at_320_width=displacement, correlation_response=float(response),
                geometry_reuse_authorized=False, limitation="Object motion/parallax can affect estimate; not a camera pose")
