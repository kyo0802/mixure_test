from memory_graph.models import ObjectTrack, ObjectObservation, VideoMetadata, FrameInfo
from memory_graph.perception.track_timeline import build_timelines
from memory_graph.events.models import EventProposal, Keyframe


def timelines(paths, classes=None, step=.4, duration=6):
    classes = classes or ["cup", "chair", "chair"]
    tracks = []
    for tid, points in enumerate(paths, 1):
        obs = [ObjectObservation(object_id=f"source_{tid}", tracker_id=tid, class_id=tid,
            class_name=classes[tid-1], bbox=(x, y, x+10, y+10), confidence=.95,
            frame_index=round(i*step*10), timestamp=i*step, episode_id="ep_0001")
            for i, (x, y) in enumerate(points)]
        tracks.append(ObjectTrack(object_id=f"source_{tid}", class_name=classes[tid-1], first_seen=0,
                                  last_seen=obs[-1].timestamp, observations=obs))
    meta = VideoMetadata(fps=10, frame_count=int(duration*10), width=100, height=100, duration=duration,
        decoded_frame_count=int(duration*10), sampled_frames=[FrameInfo(frame_index=i, timestamp=i/10) for i in range(0,int(duration*10),2)])
    meta.sampled_frames.append(FrameInfo(frame_index=meta.frame_count-1,timestamp=(meta.frame_count-1)/10))
    return build_timelines(tracks,meta,[],3), meta


def event(ids=(1,2), event_id="evt_001", start=0, peak=1, end=2):
    return EventProposal(event_id=event_id,event_type="interaction_candidate",episode_id="ep_0001",
        start_time=start,peak_time=peak,end_time=end,involved_track_ids=list(ids),confidence=.9,
        signals=["proximity_change"],selected=True)


def frames(times=(0,.8,1.6), ids=(1,2)):
    return [Keyframe(phase=phase,frame_index=round(t*10),timestamp=t,desired_timestamp=t,
        image_path=phase+'.jpg',visible_track_ids=list(ids),supplied_track_ids=list(ids),sharpness=100,selection_score=.8)
        for phase,t in zip(['before','during','after'],times)]
