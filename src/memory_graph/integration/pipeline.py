"""Small deterministic decision and search layer over the existing TemporalMemory."""
from collections import defaultdict
from pathlib import Path
from memory_graph.scene_graph.models import SemanticEntity, TemporalMemory
from memory_graph.memory.memory_store import save_json
from .adapters import key, category


def independent_state(obs):
    evidence = obs.get("physical_state_evidence") or {}
    return (obs["source"] == "CV" and evidence.get("origin") == "CV_MEASUREMENT"
            and bool(evidence.get("refs")) and obs["visibility"] == "VISIBLE")


def decide(hypothesis, observations, association=None):
    """An association cites exact CV obs IDs; category equality cannot create it.

    Independent state evidence must originate from an upstream CV measurement,
    never from an annotation verdict or a second description of the same VLM.
    Current raw detector/SAM adapters do not manufacture this measurement.
    """
    h = hypothesis
    decision = dict(h, decision="UNCERTAIN", authorized_entity_id=None,
        supporting_observation_ids=[], conflicting_observation_ids=[],
        reason_codes=[], unresolved_assumptions=[], visual_grounding_status="UNVERIFIED")
    expected = ("ON_SURFACE","HELD_BY_PERSON") if h["type"]=="PICKUP" else ("HELD_BY_PERSON","ON_SURFACE")
    if not h["temporal_valid"]:
        decision.update(decision="REJECTED", reason_codes=["INVALID_SOURCE_TEMPORAL_CITATIONS"])
        return decision
    claims = h["before_claims"], h["after_claims"]
    if any(any(v not in (wanted,"UNKNOWN",None) for v in values) for values,wanted in zip(claims,expected)):
        decision.update(decision="REJECTED",reason_codes=["MODEL_STATE_TRANSITION_CONTRADICTION"])
        return decision
    if not h["raw_strict_valid"]:
        decision["reason_codes"].append("STRICT_INVALID_NOT_AUTHORITATIVE")
    if not association:
        decision["reason_codes"] += ["INSTANCE_ASSOCIATION_UNRESOLVED","NO_INDEPENDENT_STATE_EVIDENCE"]
        decision["unresolved_assumptions"] = ["VLM object description has no CV instance binding",
                                             "VLM states are assertions, not independent confirmation"]
        return decision
    by_id={o["observation_id"]:o for o in observations}
    groups=[]
    for phase in ("before","after"):
        ids=association.get(phase+"_observation_ids",[])
        group=[by_id[i] for i in ids if i in by_id]
        frames={f["source_frame_index"] for f in h[phase+"_refs"]}
        if not group or len(group)!=len(ids) or any(
            o["source"]!="CV" or o["source_video_sha256"]!=h["source_video_sha256"] or
            o["video_id"]!=h["video_id"] or not set(o["source_frame_indices"]) <= frames or
            o["object_category"]!=h["object_category"] for o in group) or \
            {f for o in group for f in o["source_frame_indices"]}!=frames:
            decision["reason_codes"].append("ASSOCIATION_SCOPE_MISMATCH")
            return decision
        # Native times must match as well as frame indices.
        mapping={f["source_frame_index"]:f["native_pts_s"] for f in h[phase+"_refs"]}
        if any(len(o["source_times_s"])!=len(o["source_frame_indices"]) or
               any(abs(t-mapping[f])>1e-9 for f,t in zip(o["source_frame_indices"],o["source_times_s"])) for o in group):
            decision["reason_codes"].append("ASSOCIATION_NATIVE_PTS_MISMATCH")
            return decision
        groups.append(group)
    all_obs=groups[0]+groups[1]
    entities={o.get("authorized_entity_id") for o in all_obs}
    if None in entities or len(entities)!=1 or any(not o.get("identity_authorization") or
            o.get("authorization_validation")!="VERIFIED_FINAL_LEDGER_REPLAY" for o in all_obs):
        decision["reason_codes"].append("IDENTITY_NOT_INDEPENDENTLY_AUTHORIZED")
        return decision
    decision["authorized_entity_id"]=next(iter(entities))
    for group,wanted in zip(groups,expected):
        for o in group:
            if independent_state(o) and o["physical_state"] not in (wanted,"UNKNOWN"):
                decision["conflicting_observation_ids"].append(o["observation_id"])
            elif independent_state(o) and o["physical_state"]==wanted:
                decision["supporting_observation_ids"].append(o["observation_id"])
    if decision["conflicting_observation_ids"]:
        decision.update(decision="REJECTED",visual_grounding_status="INDEPENDENT_CONTRADICTION")
        decision["reason_codes"].append("CV_STATE_CONTRADICTS_TRANSITION")
    elif len(decision["supporting_observation_ids"])!=len(all_obs):
        decision["reason_codes"].append("NO_INDEPENDENT_STATE_EVIDENCE")
        decision["unresolved_assumptions"].append("Occlusion/contact/geometry alone cannot establish state")
    elif h["raw_strict_valid"]:
        decision.update(decision="SUPPORTED",visual_grounding_status="INDEPENDENT_CV_SUPPORTED")
        decision["reason_codes"].append("AUTHORIZED_INSTANCE_AND_MEASURED_TRANSITION")
    return decision


