"""Phase 6 CPU contracts. Localized model claims are not physical verification."""
from copy import deepcopy
import json
import math
import cv2
import numpy as np
from .adapters import key, observation
from .regions import scope, validate_region, box_polygon
from .spatial import iou, authorized, enrich_memory
from .pipeline import build_memory, search

TARGET_TYPES=["smartphone","desk_telephone","handset","remote_control","phone_like_unknown","requested_object"]
SURFACE_TYPES=["tabletop","desk_surface","microwave_top","shelf_top","other_visible_surface"]
COORD={"type":"number","minimum":0,"maximum":1000}
BBOX={"type":"array","items":COORD,"minItems":4,"maxItems":4}
POINT={"type":"array","items":COORD,"minItems":2,"maxItems":2}
SCHEMA={"type":"object","additionalProperties":False,"required":["targets","surfaces"],"properties":{
    "targets":{"type":"array","maxItems":8,"items":{"type":"object","additionalProperties":False,
        "required":["id","kind","bbox","visible_state","description"],"properties":{
            "id":{"type":"string"},"kind":{"enum":TARGET_TYPES},"bbox":BBOX,
            "visible_state":{"enum":["HELD","PARTIALLY_OCCLUDED","SURFACE_ALIGNED","UNKNOWN"]},
            "description":{"type":"string"}}}},
    "surfaces":{"type":"array","maxItems":5,"items":{"type":"object","additionalProperties":False,
        "required":["id","kind","polygon","description"],"properties":{
            "id":{"type":"string"},"kind":{"enum":SURFACE_TYPES},
            "polygon":{"type":"array","items":POINT,"minItems":3,"maxItems":8},
            "description":{"type":"string"}}}}}}


def prompt(query,canvas=None):
    instruction=("Inspect ONLY the current source image F0001. Localize visible objects relevant to the search for "
        +json.dumps(query)+". Distinguish smartphones (flat touchscreen mobile phones), desk telephones, "
        "telephone handsets, remote controls and uncertain phone-like objects. Include visible distractors with "
        "their own kinds; do not call them the user's target. Return tight object bounding boxes. "
        "Also localize the actual VISIBLE TOP/support faces of tables, desks, microwaves or shelves. "
        "For each surface return a convex polygon along the visible support-face boundary, in perimeter order. "
        "Do NOT outline the entire table/legs or microwave body/front. Omit surfaces whose top is not visible "
        "or cannot be localized. Do not use an arbitrary upper slice of an object. "
        "Coordinates MUST be normalized to [0,1000] relative to F0001's full width and height; boxes are "
        "[xmin,ymin,xmax,ymax]. Polygon vertices are [x,y]. No coordinates refer to the optional reference image. "
        "HELD is a visual assertion, not confirmed contact; SURFACE_ALIGNED does not prove support. "
        "An optional target reference is appearance context only, never persistent identity authorization. "
        "Use requested_object only for non-phone search categories. Return empty arrays when appropriate. "
        "Output only JSON matching this schema, no markdown: ")
    schema=deepcopy(SCHEMA)
    if canvas:
        w,h=canvas
        instruction=instruction.replace("Coordinates MUST be normalized to [0,1000] relative to F0001's full width and height; boxes are ",
            f"F0001 is exactly {w} pixels wide and {h} pixels high. Coordinates MUST be ABSOLUTE PIXELS in this image, NOT normalized. x is 0..{w}, y is 0..{h}. Boxes are ")
        schema["properties"]["targets"]["items"]["properties"]["bbox"]["items"]["maximum"]=max(w,h)
        schema["properties"]["surfaces"]["items"]["properties"]["polygon"]["items"]["items"]["maximum"]=max(w,h)
    return instruction+json.dumps(schema,separators=(",",":"))


