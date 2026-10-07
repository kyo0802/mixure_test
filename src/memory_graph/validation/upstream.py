"""Canonical raw perception/identity and dense evidence, with isolated IO only.
Phase bodies copied from V292; current adaptive windows replace its old VLM/memory tail.
"""
import os, time, gc
from copy import deepcopy
from pathlib import Path
from .common import ROOT, OUT, VIDEOS, VideoRoot, read, write, sha
from memory_graph.v292 import pipeline as canonical
from memory_graph.v292.pipeline import (_write, _read, _load_v21_inputs, _canonical_identity,
    _remap_paths, _store_masks, _reconcile_forward_timeline, _identity_memory_frames,
    _event_candidates, _authorize_dense_rows, _recover_anchors)

class ValidationContext(canonical.RunContext):
    def __enter__(self):
        super().__enter__()
        from memory_graph.v25rerun import adapter, sam_route, reid
        from memory_graph.v29 import dense_reinspection
        from memory_graph.v293 import sources, audit
        from memory_graph.reasoning import model
        for module in (adapter,sam_route,reid,dense_reinspection,sources):
            self._set(module,'ROOT',VideoRoot(str(ROOT)))
        self._set(sources,'BASE',self.output_root)
        self._set(sources,'OUT',self.output_root/'recovered')
        self._set(audit,'OUT',self.output_root/'recovered')
        self._set(model,'OUT',self.output_root)
        self.previous_cwd=Path.cwd()
        # Legacy V21 output guard is cwd-relative; stay inside isolated run root.
        os.chdir(self.output_root)
        return self
    def __exit__(self,*args):
        os.chdir(self.previous_cwd)
        return super().__exit__(*args)