def group_candidates(decisions):
    """Record possible associations; never merge by overlapping window alone."""
    links=[]
    for i,a in enumerate(decisions):
        for b in decisions[i+1:]:
            if (a["source_video_sha256"],a["type"],a["object_category"]) != (b["source_video_sha256"],b["type"],b["object_category"]):
                continue
            if not a["native_interval_s"] or not b["native_interval_s"]:continue
            frames=lambda e:tuple(tuple(f["source_frame_index"] for f in e[p]) for p in ("before_refs","after_refs"))
            same_evidence=frames(a)==frames(b)
            ai,bi=a["native_interval_s"],b["native_interval_s"]
            intersects=max(ai[0],bi[0])<=min(ai[1],bi[1])
            common={f["source_frame_index"] for f in a["before_refs"]+a["after_refs"]}&{f["source_frame_index"] for f in b["before_refs"]+b["after_refs"]}
            if not same_evidence and not (intersects and common):continue
            same_entity=a.get("authorized_entity_id") and a.get("authorized_entity_id")==b.get("authorized_entity_id")
            links.append(dict(hypothesis_ids=[a["hypothesis_id"],b["hypothesis_id"]],
                status="SAME_AUTHORIZED_EXACT_EVIDENCE" if same_evidence and same_entity else "POSSIBLE_SAME_EVENT_UNRESOLVED"))
    # Even overlapping supported time brackets cannot establish two real events.
    supported=[d for d in decisions if d["decision"]=="SUPPORTED"]
    for i,a in enumerate(supported):
        for b in supported[i+1:]:
            if (a["source_video_sha256"],a["authorized_entity_id"],a["type"])!=(b["source_video_sha256"],b["authorized_entity_id"],b["type"]):continue
            ai,bi=a["native_interval_s"],b["native_interval_s"]
            if max(ai[0],bi[0])>min(ai[1],bi[1]):continue
            af=[f["source_frame_index"] for f in a["before_refs"]+a["after_refs"]]
            bf=[f["source_frame_index"] for f in b["before_refs"]+b["after_refs"]]
            if af!=bf:
                for d in (a,b):
                    d["decision"]="UNCERTAIN"
                    if "OVERLAPPING_EVENT_IDENTITY_UNRESOLVED" not in d["reason_codes"]:
                        d["reason_codes"].append("OVERLAPPING_EVENT_IDENTITY_UNRESOLVED")
    return links


def build_memory(video_id, observations, decisions, receipts, grouping):
    """Reuse existing entities/events/metadata; no schema rewrite or production IO."""
    grouped=defaultdict(list)
    for o in observations:
        grouped[o.get("authorized_entity_id") or o["object_instance_candidate"]].append(o)
    entities=[]
    for index,(candidate,items) in enumerate(sorted(grouped.items())):
        times=[t for o in items for t in o["source_times_s"]]
        entities.append(SemanticEntity(track_id=index,entity_id=candidate,
            detector_class=items[0]["object_category"], first_seen=min(times,default=0),
            last_seen=max(times,default=0), admission_status="unknown",
            attributes={"identity_scope":"AUTHORIZED_REPLAY" if items[0].get("authorized_entity_id") else "UNRESOLVED_CANDIDATE"},
            evidence=[{"observation_id":o["observation_id"]} for o in items]))
    transitions=[];seen=set();by_id={o["observation_id"]:o for o in observations}
    for d in decisions:
        if d["decision"]!="SUPPORTED" or not d["authorized_entity_id"]:continue
        signature=(d["authorized_entity_id"],d["type"],tuple(f["source_frame_index"] for f in d["before_refs"]+d["after_refs"]))
        if signature in seen:continue
        seen.add(signature)
        after_frames={f["source_frame_index"] for f in d["after_refs"]}
        destinations=[by_id[i]["location_candidate"] for i in d["supporting_observation_ids"]
            if set(by_id[i]["source_frame_indices"])<=after_frames and trusted_location(by_id[i])]
        # State transitions may be known without a destination. Never set a
        # trusted location or invent a graph placement edge without location evidence.
        transitions.append(dict(event_id=d["hypothesis_id"],entity_id=d["authorized_entity_id"],
            type=d["type"],evidence_interval_s=d["native_interval_s"],
            location=destinations[0] if d["type"]=="PLACEMENT" and len({x["id"] for x in destinations})==1 else None,
            supporting_observation_ids=d["supporting_observation_ids"]))
    return TemporalMemory(video=video_id,entities=entities,events=decisions,transitions=transitions,
        metadata=dict(integration_version="phase4_v1",isolated_demo=True,
            observations=observations, response_receipts=receipts, candidate_groupings=grouping,
            trusted_location_policy="Only independently sourced observations; hypotheses never overwrite",
            graph_edges=[{"source":o.get("authorized_entity_id") or o["object_instance_candidate"],
                "predicate":"OBSERVED_BY","target":o["observation_id"]} for o in observations]+
                [{"source":d["hypothesis_id"],"predicate":"CITES","target":oid} for d in decisions
                 for oid in d["supporting_observation_ids"]+d["conflicting_observation_ids"]]))