def parse(raw,canvas=None):
    import jsonschema
    original=raw.strip();body=original;origin="RAW"
    if body.startswith("```json\n") and body.endswith("```"):
        body=body[len("```json\n"):-3].strip();origin="EXACT_OUTER_FENCE"
    try:
        value=json.loads(body)
        schema=deepcopy(SCHEMA)
        if canvas:
            schema["properties"]["targets"]["items"]["properties"]["bbox"]["items"]["maximum"]=max(canvas)
            schema["properties"]["surfaces"]["items"]["properties"]["polygon"]["items"]["items"]["maximum"]=max(canvas)
        jsonschema.validate(value,schema)
        ids=[x["id"] for x in value["targets"]+value["surfaces"]]
        if len(ids)!=len(set(ids)):raise ValueError("DUPLICATE_LOCAL_ID")
        if canvas:
            w,h=canvas
            for row in value["targets"]:
                x1,y1,x2,y2=row["bbox"]
                if not (0<=x1<x2<=w and 0<=y1<y2<=h):raise ValueError("CANVAS_BBOX_OUT_OF_BOUNDS")
                row["bbox"]=[x1/w*1000,y1/h*1000,x2/w*1000,y2/h*1000]
            for row in value["surfaces"]:
                if any(not (0<=x<=w and 0<=y<=h) for x,y in row["polygon"]):raise ValueError("CANVAS_POLYGON_OUT_OF_BOUNDS")
                row["polygon"]=[[x/w*1000,y/h*1000] for x,y in row["polygon"]]
        return value,dict(valid=True,origin=origin,raw_preserved=True,
            coordinate_conversion="EXPLICIT_MODEL_CANVAS_TO_NORMALIZED_TO_SOURCE" if canvas else "NORMALIZED_TO_SOURCE",canvas=canvas)
    except (ValueError,jsonschema.ValidationError) as exc:
        return None,dict(valid=False,origin=origin,error=str(exc)[:1000],invalid_is_not_absence=True)


def pixels(values,width,height,box=False):
    a=np.asarray(values,dtype=float)
    if not np.isfinite(a).all() or (a<0).any() or (a>1000).any():raise ValueError("COORDINATE_RANGE")
    if box:
        if a.shape!=(4,):raise ValueError("BBOX_SHAPE")
        a*=np.array([width,height,width,height])/1000
        box_polygon(a)
    else:
        if a.ndim!=2 or a.shape[1]!=2:raise ValueError("POLYGON_SHAPE")
        a*=np.array([width,height])/1000
        if len(a)<3 or not cv2.isContourConvex(a.astype(np.float32)):raise ValueError("NONCONVEX_SURFACE")
        if cv2.contourArea(a.astype(np.float32))<4:raise ValueError("EMPTY_SURFACE")
    return a.tolist()


def validate_frame(video,frame):
    expected=scope(video,frame["source_frame_index"])
    for k in ("video_id","source_video_sha256","source_time_s","native_pts","time_base"):
        if frame.get(k)!=expected[k]:raise ValueError("LOCALIZATION_FRAME_SCOPE:"+k)
    if frame["width"]!=video["width"] or frame["height"]!=video["height"]:raise ValueError("LOCALIZATION_DIMENSIONS")
    if not frame.get("sha256"):raise ValueError("SOURCE_FRAME_HASH_REQUIRED")


def checked_refinement(refinements,identifier,frame):
    value=refinements.get(identifier)
    if not value or not value.get("accepted"):return None
    if value.get("source_frame_sha256")!=frame["sha256"]:
        raise ValueError("MASK_SOURCE_FRAME_MISMATCH")
    if value.get("mask_rle",{}).get("shape")!=[frame["height"],frame["width"]]:
        raise ValueError("MASK_SOURCE_DIMENSION_MISMATCH")
    if not value.get("mask_ref",{}).get("sha256"):raise ValueError("MASK_HASH_REQUIRED")
    return value


