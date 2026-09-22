from pathlib import Path
from collections.abc import Iterator
import cv2
import numpy as np
from ..models import FrameInfo, VideoMetadata


class VideoReader:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(f"Input video does not exist: {self.path.resolve()}")
        cap = cv2.VideoCapture(str(self.path))
        try:
            if not cap.isOpened():
                raise ValueError(f"OpenCV cannot open video: {self.path}")
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if fps <= 0 or not np.isfinite(fps) or count <= 0:
                raise ValueError("Video needs valid FPS and frame count; variable-rate timing is not supported")
            self.metadata = VideoMetadata(fps=fps, frame_count=count,
                width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                duration=count/fps)
        finally:
            cap.release()

    def frames(self, sample_fps: float | None = None) -> Iterator[tuple[FrameInfo, np.ndarray]]:
        if sample_fps is not None and sample_fps <= 0:
            raise ValueError("sample_fps must be positive")
        cap = cv2.VideoCapture(str(self.path))
        rate = min(sample_fps or self.metadata.fps, self.metadata.fps)
        next_time = 0.0
        sampled = []
        count = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                index = count
                count += 1
                timestamp = index/self.metadata.fps
                if timestamp+1e-9 >= next_time or index == self.metadata.frame_count-1:
                    info = FrameInfo(frame_index=index, timestamp=timestamp)
                    sampled.append(info)
                    yield info, frame
                    next_time += 1/rate
            if count != self.metadata.frame_count:
                raise RuntimeError(f"Incomplete/ambiguous decode: read {count}, metadata advertises {self.metadata.frame_count} frames")
            self.metadata.decoded_frame_count = count
            self.metadata.sampled_frames = sampled
        finally:
            cap.release()