def trusted_location(obs):
    loc=obs.get("location_candidate") or {}
    return obs["source"]=="CV" and obs["visibility"]=="VISIBLE" and loc.get("origin")=="CV_SPATIAL_OBSERVATION" and bool(loc.get("id")) and bool(loc.get("evidence_refs"))


def search(memory, query, entity_id=None):
    """Lexicographic evidence ordering, no numeric weighted confidence."""
    if memory.metadata.get("perception_version") == "phase6_v1":
        from .target_surface import query_result
        return query_result(memory, query, entity_id)
    if memory.metadata.get("spatial_version") == "phase5_v1":
        from .spatial import search_spatial
        return search_spatial(memory, query, entity_id)
    q=query.strip().lower()
    if entity_id is None:
        identities={o.get("authorized_entity_id") for o in memory.metadata["observations"] if o.get("authorized_entity_id")}
        matched=[i for i in identities if i==query.strip() or i.split("::")[-1]==query.strip()]
        if len(matched)==1:entity_id=matched[0]
    label="phone" if "phone" in q or "手機" in q else category(q)
    obs=[o for o in memory.metadata["observations"] if
        (o.get("authorized_entity_id")==entity_id if entity_id else o["object_category"]==label)]
    obs.sort(key=lambda o:(max(o["source_times_s"],default=-1),o["observation_id"]))
    relevant=[e for e in memory.events if e["decision"]!="REJECTED" and
        (e.get("authorized_entity_id")==entity_id or (not e.get("authorized_entity_id") and e["object_category"]==label)
         if entity_id else e["object_category"]==label)]
    candidates=[]
    for o in obs:
        if not trusted_location(o):continue
        time=max(o["source_times_s"])
        identity=o.get("authorized_entity_id")
        later=[e for e in relevant if e["native_interval_s"] and e["native_interval_s"][1]>time
               and (not identity or not e.get("authorized_entity_id") or e["authorized_entity_id"]==identity)]
        blockers=[e for e in later if e["decision"]=="SUPPORTED" and identity and e.get("authorized_entity_id")==identity and e["type"]=="PICKUP"]
        if blockers:continue
        if identity and any(n.get("authorized_entity_id")==identity and independent_state(n)
                and n["physical_state"]=="HELD_BY_PERSON" and max(n["source_times_s"])>time for n in obs):continue
        # Later trustworthy location supersedes only the SAME authorized entity.
        if identity and any(n.get("authorized_entity_id")==identity and trusted_location(n) and max(n["source_times_s"])>time for n in obs):continue
        uncertainty=["Latest observed location, not proof of current presence"]
        if not identity:uncertainty.append("Physical identity unresolved")
        if later:uncertainty.append("Later manipulation evidence may invalidate this location; destination unknown")
        candidates.append(dict(location=o["location_candidate"],entity_id=identity,
            candidate_id=o["object_instance_candidate"],observed_time_s=time,
            evidence_type="IDENTITY_SUPPORTED_LOCATION" if identity else "UNRESOLVED_OBJECT_LOCATION",
            supporting_observation_ids=[o["observation_id"]],event_ids=[e["hypothesis_id"] for e in later],
            evidence_refs=o["evidence_refs"],uncertainty=uncertainty,
            reason="Direct CV spatial observation; ordered by identity authorization then native time",
            _tier=(0 if identity else 1, 1 if later else 0)))
    candidates.sort(key=lambda c:(c["_tier"],-c["observed_time_s"],c["location"]["id"],c["candidate_id"]))
    unique=[];seen=set()
    for c in candidates:
        signature=(c["entity_id"] or c["candidate_id"],c["location"]["id"])
        if signature in seen:continue
        seen.add(signature);c.pop("_tier");c["rank"]=len(unique)+1;unique.append(c)
    return dict(query=query,video_id=memory.video,status=("CANDIDATES_FOUND" if any(c["entity_id"] for c in unique) else "CONDITIONAL_CANDIDATES") if unique else "UNKNOWN",
        candidates=unique,last_useful_observation=obs[-1] if obs else None,
        evidence_history_observation_ids=[o["observation_id"] for o in obs],
        event_ids=[e["hypothesis_id"] for e in relevant],
        reason="No independently grounded named location" if not unique else "Graph evidence, identity scope, temporal precedence; stable ID tie-break",
        graph_write_performed=False)


def run(video_id, observations, hypotheses, receipts, associations=None):
    decisions=[decide(h,observations,(associations or {}).get(h["hypothesis_id"])) for h in hypotheses]
    grouping=group_candidates(decisions)
    return build_memory(video_id,observations,decisions,receipts,grouping)


def persist(memory, path):
    destination=Path(path).resolve()
    allowed=Path(__file__).resolve().parents[3]/"artifacts/phase4"
    if not memory.metadata.get("isolated_demo") or not destination.is_relative_to(allowed.resolve()):
        raise PermissionError("Phase 4 persistence is restricted to isolated artifacts/phase4")
    save_json(path,memory)