def adapt_localization(parsed,video,frame,raw_ref,existing,query="smartphone",refinements=None):
    """Reuse exact authorized CV rows; never transfer identity to new model boxes.

    Newly localized CV-like geometry records have MODEL_DERIVED_LOCALIZATION
    provenance, no independent state evidence and no persistent authorization.
    Historical VLM claims are never augmented with these new coordinates.
    """
    validate_frame(video,frame)
    refined=refinements or {}
    targets=[];regions=[];claims=[];audit=[];classified={}
    native=[dict(source_frame_index=frame["source_frame_index"],native_pts_s=frame["source_time_s"])]
    for row in parsed["targets"]:
        try:bbox=pixels(row["bbox"],video["width"],video["height"],box=True)
        except ValueError as e:audit.append(dict(id=row["id"],status="REJECTED_GEOMETRY",reason=str(e)));continue
        label="phone" if row["kind"]=="smartphone" else query if row["kind"]=="requested_object" else row["kind"]
        oid="perception:"+key(frame["sha256"],raw_ref,row["id"])
        refs=[frame,raw_ref]
        ob=observation(oid,video,"CV","local:"+key(video["source_sha256"],frame["source_frame_index"],row["id"]),label,native,refs,
            dict(provider="MODEL_DERIVED_LOCALIZATION",model_output_ref=raw_ref,coordinate_space="SOURCE_PIXELS",
                source_coordinate_space="NORMALIZED_0_1000",model_canvas=frame.get("model_canvas"),frame_sha256=frame["sha256"]))
        ob.update(bbox=bbox,visibility="VISIBLE",target_query=query,target_kind=row["kind"],
            object_description=row["description"],state_claim=row["visible_state"],
            physical_state_evidence=None,persistent_identity_status="UNRESOLVED",
            localization_source="QWEN_NF4_FRAME_GROUNDING",candidate_mask_ref=None)
        refinement=checked_refinement(refined,row["id"],frame)
        if refinement and refinement.get("accepted"):
            ob["candidate_mask_ref"]=refinement["mask_ref"]
            ob["pixel_mask_rle"]=refinement["mask_rle"]
            ob["evidence_refs"]=[*refs,refinement["mask_ref"]]
            ob["provenance"]["boundary_refinement"]="SAM21_CLIPPED_TO_LOCALIZATION"
        comparable=[c for c in existing if c["source"]=="CV" and c.get("bbox") and c["visibility"]=="VISIBLE"
            and c["source_video_sha256"]==video["source_sha256"] and c["source_frame_indices"]==[frame["source_frame_index"]]
            and c["source_times_s"]==[frame["source_time_s"]] and c["object_category"] in {"phone",label}]
        matches=[c for c in comparable if iou(c["bbox"],bbox)>=.7]
        competitors=[c for c in comparable if iou(c["bbox"],bbox)>.1]
        if len(matches)==1 and len(competitors)==1 and matches[0]["observation_id"] not in classified:
            cv=matches[0]
            classified[cv["observation_id"]]=dict(kind=row["kind"],label=label,localization_id=oid)
            ob["local_cv_observation_match"]=cv["observation_id"]
            # Keep exact CV geometry and authorization in its own existing row.
            audit.append(dict(id=oid,status="UNIQUE_LOCAL_CV_OVERLAP",cv_observation_id=cv["observation_id"],
                identity_transferred=False,existing_identity_authorized=authorized(cv)))
        else:audit.append(dict(id=oid,status="NEW_OR_AMBIGUOUS_LOCAL_CANDIDATE",candidate_cv_ids=[c["observation_id"] for c in competitors]))
        targets.append(ob)
        claim=observation("claim:"+oid,video,"VLM","claim-local:"+oid,label,native,refs,
            dict(provider="NEW_LOCALIZED_QWEN_CLAIM",historical_nemotron=False,frame_sha256=frame["sha256"]))
        claim.update(localization=dict(coordinate_space="SOURCE_PIXELS",bbox=bbox,evidence_refs=refs),
            object_description=row["description"],state_claim=row["visible_state"])
        claims.append(claim)
    for row in parsed["surfaces"]:
        try:polygon=pixels(row["polygon"],video["width"],video["height"])
        except ValueError as e:audit.append(dict(id=row["id"],status="REJECTED_GEOMETRY",reason=str(e)));continue
        r=dict(**scope(video,frame["source_frame_index"]),region_id="surface:"+key(frame["sha256"],raw_ref,row["id"]),
            region_label=row["kind"]+" candidate",region_category=row["kind"],polygon=polygon,
            geometry_kind="MODEL_VISIBLE_SURFACE_POLYGON",grounding_status="CANDIDATE",usable_surface=False,
            surface_candidate=True,surface_semantics="UNVERIFIED_SURFACE_CANDIDATE",
            visibility="MODEL_VISIBLE_PROPOSAL",valid_frame_indices=[frame["source_frame_index"]],
            viewpoint_id="view:"+key(video["source_sha256"],frame["source_frame_index"]),semantic_region_id=None,
            evidence_refs=[frame,raw_ref],description=row["description"],
            provenance=dict(origin="MODEL_DERIVED_SURFACE_LOCALIZATION",physical_contact_verified=False),
            limitations=["Model-derived top-face semantics, not independent proof", "Frame-local; no cross-view propagation", "Polygon can include occluded portions"])
        refinement=checked_refinement(refined,row["id"],frame)
        if refinement and refinement.get("accepted"):
            r.update(pixel_mask_rle=refinement["mask_rle"],mask_ref=refinement["mask_ref"],
                geometry_kind="SAM21_CLIPPED_MODEL_SURFACE_MASK")
            r["evidence_refs"].append(refinement["mask_ref"])
            r["provenance"]["boundary_refinement"]="SAME_IMAGE_SAM_NOT_INDEPENDENT_SEMANTIC_VALIDATION"
        r["provenance"]["model_canvas"]=frame.get("model_canvas")
        identical=next((prior for prior in regions if prior["polygon"]==r["polygon"]),None)
        if identical:
            identical.setdefault("alternative_model_labels",[]).append(r["region_label"])
        else:regions.append(validate_region(r,video))
    return targets,regions,claims,audit,classified


