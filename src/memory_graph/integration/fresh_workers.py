"""Model workers; imported only by explicit process stages, never session search."""
from .adapters import read,sha
from .fresh_video import save


def cv_worker(root,session):
    import time
    import cv2
    from memory_graph.config import DetectorConfig,TrackingConfig,ObjectsConfig
    from memory_graph.models import FrameInfo
    from memory_graph.perception.detector import Detector
    from memory_graph.perception.tracker import ObjectTracker
    manifest=read(session/'source_manifest.json');video=manifest['video'];start=time.monotonic()
    model=root/'.models/yolo11s.pt'
    if not model.is_file():raise FileNotFoundError('EXISTING_YOLO_WEIGHTS_REQUIRED')
    config=DetectorConfig(model=str(model),device='0')
    save(session/'cv/configuration.json',dict(model_sha256=sha(model),detector=config.model_dump(),
        tracking=TrackingConfig().model_dump(),identity_policy='NO_ENROLLMENT_NO_AUTHORIZATION',
        sample_fps=manifest['config']['cv_fps']))
    save(session/'cv/identity_guard.json',dict(aliases=[],authorizations=[],final_ledger=[],
        reason='Fresh video has no identity enrollment. Local ByteTrack IDs grant no capabilities.'))
    detector=Detector(config);tracker=ObjectTracker(TrackingConfig(),detector.names,ObjectsConfig(),manifest['config']['cv_fps'])
    tracks={};count=0
    try:
        for f in manifest['frames']:
            path=root/f['path']
            if sha(path)!=f['sha256']:raise ValueError('CV_FRAME_HASH_MISMATCH')
            im=cv2.imread(str(path))
            if im is None or im.shape[:2]!=(video['height'],video['width']):raise ValueError('CV_SOURCE_DIMENSIONS')
            detections=detector.detect(im,FrameInfo(frame_index=f['source_frame_index'],timestamp=f['source_time_s']))
            tracked=tracker.update(detections,'session',im.shape[:2]);lookup={tuple(o.bbox):o for o in tracked}
            rows=[]
            for n,d in enumerate(detections):
                track=lookup.get(tuple(d.bbox));tid=track.object_id if track else f"untracked_{f['source_frame_index']}_{n}"
                label=ObjectsConfig().aliases.get(d.class_name,d.class_name)
                tracks.setdefault(tid,dict(track_id=tid,detector_class=label,observations=[]))['observations'].append(
                    dict(frame_index=d.frame_index,timestamp=d.timestamp,bbox=list(d.bbox),confidence=d.confidence))
                rows.append(dict(**d.model_dump(),track_candidate=tid,tracker_id=track.tracker_id if track else None,
                    source_frame=f,identity_authorized=False))
            save(session/'cv/frames'/f"f{f['source_frame_index']:08d}.json",rows);count+=1
    finally:
        save(session/'cv/tracks.json',list(tracks.values()))
        save(session/'cv/receipt.json',dict(frames_completed=count,frames_requested=len(manifest['frames']),
            observations=sum(len(t['observations']) for t in tracks.values()),elapsed_s=time.monotonic()-start,
            identity_authorizations=0,tracker_is_not_persistent_identity=True))


def perception_worker(root,session,stage):
    from .perception_runtime import localize,refine
    manifest=read(session/'source_manifest.json');plan=read(session/'localization/plan.json')
    frames=plan['frames'];output=session/'localization'
    if stage=='localization':localize(root,frames,output,manifest['localization_query'],None,[1008,560])
    elif stage=='sam':
        # Failed/missing localization frames remain absent, never fabricated.
        ready=[f for f in frames if (output/'perception'/f['frame_id']/'parsed.json').exists()]
        if ready:refine(root,ready,output)
        else:raise RuntimeError('NO_LOCALIZATION_OUTPUT_FOR_SAM')
