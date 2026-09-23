"""V2 perception cache is independent of V1; semantics never rename tracker IDs."""
import hashlib
import json
import logging
import time
from importlib.metadata import version
from pathlib import Path
from ..models import VideoMetadata, Episode, ObjectTrack, AnchorInfo
from ..video.reader import VideoReader
from ..video.episode_segmenter import EpisodeSegmenter, episode_for
from .detector import Detector
from .tracker import ObjectTracker
from ..spatial.anchor_selector import select_anchors
from ..memory.memory_store import save_json
from .track_timeline import TrackTimeline, build_timelines

log = logging.getLogger(__name__)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collect_tracks(source, output, config):
    output = Path(output)
    reader = VideoReader(source)
    fingerprint = hashlib.sha256(json.dumps({"video": sha256(source), "config": config.perception.model_dump(),
        "neighbors": config.events.nearest_neighbors, "version": "v2-timelines-2",
        "runtime": {name: version(name) for name in ("torch", "ultralytics", "opencv-python")},
        "weights": sha256(config.perception.detector.model) if Path(config.perception.detector.model).is_file() else config.perception.detector.model}, sort_keys=True).encode()).hexdigest()
    cache = output/"perception_cache.json"
    if cache.exists() and json.loads(cache.read_text())["fingerprint"] == fingerprint:
        try:
            metadata = VideoMetadata.model_validate_json((output/"video_metadata.json").read_text())
            episodes = [Episode.model_validate(x) for x in json.loads((output/"episodes.json").read_text())]
            timelines = [TrackTimeline.model_validate(x) for x in json.loads((output/"track_timelines.json").read_text())]
            log.info("Reusing verified V2 perception cache (%d track IDs)", len(timelines))
            return metadata, episodes, timelines
        except (OSError, ValueError, KeyError):
            log.warning("Perception cache incomplete; recomputing")
    segmenter = EpisodeSegmenter(config.perception.episodes)
    for info, image in reader.frames(config.perception.video.sample_fps):
        segmenter.observe(info, image)
    episodes = segmenter.finish(reader.metadata)
    detector = Detector(config.perception.detector)
    tracker = ObjectTracker(config.perception.tracking, detector.names, config.perception.objects,
                            min(config.perception.video.sample_fps, reader.metadata.fps))
    raw = []
    last_log = time.monotonic()
    for info, image in reader.frames(config.perception.video.sample_fps):
        detections = detector.detect(image, info)
        raw.extend(detections)
        tracker.update(detections, episode_for(info.frame_index, episodes).episode_id, image.shape[:2])
        if time.monotonic()-last_log > 15:
            log.info("Perception %.1f / %.1fs", info.timestamp, reader.metadata.duration)
            last_log = time.monotonic()
    tracks = list(tracker.tracks.values())
    anchors = select_anchors(tracks, reader.metadata.width, reader.metadata.height, config.perception.anchors)
    timelines = build_timelines(tracks, reader.metadata, anchors, config.events.nearest_neighbors)
    save_json(output/"video_metadata.json", reader.metadata)
    save_json(output/"episodes.json", episodes)
    save_json(output/"detections.json", raw)
    save_json(output/"track_timelines.json", timelines)
    save_json(output/"track_id_mapping.json", [{"track_id": t.track_id, "source_track_key": t.source_track_key,
        "raw_tracker_ids": sorted({o.raw_tracker_id for o in t.observations})} for t in timelines])
    save_json(cache, {"fingerprint": fingerprint, "source_sha256": sha256(source)})
    return reader.metadata, episodes, timelines