def run(video_id, root):
    import torch
    from memory_graph.config_v2 import load_v2_config
    from memory_graph.v21.pipeline import run as run_v21
    from memory_graph.v25rerun.binding import automatic_bind
    from memory_graph.v25rerun.candidates import CandidateHypothesis
    from memory_graph.v25rerun import adapter, pipeline as v25_pipeline, sam_route, reid as v25_reid
    from memory_graph.v26 import pipeline as v26_pipeline
    if video_id not in VIDEOS:raise ValueError(video_id)
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    task_root=root/video_id
    if task_root.exists():raise RuntimeError('Fresh raw execution requires absent video output')
    task_root.mkdir()
    video=ROOT/'val_set'/f'{video_id}.mp4';raw_hash=sha(video)
    config=canonical.canonical_config();config_hash=config['canonical_config_sha256']
    _write(root/'canonical_config.json',config)
    manifest={'video_id':video_id,'video_sha256':raw_hash,'stages':[],'gt_accessed':False,'cache_reused':False}
    timings={};started=stage_start=time.monotonic()
    with ValidationContext(root):
        # Phase 1: fresh full-scene YOLO/tracking from this raw file.
        upstream = task_root / "upstream_v21"
        perception_config = load_v2_config(ROOT / "configs/v2.yaml")
        perception_config.perception.detector.model = str(ROOT / ".models/yolo11s.pt")
        v21_status = run_v21(video, perception_config, upstream,
                             reuse=None, events_only=True)
        inputs = _load_v21_inputs(video_id, task_root)
        if not v21_status.get("status") == "complete" or v21_status.get("video_sha256") != raw_hash:
            raise RuntimeError(f"Fresh V2.1 raw-video inference did not complete: {v21_status}")
        _write(task_root / "video_metadata.json", inputs["metadata"])
        _write(task_root / "perception/yolo_detections.json", inputs["detections"])
        _write(task_root / "perception/tracks.json", inputs["tracks"])
        manifest["stages"].append({"stage": "fresh_yolo_tracking", "status": "COMPLETE",
                                    "raw_hash": raw_hash, "details": v21_status})

        timings['yolo_and_local_tracking']=time.monotonic()-stage_start
        stage_start=time.monotonic()
        # Phase 2: automatic causal target binding, SAM2.1, fusion and candidate admission.
        current_stage = "target_binding_sam_fusion"
        metadata = inputs["metadata"]
        bound, binding_audit = automatic_bind(metadata.get("sampled_frames", []), inputs["tracks"])
        _write(task_root / "target_binding_audit.json", binding_audit)
        _write(task_root / "identity/target_binding.json", binding_audit)
        task = video_id
        router = sam_route.SamRouter(task) if bound is not None else None
        target_sam = router.target(bound) if router else {"status": "TARGET_BINDING_AMBIGUOUS", "segments": [], "events": []}
        _write(task_root / "sam/sam_continuity_log.json", target_sam)
        fusion, stream = v25_pipeline.run_admission(task)
        candidate_rows = _read(task_root / "candidate_grouping_audit.json", {}).get("candidates", [])
        last_frame = max((int(x["frame_index"]) for x in metadata.get("sampled_frames", [])), default=0)
        candidate_support = []
        for summary in candidate_rows:
            hypothesis = CandidateHypothesis(summary["candidate_id"])
            for observation in summary.get("observations", []):
                hypothesis.add(observation)
            if router is not None:
                candidate_support.append(router.candidate(hypothesis, last_frame))
        _write(task_root / "sam/candidate_sam_support.json", {"task": task,
            "candidate_support": candidate_support, "status": "COMPLETE", "gt_accessed": False})
        _write(task_root / "identity/entity_registry_pre_guard.json", _read(task_root / "entity_registry.json", {}))
        manifest["stages"].append({"stage": "binding_sam_fusion_candidate_admission", "status": "COMPLETE",
            "binding": binding_audit.get("decision"), "sam_target_status": target_sam.get("status"),
            "candidate_count": len(candidate_rows)})

        timings['sam_binding_fusion']=time.monotonic()-stage_start
        stage_start=time.monotonic()
        # Phase 3: frozen appearance model and unchanged V2.6 Identity Guard.
        current_stage = "appearance_identity_guard"
        reid_audit = v25_reid.run_reid(task)
        guard_audit = v26_pipeline.run_video(task)
        raw_identity = _read(task_root / "identity_timeline.json", {}).get("phone_timeline", [])
        registry = _read(task_root / "entity_registry.json", {}) or {}
        reinit = _read(task_root / "sam_reinit_log.json", {}) or {}
        stream = _read(task_root / "candidate_stream.json", stream.as_json()) or {}
        timeline, authorizations, projections = _canonical_identity(video_id, task_root, raw_identity,
            guard_audit, registry, stream, reinit, float(metadata.get("fps", 1)))
        identity_dir = task_root / "identity"
        registry_canonical = _remap_paths(deepcopy(registry), video_id)
        _write(identity_dir / "entity_registry.json", registry_canonical)
        _write(identity_dir / "identity_timeline.json", {"video_id": video_id, "phone_timeline": timeline,
            "identity_event_store": projections["identity_events"], "registry_projection": projections["registry_projection"]})
        _write(identity_dir / "identity_authorizations.json", authorizations)
        _write(identity_dir / "reid_audit.json", _remap_paths(guard_audit, video_id))
        _write(identity_dir / "v25_reid_audit.json", _remap_paths(reid_audit, video_id))
        _write(identity_dir / "candidate_stream.json", _remap_paths(stream, video_id))
        _write(identity_dir / "appearance_bank.json", {"source": "fresh V2.6 Identity Guard attempts",
            "last_attempt": next((a.get("bank_prototypes") for a in reversed(guard_audit.get("attempts", []))
                                  if a.get("bank_prototypes")), None), "gt_accessed": False})
        manifest["stages"].append({"stage": "appearance_and_identity_guard", "status": "COMPLETE",
            "guard_decision": guard_audit.get("decision"), "identity_confirmations": len(authorizations)})

        timings['reid_guard']=time.monotonic()-stage_start
        stage_start=time.monotonic()
        # Phase 4: one mask authorizer applies to target, candidate, reinitialized and dense masks.
        current_stage = "identity_state_and_mask_authorization"
        mask_refs, mask_audit, mask_paths = _store_masks(video_id, task_root, task_root, timeline, authorizations)
        timeline = _reconcile_forward_timeline(timeline, authorizations, mask_refs)
        identity_doc = _read(identity_dir / "identity_timeline.json", {}) or {}
        identity_doc["phone_timeline"] = timeline
        identity_doc["identity_event_store"] = [{"event_id": row["identity_event_id"],
            "video_id": video_id, "frame": row["frame_index"], "time": row["timestamp"],
            "state": "IDENTITY_CONFIRMED" if row["state"] == "MATCHED" else row["state"],
            "candidate_id": row.get("candidate_id"), "authorization_id": row.get("authorization_id"),
            "provenance": row.get("provenance", [])} for row in timeline]
        _write(identity_dir / "identity_timeline.json", identity_doc)
        _write(task_root / "segmentation/target_masks.json", [r for r in mask_refs if r.get("object_id") == "phone_01"])
        _write(task_root / "segmentation/mask_authorization.json", mask_audit)
        _write(task_root / "segmentation/mask_references.json", mask_refs)
        manifest["stages"].append({"stage": "unified_mask_authorization", "status": "COMPLETE",
            "mask_refs": len(mask_refs), "trusted": sum(r.get("trusted") is True for r in mask_refs)})

        timings['mask_authorization']=time.monotonic()-stage_start
        stage_start=time.monotonic()
        # Build trusted target/anchor frames exclusively from fresh V2.1/V2.6 outputs.
        current_stage = "event_detection_and_dense_reinspection"
        frames_for_graph = _identity_memory_frames(video_id, task_root, inputs, registry, timeline,
                                                    float(metadata.get("fps", 1)), mask_refs)
        size = (int(metadata.get("width", 1)), int(metadata.get("height", 1)))
        fps = float(metadata.get("fps", 1))
        accepted_masks = []
        for ref in mask_refs:
            if ref.get("trusted") and ref.get("source_kind") == "target_full":
                accepted_masks.append({"frame": ref["frame"], "trusted": True,
                    "mask_bbox": ref.get("bbox"), "mask_area": ref.get("mask_area"),
                    "mask_reference": ref["artifact_path"]})
        last_frame = max((int(x["frame_index"]) for x in metadata.get("sampled_frames", [])), default=0)
        events, stage_audit = _event_candidates(video_id, timeline, frames_for_graph, accepted_masks,
                                                 fps, last_frame, registry, size)
        recovery = __import__("memory_graph.v292.events", fromlist=["recovery_episodes"]).recovery_episodes(
            timeline, authorizations, fps)
        _write(task_root / "events/event_candidates.json", stage_audit)
        _write(task_root / "events/selected_events.json", events)
        _write(task_root / "events/recovery_episodes.json", recovery)
        dense_summaries, anchors_all, pair_requests_all = [], [], []
        dense_mask_refs, vlm_grounding_all, physical_candidates, physical_decisions = [], [], [], []
        dense_runner = None
        vlm_state = []
        from memory_graph.v29 import dense_reinspection as dense_module
        original_frame_numbers = dense_module.frame_numbers
        def cover_requested_end(event_spec, requested_fps, native_fps):
            numbers = original_frame_numbers(event_spec, requested_fps, native_fps)
            end = int(event_spec["end_frame"])
            if numbers and numbers[-1] < end:
                numbers = [*numbers, end]
            return numbers
        for event in events:
            event_root = task_root / "events/dense" / event["event_id"]
            from memory_graph.v292.events import cache_signature
            event_signature = cache_signature(video_sha256=raw_hash, start_frame=event["start_frame"],
                end_frame=event["end_frame"], pipeline_version="2.9.2", code_config_sha256=config_hash,
                yolo_model=config["yolo"]["model"], yolo_config=config["yolo"],
                sam_model=config["sam"]["checkpoint"], sam_config=config["sam"],
                sampling_policy=config["dense_sampling"])
            if dense_runner is None:
                from memory_graph.v29.dense_reinspection import DenseRunner
                dense_runner = DenseRunner()
            dense_module.frame_numbers = cover_requested_end
            try:
                dense_summary = dense_runner.run(task, event, accepted_masks, fps, event_root)
            finally:
                dense_module.frame_numbers = original_frame_numbers
            dense_path = event_root / "dense_observations.json"
            dense = _read(dense_path, {}) or {}
            dense["signature"] = event_signature
            dense["sampling"]["requested_start_frame"] = event["start_frame"]
            dense["sampling"]["requested_end_frame"] = event["end_frame"]
            dense["sampling"]["requested_interval_fully_covered"] = (
                dense["sampling"].get("start_frame", -1) <= event["start_frame"]
                and dense["sampling"].get("end_frame", -1) >= event["end_frame"])
            rows, dense_refs = _authorize_dense_rows(video_id, event, dense, timeline, task_root)
            dense_mask_refs.extend(dense_refs.values())
            anchors_result, anchors = _recover_anchors(video_id, event, dense, size)
            anchors_all.extend(anchors)
            _write(task_root / "anchors/event_local_anchors.json", anchors_all)
            _write(task_root / "anchors/anchor_provenance.json", anchors_all)
            _write(event_root / "dense_observations.json", dense)
            # Only the requested window is represented in the cache manifest; no older cache is read.
            _write(event_root / "cache_signature.json", {"signature": event_signature,
                "requested_start_frame": event["start_frame"], "requested_end_frame": event["end_frame"],
                "actual_start_frame": dense.get("sampling", {}).get("start_frame"),
                "actual_end_frame": dense.get("sampling", {}).get("end_frame"),
                "reused": False, "video_sha256": raw_hash, "canonical_config_sha256": config_hash})
            _write(event_root / "anchor_recovery.json", anchors_result)
            dense_summaries.append({**dense_summary, "event_id": event["event_id"],
                "cache_signature": event_signature,
                "requested_interval_fully_covered": dense["sampling"]["requested_interval_fully_covered"]})
            # Preserve old pair evidence requests only to drive unchanged bounded evidence recovery.
            from memory_graph.v292.vlm_pairs import build_pair_request
            pair_rows=[{'frame':r['frame'],'time':r.get('time'),'target_authorized':True,
                'authorization_id':r.get('authorization_id'),'target_bbox':r['sam_phone']['bbox'],
                'target_mask_path':None,'anchors':r.get('anchors',[])} for r in dense['rows']
                if r.get('identity_authorized') and r.get('sam_phone')]
            for anchor in sorted(anchors,key=lambda a:(-int(a.get('co_visible_frames',0)),a['anchor_key']))[:2]:
                pair_requests_all.append(build_pair_request(video_id=video_id,event=event,target_id='phone_01',anchor=anchor,rows=pair_rows))
        _write(task_root/'vlm/pair_requests.json',pair_requests_all)
        _write(task_root/'events/dense_windows.json',dense_summaries)
        # Match existing development source observations without promoting physical relations.
        memory_frames=_identity_memory_frames(video_id,task_root,inputs,registry,timeline,fps,mask_refs)
        observations=[]
        for frame in memory_frames:
            for o in frame['observations']+frame['anchors']:
                observations.append({'observation_id':o.observation_id,'entity_id':o.entity_id,'frame':o.frame,
                    'time':o.time,'status':o.identity,'provenance':[o.observation_id,o.source],
                    'bbox':o.bbox,'raw_detector_label':o.label})
        _write(task_root/'memory/observations.json',observations)
        future_updates=canonical._update_future_appearance_bank(video,video_id,task_root,mask_refs,authorizations,fps)
        bank=_read(task_root/'identity/appearance_bank.json',{})
        bank.update(future_authorized_updates=future_updates,future_update_count=len(future_updates))
        _write(task_root/'identity/appearance_bank.json',bank)
        _write(task_root/'run_manifest.json',manifest)
        del router, dense_runner
        gc.collect();torch.cuda.empty_cache()
        from memory_graph.v293.sources import EvidenceSources
        source=EvidenceSources();prepared=[]
        try:
            for event in events:
                spec,rows,anchors,masks,log,size,fps=source.prepare(video_id,event)
                prepared.append({'event':spec,'rows':rows,'masks':masks,'size':size,'fps':fps})
        finally:source.close()
        _write(root/'recovered'/video_id/'prepared_events.json',prepared)
        timings['dense_evidence_recovery']=time.monotonic()-stage_start
        timings['upstream_total']=time.monotonic()-started
        manifest.update(status='COMPLETE',runtime=timings)
        _write(task_root/'run_manifest.json',manifest)
    return manifest
