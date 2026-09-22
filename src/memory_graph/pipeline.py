import logging
from pathlib import Path
import time
import torch
import cv2
from .config import Config
from .video.reader import VideoReader
from .video.episode_segmenter import EpisodeSegmenter, episode_for
from .perception.detector import Detector
from .perception.tracker import ObjectTracker
from .perception.object_classifier import canonical_class
from .spatial.anchor_selector import select_anchors
from .spatial.relation_extractor import extract_relations
from .memory.temporal_filter import stabilize
from .memory.graph_builder import build_graph, derive_transitions
from .memory.memory_store import save_json
from .visualization.graph_visualizer import render_graph
from .visualization.video_visualizer import render_video

logger = logging.getLogger(__name__)
ARTIFACTS = ["video_metadata.json", "episodes.json", "detections.json", "tracks.json", "anchors.json",
             "relation_observations.json", "stable_relations.json", "transitions.json", "memory_graph.json",
             "memory_graph.png", "annotated.mp4", "run_config.json", "run.log", "run_status.json"]


def run_video(source: str | Path, config: Config, output: str | Path | None = None, detector=None):
    """Run a fresh per-video pipeline. Detector injection is only for deterministic integration tests."""
    source = Path(source).resolve()
    reader = VideoReader(source)  # Fail before creating misleading output artifacts for missing inputs.
    output = Path(output) if output else Path("outputs")/source.stem
    output.mkdir(parents=True, exist_ok=True)
    # Only replace this pipeline's named artifacts, never arbitrary user files or input videos.
    artifacts = [output/name for name in ARTIFACTS] + list(output.glob("memory_graph_page_*.png"))
    if source in {p.resolve() for p in artifacts}:
        raise ValueError("Output artifacts would overwrite the input video")
    for path in artifacts:
        if path.is_file():
            path.unlink()
    handler = logging.FileHandler(output/"run.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(handler)
    started = time.monotonic()
    save_json(output/"run_status.json", {"status": "running", "video": str(source)})
    try:
        save_json(output/"run_config.json", config)
        metadata = reader.metadata
        logger.info("Loading %s; duration %.2fs, %d frames, %.3f FPS, %dx%d", source.name,
                    metadata.duration, metadata.frame_count, metadata.fps, metadata.width, metadata.height)
        logger.info("Segmenting episodes; sampling at %.2f FPS", min(config.video.sample_fps, metadata.fps))
        segmenter = EpisodeSegmenter(config.episodes)
        for info, frame in reader.frames(config.video.sample_fps):
            segmenter.observe(info, frame)
        episodes = segmenter.finish(metadata)
        save_json(output/"video_metadata.json", metadata)
        save_json(output/"episodes.json", episodes)
        logger.info("Found %d episodes; decoded all %d frames; sampled %d", len(episodes),
                    metadata.decoded_frame_count, len(metadata.sampled_frames))
        detector = detector or Detector(config.detector)
        supported = {canonical_class(name, config.objects) for name in detector.names.values()}
        unavailable = sorted(set(config.anchors.classes)-supported)
        if unavailable:
            logger.info("Configured anchor classes outside detector vocabulary: %s", ", ".join(unavailable))
        tracker = ObjectTracker(config.tracking, detector.names, config.objects, min(config.video.sample_fps, metadata.fps))
        logger.info("Running object detection and tracking...")
        detections = []
        last_log = time.monotonic()
        for i, (info, frame) in enumerate(reader.frames(config.video.sample_fps)):
            raw = detector.detect(frame, info)
            detections.extend(raw)
            tracker.update(raw, episode_for(info.frame_index, episodes).episode_id, (metadata.height, metadata.width))
            if time.monotonic()-last_log >= 15:
                logger.info("Tracking %.1f / %.1fs (%d sampled frames)", info.timestamp, metadata.duration, i+1)
                last_log = time.monotonic()
        tracks = list(tracker.tracks.values())
        save_json(output/"detections.json", detections)
        save_json(output/"tracks.json", tracks)
        logger.info("Found %d persistent track fragments from %d detections", len(tracks), len(detections))
        logger.info("Selecting anchors...")
        anchors = select_anchors(tracks, metadata.width, metadata.height, config.anchors)
        save_json(output/"anchors.json", anchors)
        anchor_count = sum(a.is_anchor for a in anchors)
        logger.info("Selected %d anchors", anchor_count)
        logger.info("Extracting relative relations...")
        observations = extract_relations(tracks, anchors, metadata.width, metadata.height, config)
        save_json(output/"relation_observations.json", observations)
        logger.info("Temporal filtering %d relation observations...", len(observations))
        stable = stabilize(observations, config.temporal_filter)
        transitions = derive_transitions(stable, config.transitions)
        save_json(output/"stable_relations.json", stable)
        save_json(output/"transitions.json", transitions)
        logger.info("Building memory graph: %d stable intervals, %d transitions", len(stable), len(transitions))
        run_metadata = metadata.model_dump(mode="json")
        run_metadata.update({"torch_version": torch.__version__, "opencv_version": cv2.__version__,
            "cuda_available": torch.cuda.is_available(), "device": detector.device, "detector_model": config.detector.model,
            "tracker": "class-specific ByteTrack", "identity_scope": "local tracking within an episode; not long-term ReID"})
        graph = build_graph(source.name, run_metadata, episodes, tracks, anchors, stable, transitions)
        save_json(output/"memory_graph.json", graph)
        logger.info("Saved %s", output/"memory_graph.json")
        render_graph(graph, output/"memory_graph.png", config.visualization.graph_nodes_per_page)
        logger.info("Saved %s", output/"memory_graph.png")
        if config.visualization.annotated_video:
            logger.info("Rendering full-duration annotated video...")
            render_video(source, output/"annotated.mp4", tracks, anchors, stable, episodes,
                         metadata.sampled_frames, config.visualization)
        for label, count in [("tracks", len(tracks)), ("anchors", anchor_count), ("relation observations", len(observations)),
                             ("stable relations", len(stable))]:
            if count == 0:
                logger.warning("No %s: inspect intermediate evidence and detector vocabulary; no data fabricated", label)
        required = ARTIFACTS[:10] + (["annotated.mp4"] if config.visualization.annotated_video else [])
        if any(not (output/name).is_file() or (output/name).stat().st_size == 0 for name in required):
            raise RuntimeError("Required output verification failed")
        save_json(output/"run_status.json", {"status": "complete", "video": str(source),
            "elapsed_seconds": time.monotonic()-started, "episodes": len(episodes), "tracks": len(tracks),
            "anchors": anchor_count, "relation_observations": len(observations), "stable_relations": len(stable),
            "transitions": len(transitions), "decoded_frames": metadata.decoded_frame_count})
        logger.info("Completed %s in %.1fs", source.name, time.monotonic()-started)
        return graph
    except Exception as error:
        save_json(output/"run_status.json", {"status": "failed", "video": str(source), "error": str(error)})
        logger.exception("Pipeline failed")
        raise
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()
