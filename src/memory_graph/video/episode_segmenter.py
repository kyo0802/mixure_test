import cv2
from ..config import EpisodesConfig
from ..models import Episode, FrameInfo, VideoMetadata


class EpisodeSegmenter:
    """Global HSV appearance cuts with duration/cooldown; not activity recognition."""
    def __init__(self, config: EpisodesConfig):
        self.config = config
        self.previous = None
        self.starts = [FrameInfo(frame_index=0, timestamp=0)]

    def observe(self, info: FrameInfo, frame) -> None:
        hsv = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 8, 8], [0, 180, 0, 256, 0, 256])
        cv2.normalize(hist, hist, norm_type=cv2.NORM_L1)
        if self.previous is not None:
            change = cv2.compareHist(self.previous, hist, cv2.HISTCMP_BHATTACHARYYA)
            elapsed = info.timestamp-self.starts[-1].timestamp
            if change >= self.config.scene_change_threshold and elapsed >= max(
                    self.config.min_duration_seconds, self.config.cooldown_seconds):
                self.starts.append(info)
        self.previous = hist

    def finish(self, metadata: VideoMetadata) -> list[Episode]:
        starts = list(self.starts)
        if len(starts) > 1 and metadata.duration-starts[-1].timestamp < self.config.min_duration_seconds:
            starts.pop()
        episodes = []
        for i, start in enumerate(starts):
            following = starts[i+1] if i+1 < len(starts) else None
            episodes.append(Episode(episode_id=f"ep_{i+1:04d}", start_time=start.timestamp,
                end_time=following.timestamp if following else metadata.duration,
                start_frame=start.frame_index,
                end_frame=following.frame_index-1 if following else metadata.frame_count-1))
        return episodes


def episode_for(frame_index: int, episodes: list[Episode]) -> Episode:
    for episode in episodes:
        if episode.start_frame <= frame_index <= episode.end_frame:
            return episode
    raise ValueError(f"Frame {frame_index} is outside episodes")
