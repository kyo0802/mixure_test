"""Spatial evidence within TemporalMemory; no event confirmation shortcuts."""
import math
import cv2
import numpy as np
from .adapters import key
from .regions import box_polygon, validate_region, REGION_CLASSES

RELATIONS={"INSIDE_REGION","OVERLAPS_REGION","NEAR_REGION","ABOVE_REGION",
           "POSSIBLY_ON_SURFACE","ON_SURFACE","UNKNOWN"}


def authorized(obs):
    return (obs.get("source")=="CV" and bool(obs.get("authorized_entity_id"))
        and bool(obs.get("identity_authorization"))
        and obs.get("authorization_validation")=="VERIFIED_FINAL_LEDGER_REPLAY")


def same_frame(obs, region):
    return (obs["source_video_sha256"]==region["source_video_sha256"]
        and obs["video_id"]==region["video_id"]
        and obs["source_frame_indices"]==[region["source_frame_index"]]
        and obs["source_times_s"]==[region["source_time_s"]]
        and region["valid_frame_indices"]==obs["source_frame_indices"])


def support_measurement(obs, region, cue):
    """Separate explicit independent contact measurement; never a VLM claim.

    The current detector pipeline supplies no such measurements. This interface
    accepts upstream sensor/contact measurements or explicit reviewed contact,
    with exact observation + region binding and provenance. Tests use mock refs.
    """
    return bool(cue and cue.get("origin") in {"INDEPENDENT_CONTACT_MEASUREMENT","EXPLICIT_CONTACT_REVIEW"}
        and cue.get("observation_id")==obs["observation_id"]
        and cue.get("region_id")==region["region_id"]
        and cue.get("source_video_sha256")==obs["source_video_sha256"]
        and cue.get("source_frame_index")==region["source_frame_index"]
        and cue.get("source_time_s")==region["source_time_s"] and cue.get("refs")
        and cue.get("state") in {"RESTING_CONTACT","HELD_ABOVE","NOT_ON_SURFACE"})


