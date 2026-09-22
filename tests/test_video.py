import cv2
import numpy as np
import pytest
from memory_graph.video.reader import VideoReader
from memory_graph.video.episode_segmenter import EpisodeSegmenter
from memory_graph.config import EpisodesConfig


def make_video(path, frames=90, fps=10, cut=False):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 240))
    assert writer.isOpened()
    for i in range(frames):
        frame = np.full((240, 320, 3), (0, 180, 0) if cut and i >= 40 else (0, 0, 180), dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_reader_samples_both_endpoints_and_decodes_all(tmp_path):
    path = tmp_path/"synthetic.mp4"
    make_video(path)
    reader = VideoReader(path)
    samples = list(reader.frames(3))
    assert samples[0][0].frame_index == 0 and samples[-1][0].frame_index == 89
    assert reader.metadata.decoded_frame_count == 90
    assert all(a[0].timestamp < b[0].timestamp for a, b in zip(samples, samples[1:]))


def test_segmentation_cut_and_duration(tmp_path):
    path = tmp_path/"cut.mp4"
    make_video(path, cut=True)
    reader = VideoReader(path)
    segmenter = EpisodeSegmenter(EpisodesConfig(min_duration_seconds=2, cooldown_seconds=2))
    for info, image in reader.frames(3):
        segmenter.observe(info, image)
    episodes = segmenter.finish(reader.metadata)
    assert len(episodes) == 2
    assert episodes[0].start_frame == 0 and episodes[-1].end_frame == 89
    assert episodes[0].end_frame+1 == episodes[1].start_frame
    assert episodes[1].start_time == 4


def test_missing_input_fails_clearly(tmp_path):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        VideoReader(tmp_path/"absent.mp4")