def integrate(base,video,frames,perception):
    """A matched-frame evaluation graph. Full Phase 5 graph remains immutable."""
    frame_ids={f["source_frame_index"] for f in frames}
    existing=[deepcopy(o) for o in base.metadata["observations"] if set(o["source_frame_indices"])<=frame_ids]
    targets=[];regions=[];claims=[];audit=[];classified={}
    for frame in frames:
        payload=perception.get(frame["source_frame_index"])
        if not payload or payload.get("parsed") is None:continue
        t,r,c,a,k=adapt_localization(payload["parsed"],video,frame,payload["raw_ref"],existing,
            payload.get("target_query","smartphone"),payload.get("refinements"))
        targets+=t;regions+=r;claims+=c;audit+=a;classified.update(k)
    # Preserve originals; derived taxonomy is explicitly a new model claim.
    for o in existing:
        if o["source"]=="CV" and o["object_category"]=="phone":
            o["phase5_object_category"]=o["object_category"]
            classification=classified.get(o["observation_id"])
            o["target_kind"]=classification["kind"] if classification else "phone_like_unknown"
            o["target_classification_evidence"]=classification
            o["object_category"]=classification["label"] if classification else "phone_like_unknown"
            if classification and classification["kind"] not in {"smartphone","requested_object"} and o.get("authorized_entity_id"):
                o["identity_category_conflict"]=dict(original_entity_id=o["authorized_entity_id"],
                    original_authorization=o.get("identity_authorization"),reason="NEW_CATEGORY_CLAIM_CONFLICTS_WITH_TARGET_SMARTPHONE")
                o["authorized_entity_id"]=None
                o["identity_authorization"]=None
                o["authorization_validation"]="WITHHELD_IN_DERIVED_VIEW_CATEGORY_CONFLICT"
    observations=existing+targets+claims
    memory=build_memory(base.video,observations,deepcopy(base.events),deepcopy(base.metadata.get("response_receipts",[])),[])
    # Retain original regions at the same frames as fallback; new regions carry
    # more specific surface labels but do not erase baseline evidence.
    old_regions=[deepcopy(r) for r in base.metadata.get("scene_regions",[]) if r["source_frame_index"] in frame_ids]
    enrich_memory(memory,video,old_regions+regions)
    # Recomputing geometry must not downgrade independently verified historical
    # support. Preserve the original trusted evidence, not a newly fabricated cue.
    preserved=[deepcopy(r) for r in base.metadata.get("trusted_location_history",[])
        if r["source_frame_index"] in frame_ids and r.get("persistent_entity_id")
        and r.get("physical_support_verified") and r["grounding_status"]=="VERIFIED"]
    preserved_ids={r["observation_id"] for r in preserved}
    memory.metadata["location_observations"]=[r for r in memory.metadata["location_observations"] if r["observation_id"] not in preserved_ids]+preserved
    memory.metadata["trusted_location_history"]=preserved
    memory.metadata["candidate_location_history"]=[r for r in memory.metadata["location_observations"] if r["grounding_status"]=="CANDIDATE"]
    memory.metadata.update(perception_version="phase6_v1",evaluation_scope="SELECTED_SOURCE_FRAMES_ONLY",
        selected_frame_indices=sorted(frame_ids),target_localizations=targets,
        new_surface_regions=regions,localization_audit=audit,
        original_selected_observations=[o for o in base.metadata["observations"] if set(o["source_frame_indices"])<=frame_ids],
        target_identity_policy="Reference/category/local match is not persistent identity",reference_identity_enrolled=False)
    for loc in memory.metadata["location_observations"]:
        o=next(o for o in observations if o["observation_id"]==loc["object_observation_id"])
        if o.get("state_claim"):
            loc["model_state_claim"]=o["state_claim"]
            loc["state_claim_is_independent_support"]=False
            if o["state_claim"]=="HELD":
                if loc["spatial_relation"]=="POSSIBLY_ON_SURFACE":loc["spatial_relation"]=loc["projection_relation"]
                loc["reason_codes"].append("MODEL_REPORTS_HELD_PHYSICAL_SUPPORT_UNRESOLVED")
    relations={loc["observation_id"]:loc["spatial_relation"] for loc in memory.metadata["location_observations"]}
    for edge in memory.metadata["graph_edges"]:
        if edge["source"] in relations:edge["predicate"]=relations[edge["source"]]
    return memory