def relate(obs, region, cue=None):
    record=dict(observation_id="location:"+key(obs["observation_id"],region["region_id"]),
        video_id=obs["video_id"],source_video_sha256=obs["source_video_sha256"],
        source_frame_index=region["source_frame_index"],source_time_s=region["source_time_s"],
        native_pts=region["native_pts"],object_observation_id=obs["observation_id"],
        object_category=obs["object_category"],object_candidate_id=obs["object_instance_candidate"],
        persistent_entity_id=obs["authorized_entity_id"] if authorized(obs) else None,
        identity_evidence=obs.get("identity_authorization") if authorized(obs) else None,
        region_id=region["region_id"],region_label=region["region_label"],
        spatial_relation="UNKNOWN",grounding_status="UNKNOWN",projection_relation="UNKNOWN",
        relation_scope="IMAGE_SPACE_ONLY",physical_support_verified=False,
        object_evidence_refs=obs["evidence_refs"],region_evidence_refs=region["evidence_refs"],
        association_evidence_refs=[],reason_codes=[],
        validity="OBSERVED_FRAME_ONLY_NOT_CURRENT_PRESENCE",provenance={"method":"convex_image_geometry_v1"})
    if not same_frame(obs,region):
        record["reason_codes"]=["REGION_FRAME_OR_NATIVE_PTS_MISMATCH"]
        return record
    if obs.get("visibility")!="VISIBLE" or not obs.get("bbox") or region["grounding_status"] in {"UNKNOWN","CONTRADICTED"}:
        record["reason_codes"]=["MISSING_VISIBLE_GEOMETRY"]
        return record
    try:
        obj=np.array(box_polygon(obs["bbox"]),dtype=np.float32)
        reg=np.array(region["polygon"],dtype=np.float32)
        area=cv2.contourArea(obj)
        intersection,_=cv2.intersectConvexConvex(obj,reg)
        overlap=max(0.,min(1.,float(intersection)/area))
    except (ValueError,cv2.error):
        record["reason_codes"]=["INVALID_OBJECT_GEOMETRY"]
        return record
    x1,y1,x2,y2=obs["bbox"]
    rx1,ry1=reg.min(axis=0);rx2,ry2=reg.max(axis=0)
    dx=max(float(rx1)-x2,x1-float(rx2),0.)
    dy=max(float(ry1)-y2,y1-float(ry2),0.)
    bbox_gap=math.hypot(dx,dy)
    distance=0. if intersection>0 else min(
        [abs(cv2.pointPolygonTest(reg,tuple(map(float,p)),True)) for p in obj]+
        [abs(cv2.pointPolygonTest(obj,tuple(map(float,p)),True)) for p in reg])
    if region.get("pixel_mask_rle"):
        from memory_graph.v22.sam_tracking import decode_mask
        surface=decode_mask(region["pixel_mask_rle"]).astype(bool)
        if obs.get("pixel_mask_rle"):
            object_mask=decode_mask(obs["pixel_mask_rle"]).astype(bool)
            if object_mask.shape!=surface.shape:raise ValueError("OBJECT_SURFACE_MASK_DIMENSION_MISMATCH")
        else:
            object_mask=np.zeros(surface.shape,np.uint8)
            cv2.fillConvexPoly(object_mask,np.rint(obj).astype(np.int32),1)
            object_mask=object_mask.astype(bool)
        if not object_mask.any() or not surface.any():
            record["reason_codes"]=["EMPTY_LOCALIZATION_MASK"]
            return record
        overlap=float(np.count_nonzero(surface & object_mask)/np.count_nonzero(object_mask))
        distances=cv2.distanceTransform((~surface).astype(np.uint8),cv2.DIST_L2,5)
        distance=float(distances[object_mask].min())
        record["provenance"]["geometry"]="SOURCE_PIXEL_MASK_INTERSECTION_AND_DISTANCE"
    near_limit=.1*math.hypot(float(rx2-rx1),float(ry2-ry1))
    projection="INSIDE_REGION" if overlap>=.98 else "OVERLAPS_REGION" if overlap>.01 else (
        "ABOVE_REGION" if y2<=ry1 and dx==0 and dy<=near_limit else "NEAR_REGION" if distance<=near_limit else "UNKNOWN")
    record.update(projection_relation=projection,spatial_relation=projection,
        geometry=dict(object_fraction_intersection=overlap,bbox_gap_px=bbox_gap,polygon_gap_px=distance,
                      near_limit_px=near_limit,object_bottom_image_y=float(y2)))
    if projection=="UNKNOWN":
        record["reason_codes"]=["NO_LOCAL_SPATIAL_PROXIMITY"]
        return record
    record.update(grounding_status="CANDIDATE",association_evidence_refs=[dict(
        object_observation_id=obs["observation_id"],region_id=region["region_id"],
        method="SAME_SOURCE_FRAME_CONVEX_INTERSECTION")],
        reason_codes=["PROJECTED_RELATION_NOT_DEPTH_OR_CONTACT","REGION_SEMANTICS_MAY_BE_WRONG"])
    if region.get("surface_candidate") and overlap>.01:
        record["spatial_relation"]="POSSIBLY_ON_SURFACE"
        record["reason_codes"].append("EDGE_PATCH_NOT_VERIFIED_SUPPORT_SURFACE")
    if support_measurement(obs,region,cue):
        record["association_evidence_refs"]+=cue["refs"]
        if cue["state"] in {"HELD_ABOVE","NOT_ON_SURFACE"}:
            record.update(grounding_status="CONTRADICTED",reason_codes=["INDEPENDENT_EVIDENCE_CONTRADICTS_SUPPORT"])
        elif region["grounding_status"]=="VERIFIED" and region.get("usable_surface"):
            record.update(spatial_relation="ON_SURFACE",grounding_status="VERIFIED",
                relation_scope="INDEPENDENT_PHYSICAL_SUPPORT",physical_support_verified=True,
                reason_codes=["EXPLICIT_CONTACT_AND_VERIFIED_REGION"],support_evidence=cue)
    return record


def iou(a,b):
    left=max(a[0],b[0]);top=max(a[1],b[1]);right=min(a[2],b[2]);bottom=min(a[3],b[3])
    inter=max(0,right-left)*max(0,bottom-top)
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union>0 else 0.


