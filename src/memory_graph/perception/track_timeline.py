from collections import defaultdict
from math import hypot
from pydantic import Field
from scipy.spatial import cKDTree
from ..models import Model, Probability, Time, Detection
from ..spatial.geometry import pair_signals


class TrackObservation(Detection):
    track_id: int
    detector_class: str
    raw_tracker_id: int
    episode_id: str
    area_fraction: float = 0
    normalized_center: tuple[float, float] = (0, 0)
    velocity: tuple[float, float] = (0, 0)
    speed: float = 0
    nearest_tracks: list[dict] = Field(default_factory=list)
    distance_to_person: float | None = None


class TrackTimeline(Model):
    track_id: int
    source_track_key: str
    detector_class: str
    first_seen: Time
    last_seen: Time
    mean_detector_confidence: Probability
    observations: list[TrackObservation]
    visibility: list[bool]
    is_anchor: bool = False
    anchor_score: Probability = 0


def build_timelines(tracks, metadata, anchors, nearest_neighbors=3):
    anchor_map = {a.object_id: a for a in anchors}
    timelines = []
    frames = defaultdict(list)
    for tid, track in enumerate(tracks, 1):
        observations = []
        previous = None
        for source in track.observations:
            x1, y1, x2, y2 = source.bbox
            center = (source.center[0]/metadata.width, source.center[1]/metadata.height)
            velocity = (0, 0)
            if previous and 0 < source.timestamp-previous.timestamp <= 1:
                dt = source.timestamp-previous.timestamp
                velocity = tuple((center[i]-previous.normalized_center[i])/dt for i in range(2))
            obs = TrackObservation(**source.model_dump(exclude={"object_id", "tracker_id", "center"}),
                track_id=tid, detector_class=source.class_name, raw_tracker_id=source.tracker_id,
                normalized_center=center, velocity=velocity, speed=hypot(*velocity),
                area_fraction=(x2-x1)*(y2-y1)/(metadata.width*metadata.height))
            observations.append(obs)
            frames[obs.frame_index].append(obs)
            previous = obs
        seen = {o.frame_index for o in observations}
        anchor = anchor_map.get(track.object_id)
        timelines.append(TrackTimeline(track_id=tid, source_track_key=track.object_id, detector_class=track.class_name,
            first_seen=track.first_seen, last_seen=track.last_seen, observations=observations,
            mean_detector_confidence=sum(o.confidence for o in observations)/len(observations),
            visibility=[f.frame_index in seen for f in metadata.sampled_frames],
            is_anchor=anchor.is_anchor if anchor else False, anchor_score=anchor.anchor_score if anchor else 0))
    for observations in frames.values():
        if len(observations) < 2:
            continue
        tree = cKDTree([o.normalized_center for o in observations])
        persons = [o for o in observations if o.detector_class == "person"]
        for obs in observations:
            _, indices = tree.query(obs.normalized_center, k=min(nearest_neighbors+1, len(observations)))
            for index in indices:
                other = observations[int(index)]
                if other.track_id == obs.track_id:
                    continue
                signals = pair_signals(obs.bbox, other.bbox, metadata.width, metadata.height)
                obs.nearest_tracks.append({"track_id": other.track_id,
                    "center_distance": hypot(signals["dx"], signals["dy"]), **signals})
            if persons:
                obs.distance_to_person = min(hypot(obs.normalized_center[0]-p.normalized_center[0],
                    obs.normalized_center[1]-p.normalized_center[1]) for p in persons)
    return timelines
