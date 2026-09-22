from bisect import bisect_right
from collections import defaultdict
from pathlib import Path
import cv2
from ..config import VisualizationConfig
from ..models import AnchorInfo, Episode, ObjectTrack, StableRelation, FrameInfo
from ..video.reader import VideoReader
from ..video.episode_segmenter import episode_for


def render_video(source: str | Path, output: str | Path, tracks: list[ObjectTrack], anchors: list[AnchorInfo],
                 relations: list[StableRelation], episodes: list[Episode], sampled_frames: list[FrameInfo],
                 config: VisualizationConfig) -> dict:
    reader = VideoReader(source)
    metadata = reader.metadata
    scale = min(1, config.max_video_width/metadata.width)
    size = (int(metadata.width*scale)//2*2, int(metadata.height*scale)//2*2)
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), metadata.fps, size)
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not initialize the MP4 writer")
    by_frame = defaultdict(list)
    for track in tracks:
        for observation in track.observations:
            by_frame[observation.frame_index].append(observation)
    indices = [f.frame_index for f in sampled_frames]
    anchor_ids = {a.object_id for a in anchors if a.is_anchor}
    stable_by_frame = {sample.frame_index: [r for r in relations if r.start_frame <= sample.frame_index <= r.end_frame]
                       for sample in sampled_frames}
    written = 0
    try:
        for info, frame in reader.frames():
            frame = cv2.resize(frame, size)
            evidence_index = indices[max(0, bisect_right(indices, info.frame_index)-1)]
            observations = by_frame[evidence_index]
            visible = {o.object_id for o in observations}
            object_labels = []
            for obs in observations:
                is_anchor = obs.object_id in anchor_ids
                color = (65, 190, 245) if is_anchor else (235, 195, 110)
                x1, y1, x2, y2 = [int(v*scale) for v in obs.bbox]
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = f"{obs.object_id} | {'ANCHOR' if is_anchor else 'TRACKED'} {obs.confidence:.2f}"
                object_labels.append((label, x1, y1, color))
            episode = episode_for(info.frame_index, episodes)
            lines = [f"{episode.episode_id} | t={info.timestamp:.2f}s | 2D RGB memory",
                     f"Sample evidence held from {evidence_index/metadata.fps:.2f}s | retrospective labels"]
            active = [r for r in stable_by_frame[evidence_index] if r.subject_id in visible and r.object_id in visible
                      and r.episode_id == episode.episode_id]
            active.sort(key=lambda r: (r.reference_frame == "camera", -r.confidence))
            lines.extend(f"{r.subject_id} -> {r.predicate} -> {r.object_id}" for r in active[:config.overlay_relations])
            text_scale = min(.52, max(.22, size[0]/2400))
            line_height = max(13, int(44*text_scale))
            panel_height = min(size[1], 10+line_height*len(lines))
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (size[0], panel_height), (20, 25, 30), -1)
            cv2.addWeighted(overlay, .75, frame, .25, 0, frame)
            for line_index, line in enumerate(lines):
                text_width = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, text_scale, 1)[0][0]
                fitted_scale = text_scale*min(1, (size[0]-20)/max(text_width, 1))
                cv2.putText(frame, line, (10, line_height*(line_index+1)), cv2.FONT_HERSHEY_SIMPLEX,
                            fitted_scale, (245, 245, 245), 1, cv2.LINE_AA)
            occupied = []
            for label, x, y, color in object_labels:
                font_scale = min(.48, size[0]/1400)
                (w, h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
                x = max(0, min(x, size[0]-w-6))
                y = max(panel_height+h+6, y-5)
                for _ in range(len(object_labels)+1):
                    y = min(y, size[1]-baseline-4)
                    rectangle = (x, y-h-3, x+w+5, y+baseline+2)
                    if not any(rectangle[0] < b[2] and b[0] < rectangle[2] and rectangle[1] < b[3] and b[1] < rectangle[3]
                               for b in occupied):
                        break
                    y += h+baseline+6
                occupied.append(rectangle)
                cv2.rectangle(frame, rectangle[:2], rectangle[2:], (20, 25, 30), -1)
                cv2.putText(frame, label, (x+2, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 1, cv2.LINE_AA)
            writer.write(frame)
            written += 1
    finally:
        writer.release()
    check = cv2.VideoCapture(str(output))
    try:
        if not check.isOpened() or int(check.get(cv2.CAP_PROP_FRAME_COUNT)) != written:
            raise RuntimeError("Annotated video validation failed")
        check.set(cv2.CAP_PROP_POS_FRAMES, max(0, written-1))
        ok, _ = check.read()
        if not ok:
            raise RuntimeError("Annotated video final frame cannot be decoded")
    finally:
        check.release()
    return {"frame_count": written, "fps": metadata.fps, "width": size[0], "height": size[1], "audio": False}