def associate_vlm(observations):
    """Exact-frame compatible candidates; category uniqueness is insufficient."""
    cv={}
    for obs in observations:
        if obs["source"]=="CV":
            k=(obs["source_video_sha256"],tuple(obs["source_frame_indices"]),tuple(obs["source_times_s"]),obs["object_category"])
            cv.setdefault(k,[]).append(obs)
    associations=[]
    for obs in observations:
        if obs["source"]!="VLM":continue
        k=(obs["source_video_sha256"],tuple(obs["source_frame_indices"]),tuple(obs["source_times_s"]),obs["object_category"])
        candidates=cv.get(k,[])
        row=dict(vlm_observation_id=obs["observation_id"],candidate_observation_ids=[c["observation_id"] for c in candidates],
            status="UNRESOLVED",persistent_entity_id=None,evidence_refs=obs["evidence_refs"],
            reason="NO_CV_DETECTION_NOT_PROOF_OF_ABSENCE" if not candidates else "NO_OBJECT_LOCALIZATION_CATEGORY_ALONE_INSUFFICIENT")
        # Only explicitly sourced pixel coordinates can resolve an observation.
        local=obs.get("localization") or {}
        if local.get("coordinate_space")=="SOURCE_PIXELS" and local.get("bbox") and local.get("evidence_refs"):
            box_polygon(local["bbox"])
            scored=[(iou(local["bbox"],c["bbox"]),c) for c in candidates if c.get("bbox") and c["visibility"]=="VISIBLE"]
            matching=[c for score,c in scored if score>=.7]
            competing=[c for score,c in scored if score>.1]
            if len(matching)==1 and len(competing)==1:
                c=matching[0]
                row.update(status="RESOLVED_LOCAL_OBSERVATION",cv_observation_id=c["observation_id"],
                    persistent_entity_id=c["authorized_entity_id"] if authorized(c) else None,
                    reason="EXPLICIT_LOCALIZATION_UNIQUE_GEOMETRIC_MATCH",
                    evidence_refs=obs["evidence_refs"]+local["evidence_refs"]+c["evidence_refs"])
            else:row["reason"]="LOCALIZATION_MISSING_OR_AMBIGUOUS_MATCH"
        associations.append(row)
    return associations


def enrich_memory(memory,video,regions,cues=None):
    """New metadata and evidence edges; existing event decisions stay unchanged."""
    for region in regions:validate_region(region,video)
    if len({r["region_id"] for r in regions})!=len(regions):raise ValueError("DUPLICATE_REGION_ID")
    by_frame={}
    for r in regions:by_frame.setdefault(r["source_frame_index"],[]).append(r)
    observations=memory.metadata["observations"]
    locations=[]
    for obs in observations:
        if obs["source"]!="CV" or obs["object_category"] in REGION_CLASSES | {"person","unknown"}:continue
        for frame in obs["source_frame_indices"]:
            for region in by_frame.get(frame,[]):
                locations.append(relate(obs,region,(cues or {}).get((obs["observation_id"],region["region_id"]))))
    associations=associate_vlm(observations)
    memory.metadata.update(spatial_version="phase5_v1",scene_regions=regions,
        location_observations=locations,vlm_cv_associations=associations,
        trusted_location_history=[r for r in locations if r["grounding_status"]=="VERIFIED" and r["persistent_entity_id"]],
        candidate_location_history=[r for r in locations if r["grounding_status"]=="CANDIDATE"],
        region_geometry_policy="FRAME_ONLY_NO_CROSS_VIEW_REUSE")
    edges=memory.metadata.setdefault("graph_edges",[])
    for r in regions:
        edges.append(dict(source=r["region_id"],predicate="GROUNDED_IN_FRAME",target=str(r["source_frame_index"]),source_video_sha256=r["source_video_sha256"]))
    for loc in locations:
        edges.append(dict(source=loc["persistent_entity_id"] or loc["object_candidate_id"],predicate="HAS_LOCATION_EVIDENCE",target=loc["observation_id"]))
        edges.append(dict(source=loc["observation_id"],predicate=loc["spatial_relation"],target=loc["region_id"],grounding_status=loc["grounding_status"]))
    for entity in memory.entities:
        entity.evidence += [{"location_observation_id":r["observation_id"]} for r in locations
            if (r["persistent_entity_id"] or r["object_candidate_id"])==entity.entity_id]
    return memory


