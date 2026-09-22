"""ByteTrack associations are local continuity, not long-term object ReID."""
from collections import defaultdict
from math import ceil
from types import SimpleNamespace
import inspect
import numpy as np
from ..config import ObjectsConfig, TrackingConfig
from ..models import Detection, ObjectObservation, ObjectTrack
from .object_classifier import canonical_class, id_prefix
from .runtime import configure_ultralytics


class ObjectTracker:
    def __init__(self, config: TrackingConfig, classes: dict[int, str], objects: ObjectsConfig, sample_fps: float):
        configure_ultralytics()
        from ultralytics.trackers.byte_tracker import BYTETracker
        self.tracker_type = BYTETracker
        self.config, self.classes, self.objects = config, classes, objects
        self.sample_fps = sample_fps
        self.counts = defaultdict(int)
        self.identities = {}
        self.tracks: dict[str, ObjectTrack] = {}
        self.episode_id = None
        self.trackers = {}

    def _reset(self, episode_id):
        self.episode_id = episode_id
        old_api = "frame_rate" in inspect.signature(self.tracker_type).parameters
        args = SimpleNamespace(track_high_thresh=self.config.high_threshold,
            track_low_thresh=self.config.low_threshold, new_track_thresh=self.config.new_track_threshold,
            match_thresh=self.config.match_threshold, fuse_score=True,
            track_buffer=ceil(self.config.lost_seconds*(30 if old_api else self.sample_fps)))
        # Construct every class tracker before updates: constructors reset a shared numeric ID counter.
        self.trackers = {cid: self.tracker_type(args, **({"frame_rate": self.sample_fps} if old_api else {}))
                         for cid in self.classes}

    def update(self, detections: list[Detection], episode_id: str, shape: tuple[int, int]) -> list[ObjectObservation]:
        from ultralytics.engine.results import Boxes
        if self.episode_id != episode_id:
            self._reset(episode_id)
        grouped = defaultdict(list)
        for detection in detections:
            grouped[detection.class_id].append(detection)
        observations = []
        for cid, tracker in self.trackers.items():
            raw = grouped[cid]
            values = np.array([[*d.bbox, d.confidence, d.class_id] for d in raw], dtype=np.float32).reshape(-1, 6)
            rows = tracker.update(Boxes(values, orig_shape=shape))
            for row in rows:
                tracker_id, detection_index = int(row[4]), int(row[-1])
                detection = raw[detection_index]
                name = canonical_class(detection.class_name, self.objects)
                key = (episode_id, cid, tracker_id)
                if key not in self.identities:
                    prefix = id_prefix(name)
                    self.counts[prefix] += 1
                    object_id = f"{prefix}_{self.counts[prefix]:02d}"
                    self.identities[key] = object_id
                    self.tracks[object_id] = ObjectTrack(object_id=object_id, class_name=name,
                        first_seen=detection.timestamp, last_seen=detection.timestamp)
                object_id = self.identities[key]
                observation = ObjectObservation(**detection.model_dump(exclude={"center", "class_name"}),
                    class_name=name, object_id=object_id, tracker_id=tracker_id, episode_id=episode_id)
                track = self.tracks[object_id]
                track.last_seen = observation.timestamp
                track.observations.append(observation)
                observations.append(observation)
        return observations