def scoped_baseline(base,frame_ids):
    memory=base.model_copy(deep=True)
    for field in ("observations","location_observations","scene_regions"):
        values=memory.metadata.get(field,[])
        memory.metadata[field]=[v for v in values if (set(v["source_frame_indices"])<=frame_ids if field=="observations" else v["source_frame_index"] in frame_ids)]
    return memory


def query_result(memory,query="Where is my phone?",entity_id=None):
    from .spatial import search_spatial
    from .adapters import category
    result=search_spatial(memory,query,entity_id)
    entity_id=result["requested_entity_id"]
    label="phone" if "phone" in query.lower() or "手機" in query else category(query.lower().strip())
    localized=[o for o in memory.metadata.get("target_localizations",[]) if
        (o.get("authorized_entity_id")==entity_id if entity_id else o["object_category"]==label)]
    result["localized_object_without_region"]=[o for o in localized if not any(c["object_observation_id"]==o["observation_id"] for c in result["candidates"])]
    result["observation_status"]="LOCALIZED_OBJECT_WITHOUT_GROUNDED_REGION" if localized and not result["candidates"] else "LOCALIZED_OBJECT_WITH_REGION" if localized else "NO_NEW_LOCALIZATION_NOT_ABSENCE"
    result["search_scope"]="PERSISTENT_ENTITY" if entity_id else "CATEGORY_LEVEL"
    result["evaluation_scope"]=memory.metadata.get("evaluation_scope")
    result["unclassified_phone_like_observations"]=[o["observation_id"] for o in memory.metadata["observations"] if o["object_category"]=="phone_like_unknown"]
    return result