def search_spatial(memory,query,entity_id=None):
    from .adapters import category
    q=query.lower().strip()
    label="phone" if "phone" in q or "手機" in q else category(q)
    identities={o.get("authorized_entity_id") for o in memory.metadata["observations"] if authorized(o)}
    if entity_id is None:
        exact=[i for i in identities if i==query.strip() or i.split("::")[-1]==query.strip()]
        if len(exact)==1:entity_id=exact[0]
    observations=[o for o in memory.metadata["observations"] if (o.get("authorized_entity_id")==entity_id if entity_id else o["object_category"]==label)]
    history=[r for r in memory.metadata["location_observations"] if (r["persistent_entity_id"]==entity_id if entity_id else r["object_category"]==label)]
    trusted=[r for r in history if r["grounding_status"]=="VERIFIED" and r["persistent_entity_id"] and r["physical_support_verified"]]
    candidates=[]
    for loc in history:
        if loc["grounding_status"] not in {"VERIFIED","CANDIDATE"}:continue
        identity=loc["persistent_entity_id"];time=loc["source_time_s"]
        is_trusted=loc in trusted
        superseded=is_trusted and any(r["persistent_entity_id"]==identity and r["source_time_s"]>time for r in trusted)
        if superseded:continue
        later=[e for e in memory.events if e.get("decision")!="REJECTED" and e.get("native_interval_s") and e["native_interval_s"][1]>time
            and (e.get("authorized_entity_id")==identity if identity and e.get("authorized_entity_id") else e.get("object_category")==loc["object_category"])]
        moved=bool(identity and any(e["decision"]=="SUPPORTED" and e.get("authorized_entity_id")==identity and e["type"]=="PICKUP" for e in later))
        from .pipeline import independent_state
        held=bool(identity and any(o.get("authorized_entity_id")==identity and independent_state(o) and o["physical_state"]=="HELD_BY_PERSON" and max(o["source_times_s"])>time for o in observations))
        candidates.append(dict(**loc,location_class="LAST_CONFIRMED_LOCATION" if is_trusted else "POSSIBLE_LOCATION",
            identity_scope="AUTHORIZED_PERSISTENT_ENTITY" if identity else "CATEGORY_CANDIDATE_NOT_USERS_PHONE",
            later_event_ids=[e["hypothesis_id"] for e in later],current_location_uncertain=True,
            prior_location_invalidated=moved or held,
            uncertainty=["Only observed at the cited time; not proof of current presence"]+
                (["Later same-entity pickup/held evidence invalidates current presence"] if moved or held else [])+
                (["Later event hypothesis remains unresolved"] if later else [])+
                (["Projected geometry does not establish depth, containment or physical support"] if not is_trusted else [])+
                (["Category match does not identify your particular phone"] if not identity else []),
            reason="Evidence authority first, then native time; no fixed-weight score",
            _order=(0 if is_trusted else 1 if identity else 2,-time)))
    candidates.sort(key=lambda r:(r["_order"],r["observation_id"]))
    previous=None;rank=0
    for c in candidates:
        order=c.pop("_order")
        # Time is a display order across different instances, not proof that
        # one unresolved instance is the user's object. Equal authority ties
        # remain explicit instead of being hidden by stable-ID ordering.
        if order[0]!=previous:rank+=1
        c["rank"]=rank;previous=order[0]
    ranks={}
    for c in candidates:ranks[c["rank"]]=ranks.get(c["rank"],0)+1
    for c in candidates:
        c["ordering_unresolved_tie"]=ranks[c["rank"]]>1
        c["display_order_policy"]="Native time within authority tier; recency is not identity resolution"
    return dict(query=query,video_id=memory.video,requested_entity_id=entity_id,
        status="LAST_CONFIRMED_LOCATION" if trusted else "POSSIBLE_LOCATIONS" if candidates else "UNKNOWN",
        candidates=candidates,last_useful_observation=max(observations,key=lambda o:max(o["source_times_s"],default=-1),default=None),
        location_history=history,graph_write_performed=False,
        reason="Historical spatial evidence, not a current-location guarantee" if candidates else "No adequately grounded region relationship")
